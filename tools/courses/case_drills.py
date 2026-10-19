#!/usr/bin/env python3
"""Drills for the six case courses and the time expressions, from real
sentences only:

  * Tatoeba (tatoeba.org, CC BY 2.0 FR) — Russian sentences with English
    translations, written by people
  * the library's own public-domain Russian books
    (tools/courses/library_sentences.tsv, from library_sentences.py)

Each sentence is filed under every use of a case it shows — «из» + genitive,
the possessor in the genitive, нравится + dative, заниматься + instrumental,
на этой неделе … — and the word that shows it is blanked. The answer is the
word the sentence has; the hint is its dictionary form; the choices are the
same word in its other cases.

    cd /mnt/c/Users/david/projects/govorim-app
    python3 tools/courses/library_sentences.py
    python3 tools/courses/case_drills.py ~/tatoeba/rus.txt
    python3 tools/courses/build_courses.py
→ tools/courses/case_drills.json  { key: [exercise, …] }
"""
import hashlib, io, json, os, re, sys
from collections import defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE); sys.path.insert(0, os.path.dirname(HERE))
import tatoeba_drills as td
from tatoeba_drills import M, WORD, CASES, CASE_EN, parses, tags, form_of, SKIP_TAGS
from tense_examples import read

CAP = int(os.environ.get("CAP", "240"))           # most drills kept per key
NORM_PREP = {"во": "в", "со": "с", "ко": "к", "об": "о", "обо": "о", "надо": "над", "передо": "перед", "подо": "под"}
PREP_CASES = {
    "gent": "без для из от у около после до кроме мимо против вместо из-за из-под возле вокруг среди с напротив вдоль".split(),
    "datv": "к по благодаря вопреки согласно навстречу".split(),
    "accs": "в на за под через про сквозь".split(),
    "ablt": "с над под за перед между".split(),
    "loct": "в на о при".split(),
}
ALLOWED = defaultdict(set)
for c, ps in PREP_CASES.items():
    for p in ps:
        ALLOWED[p].add(c)
for p in ("в", "на", "о", "при"):
    ALLOWED[p].add("loc2")

V_GEN = set("бояться побояться избегать избежать достигать достичь достигнуть касаться коснуться желать пожелать требовать "
            "потребовать дождаться ожидать лишать лишить опасаться стесняться слушаться послушаться добиваться добиться "
            "заслуживать заслужить стыдиться придерживаться держаться пугаться испугаться".split())
V_DAT_IO = set("давать дать говорить сказать показывать показать писать написать посылать послать отправить отправлять "
               "дарить подарить рассказывать рассказать объяснять объяснить приносить принести покупать купить обещать "
               "пообещать продавать продать отдавать отдать передавать передать возвращать вернуть предлагать предложить "
               "напоминать напомнить сообщать сообщить доставить оставить оставлять готовить приготовить читать прочитать".split())
V_DAT = set("помогать помочь мешать помешать верить поверить доверять доверить советовать посоветовать завидовать угрожать "
            "служить принадлежать радоваться обрадоваться удивляться удивиться улыбаться улыбнуться аплодировать кланяться "
            "сочувствовать следовать последовать подражать противоречить соответствовать грозить звонить позвонить "
            "отвечать ответить изменять изменить проиграть проигрывать уступать уступить сопротивляться научиться учиться "
            "научить учить нравиться понравиться надоесть надоедать".split())
V_INS = set("заниматься заняться интересоваться заинтересоваться пользоваться воспользоваться гордиться командовать "
            "руководить управлять владеть овладеть обладать увлекаться увлечься восхищаться любоваться наслаждаться "
            "дорожить рисковать жертвовать пожертвовать злоупотреблять обмениваться делиться поделиться болеть заболеть "
            "торговать заведовать хвастаться похвастаться дышать махать махнуть кивать кивнуть".split())
V_PRED = set("быть стать становиться работать считаться казаться показаться оказаться оказываться остаться оставаться "
             "являться называться служить родиться умереть выглядеть сделаться притворяться притвориться".split())
