# Project notes for Claude

Говорим (govorim) — React + Vite Russian practice app. `README.md` is the
human-facing setup guide; this file is orientation for an assistant picking up work.

## Layout

- `src/App.jsx` — the entire app in one large file. Features are added by editing
  shared code paths here, not per-book branches: anything that works for one book
  with word timings should work for every book with word timings.
- `private/books/index.json` — the book catalogue. It lives outside `public/`
  because `/api/catalogue` serves it and strips `restricted: true` entries for
  everyone except `ADMIN_EMAIL`; a manifest published as a static asset would
  list every restricted title and chapter to anyone.
- `public/books/novel/*.fb2` — source texts.
- `private/books/**` — the same shapes, for restricted books. Nothing here is
  published; `/api/media` serves it after an admin session check, and the
  audio for these books lives in a private R2 bucket reached by presigned URL.
  `scripts/gate-books.sh` moves a book from one tree to the other.
- `public/books/audio/<book>/*.json` — per-chapter transcripts **with word-level
  timings**. Schema: `{audio_url, narrator, word_timings, fragments: [{text, begin,
  end, words: [{word, begin, end}]}]}`. Note that punctuation such as a leading `—`
  is stored as its own word token — code that walks `words[]` positionally against
  an external source will drift unless it accounts for that.
- `public/books/exercises/<slug>__NN.json` — per-chapter exercises.
  Schema: `{title, source, cases[], reading[], highlight[]}` where `cases` are
  fill-in-the-blank grammar items, `reading` multiple-choice comprehension, and
  `highlight` "pick the sentence" items. Every item must quote the source text
  exactly — validate generated exercises against the FB2 before saving.
- `scripts/mfa/` — audiobook forced-alignment pipeline.
- `docs/` — process documentation.

## Forced alignment (audiobook → word timings)

**Read `docs/mfa_playbook.md` before touching this.** It records the failure modes
we already hit and the reasoning that resolved them; several are non-obvious and
expensive to rediscover. `docs/mfa_alignment_guide.md` is the command-by-command
runbook.

The headline: MFA's peak memory is driven by the length of the **longest single
utterance**, not by corpus size. Never hand it a whole chapter — split into ~30 s
segments first (`scripts/mfa/split_corpus.py`). Batching chapters does not help and
we burned real time proving that twice.

Also: never run `mfa validate` (trains from scratch, crashes), and never run two
aligners concurrently.

## Auth

The site is public: reading, audio, definitions and exercises all work signed
out. An optional account (email + password) exists so vocabulary, tips and
progress sync across devices, and so the admin account can see restricted
books and the dashboard. There is no third-party auth service — `lib/auth.js`
hashes passwords with scrypt, keeps accounts as JSON in R2 alongside the other
user data, and signs an HttpOnly session cookie. Server env vars:
`AUTH_SECRET` (signs cookies; changing it signs everyone out), `ADMIN_EMAIL`,
`R2_*`, `R2_PRIVATE_BUCKET`.

Client code must never decide access on its own: `isAdmin` in `App.jsx` only
chooses what to render, and every gated route re-checks the session server-side.

## Working agreements

- **Scripts the user runs must be committed into the repo**, and commands should
  reference them as `"$REPO/scripts/..."`. A script that only exists as a chat
  attachment produces `can't open file`.
- The user runs the alignment toolchain in **WSL Ubuntu**, not PowerShell. Windows
  paths become `/mnt/c/...`, and env vars must be re-exported in every new shell.
- Prefer verifying a long-running pipeline with synthesised inputs before committing
  the user to a multi-hour run — see `docs/mfa_playbook.md` §5 for the technique that
  has already caught one silent bug.
- Direction of travel: the alignment pipeline is intended to become a Windows
  executable that works by loading files. Keep new pipeline logic aligner-agnostic
  where practical; `docs/mfa_playbook.md` §7 has the design notes.
