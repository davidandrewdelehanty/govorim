#!/usr/bin/env python3
"""
add_plain_book.py — put a book in the catalogue with per-chapter audio and no
alignment at all.

A chapter JSON only needs an audio_url. Alignment used to be a prerequisite
because the reader highlighted along with the narrator; it doesn't any more, so
a book goes live as soon as its audio is on R2 and its FB2 is in the repo. No
MFA, no GPU, no WSL — this runs in a second.

What it writes:
  public/books/audio/<slug>/<slug>-chNN.json   {audio_url, narrator, fragments: []}
  public/books/index.json                      one new entry, chapters in order

It refuses to write if the audio file count and the FB2 chapter count disagree,
because a silent off-by-one there means every chapter plays the wrong recording
and nothing in the UI would reveal it.

Usage (dry run first — always):
    python3 tools/add_plain_book.py --repo . --slug gore-ot-uma \
        --fb2 novel/Griboedov_Gore_ot_uma.fb2 \
        --title "Горе от ума" --author "Грибоедов А.С."

    python3 tools/add_plain_book.py ... --apply

Audio filenames come from the staging manifest if there is one
(~/upload-staging/<slug>/manifest.tsv), else from `rclone lsf`, else from
--count with a %0Nd pattern.
"""
import argparse, json, os, re, subprocess, sys

PUBLIC_BASE = "https://pub-84adcd23e17e4925a0ac7eca17ea2556.r2.dev"
AUDIO_EXT = (".mp3", ".m4a", ".wav", ".ogg", ".opus", ".flac")


def load(path):
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


def audio_names(args):
    """The audio filenames on the bucket, in chapter order."""
    manifest = os.path.expanduser(os.path.join(args.staging, args.slug, "manifest.tsv"))
    if os.path.exists(manifest):
        names = []
        with open(manifest, encoding="utf-8") as fh:
            next(fh, None)
            for line in fh:
                new = line.split("\t")[0].strip()
                if new.lower().endswith(AUDIO_EXT):
                    names.append(new)
        if names:
            print("audio list from %s" % manifest)
            return names
    try:
        out = subprocess.check_output(
            ["rclone", "lsf", "%s/%s/" % (args.remote, args.slug)],
            stderr=subprocess.DEVNULL).decode()
        names = sorted(n.strip() for n in out.splitlines()
                       if n.strip().lower().endswith(AUDIO_EXT))
        if names:
            print("audio list from %s/%s/" % (args.remote, args.slug))
            return names
    except Exception:
        pass
    if args.count:
        pad = len(str(args.count)) if args.count > 99 else 2
        print("audio list synthesised from --count %d" % args.count)
        return ["%0*d.mp3" % (pad, i) for i in range(1, args.count + 1)]
    raise SystemExit("Could not determine the audio filenames. Pass --count, or "
                     "make sure the staging manifest or the rclone remote is reachable.")


def fb2_chapter_count(repo, rel):
    """Reuse the FB2 splitter from chop_by_transcript.py rather than a second copy."""
    import importlib.util
    tool = os.path.join(repo, "tools", "chop_by_transcript.py")
    if not os.path.exists(tool):
        return None
    spec = importlib.util.spec_from_file_location("cbt", tool)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    try:
        return len(m.fb2_chapters(os.path.join(repo, "public/books", rel)))
    except Exception as e:
        print("  (couldn't parse the FB2 for a chapter count: %s)" % e)
        return None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo", default=".")
    ap.add_argument("--slug", required=True, help="R2 folder AND the audio/<slug>/ folder name")
    ap.add_argument("--fb2", required=True, help="path under public/books/, e.g. novel/idiot.fb2")
    ap.add_argument("--title", required=True)
    ap.add_argument("--author", default="")
    ap.add_argument("--category", default="Works")
    ap.add_argument("--narrator", default="audiobook")
    ap.add_argument("--source", default="r2")
    ap.add_argument("--base", default=PUBLIC_BASE, help="public bucket base URL")
    ap.add_argument("--remote", default="r2:govorim-audio")
    ap.add_argument("--staging", default="~/upload-staging")
    ap.add_argument("--count", type=int, help="number of chapters, if the filenames can't be listed")
    ap.add_argument("--force", action="store_true", help="write even if the counts disagree")
    ap.add_argument("--apply", action="store_true")
    args = ap.parse_args()

    repo = os.path.abspath(args.repo)
    books_dir = os.path.join(repo, "public/books")
    fb2_path = os.path.join(books_dir, args.fb2)
    if not os.path.exists(fb2_path):
        raise SystemExit("FB2 not found: %s" % fb2_path)

    names = audio_names(args)
    n_ch = fb2_chapter_count(repo, args.fb2)
    print("\n%s — %d audio files, FB2 has %s chapters"
          % (args.title, len(names), n_ch if n_ch is not None else "?"))
    if n_ch is not None and n_ch != len(names):
        print("  !! MISMATCH: %d audio files vs %d FB2 chapters." % (len(names), n_ch))
        print("     Pairing would be off and nothing in the reader would show it.")
        if not args.force:
            raise SystemExit("     Refusing to write. Fix the split, or pass --force if you know why.")
        print("     --force given; writing anyway.")

    index_path = os.path.join(books_dir, "index.json")
    index = load(index_path)
    if any(b.get("title") == args.title for b in index):
        raise SystemExit('"%s" is already in index.json.' % args.title)

    out_dir = os.path.join(books_dir, "audio", args.slug)
    rel_chapters, pad = [], max(2, len(str(len(names))))
    for i, fname in enumerate(names, 1):
        stem = "%s-ch%0*d" % (args.slug, pad, i)
        rel_chapters.append("audio/%s/%s.json" % (args.slug, stem))
        if i <= 2 or i == len(names):
            print("  %-30s -> %s/%s/%s" % (stem + ".json", args.base.rsplit("/", 1)[-1], args.slug, fname))
        elif i == 3:
            print("  …")
    entry = {
        "filename": args.fb2,
        "title": args.title,
        "author": args.author,
        "category": args.category,
        "audiobook": {"narrator": args.narrator, "source": args.source, "chapters": rel_chapters},
    }

    if not args.apply:
        print("\nDry run — nothing written. Re-run with --apply.")
        return

    os.makedirs(out_dir, exist_ok=True)
    for i, fname in enumerate(names, 1):
        stem = "%s-ch%0*d" % (args.slug, pad, i)
        doc = {
            "audio_url": "%s/%s/%s" % (args.base.rstrip("/"), args.slug, fname),
            "narrator": args.narrator,
            "fragments": [],
        }
        with open(os.path.join(out_dir, stem + ".json"), "w", encoding="utf-8") as fh:
            json.dump(doc, fh, ensure_ascii=False)
            fh.write("\n")
    index.append(entry)
    with open(index_path, "w", encoding="utf-8") as fh:
        json.dump(index, fh, ensure_ascii=False, indent=2)
        fh.write("\n")
    print("\nWrote %d chapter JSONs to public/books/audio/%s/ and added \"%s\" to index.json."
          % (len(names), args.slug, args.title))


if __name__ == "__main__":
    main()
