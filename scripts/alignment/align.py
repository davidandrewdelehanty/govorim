#!/usr/bin/env python3
"""Sequence-align chapter text to a Whisper transcript.

Algorithm: Longest Common Subsequence (via difflib.SequenceMatcher) at the
word level. Every text line gets a begin/end and a confidence label:

  high          ≥ 60% of the line's words aligned to a transcript word
  medium        30-60% aligned
  low           < 30% aligned (one anchor word)
  interpolated  no words aligned; timing inferred linearly between anchors
  none          chapter has zero aligned anchors anywhere (degenerate)
"""
import argparse, json, re, sys

def normalize(w):
    return re.sub(r'[^\wа-яёА-ЯЁa-zA-Z0-9]', '', w, flags=re.UNICODE).lower()

def tokenize(line):
    return [n for n in (normalize(w) for w in line.split()) if n]

def align(lines, words):
    import difflib
    text_words = []
    line_ranges = []
    for line in lines:
        start = len(text_words)
        text_words.extend(tokenize(line))
        line_ranges.append((start, len(text_words)))

    if not text_words or not words:
        return [{"begin": 0.0, "end": 0.0, "text": l, "confidence": "none"} for l in lines]

    trans_tokens = [w["text"] for w in words]
    sm = difflib.SequenceMatcher(None, text_words, trans_tokens, autojunk=False)
    text_to_trans = [None] * len(text_words)
    for tag, i1, i2, j1, j2 in sm.get_opcodes():
        if tag == "equal":
            for k in range(i2 - i1):
                text_to_trans[i1 + k] = j1 + k

    aligned_words = sum(1 for x in text_to_trans if x is not None)
    print(f"[align] word-level: {aligned_words}/{len(text_words)} ({100*aligned_words/max(1,len(text_words)):.1f}%)",
          file=sys.stderr)

    # Per-line start time + confidence
    line_info = []
    for (s, e) in line_ranges:
        if s >= e:
            line_info.append(None)
            continue
        first_trans_idx = next((text_to_trans[ti] for ti in range(s, e) if text_to_trans[ti] is not None), None)
        if first_trans_idx is None:
            line_info.append(None)
            continue
        matched = sum(1 for ti in range(s, e) if text_to_trans[ti] is not None)
        line_info.append({
            "begin": words[first_trans_idx]["start"],
            "ratio": matched / (e - s),
        })

    anchors = [(i, li["begin"]) for i, li in enumerate(line_info) if li is not None]

    if not anchors:
        total = words[-1]["end"] if words else 0
        per = total / max(1, len(lines))
        return [{"begin": round(i * per, 3), "end": round((i + 1) * per, 3),
                 "text": lines[i], "confidence": "none"} for i in range(len(lines))]

    # Average pace, used for extrapolation at boundaries
    if len(anchors) >= 2:
        pace = (anchors[-1][1] - anchors[0][1]) / max(1, anchors[-1][0] - anchors[0][0])
    else:
        pace = 1.0

    begins = [None] * len(lines)
    confs = [None] * len(lines)
    for i in range(len(lines)):
        if line_info[i] is not None:
            begins[i] = line_info[i]["begin"]
            r = line_info[i]["ratio"]
            confs[i] = "high" if r >= 0.6 else ("medium" if r >= 0.3 else "low")
        else:
            prev_a = next(((ai, at) for ai, at in reversed(anchors) if ai < i), None)
            next_a = next(((ai, at) for ai, at in anchors if ai > i), None)
            if prev_a and next_a:
                t = (i - prev_a[0]) / (next_a[0] - prev_a[0])
                begins[i] = prev_a[1] + t * (next_a[1] - prev_a[1])
            elif prev_a:
                begins[i] = prev_a[1] + (i - prev_a[0]) * pace
            elif next_a:
                begins[i] = max(0.0, next_a[1] - (next_a[0] - i) * pace)
            else:
                begins[i] = 0.0
            confs[i] = "interpolated"

    # Enforce monotonicity (interpolation can drift if anchors are out of order)
    for i in range(1, len(begins)):
        if begins[i] < begins[i - 1]:
            begins[i] = begins[i - 1] + 0.001

    last_word_end = words[-1]["end"]
    fragments = []
    for i, line in enumerate(lines):
        b = round(begins[i], 3)
        e = round(begins[i + 1] if i + 1 < len(lines) else last_word_end, 3)
        if e <= b:
            e = round(b + 0.5, 3)
        fragments.append({"begin": b, "end": e, "text": line, "confidence": confs[i]})
    return fragments

def main():
    p = argparse.ArgumentParser()
    p.add_argument("--text", required=True)
    p.add_argument("--words", required=True)
    p.add_argument("--output", required=True)
    p.add_argument("--audio-url", default="")
    p.add_argument("--narrator", default="")
    args = p.parse_args()

    with open(args.text, encoding="utf-8") as f:
        lines = [l.strip() for l in f if l.strip()]
    with open(args.words, encoding="utf-8") as f:
        transcript = json.load(f)
    words = transcript["words"]

    print(f"[align] {len(lines)} lines vs {len(words)} words", file=sys.stderr)
    fragments = align(lines, words)

    counts = {}
    for f in fragments:
        counts[f["confidence"]] = counts.get(f["confidence"], 0) + 1
    print("[align] coverage:", file=sys.stderr)
    for k in ("high", "medium", "low", "interpolated", "none"):
        if k in counts:
            print(f"  {k:14s} {counts[k]:3d}  ({100*counts[k]/len(fragments):5.1f}%)", file=sys.stderr)

    out = {
        "audio_url": args.audio_url,
        "narrator": args.narrator,
        "fragments": fragments,
    }
    with open(args.output, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=2)
    print(f"[align] → {args.output}", file=sys.stderr)

if __name__ == "__main__":
    main()
