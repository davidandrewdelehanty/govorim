#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Give every Verbs of Motion exercise the explanation of its OWN verb.

attach_context.py and pertinence.py pick a rule by looking at the sentence's
grammar; for the motion course that put the идти paragraph under a лететь
exercise and the вести paragraph under «Tom wears a hat». Here the choice is
made from what the exercise is actually about: which verb the answer is a form
of (found with pymorphy3, or taken from the hint in brackets), whether that
verb is the one-direction or the many-directions member of its pair, which
prefix it carries, and what form the answer has.

Nothing is written by a machine. Every rule is a sentence of the course's own
lessons (the DLI Grammar Reference Books, Wikipedia's «Russian grammar», both
quoted in the lessons) carried across verbatim with its source; the verb's
meaning and its forms are Wiktionary's (tools/courses/motion_src); the
examples are the lessons' own examples that use the same verb.

    cd /mnt/c/Users/david/projects/govorim-app
    python3 tools/courses/motion_explain.py            # report only
    python3 tools/courses/motion_explain.py --apply
"""
import argparse, glob, io, json, os, re, sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
ROOT = os.path.dirname(os.path.dirname(HERE))
COURSE = os.path.join(ROOT, "public", "courses", "motion")

import motion_mine as MM
import motion_kit as MK

M = MM.M
ACUTE = "́"
MISSING = set()


def plain(s):
    return (s or "").replace(ACUTE, "")


# ── the lessons, as sources ───────────────────────────────────────────────
_L = {}


def lesson(sid):
    if sid not in _L:
        p = os.path.join(COURSE, sid + ".json")
        j = json.load(io.open(p, encoding="utf-8"))
        bl = j.get("blocks") or []
        nxt, cur = [""] * len(bl), ""
        for i in range(len(bl) - 1, -1, -1):
            if bl[i].get("t") == "note":
                cur = re.sub(r"\s+", " ", bl[i].get("text") or "").strip()
            nxt[i] = cur
        _L[sid] = (bl, nxt)
    return _L[sid]


def trim(s, n):
    s = s.strip()
    if len(s) <= n:
        return s
    cut = s[:n]
    k = max(cut.rfind(". "), cut.rfind("! "), cut.rfind("? "))
    if k > n * 0.5:
        return cut[:k + 1]
    return cut.rsplit(" ", 1)[0].rstrip(",;:") + "…"


def clean(s):
    return re.sub(r"\s+", " ", s or "").strip()


def Q(sid, rx, start=None, end=None, n=560):
    """(text, source) — a paragraph of lesson `sid` whose start matches `rx`, cut by `start`/`end`."""
    bl, nxt = lesson(sid)
    for i, b in enumerate(bl):
        if b.get("t") != "p":
            continue
        t = clean(b.get("text"))
        if not re.search(rx, t):
            continue
        if start:
            m = re.search(start, t)
            if not m:
                continue
            t = t[m.start():]
        if end:
            m = re.search(end, t)
            if m:
                t = t[:m.start()]
        return (trim(t, n), nxt[i])
    MISSING.add((sid, rx))
    return None


def seg_q(sid, rx, lemma, partner, n=520):
    """One entry of a «приносить — принести — to bring; …» paragraph: the one naming this verb."""
    bl, nxt = lesson(sid)
    for i, b in enumerate(bl):
        if b.get("t") != "p":
            continue
        t = clean(b.get("text"))
        if not re.search(rx, t):
            continue
        body = re.sub(r"^With the carrying verbs:\s*", "", t)
        segs = re.split(r";\s+(?=[А-Яа-яЁё]+(?:ть|ти|чь) — )", body)
        hit = [s for s in segs if re.search(r"(?<![а-яё])(%s|%s)(?![а-яё])" % (re.escape(lemma), re.escape(partner or lemma)), s.lower())]
        if hit:
            return (trim(" ".join(hit), n), nxt[i])
        return None
    MISSING.add((sid, rx))
    return None


def wp_row(lemma, full=False):
    """The Wikipedia table row for the lemma's prefix: meaning, example, prepositions."""
    m = MM.PRE_RE.match(lemma)
    if not m:
        return None
    p = m.group(1)
    g = MM.GROUP[p]
    sid = MM.LESSON.get(g)
    if not sid:
        return None
    bl, nxt = lesson(sid)
    refl = lemma.endswith("ся") or lemma.endswith("сь")
    cands = []
    for i, b in enumerate(bl):
        if b.get("t") != "table" or not (b.get("head") or [""])[0].startswith("prefix"):
            continue
        for r in b.get("rows") or []:
            c0 = r[0].replace("*", "")
            toks = re.findall(r"([а-яё]+)-", c0.split(" — ")[0])
            if p in toks:
                cands.append((r, nxt[i], "+ся" in c0))
    if not cands:
        return None
    pick = [c for c in cands if c[2] == refl] or cands
    r, src, _ = pick[0]
    ex1 = clean(r[1]) if len(r) > 1 and r[1] else ""
    if not full:
        ex1 = re.split(r"\s+Other:", ex1)[0]
    text = clean(r[0]) + (" Example: " + ex1 if ex1 else "") + (" Prepositional phrases: " + clean(r[2]).rstrip(".") + "." if len(r) > 2 and r[2] else "")
    return (trim(text, 640), src), clean(r[0])


