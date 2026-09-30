#!/usr/bin/env python3
import io, json, os, re, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from scan_alignment import chapters
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SUSPECTS = json.load(open(os.path.join(ROOT,"tools","qc-suspects.json"),encoding="utf-8"))
man = json.load(open(os.path.join(ROOT,"private","books","index.json"),encoding="utf-8"))
def clip(t,n=170):
    t=re.sub(r"\s+"," ",t or "").strip()
    return t if len(t)<=n else t[:n]+"…"
out={}
for e in man:
    fn=e.get("filename")
    if not fn or fn not in SUSPECTS: continue
    if fn in out: continue
    path=os.path.join(ROOT,"public","books",fn)
    if not os.path.exists(path): path=os.path.join(ROOT,"private","books",fn)
    chs=chapters(path,e.get("title",""))
    if not chs: out[fn]={"error":"unparseable"}; continue
    out[fn]={"n":len(chs),
      "head":[clip(p) for p in chs[0][:8]],
      "tail":[clip(p) for p in chs[-1][-8:]],
      "tail_counts":len(chs[-1])}
json.dump(out,open(os.path.join(ROOT,"tools","qc-detail.json"),"w",encoding="utf-8"),ensure_ascii=False,indent=1)
print("done",len(out))
