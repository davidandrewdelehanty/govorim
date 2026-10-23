"""Drop exercises whose blank is a NOUN that the dictionary also reads as another part of speech (verb, adverb, short adjective, ...).

The case courses do this inside case_explain.rewrite; this is the same rule for every other course.
A blank counts as a noun when its hint is a noun lemma (the hint's own top reading is NOUN) and the answer is a NOUN form of it.
Needs pymorphy3.  Usage: pos_guard.py [--apply] [--course ID]
"""
import argparse, io, json, os, re, sys
from collections import Counter

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
COURSES = os.path.join(ROOT, "public", "courses")
CASE_COURSES = {"cases", "case-nom", "case-gen", "case-dat", "case-acc", "case-ins", "case-prp"}   # case_explain handles these
WORD = re.compile(r"[А-Яа-яЁё]+(?:-[А-Яа-яЁё]+)?")
HINT = re.compile(r"___ \(([^)]*)\)")


def _norm(w):
    return w.lower().replace("ё", "е")


def other_pos(M, e):
    """{answer word: [other POS]} for the noun words of this exercise, or None."""
    m = HINT.search(e.get("q") or "")
    if not m:
        return None
    hint = re.sub(r",\s*(nom|gen|dat|acc|instr|prep)\.\s*(sg|pl)\.(\s*[mfn]\.)?(\s*— word has no singular)?\s*$", "", m.group(1).strip())
    if re.search(r"\d|[A-Za-z+/·]", hint):
        return None
    ans = (e.get("answers") or [""])[0]
    hw, aw = WORD.findall(hint), WORD.findall(ans)
    if not aw or len(hw) != len(aw):
        return None
    hits = {}
    for h, a in zip(hw, aw):
        hp = M.parse(h)
        if not hp or hp[0].tag.POS != "NOUN":
            continue
        lemmas = {_norm(hp[0].normal_form), _norm(h)}
        ps = M.parse(a)
        if not any(p.tag.POS == "NOUN" and _norm(p.normal_form) in lemmas for p in ps):
            continue
        o = sorted({p.tag.POS or "?" for p in ps if p.tag.POS != "NOUN"})
        if o:
            hits[a] = o
    return hits or None


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true")
    ap.add_argument("--course")
    a = ap.parse_args(argv)
    import pymorphy3
    M = pymorphy3.MorphAnalyzer()
    st, by, ex = Counter(), Counter(), {}
    for cid in sorted(os.listdir(COURSES)):
        d = os.path.join(COURSES, cid)
        if cid in CASE_COURSES or cid.startswith("_") or not os.path.isdir(d) or (a.course and cid != a.course):
            continue
        for fn in sorted(os.listdir(d)):
            if not fn.endswith(".json") or fn == "exam.json":
                continue
            p = os.path.join(d, fn)
            doc = json.load(io.open(p, encoding="utf-8"))
            keep = []
            for e in doc.get("exercises") or []:
                h = other_pos(M, e) if e.get("type") == "fill" else None
                st[cid + ":checked"] += 1 if e.get("type") == "fill" else 0
                if h:
                    st[cid + ":drop"] += 1
                    for pos in {x for v in h.values() for x in v}:
                        by[pos] += 1
                    ex.setdefault(cid, []).append((list(h), e["q"][:80]))
                    continue
                keep.append(e)
            if a.apply and len(keep) != len(doc.get("exercises") or []):
                doc["exercises"] = keep
                io.open(p, "w", encoding="utf-8").write(json.dumps(doc, ensure_ascii=False))
    print("pos_guard:", dict(st))
    if not a.apply or True:
        print(dict(by))
        for cid, v in ex.items():
            print(cid, len(v))
            for x in v[:5]:
                print("    ", x)


if __name__ == "__main__":
    main()
