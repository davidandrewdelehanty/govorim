"""Dry-run / apply: find noun answers in the case courses that ANY dictionary reading also gives as another part of speech."""
import io, json, os, re, sys
from collections import Counter
import case_explain as C
M = C.M
WORD = C.WORD
OTHER_OK = set()            # POS values that do not count as "another part of speech"
def other_pos(word, lemma):
    """POS tags (other than NOUN) of any reading of the exact word form; only when the word is a NOUN form of the hinted lemma."""
    ps = M.parse(word)
    if not any(p.tag.POS == "NOUN" and C.norm(p.normal_form) in ({C.norm(lemma)} | {C.norm(x.normal_form) for x in M.parse(lemma)}) for p in ps):
        return None
    return sorted({p.tag.POS or "?" for p in ps if p.tag.POS != "NOUN" and p.tag.POS not in OTHER_OK})
def check(e):
    q = e.get("q") or ""
    m = re.search(r"___ \(([^)]*)\)", q)
    if not m: return None
    hint = re.sub(r",\s*(nom|gen|dat|acc|instr|prep)\.\s*(sg|pl)\.(\s*[mfn]\.)?(\s*— word has no singular)?\s*$", "", m.group(1).strip())
    ans = (e.get("answers") or [""])[0]
    hw, aw = WORD.findall(hint), WORD.findall(ans)
    if not aw or len(hw) != len(aw): return None
    hits = {}
    for h, a in zip(hw, aw):
        o = other_pos(a, h)
        if o: hits[a] = o
    return hits or None
if __name__ == "__main__":
    apply = "--apply" in sys.argv
    st, by, ex = Counter(), Counter(), {}
    for cid in C.CASE_COURSES:
        d = os.path.join(C.COURSES, cid)
        for fn in sorted(os.listdir(d)):
            if not fn.endswith(".json") or fn == "exam.json": continue
            p = os.path.join(d, fn); doc = json.load(io.open(p, encoding="utf-8"))
            keep = []
            for e in doc.get("exercises") or []:
                if e.get("type") != "fill": keep.append(e); continue
                st["fill"] += 1
                h = check(e)
                if h:
                    st["hit"] += 1; st["hit_" + cid] += 1
                    for pos in {x for v in h.values() for x in v}: by[pos] += 1
                    ex.setdefault(tuple(sorted({x for v in h.values() for x in v})), []).append((e["answers"][0], e["q"][:70]))
                    if not apply: keep.append(e)
                else: keep.append(e)
            if apply and len(keep) != len(doc["exercises"]):
                doc["exercises"] = keep
                io.open(p, "w", encoding="utf-8").write(json.dumps(doc, ensure_ascii=False))
    print(dict(st)); print(dict(by))
    for k, v in sorted(ex.items(), key=lambda kv: -len(kv[1]))[:14]:
        print(k, len(v), v[:4])
