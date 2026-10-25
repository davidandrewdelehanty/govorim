# -*- coding: utf-8 -*-
"""Data for the Exercises tab's clock practice: every time of the day, said in words (the clock set from the words, or the words
written from the clock).  The forms are the ones gen_clock.py built from OpenCorpora dictionary forms by the DLI Grammar Reference
Book's rules (Lessons 40, 73, 74); nothing is written here.
    python3 tools/courses/gen_clock_drill.py   (from the repo root)   →   public/vocab/clock-times.json
Item: [hhmm, kind, [wordings to set], [accepted words], [parts of the day], [24-hour wordings], clock, part of the day, noSay]"""
import io, json, os, sys
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
ROOT = os.path.dirname(os.path.dirname(HERE))
import clock_course as CC
D = json.load(io.open(os.path.join(HERE, "clock_data.json"), encoding="utf-8"))
out = {"why": dict(CC.WHY, h24=CC.H24), "ctx": CC.CTX,
       "t": [[d["hhmm"], d["k"], d["sets"], d["a"], d["pods"], d["a24"], d["clock"], d["pod"], 1 if d.get("noSay") else 0] for d in D["drills"]]}
p = os.path.join(ROOT, "public", "vocab", "clock-times.json")
io.open(p, "w", encoding="utf-8").write(json.dumps(out, ensure_ascii=False, separators=(",", ":")))
print(len(out["t"]), "times,", os.path.getsize(p) // 1024, "KB")
