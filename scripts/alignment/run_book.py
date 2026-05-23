#!/usr/bin/env python3
"""Bulk-align all 239 audio chapters of Anna Karenina.

MP3 N → book chapter N. Audio files in /mnt/c/Users/david/Downloads/anna-audio-v2/.
Chapter 1 uses a hand-trimmed audio ('01-cleaned.mp3'); chapters 2-239 use the
raw archive.org files. Chapter 240 has no audio (audiobook is 239 files for 240
book chapters).

Resumes automatically: if the per-chapter output JSON already exists, the
chapter is skipped (use --force to re-align). Whisper transcripts are cached
per audio file, so re-aligning is essentially free after the first run.
"""
import argparse, os, subprocess, sys, time

# Anna Karenina chapter counts per part
PART_CHAPTERS = [34, 35, 32, 24, 33, 32, 31, 19]
NARRATOR = "Андрей Кузнецов"
AUDIO_DIR = "/mnt/c/Users/david/Downloads/anna-audio-v2"
TEXT_DIR = "public/books/novel"
OUTPUT_DIR = "public/books/audio"
ARCHIVE_ITEM = "05_20241004_202410_0005"
SPECIAL_CH1_AUDIO = "01-cleaned.mp3"
SPECIAL_CH1_URL = "https://archive.org/download/govorim-anna-karenina-aligned-v1/01-cleaned.mp3"

def part_chap_for(n):
    """MP3 N (1-based) → (part_1based, chap_in_part_1based) for the 240-chapter book."""
    cum = 0
    for pi, cnt in enumerate(PART_CHAPTERS):
        if cum + cnt >= n:
            return (pi + 1, n - cum)
        cum += cnt
    return None

def audio_file(n):
    if n == 1: return SPECIAL_CH1_AUDIO
    if n < 100: return f"{n:02d}.mp3"
    return f"{n}.mp3"

def audio_url(n):
    if n == 1: return SPECIAL_CH1_URL
    if n < 100: return f"https://archive.org/download/{ARCHIVE_ITEM}/{n:02d}.mp3"
    return f"https://archive.org/download/{ARCHIVE_ITEM}/{n}.mp3"

def main():
    p = argparse.ArgumentParser()
    p.add_argument("--start", type=int, default=1)
    p.add_argument("--end", type=int, default=239)
    p.add_argument("--force", action="store_true",
                   help="Re-align even when output JSON already exists")
    p.add_argument("--model", default="small")
    args = p.parse_args()

    here = os.path.dirname(os.path.abspath(__file__))
    repo = os.path.abspath(os.path.join(here, "..", ".."))
    runner = os.path.join(here, "run_chapter.py")

    total = args.end - args.start + 1
    done = skipped = failed = 0
    t0 = time.time()

    for n in range(args.start, args.end + 1):
        idx_in_run = n - args.start + 1
        pc = part_chap_for(n)
        if pc is None:
            print(f"[{n:3d}] no chapter mapping; skipping"); skipped += 1; continue
        part, chap = pc

        audio_path = os.path.join(AUDIO_DIR, audio_file(n))
        text_path = os.path.join(repo, TEXT_DIR, f"tolstoy-anna-karenina-p{part}-ch{chap}.txt")
        out_path = os.path.join(repo, OUTPUT_DIR, f"tolstoy-anna-karenina-p{part}-ch{chap}.json")

        if not os.path.exists(audio_path):
            print(f"[{n:3d}/{args.end}] p{part}c{chap}  audio missing: {audio_path}"); skipped += 1; continue
        if not os.path.exists(text_path):
            print(f"[{n:3d}/{args.end}] p{part}c{chap}  text missing: {text_path}"); skipped += 1; continue
        if os.path.exists(out_path) and not args.force:
            print(f"[{n:3d}/{args.end}] p{part}c{chap}  ✓ already aligned; skipping"); skipped += 1; continue

        elapsed = time.time() - t0
        per_done = elapsed / max(1, done) if done else 0
        remaining = total - idx_in_run + 1
        eta = per_done * remaining
        print(f"\n=== [{n:3d}/{args.end}] p{part}c{chap}  "
              f"done={done} skipped={skipped} failed={failed}  "
              f"elapsed={int(elapsed)}s  eta={int(eta)}s ({int(eta/60)} min) ===")

        rc = subprocess.run([
            sys.executable, runner,
            "--audio", audio_path,
            "--text", text_path,
            "--output", out_path,
            "--audio-url", audio_url(n),
            "--narrator", NARRATOR,
            "--model", args.model,
        ]).returncode

        if rc == 0:
            done += 1
        else:
            failed += 1
            print(f"[{n:3d}] FAILED rc={rc}")

    print(f"\n=== FINISHED: {done} aligned, {skipped} skipped, {failed} failed in {int(time.time()-t0)}s ===")

if __name__ == "__main__":
    main()
