# -*- coding: utf-8 -*-
"""Every Russian form in the grammar-tables course comes out of here.

Nothing in this file writes a Russian ending.  Each form is looked up in the
OpenCorpora morphological dictionary through pymorphy3 and printed as the
dictionary has it, so no form in the finished tables can be invented.
"""
import re

import pymorphy3

M = pymorphy3.MorphAnalyzer()

CASES = [("nomn", "N."), ("gent", "G."), ("datv", "D."),
         ("accs", "A."), ("ablt", "I."), ("loct", "P.")]
GEND = [("masc", "Masc."), ("femn", "Fem."), ("neut", "Neut.")]

# Grammemes OpenCorpora itself puts on forms a textbook would not print:
# archaic, infrequent, erroneous, distorted, abbreviation, slang, and the
# poetic/colloquial spelling variants (зданье for здание, синею for синей).
DROP = ("Arch", "Infr", "Erro", "Dist", "Abbr", "Slng",
        "V-ey", "V-oy", "V-ej", "V-be", "V-bi", "V-sh", "Af-p", "Fimp")


# Entries a lower-case headword must not pull in: surnames, first names,
# patronymics, place and organisation names.
PROPER = {"Surn", "Name", "Patr", "Geox", "Orgn", "Trad"}


class NotInDict(Exception):
    pass


def _lemma(word, pos, require=()):
    """Every dictionary entry for `word` as part of speech `pos`, merged.

    OpenCorpora often holds one word as several entries — стул has one with the
    plural стулы and another with стулья, высокий keeps its comparative выше in
    an entry of its own.  Picking the likeliest entry would quietly drop the
    other half of the paradigm, so every matching entry is merged instead and
    a cell that really has two forms shows both.

    A capitalised headword (Андрей) is looked up in lower case and its forms
    are capitalised back, since the dictionary stores names in lower case."""
    want = set(require)
    low = word.lower()
    hits = []
    for p in M.parse(low):
        if pos not in p.tag:
            continue
        if want and not want <= set(str(p.tag).replace(" ", ",").split(",")):
            continue
        if p.normal_form != low and not (p.word == low and "nomn" in p.tag):
            continue        # душа is not the genitive of душ, but деньги
                            # is a headword even though the dictionary lemma is деньга
        t = set(str(p.tag).replace(" ", ",").split(","))
        if not word[:1].isupper() and t & PROPER:
            continue        # лист the leaf, not Лист the composer
        hits.append(p)
    if not hits:
        raise NotInDict("%s (%s) not in the dictionary" % (word, pos))
    return _Merged(hits, word[:1].isupper())


class _Merged(object):
    """The lexemes of several dictionary entries for one word, as one lexeme."""

    def __init__(self, parses, cap=False):
        self._parses = parses
        self._cap = cap
        self.tag = parses[0].tag
        self.normal_form = parses[0].normal_form

    @property
    def lexeme(self):
        out, seen = [], set()
        for p in self._parses:
            for f in p.lexeme:
                k = (f.word, str(f.tag))
                if k in seen:
                    continue
                seen.add(k)
                out.append(_CapForm(f) if self._cap else f)
        return out


class _CapForm(object):
    def __init__(self, f):
        self._f = f
        self.word = f.word[:1].upper() + f.word[1:]
        self.tag = f.tag


def _pick(lex, *tags, **kw):
    """Every distinct form in the lexeme carrying all of `tags`."""
    drop = kw.get("drop", DROP)
    out = []
    for f in lex:
        s = set(str(f.tag).replace(" ", ",").split(","))
        if not set(tags) <= s:
            continue
        if any(d in s for d in drop):
            continue
        if f.word not in out:
            out.append(f.word)
    return out


def _cell(lex, *tags, **kw):
    got = _pick(lex, *tags, **kw)
    return ", ".join(got) if got else "—"


# ---------------------------------------------------------------- nouns

def noun(word):
    """[['N.', sing, plur], ...] for one noun."""
    p = _lemma(word, "NOUN")
    lex = p.lexeme
    sing = bool(_pick(lex, "sing"))
    plur = bool(_pick(lex, "plur"))
    rows = []
    for tag, label in CASES:
        row = [label]
        if sing:
            row.append(_cell(lex, tag, "sing"))
        if plur:
            row.append(_cell(lex, tag, "plur"))
        rows.append(row)
    head = [""] + (["Singular"] if sing else []) + (["Plural"] if plur else [])
    return head, rows


def nouns(words, labels=None):
    """One table, a column per noun: [['N.', ...], ...]."""
    cols = []
    for w in words:
        p = _lemma(w, "NOUN")
        cols.append(p.lexeme)
    rows = []
    for tag, label in CASES:
        row = [label]
        for lex in cols:
            s, pl = _cell(lex, tag, "sing"), _cell(lex, tag, "plur")
            if pl == "—" or s == pl:
                row.append(s)          # indeclinable, or no plural
            elif s == "—":
                row.append(pl)
            else:
                row.append(s + " / " + pl)
        rows.append(row)
    return [""] + list(labels or words), rows


