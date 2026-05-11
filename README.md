# Говорим — Russian Practice Web App

A self-contained React + Vite web app for Russian language practice with EPUB
reading, conversational tutoring, click-to-define vocabulary, and rotating
comprehension questions. Powered by Google Gemini 2.5 Flash on the free tier.

## What's in this folder

```
govorim-app/
├── src/
│   ├── App.jsx              ← the entire React app (~1800 lines, single file)
│   └── main.jsx             ← entry point that mounts <App />
├── api/
│   └── chat.js              ← serverless function that proxies to Gemini
├── public/
│   ├── favicon.svg          ← icon shown in browser tab and home screen
│   └── manifest.webmanifest ← PWA manifest (lets users install as app)
├── index.html
├── package.json
├── vite.config.js
├── vercel.json
├── .gitignore
└── README.md (you are here)
```

---

## Step 1 — Get a free Gemini API key (2 minutes)

1. Open <https://aistudio.google.com/apikey> in your browser.
2. Sign in with any Google account.
3. Click **"Create API key"**. Pick a project (or let it create one).
4. Copy the key — looks like `AIzaSy...`. **Save it somewhere safe.**

You don't need a credit card. The free tier gives you 1,500 requests per day
on Gemini 2.5 Flash, which is plenty for 20–50 active users.

---

## Step 2 — Put this code on GitHub (5 minutes)

If you already have GitHub set up, skip to step 2c.

### 2a. Create a GitHub account (if you don't have one)

Go to <https://github.com/join> and follow the prompts. Free.

### 2b. Install Git on Windows

1. Download <https://git-scm.com/download/win> and run the installer.
2. Accept all defaults during installation.
3. Open **Git Bash** (installed automatically) for the next steps.

### 2c. Create a new GitHub repository

1. Go to <https://github.com/new>.
2. Repository name: `govorim` (or whatever you like).
3. Set to **Private** if you don't want strangers to see the code (optional).
4. Don't add a README, .gitignore, or license — we already have these.
5. Click **"Create repository"**. GitHub will show you commands like
   `git remote add origin https://github.com/YOUR_USERNAME/govorim.git`.
   Keep that page open.

### 2d. Push this folder to GitHub

Open Git Bash, navigate to this folder, and run:

```bash
cd /path/to/govorim-app
git init
git add .
git commit -m "Initial commit"
git branch -M main
git remote add origin https://github.com/YOUR_USERNAME/govorim.git
git push -u origin main
```

Replace `YOUR_USERNAME` with your actual GitHub username. You'll be asked
to authenticate the first time — GitHub now uses a personal access token,
which Git Bash will guide you through if needed.

---

## Step 3 — Deploy to Vercel (5 minutes)

1. Go to <https://vercel.com/signup> and sign up using your GitHub account.
   (This makes the next step seamless.)
2. Once signed in, click **"Add New..." → "Project"**.
3. Find your `govorim` repo in the list and click **"Import"**.
4. On the configuration screen:
   - **Framework Preset**: should auto-detect as **Vite**. If not, select it.
   - **Root Directory**: leave as the default (root).
   - **Build Command**, **Output Directory**: leave as defaults — `vercel.json`
     handles them.
5. **Before clicking Deploy**, expand the **"Environment Variables"** section
   and add:
   - **Name**: `GEMINI_API_KEY`
   - **Value**: paste your Gemini API key from Step 1
   - Click **"Add"**.
6. Click **"Deploy"**. Wait 1–2 minutes for the build to finish.
7. You'll get a URL like `https://govorim-yourname.vercel.app`. Open it.
   You should see the start screen of the app.

If the build fails, scroll up in the build log to find the first red error
line. Common causes: missing environment variable, typo in `vercel.json`,
or a syntax error from a manual edit.

---

## Step 4 — Set spending caps (3 minutes)

Even though Gemini's free tier is genuinely free, set guardrails so you can
never get a surprise bill if you accidentally upgrade or hit a paid feature.

### 4a. Vercel spending cap

1. Go to your Vercel dashboard → **Settings → Billing → Spend Management**.
2. Set the budget to **$5/month**.
3. Enable **"Pause projects at 100%"**.
4. Add notification thresholds at 50% and 80%.

### 4b. Google AI Studio quota cap