def meaning_of_prefix(lemma):
    r = wp_row(lemma)
    if not r:
        return ""
    c0 = r[1].replace("*", "")
    body = c0.split(" — ", 1)[-1]
    body = re.split(r"\s*Antonym", body)[0].strip().rstrip(".")
    pre = c0.split(" — ")[0].split(" (")[0].strip()
    return "%s — %s" % (pre, body)


def table_line(sid, head0, key_pred, fmt):
    bl, nxt = lesson(sid)
    for i, b in enumerate(bl):
        if b.get("t") == "table" and (b.get("head") or [""])[0] == head0:
            for r in b["rows"]:
                if key_pred(r):
                    return (fmt(b["head"], r), nxt[i])
    return None


# the going-verbs / carrying paragraphs, always read from the lessons
def S(src, short=None):
    return src


# ── examples the lessons themselves give with the same verb ───────────────
_EX = None


def ex_index():
    global _EX
    if _EX is not None:
        return _EX
    idx = {}
    for f in sorted(glob.glob(os.path.join(COURSE, "m*.json"))):
        sid = os.path.basename(f)[:-5]
        if re.search(r"-practice(-\d+)?$", sid):
            continue
        bl, nxt = lesson(sid)
        for i, b in enumerate(bl):
            if b.get("t") != "ex":
                continue
            for it in b.get("items") or []:
                ru = clean(it[0])
                en = clean(it[1]) if len(it) > 1 else ""
                ls = set()
                for w in re.findall(r"[А-Яа-яЁё]+", ru):
                    for p in M.parse(w.lower()):
                        if p.tag.POS in ("VERB", "INFN") and p.score >= 0.05:
                            ls.add(p.normal_form)
                for l in ls:
                    idx.setdefault(l, []).append((ru, en, nxt[i]))
    _EX = idx
    return idx


def compare(lemma, partner, sentence, used, k=2):
    idx = ex_index()
    out, seen = [], set()
    if partner in MM.AMBIG or partner in MM.S_TRIP or partner in MM.PO_WHILE:
        partner = None
    for l in (lemma, partner):
        for ru, en, src in idx.get(l, []):
            if not l or ru in seen or ru == sentence or any(ru in u for u in used):
                continue
            if clean(plain(ru)) == clean(plain(sentence)):
                continue
            seen.add(ru)
            out.append((ru, en, src))
            if len(out) >= k:
                return out
    return out


# ── the exercise, read ────────────────────────────────────────────────────
HINT = re.compile(r"\(([А-Яа-яЁё\-]+)(?:\s+—\s+[^)]*)?\)")


def sentence_of(e):
    if e["type"] == "mc":
        a = e["options"][e["answer"]]
        return clean((e.get("ru") or e["q"]).replace("___", a).replace("*", "")), a
    a = e["answers"][0]
    q = re.sub(r"___\s*\([^)]*\)", a, e["q"])
    q = q.replace("___", a)
    return clean(q.replace("*", "")), a


def lemma_of(word, prefer=None):
    w = plain(word).lower()
    ps = [p for p in M.parse(w) if p.tag.POS in ("VERB", "INFN")]
    if prefer:
        for p in ps:
            if p.normal_form == prefer:
                return prefer, p
        return prefer, None
    for p in ps:
        if p.score >= 0.05 and MM.lesson_of(p.normal_form):
            return p.normal_form, p
    return None, None


def aspect_of(lemma, p):
    for e in MM.WIKT.get(lemma) or []:
        pass
    ents = MM.WIKT.get(lemma) or []
    if len(ents) == 1:
        h = ents[0].get("head") or ""
        if re.search(r"\bpf\b", h) and not re.search(r"\bimpf\b", h):
            return "pf"
        if re.search(r"\bimpf\b", h) and not re.search(r"\bpf\b", h):
            return "impf"
    if p is not None and p.tag.aspect:
        return "pf" if p.tag.aspect == "perf" else "impf"
    return None


PERS = {"1per": "1st person", "2per": "2nd person", "3per": "3rd person"}
NUM = {"sing": "singular", "plur": "plural"}
GEN = {"masc": "masculine", "femn": "feminine", "neut": "neuter"}


def tense_of(p, asp):
    t = p.tag.tense
    if t == "futr" and asp == "impf":
        return "pres"
    return t


def describe(p, asp=None):
    if p is None:
        return ""
    t = p.tag
    if p.tag.POS == "INFN":
        return "the infinitive"
    if t.mood == "impr":
        return "the imperative (%s)" % ("вы, plural or polite" if t.number == "plur" else "ты, singular")
    tn = tense_of(p, asp)
    if tn == "past":
        return "the past tense (%s)" % (GEN.get(t.gender) or "plural")
    pe, nu = PERS.get(t.person, ""), NUM.get(t.number, "")
    if tn == "pres":
        return "the present tense (%s %s)" % (pe, nu)
    if tn == "futr":
        return "the future tense (%s %s)" % (pe, nu)
    return ""


