#!/usr/bin/env python3
"""
chop_aligned.py — cut a long recording into one MP3 per chapter/act, using the
chapter boundaries that ALREADY exist in the alignment JSONs.

Why this exists
---------------
Several books stream one long MP3 and slice it per chapter with `stopAtEnd`.
Now that read-along highlighting is gone, each chapter should have its own file.
The cut points do not need to be rediscovered: every chapter JSON already
carries `word_timings` in the long file's timeline, so chapter N ends at its
last word and chapter N+1 starts at its first word. We cut in the gap between
them and rebase every timestamp in the JSON to the new file's zero.

What it touches
---------------
  * writes new MP3s into a work dir, and (with --upload) to an R2 folder
  * rewrites each affected chapter JSON in place: new audio_url, rebased
    fragments/word_timings, `stopAtEnd` dropped
  * public/books/index.json is NOT touched — chapter JSON paths do not change

Requires: ffmpeg + ffprobe, and (for --download/--upload) an rclone remote that
already points at the bucket. No credentials live in this file.

Usage (dry run — prints the cut table and stops):
    python3 tools/chop_aligned.py --repo . --title "Дядя Ваня"
    python3 tools/chop_aligned.py --repo . --all

Then, for real:
    python3 tools/chop_aligned.py --repo . --title "Дядя Ваня" --apply
    python3 tools/chop_aligned.py --repo . --title "Дядя Ваня" --apply --upload
"""
import argparse, json, os, re, shutil, subprocess, sys, tempfile

LEAD = 1.0          # seconds of run-up kept before a chapter's first word
TAIL = 1.5          # seconds kept after the last chapter's last word (if available)


# ── small helpers ────────────────────────────────────────────────────────────
def run(cmd, **kw):
    return subprocess.run(cmd, check=True, **kw)


def probe_duration(path):
    out = subprocess.check_output(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration",
         "-of", "csv=p=0", path])
    return float(out.decode().strip())


def load(path):
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


def save(path, obj):
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(obj, fh, ensure_ascii=False)
        fh.write("\n")


def span(doc):
    """(first spoken word begin, last spoken word end) for a chapter JSON."""
    wt = doc.get("word_timings") or []
    if wt:
        return float(wt[0]["begin"]), float(wt[-1]["end"])
    fr = [f for f in (doc.get("fragments") or []) if f.get("begin") is not None]
    if not fr:
        return None, None
    return float(fr[0]["begin"]), float(fr[-1].get("end", fr[-1]["begin"]))


