#!/usr/bin/env python3
"""End-to-end alignment for one chapter.
Caches Whisper transcript so re-aligning is instant after first run."""
import argparse, os, subprocess, sys

def main():
    p = argparse.ArgumentParser()
    p.add_argument("--audio", required=True)
    p.add_argument("--text", required=True)
    p.add_argument("--output", required=True)
    p.add_argument("--audio-url", required=True)
    p.add_argument("--narrator", default="")
    p.add_argument("--model", default="small")
    p.add_argument("--force-transcribe", action="store_true")
    args = p.parse_args()

    here = os.path.dirname(os.path.abspath(__file__))
    cache_dir = os.path.join(here, "cache")
    os.makedirs(cache_dir, exist_ok=True)

    audio_key = os.path.splitext(os.path.basename(args.audio))[0]
    words_json = os.path.join(cache_dir, f"{audio_key}.{args.model}.words.json")

    if os.path.exists(words_json) and not args.force_transcribe:
        print(f"[run] cached: {words_json}", file=sys.stderr)
    else:
        rc = subprocess.run([sys.executable, os.path.join(here, "transcribe.py"),
                             "--audio", args.audio, "--output", words_json,
                             "--model", args.model]).returncode
        if rc: sys.exit(rc)

    rc = subprocess.run([sys.executable, os.path.join(here, "align.py"),
                         "--text", args.text, "--words", words_json,
                         "--output", args.output,
                         "--audio-url", args.audio_url,
                         "--narrator", args.narrator]).returncode
    if rc: sys.exit(rc)
    print(f"[run] ✓ {args.output}", file=sys.stderr)

if __name__ == "__main__":
    main()