def paradigm(lemma, p, asp):
    e = MK.entry(lemma, asp)
    c = (e and e.get("c")) or {}
    if p is None or not c:
        return ""
    t = p.tag
    if p.tag.POS == "INFN":
        return ""
    if t.mood == "impr":
        imp = [x for x in (c.get("imp") or []) if x]
        return "imperative: " + " · ".join(imp) if imp else ""
    tn = tense_of(p, asp)
    if tn == "past":
        pa = c.get("past") or {}
        return "past: " + " · ".join(x for x in ("он " + pa.get("m", ""), "она " + pa.get("f", ""), "оно " + pa.get("n", ""), "они " + pa.get("pl", "")) if x.split(" ")[-1])
    rows = [x for x in (c.get("pres") or [])] if tn == "pres" else [x for x in (c.get("fut") or [])]
    if len(rows) == 6 and any(rows) and not any("," in x for x in rows):
        return ("present: " if tn == "pres" else "future: ") + " · ".join("%s %s" % (w, f) for w, f in zip(["я", "ты", "он", "мы", "вы", "они"], rows))
    return ""


def wiki(l):
    return "Wiktionary, «%s» (CC BY-SA 4.0)" % l


def short_src(s):
    s = (s or "").strip()
    if s.startswith("Wikipedia"):
        return "Wikipedia, «Russian grammar» § Verbs of motion (CC BY-SA 4.0)"
    return s


def clean_defs(d):
    d = re.sub(r"\.mw-parser-output[^{]*\{[^}]*\}", "", d)
    d = re.sub(r"\s{2,}", " ", d)
    parts = [x.strip() for x in d.split("; ")]
    parts = [x for x in parts if x and not x.startswith("see ") and "#" not in x]
    return "; ".join(parts)


def defs_of(lemma, asp=None, n=2):
    d = clean_defs(MK.defs(lemma, n + 2, asp))
    d = "; ".join(d.split("; ")[:n])
    m = re.match(r"^alternative form of ([^\s(;,]+)", plain(d))
    if m and m.group(1) in MM.WIKT and m.group(1) != lemma:
        return "; ".join(clean_defs(MK.defs(m.group(1), n + 2, None)).split("; ")[:n])
    return d


def role_of(L):
    if L in MM.UNI:
        return "uni"
    if L in MM.MULTI or L == "лазать":
        return "multi"
    if L in MM.SYA:
        return "uni" if L in ("катиться", "нестись", "гнаться", "тащиться") else "multi"
    return None


def uni_of(L):
    if L in MM.UNI:
        return L
    if L == "лазать":
        return "лезть"
    return MM.PAIR.get(L, L)


