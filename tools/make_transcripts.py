#!/usr/bin/env python3
"""
make_transcripts.py — turn the audiobooks in R2 into the word-timing transcript
JSONs that govorim-app's reader expects.

Same script as the one that made the 19 books already in the app. The only
change: it knows the six remaining books by name and fetches their audio from
the public r2.dev URLs itself, so there is no manifest to pass and no R2
credentials anywhere.

Install (once):
    pip install -U whisperx
    # WhisperX pulls in faster-whisper + torch. With an NVIDIA GPU install a
    # CUDA torch build first, e.g.
    #   pip install torch torchaudio --index-url https://download.pytorch.org/whl/cu121

Run (one command per book):
    python make_transcripts.py --book dyadya-vanya
    python make_transcripts.py --book vishnevy-sad
    python make_transcripts.py --book chaika-1946
    python make_transcripts.py --book prestuplenie
    python make_transcripts.py --book anna-karenina
    python make_transcripts.py --book voina-i-mir

It is resumable: chapters whose output JSON already exists are skipped, so you
can stop it and restart at any time. On a modern GPU with large-v3, roughly
real-time / 10 — Дядя Ваня is minutes, Crime & Punishment about an hour and a
half, War & Peace five or six. On CPU, days. Start with Дядя Ваня.

Output shape (matches every existing file under public/books/audio/):

    {
      "audio_url": "https://pub-....r2.dev/pn/001.mp3",
      "narrator": "audiobook",
      "fragments": [
        {"text": "...", "begin": 3.372, "end": 6.213,
         "words": [{"word": "...", "begin": 3.372, "end": 3.932}, ...]},
        ...
      ],
      "word_timings": [{"word": "...", "begin": 3.372, "end": 3.932}, ...]
    }
"""

import argparse
import gc
import json
import os
import sys
import time
import urllib.request

MODEL = "large-v3"
LANG = "ru"
PUBLIC = "https://pub-84adcd23e17e4925a0ac7eca17ea2556.r2.dev"

# Anna Karenina chapter 1 is stored under a different object name than the rest
# of the book (it was re-uploaded after a cleanup pass). Everything else in the
# folder is NN.mp3. The output stem is normalised back to "01" below so the
# chapter numbering in public/books/audio/ stays contiguous.
_AK = [f"anna-karenina/{i:02d}.mp3" for i in range(1, 240)]
_AK[0] = "anna-karenina/01-cleaned.mp3"

# book -> (r2 keys, default output folder under public/books/audio/)
BOOKS = {
    "dyadya-vanya":    (["dyadya-vanya/dyadya-vanya-full.mp3"],       "dyadya-vanya"),
    "vishnevy-sad":    (["vishnevy-sad-full/vishnevy-sad-full.mp3"],  "vishnevy-sad-full"),
    "chaika-1946":     (["chaika-1946/chaika-1946-full.mp3"],         "chaika-1946"),
    "moskva-petushki": (["mp/full.mp3"],                              "mp"),
    "prestuplenie":    ([f"pn/{i:03d}.mp3"  for i in range(1, 42)],   "pn"),
    "voina-i-mir":     ([f"vim/{i:03d}.mp3" for i in range(1, 363)],  "vim"),
    "anna-karenina":   (_AK,                                          "ak_mfa"),
}


def parse_range(spec, n):
    """'5' -> {5}; '1-120' -> {1..120}; '1,4,9-11' -> {1,4,9,10,11}.
    Chapter numbers are 1-based positions in the book's key list."""
    want = set()
    for part in spec.split(","):
        part = part.strip()
        if not part:
            continue
        if "-" in part.lstrip("-"):
            lo, hi = part.split("-", 1)
            lo, hi = int(lo), int(hi)
            if lo > hi:
                raise ValueError(f"bad range {part!r}: {lo} > {hi}")
            want.update(range(lo, hi + 1))
        else:
            want.add(int(part))
    bad = sorted(x for x in want if x < 1 or x > n)
    if bad:
        raise ValueError(f"chapter(s) out of range 1-{n}: {bad}")
    return want


def fetch(url, dst):
    """Download once, resume-safe: a finished file is never re-fetched."""
    if os.path.exists(dst) and os.path.getsize(dst) > 0:
        return dst
    os.makedirs(os.path.dirname(dst), exist_ok=True)
    tmp = dst + ".part"
    with urllib.request.urlopen(url) as r, open(tmp, "wb") as f:
        while True:
            chunk = r.read(1 << 20)
            if not chunk:
                break
            f.write(chunk)
    os.replace(tmp, dst)
    return dst


def fix_word_times(words, seg_start, seg_end):
    """WhisperX occasionally emits a word with no start/end (numerals, symbols).
    Fill those in by linear interpolation so timings stay monotonic — the
    reader's highlighter assumes non-decreasing begin values."""
    out = []
    for w in words:
        out.append({
            "word": (w.get("word") or "").strip(),
            "begin": w.get("start"),
            "end": w.get("end"),
        })
    out = [w for w in out if w["word"]]
    if not out:
        return []
    n = len(out)
    if out[0]["begin"] is None:
        out[0]["begin"] = seg_start
    if out[-1]["end"] is None:
        out[-1]["end"] = seg_end
    for i in range(n):
        if out[i]["begin"] is None:
            prev = out[i - 1]["end"] if i and out[i - 1]["end"] is not None else out[i - 1]["begin"]
            nxt, j = None, i + 1
            while j < n:
                if out[j]["begin"] is not None:
                    nxt = out[j]["begin"]
                    break
                j += 1
            if prev is None:
                prev = seg_start
            if nxt is None:
                nxt = seg_end
            span = max(0.0, nxt - prev)
            out[i]["begin"] = round(prev + span * (1.0 / (j - i + 1)), 3)
        if out[i]["end"] is None:
            nb = out[i + 1]["begin"] if i + 1 < n and out[i + 1]["begin"] is not None else seg_end
            out[i]["end"] = round(max(out[i]["begin"], nb), 3)
    for i in range(1, n):
        if out[i]["begin"] < out[i - 1]["begin"]:
            out[i]["begin"] = out[i - 1]["begin"]
        if out[i]["end"] < out[i]["begin"]:
            out[i]["end"] = out[i]["begin"]
    for w in out:
        w["begin"] = round(float(w["begin"]), 3)
        w["end"] = round(float(w["end"]), 3)
    return out