IMPERS = set("нравится нравятся нравился нравилась нравилось нравились понравился понравилась понравилось понравились "
             "нужен нужна нужно нужны надо нельзя можно пора хочется хотелось кажется казалось стыдно холодно жарко "
             "скучно весело грустно трудно легко жаль лет года исполнилось исполнится удалось удаётся пришлось приходится "
             "повезло везёт страшно некогда интересно было будет".split())
TIME_N = td.TIMEW | td.DAYS | td.MONTHS | set("выходные будни праздник праздники каникулы сутки начало конец середина "
                                               "время пора момент минута раз десятилетие столетие тысячелетие эпоха".split())
CORE_TIME = td.TIMEW | td.DAYS | td.MONTHS | set("выходные будни праздник праздники каникулы сутки десятилетие столетие век".split())
PHASE = {"начало", "конец", "середина"}
SEASONS = {"весна", "лето", "осень", "зима", "утро", "день", "вечер", "ночь"}
MODS = set("этот тот следующий прошлый будущий весь целый каждый первый последний ближайший позапрошлый нынешний "
           "текущий наступающий тот же один другой".split())
ADV_TIME = [("позавчера", r"\bday before yesterday\b"), ("послезавтра", r"\bday after tomorrow\b"),
            ("вчера", r"\byesterday\b"), ("завтра", r"\btomorrow\b"), ("сегодня", r"\btoday\b|\btonight\b"),
            ("недавно", r"\brecently\b|\blately\b"), ("скоро", r"\bsoon\b"), ("всегда", r"\balways\b"),
            ("иногда", r"\bsometimes\b"), ("никогда", r"\bnever\b"), ("часто", r"\boften\b|\bfrequently\b"),
            ("редко", r"\brarely\b|\bseldom\b"), ("рано", r"\bearly\b"), ("поздно", r"\blate\b"),
            ("сейчас", r"\bnow\b|\bright now\b"), ("потом", r"\blater\b|\bafterwards\b"), ("давно", r"\blong ago\b|\bfor a long time\b|\bin a long time\b|\bfor ages\b")]
ADV_SETS = [["позавчера", "вчера", "сегодня", "завтра", "послезавтра"],
            ["недавно", "давно", "скоро", "сейчас", "потом"],
            ["всегда", "иногда", "никогда", "часто", "редко"], ["рано", "поздно", "сейчас", "потом"]]


def noun_at(low, j, allowed):
    """(parse, case) of the noun at j, read unambiguously within `allowed` (loc2 kept apart)."""
    ps = [p for p in parses(low[j]) if p.tag.POS == "NOUN" and p.score > 0.01 and not (tags(p) & SKIP_TAGS)]
    if not ps:
        return None
    lem = ps[0].normal_form
    cs = {p.tag.case for p in ps if p.normal_form == lem and p.tag.case in allowed}
    if "loc2" in cs:
        cs = {"loc2"}
    if len(cs) != 1:
        return None
    c = cs.pop()
    return next(p for p in ps if p.normal_form == lem and p.tag.case == c), c


def adj_at(low, j, noun_p):
    if j < 0:
        return None
    for q in parses(low[j]):
        if q.tag.POS == "ADJF" and q.score > 0.05 and q.tag.case == noun_p.tag.case and q.tag.number == noun_p.tag.number \
                and (noun_p.tag.number == "plur" or q.tag.gender in (noun_p.tag.gender, None)):
            return q
    return None


def phrase_forms(noun_p, adj_p, num):
    out = []
    for c in CASES:
        n = form_of(noun_p, {c, num})
        if not n:
            continue
        if adj_p:
            g = {c, num} | ({noun_p.tag.gender} if num == "sing" and noun_p.tag.gender and adj_p.tag.gender else set())
            if c == "accs" and "anim" in str(noun_p.tag):
                g.add("anim")
            a = form_of(adj_p, g)
            if not a:
                continue
            n = a + " " + n
        if n not in out:
            out.append(n)
    return out


