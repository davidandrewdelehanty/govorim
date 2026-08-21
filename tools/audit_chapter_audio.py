#!/usr/bin/env python3
"""
audit_chapter_audio.py — check that every catalogue book really is one audio
file per chapter.

Now that read-along highlighting is gone, a book is "done" when each chapter
has its own recording. Several books used to stream one long MP3 and stop at a
timestamp instead (`stopAtEnd`), and the only way to tell the two apart from
outside is to look at what each chapter JSON actually points at.

Reports, per book:
  SHARED    two or more chapters pointing at the SAME audio_url — not cut yet
  MISSING   a chapter JSON that isn't on disk, or has no audio_url
  STOPAT    a chapter still carrying stopAtEnd (the old shared-file marker)
  HEAVY     a chapter JSON still carrying word_timings (harmless, just fat)
  OK        one distinct recording per chapter

Reads only the head of each JSON, so it costs a few seconds over thousands of
chapters rather than minutes.

    python3 tools/audit_chapter_audio.py --repo . > audit.txt
"""

import argparse
import json
import re
from pathlib import Path

HEAD = 4096
URL_RE = re.compile(r'"audio_url"\s*:\s*"([^"]*)"')
STOP_RE = re.compile(r'"stopAtEnd"\s*:\s*(true|[0-9.]+)')
WT_RE = re.compile(r'"word_timings"\s*:\s*\[\s*\{')


def probe(path: Path):
    """(audio_url, stop_at_end, has_word_timings) from the file's head."""
    try:
        head = path.open("r", encoding="utf-8").read(HEAD)
    except FileNotFoundError:
        return None, False, False
    m = URL_RE.search(head)
    return (m.group(1) if m else ""), bool(STOP_RE.search(head)), bool(WT_RE.search(head))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo", default=".")
    ap.add_argument("--index", default=None,
                    help="catalogue path (default: private/books/index.json, "
                         "falling back to public/books/index.json)")
    a = ap.parse_args()
    repo = Path(a.repo)
    index = Path(a.index) if a.index else None
    if index is None:
        for cand in ("private/books/index.json", "public/books/index.json"):
            if (repo / cand).exists():
                index = repo / cand
                break
    books = json.loads(index.read_text(encoding="utf-8"))

    print(f"catalogue: {index}")
    print(f"{len(books)} entries\n")
    problems = []
    for b in books:
        ab = b.get("audiobook") or {}
        chapters = ab.get("chapters") or []
        title = b.get("title") or b.get("filename")
        if not chapters:
            print(f"  --   {title}: no audiobook")
            continue
        urls, missing, stopat, heavy = [], [], 0, 0
        for rel in chapters:
            # A null entry is a chapter with no recording at all — the
            # catalogue's way of saying "text only" (or an editing slip).
            if not rel:
                missing.append("(null entry)")
                continue
            # Chapter paths are relative to the books dir the catalogue lives in.
            p = index.parent / rel
            if not p.exists():
                alt = repo / "public" / "books" / rel
                p = alt if alt.exists() else p
            url, stop, wt = probe(p)
            if url is None or not url:
                missing.append(rel)
            else:
                urls.append(url)
            stopat += 1 if stop else 0
            heavy += 1 if wt else 0
        dupes = len(urls) - len(set(urls))
        flags = []
        if dupes:
            flags.append(f"SHARED×{dupes}")
        if missing:
            flags.append(f"MISSING×{len(missing)}")
        if stopat:
            flags.append(f"STOPAT×{stopat}")
        if heavy:
            flags.append(f"HEAVY×{heavy}")
        status = " ".join(flags) if flags else "OK"
        print(f"  {'!!' if flags and flags[0].startswith(('SHARED','MISSING')) else '  '}   "
              f"{title}: {len(chapters)} chapter(s), {len(set(urls))} distinct "
              f"recording(s) — {status}")
        if flags:
            problems.append((title, status, missing[:4], urls))

    print("\n" + "=" * 70)
    if not problems:
        print("Every catalogue book is one recording per chapter.")
        return 0
    print("Needs attention:\n")
    for title, status, missing, urls in problems:
        print(f"  {title} — {status}")
        if missing:
            print(f"      missing: {', '.join(missing)}"
                  + (" …" if len(missing) == 4 else ""))
        if "SHARED" in status:
            seen, dupe_urls = set(), []
            for u in urls:
                if u in seen and u not in dupe_urls:
                    dupe_urls.append(u)
                seen.add(u)
            for u in dupe_urls[:3]:
                print(f"      shared: {u.rsplit('/', 1)[-1]} ×{urls.count(u)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
