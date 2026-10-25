# -*- coding: utf-8 -*-
"""Which DLI model word a noun or adjective really declines like — checked, not guessed.

The case explanations used to name a model by the sound of the noun alone:
every plural ending in a hard consonant «declined like слова», so проект →
проектов was explained by слово → слов (a neuter, with no ending) and was
wrong. Here a model is named only when its endings are compared, form by form,
with the word's own forms from the dictionary:

  full   every form of that number has the model's ending (the spelling rules
         DLI teaches — ы never after г к х ж ч ш щ, -ом/-ем after sibilants,
         -ём for stressed -ем — are allowed for, nothing else is);
  form   only the asked form has the model's ending: stated as that, no more;
  none   no model is named.

The model words are DLI's own (Grammar Reference Book, the lessons the case
courses quote); their forms are the dictionary's (OpenCorpora via pymorphy3).
"""
import re

GUTT, SIB = "гкх", "жчшщ"
CASES = ["nomn", "gent", "datv", "accs", "ablt", "loct"]

# (word, gender, animate) — in the order a match is looked for
NOUN_MODELS = [
    ("студент", "masc", True), ("дом", "masc", False), ("стол", "masc", False), ("учитель", "masc", True),
    ("автомобиль", "masc", False), ("словарь", "masc", False), ("трамвай", "masc", False), ("андрей", "masc", True),
    ("окно", "neut", False), ("слово", "neut", False), ("поле", "neut", False), ("море", "neut", False), ("здание", "neut", False),
    ("сестра", "femn", True), ("газета", "femn", False), ("книга", "femn", False), ("тётя", "femn", True), ("неделя", "femn", False),
    ("батарея", "femn", False), ("армия", "femn", False), ("лекция", "femn", False), ("семья", "femn", False), ("часть", "femn", False), ("тетрадь", "femn", False),
    ("ключ", "masc", False),
]
# Never a model: имя (and the other ten nouns in -мя) takes -ен- before every ending. Models whose PLURAL is irregular
# (дом → дома, учитель → учителя) are cited for singular forms only.
IRREGULAR_PLURAL = {"дом", "учитель"}
ADJ_MODELS = [("новый", "hard"), ("синий", "soft"), ("русский", "guttural"), ("хороший", "sibilant")]
POSS_MODELS = [("мой", "мой"), ("наш", "наш")]


def norm(w):
    return (w or "").lower().replace("ё", "е")


def nrm(w):
    return (w or "").lower()


def stem_of(nom):
    n = nrm(nom)
    return re.sub(r"(ый|ий|ой)$", "", n) if re.search(r"(ый|ий|ой)$", n) else re.sub(r"[аяоеёьй]$", "", n)


def sig(nom, form):
    """(ending, kind) of `form` after the stem of `nom`; None when the stem itself changes beyond the fleeting/inserted vowel."""
    a, b = nrm(nom), nrm(form)
    st = stem_of(a)
    if b.startswith(st):
        return b[len(st):], "plain"
    if len(st) >= 3 and st[-2] in "оеё" and b.startswith(st[:-2] + st[-1]):
        return b[len(st) - 1:], "fleet"
    if st.endswith("ь") and b.startswith(st[:-1]) and not b.startswith(st):
        return b[len(st) - 1:], "soft"
    # the inserted vowel of the genitive plural: окно → окон, сестра → сестёр, письмо → писем
    if len(st) >= 2:
        for cut in (1, 2):
            if len(st) > cut and b == st[:-cut] + b[len(st) - cut:len(st) - cut + 1] + st[-cut:] and b[len(st) - cut] in "оеё" and (cut == 1 or st[-2] == "ь"):
                return "", "inserted"
    return None, "stem"


def _canon_ending(e):
    return e.replace("ё", "е")


