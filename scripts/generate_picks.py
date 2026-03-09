#!/usr/bin/env python3
"""
SharpAI Daily Picks Generator — uses Gemini, no f-string HTML conflicts
"""

import os
import json
import requests
from datetime import datetime, timezone

ODDS_API_KEY   = os.environ["ODDS_API_KEY"]
GEMINI_API_KEY = os.environ["GEMINI_API_KEY"]

SPORTS = [
    ("americanfootball_nfl",  "NFL",     "nfl"),
    ("basketball_nba",         "NBA",     "nba"),
    ("baseball_mlb",           "MLB",     "mlb"),
    ("icehockey_nhl",          "NHL",     "nhl"),
    ("soccer_epl",             "Soccer",  "soccer"),
    ("basketball_ncaab",       "College", "ncaa"),
    ("basketball_wnba",        "WNBA",    "wnba"),
]


def fetch_odds(sport_key):
    url = "https://api.the-odds-api.com/v4/sports/" + sport_key + "/odds"
    params = {
        "apiKey": ODDS_API_KEY,
        "regions": "us",
        "markets": "h2h,spreads,totals",
        "oddsFormat": "american",
        "dateFormat": "iso",
    }
    try:
        r = requests.get(url, params=params, timeout=15)
        if r.status_code == 200:
            return r.json()[:3]
        print("  Warning " + sport_key + ": HTTP " + str(r.status_code))
        return []
    except Exception as e:
        print("  Warning " + sport_key + ": " + str(e))
        return []


def summarise_game(game):
    lines = [
        "Game: " + game.get("away_team", "") + " @ " + game.get("home_team", ""),
        "Time: " + game.get("commence_time", "TBD"),
    ]
    for bm in game.get("bookmakers", [])[:1]:
        for mkt in bm.get("markets", []):
            if mkt["key"] == "h2h":
                outcomes = {o["name"]: o["price"] for o in mkt["outcomes"]}
                lines.append("Moneyline: " + str(outcomes))
            elif mkt["key"] == "spreads":
                for o in mkt["outcomes"]:
                    lines.append("Spread: " + o["name"] + " " + str(o.get("point", "")) + " @ " + str(o["price"]))
            elif mkt["key"] == "totals":
                for o in mkt["outcomes"]:
                    lines.append("Total: " + o["name"] + " " + str(o.get("point", "")) + " @ " + str(o["price"]))
    return "\n".join(lines)


def ask_gemini(games_text, sport_label):
    url = "https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key=" + GEMINI_API_KEY

    prompt = (
        "You are SharpAI, an expert sports betting analyst.\n"
        "Given game odds data, return ONLY a valid JSON array (no markdown, no backticks, no explanation).\n"
        "Each element must have exactly these fields:\n"
        '{"sport":"<sport_id e.g. nba>","sportLabel":"<e.g. NBA>","time":"<e.g. 7:30 PM ET>",'
        '"home":"<home team>","away":"<away team>","line":"<spread or ML or O/U>",'
        '"pickType":"<Spread|Moneyline|Over/Under>","pickValue":"<e.g. Celtics -5.5>",'
        '"odds":"<american odds e.g. -110>","confidence":"<high|med|low>",'
        '"analysis":"<2-3 sentence sharp analysis max 180 chars>",'
        '"ai":"<Model confidence: XX% - based on N signals>"}\n\n'
        "Sport: " + sport_label + "\n\n"
        "Games:\n" + games_text + "\n\n"
        "Return ONLY the JSON array. No markdown. No explanation."
    )

    payload = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {"temperature": 0.3, "maxOutputTokens": 1000}
    }

    try:
        r = requests.post(url, json=payload, timeout=30)
        if r.status_code != 200:
            print("  Gemini error: " + str(r.status_code))
            return []
        data = r.json()
        raw = data["candidates"][0]["content"]["parts"][0]["text"].strip()
        if raw.startswith("```"):
            parts = raw.split("```")
            raw = parts[1]
            if raw.startswith("json"):
                raw = raw[4:]
        return json.loads(raw.strip())
    except Exception as e:
        print("  Gemini parse error for " + sport_label + ": " + str(e))
        return []


