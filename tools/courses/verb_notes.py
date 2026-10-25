"""«Conjugation, Position Verbs and -ся» (course `verbs`): name the aspect, tense and person in every blank and put the forms
needed to conjugate the verb under the answer — «___ (петь)» → «___ (петь, impf., pres. 3rd sg.)», and the note lists the
present (future for a perfective) and past forms from the OpenCorpora dictionary, with stress marks wherever every form of
the verb has a stress that two independent sources (OpenRussian, Koziev) agree on.

    python3 tools/courses/verb_notes.py [--apply]     (run from the repository root)"""
import gzip, io, json, glob, os, re, sys, collections
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import paradigms as P
import orverbs as OR
M = P.M
ACUTE = "́"
VOW = "аеёиоуыэюя"
STRESS = json.load(gzip.open("tools/data/stress-dict.json.gz", "rt", encoding="utf-8"))
PERSONS = [("sing", "1per", "я"), ("sing", "2per", "ты"), ("sing", "3per", "он"),
           ("plur", "1per", "мы"), ("plur", "2per", "вы"), ("plur", "3per", "они")]
def mark(w):
    """The word with its stress mark, or None when the stress is not certain."""
    lw = w.lower()
    if "ё" in lw: return w
    n = sum(ch in VOW for ch in lw)
    if n <= 1: return w
    i = STRESS.get(lw)
    if i is None or lw[i] not in VOW: return None
    return w[:i + 1] + ACUTE + w[i + 1:]
def marked(forms):
    """All of the forms marked, or None: a half-marked line would read as «the rest is unstressed»."""
    out = []
    for ws in forms:
        r = [mark(w) for w in ws]
        if any(x is None for x in r): return None
        out.append(r)
    return out
def aspect_of(inf):
    asp = set()
    for p in M.parse(inf):
        if p.tag.POS == "INFN" and p.normal_form == inf:
            if "perf" in p.tag: asp.add("pf.")
            if "impf" in p.tag: asp.add("impf.")
    return asp
def lexeme(inf):
    return P._lemma(inf, "INFN").lexeme
def entry_lexeme(inf, ans=None):
    """The forms of the dictionary entry of `inf` that holds the answer (писать «write» has пишу, not писаю of the other entry), else all entries merged."""
    if ans:
        for p in M.parse(inf):
            if p.tag.POS == "INFN" and p.normal_form == inf:
                lx = p.lexeme
                if any(fold(f.word) == fold(ans) for f in lx): return lx
    return lexeme(inf)
def forms_for(inf, pf, ans=None):
    lex = entry_lexeme(inf, ans)
    tense = "futr" if pf else "pres"
    pres = []
    for num, per, pro in PERSONS:
        got = P._pick(lex, "VERB", num, per, tense) or P._pick(lex, "VERB", num, per, "futr" if not pf else "pres")
        pres.append(got)
    past = [P._pick(lex, "VERB", "past", *t) for t in (("masc", "sing"), ("femn", "sing"), ("neut", "sing"), ("plur",))]
    return pres, past
WHY = re.compile(r"^\*\*([^*→]+?)\s*→\s*([^*]+?)\*\*\s*[—–-]\s*(present tense|present-type form|past tense),?\s*([^:()]*?)\s*(\([^)]*\))?\.?\s*(?::\s*(.*))?$", re.S)
def fold(w): return w.lower().replace("ё", "е")
# the dictionary lists both aspects for these (a perfective and an imperfective entry spelt alike): the aspect of the sentence's reading
PAST_ASPECT = {"родиться": "pf.", "образоваться": "pf.", "перерезать": "pf.", "отрезать": "pf.", "использовать": "impf./pf.",
               "конфисковать": "impf./pf.", "жениться": "impf./pf.", "считать": "impf.", "замыкать": "impf.", "разбегаться": "impf.", "простираться": "impf."}
def aspect(inf, kind, ans=None):
    ent = OR.entry(inf, ans)
    if ent and ent["aspect"]:
        if ent["aspect"] == "impf./pf.": return "impf." if kind == "pres" else "impf./pf."
        return ent["aspect"]
    asp = aspect_of(inf)
    if len(asp) == 1: return next(iter(asp))
    return "impf." if kind == "pres" else PAST_ASPECT.get(inf, "impf.")
def label_from(why):
    m = WHY.match((why or "").strip())
    if not m: return None
    inf, ans, kind, who, paren, tail = m.groups()
    who = who.strip().rstrip(".")
    if kind == "past tense":
        g = {"masc": "m.", "fem": "f.", "neut": "n.", "plural": "pl."}.get(who)
        if not g: return None
        return dict(kind="past", who=g, paren=paren or "", tail=tail or "")
    pm = re.match(r"(1st|2nd|3rd)?\s*person (singular|plural)$", who)
    if not pm: return None
    return dict(kind="pres", who=(pm.group(1) or "3rd") + " " + ("sg." if pm.group(2) == "singular" else "pl."), paren=paren or "", tail=tail or "")
