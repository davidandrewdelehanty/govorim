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
    """A gender is named only where the dictionary's forms differ by gender for that number and case (один / одна /
    одно, две / два); where all three genders give the same form (десять тысяч) none is named. Genders sharing a form
    are named together (двадцати одного: masculine or neuter)."""
    out = []
    for n in NUMS:
        def by_gender(case, anim=None):
            got = {}
            for g in ("masc", "femn", "neut"):
                try:
                    f = tuple(uniq(G.cardinal(n, case, g) if anim is None else G.cardinal(n, case, g, anim)))
                except Exception as e:
                    print("skip card", n, g, case, e); continue
                got.setdefault(f, []).append(G1[g])
            return got
        num = "s" if n == 1 else ""
        for c in CASES:
            groups = by_gender(c)
            for f, gs in groups.items():
                out.append([n, c, "" if len(groups) == 1 else "".join(gs), num, "", list(f)])
        # The accusative, gender by gender: animacy is named only where it changes this gender's form, and a form
        # that is simply the nominative's again is not asked for.
        acc = {}
        for g in ("masc", "femn", "neut"):
            try:
                fn = tuple(uniq(G.cardinal(n, "nomn", g)))
                fi = tuple(uniq(G.cardinal(n, "accs", g, False)))
                fa = tuple(uniq(G.cardinal(n, "accs", g, True)))
            except Exception as e:
                print("skip card acc", n, g, e); continue
            if fi == fa:
                if fi != fn: acc.setdefault((fi, ""), []).append(G1[g])
            else:
                if fi != fn: acc.setdefault((fi, "i"), []).append(G1[g])
                acc.setdefault((fa, "a"), []).append(G1[g])
        one = len({f for f, t in acc}) == 1 and len(acc) == 1 and len(acc[next(iter(acc))]) == 3
        for (f, tag), gs in acc.items():
            out.append([n, "accs", "" if one else "".join(gs), num, tag, list(f)])
        if n == 1:                                       # одни: the plural (одни сутки, одни ножницы)
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
