#!/usr/bin/env python3
"""Find a YouTube reading for books that have none, and fetch its transcript.

The two steps of the audio pipeline that need the network, in one command.
Everything after them — placing the chapters in the recording, and building
the paragraph jump points from the transcript — reads only files on disk and
runs anywhere:

    # here, because these need yt-dlp and a way out to YouTube
    python3 tools/youtube_for.py --author Булгаков
    python3 tools/youtube_for.py --slug master-i-margarita --slug sobache-serdtse

    # anywhere, afterwards
    python3 tools/place_picks.py <from> <to>     # writes the videos map
    python3 tools/sync_all.py                    # writes the jump points

What it does, per book: hand the title, author and word count to
hunt_audio.py, which screens YouTube for a complete, embeddable, natively
Russian-captioned reading; then pull that video's Russian auto-captions into
tools/vtt/, where place_picks.py and sync_all.py look for them.

Nothing is written to the catalogue here. A recording is only attached once
place_picks.py has found every chapter's opening line in the transcript, in
order — the transcript decides, not this script and not the uploader's title.

Books that already carry a `videos` map are skipped unless --force: re-running
is safe and cheap, since both the hunt and the captions are cached.
"""
import argparse
import io
import json
import os
import subprocess
import sys

MANIFEST = "private/books/index.json"
HUNT_OUT = "tools/hunt-results.json"
VTT_DIR = "tools/vtt"


def load_manifest(path):
    data = json.load(io.open(path, encoding="utf-8"))
    return data["books"] if isinstance(data, dict) and "books" in data else data


def author_short(entry):
    """«Булгаков М.А.» → «Булгаков». The search wants the name as a person
    says it, not as a catalogue prints it."""
    a = str(entry.get("author") or "").strip()
    return a.split()[0].rstrip(",") if a else ""


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--author", action="append", default=[],
                    help="match on the catalogue's author field, e.g. Булгаков")
    ap.add_argument("--slug", action="append", default=[])
    ap.add_argument("--force", action="store_true",
                    help="include books that already have a videos map")
    ap.add_argument("--min-words", type=int, default=0,
                    help="skip anything shorter; a sixty-word lyric has no audiobook, "
                         "and the search spends a minute per book finding that out")
    ap.add_argument("--max-books", type=int, default=0,
                    help="stop after this many, to take a long shelf in sittings")
    ap.add_argument("--dry-run", action="store_true",
                    help="list what would be hunted and stop")
    ap.add_argument("--allow-uncaptioned", action="store_true",
                    help="accept a recording with no Russian transcript: it gets chapter "
                         "audio and no jump points, and nothing checks it against the text")
    ap.add_argument("--retry-misses", action="store_true",
                    help="ask again about the books the hunt already answered with nothing")
    ap.add_argument("--manifest", default=MANIFEST)
    ap.add_argument("--list-out", default="tools/hunt-wanted.json")
    ap.add_argument("--no-captions", action="store_true",
                    help="run the search but do not pull transcripts")
    a = ap.parse_args()
    if not a.author and not a.slug:
        ap.error("give --author or --slug")

    books = load_manifest(a.manifest)
    wanted = []
    for b in books:
        if not isinstance(b, dict) or not b.get("filename"):
            continue
        hit = (any(s in str(b.get("author") or "") for s in a.author) or
               b.get("slug") in a.slug)
        if not hit:
            continue
        if b.get("videos") and not a.force:
            print("have video   %s" % (b.get("title") or b.get("slug")))
            continue
        if not b.get("words"):
            print("no wordcount %s — skipped, the search needs it to tell a "
                  "reading from a lecture" % (b.get("title") or b.get("slug")))
            continue
        if a.min_words and b["words"] < a.min_words:
            continue
        if a.max_books and len(wanted) >= a.max_books:
            break
        wanted.append({"file": b["filename"], "title": b.get("title") or "",
                       "author_short": author_short(b), "words": b["words"]})

    if not wanted:
        print("\nnothing to hunt.")
        return 0

    io.open(a.list_out, "w", encoding="utf-8", newline="\n").write(
        json.dumps(wanted, ensure_ascii=False, indent=1) + "\n")
    print("\n%d book(s) → %s\n" % (len(wanted), a.list_out))
    if a.dry_run:
        return 0

    # The hunt appends to tools/hunt-results.json and skips any book already
    # answered there, so this is resumable and re-running costs nothing. That
    # also means a book it once found nothing for is never asked about again —
    # so when the rules change, the old "nothing" has to be cleared out first.
    if a.retry_misses and os.path.exists(HUNT_OUT):
        done = json.load(io.open(HUNT_OUT, encoding="utf-8"))
        ours = {w["file"] for w in wanted}
        keep = [r for r in done if r.get("pick") or r.get("file") not in ours]
        if len(keep) != len(done):
            io.open(HUNT_OUT, "w", encoding="utf-8", newline="\n").write(
                json.dumps(keep, ensure_ascii=False, indent=1) + "\n")
            print("asking again about %d book(s) the hunt had given up on\n" % (len(done) - len(keep)))

    cmd = [sys.executable, "tools/hunt_audio.py", a.list_out]
    if a.allow_uncaptioned:
        cmd.append("--allow-uncaptioned")
    rc = subprocess.call(cmd)
    if rc != 0:
        print("hunt_audio.py exited %d" % rc)
        return rc

    results = json.load(io.open(HUNT_OUT, encoding="utf-8"))
    ours = {w["file"] for w in wanted}
    picks = [(r["file"], r["pick"]["id"]) for r in results
             if r.get("pick") and r.get("file") in ours]
    misses = [r["file"] for r in results if r.get("file") in ours and not r.get("pick")]

    # A pick with no Russian transcript has nothing to download; tools/
    # place_uncaptioned.py is what places those.
    if not a.no_captions:
        os.makedirs(VTT_DIR, exist_ok=True)
        for f, vid in picks:
            dest = os.path.join(VTT_DIR, vid + ".ru.vtt")
            if os.path.exists(dest):
                print("captions cached  %s  %s" % (vid, f))
                continue
            print("captions         %s  %s" % (vid, f))
            subprocess.call(["yt-dlp", "--write-auto-sub", "--sub-lang", "ru",
                             "--skip-download", "--quiet",
                             "-o", os.path.join(VTT_DIR, "%(id)s"),
                             "https://youtu.be/" + vid])
            if not os.path.exists(dest):
                print("   no ru transcript came down — this one cannot be synced")

    print("\n%d picked, %d with nothing usable" % (len(picks), len(misses)))
    for f in misses:
        print("   no recording: %s" % f)
    bare = [f for f, vid in picks if not os.path.exists(os.path.join(VTT_DIR, vid + ".ru.vtt"))]
    if bare:
        print("\n%d pick(s) came with no transcript — place those with:" % len(bare))
        print("  python3 tools/place_uncaptioned.py")
    if picks:
        # place_picks.py slices the results that HAVE a pick, not all of them,
        # so the range is worked out against that list rather than guessed.
        picked_all = [r for r in results if r.get("pick")]
        idx = [i for i, r in enumerate(picked_all) if r.get("file") in ours]
        lo, hi = min(idx), max(idx) + 1
        extra = hi - lo - len(idx)
        print("\nnext — neither of these needs the network:")
        print("  python3 tools/place_picks.py %d %d" % (lo, hi))
        if extra:
            print("     (that range also covers %d earlier book(s); check what it reports)" % extra)
        print("  python3 tools/sync_new.py 0 99")
    return 0


if __name__ == "__main__":
    sys.exit(main())
