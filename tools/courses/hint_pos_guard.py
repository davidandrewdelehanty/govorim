# -*- coding: utf-8 -*-
"""Drop an exercise whose hint is a verb (the infinitive) but whose answer is a participle or a gerund —
«прожечь» → «прожжённый», «наматывать» → «наматывая» — in a section that is not about forming them.
The hint must be of the part of speech the answer is; in the participle and gerund sections a verb hint is the point
(the learner builds the form) and stays.   Dropped ones go to _dropped/hint_pos.json.
Usage: hint_pos_guard.py [--apply] [--course X]"""
import glob, io, json, os, re, sys
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
# sections where building the participle / gerund from the verb is what is taught
ALLOW_COURSE = {"forms", "tables", "tenses", "gramterms"}
ALLOW_SECTION = re.compile(r"^(i12|i13|i14|i15)-")


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    apply = "--apply" in argv
    only = argv[argv.index("--course") + 1] if "--course" in argv else None
    try:
        import pymorphy3
    except ImportError:
        print("hint_pos_guard skipped (pymorphy3 not installed)")
        return
    M = pymorphy3.MorphAnalyzer()
    ye = lambda s: s.lower().replace("ё", "е")
    dropped = []
    for f in sorted(glob.glob(os.path.join(ROOT, "public", "courses", "*", "*.json"))):
        c = f.split(os.sep)[-2]
        sec = os.path.basename(f)[:-5]
        if (only and c != only) or sec == "exam" or c in ALLOW_COURSE or ALLOW_SECTION.match(sec):
            continue
        doc = json.load(io.open(f, encoding="utf-8"))
        keep = []
        for e in doc.get("exercises") or []:
            m = re.search(r"___ \(([^)]*)\)", e.get("q") or "")
            if m and e.get("type") == "fill" and e.get("answers"):
                h = ye(re.split(r"[,;— ]", m.group(1).strip())[0])
                a = ye(e["answers"][0])
                if re.fullmatch(r"[а-я]+", h) and re.fullmatch(r"[а-я\-]+", a):
                    hv = any(p.tag.POS in ("INFN", "VERB") and ye(p.normal_form) == h for p in M.parse(h))
                    ap_ = [p for p in M.parse(a) if p.score > 0.02]
                    # the answer's likeliest reading a participle or a gerund
                    if hv and ap_ and ap_[0].tag.POS in ("PRTF", "PRTS", "GRND"):
                        dropped.append(dict(e, _from=c + "/" + sec))
                        continue
            keep.append(e)
        if len(keep) != len(doc.get("exercises") or []):
            doc["exercises"] = keep
            if apply:
                io.open(f, "w", encoding="utf-8").write(json.dumps(doc, ensure_ascii=False))
    for d in dropped:
        print("  dropped %-34s (%s) -> %s | %s" % (d["_from"], re.search(r"\(([^)]*)\)", d["q"]).group(1), d["answers"][0], d["q"][:50]))
    if apply and dropped:
        out = os.path.join(HERE, "_dropped")
        os.makedirs(out, exist_ok=True)
        io.open(os.path.join(out, "hint_pos.json"), "w", encoding="utf-8").write(json.dumps(dropped, ensure_ascii=False, indent=1))
    print("hint_pos_guard: %d dropped%s" % (len(dropped), "" if apply else " (dry run)"))


if __name__ == "__main__":
    main()
