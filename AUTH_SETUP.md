# Sign-In, Approval, and Email Notifications

This walkthrough covers three things that work together:

1. **Sign-in with Google** via Clerk
2. **Manual approval** — every new signup waits for you to approve them
3. **Approval emails** — users automatically receive an email when you approve them

Total setup time: ~20 minutes.

---

## Step 1 — Sign up for Clerk (3 minutes)

1. Go to <https://dashboard.clerk.com/sign-up> — free account, no credit card.
2. Create an application named `Govorim` (or whatever).
3. On signup, when asked for sign-in methods, **enable Google** (toggle on).
4. Complete signup.

You'll land on the Clerk dashboard for your new app.

---

## Step 2 — Enable Google sign-in (if not done in Step 1)

If your sign-in screen shows email but not the "Continue with Google" button:

1. In Clerk dashboard → left sidebar → **User & Authentication → SSO Connections**
   (older dashboards may call it "Social Connections").
2. Find **Google** in the list. Click it.
3. Toggle it **On**.
4. Clerk offers two modes:
   - **"Use Clerk's shared credentials"** — works instantly, fine for personal/testing use.
   - **"Use custom credentials"** — for production, requires creating a Google
     OAuth client in [Google Cloud Console](https://console.cloud.google.com/apis/credentials).
     For a personal app, skip this for now.
5. Save.

Refresh your app — the Google button should now appear above the email form.

---

## Step 3 — Get your Clerk API keys (1 minute)

In the Clerk dashboard → **API keys** (left sidebar). You'll see:

- **Publishable key** — `pk_test_...` or `pk_live_...` — frontend, safe to expose.
- **Secret key** — `sk_test_...` or `sk_live_...` — backend, never expose.

Copy both. Keep this tab open.

---

## Step 4 — Sign up for Resend (3 minutes) — for the approval emails

[Resend](https://resend.com) sends the email notifications when you approve users.
Free tier: 100 emails/day, 3,000/month — way beyond personal use.

1. Go to <https://resend.com/signup> and create an account.
2. After signing in, go to **API Keys** → click **"Create API Key"**.
3. Name it `Govorim`, scope: **Sending access**, domain: All.
4. Copy the key — starts with `re_...`.

You can also leave the "From" address as the default `onboarding@resend.dev`
(that's what's used if you don't configure your own domain). For sending
to your own personal email this is fine. If you want emails to come from
your own domain (`approve@yoursite.com`), you'd verify the domain in
Resend's Domains tab — optional.

---

## Step 5 — Add all five environment variables to Vercel

1. <https://vercel.com/dashboard> → your project → **Settings → Environment Variables**.
2. Add these (Production + Preview + Development for all):

   | Name | Value | Notes |
   |------|-------|-------|
   | `VITE_CLERK_PUBLISHABLE_KEY` | `pk_test_...` from Clerk | Frontend |
   | `VITE_ADMIN_EMAIL` | your email (the one you'll sign in with) | Frontend — controls who sees the admin panel |
   | `CLERK_SECRET_KEY` | `sk_test_...` from Clerk | Backend |
   | `ADMIN_EMAIL` | same email as above | Backend — auto-approves your account |
   | `RESEND_API_KEY` | `re_...` from Resend | Backend |
   | `APP_URL` *(optional)* | your Vercel URL like `https://govorim.vercel.app` | Used in approval emails |
   | `RESEND_FROM_EMAIL` *(optional)* | `Govorim <hi@yourdomain.com>` if you have a verified domain | Backend |
   | `GEMINI_API_KEY` | `AIzaSy...` (already set from before) | Backend |

   The `VITE_` prefix on the first two is **mandatory** — Vite only exposes
   env vars to the browser if they start with `VITE_`.

   Note: Both `VITE_ADMIN_EMAIL` (frontend) and `ADMIN_EMAIL` (backend) need
   to be set to the same value. The frontend uses it to show/hide the admin
   button; the backend uses it to enforce admin-only API access. They're
   redundant by design — frontend env vars are visible in browser source,
   so the backend has its own copy as the source of truth.

3. Save each.

---

## Step 6 — Push the code and redeploy

```bash
cd /path/to/govorim-app
git add .
git commit -m "Add approval workflow with email notifications"
git push
```

Vercel auto-redeploys. Wait for the green checkmark.

If you only added env vars without code changes: Vercel dashboard → Deployments
→ latest → ⋮ → Redeploy → uncheck "Use existing Build Cache" → Redeploy.

---

## Step 7 — Test the full flow

### As you (the admin):

1. Open your app URL in an incognito window.
2. Click **Continue with Google**, sign in with the email matching `ADMIN_EMAIL`.
3. You should see the regular app — admins are auto-approved, you don't have to approve yourself.
4. Top-right of the header: a small **👥 Users** button. That's the admin panel — only you see it.

### As a new user (test with a different Google account or browser profile):

1. Open your app URL.
2. Click **Continue with Google**, sign in with a *different* Google account.
3. You should see a **"Waiting for approval"** screen with the user's email shown.
4. The user can sign out from this screen but cannot access the app yet.

### Approving them:

1. Switch back to your admin account.
2. Click **👥 Users** in the header — modal opens with all signed-up users.
3. Find the pending user (yellow "Pending" pill).
4. Click **Approve**.
5. You should see a confirmation. The user list refreshes.
6. The user's email inbox should now have a "You're approved on Говорим" email
   with a link back to the app.
7. The user refreshes the app → they're in.

### Revoking access:

In the admin panel, click **Revoke** on an approved user. Their next API call
returns 403 PENDING_APPROVAL and they're back to the waiting screen.

---

## Troubleshooting

### "Google sign-in button doesn't appear"

Google isn't enabled in Clerk. Go to Clerk dashboard → **User & Authentication
→ SSO Connections** → enable Google.

### "Setup required" screen on first load

`VITE_CLERK_PUBLISHABLE_KEY` is missing or wasn't applied. Re-check Vercel env
vars and redeploy.

### Sign-in works but the chat says "Not signed in"

`CLERK_SECRET_KEY` is missing on the server side. Add it and redeploy.

### "Your account is pending approval" but you ARE the admin

Your `ADMIN_EMAIL` env var doesn't exactly match the email you're signed in
with. Check both:
- The `ADMIN_EMAIL` value in Vercel (case-insensitive, but spelling matters)
- The email shown on your "pending" screen

If they don't match, fix the env var and redeploy.

### Admin panel "👥 Users" button doesn't appear

Frontend `VITE_ADMIN_EMAIL` is missing or doesn't match your sign-in email.
Make sure both `ADMIN_EMAIL` AND `VITE_ADMIN_EMAIL` are set to the same value.

### Approving a user works but the email doesn't arrive

Check the admin panel — there's an error banner that shows if Resend failed.
Common causes:
- `RESEND_API_KEY` is missing or wrong
- The user's email is on a domain Resend has flagged (rare; check Resend dashboard for delivery logs)
- Your daily Resend quota (100/day on free tier) is exhausted (very unlikely for personal use)

Even if email fails, the user IS approved — they just won't get notified.
You can text/message them manually that they're approved.

---

## What's stored where

- **Clerk** stores: user accounts (email, name, profile image, password hash if applicable),
  approval status (in user's public metadata), Google OAuth tokens.
- **Vercel** stores: nothing user-related; just runs the code.
- **Resend** stores: outbound email delivery logs (subject, recipient, sent timestamp).
- **Your app's localStorage** stores: vocab list, EPUB cache, bookmarks, question history,
  landing-screen-seen flag — all per device, per user implicitly via browser.

---

## Costs after this

- Clerk: $0/month (free tier: 10,000 monthly active users)
- Resend: $0/month (free tier: 3,000 emails/month, 100/day)
- Gemini: $0/month (free tier: 1,500 requests/day)
- Vercel: $0/month (Hobby tier for personal use)

If your Russian app suddenly takes off and exceeds free tiers on any of these,
each provider has clear $5–$20/month entry points. None of them have surprise
billing — they all rate-limit to $0 by default until you opt into paid tiers.
