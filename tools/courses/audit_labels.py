#!/usr/bin/env python3
"""Independent check of the case label in every case-course question: the answer must really be a form of the hinted word
in that case and number (dictionary: OpenCorpora via pymorphy3). Exits 1 on any mismatch."""
import io, json, os, re, sys
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
try:
    import pymorphy3
except ImportError:
    print("audit_labels skipped (pymorphy3 not installed)"); sys.exit(0)
M = pymorphy3.MorphAnalyzer()
CASE = {"nom": "nomn", "gen": "gent", "dat": "datv", "acc": "accs", "instr": "ablt", "prep": "loct"}
NUM = {"sg": "sing", "pl": "plur"}
W = re.compile(r"[А-Яа-яЁё]+(?:-[А-Яа-яЁё]+)?")
norm = lambda w: w.lower().replace("ё", "е")
bad, n = [], 0
for cid in ["cases", "case-nom", "case-gen", "case-dat", "case-acc", "case-ins", "case-prp"]:
    d = os.path.join(ROOT, "public", "courses", cid)
    for fn in sorted(os.listdir(d)):
        if not fn.endswith(".json") or fn == "exam.json":
            continue
        for e in json.load(io.open(os.path.join(d, fn), encoding="utf-8")).get("exercises", []):
            if e.get("type") != "fill":
                continue
            m = re.search(r"___ \(([^)]*?),\s*(nom|gen|dat|acc|instr|prep)\.\s*(sg|pl)\.(?:\s*[mfn]\.)?\)", e.get("q", ""))
            if not m:
                continue
            n += 1
            hint = W.findall(m.group(1))
            ans = W.findall((e.get("answers") or [""])[0])
            case, num = CASE[m.group(2)], NUM[m.group(3)]
            if len(hint) != len(ans):
                bad.append((cid, fn, e["q"], "word count")); continue
            ok = True
            for h, a in zip(hint, ans):
                hit = False
                for p in M.parse(a):
                    c = {"gen2": "gent", "loc2": "loct", "acc2": "accs"}.get(p.tag.case, p.tag.case)
                    if c != case or (p.tag.number and p.tag.number != num):
                        continue
                    if norm(p.normal_form) == norm(h) or norm(h) in {norm(f.word) for f in p.lexeme if f.tag.case == "nomn"}:
                        hit = True; break
                if not hit and norm(a) == norm(h) and norm(a) in ("его", "ее", "их"):
                    hit = True
                if not hit:
                    ok = False
            if not ok:
                bad.append((cid, fn, e["q"], (e.get("answers") or [""])[0]))
print("labelled questions checked:", n)
print("label problems:", len(bad))
for b in bad[:30]:
    print("  ", b)
sys.exit(1 if bad else 0)