PERS_WHO = ["1st sg.", "2nd sg.", "3rd sg.", "1st pl.", "2nd pl.", "3rd pl."]
def analyze(inf, ans):
    """{(kind, who)} the answer can be: the slot of the OpenRussian table it fills, else the dictionary's forms of the verb."""
    out = set()
    ent = OR.entry(inf, ans)
    if ent:
        for i, ws in enumerate(ent["pres"]):
            if any(OR.fold(w) == OR.fold(ans) for w in ws): out.add(("pres", PERS_WHO[i]))
        for i, ws in enumerate(ent["past"]):
            if any(OR.fold(w) == OR.fold(ans) for w in ws): out.add(("past", ["m.", "f.", "n.", "pl."][i]))
        if out: return out
    try: lex = lexeme(inf)
    except Exception: return out
    for f in lex:
        t = set(str(f.tag).replace(" ", ",").split(","))
        if "VERB" not in t or fold(f.word) != fold(ans) or t & set(P.DROP): continue
        if "past" in t:
            g = "pl." if "plur" in t else {"masc": "m.", "femn": "f.", "neut": "n."}.get(next((x for x in ("masc", "femn", "neut") if x in t), ""))
            if g: out.add(("past", g))
        elif t & {"pres", "futr"} and t & {"1per", "2per", "3per"}:
            out.add(("pres", {"1per": "1st", "2per": "2nd", "3per": "3rd"}[next(x for x in ("1per", "2per", "3per") if x in t)] + (" pl." if "plur" in t else " sg.")))
    return out
def cap(s): return s[:1].upper() + s[1:]
# the blank is an imperative, though the lesson's earlier note called it a present form (Не входите! — «go in»)
IMPERATIVE = {("входить", "входите"), ("грузить", "грузите"), ("зубрить", "зубрите"), ("положить", "положи"), ("положить", "положите"), ("ложиться", "ложитесь")}
def rule_tail(inf, ans, kind, who):
    """The DLI's own one-line rules: the type of a present ending (е / и), and how the past is made."""
    a = fold(ans)
    if kind == "past":
        end = {"m.": "л", "f.": "ла", "n.": "ло", "pl.": "ли"}[who]
        stem = fold(inf)
        stem = stem[:-2] if stem.endswith("ся") else stem
        reg = fold(stem[:-2] + end) if stem.endswith("ть") else None
        refl = fold(inf).endswith("ся")
        reg_full = (reg + ("ся" if end in ("л", "ла", "ло", "ли") and who in ("m.", "pl.") and False else "")) if reg else None
        if reg and a.startswith(reg[:-len(end)] if False else reg) : return "Drop -ть, add %s." % ("-" + end) if not refl else "Drop -ться, add -%s%s." % (end, "ся" if who in ("m.", "pl.") else "сь")
        return "Irregular past stem: the past is not made by dropping -ть." if not (reg and a.startswith(reg)) else ""
    if who.startswith("1st sg"): return ""
    typ = None
    for e1, t in (("ешься", "e"), ("ёшься", "e"), ("ишься", "i"), ("ется", "e"), ("ётся", "e"), ("ится", "i"), ("емся", "e"), ("ёмся", "e"), ("имся", "i"), ("етесь", "e"), ("ётесь", "e"), ("итесь", "i"),
                  ("утся", "e"), ("ются", "e"), ("атся", "i"), ("ятся", "i"), ("ешь", "e"), ("ёшь", "e"), ("ишь", "i"), ("ете", "e"), ("ёте", "e"), ("ите", "i"), ("ем", "e"), ("ём", "e"), ("им", "i"),
                  ("ет", "e"), ("ёт", "e"), ("ит", "i"), ("ут", "e"), ("ют", "e"), ("ат", "i"), ("ят", "i")):
        if a.endswith(fold(e1)): typ = (e1, t); break
    if not typ: return ""
    return "Ending -%s belongs to the %s conjugation." % (typ[0], "first (е)" if typ[1] == "e" else "second (и)")
