#!/usr/bin/env python3
"""Build the Courses tab: each course's sections → public/courses/<course>/<section>.json,
and the outline (titles, section lists, exercise counts) → src/courses-outline.js,
which the app and the server's badge code both read.

    cd /mnt/c/Users/david/projects/govorim-app
    python3 tools/courses/build_courses.py
"""
import importlib, io, json, os, sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, HERE)

COURSES = [
    {
        "id": "wikibook", "title": "Russian Grammar from the Wikibook", "short": "Wikibook", "mark": "W",
        "blurb": "Twenty short lessons, from your first «Привет!» to the six cases, verbs of motion and numbers — "
                 "a guided tour of everyday Russian grammar.",
        "credit": "Adapted from the Wikibooks Russian textbook and its contributors",
        "creditUrl": "https://en.wikibooks.org/wiki/Russian",
        "license": "CC BY-SA 4.0", "licenseUrl": "https://creativecommons.org/licenses/by-sa/4.0/",
        "modules": ["wikibook_a", "wikibook_b", "wikibook_c"],
        "order": ["greetings", "no-the-no-is", "gender", "plurals", "pronouns", "adjectives",
                  "present", "past", "future", "aspect",
                  "cases", "accusative", "prepositional", "genitive", "dative", "instrumental",
                  "reflexive", "going", "questions", "numbers"],
    },
]
COURSES.append({
    "id": "motion", "title": "Verbs of Motion", "short": "Motion", "mark": "→",
    "blurb": "Going, carrying, leading and driving — the unprefixed pairs, then every prefix from при- to с-, "
             "with drills: a course of its own, also in the Grammar tab.",
    "credit": "Based on the Defense Language Institute Russian Basic Course, Grammar Reference Book and Student Workbooks (US Government work, public domain)",
    "creditUrl": "https://www.fsi-language-courses.org/russian/courses/dli-russian-basic-course",
    "license": "Public domain", "licenseUrl": "",
    "modules": ["motion_a", "motion_b", "motion_c"], "order": None,
})
if os.path.exists(os.path.join(HERE, "dli_a.py")):
    COURSES.append({
        "id": "dli", "title": "DLI Basic Russian Grammar", "short": "DLI", "mark": "D",
        "blurb": "The grammar of the US Defense Language Institute's Basic Russian course — thorough, systematic, "
                 "with drills — rewritten as lessons and exercises.",
        "credit": "Based on the Defense Language Institute Russian Basic Course (US Government work, public domain)",
        "creditUrl": "https://www.fsi-language-courses.org/russian/courses/dli-russian-basic-course",
        "license": "Public domain", "licenseUrl": "",
        "modules": sorted(m[:-3] for m in os.listdir(HERE) if m.startswith("dli_") and m.endswith(".py")),
        "order": None,
    })


def main():
    outline = []
    for c in COURSES:
        secs = []
        for m in c["modules"]:
            secs += importlib.import_module(m).SECTIONS
        by = {s["id"]: s for s in secs}
        if len(by) != len(secs):
            raise SystemExit("duplicate section id in " + c["id"])
        order = c["order"] or [s["id"] for s in secs]
        missing = [i for i in order if i not in by]
        if missing:
            raise SystemExit("missing sections: %s" % missing)
        out_dir = os.path.join(ROOT, "public", "courses", c["id"])
        os.makedirs(out_dir, exist_ok=True)
        osecs = []
        for sid in order:
            s = by[sid]
            exs = []
            for i, e in enumerate(s["exercises"], 1):
                e = dict(e, id="q%d" % i)
                if e["type"] == "mc":
                    assert 0 <= e["answer"] < len(e["options"]), (sid, i)
                exs.append(e)
            data = {"id": sid, "title": s["title"], "blocks": s["blocks"], "exercises": exs}
            io.open(os.path.join(out_dir, sid + ".json"), "w", encoding="utf-8").write(
                json.dumps(data, ensure_ascii=False, separators=(",", ":")))
            o = {"id": sid, "title": s["title"], "n": len(exs)}
            if s.get("sub"):
                o["sub"] = s["sub"]
            osecs.append(o)
        meta = {k: v for k, v in c.items() if k not in ("modules", "order")}
        meta["sections"] = osecs
        outline.append(meta)
        print("%-10s %2d sections, %3d exercises" % (c["id"], len(osecs), sum(s["n"] for s in osecs)))
    js = ("// Written by tools/courses/build_courses.py — the courses, their sections and\n"
          "// how many exercises each has. The lessons themselves are in public/courses/.\n"
          "export default " + json.dumps(outline, ensure_ascii=False, indent=1) + ";\n")
    io.open(os.path.join(ROOT, "src", "courses-outline.js"), "w", encoding="utf-8").write(js)


if __name__ == "__main__":
    main()
