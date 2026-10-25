"""Audit of course exercises. Finds (1) a capitalised answer in the middle of a sentence whose hint lemma is lower-case (a NAME read as a common word:
Том ≠ тот), (2) a case-drill blank whose hint names no case/number."""
import glob, json, re, sys, collections
def walk(o, out):
    if isinstance(o, dict):
        if "q" in o and "answers" in o and isinstance(o["q"], str): out.append(o)
        for v in o.values(): walk(v, out)
    elif isinstance(o, list):
        for v in o: walk(v, out)
def items():
    for f in sorted(glob.glob("public/courses/*/*.json")):
        try: j = json.load(open(f, encoding="utf-8"))
        except Exception: continue
        out = []; walk(j, out)
        for e in out: yield f, e
import pymorphy3
MA = pymorphy3.MorphAnalyzer()
def lemma_forms(lem):
    return {f.word for p in MA.parse(lem.split()[0]) for f in p.lexeme}
def names():
    res = []
    for f, e in items():
        q = e["q"]; a = (e.get("answers") or [""])[0]
        if not a or not a[0].isupper(): continue
        for m in re.finditer(r"___\s*\(([^()]*)\)", q):
            pre = q[:m.start()].rstrip("   —–-«\"(")
            if not pre or pre[-1] in ".!?…:;»":                      # sentence start: the capital proves nothing, so ask the dictionary
                if (a.lower() in (lemma_forms(m.group(1).split(",")[0].strip()))) and any({"Name", "Surn", "Geox"} & set(str(p.tag).replace(",", " ").split()) for p in MA.parse(a)[:3]):
                    res.append((f, e, m.group(1).split(",")[0].strip()))
                continue
            lem = m.group(1).split(",")[0].strip()
            if lem and lem[0].islower(): res.append((f, e, lem))
    return res
if __name__ == "__main__":
    r = names()
    c = collections.Counter(x[0].split("/")[2] for x in r)
    print("names read as common words:", len(r), dict(c))
    for f, e, lem in r[:60]: print(f.split("courses/")[1], "|", e["q"][:80], "|", e["answers"][0], "|", lem)
