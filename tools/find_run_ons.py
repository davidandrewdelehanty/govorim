#!/usr/bin/env python3
"""Find words in the Synodal source that lost the space between them.

The source drops spaces here and there — "И стал свет" arrives as "И сталсвет",
"вложил персты" as "вложилперсты", "Младенца с Мариею" as "Младенцас Мариею".
About one verse in thirteen has one, and the reader shows text exactly as it
is written.

This finds them and writes tools/synodal_fixes.json, which build_synodal.py
applies. That table is committed, so building the Bible needs neither
pymorphy3 nor a network — only regenerating the table does:

    pip install pymorphy3 pymorphy3-dicts-ru
    python3 tools/find_run_ons.py

A candidate must be a word the Russian morphology dictionary does not know,
cut into pieces that are each a real word attested on its own in this text.
Beyond that there are three tiers, in falling order of confidence:

  1. The join is a word PAIR that occurs elsewhere in this text with a space
     in it. This is the strong test, and it is what separates "сталскот"
     (стал скот) from the real compound "тысяченачальниками", which is not
     "тысяче начальниками" anywhere, and from archaic words like "приидет".

  2. No such pair, but the word cuts cleanly in two, both halves real and
     attested. Needed because a pair often occurs exactly once — in the broken
     instance. "И стал свет" is the whole reason: the phrase appears once in
     Genesis and that once it is joined, so tier 1 can never see it. Both
     halves must be three letters or more here, since without the pair test a
     one-letter piece is far too easy to find.

  3. The word ends in a preposition, which tier 1 and 2 refuse (they would cut
     the real adjective "Израилев" into "Израиле в"). Allowed here only when
     the next word in the verse is one the preposition could govern — "силенна
     земле" is "силен на земле"; "дом Израилев хлебу" is not.

WHAT THIS CANNOT DO is tell a proper name or an archaic form from a run-on.
"Васане" is a place in Bashan, not "вас а не"; "Рахилина" is Rachel's, not
"Рахили на"; "соделал" and "приидет" are simply old words. Those are in SKIP.
Nor does it always cut in the right place when a boundary is ambiguous —
"онидали" is "они дали", not "он и дали". Those are in FIX.

Both lists were made by reading every candidate from all three tiers against
its verse. Anything new this turns up should be read the same way before it is
trusted: the JSON it writes is reviewed data, not raw output.
"""
import collections, io, json, os, re, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.abspath(os.path.join(ROOT, "..", "govorim-sources", "bible"))
OUT = os.path.join(ROOT, "tools", "synodal_fixes.json")
BOOKS = [0, 1, 2, 3, 4, 39, 40, 41, 42]

TOK = re.compile(r"[А-Яа-яЁё]+")
# One-letter words that genuinely exist, so a cut may produce one.
SHORT = set(["с", "в", "к", "о", "у", "и", "а", "я", "ж", "б"])
# Endings tier 1 and 2 will not leave a word on; tier 3 handles them.
TAIL = set(["в", "к", "с", "о", "у", "и", "а", "ж", "б"])
PREP = set(["в", "к", "с", "о", "у", "на", "за", "по", "до", "из", "от", "во",
            "со", "ко", "при", "над", "под", "пред", "без", "для", "про",
            "чрез", "через", "между", "ради"])
NOMINAL = ("NOUN", "ADJF", "ADJS", "NPRO", "NUMR", "PRTF")

# Real words the rules mistake for run-ons: proper names and their possessive
# adjectives (Авраамово, Рахилина), archaic forms the dictionary lacks
# (приидет, соделал), and genuine compounds (стоначальники, beside the
# тысяченачальники it stands next to in Numbers 31).
SKIP = set("""
авраамово авраамову васана васане гадову давидову десятиначальниками иаковлев
израилев израилево израилевы каинана левииных лотана моисеево нимрода предану
приидет приидешь приидите пятидесятиначальниками распяту рахилина рахилиной
ревеккина соделает соделал соделать стоначальники стоначальниками
стоначальников тысяченачальник тысяченачальниками тысяченачальникам
тысяченачальники тысяченачальников
""".split())

# Run-ons written out by hand: ones cut in the wrong place, because a boundary
# can be ambiguous ("онидали" reads as "он и дали" or "они дали", and only the
# verse says which), and one whose halves are both too rare to be found.
FIX = {
    "взялитакже":      "взяли также",
    "виделидела":      "видели дела",
    "вложилперсты":    "вложил персты",
    "вырослии":        "выросли и",
    "инеправедных":    "и неправедных",
    "иудеямиоб":       "иудеями об",
    "нимипоступили":   "ними поступили",
    "онидали":         "они дали",
    "ониузнают":       "они узнают",
    "принадлежитвсем": "принадлежит всем",
    "стоялипред":      "стояли пред",
}


