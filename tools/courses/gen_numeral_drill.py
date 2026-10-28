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


# ---------------------------------------------------------------- sentence context
# Every question is put in a short sentence: a preposition (or a frame) that requires the case, the blank for the
# number, and one of four countable objects in the form the number calls for. The noun forms are OpenCorpora's own
# (pymorphy3); which form the number takes is the DLI rule set gen_numerals.py quotes:
#   один (and compounds ending in it) agrees with the noun in the singular; 2-4 (not 12-14) and above take the
#   genitive singular / plural after the nominative and inanimate accusative; animate двух/трёх/четырёх take the
#   accusative (= genitive) plural; in the oblique cases «the numbers always agree in case with the noun» — plural;
#   тысяча, миллион «are used and declined as nouns» — the noun after them is always genitive plural.
# Item fields added: [6] noun form "case:s|p", [7] the noun keys that fit (gender, animacy).
NOUNS = {   # key: lemma, tail kept as is, gender, animate
    "b": ("бутылка", " пива", "f", False),
    "s": ("стакан", "", "m", False),
    "y": ("яблоко", "", "n", False),
    "k": ("кот", "", "m", True),
    "z": ("ножницы", "", "", False),          # only for одни / одних (plural of один, with a plural-only noun)
}
OBJ = "bsyk"


def noun_forms():
    import pymorphy3
    m = pymorphy3.MorphAnalyzer()
    out = {}
    for k, (lemma, tail, g, an) in NOUNS.items():
        p = [x for x in m.parse(lemma) if "NOUN" in x.tag and x.normal_form == lemma][0]
        f = {}
        for c in ["nomn", "gent", "datv", "accs", "ablt", "loct"]:
            for num, t in (("s", "sing"), ("p", "plur")):
                w = p.inflect({c, t})
                if w: f[c + ":" + num] = w.word + tail
        out[k] = f
    return out


def card_spec(n, case, tag, num):
    if n == 1 and num == "p":
        return case + ":p"
    if n % 1000 == 0:
        return "gent:p"
    r, d = n % 100, n % 10
    if d == 1 and r != 11:
        return case + ":s"
    if case in ("nomn", "accs"):
        if 2 <= d <= 4 and not 12 <= r <= 14:
            return "accs:p" if tag == "a" else "gent:s"
        return "gent:p"
    return case + ":p"


def fit(gender, tag, num, n=None):
    if n == 1 and num == "p":
        return "" if tag == "a" else "z"
    if tag == "a":
        return "k"
    if tag == "i":
        return "".join(k for k in OBJ if not NOUNS[k][3] and (not gender or NOUNS[k][2] in gender))
    return "".join(k for k in OBJ if not gender or NOUNS[k][2] in gender)


def add_context(c, o):
    cc, oo = [], []
    for it in c:
        keys = fit(it[2], it[4], it[3], it[0])
        if keys: cc.append(it + [card_spec(it[0], it[1], it[4], it[3]), keys])
    for it in o:
        keys = fit(it[2] if it[3] == "s" else "", it[4], it[3])
        if keys: oo.append(it + [it[1] + ":" + it[3], keys])
    return cc, oo


# Frames: [words before the preposition, the preposition, end]. The client turns с/к/о into со/ко/об where the number's
# first word needs it (со второй, ко второму, об одном).
FRAMES = {
    "nomn":   [["У меня есть", "", "."]],
    "nomn_o": [["Это", "", "."]],
    "gent":   [["Я пришёл", "без", "."], ["Это коробка", "для", "."], ["Он стоял", "около", "."]],
    "datv":   [["Он подошёл", "к", "."], ["Я привык", "к", "."]],
    "accs":   [["Мы говорили", "про", "."], ["Я заплатил", "за", "."]],
    "ablt":   [["Он пришёл", "с", "."], ["Мы нашли ключ", "под", "."]],
    "loct":   [["Мы говорили", "о", "."], ["Он думал", "о", "."]],
}


def main():
    c, o = add_context(cardinals(), ordinals())
    path = os.path.join(ROOT, "public", "vocab", "numeral-forms.json")
    io.open(path, "w", encoding="utf-8").write(json.dumps({"v": 2, "c": c, "o": o, "nn": noun_forms(), "fr": FRAMES}, ensure_ascii=False, separators=(",", ":")))
    print("cardinal items", len(c), "ordinal items", len(o), "bytes", os.path.getsize(path))


if __name__ == "__main__":
    main()