def clock(s):
    s = max(0.0, float(s))
    return "%d:%02d:%06.3f" % (int(s // 3600), int(s % 3600 // 60), s % 60)


# ── job discovery ────────────────────────────────────────────────────────────
URL_RE = re.compile(r'"audio_url"\s*:\s*"([^"]*)"')


def peek_url(path):
    """Pull audio_url out of the head of a chapter JSON without parsing it all.

    These files run to megabytes once word_timings are in them, and a full
    library sweep touches thousands. Only the ones that turn out to matter get
    a real json.load().
    """
    with open(path, "rb") as fh:
        head = fh.read(65536).decode("utf-8", errors="ignore")
    m = URL_RE.search(head)
    if m:
        return m.group(1)
    return (load(path).get("audio_url") or "")


def find_jobs(repo, title_filter):
    """A 'job' is a run of chapters in one book that share a single audio_url."""
    books = load(os.path.join(repo, "public/books/index.json"))
    jobs = []
    for book in books:
        title = book.get("title", "?")
        if title_filter and title != title_filter:
            continue
        ab = book.get("audiobook") or {}
        chapters = [c for c in (ab.get("chapters") or []) if isinstance(c, str)]
        if not chapters:
            continue
        groups, prev_url = [], None
        for rel in chapters:
            path = os.path.join(repo, "public/books", rel)
            if not os.path.exists(path):
                print("  ! missing chapter JSON: %s" % rel, file=sys.stderr)
                prev_url = None
                continue
            url = peek_url(path)
            if url and url == prev_url:
                groups[-1]["items"].append((rel, path))
            else:
                groups.append({"url": url, "items": [(rel, path)]})
            prev_url = url
        for g in groups:
            if len(g["items"]) > 1:
                g["title"] = title
                g["items"] = [(rel, path, load(path)) for rel, path in g["items"]]
                jobs.append(g)
    return jobs


# ── boundary maths ───────────────────────────────────────────────────────────
def plan_cuts(job, duration):
    """Turn a group of chapters into [(rel, path, doc, start, end)]."""
    spans = []
    for rel, path, doc in job["items"]:
        b, e = span(doc)
        if b is None:
            raise SystemExit("no timings in %s — cannot derive a cut point" % rel)
        spans.append((rel, path, doc, b, e))

    cuts = []
    for i, (rel, path, doc, b, e) in enumerate(spans):
        # start
        if i == 0:
            start = max(0.0, b - LEAD)
        else:
            prev_end = spans[i - 1][4]
            start = (prev_end + b) / 2.0 if b > prev_end else b
        # end
        if i == len(spans) - 1:
            end = min(duration, e + TAIL) if duration else e + TAIL
        else:
            nxt_begin = spans[i + 1][3]
            end = (e + nxt_begin) / 2.0 if nxt_begin > e else nxt_begin
        cuts.append([rel, path, doc, round(start, 3), round(end, 3)])

    # make the segments strictly contiguous and monotonic
    for i in range(1, len(cuts)):
        if cuts[i][3] < cuts[i - 1][4]:
            cuts[i][3] = cuts[i - 1][4]
        cuts[i - 1][4] = cuts[i][3]
    return cuts


def rebase(doc, start, new_url):
    """Shift every timestamp so the new file starts at 0."""
    def sh(t):
        return round(max(0.0, float(t) - start), 3)

    out = dict(doc)
    out["audio_url"] = new_url
    out.pop("stopAtEnd", None)
    frags = []
    for f in doc.get("fragments") or []:
        g = dict(f)
        if g.get("begin") is not None:
            g["begin"] = sh(g["begin"])
        if g.get("end") is not None:
            g["end"] = sh(g["end"])
        if g.get("words"):
            g["words"] = [dict(w, begin=sh(w["begin"]), end=sh(w["end"]))
                          for w in g["words"]]
        frags.append(g)
    if frags:
        out["fragments"] = frags
    if doc.get("word_timings"):
        out["word_timings"] = [dict(w, begin=sh(w["begin"]), end=sh(w["end"]))
                               for w in doc["word_timings"]]
    return out


def push(workdir, remote):
    """Upload every folder of cut MP3s under `workdir` to the bucket.

    Split out from the cut step on purpose. Once the chapter JSONs have been
    rewritten they no longer share an audio_url, so a second --apply run finds
    nothing to do and would silently skip the upload — leaving the JSONs
    pointing at files that are not on the bucket yet.
    """
    if not os.path.isdir(workdir):
        raise SystemExit("no such work dir: %s" % workdir)
    folders = sorted(d for d in os.listdir(workdir)
                     if os.path.isdir(os.path.join(workdir, d))
                     and any(f.endswith(".mp3") for f in os.listdir(os.path.join(workdir, d))))
    if not folders:
        raise SystemExit("no folders of MP3s under %s" % workdir)
    for d in folders:
        src = os.path.join(workdir, d)
        n = len([f for f in os.listdir(src) if f.endswith(".mp3")])
        print("uploading %d files: %s -> %s/%s/" % (n, src, remote, d))
        run(["rclone", "copy", src, "%s/%s/" % (remote, d),
             "--transfers", "8", "--progress"])
    print("\nUploaded %d folder(s). Hard-refresh the reader to clear the old audio." % len(folders))


# ── main ─────────────────────────────────────────────────────────────────────
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo", default=".", help="govorim-app repo root")
    ap.add_argument("--title", help="book title exactly as it appears in index.json")
    ap.add_argument("--all", action="store_true", help="every book that needs chopping")
    ap.add_argument("--apply", action="store_true", help="actually cut + rewrite JSONs")
    ap.add_argument("--upload", action="store_true", help="rclone the new MP3s to the bucket")
    ap.add_argument("--remote", default="r2:govorim-audio",
                    help="rclone remote:bucket (configure it once, outside this script)")
    ap.add_argument("--dest-suffix", default="-split",
                    help="new bucket folder = <source folder><suffix>")
    ap.add_argument("--work", help="work dir (default: a temp dir)")
    ap.add_argument("--push", metavar="WORKDIR",
                    help="upload an already-cut work dir and exit. Use this when you "
                         "cut in one run and upload in another: by then the JSONs no "
                         "longer share an audio_url, so the normal scan finds nothing.")
    ap.add_argument("--quality", default="3", help="libmp3lame -q:a value")
    ap.add_argument("--copy", action="store_true",
                    help="stream-copy instead of re-encoding (faster, ~26ms granularity)")
    args = ap.parse_args()

    for tool in ("ffmpeg", "ffprobe"):
        if not shutil.which(tool):
            raise SystemExit("%s not found on PATH" % tool)

    if args.push:
        push(args.push, args.remote)
        return

    if not args.title and not args.all:
        ap.error("pass --title, --all, or --push")

    jobs = find_jobs(args.repo, args.title)
    if not jobs:
        print("Nothing to chop — every chapter already has its own file.")
        return

    work = args.work or tempfile.mkdtemp(prefix="chop-")
    os.makedirs(work, exist_ok=True)
    print("work dir: %s\n" % work)

    for job in jobs:
        url = job["url"]
        folder, fname = url.rstrip("/").rsplit("/", 2)[-2:]
        base = url.rsplit("/", 2)[0]
        dest_folder = folder + args.dest_suffix
        src = os.path.join(work, folder + "__" + fname)

        print("=" * 78)
        print("%s  —  %d chapters share %s/%s" % (job["title"], len(job["items"]), folder, fname))

        duration = 0.0
        if args.apply:
            if not os.path.exists(src):
                print("  downloading %s/%s …" % (folder, fname))
                run(["rclone", "copyto", "%s/%s/%s" % (args.remote, folder, fname), src])
            duration = probe_duration(src)
            print("  source duration: %s" % clock(duration))

        cuts = plan_cuts(job, duration)

        print("  %-34s %-14s %-14s %s" % ("chapter json", "start", "end", "length"))
        for rel, path, doc, start, end in cuts:
            print("  %-34s %-14s %-14s %s" %
                  (os.path.basename(rel), clock(start), clock(end), clock(end - start)))
        if not args.apply:
            print("  (dry run — pass --apply to cut)\n")
            continue

        outdir = os.path.join(work, dest_folder)
        os.makedirs(outdir, exist_ok=True)
        for rel, path, doc, start, end in cuts:
            stem = os.path.splitext(os.path.basename(rel))[0]
            out_mp3 = os.path.join(outdir, stem + ".mp3")
            enc = ["-c", "copy"] if args.copy else ["-c:a", "libmp3lame", "-q:a", args.quality]
            run(["ffmpeg", "-y", "-v", "error", "-ss", "%.3f" % start, "-to", "%.3f" % end,
                 "-i", src] + enc + ["-map_metadata", "-1", out_mp3])
            got = probe_duration(out_mp3)
            want = end - start
            flag = "" if abs(got - want) < 0.75 else "   <-- CHECK (%.2fs off)" % (got - want)
            new_url = "%s/%s/%s.mp3" % (base, dest_folder, stem)
            new_doc = rebase(doc, start, new_url)
            _, last = span(new_doc)
            if last is not None and last > got + 0.5:
                flag += "   <-- last word (%s) past end of file" % clock(last)
            save(path, new_doc)
            print("  wrote %-20s %s%s" % (stem + ".mp3", clock(got), flag))

        if args.upload:
            print("  uploading to %s/%s/ …" % (args.remote, dest_folder))
            run(["rclone", "copy", outdir, "%s/%s/" % (args.remote, dest_folder),
                 "--transfers", "8", "--progress"])
        else:
            print("")
            print("  !! NOT UPLOADED. The JSONs now point at %s/ on the bucket," % dest_folder)
            print("  !! and until these files are there, this book has no audio. Run:")
            print("  !!     python3 %s --push %s" % (os.path.basename(__file__), work))
        print()

    if args.apply:
        print("Done. Chapter JSONs were rewritten in place; index.json needs no edit.")
    else:
        print("Dry run only — nothing was downloaded, cut, uploaded or rewritten.")


if __name__ == "__main__":
    main()
