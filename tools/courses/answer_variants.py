#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Accept both spellings of an instrumental: -ою/-ею and -ой/-ей.

Sentences from the library keep their authors' forms — «весною», «зимою»,
«тою», «моею», «нею» — and a reader who writes the everyday «весной» is
right. For every answer word ending in -ою / -ею that the dictionary marks
as the instrumental's long variant (OpenCorpora's V-oy / V-ey), the -ой / -ей
form is added to the accepted answers.

Only in that direction: -ою/-ею is always an instrumental, but -ой/-ей is
just as often a genitive or a dative («ей» is "to her"), so turning those into
-ою would accept wrong answers.

    python3 tools/courses/answer_variants.py            # report
    python3 tools/courses/answer_variants.py --apply    # build_courses.py does this
"""
import argparse, io, itertools, json, os, re

import pymorphy3

M = pymorphy3.MorphAnalyzer()
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.join(os.path.dirname(os.path.dirname(HERE)), "public", "courses")
WORD = re.compile(r"[а-яёА-ЯЁ]+")
_cache = {}


def _ablt(w):
    return any("ablt" in str(p.tag) for p in M.parse(w))


def _only_ablt(w):
    """True when every reading of w that has a case is the instrumental:
    ночью, весной, рукою. Such a word fixes the whole phrase as
    instrumental."""
    cases = [p.tag.case for p in M.parse(w) if p.tag.case]
    return bool(cases) and all(c == "ablt" for c in cases)


def modern(w):
    """The -ой/-ей spelling of a literary instrumental, or None.

    -ою/-ею is only ever an instrumental, so the short form is safe to accept
    whenever it is itself an instrumental — including for words the dictionary
    does not list in the long form at all («тою», «сею»)."""
    lw = w.lower()
    if lw in _cache:
        out = _cache[lw]
    else:
        out = None
        if lw.endswith(("ою", "ею")) and len(lw) > 2:
            cand = lw[:-1] + "й"
            known_other = M.word_is_known(lw) and not _ablt(lw)
            # A pronoun or adjective (тот, этот, сей, одна, такой…) is where
            # -ою is the classic literary instrumental; the dictionary knowing
            # «тою» only as the dative of the rare noun «той» (a feast) must
            # not block it.
            adj_ablt = any("ablt" in str(p.tag) and any(x in str(p.tag) for x in ("ADJF", "PRTF", "Apro", "NUMR"))
                           for p in M.parse(cand))
            if _ablt(cand) and (adj_ablt or not known_other):
                out = cand
        _cache[lw] = out
    if out and w[:1].isupper():
        out = out[:1].upper() + out[1:]
    return out


def literary(w):
    """The -ою/-ею spelling of an instrumental -ой/-ей («той» -> «тою»)."""
    lw = w.lower()
    if not lw.endswith(("ой", "ей")) or len(lw) < 3 or not _ablt(lw):
        return None
    out = lw[:-1] + "ю"
    if w[:1].isupper():
        out = out[:1].upper() + out[1:]
    return out


def variants(answer, next_word=""):
    """Other spellings to accept. Literary -ою -> modern -ой always; modern
    -ой -> literary -ою only where the phrase is certainly instrumental: some
    word of the answer, or the word right after the blank, can be nothing but
    an instrumental («той ночью», «___ ночью» with «той» in the blank)."""
    parts = re.split(r"([\u0430-\u044f\u0451\u0410-\u042f\u0401]+)", answer)
    words = [parts[i] for i in range(1, len(parts), 2)]
    instr_phrase = any(_only_ablt(x) or (modern(x) is not None) for x in words) or \
        (next_word and _only_ablt(next_word))
    opts = []
    for i, part in enumerate(parts):
        if i % 2 == 1:
            alt = [part]
            m = modern(part)
            if m and m != part:
                alt.append(m)
            if instr_phrase:
                l = literary(part)
                if l and l != part:
                    alt.append(l)
            opts.append(alt)
        else:
            opts.append([part])
    out = ["".join(x) for x in itertools.product(*opts)]
    return [o for o in out if o != answer][:15]


def fix_hint(e):
    """«в летах», «не по летам»: the dictionary files летах under год, so the
    hint read «(годы)» — and nobody can get from годы to летах. The hint names
    the word actually used, лета."""
    ans = (e.get("answers") or [""])[0].lower().split()
    q = e.get("q") or ""
    if not ans or not ans[-1].startswith("лет") or ans[-1] == "лет":
        return False
    m = re.search(r"___ \(([^)]*)\)", q)
    if not m or not re.search(r"\bгод(ы|а)?\b", m.group(1)):
        return False
    hint = re.sub(r"\bгод(ы|а)?\b", "лета", m.group(1))
    e["q"] = q[:m.start(1)] + hint + q[m.end(1):]
    return True


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true")
    a = ap.parse_args(argv)
    added = files = hints = 0
    for course in sorted(os.listdir(ROOT)):
        d = os.path.join(ROOT, course)
        if not os.path.isdir(d):
            continue
        for fn in sorted(os.listdir(d)):
            if not fn.endswith(".json"):
                continue
            p = os.path.join(d, fn)
            sec = json.load(io.open(p, encoding="utf-8"))
            changed = False
            for e in sec.get("exercises") or []:
                if fix_hint(e):
                    hints += 1
                    changed = True
                ans = list(e.get("answers") or [])
                q = e.get("q") or ""
                after = re.sub(r"^\s*\([^)]*\)", "", q[q.find("___") + 3:]) if "___" in q else ""
                nxt = (WORD.findall(after) or [""])[0]
                for x in list(ans):
                    for v in variants(x, nxt):
                        if v not in ans:
                            ans.append(v)
                            added += 1
                            changed = True
                e["answers"] = ans
            if changed:
                files += 1
                if a.apply:
                    io.open(p, "w", encoding="utf-8").write(json.dumps(sec, ensure_ascii=False, separators=(",", ":")))
    print("instrumental spellings accepted: %d added; лета hints fixed: %d; %d sections%s"
          % (added, hints, files, "" if a.apply else " (report only)"))


if __name__ == "__main__":
    main()