def nom_hint(noun_p, adj_p, num):
    n = form_of(noun_p, {"nomn", num}) or noun_p.normal_form
    if adj_p:
        a = form_of(adj_p, {"nomn", num} | ({noun_p.tag.gender} if num == "sing" and noun_p.tag.gender else set())) or adj_p.normal_form
        return a + " " + n
    return n


class D2(td.Drill):
    def __init__(self, ru, en, cite, words, i0, i1, answer, lemma, why, options):
        super().__init__(ru, en, words, i0, answer, lemma, why, options)
        self.i1, self.cite = i1, cite

    def blanked(self, with_hint):
        s, e = self.words[self.i].span()[0], self.words[self.i1].span()[1]
        hint = (" (" + self.lemma + ")") if with_hint and self.lemma else ""
        return self.ru[:s] + "___" + hint + self.ru[e:]


def scan(ru, en, cite):
    out = []
    ws = list(WORD.finditer(ru))
    low = [w.group().lower() for w in ws]
    timey = bool(re.search(r"\d", ru))
    if not (3 <= len(ws) <= 14) or (timey and not re.search(r"\b\d{1,4}\b", ru)) or td.RUDE_EN.search(en or "") or td.RUDE_RU.search(ru):
        return out
    if re.search(r"\d", ru) and not re.search(r"\b(час|год|минут|лет|мая|июн|июл|январ|феврал|март|апрел|август|сентябр|октябр|ноябр|декабр)", ru):
        return out
    if any(tags(parses(w)[0]) & {"Infr", "Slng", "Obsc"} for w in low):
        return out
    fixed = [m.span() for m in td.FIXED.finditer(ru)]

    def ok(i):
        w = ws[i].group()
        if i > 0 and w[:1].isupper():
            return False
        if not M.word_is_known(w.lower()):
            return False
        a, b = ws[i].span()
        return not any(x <= a < y or x < b <= y for x, y in fixed)

    def add(key, j, p, c, why, adj=None):
        """File the noun at j (and its adjective, if any) under `key`."""
        num = p.tag.number or "sing"
        i0 = j - 1 if adj is not None else j
        if not all(ok(k) for k in range(i0, j + 1)):
            return
        if (j == 0 or i0 == 0) and tags(p) & {"Name", "Surn", "Geox"}:
            return
        ans = ru[ws[i0].span()[0]:ws[j].span()[1]]
        if " " not in ans.strip() and i0 != j:
            return
        opts = phrase_forms(p, adj, num)
        lemma = nom_hint(p, adj, num)
        out.append((key, D2(ru, en, cite, ws, i0, j, ans, lemma, why, opts)))
        if adj is not None and ok(i0):                      # the adjective alone, for agreement
            g = {num} | ({p.tag.gender} if num == "sing" and p.tag.gender else set())
            aopts = [x for x in dict.fromkeys(form_of(adj, {cc} | g) for cc in CASES) if x]
            out.append((c + ":adj", D2(ru, en, cite, ws, i0, i0, ws[i0].group(), adj.normal_form,
                                         "The adjective agrees with «%s»: %s %s." % (ws[j].group(), CASE_EN[c], "plural" if num == "plur" else "singular"), aopts)))

    def noun_after(i, allowed, span=3):
        """Noun (optionally after one adjective) right after position i."""
        for j in range(i + 1, min(len(low), i + 1 + span)):
            r = noun_at(low, j, allowed)
            if r:
                adj = adj_at(low, j - 1, r[0]) if j - 1 > i else None
                if j - 1 > i and adj is None and j > i + 1:
                    return None, None, None
                return j, r, adj
            if not any(q.tag.POS in ("ADJF", "PRTF", "NUMR") or (q.tag.POS == "NPRO") for q in parses(low[j])[:1]):
                return None, None, None
        return None, None, None

    for i, w in enumerate(low):
        p0 = parses(w)[0]
        T0 = tags(p0)
        prev = low[i - 1] if i else ""
        # ── prepositions ──
        pw = NORM_PREP.get(w, w)
        if pw in ALLOWED and not (pw == "в" and i + 1 < len(low) and low[i + 1] == "течение"):
            j, r, adj = noun_after(i, ALLOWED[pw], 2)
            if j is not None:
                p, c = r
                cc = "loct" if c == "loc2" else c
                why = "«%s» + %s." % (w, CASE_EN[cc])
                if c == "loc2":
                    add("loct:loc2", j, p, cc, "«%s» + the second prepositional in stressed -у: в лесу, на берегу." % w, adj)
                add("%s:prep:%s" % (cc, pw), j, p, cc, why, adj)
                lem = p.normal_form
                nxt = noun_at(low, j + 1, {"gent"}) if j + 1 < len(low) else None
                if lem in CORE_TIME or (lem in PHASE and nxt and nxt[0].normal_form in CORE_TIME):
                    add("time:%s:%s" % (pw, cc), j, p, cc, why, adj)
                if cc == "loct" and pw == "на" and lem in ("поезд", "самолёт", "автобус", "машина", "такси", "метро", "трамвай", "велосипед", "корабль", "лодка", "троллейбус", "электричка", "лошадь"):
                    add("loct:transport", j, p, cc, "«на» + prepositional for how you travel: на поезде, на машине.", adj)
        if w == "в" and i + 2 < len(low) and low[i + 1] == "течение":
            j, r, adj = noun_after(i + 1, {"gent"}, 2)
            if j is not None:
                add("time:в течение:gent", j, r[0], "gent", "«в течение» + genitive: during, within.", adj)
        if w == "назад" and i >= 1:
            for j in (i - 1,):
                r = noun_at(low, j, {"accs", "gent"})
                if r and r[0].normal_form in TIME_N:
                    add("time:назад", j, r[0], r[1], "«… назад» (ago): accusative, or genitive after a number — неделю назад, три дня назад.", adj_at(low, j - 1, r[0]))
        # ── quantity, numbers, negation ──
        if w in td.QUANT or w in td.NUM_GS or w in td.NUM_GP or w in td.COLLECT:
            j, r, adj = noun_after(i, {"gent"}, 2)
            if j is not None and p0.tag.case in (None, "nomn", "accs"):
                add("gent:count", j, r[0], "gent", "After «%s» the genitive %s." % (w, "plural" if r[0].tag.number == "plur" else "singular"), adj)
        if w == "нет" or (w in ("было", "будет") and prev == "не"):
            j, r, adj = noun_after(i, {"gent"}, 2)
            if j is not None:
                add("gent:neg", j, r[0], "gent", "«%s» + genitive: there is (was, will be) no …" % ("нет" if w == "нет" else "не " + w), adj)
        # ── verbs that govern a case ──
        if p0.tag.POS in ("VERB", "INFN"):
            lem = p0.normal_form
            for vs, c, key, why in ((V_GEN, {"gent"}, "gent:verb", "«%s» takes the genitive." % lem),
                                    (V_DAT, set(CASES), "datv:verb", "«%s» takes the dative." % lem),
                                    (V_DAT_IO, set(CASES), "datv:io", "«%s»: the person it goes to is in the dative." % lem),
                                    (V_INS, {"ablt"}, "ablt:verb", "«%s» takes the instrumental." % lem),
                                    (V_PRED, {"ablt"}, "ablt:pred", "After «%s» the noun is in the instrumental." % lem)):
                if lem in vs and not (lem == "быть" and "pres" in T0):
                    j, r, adj = noun_after(i, c, 3)
                    if j is not None and (key not in ("datv:verb", "datv:io") or r[1] == "datv") \
                            and (key != "datv:io" or "anim" in tags(r[0])):
                        add(key, j, r[0], r[1], why, adj)
            if "tran" in T0 and prev != "не" and lem not in V_GEN | V_DAT | V_INS | V_PRED:
                j, r, adj = noun_after(i, {"accs"} | set(CASES), 2)
                if j is not None and r[1] == "accs":
                    add("accs:obj", j, r[0], "accs", "The direct object of «%s»: accusative." % lem, adj)
                elif j is not None and r[1] == "ablt" and r[0].normal_form not in TIME_N:
                    add("ablt:tool", j, r[0], "ablt", "What it is done with: the instrumental, no preposition.", adj)
            if prev == "не" and "tran" in T0:
                j, r, adj = noun_after(i, set(CASES), 2)
                if j is not None and r[1] == "gent":
                    add("gent:neg", j, r[0], "gent", "After a negated verb the object is often genitive.", adj)
        # ── the dative person: мне нравится, детям нужно ──
        if w in IMPERS and i >= 1:
            r = noun_at(low, i - 1, set(CASES))
            if r and r[1] == "datv":
                add("datv:impers", i - 1, r[0], "datv", "The person who likes, needs, feels …: dative.", adj_at(low, i - 2, r[0]))
        # ── possession: a noun + the owner's genitive ──
        if p0.tag.POS == "NOUN" and p0.score > 0.5 and not any(q.tag.POS == "ADJF" for q in parses(w)) \
                and i + 1 < len(low) and prev not in ALLOWED and prev not in td.QUANT:
            r = noun_at(low, i + 1, set(CASES))
            if r and r[1] == "gent" and p0.normal_form not in TIME_N and not (tags(r[0]) & {"Name", "Surn", "Patr", "Geox"}):
                add("gent:poss", i + 1, r[0], "gent", "A noun that tells whose, or of what, follows in the genitive.")
        # ── the subject ──
        if i == 0 or (i == 1 and parses(low[0])[0].tag.POS == "ADJF"):
            r = noun_at(low, i, {"nomn", "accs"} if True else set())
            if r and i + 1 < len(low):
                v = parses(low[i + 1])[0]
                if v.tag.POS == "VERB" and (v.tag.number == r[0].tag.number or v.tag.number is None) and "3per" in tags(v) | {"3per"} and \
                        not (r[0].tag.case == "accs" and "nomn" not in {q.tag.case for q in parses(low[i]) if q.normal_form == r[0].normal_form}):
                    add("nomn:subject", i, r[0], "nomn", "The subject: nominative.", adj_at(low, i - 1, r[0]) if i else None)
        if w in ("это", "вот") and i + 1 < len(low):
            j, r, adj = noun_after(i, {"nomn"}, 2)
            if j is not None and noun_at(low, j, set(CASES)) and noun_at(low, j, set(CASES))[1] == "nomn":
                add("nomn:eto", j, r[0], "nomn", "«%s» + nominative." % w, adj)
        # ── time, without a preposition ──
        if p0.normal_form in ("каждый", "весь", "целый") and i + 1 < len(low) and prev not in ALLOWED:
            r = noun_at(low, i + 1, {"accs"})
            if r and r[0].normal_form in TIME_N:
                add("time:every", i + 1, r[0], "accs", "«%s» + a stretch of time, no preposition: accusative." % p0.normal_form, parses(low[i])[0] if parses(low[i])[0].tag.case == "accs" else None)
        if p0.tag.POS == "ADJF" and i + 1 < len(low) and prev not in ALLOWED and p0.normal_form in MODS:
            r = noun_at(low, i + 1, {"ablt"})
            a = adj_at(low, i, r[0]) if r else None
            if r and a is not None and ok(i) and r[0].normal_form in SEASONS:
                add("time:season", i + 1, r[0], "ablt", "Seasons and parts of the day with этот, прошлый, следующий: instrumental — этим летом, прошлой зимой.", a)
        if w in ("утром", "днём", "днем", "вечером", "ночью", "весной", "летом", "осенью", "зимой") and prev not in ALLOWED and ok(i) \
                and not (i and parses(prev)[0].tag.POS == "ADJF"):
            opts = ["утром", "днём", "вечером", "ночью"] if w in ("утром", "днём", "днем", "вечером", "ночью") else ["весной", "летом", "осенью", "зимой"]
            out.append(("ablt:time", D2(ru, en, cite, ws, i, i, ws[i].group(), "", "The instrumental of the noun is the adverb of time.", opts)))
        if p0.tag.POS == "ADJF" and "Anum" in T0 and i + 1 < len(low):
            r = noun_at(low, i + 1, {"gent"})
            if r and r[0].normal_form in td.MONTHS:
                add("time:date", i + 1, r[0], "gent", "In a date the month is genitive: первого мая.")
        if re.fullmatch(r"год[уа]?|году", w) and i >= 1 and re.fullmatch(r"\d{3,4}(-?[а-я]+)?", ws[i - 1].group()) is None:
            pass
    # adverbs of time (Tatoeba only: the English decides the answer)
    if en:
        for word, rx in ADV_TIME:
            if word in low and re.search(rx, en, re.I):
                i = low.index(word)
                st = next((s for s in ADV_SETS if word in s), None)
                others = [x for x in st if x != word and x in low]
                if st and not others and ok(i):
                    out.append(("time:adv", D2(ru, en, cite, ws, i, i, ws[i].group(), "", "", st)))
                break
    return out


