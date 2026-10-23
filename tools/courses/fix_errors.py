# -*- coding: utf-8 -*-
"""Mechanical clean-up of every course after it is built: what the audits (audit_deep.py and friends) found to be wrong.

  markup     raw wiki markup in lesson blocks and quotes (''' [[ ]] {{ }}), broken ** / * pairs, a stray acute after a hint
  spacing    leading / trailing / double spaces in a question
  duplicate  the same exercise twice in one section
  reject     exercises that cannot be right and are dropped (listed with the reason in tools/courses/_dropped/fix_errors.json):
               - pre-1918 spelling (ъ at the end of a word)
               - a hint word the dictionary does not know (the lemma was back-formed from the sentence: нонкий → нонче)
               - a verb hint whose answer is a noun in its sentence (бреду, слёз, набег, еду …)
               - typos in the sentence or the answer, found by reading the words the dictionary does not know
Needs pymorphy3 for `reject`.   Usage: fix_errors.py [--apply] [--course ID]
"""
import argparse, io, json, os, re, sys
from collections import Counter, defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
COURSES = os.path.join(ROOT, "public", "courses")
WORD = re.compile(r"[А-Яа-яЁё]+(?:-[А-Яа-яЁё]+)?")
norm = lambda w: w.lower().replace("ё", "е")

# hint repairs: pymorphy's lemma for these forms is the wrong verb
HINT_FIX = {"живить": "жить"}
# a hint word that is real although the dictionary lacks it
HINT_KEEP = {"пресчастливый"}
# typos found by reading every word the dictionary does not know (answer or sentence)
TYPO = ["подхдящ", "эмоцилнально", "обьяснить", "всё-же", "по-французки", "восьмиста", "неуверенна", "ездиют"]      # whole words
# (answer, text that the sentence contains): a noun / a name where the hint asks for a verb, or the wrong verb
MANUAL = [
    ("еду", "купить"), ("слезу", "смахнула"), ("Набеги", "на сонных"), ("набеги", "германцев"), ("набегу", "подвергся"),
    ("Кати", "Вольф"), ("Вели", "чаю дать"), ("побеги", "дикие"), ("погони", "недолгой"),
]


def unwiki(s):
    """Wikibooks markup → the app's markup (**bold**, *italic*); templates and stray brackets removed."""
    s = re.sub(r"\{\{[^}]*\}\}", "", s)
    s = re.sub(r"\[\[(?:[^|\]]*\|)?([^\]]*)\]\]", r"\1", s)
    s = re.sub(r"'''''(.+?)'''''", r"**\1**", s)
    s = re.sub(r"'''(.+?)'''", r"**\1**", s)
    s = re.sub(r"''(.+?)''", r"*\1*", s)
    s = s.replace("[[", "").replace("]]", "").replace("{{", "").replace("}}", "")
    s = re.sub(r"\(\s*\)", "", s)
    return re.sub(r"[ \t]{2,}", " ", s).strip()


INVIS = re.compile("[\u00ad\u200b\u200c\u200d\u2060\ufeff]")
WIKI = re.compile(r"\[\[|\]\]|\{\{|\}\}|'''|''")


def fix_item(item):
    """An interlinear example [ru, en] whose wiki links were split at their own '|'."""
    if not isinstance(item, list) or not any(isinstance(x, str) and WIKI.search(x) for x in item):
        return item
    s = unwiki("|".join(str(x) for x in item))
    parts = [p.strip() for p in s.split("|")]
    if len(item) == 2 and len(parts) >= 2:
        return [parts[0], " ".join(parts[1:])] if len(parts) > 2 else parts
    return [unwiki(str(x)) for x in item]


def fix_block(b):
    if isinstance(b, str):
        return unwiki(b) if WIKI.search(b) else b
    if isinstance(b, list):
        return [fix_block(x) for x in b]
    if isinstance(b, dict):
        out = {}
        for k, v in b.items():
            if k == "items" and isinstance(v, list) and v and all(isinstance(i, list) for i in v):
                out[k] = [fix_item(i) for i in v]
                out[k] = [[fix_block(c) for c in i] for i in out[k]]
            else:
                out[k] = fix_block(v)
        return out
    return b


