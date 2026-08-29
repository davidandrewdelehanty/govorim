#!/usr/bin/env python3
"""Check every chapter video in the catalogue for embeddability.

A YouTube video can be public and still refuse to be embedded, in which case
the reader shows an empty player and the only way to watch is on YouTube. That
failure is invisible from the catalogue: the id is valid, the link works, and
nothing looks wrong until someone opens the page.

YouTube's oEmbed endpoint answers the question directly — 200 with JSON for a
video that allows embedding, 401 for one that does not, 404 for one that is
gone. The response also carries the real title, which catches the other quiet
failure: an id that embeds perfectly well but points at the wrong work.

Run from the repo root:

    python3 tools/check_embeds.py              # every video
    python3 tools/check_embeds.py --only shinel
"""
import argparse
import io
import json
import os
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
INDEX = os.path.join(ROOT, "private", "books", "index.json")
OEMBED = "https://www.youtube.com/oembed?url=%s&format=json"
UA = "govorim.dev embed check"


def check(vid):
    """(status, title, author) — status is ok / no-embed / missing / error."""
    url = OEMBED % urllib.parse.quote(
        "https://www.youtube.com/watch?v=" + vid, safe="")
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    try:
        with urllib.request.urlopen(req, timeout=20) as r:
            d = json.load(r)
            return "ok", d.get("title", ""), d.get("author_name", "")
    except urllib.error.HTTPError as e:
        if e.code == 401:
            return "no-embed", "", ""
        if e.code in (403, 404):
            return "missing", "", ""
        return "error", "HTTP %d" % e.code, ""
    except Exception as e:
        return "error", str(e)[:40], ""


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--only", help="check one book by slug")
    ap.add_argument("--delay", type=float, default=0.4,
                    help="seconds between requests (default 0.4)")
    a = ap.parse_args()

    books = json.load(io.open(INDEX, encoding="utf-8"))
    rows = []
    for b in books:
        vids = b.get("videos") or {}
        if not vids:
            continue
        if a.only and b.get("slug") != a.only:
            continue
        for k in sorted(vids, key=lambda x: int(x) if x.isdigit() else 0):
            v = vids[k]
            vid = (v.get("youtube") if isinstance(v, dict) else v) or ""
            head = (v.get("heading") if isinstance(v, dict) else "") or ""
            if vid:
                rows.append((b.get("slug"), b.get("title") or "", k, head, vid))

    if not rows:
        print("no videos to check")
        return 0

    print("checking %d video(s)\n" % len(rows))
    bad = []
    seen = {}
    for slug, title, ch, head, vid in rows:
        if vid in seen:
            status, yt_title, author = seen[vid]
        else:
            status, yt_title, author = check(vid)
            seen[vid] = (status, yt_title, author)
            time.sleep(a.delay)
        mark = {"ok": "  ok      ", "no-embed": "  NO EMBED",
                "missing": "  MISSING ", "error": "  error   "}[status]
        print("%s %-26s ch%-3s %-12s %s" % (mark, slug[:26], ch, vid, yt_title[:44]))
        if status != "ok":
            bad.append((slug, ch, vid, status))

    print()
    if bad:
        print("%d need attention:" % len(bad))
        for slug, ch, vid, status in bad:
            print("   %-26s chapter %-3s %-12s %s" % (slug, ch, vid, status))
        print()
        print("no-embed  the video refuses embedding; the reader shows an empty")
        print("          player. Replace it, or drop it and leave the chapter")
        print("          with its audio bar instead.")
        print("missing   the video is private, deleted or region-blocked.")
    else:
        print("every video embeds cleanly.")

    print()
    print("Check the titles above against the works they are attached to — a")
    print("video can embed perfectly and still be the wrong reading.")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