def main():
    try:
        import pymorphy3
    except ImportError:
        sys.exit("pymorphy3 is not installed — see the note at the top of this file.")
    morph = pymorphy3.MorphAnalyzer()

    ru = json.load(io.open(os.path.join(SRC, "ru_synodal.json"), encoding="utf-8-sig"))
    verses = [re.sub(r"\s+", " ", str(v))
              for b in BOOKS for ch in ru[b]["chapters"] for v in ch]

    freq, big = collections.Counter(), collections.Counter()
    for v in verses:
        ws = [w.lower() for w in TOK.findall(v)]
        freq.update(ws)
        big.update(zip(ws, ws[1:]))

    cache = {}
    def known(w):
        if w not in cache:
            cache[w] = morph.parse(w)[0].is_known
        return cache[w]

    def nominal(w):
        return any(p.tag.POS in NOMINAL for p in morph.parse(w))

    def candidate(w):
        return len(w) >= 5 and w not in SKIP and not known(w)

    def cuts(w, limit, minfreq):
        out = []
        def rec(i, parts):
            if len(parts) > limit:
                return
            if i == len(w):
                if len(parts) >= 2:
                    out.append(list(parts))
                return
            for j in range(i + 1, len(w) + 1):
                p = w[i:j]
                if len(p) == 1:
                    if p not in SHORT:
                        continue
                elif freq.get(p, 0) < minfreq or not known(p):
                    continue
                parts.append(p)
                rec(j, parts)
                parts.pop()
        rec(0, [])
        return out

    fixes = {}

    # Tier 1 — the join is attested as a spaced pair somewhere in the text.
    for w in freq:
        if not candidate(w) or len(w) < 6 or w in FIX:
            continue
        best = None
        for seg in cuts(w, 3, 3):
            if seg[-1] in TAIL:
                continue
            ev = [big.get((seg[i], seg[i + 1]), 0) for i in range(len(seg) - 1)]
            if min(ev) < 1:
                continue
            # Fewest pieces first: an ambiguous boundary is far more often one
            # lost space than two.
            score = (-len(seg), min(ev), sum(ev))
            if best is None or score > best[0]:
                best = (score, seg)
        if best:
            fixes[w] = " ".join(best[1])

    # Tier 2 — no attested pair, but the word cuts cleanly in two. Two passes:
    # a common short word may be one of the halves ("с человека", "можно ли"),
    # but only when both halves are common; a rarer half has to be a whole word
    # of three letters or more, or the cut is too easy to find by accident.
    for minfreq, minlen in ((10, 1), (3, 3)):
        for w in freq:
            if not candidate(w) or len(w) < 7 or w in fixes or w in FIX:
                continue
            best = None
            for seg in cuts(w, 2, minfreq):
                if seg[-1] in TAIL or any(len(p) < minlen for p in seg):
                    continue
                score = min(freq[seg[0]], freq[seg[1]])
                if best is None or score > best[0]:
                    best = (score, seg)
            if best:
                fixes[w] = " ".join(best[1])

    # Tier 3 — ends in a preposition the following word can be governed by.
    for v in verses:
        ws = TOK.findall(v)
        for i, tok in enumerate(ws):
            w = tok.lower()
            if not candidate(w) or w in fixes or w in FIX:
                continue
            nxt = ws[i + 1].lower() if i + 1 < len(ws) else ""
            if not (nxt and nominal(nxt)):
                continue
            for j in range(2, len(w)):
                a, b = w[:j], w[j:]
                if b in PREP and freq.get(a, 0) >= 3 and known(a):
                    fixes[w] = a + " " + b
                    break

    fixes.update(FIX)
    for k in FIX:
        if "".join(FIX[k].split()) != k:
            sys.exit("hand-written fix %r does not spell %r" % (FIX[k], k))

    occurrences = sum(freq[w] for w in fixes)
    io.open(OUT, "w", encoding="utf-8").write(
        json.dumps(fixes, ensure_ascii=False, indent=1, sort_keys=True) + "\n")
    print("%d run-on words, %d occurrences -> %s" % (len(fixes), occurrences, OUT))


if __name__ == "__main__":
    main()
