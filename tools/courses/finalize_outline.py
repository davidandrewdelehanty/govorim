# -*- coding: utf-8 -*-
"""Recount every section of src/courses-outline.js from the files on disk, drop empty practice sets, deal the exams again.
Run after any pass that removes exercises without a full build:  python3 tools/courses/finalize_outline.py"""
import io, json, os, re, sys
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
ROOT = os.path.dirname(os.path.dirname(HERE))
op = os.path.join(ROOT, "src", "courses-outline.js")
txt = io.open(op, encoding="utf-8").read()
cur = json.loads(txt[txt.index("export default ") + 15:].rstrip().rstrip(";"))
for m in cur:
    kept = []
    for o in m["sections"]:
        if o.get("exam"):
            kept.append(o); continue
        p = os.path.join(ROOT, "public", "courses", m["id"], o["id"] + ".json")
        if not os.path.exists(p):
            continue
        j = json.load(io.open(p, encoding="utf-8"))
        if not (j.get("stream") and not j.get("finite")):
            o["n"] = len(j.get("exercises") or [])
        if o["n"] == 0 and re.search(r"-practice(?:-\d+)?$", o["id"]):
            os.remove(p); continue
        kept.append(o)
    m["sections"] = kept
import make_exams
make_exams.add_exams(cur)
io.open(op, "w", encoding="utf-8").write("// Written by tools/courses/build_courses.py — the courses, their sections and\n"
    "// how many exercises each has. The lessons themselves are in public/courses/.\n"
    "export default " + json.dumps(cur, ensure_ascii=False, indent=1) + ";\n")
