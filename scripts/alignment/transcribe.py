#!/usr/bin/env python3
"""Transcribe audio with faster-whisper. Output: words+timestamps JSON."""
import argparse, json, re, time, sys
from faster_whisper import WhisperModel

def normalize(w):
    return re.sub(r'[^\wа-яёА-ЯЁa-zA-Z0-9]', '', w, flags=re.UNICODE).lower()

def main():
    p = argparse.ArgumentParser()
    p.add_argument("--audio", required=True)
    p.add_argument("--output", required=True)
    p.add_argument("--model", default="small", help="tiny | base | small | medium | large")
    p.add_argument("--language", default="ru")
    p.add_argument("--compute-type", default="int8")
    args = p.parse_args()

    print(f"[transcribe] {args.audio} model={args.model} lang={args.language}", file=sys.stderr)
    t0 = time.time()
    model = WhisperModel(args.model, device="cpu", compute_type=args.compute_type)
    segments, info = model.transcribe(
        args.audio, language=args.language,
        word_timestamps=True, beam_size=5, vad_filter=True,
    )
    words = []
    for seg in segments:
        for w in seg.words:
            n = normalize(w.word)
            if n:
                words.append({
                    "text": n,
                    "raw": w.word.strip(),
                    "start": round(w.start, 3),
                    "end": round(w.end, 3),
                })
    elapsed = time.time() - t0

    output = {
        "audio": args.audio,
        "model": args.model,
        "language": args.language,
        "duration": getattr(info, "duration", None),
        "elapsed_seconds": round(elapsed, 1),
        "word_count": len(words),
        "words": words,
    }
    with open(args.output, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)
    print(f"[transcribe] {len(words)} words in {elapsed:.0f}s → {args.output}", file=sys.stderr)

if __name__ == "__main__":
    main()