def exercise(d, n):
    """Type the sentence's own word; the hint is its dictionary form. No
    explanation of ours: the course adds the source's sentence for the rule."""
    if not d.lemma:
        return None
    src = ("From %s." % d.cite) if d.cite else "Sentence and translation from Tatoeba (CC BY 2.0 FR)."
    return {"type": "fill", "q": d.blanked(True), "prompt": d.en or ("*" + d.cite + "*"), "answers": [d.answer], "why": src}


def main():
    path = sys.argv[1] if len(sys.argv) > 1 else os.path.expanduser("~/tatoeba/rus.txt")
    rows = [(ru, en, "") for ru, en, _ in read(path)]
    lib = os.path.join(HERE, "library_sentences.tsv")
    nlib = 0
    if os.path.exists(lib):
        for line in io.open(lib, encoding="utf-8"):
            pr = line.rstrip("\n").split("\t")
            if len(pr) >= 3 and pr[0]:
                rows.append((pr[0], "", pr[2])); nlib += 1
    print("%d Tatoeba pairs, %d library sentences" % (len(rows) - nlib, nlib), flush=True)
    found = defaultdict(list)
    seen = set()
    for k, (ru, en, cite) in enumerate(rows):
        if ru in seen:
            continue
        seen.add(ru)
        for key, d in scan(ru, en, cite):
            found[key].append(d)
        if k and k % 50000 == 0:
            print("  %d sentences…" % k, flush=True)
    out = {}
    for key, ds in sorted(found.items()):
        # Tatoeba (with a translation) first, short sentences first, then a fixed shuffle
        ds.sort(key=lambda d: (not d.en, len(d.words) > 10, hashlib.md5((key + d.ru).encode()).hexdigest()))
        pick, lem, sents = [], defaultdict(int), set()
        for cap in (1, 2, 4, 8):
            for d in ds:
                lk = (d.lemma or d.answer.lower())
                if lem[lk] >= cap or d.ru in sents:
                    continue
                lem[lk] += 1; sents.add(d.ru); pick.append(d)
                if len(pick) >= CAP:
                    break
            if len(pick) >= CAP:
                break
        exs = [e for e in (exercise(d, n) for n, d in enumerate(pick)) if e]
        out[key] = exs
        print("%-28s %6d found, %4d kept" % (key, len(ds), len(exs)))
    io.open(os.path.join(HERE, "case_drills.json"), "w", encoding="utf-8").write(json.dumps(out, ensure_ascii=False))


if __name__ == "__main__":
    main()
