# -*- coding: utf-8 -*-
"""The FSI Russian FAST Course as a course: one section per lesson — the
lesson's cultural notes, its dialogues and their variants, its useful words
and expressions — every line with the tape's recording of it (a ▶ in the
app), and exercises on the dialogue lines themselves: the line with a word
to type back from its English, what a line means, and the lesson's words
matched to theirs. Text: tools/courses/fast_src.py; where each line is on
the tapes: tools/courses/fast_clips.json (tools/pd_courses/fast_build.py)."""
import io, json, os, random, re
from kit import SEC, P, NOTE
import fast_src

HERE = os.path.dirname(os.path.abspath(__file__))
_CP = os.path.join(HERE, "fast_clips.json")
CLIPS = json.load(io.open(_CP, encoding="utf-8")) if os.path.exists(_CP) else {}
AUDIO = "https://pub-84adcd23e17e4925a0ac7eca17ea2556.r2.dev/fast/"
IN_SECTION = 50
SLUGS = {2: "geography", 3: "meeting-people", 4: "family", 5: "where-do-you-work", 6: "where-do-you-live",
         7: "shopping", 8: "restaurant", 9: "transportation", 10: "hotel", 11: "telephone"}


def clip(cid):
    return AUDIO + cid + ".mp3" if cid in CLIPS else None


def line(ru, en, cid, who=None):
    d = {"ru": ru, "en": en}
    if who:
        d["who"] = who
    c = clip(cid)
    if c:
        d["clip"] = c
    return d


def blank_word(ru):
    """The word to take out of a line: the longest everyday word of four
    letters or more, not a name (capitalised inside the sentence), not a
    figure. None when the line has nothing to blank."""
    words = re.findall(r"[А-Яа-яЁё\-]+", ru)
    best = None
    for k, w in enumerate(words):
        if len(w.replace("-", "")) < 4:
            continue
        if k > 0 and w[0].isupper():
            continue                          # Линда, Смит, Проспект Мира
        if best is None or len(w) > len(best):
            best = w
    return best


def fill_ex(ru, en, cid, why, ctx):
    w = blank_word(ru)
    if not w:
        return None
    q = re.sub(r"(?<![А-Яа-яЁё\-])" + re.escape(w) + r"(?![А-Яа-яЁё\-])", "___", ru, count=1)
    if "___" not in q:
        return None
    # `context` is the line above the question; given here so that
    # attach_context.py leaves these alone (its lesson prose is the cultural note).
    e = {"type": "fill", "q": q, "answers": [w], "prompt": "*%s*" % en, "why": why, "context": ctx, "keep": True}
    c = clip(cid)
    if c:
        e["clip"] = c
        e["hint"] = "Listen, then type the missing word."
    return e


def mc_ex(ru, en, others, rng, why, cid, ctx):
    pool = sorted(set(o for o in others if o != en and abs(len(o) - len(en)) < 40))
    if len(pool) < 3:
        return None
    opts = [en] + rng.sample(pool, 3)
    rng.shuffle(opts)
    e = {"type": "mc", "q": "What does this line mean?", "ru": ru, "options": opts, "answer": opts.index(en),
         "why": why, "context": ctx, "keep": True}
    c = clip(cid)
    if c:
        e["clip"] = c
    return e