def build_json(result, audio_url, narrator):
    fragments, word_timings = [], []
    for seg in result.get("segments", []):
        text = (seg.get("text") or "").strip()
        if not text:
            continue
        ws = fix_word_times(seg.get("words") or [], seg.get("start", 0.0), seg.get("end", 0.0))
        if not ws:
            continue
        fragments.append({
            "text": text,
            "begin": ws[0]["begin"],
            "end": ws[-1]["end"],
            "words": ws,
        })
        word_timings.extend([dict(w) for w in ws])
    return {
        "audio_url": audio_url,
        "narrator": narrator,
        "fragments": fragments,
        "word_timings": word_timings,
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--book", required=True, choices=sorted(BOOKS))
    ap.add_argument("--out", default=None, help="output folder (default public/books/audio/<book>)")
    ap.add_argument("--audio", default="audio", help="where to cache the downloaded mp3s")
    ap.add_argument("--narrator", default="audiobook")
    ap.add_argument("--device", default=None, help="cuda or cpu (auto-detected)")
    ap.add_argument("--model", default=MODEL)
    ap.add_argument("--batch-size", type=int, default=16)
    ap.add_argument("--only", default=None, help="comma-separated chapter numbers, e.g. 1,2,3")
    ap.add_argument("--range", dest="rng", default=None,
                    help="chapter range for splitting a book across pods, e.g. 1-120 or 1,4,9-11")
    args = ap.parse_args()

    import torch
    import whisperx

    keys, folder = BOOKS[args.book]
    out = args.out or os.path.join("public", "books", "audio", folder)
    cache = os.path.join(args.audio, args.book)

    spec = args.rng or args.only
    if spec:
        want = parse_range(spec, len(keys))
        keys = [k for i, k in enumerate(keys, 1) if i in want]
        if not keys:
            sys.exit(f"no chapters selected by {spec!r}")

    device = args.device or ("cuda" if torch.cuda.is_available() else "cpu")
    compute_type = "float16" if device == "cuda" else "int8"
    print(f"{args.book}: {len(keys)} chapters -> {out}")
    print(f"device={device} compute_type={compute_type} model={args.model}")

    os.makedirs(out, exist_ok=True)

    asr = whisperx.load_model(args.model, device, compute_type=compute_type, language=LANG)
    align_model, align_meta = whisperx.load_align_model(language_code=LANG, device=device)

    def transcribe(audio):
        """whisperx changed transcribe()'s signature across releases: some builds
        take language=, some reject it because the model is already language-bound
        by load_model(). Try the richer call, fall back rather than dying."""
        try:
            return asr.transcribe(audio, batch_size=args.batch_size, language=LANG)
        except TypeError:
            return asr.transcribe(audio, batch_size=args.batch_size)

    t0 = time.time()
    done = skipped = failed = 0
    audio_secs = 0.0
    for n, key in enumerate(keys, 1):
        stem = os.path.splitext(os.path.basename(key))[0]
        stem = stem.replace("-cleaned", "")        # 01-cleaned -> 01
        dst = os.path.join(out, stem + ".json")
        if os.path.exists(dst):
            skipped += 1
            continue
        url = f"{PUBLIC}/{key}"
        print(f"[{n}/{len(keys)}] {stem}", flush=True)
        c0 = time.time()
        try:
            src = fetch(url, os.path.join(cache, os.path.basename(key)))
            audio = whisperx.load_audio(src)
            secs = len(audio) / 16000.0
            res = transcribe(audio)
            res = whisperx.align(res["segments"], align_model, align_meta, audio, device,
                                 return_char_alignments=False)
            js = build_json(res, url, args.narrator)
            if not js["word_timings"]:
                raise RuntimeError("no words produced")
            tmp = dst + ".part"
            with open(tmp, "w", encoding="utf-8") as f:
                json.dump(js, f, ensure_ascii=False)
            os.replace(tmp, dst)                   # never leave a half-written json
            took = time.time() - c0
            audio_secs += secs
            done += 1
            rate = (secs / took) if took else 0.0
            elapsed = time.time() - t0
            remaining = len(keys) - n
            eta = (elapsed / done * remaining / 60.0) if done else 0.0
            print(f"      {len(js['fragments'])} fragments, {len(js['word_timings'])} words | "
                  f"{secs/60:.1f} min audio in {took/60:.1f} min ({rate:.1f}x realtime) | "
                  f"eta {eta:.0f} min", flush=True)
        except Exception as e:                             # noqa: BLE001
            print(f"      FAILED: {e}", flush=True)
            failed += 1
        finally:
            gc.collect()
            if device == "cuda":
                torch.cuda.empty_cache()

    mins = (time.time() - t0) / 60.0
    print(f"\ndone={done} skipped={skipped} failed={failed} "
          f"in {mins:.1f} min ({audio_secs/3600:.1f} h of audio)", flush=True)
    if failed:
        sys.exit(1)


if __name__ == "__main__":
    main()
