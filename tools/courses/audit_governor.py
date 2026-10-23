# -*- coding: utf-8 -*-
"""Every blank that stands after a preposition: the answer must be able to be in a case that preposition governs (all courses but the case courses, which resolve_pair covers)."""
import glob, json, os, re, sys
from collections import Counter, defaultdict
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import case_explain as C
M = C.M
bad = defaultdict(list); tot = Counter()
for f in sorted(glob.glob("public/courses/*/*.json")):
    c = f.split("/")[2]
    if c.startswith("case") or c in ("cases",) or os.path.basename(f) == "exam.json": continue
    for e in json.load(open(f, encoding="utf-8")).get("exercises") or []:
        q = e.get("q") or ""
        m = re.search(r"___ \(([^)]*)\)", q)
        if not m or e.get("type") != "fill": continue
        if re.search(r"[A-Za-z+/]", m.group(1)) and not re.search(r"[А-Яа-я]", m.group(1)): pass
        gc = C.governing_cases(q[:m.start()])
        if not gc: continue
        aw = C.WORD.findall(e["answers"][0])
        if not aw: continue
        tot[c] += 1
        want = set(gc) | {"gen2", "loc2", "acc2"} if False else set(gc)
        ok = all(any((p.tag.case in want) or (p.tag.case in ("gen2", "acc2", "loc2") and {"gen2": "gent", "acc2": "accs", "loc2": "loct"}[p.tag.case] in want) for p in M.parse(w)) or not any(p.tag.case for p in M.parse(w)) for w in aw)
        if not ok: bad[c].append((os.path.basename(f)[:20], q[:70], e["answers"][0], sorted(gc)))
print("checked", dict(tot)); print("problems", {k: len(v) for k, v in bad.items()})
for c, v in bad.items():
    print("==", c)
    for x in v[:(80 if "--all" in sys.argv else 6)]: print("   ", x)
