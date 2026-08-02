#!/usr/bin/env python3
"""
apply_timings.py — fold MFA word timings back into the app's audio JSONs.

Two modes, picked automatically:

  SEGMENT MODE (used when $WP/segmap.json exists — the split_corpus.py flow)
    Reads $WP/segout/<batch>/<chapter>_pNNN.json, adds each segment's offset back
    on, and maps the words onto that segment's OWN fragment range. Because every
    segment is anchored independently, a hiccup in one 30-second piece cannot
    drift the rest of the chapter.

  FLAT MODE (fallback: $WP/out/NNN.json, one aligned file per chapter)

Matching is text-aware, not blindly positional: app tokens and MFA tokens are
normalised (lowercase, ё→е, punctuation stripped) and lined up with
difflib.SequenceMatcher. Tokens the app has but MFA doesn't emit — dashes,
stray punctuation "words" — get interpolated from their neighbours instead of
shoving everything after them out of sync.

USAGE
  python apply_timings.py            # dry run: per-chapter match rates
  python apply_timings.py --write    # apply (backs up the folder first)
  python apply_timings.py --write --only=001,002

ENV: REPO, WP  (optional: AUDIO_JSON_DIR)
"""
import difflib
import glob
import json
import os
import re
import shutil
import sys

REPO = os.environ.get("REPO", "")
WP = os.environ.get("WP", "")
if not REPO or not WP:
    sys.exit("ERROR: export REPO and WP first")

JSON_DIR = os.environ.get("AUDIO_JSON_DIR", f"{REPO}/public/books/audio/vim")
SEGMAP = f"{WP}/segmap.json"
SEGOUT = f"{WP}/segout"
FLATOUT = f"{WP}/out"

WRITE = "--write" in sys.argv


def opt(name, default):
    for a in sys.argv[1:]:
        if a.startswith(f"--{name}="):
            return a.split("=", 1)[1]
    return default


ONLY = opt("only", "")
only_set = {x.strip() for x in ONLY.split(",") if x.strip()} if ONLY else None
DRIFT_AT = float(opt("drift-at", 0.90))     # flag chapters below this match rate

PUNCT = re.compile(r"[^0-9a-zA-Zа-яА-ЯёЁ]+")


def norm(tok):
    return PUNCT.sub("", (tok or "").lower().replace("ё", "е"))


def mfa_words(path):
    """-> [(start, end, label)] from an MFA json, tolerant of tier naming."""
    try:
        d = json.load(open(path, encoding="utf-8"))
    except Exception:
        return []
    tiers = d.get("tiers", {}) or {}
    w = tiers.get("words") or tiers.get("Words") or {}
    out = []
    for e in w.get("entries", []) or []:
        if isinstance(e, dict):
            s, t, lab = e.get("begin"), e.get("end"), e.get("label")
        else:
            s, t, lab = e[0], e[1], e[2]
        lab = str(lab or "").strip()
        if not lab or lab in {"sil", "sp", "spn", "<eps>", "<unk>"}:
            continue
        out.append((float(s), float(t), lab))
    return out


def assign(app_words, mfa, lo_time, hi_time):
    """Map MFA intervals onto app word dicts. Returns (n_matched, n_total).

    app_words: list of dicts with 'word' (mutated in place)
    mfa: list of (start, end, label) already offset into chapter time
    lo_time/hi_time: fallback bounds for interpolation at the edges
    """
    if not app_words:
        return 0, 0
    if not mfa:
        return 0, len(app_words)

    a = [norm(w.get("word")) for w in app_words]
    b = [norm(lab) for (_, _, lab) in mfa]

    times = [None] * len(app_words)
    sm = difflib.SequenceMatcher(a=a, b=b, autojunk=False)
    matched = 0
    for i, j, n in sm.get_matching_blocks():
        for k in range(n):
            if not a[i + k]:          # punctuation-only app token: interpolate
                continue
            times[i + k] = (mfa[j + k][0], mfa[j + k][1])
            matched += 1

    # interpolate anything left over from its nearest anchored neighbours
    n = len(times)
    i = 0
    while i < n:
        if times[i] is not None:
            i += 1
            continue
        j = i
        while j < n and times[j] is None:
            j += 1
        has_left = i > 0 and times[i - 1] is not None
        has_right = j < n and times[j] is not None
        left = times[i - 1][1] if has_left else lo_time
        right = times[j][0] if has_right else hi_time
        # lo_time/hi_time are the OLD (pre-alignment) fragment bounds, so they can
        # sit on the wrong side of a freshly aligned neighbour. Trust the real
        # anchor and clamp the stale one — otherwise a leading "—" lands after the
        # word it precedes and the whole segment reads as non-monotonic.
        if right < left:
            if has_right:
                left = right
            else:
                right = left
        gap = (right - left) / float(j - i + 1)
        for k in range(i, j):
            s = left + gap * (k - i)
            times[k] = (s, s + gap)
        i = j

    for w, t in zip(app_words, times):
        w["begin"], w["end"] = round(t[0], 3), round(t[1], 3)
    return matched, len(app_words)


