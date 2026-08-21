#!/usr/bin/env bash
# Move a book out of the public site and behind the admin gate.
#
# Run from an Ubuntu (WSL) terminal:
#     bash "$REPO/scripts/gate-books.sh" novel/patriot.fb2 novel/moya-strana.fb2
#
# Three things have to move for a gate to be real, and this does the first
# two:
#
#   1. The text (FB2) moves from public/books/ to private/books/. Files under
#      public/ are published as static assets by Vercel; files under private/
#      are not, and are only reachable through /api/media, which checks the
#      session first.
#   2. The alignment JSONs move the same way, for the same reason -- they
#      carry the full text of the book, not just timings.
#   3. The audio has to leave the public R2 bucket. govorim-audio is readable
#      by anyone through its r2.dev domain, so an object left there stays
#      downloadable by anyone who knows the key, no matter what the site
#      shows. This script copies the objects to the private bucket and
#      verifies them; it does NOT delete the public originals -- run it again
#      with --purge once you have confirmed the gated book plays for you and
#      404s for a signed-out browser.
#
# Requirements: rclone with a remote named "r2" (credentials live in the
# rclone config, never in this file), and a private bucket that has NO public
# access enabled. Create it once in the Cloudflare dashboard:
#     R2 → Create bucket → name: govorim-private → Public access: disabled
# then set R2_PRIVATE_BUCKET=govorim-private in the Vercel project.

set -euo pipefail

REPO="${REPO:-$(cd "$(dirname "$0")/.." && pwd)}"
REMOTE="${R2_REMOTE:-r2}"
PUBLIC_BUCKET="${R2_BUCKET:-govorim-audio}"
PRIVATE_BUCKET="${R2_PRIVATE_BUCKET:-govorim-private}"

PURGE=0
BOOKS=()
for arg in "$@"; do
    if [ "$arg" = "--purge" ]; then PURGE=1; else BOOKS+=("$arg"); fi
done

