#!/usr/bin/env python3
"""
align-audiobook.py — align a Russian audiobook recording to its text so the
Govorim reader app can sentence-track during playback.

Aeneas is the heavy lifter: it takes (audio file, sentence-per-line text) and
emits per-sentence timestamps. This wrapper converts aeneas' output into the
compact JSON shape that App.jsx expects.

------------------------------------------------------------------------------
Install (one-time):

  macOS:
    brew install espeak ffmpeg
    pip install numpy
    pip install aeneas

  Ubuntu/Debian:
    sudo apt install espeak espeak-data ffmpeg python3-pip python3-dev
    pip3 install numpy
    pip3 install aeneas

  Windows (WSL is easier — but if native):
    Install eSpeak from http://espeak.sourceforge.net/download.html
    Install FFmpeg from https://ffmpeg.org/
    pip install numpy
    pip install aeneas

------------------------------------------------------------------------------
Workflow per chapter:

  1. Get the audiobook MP3 (download from archive.org or stream URL)
  2. Get the chapter text — one Russian sentence per line — saved as e.g. ch1.txt
     (use extract-sentences.js if you have an FB2 file)
  3. Run:

       python align-audiobook.py \
         --audio nose-ch1.mp3 \
         --text  nose-ch1.txt \
         --out   gogol-nose-ch1.json \
         --audio-url "https://archive.org/download/.../nose-ch1.mp3"

  4. Drop the JSON into public/books/audio/ and reference it from index.json
     under the book's "audiobook.chapters" array.

------------------------------------------------------------------------------
Notes on quality:

  * If a chapter's alignment drifts on long silences, try:
      --boundary-adjust auto    (default; balances neighbours)
      --boundary-adjust aftercurrent  (sticks to current segment end)
      --boundary-adjust beforenext    (sticks to next segment start)
  * Audiobook ≠ exact text: narrators sometimes skip footnotes or add intros.
    Aeneas tolerates small skips gracefully — it just leaves time gaps. For
    larger omissions, trim the text file ahead of time.
"""

import argparse
import json
import os
import sys
import tempfile


def main():
    parser = argparse.ArgumentParser(
        description="Align a Russian audiobook to its text for the Govorim reader",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--audio", required=True,
                        help="Path to local audio file (MP3, M4A, WAV, OGG, etc.)")
    parser.add_argument("--text", required=True,
                        help="Path to text file (ONE SENTENCE PER LINE)")
    parser.add_argument("--out", required=True,
                        help="Output JSON path (alignment data)")
    parser.add_argument("--audio-url", default=None,
                        help="Public streamable URL to embed in JSON. "
                             "Defaults to the local --audio path (only useful for testing).")
    parser.add_argument("--language", default="rus",
                        help="aeneas language code (default: rus)")
    parser.add_argument("--boundary-adjust", default="auto",
                        choices=["auto", "aftercurrent", "beforenext", "offset", "rate", "rateaggressive", "none"],
                        help="How aeneas adjusts fragment boundaries (default: auto)")
    parser.add_argument("--narrator", default=None,
                        help="Narrator name (saved as metadata in the JSON)")
    parser.add_argument("--year", default=None, type=int,
                        help="Recording year (saved as metadata)")
    args = parser.parse_args()

    # Late import so a missing aeneas gives a friendlier error.
    try:
        from aeneas.executetask import ExecuteTask
        from aeneas.task import Task
        from aeneas.runtimeconfiguration import RuntimeConfiguration
    except ImportError:
        print("ERROR: aeneas not installed.\n", file=sys.stderr)
        print("Install instructions:", file=sys.stderr)
        print("  macOS:  brew install espeak ffmpeg && pip install numpy aeneas", file=sys.stderr)
        print("  Linux:  sudo apt install espeak ffmpeg python3-dev && pip install numpy aeneas", file=sys.stderr)
        sys.exit(2)

    audio_abs = os.path.abspath(args.audio)
    text_abs = os.path.abspath(args.text)
    out_abs = os.path.abspath(args.out)

    if not os.path.isfile(audio_abs):
        print(f"ERROR: audio file not found: {audio_abs}", file=sys.stderr)
        sys.exit(2)
    if not os.path.isfile(text_abs):
        print(f"ERROR: text file not found: {text_abs}", file=sys.stderr)
        sys.exit(2)

    # Count sentences before running so the user gets feedback on what's about
    # to happen.
    with open(text_abs, "r", encoding="utf-8") as fh:
        sentences = [line.strip() for line in fh if line.strip()]
    if not sentences:
        print("ERROR: text file is empty or only whitespace.", file=sys.stderr)
        sys.exit(2)
    print(f"Aligning {len(sentences):,} sentences against {os.path.basename(audio_abs)}...")
    print(f"Language: {args.language}, boundary-adjust: {args.boundary_adjust}")

    config = (
        f"task_language={args.language}|"
        "is_text_type=plain|"
        "os_task_file_format=json|"
        f"task_adjust_boundary_algorithm={args.boundary_adjust}"
    )
    task = Task(config_string=config)
    task.audio_file_path_absolute = audio_abs
    task.text_file_path_absolute = text_abs

    # aeneas writes its native JSON shape. We catch that to a temp file, then
    # convert.
    tmp_out = tempfile.NamedTemporaryFile(suffix=".aeneas.json", delete=False).name
    task.sync_map_file_path_absolute = tmp_out

    try:
        ExecuteTask(task, rconf=RuntimeConfiguration("tts=espeak-ng|tts_path=/usr/bin/espeak-ng")).execute()
        task.output_sync_map_file()
    except Exception as exc:
        print(f"ERROR: aeneas failed: {exc}", file=sys.stderr)
        try:
            os.remove(tmp_out)
        except OSError:
            pass
        sys.exit(3)

    with open(tmp_out, "r", encoding="utf-8") as fh:
        aeneas_data = json.load(fh)
    os.remove(tmp_out)

    fragments_out = []
    for frag in aeneas_data.get("fragments", []):
        lines = frag.get("lines", [])
        text = " ".join(s.strip() for s in lines if s.strip()).strip()
        if not text:
            continue
        try:
            begin = float(frag["begin"])
            end = float(frag["end"])
        except (KeyError, ValueError, TypeError):
            continue
        if end <= begin:
            continue
        fragments_out.append({
            "begin": round(begin, 3),
            "end": round(end, 3),
            "text": text,
        })

    if not fragments_out:
        print("ERROR: no usable fragments produced. Check the audio/text input.", file=sys.stderr)
        sys.exit(3)

    out = {
        "version": 1,
        "language": args.language,
        "audio_url": args.audio_url or audio_abs,
        "fragments": fragments_out,
    }
    if args.narrator:
        out["narrator"] = args.narrator
    if args.year:
        out["year"] = args.year

    with open(out_abs, "w", encoding="utf-8") as fh:
        json.dump(out, fh, ensure_ascii=False, indent=2)

    dur = fragments_out[-1]["end"]
    minutes, seconds = divmod(int(dur), 60)
    print(f"OK: wrote {len(fragments_out):,} fragments to {out_abs}")
    print(f"    audiobook duration: {minutes}:{seconds:02d}")
    if not args.audio_url:
        print("    WARNING: --audio-url not set. The JSON points to the local file path,")
        print("             which won't work in production. Re-run with --audio-url before shipping.")


if __name__ == "__main__":
    main()
