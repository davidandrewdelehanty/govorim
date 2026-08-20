#!/usr/bin/env python3
"""
stage_audio_upload.py — put a staging folder's raw audio into chapter order,
rename it to a zero-padded sequence, and upload it to the bucket.

Why the renaming matters: these rips are named things like
`deti-online.com_-_glava-11.mp3`, and plain alphabetical order puts glava-11
before glava-2. Anything downstream that pairs audio to chapters by sort order
would then be silently off. This script orders by the NUMBERS in the filename,
in the order they appear, so `chast-2-kniga-6-glava-3` sorts correctly against
`chast-1-kniga-1-glava-4` — and it writes a manifest.tsv so the mapping from
`007.mp3` back to the original filename is never guesswork.

Nothing here holds credentials; uploads go through a preconfigured rclone remote.

Usage:
    python3 tools/stage_audio_upload.py --root ~/Downloads/audiobooks           # dry run
    python3 tools/stage_audio_upload.py --root ~/Downloads/audiobooks --book karamazovy
    python3 tools/stage_audio_upload.py --root ~/Downloads/audiobooks --apply --upload
"""
import argparse, os, re, shutil, subprocess, sys

# ── the books to stage: slug -> source folder, plus an optional filename filter
#    `only`  keep files matching this regex
#    `skip`  drop files matching this regex
BOOKS = [
    dict(slug="karamazovy",          folder="The Brothers Karamazov", pad=3,
         title="Братья Карамазовы — Достоевский"),
    dict(slug="tikhy-don",           folder="tixi don", pad=3,
         title="Тихий Дон — Шолохов"),
    dict(slug="zhivago",             folder="doctor zhivago", pad=2,
         title="Доктор Живаго — Пастернак"),
    dict(slug="ottsy-i-deti",        folder="fathers and sons", pad=2,
         title="Отцы и дети — Тургенев"),
    dict(slug="smert-ivana-ilicha",  folder="death of ivan", pad=2,
         title="Смерть Ивана Ильича — Толстой"),
    dict(slug="gore-ot-uma",         folder="gore ot yma", pad=2,
         title="Горе от ума — Грибоедов (4 acts)"),
    # The `mertviye dushi` folder holds TWO books. The untitled glava-N files are
    # Мёртвые души (11 chapters); the ones with a title slug after the number are
    # Капитанская дочка (14 chapters), whose own folder has the FB2 but no audio.
    dict(slug="mertvye-dushi",       folder="mertviye dushi", pad=2,
         only=r"glava-\d+\.mp3$",
         title="Мёртвые души — Гоголь (split out of a mixed folder)"),
    dict(slug="kapitanskaya-dochka", folder="mertviye dushi", pad=2,
         only=r"glava-\d+-[a-z]",
         title="Капитанская дочка — Пушкин (split out of a mixed folder)"),
    dict(slug="loshadinaya-familiya", folder="a horsey name", pad=2,
         title="Лошадиная фамилия — Чехов (single story)"),
]

AUDIO_EXT = (".mp3", ".m4a", ".wav", ".ogg", ".opus", ".flac")

# Cyrillic sub-chapter letters, transliterated the way these rips spell them.
LETTER_RANK = {l: i for i, l in enumerate(
    ["a", "b", "v", "g", "d", "e", "zh", "z", "i", "k", "l", "m", "n"])}


def sort_key(name):
    """Order by the numbers in the filename, in the order they appear.

    Handles `chast-2-kniga-6-glava-3-zh` and `kniga-1-chast-4-<title>` equally,
    because it never assumes which keyword comes first. Front and back matter
    are ranked explicitly — `ot-avtora` has no number at all, and `epilog-glava-1`
    would otherwise sort as chapter 1.
    """
    stem = re.sub(r"\.[^.]+$", "", name).lower()
    stem = re.sub(r"^.*?_-_", "", stem)
    if "ot-avtora" in stem or "predislovie" in stem:
        rank = 0
    elif stem.startswith("epilog") or "posleslovie" in stem:
        rank = 2
    else:
        rank = 1
    nums = [int(n) for n in re.findall(r"\d+", stem)]
    m = re.search(r"\d+-([a-z]{1,2})(?:$|-)", stem)
    letter = LETTER_RANK.get(m.group(1), 99) if m else -1
    return (rank, nums, letter, stem)


