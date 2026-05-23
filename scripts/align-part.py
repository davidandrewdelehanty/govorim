#!/usr/bin/env python3
"""
align-part.py — align an audiobook part chapter-by-chapter, then merge into
a single part-level alignment JSON with cumulative time offsets.

More reliable than aligning huge combined audio against thousands of sentences:
small alignments are fast and don't run out of memory.

Usage:
  python scripts/align-part.py \\
    --audio-dir ~/Downloads/anna-audio/ \\
    --part 1 \\
    --text-dir public/books/novel/ \\
    --text-prefix tolstoy-anna-karenina \\
    --out public/books/audio/tolstoy-anna-karenina-ch1.json \\
    --audio-url "https://archive.org/download/govorim-anna-karenina-aligned-v1/anna-karenina-part1.mp3" \\
    --narrator "Unknown reader"
"""
import argparse, json, os, re, subprocess, sys, tempfile, shutil
from collections import defaultdict


def ffprobe_duration(path):
    r = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration",
         "-of", "default=noprint_wrappers=1:nokey=1", path],
        capture_output=True, text=True, check=True)
    return float(r.stdout.strip())


def concat_audio(audio_files, out_path):
    lf = tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False, encoding="utf-8")
    try:
        for af in audio_files:
            lf.write(f"file '{os.path.abspath(af)}'\n")
        lf.close()
        subprocess.run(
            ["ffmpeg", "-y", "-f", "concat", "-safe", "0",
             "-i", lf.name, "-c", "copy", out_path],
            check=True, capture_output=True)
    finally:
        os.unlink(lf.name)


def align_chapter(audio, text, out, script_dir):
    align_script = os.path.join(script_dir, "align-audiobook.py")
    subprocess.run(
        ["python", align_script,
         "--audio", audio, "--text", text, "--out", out,
         "--audio-url", "placeholder://chapter"],
        check=True)


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--audio-dir", required=True)
    p.add_argument("--audio-pattern", default=r"^(\d{2})_(\d{2})_(\d{2})_.+\.mp3$")
    p.add_argument("--part", required=True, type=int)
    p.add_argument("--text-dir", required=True)
    p.add_argument("--text-prefix", required=True)
    p.add_argument("--out", required=True)
    p.add_argument("--audio-url", required=True)
    p.add_argument("--narrator", default=None)
    p.add_argument("--year", type=int, default=None)
    p.add_argument("--language", default="rus")
    p.add_argument("--keep-temp", action="store_true")
    args = p.parse_args()

    audio_dir = os.path.abspath(args.audio_dir)
    text_dir = os.path.abspath(args.text_dir)
    out_abs = os.path.abspath(args.out)
    script_dir = os.path.dirname(os.path.abspath(__file__))

    pat = re.compile(args.audio_pattern)
    by_chapter = defaultdict(list)
    for fname in sorted(os.listdir(audio_dir)):
        m = pat.match(fname)
        if not m: continue
        part_, ch_, sub_ = int(m.group(1)), int(m.group(2)), int(m.group(3))
        if part_ != args.part: continue
        by_chapter[ch_].append((sub_, os.path.join(audio_dir, fname)))

    if not by_chapter:
        print(f"ERROR: no audio files for part {args.part} in {audio_dir}", file=sys.stderr)
        sys.exit(2)
    for ch in by_chapter:
        by_chapter[ch].sort(key=lambda x: x[0])

    chapter_numbers = sorted(by_chapter.keys())
    print(f"Found {len(chapter_numbers)} chapters in part {args.part}")

    tmpdir = tempfile.mkdtemp(prefix="align-part-")
    print(f"Temp dir: {tmpdir}")
    chapter_data = []

    try:
        for i, ch_num in enumerate(chapter_numbers):
            pieces = [p[1] for p in by_chapter[ch_num]]
            text_file = os.path.join(text_dir,
                f"{args.text_prefix}-p{args.part}-ch{ch_num}.txt")
            if not os.path.isfile(text_file):
                text_file = os.path.join(text_dir,
                    f"{args.text_prefix}-ch{ch_num}.txt")
            if not os.path.isfile(text_file):
                print(f"ERROR: text file not found for chapter {ch_num}: {text_file}", file=sys.stderr)
                sys.exit(2)

            print(f"\n=== Chapter {ch_num} ({i+1}/{len(chapter_numbers)}) ===")
            print(f"  Audio: {len(pieces)} file(s)")
            print(f"  Text:  {os.path.basename(text_file)}")

            if len(pieces) > 1:
                ch_audio = os.path.join(tmpdir, f"ch{ch_num:03d}.mp3")
                print(f"  Concatenating {len(pieces)} sub-pieces...")
                concat_audio(pieces, ch_audio)
            else:
                ch_audio = pieces[0]

            duration = ffprobe_duration(ch_audio)
            print(f"  Duration: {duration:.1f}s")

            ali_json = os.path.join(tmpdir, f"ch{ch_num:03d}.json")
            align_chapter(ch_audio, text_file, ali_json, script_dir)
            with open(ali_json, "r", encoding="utf-8") as f:
                data = json.load(f)
            chapter_data.append({
                "chapter": ch_num,
                "duration": duration,
                "fragments": data.get("fragments", []),
            })

        print(f"\n=== Merging {len(chapter_data)} chapter alignments ===")
        all_frags = []
        cum = 0.0
        for ch in chapter_data:
            for f in ch["fragments"]:
                all_frags.append({
                    "begin": round(f["begin"] + cum, 3),
                    "end": round(f["end"] + cum, 3),
                    "text": f["text"],
                })
            cum += ch["duration"]

        out_obj = {
            "version": 1,
            "language": args.language,
            "audio_url": args.audio_url,
            "fragments": all_frags,
        }
        if args.narrator: out_obj["narrator"] = args.narrator
        if args.year:     out_obj["year"] = args.year

        os.makedirs(os.path.dirname(out_abs) or ".", exist_ok=True)
        with open(out_abs, "w", encoding="utf-8") as f:
            json.dump(out_obj, f, ensure_ascii=False, indent=2)

        mins, secs = divmod(int(cum), 60)
        print(f"\nOK: wrote {len(all_frags):,} fragments")
        print(f"    total duration: {mins}:{secs:02d}")
        print(f"    output: {out_abs}")

    finally:
        if not args.keep_temp:
            shutil.rmtree(tmpdir, ignore_errors=True)
        else:
            print(f"\nTemp dir kept at: {tmpdir}")


if __name__ == "__main__":
    main()