SECS = []
for les in fast_src.LESSONS:
    n = les["n"]
    cite = "FSI Russian FAST Course, Lesson %d (public domain)" % n
    blocks = [P(x) for x in les.get("intro") or []]
    for si, st in enumerate(les.get("sets") or []):
        lines = []
        for li, ln in enumerate(st["lines"]):
            who, ru, en = ln.split("|", 2)
            lines.append(line(ru, en, "l%02d-s%d-%02d" % (n, si + 1, li + 1)))
        b = {"t": "phrases", "title": st["title"], "lines": lines}
        if st.get("en"):
            b["en"] = st["en"]
        blocks.append(b)
    turns_all = []            # (ru, en, clip id, dialogue label, who)
    for d in les.get("dialogs") or []:
        did = "l%02d-%s%d%s" % (n, "d" if d["kind"] == "dialog" else "v", d["n"], ("-%d" % d["v"]) if d.get("v") else "")
        label = ("Диалог %d" % d["n"]) if d["kind"] == "dialog" else ("Вариант %sдиалога %d" % (("%d " % d["v"]) if d.get("v") else "", d["n"]))
        lines = []
        for ti, turn in enumerate(d["turns"]):
            who, ru, en = turn.split("|", 2)
            cid = "%s-%02d" % (did, ti + 1)
            if who == "-" and not en:
                lines.append({"stage": ru})           # a stage direction, in English
                continue
            if who == "-":
                lines.append({"head": ru, "en": en})   # «У кассы» — where the next lines happen
                continue
            lines.append(line(ru, en, cid, who))
            turns_all.append((ru, en, cid, label, who))
        b = {"t": "dialogue", "kind": d["kind"], "n": d["n"], "label": label, "lines": lines}
        if d.get("v"):
            b["v"] = d["v"]
        if d.get("title"):
            b["title"] = d["title"]
        if d.get("en"):
            b["en"] = d["en"]
        if d.get("setting"):
            b["setting"] = d["setting"]
        blocks.append(b)
    words = les.get("words") or []
    if words:
        blocks.append({"t": "phrases", "title": "Useful words and expressions",
                       "lines": [line(ru, en, "l%02d-w%02d" % (n, wi + 1)) for wi, (ru, en) in enumerate(words)]})
    nums = les.get("numbers") or []
    if nums:
        blocks.append({"t": "phrases", "title": "Numbers",
                       "lines": [line(ru, en, "l%02d-n%02d" % (n, wi + 1)) for wi, (ru, en) in enumerate(nums)]})
    blocks.append(NOTE("%s. Recordings: the course's own tapes, cut to each line. Exercises: the dialogues' own "
                       "lines, and the lesson's words matched to their English." % cite))

    # Exercises. The learner is responsible for the American's lines (the
    # book says so), so those come first.
    rng = random.Random(n)
    ens = [t[1] for t in turns_all]
    fills, mcs = [], []
    for ru, en, cid, label, who in sorted(turns_all, key=lambda t: (t[4] != "А", 0)):
        why = "«%s» — %s%s %s, %s." % (ru, en, "" if en.endswith(("?", "!", ".", "…")) else ".", cite, label)
        ctx = "%s — %s" % (label, cite)
        e = fill_ex(ru, en, cid, why, ctx)
        if e:
            fills.append(e)
        e = mc_ex(ru, en, ens, rng, why, cid, ctx) if (who == "А" or len(mcs) < 8) else None
        if e:
            mcs.append(e)
    matches = []
    pairs = [(ru, en) for ru, en in words if len(ru) <= 40 and len(en) <= 60]
    rng.shuffle(pairs)
    for i in range(0, len(pairs), 5):
        chunk = pairs[i:i + 5]
        if len(chunk) >= 3:
            matches.append({"type": "match", "q": "Match each word to its English. Drag a word onto its meaning, or tap one and then the other.",
                            "pairs": [[ru, en] for ru, en in chunk], "context": "Useful words and expressions — " + cite, "keep": True})
    mcs = mcs[:20]
    matches = matches[:6]
    exs = fills[:30] + mcs[:12] + matches[:4]
    rest = fills[30:] + mcs[12:] + matches[4:]
    s = SEC("f%02d-%s" % (n, SLUGS[n]), "Урок %d · %s" % (n, les["ru"]), blocks, exercises=exs,
            sub=les["en"])
    if rest:
        s["more"] = rest
        s["moreNote"] = "Exercises: more of the lesson's own dialogue lines, with their recordings. " + cite + "."
    SECS.append(s)

COURSE_DEFS = [({"id": "fast", "title": "FSI Russian FAST Course", "short": "FAST", "mark": "F",
                 "blurb": "",
                 "credit": "The Foreign Service Institute's Russian FAST Course (1994), a US Government work in the "
                           "public domain: its dialogues, useful words and cultural notes, with the recordings from "
                           "the course's own tapes",
                 "creditUrl": "https://www.fsi-language-courses.org/russian/courses/fsi-russian-fast-course",
                 "license": "Public domain", "licenseUrl": ""}, SECS)] if SECS else []