if [ ${#BOOKS[@]} -eq 0 ]; then
    echo "usage: bash scripts/gate-books.sh <novel/foo.fb2> [more…] [--purge]" >&2
    exit 2
fi
if ! command -v rclone >/dev/null 2>&1; then
    echo "rclone is not installed (sudo apt-get install -y rclone)." >&2
    exit 1
fi
if ! rclone listremotes | grep -qx "$REMOTE:"; then
    echo "No rclone remote named '$REMOTE'. Configure it once, then re-run." >&2
    exit 1
fi

MANIFEST="$REPO/private/books/index.json"
[ -f "$MANIFEST" ] || MANIFEST="$REPO/public/books/index.json"
if [ ! -f "$MANIFEST" ]; then
    echo "No book manifest found under $REPO." >&2
    exit 1
fi

# Size of one object, or empty if it isn't there.
#
# NOT `rclone lsf <path> >/dev/null`: that exits 0 with empty output for a key
# that does not exist, so it reports every object as already present. This
# script skipped every copy because of it, and the same test guarded --purge,
# which would have deleted the public originals against an empty private
# bucket. Compare sizes instead of asking a yes/no question.
object_size() {   # object_size <bucket> <key>
    rclone lsjson "$REMOTE:$1/$2" 2>/dev/null | python3 -c \
        'import sys,json
try:
    d = json.load(sys.stdin)
except Exception:
    d = []
print(d[0]["Size"] if d and not d[0].get("IsDir") else "")' 2>/dev/null
}

move_file() {   # move_file <relative path under books/>
    local rel="$1"
    local src="$REPO/public/books/$rel"
    local dst="$REPO/private/books/$rel"
    if [ -e "$dst" ] && [ ! -e "$src" ]; then
        echo "    already private: $rel"
        return
    fi
    if [ ! -e "$src" ]; then
        echo "    missing (skipped): public/books/$rel"
        return
    fi
    mkdir -p "$(dirname "$dst")"
    mv "$src" "$dst"
    echo "    moved: $rel"
}

for book in "${BOOKS[@]}"; do
    echo "── $book"

    # Ask the manifest which alignment JSONs belong to this book, rather than
    # guessing from the filename: the two books gated so far use different
    # layouts (patriot-chNN.json vs moya-strana/NNN.json), and a guess that
    # misses a chapter leaves that chapter's text public.
    mapfile -t CHAPTERS < <(REPO="$REPO" MANIFEST="$MANIFEST" BOOK="$book" node -e '
      const fs = require("fs");
      const list = JSON.parse(fs.readFileSync(process.env.MANIFEST, "utf8"));
      const e = list.find((x) => x.filename === process.env.BOOK);
      if (!e) { console.error("not in manifest: " + process.env.BOOK); process.exit(3); }
      const ch = (e.audiobook && e.audiobook.chapters) || [];
      ch.forEach((c) => console.log(c));
    ')

    echo "  text:"
    move_file "$book"
    echo "  alignment JSON (${#CHAPTERS[@]} chapter(s)):"
    for rel in "${CHAPTERS[@]}"; do move_file "$rel"; done

    # The audio keys come out of the JSONs themselves -- whatever URL the app
    # would have played is exactly what has to stop being public.
    echo "  audio:"
    KEYS=$(REPO="$REPO" node -e '
      const fs = require("fs"), path = require("path");
      const files = process.argv.slice(1);
      const keys = new Set();
      for (const rel of files) {
        for (const base of ["private", "public"]) {
          const p = path.join(process.env.REPO, base, "books", rel);
          if (!fs.existsSync(p)) continue;
          try {
            const j = JSON.parse(fs.readFileSync(p, "utf8"));
            if (j.audio_url) keys.add(new URL(j.audio_url).pathname.replace(/^\/+/, ""));
          } catch (_) {}
          break;
        }
      }
      [...keys].forEach((k) => console.log(k));
    ' "${CHAPTERS[@]}")

    if [ -z "$KEYS" ]; then
        echo "    no audio_url found in this book's JSONs — nothing to move"
        continue
    fi

    while IFS= read -r key; do
        [ -n "$key" ] || continue
        pub_size="$(object_size "$PUBLIC_BUCKET" "$key")"
        priv_size="$(object_size "$PRIVATE_BUCKET" "$key")"
        if [ -n "$priv_size" ] && [ "$priv_size" = "$pub_size" ]; then
            echo "    already private: $key ($priv_size bytes)"
        elif [ -n "$priv_size" ] && [ -z "$pub_size" ]; then
            echo "    already private: $key ($priv_size bytes, public copy gone)"
        else
            rclone copyto "$REMOTE:$PUBLIC_BUCKET/$key" "$REMOTE:$PRIVATE_BUCKET/$key" \
                --s3-no-check-bucket --progress
            priv_size="$(object_size "$PRIVATE_BUCKET" "$key")"
            if [ -n "$priv_size" ] && { [ -z "$pub_size" ] || [ "$priv_size" = "$pub_size" ]; }; then
                echo "    copied: $key ($priv_size bytes)"
            else
                echo "    COPY FAILED: $key (public $pub_size, private ${priv_size:-none})" >&2
                FAILED=1
                continue
            fi
        fi
        if [ "$PURGE" = "1" ]; then
            # Only ever delete the public copy after confirming the private
            # one is really there -- a failed copy plus an eager delete is how
            # an audiobook disappears.
            if [ -z "$(object_size "$PRIVATE_BUCKET" "$key")" ]; then
                echo "    NOT deleting public copy — private copy missing: $key" >&2
            elif [ -z "$(object_size "$PUBLIC_BUCKET" "$key")" ]; then
                # Already purged by an earlier run. rclone deletefile exits
                # non-zero on a missing object, and under `set -e` that ends the
                # whole script -- so a re-run used to abort on the first book
                # that was already done, before touching the ones that weren't.
                echo "    public copy already gone: $key"
            elif rclone deletefile "$REMOTE:$PUBLIC_BUCKET/$key" --s3-no-check-bucket; then
                echo "    removed from public bucket: $key"
            else
                echo "    delete failed, public copy still there: $key" >&2
                FAILED=1
            fi
        fi
    done <<< "$KEYS"
done

echo
if [ "${FAILED:-0}" = "1" ]; then
    echo
    echo "Some objects did not copy. Fix those before going further -- and do" >&2
    echo "NOT run --purge, which deletes the public original." >&2
    exit 1
fi

echo
echo "Done. Next:"
echo "  1. npm run books      # regenerate private/books/index.json"
echo "  2. commit and push, then check on the live site that the gated book is"
echo "     absent signed out, and plays signed in as the admin."
if [ "$PURGE" != "1" ]; then
    echo "  3. re-run with --purge to remove the public audio copies once verified."
fi
