# Corrections from the full line-by-line review of every label (Oct 25 2026): 568 distinct exercises relabelled,
# a few wrong hint words replaced, and exercises whose answer cannot come from any sensible hint removed.
# Payload fix.b64: gzip JSON [[course/file, sha1(q\tanswer)[:12], current hint, new hint or null=remove]].
import json, io, re, os, gzip, base64, hashlib, sys, collections
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
P = json.loads(gzip.decompress(base64.b64decode(open(os.path.join(HERE, "fix.b64")).read())))
apply = "--apply" in sys.argv
byfile = collections.defaultdict(list)
for cf, h, cur, new in P: byfile[cf].append((h, cur, new))
st = collections.Counter(); dropped = collections.Counter()
def lists(o):
    if isinstance(o, dict):
        for v in o.values(): yield from lists(v)
    elif isinstance(o, list):
        if o and all(isinstance(x, dict) for x in o) and any("q" in x and "answers" in x for x in o): yield o
        for v in o: yield from lists(v)
for cf, items in byfile.items():
    f = os.path.join(ROOT, "public", "courses", cf); d = json.load(io.open(f, encoding="utf-8"))
    want = {h: (cur, new) for h, cur, new in items}; seen = set()
    for L in list(lists(d)):
        keep = []
        for e in L:
            if isinstance(e, dict) and "q" in e and "answers" in e:
                h = hashlib.sha1((e["q"] + "\t" + (e["answers"] or [""])[0]).encode()).hexdigest()[:12]
                if h in want:
                    cur, new = want[h]; seen.add(h)
                    if new is None: st["removed"] += 1; dropped[cf] += 1; continue
                    old = "___ (" + cur + ")"
                    assert old in e["q"], (cf, e["q"])
                    e["q"] = e["q"].replace(old, "___ (" + new + ")", 1); st["changed"] += 1
            keep.append(e)
        L[:] = keep
    miss = set(want) - seen
    if miss: st["not found"] += len(miss); print("not found in", cf, len(miss))
    if apply: io.open(f, "w", encoding="utf-8").write(json.dumps(d, ensure_ascii=False))
# keep the outline's per-section counts true
if apply and dropped:
    op = os.path.join(ROOT, "src", "courses-outline.js"); t = io.open(op, encoding="utf-8").read()
    k = t.index("export default "); cur = json.loads(t[k + 15:].rstrip().rstrip(";"))
    for m in cur:
        for s in m["sections"]:
            key = m["id"] + "/" + s["id"] + ".json"
            if key in dropped and not s.get("exam"): s["n"] = max(0, s.get("n", 0) - dropped[key])
    io.open(op, "w", encoding="utf-8").write(t[:k + 15] + json.dumps(cur, ensure_ascii=False, indent=1) + ";\n")
# a label that landed inside a gloss's own brackets — «(on foot; pf., imper. pl.))» — moves outside them
pat = re.compile(r"(___ \([^()]*\([^()]*?)([;,] (?:impf|pf|past|pres|fut|inf|imper|\d|nom|gen|dat|acc|instr|prep|comp|superl|short)[^()]*)\)\)")
import glob
for f in glob.glob(os.path.join(ROOT, "public", "courses", "*", "*.json")):
    s = io.open(f, encoding="utf-8").read(); s2, k = pat.subn(lambda m: m.group(1) + "); " + m.group(2)[2:] + ")", s)
    if k and apply: io.open(f, "w", encoding="utf-8").write(s2); st["unnested"] += k
print(dict(st), "apply" if apply else "dry run"); print(dict(dropped))
