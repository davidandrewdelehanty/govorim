# -*- coding: utf-8 -*-
"""Lesson-page sentences with an English translation.

coverage.py --mine fills a lesson's missing patterns from the library's public-domain books, whose
sentences have no English. This does the same from Tatoeba (sentence + translation, CC BY 2.0 FR):
a pattern is "covered" only by exercises that have a translation, and the fill file is rewritten
with Tatoeba sentences. Sentences already used anywhere in the same course are not repeated.
Run:  python3 tools/courses/coverage_tatoeba.py        (then rebuild: build_courses.py)
"""
import io, json, os, random, re, sys
from collections import defaultdict
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import coverage as C
from prep_mine import load_pool

SRC = "Sentence and translation from Tatoeba (CC BY 2.0 FR)."
OUT = os.path.join(HERE, "coverage_fill.json")


def translated(e):
    p = e.get("prompt") or ""
    return bool(p) and not p.startswith("*") and re.search(r"[A-Za-z]{2,}", p) and len(re.findall(r"[А-Яа-яЁё]", p)) < 3


_load = C.load_course
def load_translated(course):
    d = _load(course)
    return {k: [e for e in v if translated(e)] for k, v in d.items()}
C.load_course = load_translated

EN = {}
def library():
    pool = load_pool()
    rows = []
    for ru, en in pool.items():
        s = ru.strip()
        if not (28 <= len(s) <= 110) or re.search(r"[A-Za-z\d]", s) or s.count(",") > 3:
            continue
        EN[s] = en
        rows.append((s, en))
    random.Random(11).shuffle(rows)
    return rows
C.library = library
C.FILL = os.path.join(HERE, "_nonexistent_fill.json")      # start from nothing
C.ADD = 6

def sent(e):
    return re.sub(r"___ \([^)]*\)", e["answers"][0], e["q"])

def used_in(course):
    out = set()
    d = os.path.join(C.COURSES, course)
    for f in os.listdir(d):
        if f.endswith(".json"):
            for e in json.load(io.open(os.path.join(d, f), encoding="utf-8")).get("exercises") or []:
                if e.get("q"):
                    out.add(re.sub(r"\s+", " ", sent(e) if e.get("answers") else e["q"]))
    return out

def main():
    a = C.audit()
    C.report(a)
    found = C.mine(a)
    new = {}
    for key, exs in found.items():
        course = key.split("/")[0]
        used = used_in(course)
        by = defaultdict(int)
        keep = []
        for e in exs:
            s = sent(e)
            if re.sub(r"\s+", " ", s) in used:
                continue
            if by[e.get("facet")] >= 3:
                continue
            en = e["prompt"].strip("*")
            e = dict(e, prompt=en, why=SRC)
            by[e.get("facet")] += 1
            keep.append(e)
        if keep:
            new[key] = keep
    json.dump(new, io.open(OUT, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print("coverage_tatoeba: %d exercises in %d lessons -> %s" % (sum(len(v) for v in new.values()), len(new), OUT))

if __name__ == "__main__":
    main()