# ---------------------------------------------------------------------------
segmented = os.path.exists(SEGMAP) and os.path.isdir(SEGOUT)
print(f"mode: {'SEGMENT' if segmented else 'FLAT'}")
print(f"transcripts: {JSON_DIR}")

if WRITE:
    bak = JSON_DIR.rstrip("/") + ".bak"
    if not os.path.exists(bak):
        shutil.copytree(JSON_DIR, bak)
        print(f"backup created: {bak}")
    else:
        print(f"backup already present: {bak}")

rows = []
changed = 0

if segmented:
    segmap = json.load(open(SEGMAP, encoding="utf-8"))
    chapters = segmap["chapters"]
    keys = sorted(chapters)
    if only_set:
        keys = [k for k in keys if k in only_set]

    for base in keys:
        tgt = f"{JSON_DIR}/{base}.json"
        if not os.path.exists(tgt):
            continue
        d = json.load(open(tgt, encoding="utf-8"))
        # split_corpus.py indexed the NON-EMPTY fragments — reproduce that view
        frs = [f for f in d.get("fragments", []) if (f.get("text") or "").strip()]

        tot_m = tot_w = 0
        missing_segs = 0
        for seg in chapters[base]["segments"]:
            mp = f"{SEGOUT}/{seg['batch']}/{seg['id']}.json"
            words = mfa_words(mp)
            if not words:
                missing_segs += 1
                tot_w += seg.get("app_words", 0)
                continue
            off = seg["offset"]
            words = [(s + off, e + off, lab) for (s, e, lab) in words]

            span = frs[seg["frag_start"]:seg["frag_end"] + 1]
            app_words = [w for f in span for w in (f.get("words") or [])]
            lo = span[0].get("begin", off) if span else off
            hi = span[-1].get("end", off) if span else off
            m, t = assign(app_words, words, lo, hi)
            tot_m += m
            tot_w += t

        # refresh fragment-level bounds from their words
        for f in frs:
            ws = f.get("words") or []
            if ws:
                f["begin"], f["end"] = ws[0]["begin"], ws[-1]["end"]

        rate = tot_m / tot_w if tot_w else 0.0
        rows.append((base, len(chapters[base]["segments"]), missing_segs, tot_m, tot_w, rate))

        if WRITE and tot_m:
            json.dump(d, open(tgt, "w", encoding="utf-8"), ensure_ascii=False)
            changed += 1

else:
    files = sorted(glob.glob(f"{FLATOUT}/*.json"))
    for mp in files:
        base = os.path.splitext(os.path.basename(mp))[0]
        if only_set and base not in only_set:
            continue
        tgt = f"{JSON_DIR}/{base}.json"
        if not os.path.exists(tgt):
            continue
        d = json.load(open(tgt, encoding="utf-8"))
        frs = [f for f in d.get("fragments", []) if (f.get("text") or "").strip()]
        app_words = [w for f in frs for w in (f.get("words") or [])]
        words = mfa_words(mp)
        lo = frs[0].get("begin", 0.0) if frs else 0.0
        hi = frs[-1].get("end", 0.0) if frs else 0.0
        m, t = assign(app_words, words, lo, hi)
        for f in frs:
            ws = f.get("words") or []
            if ws:
                f["begin"], f["end"] = ws[0]["begin"], ws[-1]["end"]
        rows.append((base, 1, 0 if words else 1, m, t, (m / t) if t else 0.0))
        if WRITE and m:
            json.dump(d, open(tgt, "w", encoding="utf-8"), ensure_ascii=False)
            changed += 1

# ---- report ---------------------------------------------------------------
print(f"\n{'chapter':10} {'segs':>5} {'gaps':>5} {'matched':>8} {'words':>7} {'rate':>7}  flag")
bad = []
for base, nseg, miss, m, t, rate in rows:
    flag = ""
    if miss:
        flag = f"{miss} SEGMENT(S) NOT ALIGNED"
    elif rate < DRIFT_AT:
        flag = "LOW MATCH"
    if flag:
        bad.append(base)
    print(f"{base:10} {nseg:5} {miss:5} {m:8} {t:7} {rate:6.1%}  {flag}")

tm = sum(r[3] for r in rows)
tw = sum(r[4] for r in rows)
print(f"\n{len(rows)} chapters, {tm}/{tw} words matched ({(tm/tw if tw else 0):.1%})")
if bad:
    print(f"worth eyeballing in the reader ({len(bad)}): {', '.join(bad[:15])}"
          + (" ..." if len(bad) > 15 else ""))
    print("For a chapter with unaligned segments, re-run that batch:")
    print("  python align_segments.py --only=<batch> --jobs=1 --beam=100 --retry-beam=400")

print(f"\nrewrote {changed} files" if WRITE
      else "\nDry run only. Re-run with --write to apply.")
