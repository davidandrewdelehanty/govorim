# -*- coding: utf-8 -*-
"""Data for the Vocab tab's numeral practice: a digit, a case (and singular or plural, gender and animacy where the
form depends on them) → the word to type.  Every form is the OpenCorpora dictionary's own (through gen_numerals.py /
paradigms.py), put together by the DLI Grammar Reference Book's rules that gen_numerals.py quotes — nothing is written here.
    python3 tools/courses/gen_numeral_drill.py      →  public/vocab/numeral-forms.json
Item: [n, case, gender, number, animacy, [accepted answers]]
  case  nomn gent datv accs ablt loct      gender  m f n or ""      number  s p or ""      animacy  a (animate) i (inanimate) or "" """
import io, json, os, sys
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import gen_numerals as G

ROOT = os.path.dirname(os.path.dirname(HERE))
CASES = ["nomn", "gent", "datv", "ablt", "loct"]
G1 = {"masc": "m", "femn": "f", "neut": "n"}
NUMS = list(range(1, 101)) + list(range(200, 1000, 100)) + [101, 111, 121, 132, 143, 154, 199, 201, 215, 222, 333, 456, 999] + \
       [1000, 2000, 3000, 5000, 10000, 20000, 100000, 1000000]


def uniq(xs):
    return list(dict.fromkeys(xs))


def card_genders(n):
    r = n % 100
    if n < 1000000 and n % 1000 != 0:
        if n % 10 == 1 and r != 11:
            return ["masc", "femn", "neut"]
        if n % 10 == 2 and r != 12:
            return ["masc", "femn"]
    return ["masc"]


def cardinals():
    """Every item names the gender of the noun counted, even where the numeral's form is the same for all three
    (тридцати пяти книг / столов / окон): the learner is always told the whole form, never left to guess."""
    out = []
    for n in NUMS:
        for g in ("masc", "femn", "neut"):
            gl = G1[g]
            try:
                nom = G.cardinal(n, "nomn", g)
                for c in CASES:
                    out.append([n, c, gl, "s" if n == 1 else "", "", uniq(G.cardinal(n, c, g))])
                inan = G.cardinal(n, "accs", g, False)
                an = G.cardinal(n, "accs", g, True)
            except Exception as e:
                print("skip card", n, g, e)
                continue
            if inan != nom:
                out.append([n, "accs", gl, "s" if n == 1 else "", "i" if an != inan else "", uniq(inan)])
            if an != inan:
                out.append([n, "accs", gl, "s" if n == 1 else "", "a", uniq(an)])
        if n == 1:                                       # одни: the plural (одни сутки, одни ножницы)
            lex = G.lex("один")
            def pl(*t):
                return uniq(G.forms("один", *t))
            for c in CASES:
                out.append([1, c, "", "p", "", pl(c, "plur")])
            out.append([1, "accs", "", "p", "a", pl("accs", "plur", "anim")])
    return out


def ordinals():
    out = []
    for n in NUMS:
        for g, num in (("masc", "sing"), ("femn", "sing"), ("neut", "sing"), ("masc", "plur")):
            gl = G1[g] if num == "sing" else ""
            pl = "s" if num == "sing" else "p"
            try:
                nom = G.ordinal(n, "nomn", g, num)
                for c in CASES:
                    out.append([n, c, gl, pl, "", uniq(G.ordinal(n, c, g, num))])
                inan = G.ordinal(n, "accs", g, num, False)
                an = G.ordinal(n, "accs", g, num, True)
            except Exception as e:
                print("skip ord", n, g, num, e)
                break
            if g == "neut":
                continue                                  # accusative neuter = nominative
            if inan != nom:
                out.append([n, "accs", gl, pl, "", uniq(inan)])
            if an != inan:
                out.append([n, "accs", gl, pl, "a", uniq(an)])
    return out


def main():
    c, o = cardinals(), ordinals()
    path = os.path.join(ROOT, "public", "vocab", "numeral-forms.json")
    io.open(path, "w", encoding="utf-8").write(json.dumps({"v": 1, "c": c, "o": o}, ensure_ascii=False, separators=(",", ":")))
    print("cardinal items", len(c), "ordinal items", len(o), "bytes", os.path.getsize(path))


if __name__ == "__main__":
    main()