def build_html(all_picks, date_str):
    picks_json = json.dumps(all_picks, ensure_ascii=False)
    total = str(len(all_picks))

    # Use plain string concatenation — no f-strings, no curly brace issues
    html = (
        '<!DOCTYPE html>\n'
        '<html lang="en">\n'
        '<head>\n'
        '<meta charset="UTF-8">\n'
        '<meta name="viewport" content="width=device-width, initial-scale=1.0">\n'
        '<title>SharpAI \u2014 Daily Sports Picks & Arbitrage Finder</title>\n'
        '<style>\n'
        ':root {\n'
        '  --bg: #0a0e1a; --surface: #111827; --surface2: #1a2235; --border: #1f2d45;\n'
        '  --text: #f0f4ff; --muted: #5a6a85; --accent: #3b82f6; --accent2: #60a5fa;\n'
        '  --green: #10d98a; --green-dim: rgba(16,217,138,0.12);\n'
        '  --gold: #f59e0b; --gold-dim: rgba(245,158,11,0.12);\n'
        '  --display: -apple-system, "Helvetica Neue", Arial, sans-serif;\n'
        '  --body: -apple-system, "Helvetica Neue", Arial, sans-serif;\n'
        '  --mono: "SF Mono", "Monaco", "Menlo", monospace;\n'
        '}\n'
        '* { margin:0; padding:0; box-sizing:border-box; }\n'
        'body { font-family: var(--body); background: var(--bg); color: var(--text); min-height: 100vh; overflow-x: hidden; }\n'
        'body::before { content:""; position:fixed; inset:0; pointer-events:none; z-index:0;\n'
        '  background-image: linear-gradient(rgba(59,130,246,0.03) 1px, transparent 1px), linear-gradient(90deg, rgba(59,130,246,0.03) 1px, transparent 1px);\n'
        '  background-size: 40px 40px; }\n'
        'header { position:sticky; top:0; z-index:100; background:rgba(10,14,26,0.85); backdrop-filter:blur(20px); border-bottom:1px solid var(--border); }\n'
        '.header-inner { max-width:1300px; margin:0 auto; padding:0 28px; display:flex; align-items:center; justify-content:space-between; height:60px; }\n'
        '.logo { display:flex; align-items:center; gap:10px; text-decoration:none; }\n'
        '.logo-mark { width:34px; height:34px; border-radius:8px; background:linear-gradient(135deg,#3b82f6,#1d4ed8); display:flex; align-items:center; justify-content:center; font-weight:900; font-size:14px; color:white; }\n'
        '.logo-name { font-weight:800; font-size:18px; color:var(--text); }\n'
        '.logo-name em { color:var(--accent2); font-style:normal; }\n'
        'nav { display:flex; gap:2px; }\n'
        'nav button { font-size:13px; font-weight:500; color:var(--muted); background:none; border:none; cursor:pointer; padding:6px 14px; border-radius:6px; transition:all .15s; }\n'
        'nav button:hover { color:var(--text); background:var(--surface); }\n'
        'nav button.active { color:var(--accent2); background:rgba(59,130,246,0.1); font-weight:600; }\n'
        '.live-pill { display:flex; align-items:center; gap:6px; font-size:11px; color:var(--green); background:var(--green-dim); border:1px solid rgba(16,217,138,0.2); padding:5px 12px; border-radius:20px; }\n'
        '.live-dot { width:6px; height:6px; background:var(--green); border-radius:50%; animation:blink 1.5s infinite; }\n'
        '@keyframes blink { 0%,100%{opacity:1} 50%{opacity:0.3} }\n'
        '.hero { position:relative; z-index:1; padding:56px 28px 48px; max-width:1300px; margin:0 auto; display:flex; align-items:flex-end; justify-content:space-between; gap:40px; }\n'
        '.hero-eyebrow { font-size:11px; color:var(--accent2); letter-spacing:2px; text-transform:uppercase; margin-bottom:16px; }\n'
        '.hero-title { font-weight:900; font-size:clamp(36px,5vw,64px); line-height:0.95; letter-spacing:-2px; margin-bottom:16px; }\n'
        '.hero-title .line2 { color:var(--accent2); }\n'
        '.hero-sub { font-size:15px; color:var(--muted); max-width:420px; line-height:1.6; }\n'
        '.hero-stats { display:flex; gap:40px; flex-shrink:0; }\n'
        '.stat { text-align:right; }\n'
        '.stat-num { font-weight:900; font-size:42px; line-height:1; color:var(--green); letter-spacing:-2px; }\n'
        '.stat-num.blue { color:var(--accent2); }\n'
        '.stat-label { font-size:10px; color:var(--muted); text-transform:uppercase; letter-spacing:1.5px; margin-top:4px; }\n'
        '.tab-bar { position:relative; z-index:1; max-width:1300px; margin:0 auto; padding:0 28px; display:flex; border-bottom:1px solid var(--border); margin-bottom:36px; }\n'
        '.tab-btn { font-size:13px; font-weight:600; color:var(--muted); background:none; border:none; border-bottom:2px solid transparent; padding:14px 20px; cursor:pointer; transition:all .15s; display:flex; align-items:center; gap:8px; margin-bottom:-1px; }\n'
        '.tab-btn:hover { color:var(--text); }\n'
        '.tab-btn.active { color:var(--accent2); border-bottom-color:var(--accent2); }\n'
        '.tab-chip { font-size:10px; font-weight:700; padding:2px 7px; border-radius:4px; text-transform:uppercase; letter-spacing:.5px; }\n'
        '.chip-free { background:var(--green-dim); color:var(--green); border:1px solid rgba(16,217,138,0.25); }\n'
        '.chip-lock { background:rgba(59,130,246,0.15); color:var(--accent2); border:1px solid rgba(59,130,246,0.3); }\n'
        '.layout { position:relative; z-index:1; max-width:1300px; margin:0 auto; padding:0 28px 60px; display:grid; grid-template-columns:1fr 300px; gap:24px; }\n'
        '.layout.full { grid-template-columns:1fr; }\n'
        '.section-label { font-size:10px; color:var(--muted); text-transform:uppercase; letter-spacing:2px; margin-bottom:16px; display:flex; align-items:center; gap:10px; }\n'
        '.section-label::after { content:""; flex:1; height:1px; background:var(--border); }\n'
        '.filter-row { display:flex; gap:6px; flex-wrap:wrap; margin-bottom:20px; }\n'
        '.fpill { font-size:11px; font-weight:500; padding:5px 12px; border-radius:20px; cursor:pointer; border:1px solid var(--border); background:none; color:var(--muted); transition:all .15s; text-transform:uppercase; letter-spacing:.5px; }\n'
        '.fpill:hover { border-color:var(--accent); color:var(--accent2); }\n'
        '.fpill.on { background:var(--accent); border-color:var(--accent); color:white; }\n'
        '.picks-list { display:flex; flex-direction:column; gap:12px; }\n'
        '.pick-card { background:var(--surface); border:1px solid var(--border); border-radius:12px; padding:20px 22px; transition:all .2s; animation:up .35s ease both; position:relative; overflow:hidden; }\n'
        '.pick-card::before { content:""; position:absolute; left:0; top:0; bottom:0; width:3px; background:var(--accent); border-radius:3px 0 0 3px; opacity:0; transition:opacity .2s; }\n'
        '.pick-card:hover { border-color:#2d3f5e; transform:translateY(-1px); box-shadow:0 8px 32px rgba(0,0,0,0.4); }\n'
        '.pick-card:hover::before { opacity:1; }\n'
        '.pick-card.hot::before { opacity:1; background:var(--green); }\n'
        '@keyframes up { from{opacity:0;transform:translateY(10px)} to{opacity:1;transform:translateY(0)} }\n'
        '.card-top { display:flex; align-items:center; justify-content:space-between; margin-bottom:14px; }\n'
        '.card-tags { display:flex; align-items:center; gap:8px; }\n'
        '.sport-pill { font-size:10px; font-weight:500; padding:3px 8px; border-radius:4px; text-transform:uppercase; letter-spacing:.5px; }\n'
        '.sp-nba{background:rgba(255,107,53,0.15);color:#ff6b35;border:1px solid rgba(255,107,53,0.25)}\n'
        '.sp-nhl{background:rgba(99,179,237,0.15);color:#63b3ed;border:1px solid rgba(99,179,237,0.25)}\n'
        '.sp-mlb{background:rgba(72,187,120,0.15);color:#48bb78;border:1px solid rgba(72,187,120,0.25)}\n'
        '.sp-ncaa{background:rgba(246,173,85,0.15);color:#f6ad55;border:1px solid rgba(246,173,85,0.25)}\n'
        '.sp-soccer{background:rgba(154,117,234,0.15);color:#9a75ea;border:1px solid rgba(154,117,234,0.25)}\n'
        '.sp-wnba{background:rgba(252,129,178,0.15);color:#fc81b2;border:1px solid rgba(252,129,178,0.25)}\n'
        '.game-time { font-size:11px; color:var(--muted); }\n'
        '.conf-badge { font-size:10px; font-weight:500; padding:3px 10px; border-radius:20px; text-transform:uppercase; letter-spacing:.5px; }\n'
        '.conf-high { background:var(--green-dim); color:var(--green); border:1px solid rgba(16,217,138,0.25); }\n'
        '.conf-med { background:var(--gold-dim); color:var(--gold); border:1px solid rgba(245,158,11,0.25); }\n'
        '.conf-low { background:rgba(90,106,133,0.15); color:var(--muted); border:1px solid var(--border); }\n'
        '.matchup { display:flex; align-items:center; gap:12px; margin-bottom:14px; }\n'
        '.team-name { font-weight:800; font-size:18px; letter-spacing:-0.5px; flex:1; }\n'
        '.team-name.away { text-align:left; }\n'
        '.team-name.home { text-align:right; }\n'
        '.vs-center { display:flex; flex-direction:column; align-items:center; gap:4px; flex-shrink:0; }\n'
        '.vs-txt { font-size:9px; color:var(--muted); text-transform:uppercase; letter-spacing:1px; }\n'
        '.line-badge { font-size:12px; font-weight:500; color:var(--accent2); background:rgba(59,130,246,0.1); border:1px solid rgba(59,130,246,0.2); padding:3px 10px; border-radius:6px; white-space:nowrap; }\n'
        '.pick-row { display:flex; align-items:center; gap:10px; background:var(--surface2); border-radius:8px; padding:10px 14px; margin-bottom:12px; }\n'
        '.pick-type { font-size:10px; color:var(--muted); text-transform:uppercase; letter-spacing:1px; white-space:nowrap; }\n'
        '.pick-val { font-weight:800; font-size:17px; flex:1; }\n'
        '.pick-odds { font-size:13px; color:var(--green); font-weight:500; margin-left:auto; }\n'
        '.analysis { font-size:13px; color:var(--muted); line-height:1.65; margin-bottom:14px; }\n'
        '.card-footer { display:flex; align-items:center; justify-content:space-between; padding-top:12px; border-top:1px solid var(--border); }\n'
        '.ai-signal { font-size:10px; color:var(--accent2); opacity:.7; }\n'
        '.card-actions { display:flex; gap:8px; }\n'
        '.btn-sm { font-size:12px; font-weight:600; padding:5px 12px; border-radius:6px; cursor:pointer; transition:all .15s; border:none; }\n'
        '.btn-ghost { background:none; border:1px solid var(--border); color:var(--muted); }\n'
        '.btn-ghost:hover { border-color:var(--accent); color:var(--accent2); }\n'
        '.btn-primary { background:var(--accent); color:white; }\n'
        '.locked-card { background:var(--surface); border:1px dashed var(--border); border-radius:12px; padding:36px 24px; text-align:center; }\n'
        '.lock-icon { font-size:28px; margin-bottom:12px; opacity:.5; }\n'
        '.lock-title { font-weight:800; font-size:20px; margin-bottom:8px; }\n'
        '.lock-sub { font-size:13px; color:var(--muted); margin-bottom:20px; line-height:1.6; }\n'
        '.btn-unlock { font-weight:700; font-size:13px; background:linear-gradient(135deg,var(--accent),#1d4ed8); color:white; border:none; padding:10px 24px; border-radius:8px; cursor:pointer; }\n'
        '.sidebar { display:flex; flex-direction:column; gap:16px; }\n'
        '.side-card { background:var(--surface); border:1px solid var(--border); border-radius:12px; padding:18px; }\n'
        '.side-title { font-weight:800; font-size:15px; margin-bottom:14px; }\n'
        '.side-row { display:flex; align-items:center; justify-content:space-between; padding:7px 0; border-bottom:1px solid var(--border); font-size:13px; }\n'
        '.side-row:last-child { border-bottom:none; }\n'
        '.side-label { font-weight:500; }\n'
        '.side-val { font-size:11px; color:var(--muted); background:var(--surface2); padding:2px 8px; border-radius:6px; }\n'
        '.promo-card { background:linear-gradient(135deg,#1a2a4a,#0f1e38); border:1px solid rgba(59,130,246,0.3); border-radius:12px; padding:18px; }\n'
        '.promo-title { font-weight:800; font-size:16px; margin-bottom:6px; }\n'
        '.promo-sub { font-size:12px; color:var(--muted); margin-bottom:14px; line-height:1.5; }\n'
        '.btn-promo { width:100%; background:var(--accent); color:white; border:none; padding:10px; border-radius:8px; font-size:13px; font-weight:700; cursor:pointer; }\n'
        '.arb-info { background:rgba(59,130,246,0.08); border:1px solid rgba(59,130,246,0.2); border-radius:10px; padding:14px 18px; margin-bottom:20px; font-size:13px; color:var(--muted); line-height:1.6; }\n'
        '.arb-info strong { color:var(--accent2); }\n'
        '.arb-toolbar { display:flex; align-items:center; gap:12px; margin-bottom:20px; }\n'
        '.btn-refresh { font-weight:700; font-size:12px; background:var(--accent); color:white; border:none; padding:8px 16px; border-radius:6px; cursor:pointer; display:flex; align-items:center; gap:6px; }\n'
        '.btn-refresh.spinning .spin-icon { animation:spin .7s linear infinite; }\n'
        '@keyframes spin { to{transform:rotate(360deg)} }\n'
        '.arb-ts { font-size:11px; color:var(--muted); }\n'
        '.arb-card { background:var(--surface); border:1px solid var(--border); border-radius:12px; padding:20px 22px; margin-bottom:12px; animation:up .35s ease both; transition:all .2s; }\n'
        '.arb-card:hover { border-color:#2d3f5e; transform:translateY(-1px); }\n'
        '.arb-card.premium { border-color:rgba(16,217,138,0.4); }\n'
        '.arb-head { display:flex; align-items:flex-start; justify-content:space-between; margin-bottom:14px; }\n'
        '.arb-game-name { font-weight:800; font-size:18px; margin-bottom:4px; }\n'
        '.arb-meta { font-size:11px; color:var(--muted); }\n'
        '.profit-block { text-align:right; flex-shrink:0; }\n'
        '.profit-num { font-weight:900; font-size:32px; color:var(--green); line-height:1; }\n'
        '.profit-label { font-size:9px; color:var(--muted); text-transform:uppercase; letter-spacing:1px; }\n'
        '.arb-legs { display:grid; grid-template-columns:1fr 1fr; gap:10px; margin-bottom:14px; }\n'
        '.arb-leg { background:var(--surface2); border-radius:8px; padding:12px 14px; }\n'
        '.leg-book { font-size:9px; font-weight:500; text-transform:uppercase; letter-spacing:1px; margin-bottom:6px; padding:2px 7px; border-radius:4px; display:inline-block; }\n'
        '.bk-fd{background:rgba(0,120,255,0.15);color:#60a5fa;border:1px solid rgba(0,120,255,0.25)}\n'
        '.bk-dk{background:rgba(255,165,0,0.15);color:#fbbf24;border:1px solid rgba(255,165,0,0.25)}\n'
        '.bk-fn{background:rgba(255,50,100,0.15);color:#f87171;border:1px solid rgba(255,50,100,0.25)}\n'
        '.bk-cz{background:rgba(50,200,100,0.15);color:#4ade80;border:1px solid rgba(50,200,100,0.25)}\n'
        '.bk-b365{background:rgba(150,100,255,0.15);color:#c084fc;border:1px solid rgba(150,100,255,0.25)}\n'
        '.bk-default{background:rgba(90,106,133,0.15);color:var(--muted);border:1px solid var(--border)}\n'
        '.leg-pick { font-weight:600; font-size:14px; margin-bottom:3px; }\n'
        '.leg-odds { font-size:13px; color:var(--accent2); }\n'
        '.leg-stake { font-size:11px; color:var(--green); margin-top:4px; }\n'
        '.arb-summary { background:var(--green-dim); border:1px solid rgba(16,217,138,0.2); border-radius:8px; padding:12px 16px; display:grid; grid-template-columns:repeat(3,1fr); gap:8px; }\n'
        '.sum-item { text-align:center; }\n'
        '.sum-num { font-weight:800; font-size:18px; color:var(--green); }\n'
        '.sum-label { font-size:9px; color:var(--muted); text-transform:uppercase; letter-spacing:.5px; margin-top:2px; }\n'
        '.arb-empty { text-align:center; padding:60px 20px; }\n'
        '.arb-empty-icon { font-size:40px; margin-bottom:12px; opacity:.4; }\n'
        '.arb-empty-title { font-weight:800; font-size:20px; margin-bottom:8px; color:var(--muted); }\n'
        '.arb-empty-sub { font-size:13px; color:var(--muted); line-height:1.6; }\n'
        '.overlay { display:none; position:fixed; inset:0; background:rgba(0,0,0,.7); backdrop-filter:blur(8px); z-index:1000; align-items:center; justify-content:center; }\n'
        '.overlay.open { display:flex; }\n'
        '.modal { background:var(--surface); border:1px solid var(--border); border-radius:16px; padding:36px; width:100%; max-width:420px; margin:24px; position:relative; }\n'
        '.modal-close { position:absolute; top:16px; right:16px; background:none; border:none; color:var(--muted); font-size:18px; cursor:pointer; }\n'
        '.modal-eyebrow { font-size:10px; color:var(--accent2); text-transform:uppercase; letter-spacing:2px; margin-bottom:8px; }\n'
        '.modal-title { font-weight:900; font-size:28px; margin-bottom:6px; }\n'
        '.modal-sub { font-size:13px; color:var(--muted); line-height:1.6; margin-bottom:20px; }\n'
        '.perks { background:var(--surface2); border-radius:8px; padding:14px 16px; margin-bottom:22px; }\n'
        '.perk { display:flex; align-items:center; gap:8px; font-size:13px; padding:4px 0; }\n'
        '.perk-icon { color:var(--green); font-size:12px; }\n'
        '.field-group { margin-bottom:14px; }\n'
        '.field-label { font-size:10px; color:var(--muted); text-transform:uppercase; letter-spacing:1px; margin-bottom:6px; display:block; }\n'
        '.field-input { width:100%; padding:10px 14px; border-radius:8px; background:var(--surface2); border:1px solid var(--border); color:var(--text); font-size:14px; outline:none; }\n'
        '.field-input:focus { border-color:var(--accent); }\n'
        '.btn-full { width:100%; background:linear-gradient(135deg,var(--accent),#1d4ed8); color:white; border:none; padding:13px; border-radius:8px; font-size:14px; font-weight:700; cursor:pointer; margin-top:4px; }\n'
        '.modal-fine { font-size:11px; color:var(--muted); text-align:center; margin-top:12px; }\n'
        '.success-wrap { text-align:center; padding:12px 0; }\n'
        '.success-emoji { font-size:48px; margin-bottom:12px; }\n'
        '.success-title { font-weight:900; font-size:26px; color:var(--green); margin-bottom:8px; }\n'
        '.success-sub { font-size:13px; color:var(--muted); line-height:1.6; margin-bottom:20px; }\n'
        '.unlock-banner { background:linear-gradient(135deg,#1a2a4a,#0f1e38); border:1px solid rgba(59,130,246,0.3); border-radius:12px; padding:18px 22px; display:flex; align-items:center; justify-content:space-between; gap:16px; margin-bottom:20px; }\n'
        '.ub-text h3 { font-weight:800; font-size:17px; margin-bottom:4px; }\n'
        '.ub-text p { font-size:12px; color:var(--muted); }\n'
        '.btn-ub { background:var(--accent); color:white; border:none; padding:9px 18px; border-radius:7px; font-size:12px; font-weight:700; cursor:pointer; white-space:nowrap; }\n'
        '@media(max-width:860px){.layout{grid-template-columns:1fr}.sidebar{display:none}.hero{flex-direction:column;gap:24px}}\n'
        '</style>\n'
        '</head>\n'
        '<body>\n'
        '<div class="overlay" id="modal">\n'
        '  <div class="modal">\n'
        '    <button class="modal-close" onclick="closeModal()">&#x2715;</button>\n'
        '    <div id="modal-form">\n'
        '      <div class="modal-eyebrow">Free Access</div>\n'
        '      <div class="modal-title">Unlock Premium Picks</div>\n'
        '      <div class="modal-sub">Get every AI pick, every day. Completely free &mdash; no credit card ever.</div>\n'
        '      <div class="perks">\n'
        '        <div class="perk"><span class="perk-icon">&#x2713;</span> All daily picks unlocked instantly</div>\n'
        '        <div class="perk"><span class="perk-icon">&#x2713;</span> High confidence picks highlighted</div>\n'
        '        <div class="perk"><span class="perk-icon">&#x2713;</span> Updated every morning at 9AM ET</div>\n'
        '        <div class="perk"><span class="perk-icon">&#x2713;</span> No credit card, no spam, ever</div>\n'
        '      </div>\n'
        '      <div class="field-group"><label class="field-label">Email Address</label><input class="field-input" type="email" id="inp-email" placeholder="you@example.com"></div>\n'
        '      <div class="field-group"><label class="field-label">Phone Number</label><input class="field-input" type="tel" id="inp-phone" placeholder="+1 (555) 000-0000"></div>\n'
        '      <button class="btn-full" onclick="doSubscribe()">Unlock All Picks &rarr;</button>\n'
        '      <div class="modal-fine">Your info stays private. Unsubscribe anytime.</div>\n'
        '    </div>\n'
        '    <div id="modal-success" style="display:none">\n'
        '      <div class="success-wrap">\n'
        '        <div class="success-emoji">&#x1F389;</div>\n'
        '        <div class="success-title">You\'re In!</div>\n'
        '        <div class="success-sub">All picks are now unlocked. Welcome to SharpAI.</div>\n'
        '        <button class="btn-full" onclick="closeModal()">View All Picks &rarr;</button>\n'
        '      </div>\n'
        '    </div>\n'
        '  </div>\n'
        '</div>\n'
        '<header><div class="header-inner">\n'
        '  <a class="logo" href="#"><div class="logo-mark">SA</div><span class="logo-name">Sharp<em>AI</em></span></a>\n'
        '  <nav>\n'
        '    <button class="active" onclick="goTab(\'picks\')" id="nav-picks">Picks</button>\n'
        '    <button onclick="goTab(\'arb\')" id="nav-arb">Arbitrage</button>\n'
        '  </nav>\n'
        '  <div class="live-pill" id="sub-pill" style="display:none">&#x2713; Premium</div>\n'
        '  <div class="live-pill" id="live-pill"><div class="live-dot"></div>Live</div>\n'
        '</div></header>\n'
        '<div class="hero"><div class="hero-left">\n'
        '  <div class="hero-eyebrow">AI &middot; Sports &middot; Arbitrage</div>\n'
        '  <div class="hero-title">SHARP<br><span class="line2">PICKS DAILY</span></div>\n'
        '  <div class="hero-sub">Real odds. Real analysis. Live arbitrage across FanDuel, DraftKings, Fanatics, Caesars &amp; Bet365.</div>\n'
        '</div><div class="hero-stats">\n'
        '  <div class="stat"><div class="stat-num" id="h-picks">' + total + '</div><div class="stat-label">Today\'s Picks</div></div>\n'
        '  <div class="stat"><div class="stat-num blue" id="h-arb">&mdash;</div><div class="stat-label">Arb Opps</div></div>\n'
        '  <div class="stat"><div class="stat-num blue">5</div><div class="stat-label">Sportsbooks</div></div>\n'
        '</div></div>\n'
        '<div class="tab-bar">\n'
        '  <button class="tab-btn active" id="tab-picks" onclick="goTab(\'picks\')">&#x1F4CA; Today\'s Picks <span class="tab-chip chip-free">2 Free/Day</span></button>\n'
        '  <button class="tab-btn" id="tab-arb" onclick="goTab(\'arb\')">&#x26A1; Arbitrage Finder <span class="tab-chip chip-free">Free</span></button>\n'
        '  <button class="tab-btn" onclick="openModal()">&#x1F3C6; Premium Picks <span class="tab-chip chip-lock">Unlock Free</span></button>\n'
        '</div>\n'
        '<div class="layout" id="sec-picks">\n'
        '  <div>\n'
        '    <div id="unlock-banner-slot"></div>\n'
        '    <div class="section-label">' + date_str + ' &middot; <span id="picks-sub-label">2 of ' + total + ' picks shown</span></div>\n'
        '    <div class="filter-row">\n'
        '      <button class="fpill on" onclick="doFilter(\'all\',this)">All</button>\n'
        '      <button class="fpill" onclick="doFilter(\'nba\',this)">NBA</button>\n'
        '      <button class="fpill" onclick="doFilter(\'nhl\',this)">NHL</button>\n'
        '      <button class="fpill" onclick="doFilter(\'mlb\',this)">MLB</button>\n'
        '      <button class="fpill" onclick="doFilter(\'ncaa\',this)">College</button>\n'
        '      <button class="fpill" onclick="doFilter(\'soccer\',this)">Soccer</button>\n'
        '      <button class="fpill" onclick="doFilter(\'wnba\',this)">WNBA</button>\n'
        '    </div>\n'
        '    <div class="picks-list" id="picks-list"></div>\n'
        '  </div>\n'
        '  <div class="sidebar">\n'
        '    <div class="side-card"><div class="side-title">Today by Sport</div><div id="sport-rows"></div></div>\n'
        '    <div class="side-card"><div class="side-title">&#x1F525; High Confidence</div><div id="hc-rows"></div></div>\n'
        '    <div class="promo-card"><div class="promo-title">Unlock All ' + total + ' Picks</div><div class="promo-sub">Free forever. No credit card.</div><button class="btn-promo" onclick="openModal()">Subscribe Free &rarr;</button></div>\n'
        '  </div>\n'
        '</div>\n'
        '<div class="layout full" id="sec-arb" style="display:none">\n'
        '  <div class="arb-info"><strong>What is arbitrage betting?</strong> When sportsbooks disagree on odds enough that you can bet both sides and guarantee a profit. SharpAI scans 5 major books in real time to find these gaps.</div>\n'
        '  <div class="arb-toolbar">\n'
        '    <button class="btn-refresh" id="refresh-btn" onclick="loadArb()"><span class="spin-icon">&#x21BB;</span> Refresh Odds</button>\n'
        '    <span class="arb-ts" id="arb-ts">Enter your Odds API key below to scan live odds</span>\n'
        '  </div>\n'
        '  <div id="api-key-setup" style="background:var(--surface);border:1px solid var(--border);border-radius:12px;padding:28px;margin-bottom:20px;max-width:560px;">\n'
        '    <div style="font-weight:800;font-size:20px;margin-bottom:8px;">&#x26A1; Connect Live Odds</div>\n'
        '    <div style="font-size:13px;color:var(--muted);margin-bottom:18px;line-height:1.6;">Paste your free Odds API key to start scanning all 5 sportsbooks for live arbitrage opportunities.</div>\n'
        '    <div style="display:flex;gap:10px;">\n'
        '      <input id="api-key-input" class="field-input" type="text" placeholder="Paste your Odds API key here..." style="flex:1">\n'
        '      <button onclick="saveApiKey()" style="background:var(--accent);color:white;border:none;padding:10px 18px;border-radius:8px;font-size:13px;font-weight:700;cursor:pointer;white-space:nowrap;">Save &amp; Scan</button>\n'
        '    </div>\n'
        '    <div style="font-size:11px;color:var(--muted);margin-top:10px;">Get a free key at <strong style="color:var(--accent2)">the-odds-api.com</strong></div>\n'
        '  </div>\n'
        '  <div id="arb-grid"></div>\n'
        '</div>\n'
        '<div style="text-align:center;padding:0 28px 40px;font-size:11px;color:var(--muted);max-width:1300px;margin:0 auto;position:relative;z-index:1">\n'
        '  SharpAI is for entertainment purposes only. Please gamble responsibly. Helpline: 1-800-522-4700.\n'
        '</div>\n'
        '<script>\n'
        'var subscriber=localStorage.getItem("sa_sub")==="1";\n'
        'var oddsKey=localStorage.getItem("sa_odds_key")||"";\n'
        'var activeFilter="all";\n'
        'var PICKS=' + picks_json + ';\n'
        '\n'
        'function sportClass(s){return {nba:"sp-nba",nhl:"sp-nhl",mlb:"sp-mlb",ncaa:"sp-ncaa",soccer:"sp-soccer",wnba:"sp-wnba"}[s]||"sp-nba";}\n'
        'function confClass(c){return c==="high"?"conf-high":c==="med"?"conf-med":"conf-low";}\n'
        'function confLabel(c){return c==="high"?"&#x1F525; High":"&#x26A1; Med";}\n'
        '\n'
        'function pickHTML(p,i){\n'
        '  return "<div class=\\"pick-card "+(p.confidence==="high"?"hot":"")+"\\" style=\\"animation-delay:"+(i*.06)+"s\\">"\n'
        '    +"<div class=\\"card-top\\"><div class=\\"card-tags\\"><span class=\\"sport-pill "+sportClass(p.sport)+"\\">"+p.sportLabel+"</span>"\n'
        '    +"<span class=\\"game-time\\">"+p.time+"</span></div>"\n'
        '    +"<span class=\\"conf-badge "+confClass(p.confidence)+"\\">"+confLabel(p.confidence)+"</span></div>"\n'
        '    +"<div class=\\"matchup\\"><div class=\\"team-name away\\">"+p.away+"</div>"\n'
        '    +"<div class=\\"vs-center\\"><span class=\\"vs-txt\\">@</span><span class=\\"line-badge\\">"+p.line+"</span></div>"\n'
        '    +"<div class=\\"team-name home\\">"+p.home+"</div></div>"\n'
        '    +"<div class=\\"pick-row\\"><span class=\\"pick-type\\">"+p.pickType+"</span><span class=\\"pick-val\\">"+p.pickValue+"</span><span class=\\"pick-odds\\">"+p.odds+"</span></div>"\n'
        '    +"<div class=\\"analysis\\">"+p.analysis+"</div>"\n'
        '    +"<div class=\\"card-footer\\"><span class=\\"ai-signal\\">"+p.ai+"</span>"\n'
        '    +"<div class=\\"card-actions\\"><button class=\\"btn-sm btn-ghost\\">Save</button><button class=\\"btn-sm btn-primary\\">Bet &rarr;</button></div></div></div>";\n'
        '}\n'
        '\n'
        'function lockedHTML(){\n'
        '  return "<div class=\\"locked-card\\"><div class=\\"lock-icon\\">&#x1F512;</div>"\n'
        '    +"<div class=\\"lock-title\\">More Picks Locked</div>"\n'
        '    +"<div class=\\"lock-sub\\">Subscribe free to unlock all "+PICKS.length+" picks today.</div>"\n'
        '    +"<button class=\\"btn-unlock\\" onclick=\\"openModal()\\">Unlock Free &rarr;</button></div>";\n'
        '}\n'
        '\n'
        'function renderPicks(filter){\n'
        '  activeFilter=filter;\n'
        '  var list=document.getElementById("picks-list");\n'
        '  var filtered=filter==="all"?PICKS:PICKS.filter(function(p){return p.sport===filter;});\n'
        '  if(!filtered.length){list.innerHTML="<div style=\\"text-align:center;padding:40px;color:var(--muted)\\">No picks for this sport today.</div>";return;}\n'
        '  if(subscriber){list.innerHTML=filtered.map(pickHTML).join("");}\n'
        '  else{var free=filtered.slice(0,2),rest=filtered.slice(2);list.innerHTML=free.map(pickHTML).join("")+(rest.length?lockedHTML():"");}\n'
        '}\n'
        '\n'
        'function doFilter(f,el){document.querySelectorAll(".fpill").forEach(function(b){b.classList.remove("on");});el.classList.add("on");renderPicks(f);}\n'
        '\n'
        'function buildSidebar(){\n'
        '  var counts={};\n'
        '  PICKS.forEach(function(p){counts[p.sportLabel]=(counts[p.sportLabel]||0)+1;});\n'
        '  document.getElementById("sport-rows").innerHTML=Object.entries(counts).map(function(e){return "<div class=\\"side-row\\"><span class=\\"side-label\\">"+e[0]+"</span><span class=\\"side-val\\">"+e[1]+" pick"+(e[1]>1?"s":"")+"</span></div>";}).join("");\n'
        '  var hc=PICKS.filter(function(p){return p.confidence==="high";});\n'
        '  document.getElementById("hc-rows").innerHTML=hc.map(function(p){return "<div class=\\"side-row\\"><span class=\\"side-label\\">"+p.pickValue+"</span><span class=\\"side-val\\">"+p.odds+"</span></div>";}).join("");\n'
        '}\n'
        '\n'
        'function updateBanner(){\n'
        '  var slot=document.getElementById("unlock-banner-slot"),lbl=document.getElementById("picks-sub-label");\n'
        '  if(subscriber){slot.innerHTML="";lbl.textContent="All "+PICKS.length+" picks unlocked";}\n'
        '  else{slot.innerHTML="<div class=\\"unlock-banner\\"><div class=\\"ub-text\\"><h3>&#x1F512; "+(PICKS.length-2)+" More Picks Available</h3><p>Subscribe free &mdash; no credit card needed.</p></div><button class=\\"btn-ub\\" onclick=\\"openModal()\\">Unlock Free &rarr;</button></div>";lbl.textContent="2 of "+PICKS.length+" picks shown";}\n'
        '}\n'
        '\n'
        'function goTab(t){\n'
        '  document.getElementById("sec-picks").style.display=t==="picks"?"grid":"none";\n'
        '  document.getElementById("sec-arb").style.display=t==="arb"?"block":"none";\n'
        '  document.getElementById("tab-picks").classList.toggle("active",t==="picks");\n'
        '  document.getElementById("tab-arb").classList.toggle("active",t==="arb");\n'
        '  document.getElementById("nav-picks").classList.toggle("active",t==="picks");\n'
        '  document.getElementById("nav-arb").classList.toggle("active",t==="arb");\n'
        '  if(t==="arb"&&oddsKey)loadArb();\n'
        '}\n'
        '\n'
        'function openModal(){document.getElementById("modal").classList.add("open");}\n'
        'function closeModal(){document.getElementById("modal").classList.remove("open");}\n'
        'document.getElementById("modal").addEventListener("click",function(e){if(e.target===this)closeModal();});\n'
        '\n'
        'function doSubscribe(){\n'
        '  var email=document.getElementById("inp-email").value.trim(),phone=document.getElementById("inp-phone").value.trim();\n'
        '  if(!email||!email.includes("@")){alert("Please enter a valid email.");return;}\n'
        '  if(!phone){alert("Please enter your phone number.");return;}\n'
        '  localStorage.setItem("sa_sub","1");localStorage.setItem("sa_email",email);localStorage.setItem("sa_phone",phone);\n'
        '  subscriber=true;\n'
        '  document.getElementById("modal-form").style.display="none";\n'
        '  document.getElementById("modal-success").style.display="block";\n'
        '  updateBanner();renderPicks(activeFilter);\n'
        '  document.getElementById("sub-pill").style.display="flex";\n'
        '  document.getElementById("live-pill").style.display="none";\n'
        '}\n'
        '\n'
        'function saveApiKey(){\n'
        '  var k=document.getElementById("api-key-input").value.trim();\n'
        '  if(!k){alert("Please paste your Odds API key.");return;}\n'
        '  localStorage.setItem("sa_odds_key",k);oddsKey=k;\n'
        '  document.getElementById("api-key-setup").style.display="none";loadArb();\n'
        '}\n'
        '\n'
        'var BOOKS=["fanduel","draftkings","fanatics","caesars","betmgm"];\n'
        'var BOOK_NAMES={fanduel:"FanDuel",draftkings:"DraftKings",fanatics:"Fanatics",caesars:"Caesars",betmgm:"Bet365"};\n'
        'var BOOK_CSS={fanduel:"bk-fd",draftkings:"bk-dk",fanatics:"bk-fn",caesars:"bk-cz",betmgm:"bk-b365"};\n'
        'function toDecimal(a){a=parseFloat(a);return a>0?(a/100)+1:(100/Math.abs(a))+1;}\n'
        '\n'
        'function findArbs(games){\n'
        '  var opps=[];\n'
        '  for(var i=0;i<games.length;i++){\n'
        '    var g=games[i],best={};\n'
        '    for(var j=0;j<g.bookmakers.length;j++){\n'
        '      var bm=g.bookmakers[j];\n'
        '      if(BOOKS.indexOf(bm.key)<0)continue;\n'
        '      var mkt=null;\n'
        '      for(var m=0;m<bm.markets.length;m++){if(bm.markets[m].key==="h2h"){mkt=bm.markets[m];break;}}\n'
        '      if(!mkt)continue;\n'
        '      for(var k=0;k<mkt.outcomes.length;k++){\n'
        '        var o=mkt.outcomes[k];\n'
        '        if(!best[o.name]||toDecimal(o.price)>toDecimal(best[o.name].odds))best[o.name]={book:bm.key,odds:o.price};\n'
        '      }\n'
        '    }\n'
        '    var teams=Object.keys(best);\n'
        '    if(teams.length<2)continue;\n'
        '    var impl=teams.reduce(function(s,t){return s+(1/toDecimal(best[t].odds));},0);\n'
        '    if(impl<1.0){\n'
        '      var pct=((1/impl)-1)*100;\n'
        '      var legs=teams.map(function(t){return {team:t,book:best[t].book,odds:best[t].odds,stake:((1/toDecimal(best[t].odds))/impl*100).toFixed(2)};});\n'
        '      opps.push({game:g.away_team+" @ "+g.home_team,sport:(g.sport_key||"").split("_").pop().toUpperCase(),\n'
        '        time:new Date(g.commence_time).toLocaleTimeString("en-US",{hour:"numeric",minute:"2-digit",timeZoneName:"short"}),\n'
        '        pct:pct.toFixed(2),impl:(impl*100).toFixed(1),profit:(100/impl-100).toFixed(2),legs:legs});\n'
        '    }\n'
        '  }\n'
        '  return opps.sort(function(a,b){return b.pct-a.pct;});\n'
        '}\n'
        '\n'
        'async function loadArb(){\n'
        '  if(!oddsKey)return;\n'
        '  var grid=document.getElementById("arb-grid"),ts=document.getElementById("arb-ts"),btn=document.getElementById("refresh-btn");\n'
        '  btn.classList.add("spinning");\n'
        '  grid.innerHTML="<div style=\\"text-align:center;padding:40px;color:var(--muted)\\">&#x1F50D; Scanning live odds...</div>";\n'
        '  ts.textContent="Fetching...";\n'
        '  var sports=["americanfootball_nfl","basketball_nba","baseball_mlb","icehockey_nhl","soccer_epl","basketball_ncaab"];\n'
        '  var all=[];\n'
        '  for(var i=0;i<sports.length;i++){\n'
        '    try{\n'
        '      var sp=sports[i];\n'
        '      var url="https://api.the-odds-api.com/v4/sports/"+sp+"/odds?apiKey="+oddsKey+"&regions=us&markets=h2h&oddsFormat=american&bookmakers="+BOOKS.join(",");\n'
        '      var r=await fetch(url);\n'
        '      if(r.ok){var d=await r.json();all=all.concat(d.map(function(g){var ng=Object.assign({},g);ng.sport_key=sp;return ng;}));}\n'
        '    }catch(e){console.warn(sports[i],e);}\n'
        '  }\n'
        '  btn.classList.remove("spinning");\n'
        '  var arbs=findArbs(all);\n'
        '  document.getElementById("h-arb").textContent=arbs.length||"0";\n'
        '  ts.textContent="Last updated "+new Date().toLocaleTimeString()+" \xb7 "+all.length+" games scanned";\n'
        '  if(!arbs.length){\n'
        '    grid.innerHTML="<div class=\\"arb-empty\\"><div class=\\"arb-empty-icon\\">&#x1F50D;</div><div class=\\"arb-empty-title\\">No Arbs Right Now</div><div class=\\"arb-empty-sub\\">"+all.length+" games scanned across 5 books.<br>Arb windows close fast &mdash; try refreshing.</div></div>";\n'
        '    return;\n'
        '  }\n'
        '  var html="";\n'
        '  for(var i=0;i<arbs.length;i++){\n'
        '    var a=arbs[i];\n'
        '    var legsHtml="";\n'
        '    for(var j=0;j<a.legs.length;j++){\n'
        '      var l=a.legs[j];\n'
        '      legsHtml+="<div class=\\"arb-leg\\"><div><span class=\\"leg-book "+(BOOK_CSS[l.book]||"bk-default")+"\\">"+(BOOK_NAMES[l.book]||l.book)+"</span></div>"\n'
        '        +"<div class=\\"leg-pick\\">"+l.team+"</div>"\n'
        '        +"<div class=\\"leg-odds\\">"+(l.odds>0?"+":"")+l.odds+"</div>"\n'
        '        +"<div class=\\"leg-stake\\">Stake $"+l.stake+"</div></div>";\n'
        '    }\n'
        '    html+="<div class=\\"arb-card "+(parseFloat(a.pct)>=2?"premium":"")+"\\" style=\\"animation-delay:"+(i*.06)+"s\\">"\n'
        '      +"<div class=\\"arb-head\\"><div><div class=\\"arb-game-name\\">"+a.game+"</div><div class=\\"arb-meta\\">"+a.sport+" &middot; "+a.time+"</div></div>"\n'
        '      +"<div class=\\"profit-block\\"><div class=\\"profit-num\\">+"+a.pct+"%</div><div class=\\"profit-label\\">Guaranteed</div></div></div>"\n'
        '      +"<div class=\\"arb-legs\\">"+legsHtml+"</div>"\n'
        '      +"<div class=\\"arb-summary\\">"\n'
        '      +"<div class=\\"sum-item\\"><div class=\\"sum-num\\">$100</div><div class=\\"sum-label\\">Stake</div></div>"\n'
        '      +"<div class=\\"sum-item\\"><div class=\\"sum-num\\">$"+a.profit+"</div><div class=\\"sum-label\\">Profit</div></div>"\n'
        '      +"<div class=\\"sum-item\\"><div class=\\"sum-num\\">"+a.impl+"%</div><div class=\\"sum-label\\">Implied</div></div>"\n'
        '      +"</div></div>";\n'
        '  }\n'
        '  grid.innerHTML=html;\n'
        '}\n'
        '\n'
        'if(subscriber){document.getElementById("sub-pill").style.display="flex";document.getElementById("live-pill").style.display="none";}\n'
        'if(oddsKey){document.getElementById("api-key-setup").style.display="none";}\n'
        'buildSidebar();updateBanner();renderPicks("all");\n'
        '</script>\n'
        '</body>\n'
        '</html>\n'
    )
    return html


def main():
    print("SharpAI — generating today's picks with Gemini...\n")
    all_picks = []

    for sport_key, label, sport_id in SPORTS:
        print("  Fetching " + label + " odds...")
        games = fetch_odds(sport_key)
        if not games:
            print("  -> No games for " + label + "\n")
            continue
        games_text = "\n\n".join(summarise_game(g) for g in games)
        print("  -> " + str(len(games)) + " game(s), asking Gemini...")
        picks = ask_gemini(games_text, label)
        for p in picks:
            p.setdefault("sport", sport_id)
            p.setdefault("sportLabel", label)
        print("  -> " + str(len(picks)) + " pick(s)\n")
        all_picks.extend(picks)

    date_str = datetime.now(timezone.utc).strftime("%B %-d, %Y")
    html = build_html(all_picks, date_str)

    with open("index.html", "w", encoding="utf-8") as f:
        f.write(html)

    print("Done! index.html written with " + str(len(all_picks)) + " picks for " + date_str)


if __name__ == "__main__":
    main()
