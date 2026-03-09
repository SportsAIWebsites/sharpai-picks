#!/usr/bin/env python3
"""
SharpAI Daily Picks Generator
Fetches odds from The Odds API, sends to Claude, generates HTML site
"""

import os
import json
import requests
import anthropic
from datetime import datetime, timezone
from pathlib import Path

# ── API Keys (set as GitHub Secrets) ──────────────────────────────────────────
ODDS_API_KEY   = os.environ["ODDS_API_KEY"]
ANTHROPIC_KEY  = os.environ["ANTHROPIC_API_KEY"]

# ── Sports to fetch ────────────────────────────────────────────────────────────
SPORTS = [
    "americanfootball_nfl",
    "basketball_nba",
    "baseball_mlb",
    "icehockey_nhl",
    "soccer_epl",
    "basketball_ncaab",
    "basketball_wnba",
]

SPORT_LABELS = {
    "americanfootball_nfl": ("NFL",     "nfl"),
    "basketball_nba":        ("NBA",     "nba"),
    "baseball_mlb":          ("MLB",     "mlb"),
    "icehockey_nhl":         ("NHL",     "nhl"),
    "soccer_epl":            ("Soccer",  "soccer"),
    "basketball_ncaab":      ("College", "ncaa"),
    "basketball_wnba":       ("WNBA",    "wnba"),
}


def fetch_odds(sport: str) -> list[dict]:
    """Pull today's odds from The Odds API."""
    url = f"https://api.the-odds-api.com/v4/sports/{sport}/odds"
    params = {
        "apiKey":  ODDS_API_KEY,
        "regions": "us",
        "markets": "h2h,spreads,totals",
        "oddsFormat": "american",
        "dateFormat": "iso",
    }
    try:
        r = requests.get(url, params=params, timeout=15)
        if r.status_code == 200:
            return r.json()[:3]          # max 3 games per sport
        print(f"  ⚠  {sport}: HTTP {r.status_code}")
        return []
    except Exception as e:
        print(f"  ⚠  {sport}: {e}")
        return []


def summarise_game(game: dict) -> str:
    """Flatten an Odds API game object into a short text summary."""
    lines = [
        f"Game: {game.get('away_team')} @ {game.get('home_team')}",
        f"Time: {game.get('commence_time', 'TBD')}",
    ]
    for bm in game.get("bookmakers", [])[:1]:      # use first bookmaker only
        for mkt in bm.get("markets", []):
            if mkt["key"] == "h2h":
                outcomes = {o["name"]: o["price"] for o in mkt["outcomes"]}
                lines.append(f"Moneyline: {outcomes}")
            elif mkt["key"] == "spreads":
                for o in mkt["outcomes"]:
                    lines.append(f"Spread: {o['name']} {o.get('point','')} @ {o['price']}")
            elif mkt["key"] == "totals":
                for o in mkt["outcomes"]:
                    lines.append(f"Total: {o['name']} {o.get('point','')} @ {o['price']}")
    return "\n".join(lines)


def ask_claude(games_text: str, sport_label: str) -> list[dict]:
    """Send game data to Claude and get back structured picks."""
    client = anthropic.Anthropic(api_key=ANTHROPIC_KEY)

    system = """You are SharpAI, an expert sports betting analyst.
Given game odds data, return ONLY a valid JSON array (no markdown, no explanation).
Each element must have exactly these fields:
{
  "sport": "<sport_label>",
  "sportLabel": "<display label>",
  "time": "<game time in ET, e.g. 7:30 PM ET>",
  "home": "<home team>",
  "away": "<away team>",
  "line": "<spread, ML, or O/U value e.g. -5.5 or ML or O 220.5>",
  "pickType": "<Spread | Moneyline | Over/Under>",
  "pickValue": "<full pick string e.g. Celtics -5.5>",
  "odds": "<american odds e.g. -110>",
  "confidence": "<high | med | low>",
  "analysis": "<2-3 sentence sharp analysis, data-driven, max 180 chars>",
  "ai": "<Model confidence: XX% — based on N predictive signals>"
}
Return only games you have a genuine edge on. Skip games with no clear edge."""

    prompt = f"""Sport: {sport_label}

Games data:
{games_text}

Return a JSON array of picks for these games."""

    try:
        msg = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=1000,
            system=system,
            messages=[{"role": "user", "content": prompt}],
        )
        raw = msg.content[0].text.strip()
        # strip accidental markdown fences
        if raw.startswith("```"):
            raw = raw.split("```")[1]
            if raw.startswith("json"):
                raw = raw[4:]
        return json.loads(raw.strip())
    except Exception as e:
        print(f"  ⚠  Claude error for {sport_label}: {e}")
        return []


