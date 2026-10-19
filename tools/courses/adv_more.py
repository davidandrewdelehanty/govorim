"""More keys for adv_drills.py: the topics of an intermediate–advanced
syllabus — adjectival nouns, short adjectives with complements, сам, cause,
condition, concession, тоже/также, где/куда/откуда, много/многие, давай/пусть,
time conjunctions, и/а/но, зато/а то, либо/или, correlatives, particles,
prefixed verbs. Real sentences only; the choices are real words."""
import re
from tatoeba_drills import M, parses, tags, form_of

CASES = ("nomn", "gent", "datv", "accs", "ablt", "loct")
SUBST = set("знакомый учёный рабочий больной взрослый военный служащий столовая ванная гостиная прошлое будущее мороженое "
            "насекомое животное второе первое заведующий дежурный портной русский часовой лесничий водитель пленный раненый "
            "приезжий прохожий родной близкий любимый богатый бедный слепой глухой немой святой молодой старый горничная "
            "детская парикмахерская булочная кладовая".split())
SHORT_COMP = {"похожий": ("на", "accs"), "готовый": ("к", "datv"), "довольный": (None, "ablt"), "занятый": (None, "ablt"),
              "рад": (None, "datv"), "радый": (None, "datv"), "согласный": ("с", "ablt"), "полный": (None, "gent"),
              "достойный": (None, "gent"), "богатый": (None, "ablt"), "известный": (None, "ablt"), "способный": ("на", "accs"),
              "виноватый": ("в", "loct"), "знакомый": ("с", "ablt"), "верный": (None, "datv"), "благодарный": (None, "datv"),
              "обязанный": (None, "datv"), "сильный": ("в", "loct"), "слабый": ("в", "loct"), "уверенный": ("в", "loct"),
              "нужный": (None, "datv"), "свойственный": (None, "datv"), "чуждый": (None, "datv"), "склонный": ("к", "datv")}
GROUPS = {
    "cause:prep": (["из-за", "благодаря"], True),
    "causeconj": (["потому что", "так как", "поскольку", "поэтому"], True),
    "concession": (["хотя", "несмотря на то что", "несмотря на", "зато"], True),
    "condconj": (["если бы", "если"], True),
    "timeconj": (["как только", "с тех пор как", "прежде чем", "после того как", "до того как", "перед тем как", "когда"], True),
    "tozhe": (["тоже", "также"], True),
    "iano": (["и", "а", "но"], True),
    "coord": (["зато", "а то", "но", "а"], True),
    "disj": (["либо", "или", "то", "не то"], True),
    "particles": (["же", "ведь", "разве", "неужели", "даже"], True),
    "imptypes": (["давайте", "давай", "пусть", "пускай"], True),
    "where": (["где", "куда", "откуда"], False),
    "here": (["здесь", "сюда", "отсюда"], False),
    "there": (["там", "туда", "оттуда"], False),
    "home": (["дома", "домой"], False),
    "corr": (["так", "такой", "столько", "настолько", "там", "туда", "тот", "то"], False),
}
PREFIXES = ["за", "по", "про", "от", "на", "раз", "рас", "вы", "до", "пере", "под", "при", "у", "с", "из", "ис", "в", "о", "об"]
ROOTS = set("говорить писать читать работать петь играть плакать смеяться кричать думать делать бегать ходить ездить "
            "летать плавать спать сидеть стоять лежать жить есть пить шуметь звонить молчать ждать гулять курить".split())


def phrase_at(low, words):
    """Indices where a (possibly multi-word) phrase starts."""
    n = len(words)
    return [i for i in range(len(low) - n + 1) if low[i:i + n] == words]