def ends_match(te, tlast, me, soft_model):
    """Is the target's ending `te` the model's ending `me`, allowing for the spelling rules DLI teaches?"""
    if te is None or me is None:
        return False
    te, me = _canon_ending(te), _canon_ending(me)
    if te == me:
        return True
    if tlast and tlast in GUTT + SIB and not soft_model:
        # ы never follows г к х ж ч ш щ → и
        if me.startswith("ы") and te == "и" + me[1:]:
            return True
    if tlast and tlast in SIB + "ц" and not soft_model:
        # after ж ч ш щ ц: -ом/-ой unstressed → -ем/-ей
        if me.startswith("ом") and te == "ем" + me[2:]:
            return True
        if me == "ой" and te == "ей":
            return True
    if tlast == "ц" and not soft_model and me.startswith("ов") and te == "ев" + me[2:]:
        return True                                           # after ц the unstressed ending is -ев: американцев
    if tlast and tlast in SIB and not soft_model:
        # unstressed -о- after sibilants is -е-: хорошего, большое
        if me.startswith("о") and te == "е" + me[1:] and len(me) <= 3:
            return True
    return False


def _paradigm_nouns(M, word, gender, anim):
    from case_explain import paradigm
    for p in M.parse(word):
        if p.tag.POS == "NOUN" and nrm(p.normal_form) == word and p.tag.gender == gender and (p.tag.animacy == "anim") == anim:
            return paradigm(p)
    for p in M.parse(word):
        if p.tag.POS == "NOUN" and nrm(p.normal_form) == word:
            return paradigm(p)
    return None


_MODEL_CACHE = {}


def noun_models(M):
    if "n" not in _MODEL_CACHE:
        out = []
        for w, g, an in NOUN_MODELS:
            par = _paradigm_nouns(M, w, g, an)
            if par and par.get(("nomn", "sing")):
                shown = ("Андрей" if w == "андрей" else w)
                soft = bool(re.search(r"(ь|й|я|е|ё)$", w))
                out.append((shown, par, soft, g, an))
        _MODEL_CACHE["n"] = out
    return _MODEL_CACHE["n"]


def _compare_cases(number, gender):
    """The cases compared: the accusative follows DLI's animacy rule (= genitive or = nominative), so it is
    compared only where it has an ending of its own — the feminine singular (-у, -ю)."""
    out = [c for c in CASES if c != "accs" and not (c == "nomn" and number == "sing")]
    if number == "sing" and gender == "femn":
        out.append("accs")
    return out


def _nom_class(w):
    w = nrm(w)
    for suf in ("ия", "ие", "мя"):
        if w.endswith(suf):
            return suf
    return w[-1:] if w[-1:] in "аяоеьй" else "c"


def match_noun(M, tpar, tnom, gender, anim, number, case):
    """{'level': 'full'|'form'|None, 'model': word, 'form': model's form in this case/number, 'same_anim': bool}."""
    if gender not in ("masc", "femn", "neut"):
        return {"level": None}
    tlast = stem_of(tnom)[-1:]
    cmp_cases = _compare_cases(number, gender)
    tsigs = {}
    for c in cmp_cases:
        f = tpar.get((c, number))
        if f:
            tsigs[c] = sig(tnom, f)
    asked = tpar.get((case, number))
    if not asked or len(tsigs) < 4:
        return {"level": None}
    t_anim = (anim == "anim")
    # a masculine noun in -а, -я is declined like a feminine one (DLI, Lesson 33)
    eff = "femn" if (gender == "masc" and nrm(tnom).endswith(("а", "я"))) else gender
    for same in (True, False):
        for shown, mpar, soft, mg, man in noun_models(M):
            if mg != eff or (man == t_anim) != same:
                continue
            if number == "plur" and shown in IRREGULAR_PLURAL:
                continue                                  # дом → дома, учитель → учителя: a plural of its own, no model for other nouns
            mnom = mpar.get(("nomn", "sing"))
            if not mpar.get(("nomn", number)):
                continue
            if _nom_class(mnom) != _nom_class(tnom):
                continue                                  # a noun in -й is modelled on a noun in -й, not on one in -ь
            ok_all = True
            for c, (te, _k) in tsigs.items():
                mf = mpar.get((c, number))
                if not mf:
                    continue
                ms = sig(mnom, mf)
                if not (_k == ms[1] or {_k, ms[1]} <= {"plain", "fleet"}):
                    ok_all = False                       # an inserted vowel (окон) is not «no change» (мест); a soft stem is not a hard one
                    break
                if not ends_match(te, tlast, ms[0], soft):
                    ok_all = False
                    break
            mfc = mpar.get((case, number))
            if ok_all and mfc:
                return {"level": "full", "model": shown, "form": mfc, "same_anim": same, "par": mpar}
    return {"level": None}