def build(e, stats):
    q = e["q"]
    m = re.search(r"___ \(([а-яё]+(?:ся|сь)?)\)", q)
    if not m: stats["nohint"] += 1; return False
    inf = m.group(1)
    ans = (e["answers"] or [""])[0]
    lab = label_from(e.get("why"))
    got = analyze(inf, ans)
    imper = (inf, fold(ans)) in IMPERATIVE
    if imper:
        lab = None; got = {("impr", "2nd sg." if fold(ans) == "положи" else "2nd pl.")}
    elif not got and not lab and fold(ans).endswith(("ется", "ится", "ает", "ит", "ется")):
        lab = {"kind": "pres", "who": "3rd sg.", "paren": "", "tail": ""}         # impersonal (житься, светать): 3rd person singular only
    if lab and (lab["kind"], lab["who"]) in got: key = (lab["kind"], lab["who"])
    elif len(got) == 1: key = next(iter(got)); lab = None
    elif lab and not got: key = (lab["kind"], lab["who"])        # impersonal verbs the dictionary has no forms for (светает)
    else: stats["ambiguous"] += 1; stats["amb:%s:%s:%s" % (inf, ans, sorted(got))] += 0; return False
    kind, who = key
    a = aspect(inf, "past" if kind == "past" else "pres", ans)
    if kind == "impr" and inf == "положить": a = "pf."
    tense = "past " if kind == "past" else "imper. " if kind == "impr" else ("pres. " if a != "pf." else "fut. ")
    tag = "%s, %s%s" % (a, tense, who)
    e["q"] = q[:m.start()] + "___ (%s, %s)" % (inf, tag) + q[m.end():]
    stats["tagged"] += 1
    if not e.get("why") and not e.get("_note"): return True      # the exam shows no notes
    ent = OR.entry(inf, ans)
    if ent:
        pres, past = ent["pres"], ent["past"]
        mk_p, mk_s, full = pres, past, True
        if any(not ws for ws in pres) or not all(past): stats["no forms line"] += 1; return True
        stats["stressed"] += 1
    else:
        try: pres, past = forms_for(inf, a == "pf.", ans)
        except Exception: stats["notindict"] += 1; return True
        if not got or any(not ws for ws in pres) or not all(past):
            stats["no forms line"] += 1; return True               # impersonal or defective verb: the old note stays
        mk_p = marked(pres); mk_s = marked(past)
        full = mk_p is not None and mk_s is not None
        if full: stats["stressed"] += 1
    pl = ["%s %s" % (pro, " / ".join(ws)) for (num, per, pro), ws in zip(PERSONS, mk_p if full else pres)]
    imp_txt = ""
    if kind == "impr":
        im = ent["impr"] if ent else [P._pick(entry_lexeme(inf, ans), "VERB", "impr", "excl", n) for n in ("sing", "plur")]
        if not ent:
            mi = marked(im) if full else None
            im = mi or im
        imp_txt = "imperative: ты %s · вы %s.  " % tuple(" / ".join(x) for x in im)
    head = "**%s → %s** (%s)" % (inf, e["answers"][0], tag)
    if lab:
        tail = (" " + cap(lab["paren"].strip("()")) + ".") if lab["paren"] else ""
        rule = cap(lab["tail"].strip())
    else:
        tail = ""; rule = rule_tail(inf, ans, kind, who) if e.get("_note") else ""
    e.pop("_note", None)
    forms = "Forms — %s%s: %s; past: %s." % (imp_txt.replace(".  ", "; "), "future" if a == "pf." else "present", " · ".join(pl), " · ".join(" / ".join(ws) for ws in (mk_s if full else past)))
    e["why"] = "%s.%s%s %s  — %s." % (head, tail, (" " + rule) if rule else "", forms, "OpenRussian (CC BY-SA 4.0)" if ent else "OpenCorpora dictionary (CC BY-SA 4.0)")
    stats["done"] += 1
    return True
def walk(o, out):
    if isinstance(o, dict):
        if isinstance(o.get("q"), str) and "answers" in o: out.append(o)
        for v in o.values(): walk(v, out)
    elif isinstance(o, list):
        for v in o: walk(v, out)
def main(argv):
    apply = "--apply" in argv
    stats = collections.Counter(); samples = []
    for f in sorted(glob.glob("public/courses/verbs/*.json")):
        j = json.load(open(f, encoding="utf-8")); out = []; walk(j, out); ch = False
        for e in out:
            if re.search(r"___ \([а-яё]+(?:ся|сь)?, (?:impf|pf)\.", e["q"]): stats["already"] += 1; continue
            if build(e, stats):
                ch = True
                if len(samples) < 6 and (stats["done"] % 90 == 1): samples.append((e["q"], e["why"]))
        if ch and apply: io.open(f, "w", encoding="utf-8").write(json.dumps(j, ensure_ascii=False))
    print({k: v for k, v in stats.items() if v and not k.startswith("amb:")}, "" if apply else "(dry)")
    for q, w in samples: print(q, "\n   ", w)
    for k in stats:
        if k.startswith("amb:"): print(k)
if __name__ == "__main__":
    main(sys.argv[1:])
