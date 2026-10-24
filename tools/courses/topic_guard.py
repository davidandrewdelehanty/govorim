# -*- coding: utf-8 -*-
"""Exercises that do not exercise what their section teaches, for the sections whose subject shows in the words.

The case and construction filters (pertinence.py) work on grammar tags; they cannot see that «Спасибо за обед» is not about
time or that «залезть» is not about counting.  Here each rule says: a section matching `sec` (course/section) must have
its subject in the sentence (`need`, a regex over the sentence, its translation and the hint), and must not be about
something the subject merely looks like (`not_`, a regex over the hint and the answer: meals and holidays are not times of day).
Dropped ones go to _dropped/topic.json.     Usage: topic_guard.py [--apply] [--course X]"""
import glob, io, json, os, re, sys
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, HERE)
import drop_offtopic as DO

fold = lambda t: str(t or "").replace("ё", "е").replace("Ё", "Е")
TIME = re.compile("(" + DO.LEXICON["time"].replace("ё", "е") + "|столет|век\\b|веке|веков|праздник|будн|десятилет|сезон|каникул)", re.I)
COUNT = re.compile(DO.LEXICON["count"].replace("ё", "е"), re.I)
MEAL = re.compile(r"(обед|ужин|завтрак|именин)", re.I)
MOTION_END = ("йти", "идти", "итти", "ходить", "хаживать", "ехать", "езжать", "ездить", "бежать", "бегать", "лететь", "летать", "плыть",
              "плавать", "плывать", "нести", "носить", "возить", "везти", "вести", "водить", "лезть", "лазить", "лазать", "ползти", "ползать",
              "катить", "катать", "гнать", "гонять", "тащить", "таскать", "брести", "бродить", "нестись", "ходиться")

# (course, section regex, what the sentence must contain, what the hint/answer must not be)
RULES = [
    ("time", r".*", TIME, None),
    ("inter2", r"i16-.*", TIME, MEAL),
    ("case-acc", r"a5-time.*", TIME, MEAL),
    ("case-ins", r"i6-time.*", TIME, MEAL),
    ("aspect", r"a.*", None, re.compile(r"^\s*быть\b")),      # быть has no aspect pair: nothing to choose
    ("count", r".*", COUNT, None),
    ("inter2", r"i0[456]-.*", COUNT, None),
    ("case-gen", r"g3-counting.*", COUNT, None),
]


def motion_ok(e):
    m = re.search(r"___ \(([^)]*)\)", e.get("q") or "")
    if not m:
        return True
    first = fold(re.split(r"[ /—,]", m.group(1).strip())[0])
    return any(first.endswith(x) or first.rstrip("ся").endswith(x.rstrip("ся")) for x in MOTION_END)


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    apply = "--apply" in argv
    only = argv[argv.index("--course") + 1] if "--course" in argv else None
    dropped = []
    for f in sorted(glob.glob(os.path.join(ROOT, "public", "courses", "*", "*.json"))):
        c = f.split(os.sep)[-2]
        sec = os.path.basename(f)[:-5]
        if sec == "exam" or (only and c != only):
            continue
        rules = [(n, ne) for (cc, sr, n, ne) in RULES if cc == c and re.fullmatch(sr, sec)]
        motion = c == "inter2" and sec.startswith("i11-")
        if not rules and not motion:
            continue
        doc = json.load(io.open(f, encoding="utf-8"))
        keep = []
        for e in doc.get("exercises") or []:
            bad = None
            blob = fold(" ".join(str(e.get(k) or "") for k in ("q", "prompt", "ru")))
            for need, nope in rules:
                if need is not None and not need.search(blob):
                    bad = "not about the subject"
                elif nope is not None:
                    m = re.search(r"___ \(([^)]*)\)", e.get("q") or "")
                    hint = fold(m.group(1)) if m else ""
                    if nope.search(hint) or nope.search(fold(" ".join(e.get("answers") or []))):
                        bad = "the hint word is excluded for this section"
            if motion and not motion_ok(e):
                bad = "the verb is not a verb of motion"
            if bad:
                dropped.append(dict(e, _from=c + "/" + sec, _why=bad))
            else:
                keep.append(e)
        if len(keep) != len(doc.get("exercises") or []):
            doc["exercises"] = keep
            if apply:
                io.open(f, "w", encoding="utf-8").write(json.dumps(doc, ensure_ascii=False))
    for d in dropped[:60]:
        print("  drop %-34s %s | %s" % (d["_from"], d["_why"], d["q"][:60]))
    if apply and dropped:
        out = os.path.join(HERE, "_dropped")
        os.makedirs(out, exist_ok=True)
        op = os.path.join(out, "topic.json")
        old = json.load(io.open(op, encoding="utf-8")) if os.path.exists(op) else []
        seen = {(o.get("_from"), o.get("q")) for o in old}
        old += [d for d in dropped if (d["_from"], d.get("q")) not in seen]
        io.open(op, "w", encoding="utf-8").write(json.dumps(old, ensure_ascii=False, indent=1))
    print("topic_guard: %d dropped%s" % (len(dropped), "" if apply else " (dry run)"))


if __name__ == "__main__":
    main()
