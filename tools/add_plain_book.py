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


def fb2_chapter_count(repo, rel, automfa):
    """Count chapters the way the READER will split this FB2.

    src/App.jsx carries its own FB2 splitter, kept deliberately identical to
    Auto-MFA's app/fb2.py (subtitle-based chapter markers, endnote sections
    dropped, and so on). A naive leaf-<section> walk disagrees with it — on
    Горе от ума by more than twofold — so counting with anything else would
    check the wrong thing. Use the canonical implementation when it is on disk;
    fall back to the rough one only to have some signal at all.
    """
    import importlib.util
    from pathlib import Path
    fb2py = os.path.expanduser(os.path.join(automfa, "app", "fb2.py")) if automfa else ""
    if fb2py and os.path.exists(fb2py):
        spec = importlib.util.spec_from_file_location("automfa_fb2", fb2py)
        m = importlib.util.module_from_spec(spec)
        try:
            spec.loader.exec_module(m)
            return len(m.extract_chapters(Path(os.path.join(repo, "public/books", rel)))), "Auto-MFA app/fb2.py"
        except Exception as e:
            print("  (Auto-MFA fb2.py could not parse this FB2: %s)" % e)
    tool = os.path.join(repo, "tools", "chop_by_transcript.py")
    if os.path.exists(tool):
        spec = importlib.util.spec_from_file_location("cbt", tool)
        m = importlib.util.module_from_spec(spec)
        try:
            spec.loader.exec_module(m)
            return len(m.fb2_chapters(os.path.join(repo, "public/books", rel))), "rough fallback splitter"
        except Exception as e:
            print("  (couldn't parse the FB2 for a chapter count: %s)" % e)
    return None, None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo", default=".")
    ap.add_argument("--slug", required=True, help="R2 folder AND the audio/<slug>/ folder name")
    ap.add_argument("--fb2", required=True, help="path under public/books/, e.g. novel/idiot.fb2")
    ap.add_argument("--title", required=True)
    ap.add_argument("--author", default="")
    ap.add_argument("--category", default="Novels")
    ap.add_argument("--narrator", default="audiobook")
    ap.add_argument("--source", default="r2")
    ap.add_argument("--base", default=PUBLIC_BASE, help="public bucket base URL")
    ap.add_argument("--remote", default="r2:govorim-audio")
    ap.add_argument("--staging", default="~/upload-staging")
    ap.add_argument("--count", type=int, help="number of chapters, if the filenames can't be listed")
    ap.add_argument("--automfa", default=None,
                    help="Auto-MFA checkout — its app/fb2.py is the canonical chapter splitter. "
                         "Defaults to a sibling of the repo, then ~/projects/Auto-MFA.")
    ap.add_argument("--chapters-without-audio", default="",
                    help="1-based chapter numbers that have no recording (e.g. a foreword or "
                         "an appendix). They get a null entry and stay text-only. "
                         "Example: --chapters-without-audio 1,233")
    ap.add_argument("--force", action="store_true", help="write even if the counts disagree")
    ap.add_argument("--apply", action="store_true")
    args = ap.parse_args()

    repo = os.path.abspath(args.repo)
    books_dir = os.path.join(repo, "public/books")
    if not args.automfa:
        # Auto-MFA normally sits beside govorim-app. Falling back to a rough
        # splitter is worse than it sounds: on Тихий Дон the two disagree by 2
        # chapters, which is exactly the kind of off-by-N this check exists to
        # catch — so say plainly which one is being used.
        for cand in (os.path.join(os.path.dirname(repo), "Auto-MFA"),
                     os.path.expanduser("~/projects/Auto-MFA")):
            if os.path.exists(os.path.join(cand, "app", "fb2.py")):
                args.automfa = cand
                break
        else:
            args.automfa = ""
    fb2_path = os.path.join(books_dir, args.fb2)
    if not os.path.exists(fb2_path):
        raise SystemExit("FB2 not found: %s" % fb2_path)

    names = audio_names(args)
    n_ch, how = fb2_chapter_count(repo, args.fb2, args.automfa)
    silent = sorted({int(x) for x in re.findall(r"\d+", args.chapters_without_audio)})
    print("\n%s — %d audio files, FB2 has %s chapters (%s)"
          % (args.title, len(names), n_ch if n_ch is not None else "?", how or "no splitter available"))
    if silent:
        print("  chapters with no recording: %s" % ", ".join(str(x) for x in silent))
    if n_ch is not None and n_ch != len(names) + len(silent):
        gap = n_ch - len(names) - len(silent)
        print("  !! MISMATCH: %d audio + %d silent != %d FB2 chapters (off by %+d)."
              % (len(names), len(silent), n_ch, -gap))
        print("     Pairing would be off and nothing in the reader would show it.")
        if not args.force:
            raise SystemExit("     Refusing to write. Fix the pairing, or pass --force if you know why.")
        print("     --force given; writing anyway.")

    index_path = os.path.join(books_dir, "index.json")
    index = load(index_path)
    if any(b.get("title") == args.title for b in index):
        raise SystemExit('"%s" is already in index.json.' % args.title)

    out_dir = os.path.join(books_dir, "audio", args.slug)
    total = (n_ch if n_ch is not None else len(names) + len(silent))
    pad = max(2, len(str(len(names))))
    rel_chapters, plan, ai = [], [], 0
    for ch_no in range(1, total + 1):
        if ch_no in silent:
            rel_chapters.append(None)          # text-only chapter, no recording
            plan.append((ch_no, None, None))
            continue
        if ai >= len(names):
            rel_chapters.append(None)
            plan.append((ch_no, None, None))
            continue
        stem = "%s-ch%0*d" % (args.slug, pad, ai + 1)
        rel_chapters.append("audio/%s/%s.json" % (args.slug, stem))
        plan.append((ch_no, stem, names[ai]))
        ai += 1
    for ch_no, stem, fname in plan:
        if ch_no <= 3 or ch_no >= total - 1 or fname is None:
            print("  ch%-4d %-30s -> %s" % (ch_no, (stem or "") + (".json" if stem else "(text only)"),
                                            ("%s/%s" % (args.slug, fname)) if fname else "—"))
        elif ch_no == 4:
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
    for ch_no, stem, fname in plan:
        if not stem:
            continue
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
    n_silent = sum(1 for c in rel_chapters if c is None)
    print("\nWrote %d chapter JSONs to public/books/audio/%s/ and added \"%s\" to index.json%s."
          % (len(names), args.slug, args.title,
             " (%d chapter(s) left text-only)" % n_silent if n_silent else ""))


if __name__ == "__main__":
    main()