# ── the sources for the verbs without prefixes ───────────────────────────
def unprefixed(L, role, form, sent, idiom, kind, generic=True):
    qs = []
    fam = uni_of(L) if kind == "pair" else L
    if idiom:
        qs.append(Q("m07-idioms", r"^The uni- and multidirectional distinction rarely", end=r":\s*$"))
        row = None
        for key in (L, fam, MM.PAIR.get(L)):
            row = table_line("m07-idioms", "verb", lambda r: r[0] == key, lambda h, r: "%s — %s" % (r[0], clean(r[1])))
            if row:
                break
        if row:
            qs.append(row)
        if fam == "идти":
            qs.append(Q("m07-idioms", r"^Note the following expressions: Идёт"))
        if fam in ("нести", "везти"):
            if re.search(r"везл|везёт|повезл|повезёт", sent, re.I):
                qs.append(Q("m04-carrying", r"^Note also the following idiomatic construction", end=r"\s+The \"carrying verbs\""))
            else:
                qs.append(Q("m04-carrying", r"^Note some special uses of these verbs"))
        if fam == "вести":
            qs.append(Q("m04-carrying", r"^This verb also follows the pattern", n=640))
        return qs
    if kind == "sya":
        qs.append(Q("m05-other-pairs", r"^Researchers have also included"))
        base = L[:-2]
        row = table_line("m05-other-pairs", "", lambda r: any(L in x.replace("*", "") for x in r[1:3]),
                         lambda h, r: "%s: %s (one direction) / %s (many directions) — %s" % (r[0], r[1].replace("*", ""), r[2].replace("*", ""), clean(r[3])))
        if row:
            qs.append(row)
        if L in ("кататься", "катиться"):
            qs.append(Q("m05-other-pairs", r"^Мне нравится кататься"))
        return qs
    if generic:
        qs.append(Q("m02-direction", r"^Unidirectional verbs describe", end=r"\s*,?\s*e\.g\.:?\s*$") if role == "uni" else Q("m02-direction", r"^Multidirectional verbs describe"))
    if generic and fam in ("идти", "ехать", "лететь"):
        qs.append(Q("m02-direction", r"^The basic meaning of the verbs идти") if role == "uni" else Q("m01-pairs", r"^The present tense of all Russian verbs has a twofold", n=640))
    if fam == "идти":
        if role == "uni":
            qs.append(Q("m01-pairs", r"^The verb идти means"))
            if re.search(r"автобус|поезд|трамва|пароход|корабл|танк|метро|электричк|рейс", sent, re.I):
                qs.append(Q("m01-pairs", r"^The verb ехать refers", start=r"Note\. —", n=420))
        else:
            qs.append(Q("m01-pairs", r"^Ходить, ездить: these two", end=r"\s+Летать:"))
    elif fam == "ехать":
        if role == "uni":
            qs.append(Q("m01-pairs", r"^The verb ехать refers", end=r"\s+Note\. —"))
        else:
            qs.append(Q("m01-pairs", r"^Ходить, ездить: these two", end=r"\s+Летать:"))
    elif fam == "лететь":
        if role == "uni":
            qs.append(Q("m01-pairs", r"^Лететь: this verb"))
        else:
            qs.append(Q("m01-pairs", r"^Ходить, ездить: these two", start=r"Летать:"))
            qs.append(Q("m02-direction", r"^Like the verb \"ходить\" \(по комнате\)", n=640))
    elif fam in ("нести", "вести", "везти"):
        qs.append(Q("m04-carrying", r"^The verb \"to carry\" in Russian is rendered", end=r"\s+Note that these verbs directly") if fam != "вести" else None)
        key = {"нести": "on foot", "везти": "by vehicle", "вести": "lead"}[fam]
        row = table_line("m04-carrying", "", lambda r: key in r[0],
                         lambda h, r: "%s — %s: %s; %s: %s; %s: %s" % (r[0], h[1].lower(), r[1], h[2].lower(), r[2], h[3].lower(), r[3]))
        qs.append(row)
        if fam == "вести":
            qs.append(Q("m04-carrying", r"^This verb also follows the pattern", n=640))
        if fam != "вести" and (MM.IDIOM_UNPREF.search(sent) or re.search(r"очк|костюм|пальто|шляп|ботинк|одежд|плать|шапк|форм", sent)):
            qs.append(Q("m04-carrying", r"^Note some special uses of these verbs"))
    elif fam == "бежать":
        qs.append(Q("m05-other-pairs", r"^The verbs бегать-бежать", n=640) if role == "uni" else Q("m05-other-pairs", r"^The verbs бегать-бежать", end=r"\s+Note that in the conjugation"))
    elif fam == "плыть":
        qs.append(Q("m05-other-pairs", r"^The verb плавать — плыть", n=640))
    else:
        qs.append(Q("m01-pairs", r"^Verbs of motion are a distinct class", start=r"Unprefixed verbs of motion", end=r"\s+Thus, the roots"))
        qs.append(Q("m01-pairs", r"^Verbs of motion are a distinct class", start=r"Thus, the roots", end=r"\s+The roots also distinguish"))
    return qs


def po_forms(L, sent, kind):
    qs = []
    if kind == "po":
        qs.append(Q("m06-po", r"^The perfective aspect of \"Going Verbs\" is formed", n=520))
        if L == "пойти":
            qs.append(Q("m06-po", r"^Note\. — that the vowel -ё-", end=r"\s+The future perfective \(поеду"))
        elif L == "поехать":
            qs.append(Q("m06-po", r"^Note\. — that the vowel -ё-", start=r"The future perfective \(поеду"))
        elif L == "полететь":
            qs.append(Q("m06-po", r"^The perfective verb полететь"))
        qs.append(Q("m06-po", r"^The addition of the prefix по- to a unidirectional", end=r",?\s+e\.g\.:?\s*$"))
    else:
        qs.append(Q("m06-po", r"^Adding a prefix to the repeated function verbs", start=r"However, prefixes"))
        if kind == "while":
            qs.append(Q("m06-po", r"^a\) Prefix \"по-\" denoting"))
        else:
            qs.append(Q("m06-po", r"^b\) Prefix \"с-\" implying"))
    if re.search(r"(?<![а-яё])за\s+[а-яё]+(ом|ем|ой|ей|ёй|ами|ями)\b", sent):
        qs.append(Q("m06-po", r"^Note the preposition: after \"going verbs\""))
    fam = uni_of(MM.PAIR.get(L, L)) if L in MM.PO_PF else None
    qs.append(table_line("m06-po", "Imperfective", lambda r: L in r[1:] or any(L in x for x in r[1:]),
                         lambda h, r: "%s: perfective %s · «for a while» %s · «round trip» %s" % (r[0], r[1], r[2], r[3])))
    return qs


