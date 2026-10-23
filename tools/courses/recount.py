# -*- coding: utf-8 -*-
"""After exercises were dropped from some courses' JSON: recount their sections in src/courses-outline.js, remove practice
sets left empty, and deal their exams afresh.   Usage: recount.py COURSE [COURSE ...]   (no names: every course)"""
import io, json, os, re, sys
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, HERE)
import make_exams


def main(ids=None):
    op = os.path.join(ROOT, "src", "courses-outline.js")
    txt = io.open(op, encoding="utf-8").read()
    k = txt.index("export default ")
    cur = json.loads(txt[k + len("export default "):].rstrip().rstrip(";"))
    sub = [m for m in cur if not ids or m["id"] in ids]
    for meta in sub:
        kept = []
        for o in meta["sections"]:
            if o["id"] == "exam":
                kept.append(o); continue
            p = os.path.join(ROOT, "public", "courses", meta["id"], o["id"] + ".json")
            j = json.load(io.open(p, encoding="utf-8"))
            if not (j.get("stream") and not j.get("finite")):
                o["n"] = len(j.get("exercises") or [])
            if o["n"] == 0 and re.search(r"-practice(?:-\d+)?$", o["id"]):
                os.remove(p); print("removed empty", p); continue
            kept.append(o)
        meta["sections"] = kept
    make_exams.add_exams(sub)
    io.open(op, "w", encoding="utf-8").write("// Written by tools/courses/build_courses.py — the courses, their sections and\n// how many exercises each has. The lessons themselves are in public/courses/.\nexport default " + json.dumps(cur, ensure_ascii=False, indent=1) + ";\n")
    print("recount:", ", ".join("%s %d" % (m["id"], sum(s["n"] for s in m["sections"] if s["id"] != "exam")) for m in sub))


if __name__ == "__main__":
    main(set(sys.argv[1:]) or None)