def scan_more(ru, en, ws, low, ok, D):
    # adjectival nouns
    for i, w in enumerate(low):
        if "-" in w or not ok(i):
            continue
        p = parses(w)[0]
        if p.tag.POS in ("ADJF", "PRTF") and p.normal_form in SUBST and p.score > 0.2:
            nxt = parses(low[i + 1])[0] if i + 1 < len(low) else None
            if nxt is None or nxt.tag.POS not in ("NOUN", "ADJF", "PRTF"):
                gr = {p.tag.number} | ({p.tag.gender} if p.tag.number == "sing" and p.tag.gender else set())
                if p.tag.animacy and p.tag.case == "accs":
                    gr.add(p.tag.animacy)
                opts = [x for x in dict.fromkeys(form_of(p, {c} | gr) for c in CASES) if x]
                D("subst", i, i, ws[i].group(), p.normal_form, [], fill=True)
        # short adjective + complement
        if p.tag.POS == "ADJS" and p.normal_form in SHORT_COMP and ok(i):
            prep, case = SHORT_COMP[p.normal_form]
            j = i + 1
            if prep and j < len(low) and low[j] in (prep, prep + "о"):
                j += 1
            if j < len(low) and ok(j):
                r = [q for q in parses(low[j]) if q.tag.POS == "NOUN" and q.tag.case == case and q.score > 0.1]
                if r:
                    q = r[0]
                    opts = [x for x in dict.fromkeys(form_of(q, {c, q.tag.number or "sing"}) for c in CASES) if x]
                    D("shortcomp", j, j, ws[j].group(), q.normal_form, [], fill=True)
        # сам
        if p.normal_form == "сам" and p.tag.POS == "ADJF" and ok(i) and not re.search(r"\bSami\b", en or ""):
            gr = {p.tag.number} | ({p.tag.gender} if p.tag.number == "sing" and p.tag.gender else set())
            opts = [x for x in dict.fromkeys(form_of(p, {c} | gr) for c in CASES) if x]
            D("sam", i, i, ws[i].group(), "сам", [], fill=True)
        # много / многие, несколько / некоторые
        if w in ("много", "многие", "многих", "многим", "многими") and ok(i) and en:
            D("mnogie", i, i, ws[i].group(), "", [w, "много" if w != "много" else "многие", "несколько", "некоторые"])
        if p.normal_form == "некоторый" and ok(i) and en:
            D("mnogie", i, i, ws[i].group(), "", [w, "несколько", "многие", "много"])
        # prefixed verbs of common roots
        if p.tag.POS == "VERB" and p.score > 0.3 and ok(i):
            for pre in sorted(PREFIXES, key=len, reverse=True):
                lem = p.normal_form
                if lem.startswith(pre) and lem[len(pre):] in ROOTS:
                    root = lem[len(pre):]
                    gr = {g for g in (p.tag.tense, p.tag.person, p.tag.number, p.tag.gender) if g}
                    opts = [w]
                    for alt in PREFIXES:
                        if alt == pre or len(opts) >= 4:
                            continue
                        al = alt + root
                        if not M.word_is_known(al):
                            continue
                        q = next((x for x in M.parse(al) if x.normal_form == al and x.tag.POS == "INFN"), None)
                        f = form_of(q, gr) if q else None
                        if f and f not in opts and M.word_is_known(f):
                            opts.append(f)
                    if len(opts) >= 3:
                        D("prefix", i, i, ws[i].group(), "", opts)
                    break
    # word groups (conjunctions, particles, adverbs): the English decides, so Tatoeba only for those flagged
    for key, (words, need_en) in GROUPS.items():
        if need_en and not en:
            continue
        for wd in sorted(words, key=lambda x: -len(x.split())):
            toks = wd.split()
            for i in phrase_at(low, toks):
                if not ok(i):
                    continue
                if key in ("iano",) and not (i > 0 and ru[ws[i].start() - 2:ws[i].start()].strip() == ","):
                    continue
                if key == "disj" and wd in ("то", "не то") and low.count("то") < 2:
                    continue
                if key == "corr" and not re.search(r",\s*(где|куда|какой|какая|какое|какие|что|сколько|как)\b", ru[ws[i].end():]):
                    continue
                if key == "concession" and wd == "хотя" and i + 1 < len(low) and low[i + 1] == "бы":
                    continue
                if key in ("home", "here", "there") and i and low[i - 1] in ("до", "из", "от", "у", "для", "около", "возле", "в", "на"):
                    continue
                if key == "particles" and wd == "же" and i and low[i - 1] in ("тот", "та", "то", "те", "такой", "так", "всё", "все", "тогда", "там", "тут", "здесь", "сейчас"):
                    continue
                j = i + len(toks) - 1
                opts = [x for x in words if x != wd][:3]
                D(key, i, j, ru[ws[i].start():ws[j].end()], "", [wd] + opts)
                break
            else:
                continue
            break