def noun_num(words, num):
    """A table of one number only (num = 'sing' or 'plur'), a column per noun."""
    rows = []
    for tag, label in CASES:
        row = [label]
        for w in words:
            row.append(_cell(_lemma(w, "NOUN").lexeme, tag, num))
        rows.append(row)
    return [""] + list(words), rows


# ---------------------------------------------------------------- adjectives

ADJ_DROP = DROP + ("Supr", "Cmp2")


def _acc(lex, *tags):
    """Accusative, animate and inanimate shown apart when they differ."""
    an = _pick(lex, "accs", "anim", *tags, drop=ADJ_DROP)
    inan = _pick(lex, "accs", "inan", *tags, drop=ADJ_DROP)
    if not an and not inan:
        return _cell(lex, "accs", *tags)
    if an == inan:
        return ", ".join(an)
    j = lambda xs: ", ".join(xs) if xs else "\u2014"
    return "%s (anim.) \u00b7 %s (inan.)" % (j(an), j(inan))


def adj(word):
    """[['N.', masc, fem, neut, plur], ...] for one adjective."""
    lex = _lemma(word, "ADJF").lexeme
    rows = []
    for tag, label in CASES:
        row = [label]
        for g, _ in GEND:
            row.append(_acc(lex, "ADJF", g, "sing") if tag == "accs"
                       else _cell(lex, "ADJF", tag, g, "sing", drop=ADJ_DROP))
        row.append(_acc(lex, "ADJF", "plur") if tag == "accs"
                   else _cell(lex, "ADJF", tag, "plur", drop=ADJ_DROP))
        rows.append(row)
    return ["", "Masc.", "Fem.", "Neut.", "Plural"], rows


def adj_row_table(words, labels=None):
    """Nominative only, a column per adjective — for comparing stem types."""
    rows = []
    for g, glabel in GEND:
        rows.append([glabel] + [_cell(_lemma(w, "ADJF").lexeme, "ADJF", "nomn", g, "sing", drop=ADJ_DROP) for w in words])
    rows.append(["Plural"] + [_cell(_lemma(w, "ADJF").lexeme, "ADJF", "nomn", "plur", drop=ADJ_DROP) for w in words])
    return [""] + list(labels or words), rows


def adj_case_table(words, labels=None, gender="masc", num="sing"):
    """One gender/number, a column per adjective, all six cases."""
    rows = []
    for tag, label in CASES:
        row = [label]
        for w in words:
            lex = _lemma(w, "ADJF").lexeme
            if tag == "accs":
                row.append(_acc(lex, "ADJF", gender, "sing") if num == "sing" else _acc(lex, "ADJF", "plur"))
            else:
                row.append(_cell(lex, "ADJF", tag, gender, num, drop=ADJ_DROP) if num == "sing"
                           else _cell(lex, "ADJF", tag, "plur", drop=ADJ_DROP))
        rows.append(row)
    return [""] + list(labels or words), rows


def adj_short(word):
    """Short forms: masc, fem, neut, plural."""
    lex = _lemma(word, "ADJF").lexeme
    return [_cell(lex, "ADJS", g, drop=ADJ_DROP) for g in ("masc", "femn", "neut", "plur")]


def adv_of(word):
    """The adverb that shares this adjective's stem (высокий → высоко), if the
    dictionary has one.  Russian spells an adjective's comparative and its
    adverb's comparative the same (выше), and OpenCorpora files the suppletive
    ones (выше, старше) under the adverb only."""
    stem = re.sub(r"(ый|ий|ой)$", "", word)
    for end in ("о", "е"):
        cand = stem + end
        for p in M.parse(cand):
            if "ADVB" in p.tag and p.normal_form == cand:
                return p
    return None


COMP_DROP = ("Erro", "Dist", "V-ej", "V-ey", "V-oy", "Af-p")


def adj_comp(word):
    """(comparative, the \u043f\u043e- comparative).  The suppletive ones (\u0432\u044b\u0448\u0435, \u0441\u0442\u0430\u0440\u0448\u0435)
    sit in the matching adverb's entry, so that is searched too."""
    got = _pick(_lemma(word, "ADJF").lexeme, "COMP", drop=COMP_DROP)
    a = adv_of(word)
    if a is not None:
        for g in _pick(a.lexeme, "COMP", drop=COMP_DROP):
            if g not in got:
                got.append(g)
    plain = [g for g in got if not g.startswith("\u043f\u043e")]
    pos = [g for g in got if g.startswith("\u043f\u043e")]
    return ", ".join(plain) or "\u2014", ", ".join(pos) or "\u2014"


