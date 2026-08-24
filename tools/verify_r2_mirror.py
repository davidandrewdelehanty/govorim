#!/usr/bin/env python3
"""Check a local R2 mirror holds every audio file the catalogue references.

Run this BEFORE deleting the R2 bucket. It walks every catalogue entry, opens
each chapter's alignment JSON, reads its audio_url, and confirms the matching
file exists in the mirror. Anything it lists as MISSING exists only on R2 and
will be lost.

    python3 tools/verify_r2_mirror.py ~/govorim-r2-mirror
"""
import json, os, sys, re
from urllib.parse import urlparse, unquote

repo = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
mirror = os.path.expanduser(sys.argv[1] if len(sys.argv) > 1 else "~/govorim-r2-mirror")
if not os.path.isdir(mirror):
    sys.exit("Mirror not found: %s\nRun the rclone copy first." % mirror)

have = set()
for root, _, files in os.walk(mirror):
    rel = os.path.relpath(root, mirror).replace("\\", "/")
    for f in files:
        have.add(f if rel == "." else "%s/%s" % (rel, f))

cat = json.load(open(os.path.join(repo, "private/books/index.json"), encoding="utf-8"))
missing, checked, nojson = [], 0, []

for book in cat:
    ab = book.get("audiobook") or {}
    for ch in (ab.get("chapters") or []):
        if not ch:
            continue                      # deliberate text-only chapter
        # Restricted books keep their alignment JSONs under private/books/,
        # out of the public folder — /api/media serves them to the admin only.
        jp = next((c for c in (os.path.join(repo, "public/books", ch),
                               os.path.join(repo, "private/books", ch))
                   if os.path.isfile(c)), None)
        if not jp:
            nojson.append((book.get("title", ""), ch)); continue
        try:
            data = json.load(open(jp, encoding="utf-8"))
        except Exception:
            nojson.append((book.get("title", ""), ch)); continue
        url = data.get("audio_url") or ""
        if not url:
            continue
        key = unquote(urlparse(url).path).lstrip("/") if "://" in url else url.lstrip("/")
        checked += 1
        if key not in have:
            missing.append((book.get("title", ""), key))

print("audio files referenced : %d" % checked)
print("present in mirror      : %d" % (checked - len(missing)))
print("MISSING                : %d" % len(missing))
if missing:
    print("\nThese exist only on R2 — do NOT delete the bucket yet:")
    for t, k in missing[:40]:
        print("   %-30s %s" % (t[:30], k))
    if len(missing) > 40:
        print("   … and %d more" % (len(missing) - 40))
if nojson:
    print("\nChapter JSONs missing from the repo (%d):" % len(nojson))
    for t, c in nojson[:10]:
        print("   %-30s %s" % (t[:30], c))
sys.exit(1 if missing else 0)
