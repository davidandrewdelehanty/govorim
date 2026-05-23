#!/usr/bin/env python3
"""Run align-chapter.py for every chapter of Anna Karenina."""
import subprocess, os

PART_CHAPTERS = [34, 35, 32, 24, 33, 32, 31, 19]
ROOT  = "/mnt/c/Users/david/projects/govorim-app"
AUDIO = "/mnt/c/Users/david/Downloads/anna-audio-v2"
URL_DEFAULT = "https://archive.org/download/05_20241004_202410_0005"
URL_TRIMMED = "https://archive.org/download/govorim-anna-karenina-aligned-v1"

mp3_num = 1
fails = []
for part_idx, n_chapters in enumerate(PART_CHAPTERS):
    part_num = part_idx + 1
    for ch_in_part in range(1, n_chapters + 1):
        mp3_name = f"{mp3_num:02d}.mp3"
        if mp3_num == 1:
            mp3_path  = f"{AUDIO}/01-trimmed.mp3"
            audio_url = f"{URL_TRIMMED}/01-trimmed.mp3"
        else:
            mp3_path  = f"{AUDIO}/{mp3_name}"
            audio_url = f"{URL_DEFAULT}/{mp3_name}"
        text_path = f"{ROOT}/public/books/novel/tolstoy-anna-karenina-p{part_num}-ch{ch_in_part}.txt"
        out_path  = f"{ROOT}/public/books/audio/tolstoy-anna-karenina-p{part_num}-ch{ch_in_part}.json"
        if not os.path.exists(mp3_path):
            print(f"WARN skip p{part_num}-ch{ch_in_part}: no audio {os.path.basename(mp3_path)}")
            fails.append((part_num, ch_in_part, "no audio"))
            mp3_num += 1
            continue
        if not os.path.exists(text_path):
            print(f"WARN skip p{part_num}-ch{ch_in_part}: no text")
            fails.append((part_num, ch_in_part, "no text"))
            mp3_num += 1
            continue
        print(f"[{mp3_num}/240] p{part_num}-ch{ch_in_part}")
        r = subprocess.run([
            "python3", "scripts/align-chapter.py",
            "--audio", mp3_path,
            "--text",  text_path,
            "--audio-url", audio_url,
            "--out",   out_path,
            "--narrator", "Андрей Кузнецов",
        ], cwd=ROOT, check=False)
        if r.returncode != 0:
            fails.append((part_num, ch_in_part, "alignment failed"))
        mp3_num += 1

print(f"\nDone. {len(fails)} failures:")
for p, c, why in fails:
    print(f"  p{p}-ch{c}: {why}")
