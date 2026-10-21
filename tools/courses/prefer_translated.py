#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Exercises with an English translation first.

Two kinds of sentence feed the courses: Tatoeba's, which come with an English
sentence (the exercise's `prompt`), and the library's public-domain books',
which come with a citation instead. A reader at a blank wants to know what
the sentence means, so where a section has enough translated sentences the
untranslated ones are dropped, and where it has not they are kept but put
after the translated ones.

Run by build_courses.py over every section before the exams are dealt.
"""
import io, json, os, re

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
COURSES = os.path.join(ROOT, "public", "courses")
ENOUGH = 10          # translated exercises a section needs before the untranslated go
LATIN = re.compile(r"[A-Za-z]{2,}")
CYR = re.compile(r"[А-Яа-яЁё]")


def translated(e):
    p = e.get("prompt") or e.get("en") or ""
    if not p or p.startswith("*"):
        return False
    return bool(LATIN.search(p)) and len(CYR.findall(p)) < 3


def run():
    secs = dropped = kept_untr = 0
    for cid in sorted(os.listdir(COURSES)):
        cdir = os.path.join(COURSES, cid)
        if not os.path.isdir(cdir):
            continue
        for fn in sorted(os.listdir(cdir)):
            if not fn.endswith(".json") or fn == "exam.json":
                continue
            p = os.path.join(cdir, fn)
            d = json.load(io.open(p, encoding="utf-8"))
            exs = d.get("exercises") or []
            if not exs or any(e.get("type") in ("clock", "mc") for e in exs):
                continue
            tr = [e for e in exs if translated(e)]
            un = [e for e in exs if not translated(e)]
            if not un or not tr:
                continue
            if len(tr) >= ENOUGH:
                new = tr
                dropped += len(un)
            else:
                new = tr + un
                kept_untr += len(un)
            # ids stay in order, so the record of what was answered keeps its shape
            for i, e in enumerate(new):
                e["id"] = "q%d" % (i + 1)
            d["exercises"] = new
            io.open(p, "w", encoding="utf-8").write(json.dumps(d, ensure_ascii=False, separators=(",", ":")))
            secs += 1
    print("translated first: %d sections reordered, %d untranslated exercises dropped where there were enough translated, %d kept" % (secs, dropped, kept_untr))


if __name__ == "__main__":
    run()
