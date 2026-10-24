# -*- coding: utf-8 -*-
"""One explanation per exercise, after the answer, without the clutter.

Every course used to show the same rule text twice (`context` above the question and `why` after the answer) and
ended each explanation with a source line («— From the DLI Grammar Reference Book, Lessons 35, 36, 41, 66.»,
«· Sentence and translation from Tatoeba (CC BY 2.0 FR).», «— DLI Grammar Reference Book; OpenCorpora dictionary…»,
«· From Антон Чехов, «На даче»»).  The sources are in each course's credit line (and the author is the exercise's `prompt`).
This pass: clears `context`, strips those source tails, and in the case courses drops the full declension rows and the
long general-rule quotes that every word of a case follows.  Idempotent.
Usage: tidy_explanations.py [--apply] [--course ID ...]
"""
import io, json, os, re, sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
COURSES = os.path.join(ROOT, "public", "courses")
SKIP = {"count"}                      # count_explain.py writes its own
CASE_LIST = ["cases", "case-nom", "case-gen", "case-dat", "case-acc", "case-ins", "case-prp"]
CASE = set(CASE_LIST)

NUMS = r"[\d–\-, and;]+"
TAILS = [
    r"\s*[—–]\s*DLI Grammar Reference Book; OpenCorpora dictionary \(CC BY-SA 4\.0\)\.?",
    r"\s*[—–]\s*(?:From the )?DLI Grammar Reference Book(?:\.|,)?(?:\s*Lessons?\s*" + NUMS + r"(?:,\s*pp?\.\s*[\d–\-]+)?)?\.?",
    r"\s*[—–]\s*(?:From the )?DLI Grammar Reference Book\.?\s*Lessons?\s*" + NUMS + r"\.?",
    r"\s*[—–]\s*DLI(?:,\s*Lessons?\s*" + NUMS + r"(?:\s*\(p\.?\s*\d+\))?)?(?:;\s*Wikibooks,\s*«[^»]*»)?\.?",
    r"\s*\(DLI,\s*Lessons?\s*[^)]*\)\.?",
    r"\s*[·•]\s*Sentence and translation from Tatoeba \(CC BY 2\.0 FR\)\.?",
    r"\s*[·•]\s*Sentence from Tatoeba[^.]*\.?",
    r"\s*(?:[·•]\s*|\.\s+)?From [^.·«]{3,70}, «[^»]*»(?: \([^)]*\))?\.?",
]
TAIL_RES = [re.compile(t) for t in TAILS]


def strip_tails(w):
    prev = None
    while prev != w:
        prev = w
        for r in TAIL_RES:
            w = r.sub("", w)
        w = w.strip()
        w = re.sub(r"\s*[·•—–]\s*$", "", w)
    return w


def trim_case(w):
    """Case courses: keep «form → answer (case). Declines like … Ending … agreeing with …»; the declension row and general-rule quotes go
    unless short and specific."""
    w = re.sub(r"\s*Declension: .*?(?=\s{2}|$)", "", w)
    # «Declines like газета (G. sg. газеты).»  ->  «Declines like газета.»; a note after «;» stays
    w = re.sub(r"(Declines like [\wё-]+) \([A-Z]\.[^;)]*\)", r"\1", w)
    w = re.sub(r"(Declines like [\wё-]+) \([A-Z]\.[^;)]*;\s*([^)]*)\)", r"\1 (\2)", w)
    w = re.sub(r"(Declines like [\wё-]+) \([^)]*= [GN][^)]*\)", r"\1", w)
    w = w.replace("No change of ending: here the accusative is the same as the nominative.", "Accusative = nominative.")
    parts = re.split(r"\s{2,}", w)
    heads = " ".join(parts[:1] + [p for p in parts if p.startswith("**")])
    stems = set()
    for a_, b_ in re.findall(r"\*\*([^*→]+?) → ([^*]+?)\*\*", heads):
        for x in (a_, b_):
            for t in re.findall(r"[А-Яа-яЁё]{5,}", x):
                stems.add(t.lower().replace("ё", "е")[:4])
    keep, quoted = [], False
    for p in parts:
        q = re.search(r"«([^»]*)»", p)
        if p.startswith("«"):
            txt = p.lower().replace("ё", "е")
            if quoted or len(q.group(1) if q else p) > 200 or not any(t in txt for t in stems):
                continue          # a general rule that does not mention this word
            quoted = True
        keep.append(p)
    return "  ".join(x for x in keep if x.strip())


def tidy_exercise(e, case):
    w = e.get("why") or ""
    w2 = strip_tails(w)
    if case:
        w2 = trim_case(w2)
    w2 = re.sub(r"\s{3,}", "  ", w2).strip()
    changed = (w2 != w) or bool(e.get("context"))
    e["why"] = w2
    e["context"] = ""
    return changed


def iter_files(only):
    for cid in sorted(os.listdir(COURSES)):
        if cid in SKIP or (only and cid not in only):
            continue
        d = os.path.join(COURSES, cid)
        if not os.path.isdir(d):
            continue
        for fn in sorted(os.listdir(d)):
            if fn.endswith(".json") and fn != "exam.json":
                yield cid, os.path.join(d, fn)


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    apply = "--apply" in argv
    only = set()
    if "--course" in argv:
        i = argv.index("--course")
        only = set(a for a in argv[i + 1:] if not a.startswith("--"))
    stats = {}
    for cid, p in iter_files(only):
        try:
            j = json.load(io.open(p, encoding="utf-8"))
        except ValueError:
            continue
        ex = j.get("exercises") or []
        n = 0
        for e in ex:
            if isinstance(e, dict) and tidy_exercise(e, cid in CASE):
                n += 1
        if n:
            stats[cid] = stats.get(cid, 0) + n
            if apply:
                io.open(p, "w", encoding="utf-8").write(json.dumps(j, ensure_ascii=False))
    print("tidy_explanations:", stats, "" if apply else "(dry run)")


if __name__ == "__main__":
    main()
