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
DEBUG = "--debug" in sys.argv


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


PARSE_ERRORS = []
SKIP_LABELS = {"sil", "sp", "spn", "<eps>", "<unk>", "<sil>", ""}


def _entries(d):
    """Find the word-interval list in an MFA json, across output shapes."""
    tiers = d.get("tiers") or d.get("Tiers") or {}
    if isinstance(tiers, dict):
        for k in ("words", "Words", "word", "utterances"):
            t = tiers.get(k)
            if isinstance(t, dict) and t.get("entries"):
                return t["entries"]
            if isinstance(t, list) and t:
                return t
    for k in ("words", "Words"):                 # flat {"words":[...]}
        if isinstance(d.get(k), list) and d[k]:
            return d[k]
    return []


def mfa_words(path):
    """-> [(start, end, label)] from an MFA json. Records why it failed."""
    try:
        d = json.load(open(path, encoding="utf-8"))
    except Exception as ex:
        PARSE_ERRORS.append(f"{os.path.basename(path)}: unreadable ({ex})")
        return []
    out = []
    for e in _entries(d) or []:
        try:
            if isinstance(e, dict):
                st = e.get("begin", e.get("start"))
                en = e.get("end", e.get("stop"))
                lab = e.get("label", e.get("word", e.get("text")))
            else:
                st, en, lab = e[0], e[1], e[2]
            lab = str(lab if lab is not None else "").strip()
            if not lab or lab in SKIP_LABELS:
                continue
            out.append((float(st), float(en), lab))
        except Exception as ex:
            PARSE_ERRORS.append(f"{os.path.basename(path)}: bad entry {e!r} ({ex})")
            return []
    if not out:
        PARSE_ERRORS.append(f"{os.path.basename(path)}: no word intervals found")
    return out


def debug_dump():
    """Show what the aligner actually produced, so a format mismatch is obvious."""
    print(f"\nsegmap: {SEGMAP} {'OK' if os.path.exists(SEGMAP) else 'MISSING'}")
    print(f"segout: {SEGOUT} {'OK' if os.path.isdir(SEGOUT) else 'MISSING'}")
    if not os.path.isdir(SEGOUT):
        print("\nNothing to inspect. Did align_segments.py finish and write here?")
        return
    batches = sorted(d for d in os.listdir(SEGOUT) if os.path.isdir(f"{SEGOUT}/{d}"))
    files = []
    for b in batches:
        fs = sorted(glob.glob(f"{SEGOUT}/{b}/*.json"))
        print(f"  {b}: {len(fs)} json")
        files += fs
    print(f"total aligned json files: {len(files)}")
    if not files:
        print("\n*** segout has no .json files — alignment produced nothing here.")
        return
    p = files[0]
    print(f"\n--- structure of {p} ---")
    try:
        d = json.load(open(p, encoding="utf-8"))
    except Exception as ex:
        print(f"UNREADABLE: {ex}")
        return
    print("top-level keys:", list(d.keys()))
    t = d.get("tiers")
    if isinstance(t, dict):
        print("tiers keys:", list(t.keys()))
        for k, v in t.items():
            if isinstance(v, dict):
                ents = v.get("entries") or []
                print(f"  tiers[{k!r}]: keys={list(v.keys())} entries={len(ents)}")
                for e in ents[:3]:
                    print(f"    {e!r}")
    got = mfa_words(p)
    print(f"\nparsed {len(got)} word intervals; first 3: {got[:3]}")
    if not got:
        print("*** parser found nothing — paste this output and I will fix the parser.")