def adj_supr(word):
    """The -\u0435\u0439\u0448\u0438\u0439/-\u0430\u0439\u0448\u0438\u0439 superlative.  \u041d\u0430\u0438- forms are shown only when the
    dictionary has no plainer one."""
    got = _pick(_lemma(word, "ADJF").lexeme, "ADJF", "Supr", "masc", "sing", "nomn", drop=COMP_DROP)
    plain = [g for g in got if not g.startswith("\u043d\u0430\u0438")]
    return ", ".join(plain or got) or "\u2014"


# A personal pronoun's forms with and without a preposition: OpenCorpora marks
# the н- forms Af-p ("after a preposition"), and a table needs both.
def personal(words):
    rows = []
    for tag, label in CASES:
        row = [label]
        for w in words:
            lex = pron(w)
            bare = _pick(lex, tag, drop=DROP)
            afp = _pick(lex, tag, drop=tuple(x for x in DROP if x != "Af-p") + ("Af-p-never",))
            afp = [f.word for f in lex
                   if tag in str(f.tag) and "Af-p" in str(f.tag)
                   and not any(d in str(f.tag) for d in ("Arch", "Infr", "Erro", "Dist", "Abbr", "V-oy", "V-ey"))]
            afp = list(dict.fromkeys(afp))
            if bare and afp and afp != bare:
                row.append("%s (%s)" % (", ".join(bare), ", ".join(afp)))
            else:
                row.append(", ".join(bare or afp) or "\u2014")
        rows.append(row)
    return [""] + list(words), rows


# ---------------------------------------------------------------- pronouns

def pron(word, pos=None):
    """All six cases of a pronoun, as a single column."""
    p = None
    for cand in ([pos] if pos else ["NPRO", "ADJF", "NOUN", "NUMR"]):
        try:
            p = _lemma(word, cand)
            break
        except NotInDict:
            continue
    if p is None:
        raise NotInDict(word + " not in the dictionary")
    return p.lexeme


def pron_table(words, labels=None, gender=None, num="sing"):
    rows = []
    for tag, label in CASES:
        row = [label]
        for w in words:
            lex = pron(w)
            tags = [tag] + ([gender] if gender else []) + ([num] if num else [])
            got = _pick(lex, *tags)
            if not got and gender:
                got = _pick(lex, tag, num)
            if not got:
                got = _pick(lex, tag)
            row.append(", ".join(got) if got else "—")
        rows.append(row)
    return [""] + list(labels or words), rows


def pron_full(word):
    """A determiner-like pronoun (этот, тот, весь, мой, наш, чей, сам...) in
    all four gender/number columns."""
    lex = pron(word)
    rows = []
    for tag, label in CASES:
        row = [label]
        for g, _ in GEND:
            row.append(_acc(lex, g, "sing") if tag == "accs" else _cell(lex, tag, g, "sing"))
        row.append(_acc(lex, "plur") if tag == "accs" else _cell(lex, tag, "plur"))
        rows.append(row)
    return ["", "Masc.", "Fem.", "Neut.", "Plural"], rows


# ---------------------------------------------------------------- verbs

def verb_present(words, labels=None):
    """я/ты/он/мы/вы/они, a column per verb (present for impf, future for pf)."""
    PERS = [("sing", "1per", "я"), ("sing", "2per", "ты"), ("sing", "3per", "он"),
            ("plur", "1per", "мы"), ("plur", "2per", "вы"), ("plur", "3per", "они")]
    cols = [_lemma(w, "INFN").lexeme for w in words]
    rows = []
    for num, per, label in PERS:
        row = [label]
        for lex in cols:
            got = _pick(lex, "VERB", num, per, "pres") or _pick(lex, "VERB", num, per, "futr")
            row.append(", ".join(got) if got else "—")
        rows.append(row)
    return [""] + list(labels or words), rows


def verb_futr(words, labels=None):
    """The compound-free future: only verbs whose dictionary entry has futr
    forms of its own (\u0431\u044b\u0442\u044c \u2192 \u0431\u0443\u0434\u0443, and every perfective verb)."""
    PERS = [("sing", "1per", "\u044f"), ("sing", "2per", "\u0442\u044b"), ("sing", "3per", "\u043e\u043d"),
            ("plur", "1per", "\u043c\u044b"), ("plur", "2per", "\u0432\u044b"), ("plur", "3per", "\u043e\u043d\u0438")]
    cols = [_lemma(w, "INFN").lexeme for w in words]
    rows = []
    for num, per, label in PERS:
        row = [label]
        for lex in cols:
            row.append(_cell(lex, "VERB", num, per, "futr"))
        rows.append(row)
    return [""] + list(labels or words), rows