PREFIX_Q = {
    "в": lambda L, P: [],
    "вы": lambda L, P: [],
    "при": lambda L, P: [Q("m10-pri-u", r"^Notice that the prefix при-", end=r"\s+Note\. —")]
    + ([Q("m10-pri-u", r"^Notice that the prefix при-", start=r"Note\. — The verbs приходить", n=700)] if L in ("приходить", "приезжать") else []),
    "у": lambda L, P: [Q("m10-pri-u", r"^Notice that the prefix при-", end=r"\s+Note\. —")],
    "под": lambda L, P: [Q("m11-pod-ot", r"^Verbs of motion with the prefix под-", end=r"\s+Verbs of motion with the prefix от-"),
                         ],
    "от": lambda L, P: [Q("m11-pod-ot", r"^Verbs of motion with the prefix под-", start=r"Verbs of motion with the prefix от-")],
    "до": lambda L, P: [Q("m12-do", r"^\"Going verbs\" with prefix \"до-\"", n=620)],
    "пере": lambda L, P: [Q("m13-pere", r"^The prefix \"пере-\" implies", n=640)],
    "про": lambda L, P: [Q("m14-pro", r"^The prefix \"про-\" implies", n=640)],
    "за": lambda L, P: [Q("m15-za", r"^The prefix \"за-\" implies", n=700)],
    "с": lambda L, P: [] if L.endswith("ся") else [Q("m16-s-raz", r"^The prefix \"с-\" implies", n=520)],
    "раз": lambda L, P: [],
    "об": lambda L, P: [Q("m17-ob-iz", r"^The prefix \"об-\" indicates", n=700)],
    "из": lambda L, P: [],
    "вз": lambda L, P: [],
    "на": lambda L, P: [],
}
CARRY_PARA = {"в": ("m09-v-vy", r"^Ввозить — ввезти"), "вы": ("m09-v-vy", r"^Ввозить — ввезти"),
              "при": ("m10-pri-u", r"^With the carrying verbs"), "у": ("m10-pri-u", r"^With the carrying verbs"),
              "под": ("m11-pod-ot", r"^Подвозить — подвезти"), "от": ("m11-pod-ot", r"^Подвозить — подвезти"),
              "пере": ("m13-pere", r"^Переносить — перенести"), "про": ("m14-pro", r"^Проводить — провести")}


def prefixed(L, p, sent, idiom, lesson_id, aspect_mode, kind):
    qs = []
    m = MM.PRE_RE.match(L)
    pf = m.group(1)
    g = MM.GROUP[pf]
    stem = m.group(2)
    if idiom:
        qs.append(Q("m20-prefixed-idioms", r"^The verbs \"носить\", \"возить\" and \"водить\" have basically", n=420))
        seg = re.search(r"(?<![а-яё])%s- — .*?(?= (?:вы|под|от|до|пере|про|на)- — |$)" % re.escape(g), clean(
            next((b.get("text") for b in lesson("m20-prefixed-idioms")[0] if b.get("t") == "p" and b.get("text", "").startswith("Other meanings from the prefix table")), "")))
        carry = None
        if g in CARRY_PARA and CARRYING.search(stem):
            carry = seg_q(CARRY_PARA[g][0], CARRY_PARA[g][1], L, ASPECT_PARTNER(L))
        if carry:
            qs.append(carry)
        elif seg:
            qs.append((trim(seg.group(0), 480), "Wikipedia, «Russian grammar» § Verbs of motion (CC BY-SA 4.0)"))
        return qs
    row = wp_row(L)
    if row:
        qs.append(row[0])
    if not aspect_mode:
        qs.extend(PREFIX_Q.get(g, lambda L, P: [])(L, p))
    if g in ("в", "вы") and not aspect_mode:
        if stem.endswith(("ходить", "йти")):
            qs.append(Q("m09-v-vy", r"^The verbs входить", end=r"\s+The verbs въезжать"))
        elif stem.endswith(("ехать", "езжать")):
            qs.append(Q("m09-v-vy", r"^The verbs входить", start=r"The verbs въезжать"))
    if g in CARRY_PARA and CARRYING.search(stem) and not aspect_mode:
        part = ASPECT_PARTNER(L)
        part_q = seg_q(CARRY_PARA[g][0], CARRY_PARA[g][1], L, part)
        if part_q:
            qs.append(part_q)
        if g == "от" and L in ("относить", "отнести", "отвозить", "отвезти", "отводить", "отвести"):
            qs.append(Q("m11-pod-ot", r"^Подвозить — подвезти", start=r"Note that the verbs", end=r"\s+Thus:\s*$", n=420))
    if lesson_id == "m08-how-prefixes-work":
        blk = next((clean(b.get("text")) for b in lesson("m08-how-prefixes-work")[0] if b.get("t") == "p" and b.get("text", "").startswith("In some verbs of motion")), "")
        lead = "In some verbs of motion, adding a prefix requires a different stem shape: "
        letter = None
        if "ъ" in L or "езж" in stem or stem.endswith("ехать"):
            letter = "B"
        elif stem.endswith("йти") or stem.endswith("ходить"):
            letter = "A"
        elif stem.endswith(("бегать", "бежать")):
            letter = "C"
        elif stem.endswith(("плывать", "плыть")):
            letter = "D"
        if sent and re.search(r"(?<![а-яё])вы[а-яё]*", sent.lower()) and g == "вы":
            letter = letter or "E"
        if letter and blk:
            mm = re.search(r"(?:^|\s)%s\. .*?(?= [A-E]\. |$)" % letter, blk[len(lead):] if blk.startswith(lead) else blk)
            if mm:
                qs.append((trim(mm.group(0).strip(), 360), next((n for b, n in zip(*lesson("m08-how-prefixes-work")) if b.get("text", "").startswith("In some verbs of motion")), "")))
    if aspect_mode:
        qs.insert(0, Q("m19-aspect", r"^Motion verbs combine with prefixes", start=r"The unidirectional verb serves"))
        qs.insert(0, Q("m19-aspect", r"^Any prefix \(except", n=300))
        if L in ("приходить", "приезжать", "прийти", "приехать"):
            qs.append(Q("m10-pri-u", r"^Notice that the prefix при-", start=r"Note\. — The verbs приходить", n=620))
    return qs