def sync_word_timings(d):
    """Mirror fragment word times into the top-level word_timings list.

    THIS MATTERS: App.jsx builds its highlight timeline from data.word_timings
    (buildWordTimeline), NOT from fragments[].words[]. Updating only the fragments
    leaves the reader playing against the OLD timings, which looks exactly like
    "alignment ran fine but highlighting is still broken".
    Returns (status, n_updated).
    """
    wt = d.get("word_timings")
    if not isinstance(wt, list) or not wt:
        return "none", 0
    flat = [w for f in d.get("fragments", []) for w in (f.get("words") or [])]
    if len(flat) == len(wt):
        n = 0
        for src, dst in zip(flat, wt):
            if src.get("begin") is not None:
                dst["begin"], dst["end"] = src["begin"], src["end"]
                n += 1
        return "ok", n
    # lengths diverge -> match on normalised text instead of position
    a = [norm(w.get("word")) for w in flat]
    b = [norm(w.get("word")) for w in wt]
    n = 0
    for i, j, k in difflib.SequenceMatcher(a=a, b=b, autojunk=False).get_matching_blocks():
        for x in range(k):
            src = flat[i + x]
            if src.get("begin") is not None:
                wt[j + x]["begin"], wt[j + x]["end"] = src["begin"], src["end"]
                n += 1
    return ("matched" if n else "FAILED"), n


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
if DEBUG:
    debug_dump()
    sys.exit(0)

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

        wt_status, wt_n = sync_word_timings(d) if tot_m else ("skip", 0)
        rate = tot_m / tot_w if tot_w else 0.0
        rows.append((base, len(chapters[base]["segments"]), missing_segs, tot_m, tot_w,
                     rate, wt_status, wt_n))

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
        wt_status, wt_n = sync_word_timings(d) if m else ("skip", 0)
        rows.append((base, 1, 0 if words else 1, m, t, (m / t) if t else 0.0,
                     wt_status, wt_n))
        if WRITE and m:
            json.dump(d, open(tgt, "w", encoding="utf-8"), ensure_ascii=False)
            changed += 1

# ---- report ---------------------------------------------------------------
print(f"\n{'chapter':10} {'segs':>5} {'gaps':>5} {'matched':>8} {'words':>7} {'rate':>7} {'word_timings':>13}  flag")
bad = []
for base, nseg, miss, m, t, rate, wts, wtn in rows:
    flag = ""
    if miss:
        flag = f"{miss} SEGMENT(S) NOT ALIGNED"
    elif rate < DRIFT_AT:
        flag = "LOW MATCH"
    if wts == "FAILED":
        flag = (flag + " " if flag else "") + "WORD_TIMINGS NOT SYNCED"
    if flag:
        bad.append(base)
    wtcol = f"{wts}:{wtn}" if wts not in ("none",) else "none"
    print(f"{base:10} {nseg:5} {miss:5} {m:8} {t:7} {rate:6.1%} {wtcol:>13}  {flag}")

tm = sum(r[3] for r in rows)
tw = sum(r[4] for r in rows)
print(f"\n{len(rows)} chapters, {tm}/{tw} words matched ({(tm/tw if tw else 0):.1%})")
if bad:
    print(f"worth eyeballing in the reader ({len(bad)}): {', '.join(bad[:15])}"
          + (" ..." if len(bad) > 15 else ""))
    print("For a chapter with unaligned segments, re-run that batch:")
    print("  python align_segments.py --only=<batch> --jobs=1 --beam=100 --retry-beam=400")

if PARSE_ERRORS:
    uniq = []
    for e in PARSE_ERRORS:
        tag = e.split(":", 1)[1].strip()
        if tag not in uniq:
            uniq.append(tag)
    print(f"\n{len(PARSE_ERRORS)} aligned file(s) yielded no usable words. Distinct reasons:")
    for u in uniq[:5]:
        print(f"  - {u}")

if tm == 0:
    print("\n" + "=" * 68)
    print("NOTHING WAS APPLIED — every chapter matched 0 words.")
    print("The app JSONs are untouched; this is not a partial write.")
    print("Diagnose with:   python apply_timings.py --debug")
    print("That prints what the aligner actually wrote, so a format or path")
    print("mismatch is obvious. Nothing is changed until this reads > 0.")
    print("=" * 68)
elif WRITE:
    print(f"\nrewrote {changed} files "
          f"(fragments[].words[] AND word_timings — the reader uses the latter)")
else:
    print("\nDry run only. Re-run with --write to apply.")
