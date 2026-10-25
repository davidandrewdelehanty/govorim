"""Name the case and number in every nominal blank of the case/number-forming courses: «___ (чувство)» → «___ (чувство, acc. pl.)».
Only when the sentence settles it (resolve_pair / a counting word); in `cases` and `prepositions` an exercise that cannot be labelled is dropped.
python3 tag_hints.py [--apply] [--course c ...]"""
import io, json, re, sys, glob, os, collections
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import case_explain as CE
M = CE.M
_old_ok = CE.lemma_ok
def _ok(p, h):
    # the hint may be a plural-only noun or a plural phrase (деньги, былые годы): accept the nominative forms of any word
    return _old_ok(p, h) or CE.norm(h) in {CE.norm(f.word) for f in p.lexeme if f.tag.case == "nomn"}
CE.lemma_ok = _ok
NOMINAL = {"NOUN", "ADJF", "NPRO", "NUMR"}
COURSES = ["cases", "prepositions", "time", "count", "numerals"]
# verified by hand: the verb takes the accusative (задеть что, осуществлять что) and the blank is plural in the plural lesson
MANUAL = {"Мы побоялись задеть его ___ (чувство).": "acc. pl.",
          "Эта авиакомпания осуществляет только грузовые ___ (авиаперевозка).": "acc. pl."}
DROP_IF_UNLABELLED = {"cases", "prepositions"}
CASE_EN = CE.CASE_EN
def walk(o, out):
    if isinstance(o, dict):
        if isinstance(o.get("q"), str) and "answers" in o: out.append(o)
        for v in o.values(): walk(v, out)
    elif isinstance(o, list):
        for v in o: walk(v, out)
def label_for(q, m, hint, ans):
    hw = CE.WORD.findall(hint); aw = CE.WORD.findall(ans)
    if not hw or len(hw) != len(aw) or len(aw) > 3: return None
    if not all(any(p.tag.POS in NOMINAL for p in M.parse(h)) for h in hw): return None
    if any(p.tag.POS in ("VERB", "INFN") and p.score > .5 for p in M.parse(hw[0])[:1]): return None
    if re.search(r"\d|[A-Za-z]", hint): return None
    if CE.norm(aw[-1]) == "лет": hw = hw[:-1] + ["год"]
    gov = CE.governed(q[:m.start()])
    pair = CE.resolve_pair(q, m, aw, hw)
    if pair == "invariant": return "invariant"
    if gov:
        gp = {x for x in CE.pairs_of(aw[-1], hw[-1]) if x[0] == gov[0]}
        if (gov[0], gov[1]) in gp: pair = (gov[0], gov[1])
        elif len(gp) == 1: pair = next(iter(gp))          # «много воды»: the counting word wants the genitive; the noun has no plural
    if not pair: return None
    case, num = pair
    lab = "%s %s" % (CASE_EN[case], "sg." if num == "sing" else "pl.")
    if len(hw) == 1 and num == "sing":
        pos = {p.tag.POS for p in M.parse(aw[0]) if CE.norm(p.normal_form) == CE.norm(hw[0])}
        if pos & {"ADJF", "NPRO", "NUMR"} and not pos & {"NOUN"}:
            g = [p.tag.gender for p in M.parse(aw[0]) if CE._cn(p.tag.case) == case and p.tag.number == "sing" and p.tag.gender and CE.norm(p.normal_form) == CE.norm(hw[0])]
            if g: lab += " " + {"masc": "m.", "femn": "f.", "neut": "n."}[g[0]]
    return lab
def main(argv):
    apply = "--apply" in argv
    cs = argv[argv.index("--course") + 1:] if "--course" in argv else COURSES
    st = collections.Counter(); samples = collections.defaultdict(list)
    for c in cs:
        for f in sorted(glob.glob("public/courses/%s/*.json" % c)):
            j = json.load(open(f, encoding="utf-8")); changed = False
            out = []; walk(j, out)
            dropids = set()
            for e in out:
                q = e["q"]; ans = (e.get("answers") or [""])[0]
                m = re.search(r"___ \(([^()]*)\)", q)
                if not m or q.count("___") != 1: continue
                hint = m.group(1).strip()
                if "," in hint: continue
                if not re.fullmatch(r"[А-Яа-яЁё\- ]+", hint): continue
                if len(CE.WORD.findall(q.replace(m.group(0), ""))) < 2: continue
                r = MANUAL.get(q) or label_for(q, m, hint, ans)
                if r == "invariant": st[c + ":invariant"] += 1; continue
                if r is None:
                    if not any(p.tag.POS in NOMINAL for p in M.parse(hint.split()[0])): continue   # a verb etc.
                    st[c + ":unlabelled"] += 1; samples[c].append((os.path.basename(f), q[:80], ans))
                    if c in DROP_IF_UNLABELLED: dropids.add(id(e))
                    continue
                e["q"] = q[:m.start()] + "___ (" + hint + ", " + r + ")" + q[m.end():]
                st[c + ":tagged"] += 1; changed = True
                if len(samples[c + "+"]) < 4: samples[c + "+"].append(e["q"][:100])
            if dropids:
                def prune(o):
                    if isinstance(o, dict):
                        for k, v in o.items():
                            if isinstance(v, list) and v and all(isinstance(x, dict) for x in v): o[k] = [x for x in v if id(x) not in dropids]
                            prune(o[k])
                    elif isinstance(o, list):
                        for v in o: prune(v)
                prune(j); changed = True; st[c + ":dropped"] += len(dropids)
            if changed and apply: io.open(f, "w", encoding="utf-8").write(json.dumps(j, ensure_ascii=False))
    print(dict(st), "" if apply else "(dry)")
    for k, v in samples.items():
        for x in v[:5]: print(k, x)
if __name__ == "__main__":
    main(sys.argv[1:])
