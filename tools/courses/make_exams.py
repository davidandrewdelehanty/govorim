#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""An exam at the end of every course.

For each course that is not a free repeat (the clock), a last section
«Exam»: when it is opened the app deals five questions from every chapter of
the course, in a random order, and the reader's first answer to each one is
the one that counts. 90% or better passes, and passing earns the course's
badge. A chapter is a lesson with its practice sets; the questions are the
course's own exercises, nothing new is written.

So that the file stays small and the exam is different each time, the file
holds up to thirty of each chapter's exercises (a fixed sample, so builds
are stable) and the app picks five of them when the exam is opened.

Called by build_courses.py after the outline is complete; writes
public/courses/<course>/exam.json and appends the section to the outline.
"""
import io, json, os, random, re

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
PER = 5          # questions from each chapter
MIN_Q = 20       # a course with few chapters asks more of each, so the exam is at least this long
POOL = 30        # of each chapter's exercises kept in the file (more when more are asked)
PASS = 90        # per cent
EXAM_PER = {"prepositions": 1}     # a course with very many chapters asks one question of each, not five
PRACTICE = re.compile(r"-practice(-\d+)?$")
KEEP = ("type", "q", "answers", "options", "answer", "ru", "prompt", "hint", "show", "k", "pairs", "clip")


def add_exams(outline):
    for meta in outline:
        if meta.get("repeat"):
            continue
        cdir = os.path.join(ROOT, "public", "courses", meta["id"])
        secs = [s for s in meta["sections"] if s["id"] != "exam"]
        meta["sections"] = secs
        topics, order = {}, []
        for s in secs:
            if not s.get("n") or (s.get("stream") and not s.get("finite")):
                continue
            key = PRACTICE.sub("", s["id"])
            j = json.load(io.open(os.path.join(cdir, s["id"] + ".json"), encoding="utf-8"))
            exs = [e for e in (j.get("exercises") or []) if e.get("type") in (None, "fill", "mc", "match") and e.get("q")]
            if not exs:
                continue
            if key not in topics:
                topics[key] = {"id": key, "title": re.sub(r"^Practice\s*\d*:\s*", "", s["title"]), "exercises": []}
                order.append(key)
            elif not PRACTICE.search(s["id"]):
                topics[key]["title"] = s["title"]
            for e in exs:
                x = {k: e[k] for k in KEEP if k in e}
                x.setdefault("type", "fill")
                topics[key]["exercises"].append(x)
        if not order:
            continue
        per = EXAM_PER.get(meta["id"]) or max(PER, -(-MIN_Q // len(order)))
        pool = max(POOL, per * 4)
        rnd = random.Random(meta["id"])
        out_topics = []
        for key in order:
            t = topics[key]
            xs = list(t["exercises"])
            rnd.shuffle(xs)
            xs = xs[:pool]
            for i, x in enumerate(xs):
                x["id"] = "q%d" % (i + 1)
            out_topics.append({"id": t["id"], "title": t["title"], "exercises": xs})
        n = sum(min(per, len(t["exercises"])) for t in out_topics)
        words = ["one", "two", "three", "four", "five", "six", "seven", "eight", "nine", "ten"]
        data = {"id": "exam", "title": "Exam", "exam": True, "pass": PASS, "per": per,
                "blocks": [
                    {"t": "lead", "text": ("%d questions from the course's one chapter with exercises, in a random order." % n) if len(out_topics) == 1
                     else "%d questions: %s from each of the %d chapters, in a random order." % (
                        n, words[per - 1] if per <= 10 else str(per), len(out_topics))},
                    {"t": "p", "text": "Your first answer to each question is the one that counts. %d%% or better passes, "
                                       "and passing earns the badge for %s. You can take it as often as you like; the questions are dealt afresh each time." % (PASS, meta["title"])},
                ],
                "topics": out_topics}
        io.open(os.path.join(cdir, "exam.json"), "w", encoding="utf-8").write(json.dumps(data, ensure_ascii=False, separators=(",", ":")))
        secs.append({"id": "exam", "title": "Exam", "n": n, "exam": True})
        print("   exam %-10s %2d chapters, %3d questions, pool %d" % (meta["id"], len(out_topics), n, sum(len(t["exercises"]) for t in out_topics)))
