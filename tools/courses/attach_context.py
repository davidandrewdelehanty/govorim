#!/usr/bin/env python3
"""Give every course exercise the explanation its own lesson already contains.

The courses were built in two halves: a teaching lesson carrying DLI/Wikibooks
rules in `blocks` and NO exercises, and practice files carrying exercises whose
`why` is only a citation — "Sentence and translation from Tatoeba", "From
Достоевский, «Преступление и наказание»". Provenance, not teaching: it tells a
learner nothing about why the answer is what it is.

Nothing here is written by a machine. The text attached to an exercise is the
lesson's own sourced prose, carried across verbatim, with the lesson's source
note kept alongside it.

  context  one line, shown above the question: what is being practised, cited
  why      the fuller rule, shown once answered, with the sentence's own citation

    cd /mnt/c/Users/david/projects/govorim-app
    python3 tools/courses/attach_context.py            # report only
    python3 tools/courses/attach_context.py --apply
"""
import argparse, io, json, os, re

ROOT = "public/courses"
# Blocks that carry teaching prose. Tables and example pairs are referenced but
# not inlined — they do not read well as a one-line context.
PROSE = ("p", "h")
BORING = re.compile(r"^\s*(memorize|study|note|read|repeat|listen|practice|review)\b", re.I)


def text_of(b):
    return re.sub(r"\s+", " ", (b.get("text") or "")).strip()


def lesson_rule(doc):
    """(one-line context, fuller rule, source note) taken verbatim from the lesson."""
    src = ""
    paras, heads = [], []
    blocks = doc.get("blocks") or []
    # the note after each block: a lesson quoting several sources cites each after the text it covers
    after, nxt = [""] * len(blocks), ""
    for i in range(len(blocks) - 1, -1, -1):
        if blocks[i].get("t") == "note":
            nxt = text_of(blocks[i])
        after[i] = nxt
    first_src = ""
    for bi, b in enumerate(blocks):
        t = b.get("t")
        if t == "note" and not src:
            src = text_of(b)
            continue
        if t not in PROSE:
            continue
        if t == "p" and not paras and after[bi]:
            first_src = after[bi]
        s = text_of(b)
        s = re.sub(r"^\*+|\*+$", "", s).strip()              # drop *emphasis* wrappers
        s = re.sub(r"^\(?\d+[.)]\s*|^[a-zа-я][.)]\s*", "", s)  # drop "1." / "a)" enumeration
        if len(s) < 25 or BORING.match(s):
            continue
        if t == "h":
            heads.append(s)
            continue
        # A lead-in ("…remember the following:") announces the rule, it is not
        # the rule. Keep it out of the one-line context.
        if s.rstrip().endswith(":"):
            continue
        paras.append(s)
    if not paras:
        # The lesson teaches through tables and example pairs rather than prose.
        # Say what it covers rather than inventing an explanation for it.
        label = (heads[0] if heads else re.sub(r"\s+", " ", doc.get("title") or "").strip())
        return label, label, src
    if first_src:
        src = first_src
    full = " ".join(paras[:3])
    if len(full) > 700:
        full = full[:700].rsplit(" ", 1)[0] + "\u2026"
    first = re.split(r"(?<=[.!?])\s+", paras[0])[0]
    if len(first) > 220:
        first = first[:220].rsplit(" ", 1)[0] + "\u2026"
    return first, full, src


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true")
    ap.add_argument("--course", help="limit to one course folder")
    args = ap.parse_args(argv)

    touched = exercises = skipped = nolesson = 0
    for course in sorted(os.listdir(ROOT)):
        d = os.path.join(ROOT, course)
        if not os.path.isdir(d) or (args.course and course != args.course):
            continue
        stems = {f[:-5] for f in os.listdir(d) if f.endswith(".json")}
        # A teaching lesson is any file that is not a practice file. Some of them
        # carry a few exercises of their own as well as the rule, so they are
        # both a source of explanation and a target for one.
        rules = {}
        for stem in stems:
            if re.search(r"-practice(?:-\d+)?$", stem):
                continue
            doc = json.load(io.open(os.path.join(d, stem + ".json"), encoding="utf-8"))
            rules[stem] = lesson_rule(doc)
        for stem in sorted(stems):
            m = re.match(r"^(.*?)-practice(?:-\d+)?$", stem)
            base = m.group(1) if m else stem
            if base not in rules:
                continue
            ctx, full, src = rules[base]
            if not ctx:
                nolesson += 1
                continue
            p = os.path.join(d, stem + ".json")
            doc = json.load(io.open(p, encoding="utf-8"))
            if doc.get("stream"):
                # A practice stream keeps one explanation per kind of drill
                # (`whys`, `ctxs`), given by its builder; nothing to add.
                continue
            changed = False
            for e in doc.get("exercises") or []:
                exercises += 1
                if (e.get("context") or "").strip():
                    # The builder already gave this one its own explanation
                    # (tools/courses/tables_course.py does). Leave it alone.
                    skipped += 1
                    continue
                cite = (e.get("why") or "").strip()
                newctx = ctx + (" (%s)" % src.rstrip(".") if src else "")
                newwhy = full + (" — %s" % src if src else "")
                if cite and cite not in newwhy:
                    newwhy += "  ·  " + cite
                if e.get("context") == newctx and e.get("why") == newwhy:
                    skipped += 1
                    continue
                e["context"] = newctx
                e["why"] = newwhy
                changed = True
            if changed and args.apply:
                io.open(p, "w", encoding="utf-8").write(json.dumps(doc, ensure_ascii=False))
            if changed:
                touched += 1
    print("practice files touched : %d" % touched)
    print("exercises covered      : %d" % exercises)
    print("already up to date     : %d" % skipped)
    print("lessons with no usable prose: %d" % nolesson)
    if not args.apply:
        print("\nreport only — add --apply to write")


if __name__ == "__main__":
    main()
