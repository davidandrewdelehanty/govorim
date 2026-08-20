# Accounts, admin, and gated books

The site is **public**. Reading, audio, word definitions, exercises and the
grammar curriculum all work with no account at all. Signing in does exactly
two things:

- your vocabulary, tips and progress sync across devices (signed out, they
  stay in the browser you saved them in);
- the one account matching `ADMIN_EMAIL` also sees the restricted books and
  the admin dashboard.

There is no third-party auth service. Accounts live in the same Cloudflare R2
bucket as the rest of the user data, passwords are hashed with scrypt from
Node's standard library, and the session is a signed HttpOnly cookie.

## Environment variables (Vercel → Project → Settings → Environment Variables)

| Variable | Required | What it does |
| --- | --- | --- |
| `AUTH_SECRET` | yes | Signs session cookies. Any long random string; changing it signs everybody out. Generate one with `openssl rand -base64 48`. |
| `ADMIN_EMAIL` | yes | The account that gets admin rights and the restricted books. Currently `david.andrew.delehanty@gmail.com`. |
| `R2_ENDPOINT`, `R2_ACCESS_KEY_ID`, `R2_SECRET_ACCESS_KEY` | yes | Already set — accounts and user data are stored here. |
| `R2_BUCKET` | no | Defaults to `govorim-audio`. |
| `R2_PRIVATE_BUCKET` | for gated books | Bucket with **public access disabled**, holding restricted books' audio. Defaults to `govorim-private`. |
| `GEMINI_API_KEY` | yes | Definitions and questions. |
| `RESEND_API_KEY`, `RESEND_FROM_EMAIL` | no | Only used by admin emails now. |

Variables no longer used, safe to delete: `CLERK_SECRET_KEY`,
`VITE_CLERK_PUBLISHABLE_KEY`, `CLERK_WEBHOOK_SECRET`, `VITE_ADMIN_EMAIL`,
`ALLOWED_EMAILS`.

## Creating your admin account

The admin account is not seeded — it is just the account whose email matches
`ADMIN_EMAIL`. After deploying:

1. Open the site, click **Sign in**, then **Create one**.
2. Sign up with `david.andrew.delehanty@gmail.com` and a password of at least
   10 characters.
3. The 👥 Users and 📤 Upload buttons appear once you are signed in as that
   address.

Anyone else can sign up too — the approval flow is gone, since an account no
longer unlocks anything except syncing your own vocabulary.

## Bringing old vocabulary across

Data saved under the old login is stored under that login's user id, which is
not the id derived from your email now. Once you have signed up again:

```bash
curl -X POST https://<your-site>/api/admin/import-userdata \
  -H "Content-Type: application/json" \
  --cookie "gv_session=<your session cookie>" \
  -d '{"from":"user_2xxxxxxxxxxxxxxxxxxxx","toEmail":"david.andrew.delehanty@gmail.com"}'
```

`from` is the old Clerk user id (the prefix under `userdata/` in R2 — list
that prefix in the Cloudflare dashboard if you don't remember it). Existing
files at the destination are never overwritten unless you add
`"overwrite": true`.

## Restricted books

`Патриот` and `Моя любимая страна` are admin-only. Three things make that
real, and all three are needed — skip one and the book is still downloadable
by anyone who knows where to look:

1. **The manifest is not public.** `private/books/index.json` is served by
   `/api/catalogue`, which drops `restricted: true` entries for everyone but
   the admin. A signed-out visitor cannot see the title, the author, or that
   the book exists.
2. **The text is not published.** The FB2 and the alignment JSONs live in
   `private/books/`, outside the static build, and only `/api/media` will
   serve them — after checking the session cookie.
3. **The audio is in a private bucket.** `govorim-audio` is public through its
   `r2.dev` domain, so anything left there stays fetchable. Restricted audio
   is copied to `govorim-private` (public access disabled) and reached through
   a presigned URL that expires in 15 minutes.

To gate another book, move it with the script and rebuild the manifest:

```bash
bash "$REPO/scripts/gate-books.sh" novel/some-book.fb2
npm run books
```

The script copies the audio to the private bucket but leaves the public copy
in place. Once you have confirmed the book plays for you and 404s in a
signed-out browser, run it again with `--purge` to delete the public copies.

To un-gate a book, move its files back from `private/books/` to
`public/books/` and run `npm run books`; the `restricted` flag is derived from
which tree the file is in, so nothing else needs editing.

## What happened to the old setup

- **Clerk** is gone: no provider in `main.jsx`, no JWTs, no webhook, and the
  three Clerk packages are out of `package.json`.
- **The approval flow** is gone. New accounts work immediately.
- **The forum** is gone, along with its Clerk-metadata storage.
- **`/api/chat` is public**, protected by a per-IP rate limit rather than a
  login: 10/minute and 100/day signed out, 15/minute and 200/day signed in.
- **The admin dashboard** stayed, now listing accounts (email, when they
  joined, when they last signed in) instead of approvals.
