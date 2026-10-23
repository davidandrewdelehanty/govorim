#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Real sentences for the Verbs of Motion course.

Nothing here is written by us: every sentence is Tatoeba's (with its
translation, CC BY 2.0 FR; public/vocab/tatoeba) or a public-domain book's
(tools/courses/library_sentences.tsv), and the answer is the word the
sentence actually has. pymorphy3 only reads the grammar: which verb it is,
and which form, so that the sentence can be filed under the lesson that
teaches that verb and the blank given its dictionary form. The one choice
offered is the pair the lesson itself teaches — идти or ходить, вошёл or
вышел, пришёл or приходил — the other member put into the same form.

    cd /mnt/c/Users/david/projects/govorim-app
    python3 tools/courses/motion_mine.py        # → tools/courses/motion_drills.json
"""
import glob, hashlib, io, json, os, re, sys
from collections import defaultdict

import pymorphy3

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
M = pymorphy3.MorphAnalyzer()
WIKT = json.load(io.open(os.path.join(HERE, "motion_src", "wiktionary_verbs.json"), encoding="utf-8"))
KNOWN = {w for w, v in WIKT.items() if v} - {"найти", "находить", "находиться", "избегать", "избежать", "избегнуть"}
# a word that is a perfective and an imperfective verb at once (сходить, проводить): no aspect choice on it
AMBIG = {w for w, v in WIKT.items() if v and {"pf", "impf"} <= {("pf" if re.search(r"\bpf\b", e.get("head") or "") else "impf" if re.search(r"\bimpf\b", e.get("head") or "") else "") for e in v}}

# ── the verbs ────────────────────────────────────────────────────────────
UNI = ["идти", "ехать", "лететь", "бежать", "плыть", "лезть", "брести", "ползти",
       "нести", "вести", "везти", "гнать", "катить", "тащить"]
MULTI = ["ходить", "ездить", "летать", "бегать", "плавать", "лазить", "бродить", "ползать",
         "носить", "водить", "возить", "гонять", "катать", "таскать"]
PAIR = dict(zip(UNI, MULTI)); PAIR.update(dict(zip(MULTI, UNI))); PAIR["лазать"] = "лезть"
GOING = {"идти", "ходить", "ехать", "ездить", "лететь", "летать"}
CARRY = {"нести", "носить", "вести", "водить", "везти", "возить"}
SYA = {"катиться": "кататься", "нестись": "носиться", "гнаться": "гоняться", "тащиться": "таскаться"}
SYA.update({v: k for k, v in list(SYA.items())})
OTHER = set(UNI + MULTI + ["лазать"]) - GOING - CARRY
PO_PF = {"пойти", "поехать", "полететь", "побежать", "поплыть", "полезть", "побрести", "поползти",
         "понести", "повести", "повезти", "погнать", "покатить", "потащить"}
PO_WHILE = {"походить", "поездить", "полетать", "побегать", "поплавать"}
S_TRIP = {"сходить", "съездить", "слетать", "сбегать", "сплавать"}

BASE = r"(йти|ходить|ехать|езжать|ездить|лететь|летать|бежать|бегать|плыть|плывать|плавать|нести|носить|вести|водить|везти|возить|лезть|лезать|лазить|ползти|ползать|брести|бродить|гнать|гонять|катить|катать|катывать|тащить|таскать|таскивать)(ся)?$"
PREFIXES = ["пере", "при", "подо", "под", "про", "разо", "раз", "рас", "вы", "взо", "вз", "вс", "ото", "от", "обо", "об", "изо", "из", "ис", "до", "за", "на", "по", "у", "во", "в", "со", "с", "о"]
PRE_RE = re.compile("^(" + "|".join(PREFIXES) + ")" + BASE)
GROUP = {"пере": "пере", "при": "при", "подо": "под", "под": "под", "про": "про", "разо": "раз", "раз": "раз", "рас": "раз",
         "вы": "вы", "взо": "вз", "вз": "вз", "вс": "вз", "ото": "от", "от": "от", "обо": "об", "об": "об", "о": "об",
         "изо": "из", "из": "из", "ис": "из", "до": "до", "за": "за", "на": "на", "по": "по", "у": "у", "во": "в", "в": "в",
         "со": "с", "с": "с"}
# the lesson for each prefix group
LESSON = {"в": "m09-v-vy", "вы": "m09-v-vy", "при": "m10-pri-u", "у": "m10-pri-u", "под": "m11-pod-ot", "от": "m11-pod-ot",
          "до": "m12-do", "пере": "m13-pere", "про": "m14-pro", "за": "m15-za", "с": "m16-s-raz", "раз": "m16-s-raz",
          "об": "m17-ob-iz", "из": "m17-ob-iz", "вз": "m18-vz-na", "на": "m18-vz-na"}
# the antonym pairs the lessons teach (perfective and imperfective alike)
ANTONYM = {}
def _anto(a, b):
    ANTONYM[a] = b; ANTONYM[b] = a
for pf, ipf in [("войти", "выйти"), ("входить", "выходить"), ("въехать", "выехать"), ("въезжать", "выезжать"),
                ("влететь", "вылететь"), ("влетать", "вылетать"), ("вбежать", "выбежать"), ("вбегать", "выбегать"),
                ("внести", "вынести"), ("вносить", "выносить"), ("ввести", "вывести"), ("вводить", "выводить"),
                ("ввезти", "вывезти"), ("ввозить", "вывозить"), ("влезть", "вылезть"), ("влезать", "вылезать"),
                ("прийти", "уйти"), ("приходить", "уходить"), ("приехать", "уехать"), ("приезжать", "уезжать"),
                ("прилететь", "улететь"), ("прилетать", "улетать"), ("прибежать", "убежать"), ("прибегать", "убегать"),
                ("принести", "унести"), ("приносить", "уносить"), ("привести", "увести"), ("приводить", "уводить"),
                ("привезти", "увезти"), ("привозить", "увозить"), ("приплыть", "уплыть"), ("приплывать", "уплывать"),
                ("подойти", "отойти"), ("подходить", "отходить"), ("подъехать", "отъехать"), ("подъезжать", "отъезжать"),
                ("подбежать", "отбежать"), ("подбегать", "отбегать"), ("подплыть", "отплыть"), ("подплывать", "отплывать"),
                ("поднести", "отнести"), ("подносить", "относить"), ("подвести", "отвести"), ("подводить", "отводить"),
                ("подвезти", "отвезти"), ("подвозить", "отвозить"),
                ("взойти", "сойти"), ("всходить", "сходить"), ("взлететь", "слететь"), ("взлетать", "слетать"),
                ("взбежать", "сбежать"), ("взбегать", "сбегать"), ("всплыть", "сплыть"),
                ("сойтись", "разойтись"), ("сходиться", "расходиться"), ("съехаться", "разъехаться"), ("съезжаться", "разъезжаться"),
                ("слететься", "разлететься"), ("слетаться", "разлетаться"), ("сбежаться", "разбежаться"), ("сбегаться", "разбегаться")]:
    _anto(pf, ipf)
# perfective ↔ imperfective, for the aspect lesson: from the Wiktionary headlines
ASPECT_PAIR = {}
for w, ents in WIKT.items():
    for e in ents or []:
        h = e.get("head") or ""
        m = re.search(r"\b(pf|impf)\b.*?\((?:perfective|imperfective) ([^)]+)\)", h)
        if m:
            for p in re.split(r"\s+or\s+|,\s*", m.group(2)):
                p = p.replace("́", "").strip()
                p = re.sub(r"\s*\(.*$", "", p)
                if PRE_RE.match(p) and p in WIKT:
                    ASPECT_PAIR.setdefault(w, p)
                    break

# ── a short English gloss for the hint, where the sentence alone may not say which verb ──
# the unprefixed pairs: Wikipedia's table (Russian grammar § Verbs of motion), one direction or not
PAIR_EN = {"бежать": "to run", "брести": "to wander, plod", "везти": "to convey by vehicle", "вести": "to lead, take along",
           "гнать": "to drive, chase", "ехать": "to go by vehicle, ride", "идти": "to go, walk", "катить": "to roll",
           "лезть": "to climb", "лететь": "to fly", "нести": "to carry on foot", "плыть": "to swim, float, sail",
           "ползти": "to crawl", "тащить": "to drag"}
FIXED_EN = {"сходить": "to go and come back (on foot)", "съездить": "to go and come back (by vehicle)", "слетать": "to fly there and back",
            "сбегать": "to run there and back", "сплавать": "to swim there and back", "походить": "to walk about for a while",
            "поездить": "to ride about for a while", "полетать": "to fly about for a while", "побегать": "to run about for a while",
            "поплавать": "to swim for a while", "пойти": "to go, set off (on foot)", "поехать": "to set off (by vehicle)",
            "полететь": "to fly off", "побежать": "to start running", "поплыть": "to start swimming, set sail",
            "понести": "to carry off (on foot)", "повести": "to lead off, take along", "повезти": "to take off (by vehicle)",
            "погнать": "to drive off, chase", "покатить": "to roll off", "потащить": "to drag off", "полезть": "to start climbing",
            "побрести": "to plod off", "поползти": "to start crawling"}
MOTION_EN = re.compile(r"\b(go|come|walk|run|fly|carry|bring|take|lead|drive|swim|sail|crawl|climb|ride|move|cross|pass|reach|enter|exit|leave|arrive|approach|depart|descend|ascend|gather|disperse|drop|stop by|call on|get|set off|drag|roll|float|haul|transport|convey|wander|chase|creep|visit|return)\b")
def gloss(lemma):
    if lemma in FIXED_EN:
        return FIXED_EN[lemma]
    if lemma in PAIR_EN:
        return PAIR_EN[lemma] + ", one way"
    if lemma in PAIR and PAIR[lemma] in PAIR_EN:
        return PAIR_EN[PAIR[lemma]] + ", there and back or in general"
    if lemma in SYA:
        base = lemma[:-2]
        for k in (base, PAIR.get(base, "")):
            if k in PAIR_EN:
                return PAIR_EN[k] + " (oneself)"
    ents = WIKT.get(lemma) or []
    cands = []
    for e in ents:
        for d in e.get("defs") or []:
            d = re.sub(r"^\((?:[^()]|\([^()]*\))*\)\s*", "", d).strip()      # (colloquial), (of a vehicle) …
            d = re.split(r"[;:]", d)[0].strip()
            d = re.sub(r"\s*\([^)]*\)", "", d).strip()
            if d and len(d) <= 48 and re.match(r"^to ", d):
                cands.append(d)
    for d in cands:
        if MOTION_EN.search(d):
            return d
    return cands[0] if cands else ""

# ── idioms (figurative uses the course has lessons on) ───────────────────
LUCK = re.compile(r"\b(не\s+)?(повезло|везёт|везло|повезёт|везла|везло)\b(?!\s+(меня|тебя|его|её|нас|вас|их|детей|сына|дочь|домой|в\b|на\b|к\b|до\b))", re.I)
SPATIAL = re.compile(r"\b(в|во|на|из|с|со|к|ко|от|до|через|мимо|за|по|вокруг|сквозь|вдоль|сюда|туда|домой|отсюда|оттуда|вверх|вниз|наверх|назад|вперёд|вперед|навстречу|обратно|дальше|ближе|прочь|внутрь|наружу|сверху|снизу|куда|откуда|где|там|здесь|тут|ко|гости|далеко|близко|рано|поздно|вовремя|опозда\w*|позвон\w*|встреча\w*|встречу|ждать|жд[её]т|ждал\w*|жду|приш[её]л\w*|дом\w*|улиц\w*|город\w*|комнат\w*|двер\w*|окн\w*|лес\w*|рек\w*|гор\w*|дорог\w*|берег\w*|станци\w*|вокзал\w*|школ\w*|магазин\w*|работ\w*|москв\w*|остановк\w*|лестниц\w*|сад\w*|парк\w*|мост\w*|поезд\w*|автобус\w*|машин\w*|самол[её]т\w*|корабл\w*|лодк\w*)\b", re.I)
IDIOM_UNPREF = re.compile(r"(ид[её]т\s+(дождь|снег|град|время|фильм|урок|война|речь|работа)|(дождь|снег|время|фильм|урок|война|речь|работа|часы|поезд|автобус|трамвай)\s+(ид[её]т|идут|шёл|шли|шла|шло)|"
                          r"(мне|тебе|вам|ему|ей|им|нам)\s+(не\s+)?(ид[её]т|идут|везёт|повезло|везло|шло|шла)|(ид[её]т|идут|шла|шло|шёл)\s+(к лицу|на пользу)|"
                          r"\b(в[её]л|вела|вели|вед[её]т|ведут|веду|вести)\s+себя|\bнос[ия]т\w*\s+(очки|костюм|платье|шляпу|имя|название|форму)|"
                          r"\bнес[её]т\w*\s+(ответственность|потери|чушь|ерунду|вздор)|врем[яе]\w*\s+(летит|бежит|идёт|летело|бежало)|"
                          r"\bходят\s+слухи|слух\w*\s+ходит|водил\w*\s+за\s+нос|\bкровь\s+(бежит|идёт|шла)|\bлез\w*\s+в\s+(драку|голову|глаза))", re.I)
IDIOM_PREF = re.compile(r"(провод\w+|провед\w+|провёл|провела|провели|провести)\s+(время|отпуск|каникулы|лето|вечер|ночь|день|выходные)|"
                        r"(перевод\w+|перевед\w+|перевёл|перевела|перевели|перевести)\s+(на|с)\s+\S*\s*(язык|английск|русск|французск|немецк|японск|китайск|испанск)|"
                        r"(привод\w+|привед\w+|привёл|привела|привели|привести)\s+(пример|в порядок|в восторг|к)|(нанес\w*|нанёс|нанос\w+)\s+(визит|удар|вред|ущерб)|"
                        r"(произвел\w*|произвёл|производ\w+)\s+впечатлени|(вывел\w*|вывод\w+|вывести)\s+из\s+себя|(сошёл|сошла|сошли|сходит|сойти)\s+с\s+ума|"
                        r"(довел\w*|довёл|довод\w+|довести)\s+до|(подвел\w*|подвёл|подвод\w+|подвести)\s+(меня|тебя|нас|вас|его|её|их|итог)|"
                        r"(завел\w*|завёл|завод\w+|завести)\s+(собаку|кошку|друзей|машину|часы|будильник|мотор|разговор|семью)|"
                        r"(перенес\w*|перенёс|перенос\w+)\s+(встречу|собрание|операцию|боль|болезнь|урок|экзамен|на)|(обошл\w*|обходит\w*|обойтись|обойд\w+)\s+(без|дорого|дёшево|в)|"
                        r"(разошл\w*|расход\w+)\s+во\s+мнени|(вошл\w*|вход\w+|войти)\s+в\s+(историю|моду|положение|привычку|состав|силу)|(вышл\w*|выход\w+|выйти)\s+(замуж|из себя|из строя|в свет)|"
                        r"(зашл\w*|заход\w+)\s+(слишком|далеко)|(нашл\w*|наход\w+|найти|найд\w+)\s+", re.I)

WORD = re.compile(r"[А-Яа-яЁё]+(?:-[А-Яа-яЁё]+)?")
STEM = re.compile(r"(ид|ход|шёл|шел|шла|шли|шло|ед|езд|езж|лет|беж|бег|плы|плав|лез|лаз|бред|брод|полз|нес|нёс|нос|вед|вёл|вел|вод|вез|вёз|воз|гон|гн|кат|тащ|таск|йд|йт)", re.I)
RUDE_EN = re.compile(r"\b(fuck\w*|shit\w*|bitch\w*|cunt|dick|cock|pussy|whore|slut|bastard|asshole|arse\w*|piss\w*|sex\w*|penis|vagina|boob\w*|nude|naked|porn\w*|rape\w*|horny|orgasm|condom|masturbat\w*|nigg\w*|fag\w*|retard\w*|cum|tits?)\b", re.I)
RUDE_RU = re.compile(r"(ху[йияеёю]|пизд|[её]б[аеиуыл]|бля|трах|сук[аи]|жоп|говн|дерьм|шлюх|мудак|мудил|сра[лт]|ссать|секс|порн|голы[йем]|насил|минет)", re.I)
MULTI_CUE = re.compile(r"\b(кажд\w+|часто|обычно|всегда|иногда|редко|никогда|ежедневно|постоянно|регулярно|много|везде|повсюду|туда и обратно|взад и вперёд|по\s+\S+(ам|ям|у|ю)\b|уме\w+|люб\w+|нрав\w+|научи\w+|привык\w+|хорошо|плохо|быстро|медленно|пешком)\b", re.I)
UNI_CUE = re.compile(r"\b(сейчас|сегодня|завтра|куда|туда|сюда|домой|прямо|навстречу|вот|смотри\w*|когда|пока|в данный момент|уже|скоро|вон)\b", re.I)

_cache = {}
def parses(w):
    k = w.lower()
    if k not in _cache:
        _cache[k] = M.parse(k)
    return _cache[k]

def tags(p):
    return set(str(p.tag).replace(" ", ",").split(","))

def inflect(lemma, grams):
    """`lemma` put into the form described by `grams` (pymorphy3), or None."""
    ps = [p for p in M.parse(lemma) if p.normal_form == lemma and p.tag.POS in ("INFN", "VERB")]
    if not ps:
        return None
    for p in ps:
        try:
            x = p.inflect(set(grams))
        except Exception:
            x = None
        if x:
            return x.word
    return None

def grams_of(p):
    g = set()
    for k in (p.tag.tense, p.tag.person, p.tag.number, p.tag.gender, p.tag.mood):
        if k:
            g.add(k)
    if p.tag.POS == "INFN":
        g.add("INFN")
    return g

def lesson_of(lemma):
    """(lesson id, kind) for a motion verb; None for a verb outside the course."""
    if lemma in GOING: return "m02-direction", "pair"
    if lemma in CARRY: return "m04-carrying", "pair"
    if lemma in OTHER: return "m05-other-pairs", "pair"
    if lemma in SYA: return "m05-other-pairs", "sya"
    if lemma in PO_PF: return "m06-po", "po"
    if lemma in PO_WHILE | S_TRIP: return "m06-po", "trip"
    m = PRE_RE.match(lemma)
    if m and lemma in KNOWN:
        g = GROUP[m.group(1)]
        if g == "по":
            return None
        if g in LESSON:
            return LESSON[g], "prefix"
    return None

def key(ru, ans):
    return hashlib.md5((ru + "|" + ans).encode("utf-8")).hexdigest()

def scan(ru, en, cite):
    """The drills this sentence offers: [(lesson, exercise)]."""
    out = []
    ws = list(WORD.finditer(ru))
    if not (3 <= len(ws) <= 14) or re.search(r"\d", ru) or RUDE_RU.search(ru) or (en and RUDE_EN.search(en)):
        return out
    cands = []
    for i, m in enumerate(ws):
        w = m.group()
        if not STEM.search(w) or (i > 0 and w[:1].isupper()):
            continue
        for p in parses(w):
            if p.tag.POS not in ("VERB", "INFN") or p.score < 0.05:
                continue
            L = p.normal_form
            if "ё" in w.lower() and "ё" not in L:
                pass
            les = lesson_of(L)
            if les:
                cands.append((i, p, L, les))
                break
    if not cands:
        return out
    src = ("Sentence and translation from Tatoeba (CC BY 2.0 FR)." if en else ("From " + cite + "."))
    if re.search(r",\.|\.\.(?!\.)|,\s*[,.]|\s[,.]", ru) or ru.count("«") != ru.count("»") or re.search(r"\b[А-ЯЁ]{2,}\b", ru):
        return out
    idiom_u = IDIOM_UNPREF.search(ru) or LUCK.search(ru)
    idiom_p = IDIOM_PREF.search(ru)
    for i, p, L, (lesson, kind) in cands:
        w = ws[i].group()
        s, e = ws[i].span()
        a, b = (idiom_u.span() if idiom_u else (None, None))
        in_idiom_u = idiom_u is not None and a <= s < b
        c, d = (idiom_p.span() if idiom_p else (None, None))
        in_idiom_p = idiom_p is not None and c <= s < d
        def fill(hint, les, keep=False):
            g = gloss(L)
            if g and (not en or kind in ("pair", "sya", "po", "trip")):
                hint = hint + " — " + g
            q = ru[:s] + "___ (" + hint + ")" + ru[e:]
            ex = {"type": "fill", "q": q, "answers": [w], "why": src}
            if en: ex["prompt"] = en
            if keep: ex["keep"] = True
            return (les, ex)
        def mc(options, les):
            o = sorted(set(x.lower() for x in options if x))
            if w.lower() not in o or len(o) < 2:
                return None
            q = ru[:s] + "___" + ru[e:]
            ex = {"type": "mc", "q": en or q, "options": o, "answer": o.index(w.lower()), "why": src, "keep": True}
            if en: ex["ru"] = q
            return (les, ex)
        if in_idiom_u:
            out.append(fill(L, "m07-idioms"))
            continue
        if in_idiom_p:
            out.append(fill(L, "m20-prefixed-idioms"))
            continue
        # the imperative and the «let's go» first person plural of the going verbs: their own lesson
        if (L in GOING or L in ("пойти", "поехать", "полететь", "побежать")) and (p.tag.mood == "impr" or (p.tag.person == "1per" and p.tag.number == "plur")):
            out.append(fill(L, "m03-now-and-lets-go"))
            continue
        if kind == "pair":
            partner = PAIR[L]
            # the going verbs in the present tense conjugate in the first lesson; everything else in the second
            if L in GOING and p.tag.tense == "pres" and p.tag.mood != "impr":
                out.append(fill(L, "m01-pairs"))
            else:
                out.append(fill(L, lesson))
            # the pair as a choice — only where the sentence shows which it wants
            if en and len(cands) == 1 and p.tag.mood != "impr" and (MULTI_CUE.search(ru) or UNI_CUE.search(ru)):
                f = inflect(partner, grams_of(p))
                if f and f != w.lower():
                    r = mc([w, f], lesson)
                    if r: out.append(r)
        elif kind == "sya":
            out.append(fill(L, lesson))
        elif kind == "po":
            out.append(fill(L, lesson))
            base = L[2:] if L != "пойти" else "идти"
            if en and p.tag.tense == "past" and base in PAIR:
                f1 = inflect(base, grams_of(p)); f2 = inflect(PAIR[base], grams_of(p))
                r = mc([w, f1, f2], lesson)
                if r: out.append(r)
        elif kind == "trip":
            out.append(fill(L, lesson))
        elif kind == "prefix":
            pair = ASPECT_PAIR.get(L)
            hint = (L + " / " + pair) if pair else L
            # a prefixed verb used away from any place or direction: its other meaning
            if not SPATIAL.search(ru):
                out.append(fill(hint, "m20-prefixed-idioms"))
                continue
            out.append(fill(hint, lesson))
            if en and L in ("прийти", "приходить", "приехать", "приезжать", "выйти", "выходить", "уйти", "уходить", "войти", "входить"):
                out.append(fill(hint, "m08-how-prefixes-work"))
            if en and L in ANTONYM and p.tag.mood != "impr" and len(cands) == 1:
                f = inflect(ANTONYM[L], grams_of(p))
                if f and f != w.lower() and (M.word_is_known(f)):
                    r = mc([w, f], lesson)
                    if r: out.append(r)
            # the aspect lesson: pf against impf in the past tense
            if pair and p.tag.tense == "past" and len(cands) == 1 and en and L not in AMBIG and pair not in AMBIG:
                f = inflect(pair, grams_of(p))
                if f and f != w.lower() and M.word_is_known(f):
                    r = mc([w, f], "m19-aspect")
                    if r: out.append(r)
            # which prefix? — the same base, other prefixes, in the same form
            if len(cands) == 1 and en and p.tag.mood != "impr":
                m = PRE_RE.match(L)
                base = L[len(m.group(1)):]
                alts = []
                for pre in ("в", "во", "вы", "при", "у", "под", "подо", "от", "ото", "до", "пере", "про", "за", "с", "со", "об", "обо"):
                    cand = pre + base
                    if cand != L and cand in KNOWN and PRE_RE.match(cand) and GROUP[PRE_RE.match(cand).group(1)] != GROUP[m.group(1)]:
                        f = inflect(cand, grams_of(p))
                        if f and f != w.lower() and M.word_is_known(f) and f not in alts:
                            alts.append(f)
                if len(alts) >= 3:
                    pick = sorted(alts, key=lambda x: hashlib.md5((ru + x).encode()).hexdigest())[:3]
                    r = mc([w] + pick, "m21-which-prefix")
                    if r: out.append(r)
    return out


def main():
    found = defaultdict(list)
    seen = set()
    # Tatoeba: the shards, lemma → [[ru, en], …]; a sentence is scanned once
    n = 0
    for f in sorted(glob.glob(os.path.join(ROOT, "public", "vocab", "tatoeba", "s*.json"))):
        d = json.load(io.open(f, encoding="utf-8"))
        for lemma, sents in d.items():
            for ru, en in sents:
                if ru in seen:
                    continue
                seen.add(ru)
                n += 1
                for les, ex in scan(ru, en, ""):
                    found[les].append(("t", ex))
    print("tatoeba: %d sentences" % n, {k: len(v) for k, v in sorted(found.items())}, flush=True)
    # the library
    n = 0
    with io.open(os.path.join(HERE, "library_sentences.tsv"), encoding="utf-8") as fh:
        for line in fh:
            parts = line.rstrip("\n").split("\t")
            if len(parts) < 3:
                continue
            ru, cite = parts[0], parts[2]
            if ru in seen or not STEM.search(ru) or len(ru) > 90:
                continue
            seen.add(ru)
            n += 1
            for les, ex in scan(ru, "", cite):
                found[les].append(("l", ex))
    print("library: %d sentences" % n, {k: len(v) for k, v in sorted(found.items())}, flush=True)
    # Dedupe, and keep the sets varied: at most 3 of one answer form from the
    # library per lesson, translated sentences first, short before long.
    out = {}
    for les, items in found.items():
        uniq, had = [], set()
        for src, ex in items:
            k = key(ex.get("ru") or ex["q"], ex["answers"][0] if ex["type"] == "fill" else ex["options"][ex["answer"]])
            if k in had:
                continue
            had.add(k); uniq.append((src, ex))
        uniq.sort(key=lambda x: (x[0] != "t", len(x[1].get("ru") or x[1]["q"]), hashlib.md5(json.dumps(x[1], ensure_ascii=False).encode()).hexdigest()))
        per = defaultdict(int)
        keep = []
        for src, ex in uniq:
            ans = (ex["answers"][0] if ex["type"] == "fill" else ex["options"][ex["answer"]]).lower()
            cap = 4 if src == "t" else 2
            if per[(src, ans)] >= cap:
                continue
            per[(src, ans)] += 1
            keep.append(ex)
        # inline: the first dozen, translated where possible, the choices among them; the rest in practice sets
        mcs = [e for e in keep if e["type"] == "mc"]
        fills = [e for e in keep if e["type"] == "fill"]
        inline = (mcs[:6] + fills[:8])
        rest = [e for e in keep if e not in inline]
        out[les] = {"ex": inline, "more": rest[:200]}
    io.open(os.path.join(HERE, "motion_drills.json"), "w", encoding="utf-8").write(json.dumps(out, ensure_ascii=False))
    for les in sorted(out):
        print("%-22s inline %2d  more %3d  (mc %d)" % (les, len(out[les]["ex"]), len(out[les]["more"]), sum(1 for e in out[les]["ex"] + out[les]["more"] if e["type"] == "mc")))


if __name__ == "__main__":
    main()
