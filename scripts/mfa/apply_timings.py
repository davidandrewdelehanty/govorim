#!/usr/bin/env python3
"""
Fold MFA word timings (from `mfa align --output_format json`) back into the app's
audio/vim/NNN.json files. Positional map onto existing fragments[].words[].

  python apply_timings.py            # dry run: report per-chapter word counts
  python apply_timings.py --write     # rewrite the vim JSONs in place

Back up first:  cp -r "$REPO/public/books/audio/vim"{,.bak}
Reads env vars: REPO, WP
"""
import json, glob, os, sys
REPO = os.environ["REPO"]; WP = os.environ["WP"]
WRITE = "--write" in sys.argv

def mfa_words(p):
    d = json.load(open(p))
    tiers = d.get("tiers", {})
    w = tiers.get("words") or tiers.get("Words") or {}
    out = []
    for e in w.get("entries", []):
        start, end, label = e[0], e[1], e[2]
        if str(label).strip():
            out.append((float(start), float(end)))
    return out

changed = 0
for mp in sorted(glob.glob(f"{WP}/out/*.json")):
    base = os.path.splitext(os.path.basename(mp))[0]
    tgt = f"{REPO}/public/books/audio/vim/{base}.json"
    if not os.path.exists(tgt):
        continue
    words = mfa_words(mp)
    d = json.load(open(tgt))
    have = sum(len(fr.get("words", [])) for fr in d.get("fragments", []))
    print(f"{base}: mfa={len(words):5}  app_word_slots={have:5}  {'OK' if abs(len(words)-have)<=3 else 'DRIFT'}")
    if not WRITE:
        continue
    i = 0
    for fr in d.get("fragments", []):
        for wd in fr.get("words", []):
            if i < len(words):
                wd["begin"], wd["end"] = round(words[i][0], 3), round(words[i][1], 3)
                i += 1
        if fr.get("words"):
            fr["begin"] = fr["words"][0]["begin"]; fr["end"] = fr["words"][-1]["end"]
    json.dump(d, open(tgt, "w", encoding="utf-8"), ensure_ascii=False)
    changed += 1
print(("\nrewrote %d files" % changed) if WRITE else "\nDry run only. Re-run with --write to apply.")
