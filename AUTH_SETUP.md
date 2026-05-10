# Adding Sign-In with Google to your deployed app

This is a one-time setup, ~15 minutes. After it's done, every visit to your
app starts with a sign-in screen, and only people you allow can use it.

---

## Step 1 — Sign up for Clerk (3 minutes)

1. Go to <https://dashboard.clerk.com/sign-up> and create a free account.
   (Free tier covers 10,000 monthly active users — way beyond personal use.)
2. After signing in, click **"Create application"**.
3. **Application name**: `Govorim` (or whatever you like).
4. **Sign-in options**: enable **Google** (toggle on). You can also enable
   **Email** if you want a password fallback.
5. Click **"Create application"**.

You'll land on a page that shows your **API keys**. Keep this tab open.

---

## Step 2 — Lock the app to specific users (recommended, 2 minutes)

This is the difference between "anyone with the URL can sign in" and
"only people on your list can sign in." For a personal/family app you
almost certainly want this.

### Option A — Email allowlist via Clerk's Restrictions (best)

1. In the Clerk dashboard, go to **User & Authentication → Restrictions**.
2. Toggle on **"Allowlist"**.
3. Click **"Add identifier"** and paste your email (and your family's emails).
4. Save.

Now only those emails can sign up. Strangers who try get blocked at the
sign-in screen with no account ever created.

### Option B — Email allowlist via ALLOWED_EMAILS env var (backup)

If the Clerk UI doesn't have Restrictions on the free tier, the
serverless function also enforces an allowlist via the `ALLOWED_EMAILS`
environment variable. Anyone can sign up but only listed emails can
actually use the API.

Format: comma-separated, no spaces. Example:

```
you@gmail.com,partner@gmail.com,kid@school.edu
```

This is configured in Vercel in Step 4 below.

---

## Step 3 — Get your Clerk keys

In the Clerk dashboard, go to **API keys** in the left sidebar. You'll see:

- **Publishable key** — starts with `pk_test_` or `pk_live_`. This goes
  in the frontend; safe to expose.
- **Secret key** — starts with `sk_test_` or `sk_live_`. This stays on
  the server. Never put this anywhere a browser could see it.

Copy both. Keep the page open.

---

## Step 4 — Add the keys to Vercel

1. Go to <https://vercel.com/dashboard> → your project → **Settings →
   Environment Variables**.
2. Add these three new variables:

   | Name | Value | Environments |
   |------|-------|--------------|
   | `VITE_CLERK_PUBLISHABLE_KEY` | your `pk_test_...` key | Production, Preview, Development |
   | `CLERK_SECRET_KEY` | your `sk_test_...` key | Production, Preview, Development |
   | `ALLOWED_EMAILS` *(optional)* | comma-separated emails | Production, Preview, Development |

   The `VITE_` prefix on the publishable key is **mandatory** — Vite only
   exposes env vars to the frontend if they start with `VITE_`.

3. Click **Save** for each.

---

## Step 5 — Push the new code and redeploy

If you haven't already pushed the auth changes to GitHub:

```bash
cd /path/to/govorim-app
git add .
git commit -m "Add Clerk sign-in"
git push
```

Vercel will auto-detect the push and start a new build within seconds.

If Vercel was already on the latest code (you only added env vars):

1. Vercel dashboard → your project → **Deployments** tab.
2. Find the latest deployment → click ⋮ menu → **Redeploy**.
3. Uncheck **"Use existing Build Cache"**.
4. Click **Redeploy**.

Wait 1–2 minutes for the green checkmark.

---

## Step 6 — Test it

1. Open your Vercel URL in a private/incognito window (so you're guaranteed
   to be signed out).
2. You should see the Говорим sign-in screen with a **"Continue with
   Google"** button.
3. Click it. Sign in with your Google account.
4. You should now see the landing/begin screen, then the app.
5. Top-right corner: a small avatar circle. Click it → "Sign out" should
   take you back to the sign-in screen.

If sign-in works but the chat fails with an auth error, the most likely
cause is missing or wrong `CLERK_SECRET_KEY` on the server. Check your
Vercel function logs (Deployments → latest → Functions tab → click an
invocation) for the exact error.

---

## Troubleshooting

**"Setup required" screen on first load** → `VITE_CLERK_PUBLISHABLE_KEY`
isn't set in Vercel, or you didn't redeploy after setting it. Re-check
step 4, then trigger a redeploy (step 5).

**Sign-in works but the chat returns "Not signed in" or "Invalid session"**
→ `CLERK_SECRET_KEY` is missing or the value is wrong on the server.
Make sure you copied the *secret* key (sk_…), not the publishable key,
into the `CLERK_SECRET_KEY` env var.

**"Your account isn't on the allow list for this app"** → expected if
you set `ALLOWED_EMAILS` and signed in with a different email. Either
add the new email to `ALLOWED_EMAILS` in Vercel and redeploy, or sign in
with an allowed account.

**Google sign-in button doesn't appear** → Google provider isn't enabled
in Clerk. Go back to Clerk dashboard → User & Authentication → Social
Connections → enable Google.

**"Could not verify user: ..."** → the serverless function tried to
look up the user via Clerk's API and failed. Almost always a bad
`CLERK_SECRET_KEY`. Regenerate the secret key in Clerk, update Vercel,
redeploy.

---

## Optional polish

- **Custom sign-in URL**: Clerk gives you a default `accounts.YOUR_APP.dev`
  URL for hosted sign-in pages. You can attach your own domain in Clerk's
  **Domains** settings if you want.
- **Disable email/password and force Google-only**: in Clerk dashboard →
  User & Authentication → Email, Phone, Username, turn off **Email
  address** as an identifier. Now Google is the only sign-in option.
- **Profile management page**: Clerk's `<UserButton>` (in the top-right
  corner) opens a built-in profile page where users can change their
  email, add 2FA, etc. — no extra work needed.

---

## Cost expectations after this

- **Clerk**: $0/month (free tier covers up to 10,000 monthly active users)
- **Gemini API**: still $0/month on the free tier
- **Vercel**: still $0–$20/month depending on plan

So adding auth doesn't change your cost picture — it just locks the door.