The free tier is auto-capped — you literally cannot exceed it without
adding billing — so there's nothing to set unless you choose to enable
billing later. If you do, set a budget alert in the
[Google Cloud Console](https://console.cloud.google.com/billing).

---

## Step 5 — (Optional) Add your phone home-screen icon

### iPhone

1. Open your Vercel URL in **Safari** (not Chrome on iOS — it works
   differently for PWAs).
2. Tap the **Share** button.
3. Scroll and tap **"Add to Home Screen"**.
4. Name it "Говорим" and tap Add.

You'll now have an app icon that opens the practice tool full-screen, no
browser chrome, like a real app.

### Windows desktop

1. Open the Vercel URL in **Microsoft Edge**.
2. Click the **install icon** (looks like a small monitor with a download
   arrow) in the address bar.
3. Click **Install**.

You'll get a desktop shortcut and Start menu entry.

---

## Step 6 — (Optional) Custom domain

If you want a nicer URL like `govorim.app` instead of
`govorim-yourname.vercel.app`:

1. Buy a domain on Namecheap, Cloudflare Registrar, or Google Domains
   ($10–15/year).
2. In Vercel: **Project → Settings → Domains → Add Domain**.
3. Vercel gives you DNS records to set at your registrar — copy them
   into your registrar's DNS settings.
4. Wait a few minutes for DNS to propagate. Vercel will issue a free
   SSL certificate automatically.

---

## Updating the app later

Any change you push to your GitHub `main` branch deploys automatically
to Vercel within a minute or two. Workflow:

```bash
# edit files locally
git add .
git commit -m "Describe what you changed"
git push
```

Vercel sees the push, builds, deploys. You'll get an email when it's done.

To roll back: in the Vercel dashboard, go to **Deployments**, find a
working version, click the menu, and select **"Promote to Production"**.

---

## Local development (optional)

If you want to run the app on your own computer before pushing changes:

```bash
# Install dependencies (one time)
npm install

# Start the dev server
npm run dev
```

Note: the `/api/chat` serverless function only works on Vercel, not in
local Vite. To test the API locally too, install Vercel CLI:

```bash
npm i -g vercel
vercel dev
```

This runs both the frontend and the serverless function together,
matching production behavior. You'll need to set the `GEMINI_API_KEY`
in a `.env.local` file at the project root:

```
GEMINI_API_KEY=AIzaSy...your-key-here...
```

The `.gitignore` already excludes `.env*` files so your key won't
accidentally land in GitHub.

---

## Architecture notes

- **Storage**: vocab list, grammar tips, EPUB cache, bookmarks, and
  per-chapter question history all live in the user's browser
  `localStorage`. No server-side database. Each device is independent.
- **API**: the frontend calls `/api/chat`, which translates Anthropic-shaped
  request payloads into Gemini's format. This means the prompts (which were
  originally written for Claude) work without modification, and you can
  swap to a different LLM later by editing only `api/chat.js`.
- **Rate limiting**: 15 requests per IP per minute, 200 per IP per day,
  enforced in-memory in `api/chat.js`. Best-effort; resets on cold start.
  If you need durable rate limiting later, swap for Upstash Redis.
- **TTS**: uses the browser's built-in `speechSynthesis` API. On Windows,
  Microsoft Edge exposes high-quality "Online (Natural)" neural voices.
  On iPhone, download Enhanced/Premium Russian voices via Settings →
  Accessibility → Spoken Content → Voices → Russian.

---

## Troubleshooting

**"Server error: GEMINI_API_KEY not configured"** — you forgot to add the
environment variable in Vercel. Go to Project → Settings → Environment
Variables, add it, then redeploy (Deployments tab → menu on latest →
"Redeploy").

**"Too many requests this minute"** — you (or someone) hit the rate limit.
Wait 60 seconds and try again. If this happens often legitimately, raise
`RATE_MAX_PER_WINDOW` in `api/chat.js`.

**"Daily limit reached for your IP"** — likewise; raise `RATE_DAILY_PER_IP`
or wait until tomorrow.

**App loads but nothing happens when I click Start** — open browser DevTools
(F12) and check the Console tab for errors. Most likely your Gemini key is
invalid or has hit its 1,500/day free-tier quota.

**TTS sounds robotic** — open the app in Edge (Windows) or Safari (iOS) and
look for voices marked "neural ★" (Edge) or download Enhanced voices in
iOS Settings.

---

## Cost expectations

For a small group (1–10 occasional users):
- **Vercel**: $0/month (Hobby tier, but verify your usage stays personal/non-commercial)
- **Gemini API**: $0/month (free tier covers 1,500 requests/day)
- **Domain**: $10–15/year if you want custom one

For viral-popular usage (100+ daily active users):
- **Vercel**: probably still $0–$20/month
- **Gemini API**: would need to enable billing; expect $5–30/month at
  Gemini Flash's $0.15/M input tokens pricing

You'll know you're approaching free-tier limits when the API starts returning
429 errors. At that point, decide whether to upgrade Gemini billing, add
Cloudflare Turnstile to block bots, or implement BYOK.
