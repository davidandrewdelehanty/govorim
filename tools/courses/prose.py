#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""The lessons' prose, set for reading.

The explanations are quoted from grammar books, which pack a paragraph:
"a. … b. …" run together in one line, the Russian examples in italics
inside the English sentence, a footnote's asterisk breaking the italics,
five sentences to a block. The words stay the source's; this pass changes
only how they are laid out, in the section files under public/courses:

  * a footnote's * (об* … * об before a hard vowel) becomes †, so that the
    italics around examples pair up again;
  * "a. … b. …", "a) … b) …", "1) … 2) …" become a lettered or numbered list
    (a `rule` block with points), the sentence before them its head;
  * a block of more than two sentences is cut into paragraphs of two, an
    example run staying with the sentence that introduces it;
  * the constructions in the English prose — the Russian words, endings
    (-ой, -ами), prepositions, «quoted» forms — are set in bold, and a
    Russian sentence left in roman inside the English is set as an example.

    python3 tools/courses/prose.py            # report
    python3 tools/courses/prose.py --apply    # build_courses.py runs this
"""
import argparse, io, json, os, re, sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
COURSES = os.path.join(ROOT, "public", "courses")
SKIP = {"fast", "stories"}          # dialogues and stories are set their own way

CYR = "А-Яа-яЁё"
ITALIC = re.compile(r"(\*[^*]+\*)")
LATIN = re.compile(r"[A-Za-z]")
# a footnote mark: * after a letter, before space or punctuation, when the
# paragraph's asterisks do not pair up
FOOTNOTE = re.compile(r"(?<=[%sA-Za-z])\*(?=[\s,.;:)])" % CYR)
# an enumeration: a. b. c. / a) b) / (a) (b) / 1) 2) / 1. 2.
MARK = re.compile(r"(?:(?<=^)|(?<=[\s(]))\(?(?:([a-h])|(\d{1,2}))[.)]\s+(?=[A-ZА-ЯЁ«*\"“(])")


def footnotes(t):
    if t.count("*") % 2 == 0:
        return t
    t2 = FOOTNOTE.sub("†", t, count=1)
    return t2 if t2.count("*") % 2 == 0 else t


def sentences(t):
    """Sentences of a paragraph, italic runs kept whole, a sentence that
    ends with a colon joined to the examples that follow it."""
    out, buf = [], ""
    for part in ITALIC.split(t):
        if not part:
            continue
        if ITALIC.fullmatch(part):
            buf += part
            continue
        pieces = re.split(r"(?<=[.!?…])\s+(?=[A-ZА-ЯЁ«„\"“(])", part)
        for i, p in enumerate(pieces):
            if i == 0:
                buf += p
            else:
                out.append(buf.strip()); buf = p
    if buf.strip():
        out.append(buf.strip())
    # a sentence ending in a colon introduces what follows
    merged = []
    for s in out:
        if merged and (merged[-1].rstrip("*").endswith(":") or s.startswith("*") or re.match(r"^[a-zа-яё]", s)):
            merged[-1] += " " + s
        else:
            merged.append(s)
    return merged


def enumeration(t):
    """(head, points, numbered) when the paragraph enumerates, else None."""
    ms = list(MARK.finditer(t))
    if len(ms) < 2:
        return None
    letters = [m.group(1) for m in ms if m.group(1)]
    numbers = [m.group(2) for m in ms if m.group(2)]
    if len(letters) >= 2 and letters[:2] == ["a", "b"]:
        ms = [m for m in ms if m.group(1)]
        numbered = False
    elif len(numbers) >= 2 and numbers[:2] == ["1", "2"]:
        ms = [m for m in ms if m.group(2)]
        numbered = True
    else:
        return None
    # the markers must come in order
    seq = [m.group(1) or m.group(2) for m in ms]
    expect = [chr(ord("a") + i) for i in range(len(seq))] if not numbered else [str(i + 1) for i in range(len(seq))]
    if seq != expect:
        k = next((i for i, (a, b) in enumerate(zip(seq, expect)) if a != b), len(seq))
        if k < 2:
            return None
        ms = ms[:k]
    head = t[:ms[0].start()].strip()
    points = []
    for i, m in enumerate(ms):
        end = ms[i + 1].start() if i + 1 < len(ms) else len(t)
        points.append(t[m.end():end].strip())
    if any(p.count("*") % 2 for p in points) or head.count("*") % 2:
        return None
    return head, points, numbered


RUN = re.compile(r"(?<![%s*\w-])((?:[-‑]?[%s][%s\u0301]*(?:[-‑][%s\u0301]+)*)(?:[ ,/]+(?:[-‑]?[%s][%s\u0301]*(?:[-‑][%s\u0301]+)*))*(?:[-‑](?=[\s,.;)]))?)(?![%s\w*])" % (CYR, CYR, CYR, CYR, CYR, CYR, CYR, CYR))


def emphasise(seg):
    """Russian in an English sentence set bold; a whole Russian sentence
    among the English set as an example (italic)."""
    if not LATIN.search(seg):
        return seg                        # Russian prose: left alone
    # «quoted» forms: bold inside the quotes
    seg = re.sub(r"«([^»]{1,60})»", lambda m: "«**" + m.group(1) + "**»" if re.search("[%s]" % CYR, m.group(1)) and "**" not in m.group(1) else m.group(0), seg)

    def one(m):
        run = m.group(1)
        words = [w for w in re.split(r"[ ,/]+", run) if w]
        if len(words) >= 5 and re.search(r"[.!?…]\s*$", seg[m.end():m.end() + 2] or "") and False:
            return run
        # a list of forms with commas: each form bold on its own
        if "," in run or "/" in run:
            return re.sub(r"([^,/]+)", lambda x: x.group(0) if not x.group(0).strip() else x.group(0).replace(x.group(0).strip(), "**" + x.group(0).strip() + "**", 1), run)
        return "**" + run + "**"
    out, last = [], 0
    for m in RUN.finditer(seg):
        before = seg[last:m.start()]
        if before.count("**") % 2:        # inside a bold already
            continue
        out.append(before)
        out.append(one(m))
        last = m.end()
    out.append(seg[last:])
    s = "".join(out)
    s = s.replace("****", "")
    s = re.sub(r"\*\*([^*]+)\*\*([?!])(?=[\s)»]|$)", r"**\1\2**", s)     # «Где?» keeps its question mark
    return s


def emphasise_para(t):
    parts = ITALIC.split(t)
    return "".join(p if ITALIC.fullmatch(p) or not p else emphasise(p) for p in parts)


def mostly_russian(t):
    cy = len(re.findall("[%s]" % CYR, t)); la = len(LATIN.findall(t))
    return cy > la * 2


def rework(blocks):
    out = []
    changed = False
    for b in blocks:
        if b.get("t") != "p" or not b.get("text") or b.get("set"):
            if b.get("t") == "note" and (b.get("text") or "").startswith("* "):
                b = dict(b, text="† " + b["text"][2:]); changed = True
            out.append(b)
            continue
        t = footnotes(re.sub(r"\s+", " ", b["text"]).strip())
        if mostly_russian(t):
            out.append(dict(b, text=t)); changed = changed or t != b["text"]
            continue
        en = enumeration(t)
        if en:
            head, points, numbered = en
            item = {"text": emphasise_para(head), "points": [emphasise_para(p) for p in points]}
            if numbered:
                item["num"] = True
            out.append({"t": "rule", "items": [item], "set": True})
            changed = True
            continue
        sents = sentences(t)
        if len(sents) > 2 and len(t) > 240:
            # paragraphs of two sentences; a short last one joins the pair before it
            groups = [sents[i:i + 2] for i in range(0, len(sents), 2)]
            if len(groups) > 1 and len(groups[-1]) == 1 and len(groups[-1][0]) < 90:
                groups[-2] += groups[-1]; groups.pop()
            for g in groups:
                out.append({"t": "p", "text": emphasise_para(" ".join(g)), "set": True})
            changed = True
            continue
        t2 = emphasise_para(t)
        out.append(dict(b, text=t2, set=True))
        changed = changed or t2 != b["text"]
    return out, changed


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true")
    ap.add_argument("--course")
    a = ap.parse_args(argv)
    files = touched = 0
    for course in sorted(os.listdir(COURSES)):
        d = os.path.join(COURSES, course)
        if not os.path.isdir(d) or course in SKIP or (a.course and course != a.course):
            continue
        for f in sorted(os.listdir(d)):
            if not f.endswith(".json"):
                continue
            p = os.path.join(d, f)
            doc = json.load(io.open(p, encoding="utf-8"))
            blocks, changed = rework(doc.get("blocks") or [])
            files += 1
            if changed:
                touched += 1
                if a.apply:
                    doc["blocks"] = blocks
                    io.open(p, "w", encoding="utf-8").write(json.dumps(doc, ensure_ascii=False))
    print("prose: %d of %d section files reset for reading%s" % (touched, files, "" if a.apply else " (report only)"))


if __name__ == "__main__":
    main()
