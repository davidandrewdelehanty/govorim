# -*- coding: utf-8 -*-
"""The dative and instrumental lessons of «Nouns and Adjectives in Cases» keep only exercises whose blanked word can ONLY be read as
that case in its sentence (coverage.strong_case): «Тафт стал очень консервативным» is instrumental, but the same form is also a
dative plural, and a label forced onto it by the lesson would teach the wrong case.
    python3 tools/courses/strong_guard.py [--apply]"""
import io, json, os, re, sys
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import coverage as C

ROOT = os.path.dirname(os.path.dirname(HERE))
D = os.path.join(ROOT, "public", "courses", "cases")
CASE = {"k4": "datv", "k5": "ablt"}


def main(argv=None):
    apply = "--apply" in (argv if argv is not None else sys.argv[1:])
    dropped = 0
    for fn in sorted(os.listdir(D)):
        if not fn.endswith(".json") or fn[:2] not in CASE:
            continue
        p = os.path.join(D, fn)
        doc = json.load(io.open(p, encoding="utf-8"))
        keep, out = [], []
        for e in doc.get("exercises") or []:
            ans = (e.get("answers") or [""])[0]
            if e.get("type") != "fill" or len(ans.split()) != 1 or not re.fullmatch(r"[А-Яа-яЁё-]+", ans):
                keep.append(e); continue
            sentence = re.sub(r"___ \([^)]*\)", ans, e.get("q") or "")
            if C.strong_case(sentence, ans, CASE[fn[:2]]):
                keep.append(e)
            else:
                out.append(e); print("drop", fn, "|", e.get("q"))
        if out:
            dropped += len(out)
            if apply:
                doc["exercises"] = keep
                for i, e in enumerate(keep):
                    e["id"] = "q%d" % (i + 1)
                io.open(p, "w", encoding="utf-8").write(json.dumps(doc, ensure_ascii=False))
    print("strong_guard: %d dropped" % dropped)


if __name__ == "__main__":
    main()
