# SharpAI — Daily AI Sports Picks

Automated daily sports picks powered by **Claude AI** + **The Odds API**, deployed free on **Netlify** via **GitHub Actions**.

---

## How It Works

Every morning at 9 AM ET, GitHub Actions:
1. Fetches live odds from The Odds API
2. Sends the data to Claude for analysis
3. Generates a fresh `index.html` with today's picks
4. Commits it back to GitHub
5. Netlify detects the change and republishes your site automatically

---

## Setup Guide (15 minutes)

### Step 1 — Get your API Keys

**Odds API (free)**
1. Go to https://the-odds-api.com
2. Click "Get API Key" — sign up for free
3. Copy your API key from the dashboard

**Anthropic API**
1. Go to https://console.anthropic.com
2. Sign in or create an account
3. Go to API Keys → Create Key
4. Copy the key (you only see it once)

---

### Step 2 — Create a GitHub Repository

1. Go to https://github.com and sign in (or create a free account)
2. Click the **+** button → **New repository**
3. Name it `sharpai-picks`
4. Set it to **Public**
5. Click **Create repository**

---

### Step 3 — Upload the Files

Upload these files to your new repository (drag and drop them on the GitHub page):
```
sharpai-picks/
├── .github/
│   └── workflows/
│       └── daily_picks.yml
├── scripts/
│   └── generate_picks.py
├── requirements.txt
└── index.html          ← the current site file
```

To upload:
1. On your GitHub repo page, click **Add file → Upload files**
2. Drag all the files in — make sure the folder structure is maintained
3. Click **Commit changes**

---

### Step 4 — Add Your API Keys as Secrets

1. In your GitHub repo, go to **Settings → Secrets and variables → Actions**
2. Click **New repository secret** and add:

| Secret Name | Value |
|---|---|
| `ODDS_API_KEY` | Your Odds API key |
| `ANTHROPIC_API_KEY` | Your Anthropic API key |

---

### Step 5 — Connect Netlify to GitHub

1. Go to https://netlify.com and log in
2. Click **Add new site → Import an existing project**
3. Choose **GitHub**
4. Select your `sharpai-picks` repository
5. Build settings:
   - Build command: *(leave blank)*
   - Publish directory: `/` (root)
6. Click **Deploy site**
7. Go to **Site settings → Change site name** and set it to `sharpai-picks`

Netlify will now automatically redeploy every time GitHub pushes a new `index.html`.

---

### Step 6 — Test It

1. Go to your GitHub repo
2. Click **Actions** tab
3. Click **Generate Daily Picks**
4. Click **Run workflow → Run workflow**
5. Watch it run — should take about 60 seconds
6. Check your Netlify site — picks should be updated!

---

## Your Site

Once set up, your site will be live at:
**https://sharpai-picks.netlify.app**

And picks will update automatically every day at 9 AM ET — no action needed from you.

---

## Costs

| Service | Cost |
|---|---|
| GitHub | Free |
| GitHub Actions | Free (2,000 mins/month — you'll use ~2/day) |
| Netlify | Free |
| The Odds API | Free (500 requests/month — you'll use ~7/day) |
| Anthropic API | ~$0.01–0.05 per day |

**Total monthly cost: approximately $1–2/month** (Anthropic API only)

---

## Troubleshooting

**Workflow fails with "No module named anthropic"**
→ Make sure `requirements.txt` is in the root of your repo

**No picks generated**
→ Check that your API keys are saved correctly in GitHub Secrets

**Netlify not updating**
→ Go to Netlify → Deploys and check if a new deploy triggered after the GitHub push

**Odds API returns empty**
→ Some sports are out of season. The script handles this gracefully and skips them.