def collect(folder, only=None, skip=None):
    files = []
    for root, _, names in os.walk(folder):
        if os.sep + "_" in root:
            continue
        for n in names:
            if not n.lower().endswith(AUDIO_EXT):
                continue
            if only and not re.search(only, n, re.I):
                continue
            if skip and re.search(skip, n, re.I):
                continue
            files.append(os.path.join(root, n))
    return sorted(files, key=lambda p: sort_key(os.path.basename(p)))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", required=True, help="the audiobooks staging folder")
    ap.add_argument("--book", action="append", help="slug(s) to do (default: all)")
    ap.add_argument("--work", default=os.path.expanduser("~/upload-staging"))
    ap.add_argument("--apply", action="store_true", help="write the renamed copies")
    ap.add_argument("--upload", action="store_true", help="rclone them to the bucket")
    ap.add_argument("--remote", default="r2:govorim-audio")
    args = ap.parse_args()

    root = os.path.expanduser(args.root)
    if not os.path.isdir(root):
        raise SystemExit("no such folder: %s\n"
                         "(under WSL, ~ is /home/david — the Windows Downloads folder is\n"
                         " /mnt/c/Users/david/Downloads/audiobooks)" % root)
    books = [b for b in BOOKS if not args.book or b["slug"] in args.book]
    if not books:
        raise SystemExit("no matching slug; known: " + ", ".join(b["slug"] for b in BOOKS))

    total = 0
    for b in books:
        src = os.path.join(root, b["folder"])
        if not os.path.isdir(src):
            print("!! missing folder: %s" % src, file=sys.stderr)
            continue
        files = collect(src, b.get("only"), b.get("skip"))
        pad = b["pad"]
        print("=" * 78)
        print("%s  ->  %s/%s/   (%d files)" % (b["title"], args.remote, b["slug"], len(files)))
        for i, p in enumerate(files, 1):
            new = "%0*d%s" % (pad, i, os.path.splitext(p)[1].lower())
            if i <= 3 or i > len(files) - 2:
                print("   %-8s <- %s" % (new, os.path.basename(p)))
            elif i == 4:
                print("   …")
        total += len(files)

        if not args.apply:
            continue

        out = os.path.join(os.path.expanduser(args.work), b["slug"])
        os.makedirs(out, exist_ok=True)
        with open(os.path.join(out, "manifest.tsv"), "w", encoding="utf-8") as fh:
            fh.write("new\toriginal\n")
            for i, p in enumerate(files, 1):
                new = "%0*d%s" % (pad, i, os.path.splitext(p)[1].lower())
                dst = os.path.join(out, new)
                if not os.path.exists(dst) or os.path.getsize(dst) != os.path.getsize(p):
                    shutil.copy2(p, dst)
                fh.write("%s\t%s\n" % (new, os.path.relpath(p, root)))
        print("   staged -> %s" % out)

        if args.upload:
            print("   uploading …")
            subprocess.run(["rclone", "copy", out, "%s/%s/" % (args.remote, b["slug"]),
                            "--include", "*" + os.path.splitext(files[0])[1].lower(),
                            "--transfers", "8", "--progress"], check=True)

    if total == 0:
        raise SystemExit("\nFound no audio at all under %s — is that the right --root?\n"
                         "(under WSL, ~ is /home/david, not /mnt/c/Users/david)" % root)
    print("\n%d files across %d book(s)." % (total, len(books)))
    if not args.apply:
        print("Dry run — nothing copied or uploaded. Add --apply --upload when the order looks right.")


if __name__ == "__main__":
    main()