_ADJ_CACHE = {}


def adj_models(M):
    if "a" not in _ADJ_CACHE:
        from case_explain import paradigm
        out = []
        for w, cls in ADJ_MODELS:
            for p in M.parse(w):
                if p.tag.POS == "ADJF" and nrm(p.normal_form) == w:
                    out.append((w, cls, paradigm(p)))
                    break
        _ADJ_CACHE["a"] = out
    return _ADJ_CACHE["a"]


def _adj_sig(lemma, form, case, gender, number):
    s, k = sig(lemma, form)
    if s in ("ый", "ой", "ий") and number == "sing" and gender == "masc" and case in ("nomn", "accs"):
        return "NOM"
    return s


def match_adj(M, tpar, lemma):
    """The adjective model whose every form has the same ending (spelling rules allowed), or None."""
    tlast = stem_of(lemma)[-1:]
    l = nrm(lemma)
    # the type DLI files the adjective under: by the last letter of its stem (большой is guttural, DLI says so)
    want = "guttural" if (l.endswith("большой") or tlast in GUTT) else "sibilant" if tlast in SIB else "soft" if l.endswith("ий") else "hard"
    for w, cls, mpar in adj_models(M):
        if cls != want:
            continue
        soft = (cls == "soft")
        ok, n = True, 0
        for key, tf in tpar.items():
            mf = mpar.get(key)
            if not mf:
                continue
            c, num, g = key[0], key[1], key[2]
            ts = _adj_sig(lemma, tf, c, g, num)
            ms = _adj_sig(w, mf, c, g, num)
            n += 1
            if ts == ms:
                continue
            if ts == "NOM" or ms == "NOM":
                ok = False
                break
            if not ends_match(ts, tlast, ms, soft):
                ok = False
                break
        if ok and n >= 12:
            return w, cls, mpar
    return None


def model_form(mpar, case, number, gender):
    g = gender if number == "sing" else None
    if case == "accs" and (number == "plur" or g == "masc"):
        return "anim. = G., inan. = N."
    for an in (None, "inan", "anim"):
        f = mpar.get((case, number, g, an if case == "accs" else None))
        if f:
            return f
    return "—"


def poss_match(M, tpar, lemma):
    from case_explain import paradigm
    for w, _ in POSS_MODELS:
        mp = None
        for p in M.parse(w):
            if p.tag.POS in ("ADJF", "NPRO") and nrm(p.normal_form) == w:
                mp = paradigm(p)
                break
        if not mp:
            continue
        ok, n = True, 0
        for key, tf in tpar.items():
            mf = mp.get(key)
            if not mf:
                continue
            n += 1
            a, b = sig(lemma, tf), sig(w, mf)
            if a[0] != b[0] and not (key[0] in ("nomn", "accs") and key[1] == "sing" and key[2] == "masc"):
                ok = False
                break
        if ok and n >= 12:
            return w
    return None


# ── the genitive plural's four types, read from the actual form ───────────
def genpl_type(nom, form, gender, nom_pl):
    """'I' 'II' 'III' 'IV', 'irr' (the lessons' listed irregulars) or None when the form fits none of DLI's four types."""
    n, f = norm(nom), norm(form)
    if n in ("раз", "человек", "солдат", "год") or norm(nom_pl or "").endswith("ья"):
        return "irr"
    if n.endswith(("ия", "ие")) and f.endswith("ий"):
        return "IV"
    if n in ("поле", "море", "семья") and f.endswith("ей"):
        return "IV"
    last = n[-1:]
    if last not in "аяоеёьй" and f.endswith(("ов", "ев")):
        return "I"                                              # a consonant (also ц, й): -ов, -ев
    if (last == "ь" or (last in SIB)) and f.endswith("ей"):
        return "II"
    if n in ("мать", "дочь") and f.endswith("ерей"):
        return "II"
    if last in "аяоеё" and not f.endswith(("ов", "ев", "ей", "ий")) and not n.endswith(("ия", "ие")):
        return "III"                                            # no ending (an inserted vowel, or -ь after a soft stem)
    return None