def verb_pres_only(words, labels=None):
    """Present tense only \u2014 no falling back to the future."""
    PERS = [("sing", "1per", "\u044f"), ("sing", "2per", "\u0442\u044b"), ("sing", "3per", "\u043e\u043d"),
            ("plur", "1per", "\u043c\u044b"), ("plur", "2per", "\u0432\u044b"), ("plur", "3per", "\u043e\u043d\u0438")]
    cols = [_lemma(w, "INFN").lexeme for w in words]
    rows = []
    for num, per, label in PERS:
        row = [label]
        for lex in cols:
            row.append(_cell(lex, "VERB", num, per, "pres"))
        rows.append(row)
    return [""] + list(labels or words), rows


def verb_past(words, labels=None):
    cols = [_lemma(w, "INFN").lexeme for w in words]
    rows = []
    for tags, label in [(("masc", "sing"), "он"), (("femn", "sing"), "она"),
                        (("neut", "sing"), "оно"), (("plur",), "они")]:
        row = [label]
        for lex in cols:
            got = _pick(lex, "VERB", "past", *tags)
            row.append(", ".join(got) if got else "—")
        rows.append(row)
    return [""] + list(labels or words), rows


def verb_impr(words, labels=None, incl=False):
    """ты- and вы-imperatives.  OpenCorpora marks the real imperative `excl`
    and the "let's" form (идём, идёмте) `incl`; `incl=True` adds that row."""
    cols = [_lemma(w, "INFN").lexeme for w in words]
    rows = []
    for num, label in [("sing", "ты"), ("plur", "вы")]:
        row = [label]
        for lex in cols:
            got = _pick(lex, "VERB", "impr", "excl", num)
            row.append(", ".join(got) if got else "—")
        rows.append(row)
    if incl:
        row = ["мы (let's)"]
        for lex in cols:
            got = _pick(lex, "VERB", "impr", "incl", "sing") + _pick(lex, "VERB", "impr", "incl", "plur")
            row.append(", ".join(got) if got else "—")
        rows.append(row)
    return [""] + list(labels or words), rows


PART = [(("pres", "actv"), "Present active"),
        (("pres", "pssv"), "Present passive"),
        (("past", "actv"), "Past active"),
        (("past", "pssv"), "Past passive")]


def verb_participles(words, labels=None):
    """The four long participles (masc. nom. sg.) and the gerund, per verb."""
    cols = [_lemma(w, "INFN").lexeme for w in words]
    rows = []
    for tags, label in PART:
        row = [label]
        for lex in cols:
            got = _pick(lex, "PRTF", "masc", "sing", "nomn", *tags)
            row.append(", ".join(got) if got else "—")
        rows.append(row)
    for tag, label in [("pres", "Gerund (pres.)"), ("past", "Gerund (past)")]:
        row = [label]
        for lex in cols:
            got = _pick(lex, "GRND", tag)
            row.append(", ".join(got) if got else "—")
        rows.append(row)
    return [""] + list(labels or words), rows


def part_short(word):
    """Short forms of the past passive participle: masc, fem, neut, plural."""
    lex = _lemma(word, "INFN").lexeme
    return [_cell(lex, "PRTS", "past", "pssv", g) for g in ("masc", "femn", "neut", "plur")]


def part_decl(word, which=("past", "pssv")):
    """One participle declined in full."""
    lex = _lemma(word, "INFN").lexeme
    rows = []
    for tag, label in CASES:
        row = [label]
        for g, _ in GEND:
            row.append(_cell(lex, "PRTF", tag, g, "sing", *which))
        row.append(_cell(lex, "PRTF", tag, "plur", *which))
        rows.append(row)
    return ["", "Masc.", "Fem.", "Neut.", "Plural"], rows


# ---------------------------------------------------------------- numerals

def numr_table(words, labels=None):
    rows = []
    for tag, label in CASES:
        row = [label]
        for w in words:
            lex = None
            for pos in ("NUMR", "ADJF", "NOUN"):
                try:
                    lex = _lemma(w, pos).lexeme
                    break
                except NotInDict:
                    continue
            if lex is None:
                row.append("—")
                continue
            got = _pick(lex, tag, "sing") or _pick(lex, tag, "plur") or _pick(lex, tag)
            row.append(", ".join(got) if got else "—")
        rows.append(row)
    return [""] + list(labels or words), rows


# ---------------------------------------------------------------- checking

def known(form):
    """True if this exact written form is in the dictionary."""
    return any(not p.tag.is_productive() is None for p in M.parse(form)) and \
        bool([p for p in M.parse(form) if "UNKN" not in str(p.tag)])


def check(form):
    ps = [p for p in M.parse(form) if "UNKN" not in str(p.tag)]
    return bool(ps), [str(p.tag) for p in ps[:3]]