def tidy_markup(w):
    """A quote cut out of the middle of a DLI paragraph starts or ends inside an emphasis: «…на поезд?* Notice also …**»."""
    if not w:
        return w
    if w.count("*") % 2 and re.match(r"^[^*]{0,170}?[.?!…»\"”)]\*{1,2}\s", w):
        w = re.sub(r"^[^*]{0,170}?[.?!…»\"”)]\*{1,2}\s+", "", w, count=1)
    if w.count("**") % 2:
        i = w.rfind("**")
        w = w[:i] + w[i + 2:]
    if w.replace("**", "").count("*") % 2:
        j = [m.start() for m in re.finditer(r"(?<!\*)\*(?!\*)", w)]
        if j:
            w = w[:j[-1]] + w[j[-1] + 1:]
    return w


def fix_text(s):
    return unwiki(s) if WIKI.search(s) else s


def exercises_of(j):
    out = list(j.get("exercises") or [])
    for t in j.get("topics") or []:
        out += t.get("exercises") or []
    return out


def reject_reason(M, e, cid):
    if e.get("type") != "fill":
        return None
    q = e.get("q") or ""
    a0 = (e.get("answers") or [""])[0]
    low = norm(q + " " + a0)
    if re.search(r"[а-яё]ъ(?![а-яё])", low):
        return "pre-1918 spelling"
    for t in TYPO:
        if re.search(r"(?<![а-яё-])" + re.escape(norm(t)) + r"(?![а-яё])", low):
            return "typo: " + t
    for ans, ctx in MANUAL:
        if a0 == ans and ctx in q:
            return "noun/name/other verb where the hint asks for a verb: " + ans
    m = re.search(r"___ \(([^)]*)\)", q)
    if not m:
        return None
    hint = re.sub(r"\s+—.*$", "", re.sub(r",\s*(nom|gen|dat|acc|instr|prep)\.\s*(sg|pl)\..*$", "", m.group(1))).strip()
    if re.search(r"[A-Za-z\d+]", hint):
        return None
    hw = WORD.findall(hint.split("/")[0])
    for h in hw:
        if len(h) >= 3 and norm(h) not in HINT_KEEP and not any(p.is_known for p in M.parse(h)):
            return "hint word not in the dictionary: " + h
    # a verb hint, a preposition or an adjective in front of the blank, and the answer reads as a noun: «в бреду», «до слёз», «дикие побеги»
    if cid.startswith("case") or cid == "cases" or cid in ("tables", "numerals"):
        return None
    if len(hw) == 1 and any(p.tag.POS == "INFN" for p in M.parse(hw[0])[:1]):
        aw = WORD.findall(a0)
        if aw:
            top = M.parse(aw[-1])[0]
            if top.tag.POS not in ("VERB", "INFN", "GRND", "PRTF", "PRTS") and top.tag.POS in ("NOUN", "ADVB", "NPRO"):
                toks = re.findall(r"[А-Яа-яЁё]+|[^\sА-Яа-яЁё]", q[:m.start()])
                if toks:
                    prev = toks[-1].lower()
                    ps = M.parse(prev)
                    if prev in ("в", "на", "до", "от", "из", "с", "со", "после", "перед", "без", "для", "про", "за", "под", "над", "при", "о", "об", "у", "к", "по", "из-за") or \
                            (ps and ps[0].tag.POS in ("ADJF", "PRTF") and len(toks) > 0):
                        return "verb hint, noun in the sentence: " + a0
    return None


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true")
    ap.add_argument("--course"); ap.add_argument("--all", action="store_true")
    a = ap.parse_args(argv)
    try:
        import pymorphy3
        M = pymorphy3.MorphAnalyzer()
    except ImportError:
        M = None
        print("fix_errors: pymorphy3 not installed — no exercises rejected")
    st, dropped, changed_courses = Counter(), [], set()
    for cid in sorted(os.listdir(COURSES)):
        d = os.path.join(COURSES, cid)
        if cid.startswith("_") or not os.path.isdir(d) or (a.course and cid != a.course):
            continue
        for fn in sorted(os.listdir(d)):
            if not fn.endswith(".json"):
                continue
            p = os.path.join(d, fn)
            raw = io.open(p, encoding="utf-8").read()
            j = json.loads(raw)
            exam = fn == "exam.json"
            before = json.dumps(j, ensure_ascii=False, separators=(",", ":"))

            def clean(e):
                if isinstance(e.get("answers"), list):
                    e["answers"] = [INVIS.sub("", x) if isinstance(x, str) else x for x in e["answers"]]
                for fld in ("q", "why", "context", "prompt"):
                    if isinstance(e.get(fld), str):
                        s = INVIS.sub("", e[fld])
                        if fld == "q":
                            s2 = re.sub(r"[ \t]{2,}", " ", s).strip()
                            s2 = re.sub(r"\)́", ")", s2)
                            for bad, good in HINT_FIX.items():
                                s2 = s2.replace("(" + bad + ")", "(" + good + ")")
                            if s2 != s: st["spacing/hint"] += 1
                            s = s2
                        if fld in ("why", "context") and "[[" in s:
                            s = ""                                  # a quote cut out of a corrupted example: no explanation is better than a broken one
                            st["wiki quote removed"] += 1
                        elif fld == "why":
                            s2 = tidy_markup(s)
                            if s2 != s: st["markup tidied"] += 1
                            s = s2
                        e[fld] = s
                return e

            def process(exs):
                keep, seen = [], set()
                for e in exs:
                    e = clean(e)
                    key = (re.sub(r"\s+", " ", (e.get("q") or "").lower()), tuple(map(norm, e.get("answers") or [str(e.get("answer"))])), tuple(map(str, e.get("options") or [])), e.get("why") if e.get("type") == "mc" else None)
                    if key in seen:
                        st["duplicate"] += 1
                        dropped.append({"course": cid, "file": fn, "q": e.get("q"), "answers": e.get("answers"), "reason": "duplicate in the same section"})
                        continue
                    seen.add(key)
                    why = reject_reason(M, e, cid) if M else None
                    if why:
                        st["rejected"] += 1
                        dropped.append({"course": cid, "file": fn, "q": e.get("q"), "answers": e.get("answers"), "reason": why})
                        continue
                    keep.append(e)
                return keep

            if exam:
                for t in j.get("topics") or []:
                    t["exercises"] = process(t.get("exercises") or [])
            else:
                j["exercises"] = process(j.get("exercises") or [])
                new_blocks = fix_block(j.get("blocks") or [])
                if new_blocks != (j.get("blocks") or []):
                    st["blocks repaired"] += 1
                    j["blocks"] = new_blocks
            after = json.dumps(j, ensure_ascii=False, separators=(",", ":"))
            if after != before:
                changed_courses.add(cid)
                if a.apply:
                    io.open(p, "w", encoding="utf-8").write(json.dumps(j, ensure_ascii=False))
    print("fix_errors:", dict(st), "| courses changed:", sorted(changed_courses))
    if a.apply and dropped:
        od = os.path.join(HERE, "_dropped")
        if not os.path.isdir(od):
            os.makedirs(od)
        pp = os.path.join(od, "fix_errors.json")
        old = []
        if os.path.exists(pp):
            try:
                old = json.load(io.open(pp, encoding="utf-8"))
            except Exception:
                old = []
        seen = {(o.get("course"), o.get("file"), o.get("q")) for o in old}
        old += [x for x in dropped if (x["course"], x["file"], x["q"]) not in seen]
        io.open(pp, "w", encoding="utf-8").write(json.dumps(old, ensure_ascii=False, indent=1))
    if not a.apply:
        c = Counter((x["course"], x["reason"].split(":")[0]) for x in dropped)
        for k, v in sorted(c.items()):
            print("  ", k, v)
        for x in dropped[:(400 if "--all" in sys.argv else 0)]:
            print("   ", x["course"], x["reason"][:50], "|", (x["q"] or "")[:60], (x["answers"] or [])[:1])
    return changed_courses


if __name__ == "__main__":
    main()