CARRYING = re.compile(r"(нести|носить|вести|водить|везти|возить)$")


def ASPECT_PARTNER(L):
    return MM.ASPECT_PAIR.get(L) or next((k for k, v in MM.ASPECT_PAIR.items() if v == L), None)


def imperative_quotes(L, word, sent):
    qs = []
    w = plain(word).lower()
    if w in ("идёмте", "идемте", "едемте"):
        qs.append(Q("m03-now-and-lets-go", r"^The forms идёмте и едемте|^The forms идёмте and едемте"))
    elif L in ("идти", "ехать", "ходить", "ездить", "пойти", "поехать"):
        qs.append(Q("m03-now-and-lets-go", r"^The imperative of идти is идите"))
        qs.append(Q("m03-now-and-lets-go", r"^The Imperative is: идите"))
    elif L in ("приходить", "приезжать", "прийти", "приехать"):
        qs.append(Q("m03-now-and-lets-go", r"^Приходите and приезжайте both mean"))
    if not w.endswith(("те", "мте")):
        qs.append(Q("m03-now-and-lets-go", r"^The familiar form of the imperative does not have"))
    return qs


# ── the cue the sentence itself gives ─────────────────────────────────────
HABIT = re.compile(r"(?<![а-яё])(кажд\w+|часто|обычно|всегда|иногда|редко|никогда|ежедневно|постоянно|регулярно|по утрам|по вечерам|раз в \w+)(?![а-яё])", re.I)
ABIL = re.compile(r"(?<![а-яё])(уме\w+|умел\w*|может\w*|могу|можешь|можем|любит\w*|люблю|любишь|любили|нравит\w*|научи\w+|привык\w*)(?![а-яё])", re.I)
VARY = re.compile(r"(?<![а-яё])по\s+[а-яё]+(?:ам|ям|у|ю|е|и|ой|ей)(?![а-яё])", re.I)
GOAL = re.compile(r"(?<![а-яё])(сейчас|сюда|туда|домой|навстречу|вот|вон|к\s+[а-яё]+у|в\s+[А-Яа-яёЁ]+(?:у|ю|ь)?)(?![а-яё])")


def cue_line(role, form, sent):
    if role == "multi":
        m = HABIT.search(sent)
        if m:
            return "«%s» marks a repeated or habitual action, which is the job of the many-directions verb." % m.group(1)
        m = ABIL.search(sent)
        if m:
            return "«%s» speaks of ability or liking — general motion, again the many-directions verb." % m.group(1)
        m = VARY.search(sent)
        if m:
            return "«%s» — movement in various directions, not towards one goal." % m.group(0)
        if form is not None and form.tag.tense == "past":
            return "A past tense with no single goal in sight: repeated trips, or one completed round trip."
    elif role == "uni":
        m = re.search(r"(?<![а-яё])(сейчас|сюда|туда|домой|навстречу|вот|вон)(?![а-яё])", sent, re.I)
        if m:
            return "«%s» gives a direction or a moment: one way, in progress, so the one-direction verb." % m.group(1)
    return ""


def fmt(q, short=False):
    t, s = q
    s = short_src(s).rstrip(".")
    t = t.rstrip()
    if t and t[-1] not in ".!?…":
        t += "."
    return "«%s» — %s." % (t, s) if s else "«%s»" % t


def prov_of(e):
    w = e.get("why") or ""
    for s in reversed([x.strip() for x in w.split("  ·  ")]):
        if re.match(r"^Sentence and translation from Tatoeba", s) or re.match(r"^From (?!the DLI)", s):
            return s
    return "Sentence and translation from Tatoeba (CC BY 2.0 FR)." if e.get("prompt") or e.get("type") == "mc" else ""


def first_sentence(t, n=230):
    t = re.sub(r"(\b\d)\.\s", "\\1.\u0001", t.strip())
    t = re.sub(r"(e\.g\.)\s", "\\1\u0001", t)
    s = re.split(r"(?<=[.!?])\s+(?=[A-ZА-ЯЁ«\"“(])", t)[0].replace("\u0001", " ")
    return trim(s, n)


NEUTRAL = {}


def neutral(kind):
    if kind not in NEUTRAL:
        if kind == "pair":
            NEUTRAL[kind] = Q("m01-pairs", r"^Verbs of motion are a distinct class", start=r"Unprefixed verbs of motion", end=r"\s+Thus, the roots")
        elif kind == "prefix":
            NEUTRAL[kind] = Q("m01-pairs", r"^Verbs of motion are a distinct class", start=r"Thus, the roots", end=r"\s+The roots also distinguish")
        elif kind == "aspect":
            NEUTRAL[kind] = Q("m19-aspect", r"^Motion verbs combine with prefixes", n=420)
        elif kind == "idiom":
            NEUTRAL[kind] = Q("m07-idioms", r"^The uni- and multidirectional distinction rarely")
    return NEUTRAL[kind]