def build_html(all_picks: list[dict], date_str: str) -> str:
    """Render the full HTML page from picks data."""
    picks_json = json.dumps(all_picks, ensure_ascii=False)
    total      = len(all_picks)
    high_conf  = sum(1 for p in all_picks if p.get("confidence") == "high")

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>SharpAI — Daily Sports Picks</title>
<link href="https://fonts.googleapis.com/css2?family=Barlow+Condensed:wght@400;600;700;800;900&family=Barlow:wght@300;400;500;600&display=swap" rel="stylesheet">
<style>
  :root{{
    --bg:#f7f8fa;--surface:#ffffff;--border:#e8eaee;--text:#0d1117;
    --text-muted:#6b7280;--accent:#0057ff;--accent-light:#e8f0ff;
    --green:#00a86b;--green-light:#e6f7f1;--red:#e63946;--red-light:#fdecea;
    --gold:#f59e0b;--gold-light:#fef3c7;
    --shadow:0 1px 3px rgba(0,0,0,.08),0 4px 16px rgba(0,0,0,.04);
    --shadow-hover:0 4px 12px rgba(0,0,0,.12),0 8px 32px rgba(0,0,0,.08);
  }}
  *{{margin:0;padding:0;box-sizing:border-box}}
  body{{font-family:'Barlow',sans-serif;background:var(--bg);color:var(--text);min-height:100vh}}
  header{{background:var(--surface);border-bottom:1px solid var(--border);position:sticky;top:0;z-index:100}}
  .header-inner{{max-width:1280px;margin:0 auto;padding:0 24px;display:flex;align-items:center;justify-content:space-between;height:64px}}
  .logo{{display:flex;align-items:center;gap:10px;text-decoration:none}}
  .logo-icon{{width:36px;height:36px;background:var(--accent);border-radius:8px;display:flex;align-items:center;justify-content:center;font-family:'Barlow Condensed',sans-serif;font-weight:900;font-size:18px;color:white;letter-spacing:-1px}}
  .logo-text{{font-family:'Barlow Condensed',sans-serif;font-weight:800;font-size:22px;color:var(--text);letter-spacing:.5px}}
  .logo-text span{{color:var(--accent)}}
  nav{{display:flex;align-items:center;gap:4px}}
  nav a{{font-size:14px;font-weight:500;color:var(--text-muted);text-decoration:none;padding:6px 14px;border-radius:6px;transition:all .15s}}
  nav a:hover,nav a.active{{color:var(--text);background:var(--bg)}}
  nav a.active{{color:var(--accent);font-weight:600}}
  .record-badge{{background:var(--green-light);color:var(--green);font-size:13px;font-weight:600;padding:5px 12px;border-radius:20px;display:flex;align-items:center;gap:6px}}
  .record-badge::before{{content:'';width:7px;height:7px;background:var(--green);border-radius:50%;animation:pulse 2s infinite}}
  @keyframes pulse{{0%,100%{{opacity:1;transform:scale(1)}}50%{{opacity:.5;transform:scale(.85)}}}}
  .hero-band{{background:linear-gradient(135deg,#0d1117 0%,#1a2235 100%);padding:48px 24px;position:relative;overflow:hidden}}
  .hero-band::before{{content:'';position:absolute;top:-60px;right:-60px;width:300px;height:300px;background:radial-gradient(circle,rgba(0,87,255,.2) 0%,transparent 70%);pointer-events:none}}
  .hero-inner{{max-width:1280px;margin:0 auto;display:flex;align-items:center;justify-content:space-between;gap:32px}}
  .hero-left h1{{font-family:'Barlow Condensed',sans-serif;font-weight:900;font-size:48px;color:white;line-height:1;letter-spacing:.5px;margin-bottom:8px}}
  .hero-left h1 span{{color:var(--accent)}}
  .hero-left p{{color:rgba(255,255,255,.55);font-size:15px;max-width:440px}}
  .hero-stats{{display:flex;gap:32px}}
  .hero-stat{{text-align:center}}
  .hero-stat-num{{font-family:'Barlow Condensed',sans-serif;font-weight:800;font-size:36px;color:white;line-height:1}}
  .hero-stat-num.green{{color:var(--green)}}
  .hero-stat-label{{font-size:12px;color:rgba(255,255,255,.4);text-transform:uppercase;letter-spacing:1px;margin-top:4px}}
  .main{{max-width:1280px;margin:0 auto;padding:32px 24px;display:grid;grid-template-columns:1fr 320px;gap:28px}}
  .section-header{{display:flex;align-items:center;justify-content:space-between;margin-bottom:16px}}
  .section-title{{font-family:'Barlow Condensed',sans-serif;font-weight:800;font-size:22px;letter-spacing:.5px;display:flex;align-items:center;gap:10px}}
  .section-title .dot{{width:8px;height:8px;background:var(--accent);border-radius:50%}}
  .filter-tabs{{display:flex;gap:6px;margin-bottom:20px;flex-wrap:wrap}}
  .filter-tab{{padding:6px 14px;border-radius:20px;font-size:13px;font-weight:600;cursor:pointer;border:1.5px solid var(--border);background:var(--surface);color:var(--text-muted);transition:all .15s}}
  .filter-tab:hover{{border-color:var(--accent);color:var(--accent)}}
  .filter-tab.active{{background:var(--accent);border-color:var(--accent);color:white}}
  .picks-grid{{display:flex;flex-direction:column;gap:14px}}
  .pick-card{{background:var(--surface);border:1px solid var(--border);border-radius:12px;padding:20px 24px;box-shadow:var(--shadow);transition:all .2s;cursor:pointer;animation:fadeUp .4s ease both}}
  .pick-card:hover{{box-shadow:var(--shadow-hover);transform:translateY(-1px);border-color:#d0d7e3}}
  @keyframes fadeUp{{from{{opacity:0;transform:translateY(12px)}}to{{opacity:1;transform:translateY(0)}}}}
  .pick-top{{display:flex;align-items:center;justify-content:space-between;margin-bottom:14px}}
  .pick-meta{{display:flex;align-items:center;gap:8px}}
  .sport-tag{{font-size:11px;font-weight:700;text-transform:uppercase;letter-spacing:1px;padding:3px 8px;border-radius:4px}}
  .sport-nba{{background:#fde9d3;color:#c2410c}}
  .sport-nfl{{background:#d1fae5;color:#065f46}}
  .sport-mlb{{background:#dbeafe;color:#1e40af}}
  .sport-nhl{{background:#ede9fe;color:#5b21b6}}
  .sport-soccer{{background:#fce7f3;color:#9d174d}}
  .sport-ncaa{{background:#fef3c7;color:#92400e}}
  .sport-wnba{{background:#f0fdf4;color:#166534}}
  .pick-time{{font-size:12px;color:var(--text-muted);font-weight:500}}
  .confidence-badge{{display:flex;align-items:center;gap:6px;font-size:12px;font-weight:700;padding:4px 10px;border-radius:20px}}
  .conf-high{{background:var(--green-light);color:var(--green)}}
  .conf-med{{background:var(--gold-light);color:var(--gold)}}
  .conf-low{{background:#f3f4f6;color:var(--text-muted)}}
  .pick-matchup{{display:flex;align-items:center;justify-content:space-between;margin-bottom:14px}}
  .team{{display:flex;flex-direction:column;gap:2px}}
  .team-name{{font-family:'Barlow Condensed',sans-serif;font-weight:800;font-size:22px;letter-spacing:.3px}}
  .team-record{{font-size:12px;color:var(--text-muted)}}
  .vs-block{{display:flex;flex-direction:column;align-items:center;gap:4px}}
  .vs-text{{font-size:11px;font-weight:700;color:var(--text-muted);text-transform:uppercase;letter-spacing:1px}}
  .vs-line{{font-family:'Barlow Condensed',sans-serif;font-weight:700;font-size:15px;color:var(--accent);background:var(--accent-light);padding:3px 10px;border-radius:6px}}
  .pick-recommendation{{background:var(--bg);border-radius:8px;padding:12px 16px;margin-bottom:14px;display:flex;align-items:center;gap:12px}}
  .pick-type-label{{font-size:11px;font-weight:700;text-transform:uppercase;letter-spacing:1px;color:var(--text-muted);white-space:nowrap}}
  .pick-value{{font-family:'Barlow Condensed',sans-serif;font-weight:800;font-size:20px;color:var(--text)}}
  .pick-odds{{font-size:14px;font-weight:600;color:var(--green);margin-left:auto}}
  .pick-analysis{{font-size:13.5px;color:var(--text-muted);line-height:1.6}}
  .pick-footer{{display:flex;align-items:center;justify-content:space-between;margin-top:14px;padding-top:14px;border-top:1px solid var(--border)}}
  .ai-tag{{font-size:11px;font-weight:600;color:var(--accent)}}
  .pick-actions{{display:flex;gap:8px}}
  .btn-save{{font-size:12px;font-weight:600;color:var(--text-muted);background:none;border:1.5px solid var(--border);padding:5px 12px;border-radius:6px;cursor:pointer;transition:all .15s}}
  .btn-save:hover{{border-color:var(--accent);color:var(--accent)}}
  .btn-bet{{font-size:12px;font-weight:700;color:white;background:var(--accent);border:none;padding:5px 14px;border-radius:6px;cursor:pointer;transition:all .15s}}
  .btn-bet:hover{{background:#0046d4}}
  .sidebar{{display:flex;flex-direction:column;gap:20px}}
  .sidebar-card{{background:var(--surface);border:1px solid var(--border);border-radius:12px;padding:20px;box-shadow:var(--shadow)}}
  .sidebar-title{{font-family:'Barlow Condensed',sans-serif;font-weight:800;font-size:17px;margin-bottom:16px}}
  .streak-row{{display:flex;align-items:center;justify-content:space-between;padding:8px 0;border-bottom:1px solid var(--border);font-size:13px}}
  .streak-row:last-child{{border-bottom:none}}
  .streak-sport{{font-weight:600}}
  .streak-pct{{font-size:12px;color:var(--text-muted);background:var(--bg);padding:2px 8px;border-radius:10px;font-weight:600}}
  .date-bar{{display:flex;align-items:center;gap:6px;margin-bottom:20px;font-size:13px;color:var(--text-muted);font-weight:500}}
  .date-bar strong{{color:var(--text);font-size:14px}}
  .date-dot{{width:4px;height:4px;background:var(--border);border-radius:50%}}
  .no-picks{{text-align:center;padding:60px 20px;color:var(--text-muted);font-size:15px}}
  .disclaimer{{max-width:1280px;margin:0 auto 40px;padding:0 24px;font-size:11px;color:var(--text-muted);text-align:center;line-height:1.6}}
  @media(max-width:900px){{.main{{grid-template-columns:1fr}}.sidebar{{display:none}}.hero-stats{{display:none}}}}
</style>
</head>
<body>
<header>
  <div class="header-inner">
    <a class="logo" href="#">
      <div class="logo-icon">SA</div>
      <span class="logo-text">Sharp<span>AI</span></span>
    </a>
    <nav>
      <a href="#" class="active">Today's Picks</a>
      <a href="#">Parlays</a>
      <a href="#">Records</a>
      <a href="#">Props</a>
    </nav>
    <div class="record-badge">Live · AI Picks Updated Daily</div>
  </div>
</header>

<div class="hero-band">
  <div class="hero-inner">
    <div class="hero-left">
      <h1>AI-POWERED<br><span>DAILY PICKS</span></h1>
      <p>Real odds. Real analysis. Machine learning across every major sport — updated every morning at 9AM ET.</p>
    </div>
    <div class="hero-stats">
      <div class="hero-stat">
        <div class="hero-stat-num green" id="stat-total">{total}</div>
        <div class="hero-stat-label">Today's Picks</div>
      </div>
      <div class="hero-stat">
        <div class="hero-stat-num green" id="stat-high">{high_conf}</div>
        <div class="hero-stat-label">High Confidence</div>
      </div>
      <div class="hero-stat">
        <div class="hero-stat-num">7</div>
        <div class="hero-stat-label">Sports Covered</div>
      </div>
    </div>
  </div>
</div>

<div class="main">
  <div class="picks-col">
    <div class="date-bar">
      <strong>{date_str}</strong>
      <div class="date-dot"></div>
      <span>{total} picks generated</span>
      <div class="date-dot"></div>
      <span>Powered by Claude AI + Live Odds</span>
    </div>
    <div class="section-header">
      <div class="section-title"><div class="dot"></div> Today's Picks</div>
    </div>
    <div class="filter-tabs">
      <div class="filter-tab active" onclick="filterPicks('all',this)">All Sports</div>
      <div class="filter-tab" onclick="filterPicks('nfl',this)">NFL</div>
      <div class="filter-tab" onclick="filterPicks('nba',this)">NBA</div>
      <div class="filter-tab" onclick="filterPicks('mlb',this)">MLB</div>
      <div class="filter-tab" onclick="filterPicks('nhl',this)">NHL</div>
      <div class="filter-tab" onclick="filterPicks('soccer',this)">Soccer</div>
      <div class="filter-tab" onclick="filterPicks('ncaa',this)">College</div>
      <div class="filter-tab" onclick="filterPicks('wnba',this)">Women's</div>
    </div>
    <div class="picks-grid" id="picks-grid"></div>
  </div>
  <div class="sidebar">
    <div class="sidebar-card">
      <div class="sidebar-title">📊 Today by Sport</div>
      <div id="sport-breakdown"></div>
    </div>
    <div class="sidebar-card">
      <div class="sidebar-title">🔥 High Confidence Picks</div>
      <div id="high-conf-list"></div>
    </div>
  </div>
</div>

<div class="disclaimer">
  SharpAI is for entertainment purposes only. We do not encourage illegal gambling. Please gamble responsibly. If you or someone you know has a gambling problem, call 1-800-522-4700.
</div>

<script>
const picks = {picks_json};

function sportClass(s){{
  const m={{'nba':'sport-nba','nfl':'sport-nfl','mlb':'sport-mlb','nhl':'sport-nhl','soccer':'sport-soccer','ncaa':'sport-ncaa','wnba':'sport-wnba'}};
  return m[s]||'sport-nba';
}}
function confClass(c){{return c==='high'?'conf-high':c==='med'?'conf-med':'conf-low';}}
function confLabel(c){{return c==='high'?'🔥 High Confidence':c==='med'?'⚡ Medium':'Low Confidence';}}

function renderPicks(filter){{
  const grid=document.getElementById('picks-grid');
  const list=filter==='all'?picks:picks.filter(p=>p.sport===filter);
  if(!list.length){{grid.innerHTML='<div class="no-picks">No picks available for this sport today.</div>';return;}}
  grid.innerHTML=list.map((p,i)=>`
    <div class="pick-card" style="animation-delay:${{i*0.06}}s">
      <div class="pick-top">
        <div class="pick-meta">
          <span class="sport-tag ${{sportClass(p.sport)}}">${{p.sportLabel}}</span>
          <span class="pick-time">${{p.time}}</span>
        </div>
        <div class="confidence-badge ${{confClass(p.confidence)}}">${{confLabel(p.confidence)}}</div>
      </div>
      <div class="pick-matchup">
        <div class="team"><div class="team-name">${{p.away}}</div></div>
        <div class="vs-block"><span class="vs-text">vs</span><span class="vs-line">${{p.line}}</span></div>
        <div class="team" style="text-align:right"><div class="team-name">${{p.home}}</div></div>
      </div>
      <div class="pick-recommendation">
        <span class="pick-type-label">${{p.pickType}}</span>
        <span class="pick-value">${{p.pickValue}}</span>
        <span class="pick-odds">${{p.odds}}</span>
      </div>
      <div class="pick-analysis">${{p.analysis}}</div>
      <div class="pick-footer">
        <span class="ai-tag">${{p.ai}}</span>
        <div class="pick-actions">
          <button class="btn-save">Save</button>
          <button class="btn-bet">Bet This Pick →</button>
        </div>
      </div>
    </div>
  `).join('');
}}

function filterPicks(sport,el){{
  document.querySelectorAll('.filter-tab').forEach(t=>t.classList.remove('active'));
  el.classList.add('active');
  renderPicks(sport);
}}

// Sport breakdown sidebar
const counts={{}};
picks.forEach(p=>{{counts[p.sportLabel]=(counts[p.sportLabel]||0)+1;}});
document.getElementById('sport-breakdown').innerHTML=
  Object.entries(counts).map(([s,n])=>`
    <div class="streak-row">
      <span class="streak-sport">${{s}}</span>
      <span class="streak-pct">${{n}} pick${{n>1?'s':''}}</span>
    </div>`).join('');

// High confidence sidebar
const high=picks.filter(p=>p.confidence==='high');
document.getElementById('high-conf-list').innerHTML=high.length
  ? high.map(p=>`<div class="streak-row"><span class="streak-sport">${{p.pickValue}}</span><span class="streak-pct">${{p.odds}}</span></div>`).join('')
  : '<div style="font-size:13px;color:var(--text-muted);padding:8px 0">No high confidence picks today.</div>';

renderPicks('all');
</script>
</body>
</html>"""


def main():
    print("🏈 SharpAI — generating today's picks…\n")
    all_picks = []

    for sport_key in SPORTS:
        label, sport_id = SPORT_LABELS[sport_key]
        print(f"  Fetching {label} odds…")
        games = fetch_odds(sport_key)

        if not games:
            print(f"  → No games found for {label}\n")
            continue

        games_text = "\n\n".join(summarise_game(g) for g in games)
        print(f"  → {len(games)} game(s) found, asking Claude…")

        picks = ask_claude(games_text, label)
        # Stamp the sport fields in case Claude omitted them
        for p in picks:
            p.setdefault("sport", sport_id)
            p.setdefault("sportLabel", label)

        print(f"  → {len(picks)} pick(s) generated\n")
        all_picks.extend(picks)

    date_str = datetime.now(timezone.utc).strftime("%A, %B %-d, %Y")
    html = build_html(all_picks, date_str)

    out = Path("index.html")
    out.write_text(html, encoding="utf-8")
    print(f"✅ index.html written — {len(all_picks)} total picks for {date_str}")


if __name__ == "__main__":
    main()