TRANSL = re.compile(r"(?<![а-яё])(перев[её]л\w*|перевод\w*|перевест\w*)(?![а-яё])[^.?!]{0,50}?(?<![а-яё])(язык\w*|английск\w*|русск\w*|французск\w*|немецк\w*|японск\w*|китайск\w*|испанск\w*|иврит\w*|латын\w*|греческ\w*|арабск\w*|корейск\w*|украинск\w*|польск\w*|итальянск\w*|турецк\w*|португальск\w*|текст\w*|книг\w*|слов\w*|фраз\w*|предложени\w*|статью|письм\w*)", re.I)
BEHAVE = re.compile(r"повел[аио]?\s+себя|повёл\s+себя|повели\s+себя", re.I)


def explain(e, stem):
    sent, ans = sentence_of(e)
    hint = None
    if e["type"] == "fill":
        m = HINT.search(e["q"])
        hint = m.group(1) if m and MM.lesson_of(m.group(1)) else None
    L, p = lemma_of(ans, hint)
    if not L:
        return None
    lk = MM.lesson_of(L)
    kind = lk[1] if lk else None
    if L in MM.PO_WHILE:
        kind = "while"
    elif L in MM.S_TRIP:
        kind = "trip"
    asp = aspect_of(L, p)
    if kind in ("trip",):
        asp = "pf"
    role = role_of(L) if kind in ("pair", "sya") else None
    idiom_u = kind in ("pair", "sya") and bool(MM.IDIOM_UNPREF.search(sent) or MM.LUCK.search(sent))
    idiom_p = kind == "prefix" and bool(MM.IDIOM_PREF.search(sent) or TRANSL.search(sent))
    # the other options of a choice
    others = []
    if e["type"] == "mc":
        for i, o in enumerate(e["options"]):
            if i == e["answer"]:
                continue
            l2, p2 = lemma_of(o)
            others.append((o, l2, p2))
    aspect_mode = False
    if kind == "prefix" and e["type"] == "mc" and others:
        aspect_mode = all(l2 and (l2 == ASPECT_PARTNER(L) or ASPECT_PARTNER(l2) == L or l2 == L) for o, l2, p2 in others)
    if stem == "m19-aspect":
        aspect_mode = True
    word = plain(ans).lower()

    # 1 — the answer and its verb
    idiom_any = idiom_u or idiom_p or (kind == "po" and bool(MM.IDIOM_UNPREF.search(sent) or MM.LUCK.search(sent) or BEHAVE.search(sent)))
    mean = defs_of(L, asp, 1 if (kind in ("pair", "sya", "po", "while", "trip") or idiom_any) else 2)
    form = describe(p, asp)
    if form == "the infinitive" and word == plain(L).lower():
        pre = "**%s** (the infinitive)" % word
    else:
        pre = "**%s** is %s of **%s**" % (word, form, L) if form else "**%s** — **%s**" % (word, L)
    tail = ""
    if kind in ("pair", "sya"):
        part = MM.PAIR.get(L) or MM.SYA.get(L)
        if L == "лазать":
            part = "лезть"
        tail = "the one-direction verb of its pair, with **%s** for many directions" % part if role == "uni" else "the many-directions (or there-and-back) verb of its pair, with **%s** for one direction" % part
    elif kind == "po":
        tail = "the perfective of **%s**, «set out»" % (next((k for k, v in MM.PAIR.items() if k in MM.UNI and L == "по" + k), None) or L[2:])
    elif kind == "while":
        tail = "the perfective of **%s** meaning «for a while»" % L[2:]
    elif kind == "trip":
        tail = "the perfective of the many-directions verb, meaning one trip there and back"
    elif kind == "prefix":
        part = ASPECT_PARTNER(L)
        a = {"pf": "perfective", "impf": "imperfective"}.get(asp, "")
        other = {"pf": "imperfective", "impf": "perfective"}.get(asp, "")
        tail = ("%s" % a if a else "") + ("; its %s partner is **%s**" % (other, part) if part and a else "")
    line1 = pre + (" (%s)" % mean if mean else "") + (" — " + tail if tail else "") + "."
    pg = paradigm(L, p, asp)
    if pg:
        line1 += " " + pg + "."
    line1 += " — " + wiki(L) + "."

    # 2 — the rules
    qs = []
    if p is not None and p.tag.mood == "impr" and kind in ("pair", "po", "prefix") and L in ("идти", "ехать", "ходить", "ездить", "пойти", "поехать", "приходить", "приезжать", "прийти", "приехать"):
        qs += imperative_quotes(L, word, sent)
    if kind in ("pair", "sya"):
        qs += unprefixed(L, role, p, sent, idiom_u, kind, generic=not (p is not None and p.tag.mood == "impr"))
        if (not idiom_u) and role == "uni" and p is not None and tense_of(p, asp) == "pres" and re.search(r"завтра|в субботу|вечером|на следующей|послезавтра|в понедельник|во вторник|в среду|в четверг|в пятницу|в воскресенье", sent, re.I) and L in ("идти", "ехать", "лететь"):
            qs.append(Q("m03-now-and-lets-go", r"^Note\. — The present tense of the verbs иду"))
    elif kind in ("po", "while", "trip"):
        qs += po_forms(L, sent, kind)
        if kind == "po" and BEHAVE.search(sent):
            qs.append(Q("m04-carrying", r"^This verb also follows the pattern", n=640))
    elif kind == "prefix":
        qs += prefixed(L, p, sent, idiom_p, stem, aspect_mode, kind)
    qs = [q for q in qs if q]
    seen, uq = set(), []
    for q in qs:
        if q[0] not in seen:
            seen.add(q[0])
            uq.append(q)
    qs = uq
    parts = [line1] + [fmt(q) for q in qs]
    if idiom_any:
        d = defs_of(L, asp, 4)
        if d:
            parts.insert(1, "Wiktionary's senses of **%s**: %s." % (L, d))
    cl = cue_line(role, p, sent) if kind == "pair" and not idiom_u else ""
    if cl:
        parts.append(cl)
    # 3 — the lessons' own examples with this verb
    used = [q[0] for q in qs]
    part = MM.PAIR.get(L) if kind == "pair" else (ASPECT_PARTNER(L) if kind == "prefix" else None)
    cmp_ = [] if idiom_any else compare(L, part, sent, used, 2)
    if cmp_:
        parts.append("Compare: " + " ".join("«%s»%s — %s." % (ru, (" · «%s»" % en) if re.search(r"[А-Яа-я]", en) else ((" (%s)" % en) if en else ""), src.rstrip(".")) for ru, en, src in [(a, b, short_src(c)) for a, b, c in cmp_]))
    # 4 — why not the other choices
    if others:
        notes = []
        for o, l2, p2 in others:
            if not l2:
                continue
            po = plain(o)
            k2 = (MM.lesson_of(l2) or (None, None))[1]
            m2 = MM.PRE_RE.match(l2)
            d2 = defs_of(l2, aspect_of(l2, p2), 1)
            if kind == "pair" and k2 == "pair" and l2 == part:
                notes.append("**%s** is from **%s**, the %s verb" % (po, l2, "many-directions" if role_of(l2) == "multi" else "one-direction"))
            elif kind == "prefix" and m2 and (l2 == ASPECT_PARTNER(L) or ASPECT_PARTNER(l2) == L):
                a2 = aspect_of(l2, p2)
                notes.append("**%s** is %s (**%s**)" % (po, {"pf": "perfective", "impf": "imperfective"}.get(a2, "the other aspect"), l2))
            elif kind == "prefix" and m2 and meaning_of_prefix(l2):
                notes.append("**%s** (**%s**) has the prefix %s" % (po, l2, meaning_of_prefix(l2)))
            elif po == plain(l2).lower():
                notes.append("**%s**%s" % (po, (" means %s" % d2) if d2 else ""))
            else:
                notes.append("**%s** is a form of **%s**%s" % (po, l2, (" (%s)" % d2) if d2 else ""))
        if notes:
            parts.append(("The other choice: " if len(notes) == 1 else "The other choices: ") + "; ".join(notes) + ".")
    why = "  ".join(parts)
    pv = prov_of(e)
    if pv:
        why += "  ·  " + pv

    # the line above the question
    if e["type"] == "mc":
        if idiom_u or idiom_p:
            nk = "idiom"
        elif aspect_mode:
            nk = "aspect"
        elif kind == "prefix":
            nk = "prefix"
        else:
            nk = "pair"
        nq = neutral(nk)
        ctx = "%s (%s)" % (first_sentence(nq[0]), short_src(nq[1]).rstrip(".")) if nq else ""
    else:
        first = qs[0] if qs else None
        ctx = "%s (%s)" % (first_sentence(first[0]), short_src(first[1]).rstrip(".")) if first else ""
    return ctx, why, L


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true")
    ap.add_argument("--show", type=int, default=0)
    args = ap.parse_args(argv)
    n = bad = 0
    nolemma = []
    for f in sorted(glob.glob(os.path.join(COURSE, "m*.json"))):
        stem = os.path.basename(f)[:-5]
        stem_lesson = re.sub(r"-practice(-\d+)?$", "", stem)
        j = json.load(io.open(f, encoding="utf-8"))
        ch = False
        for e in j.get("exercises") or []:
            n += 1
            r = explain(e, stem_lesson)
            if not r:
                bad += 1
                nolemma.append((stem, e.get("q")))
                continue
            ctx, why, L = r
            if e.get("context") != ctx or e.get("why") != why:
                e["context"], e["why"] = ctx, why
                ch = True
            if args.show and n % args.show == 0:
                print(stem, "|", L, "|", (e.get("q") or "")[:80])
                print("  CTX:", ctx)
                print("  WHY:", why)
                print()
        if ch and args.apply:
            io.open(f, "w", encoding="utf-8").write(json.dumps(j, ensure_ascii=False))
    print("exercises: %d   explained by their own verb: %d   verb not found: %d" % (n, n - bad, bad))
    for s, q in nolemma[:15]:
        print("  no verb:", s, q)
    if MISSING:
        print("MISSING lesson text:")
        for x in sorted(MISSING):
            print("  ", x)
    if not args.apply:
        print("report only — add --apply to write")


if __name__ == "__main__":
    main()
