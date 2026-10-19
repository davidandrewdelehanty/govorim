# English Tenses in Russian. The rules are DLI's, transcribed from the
# Grammar Reference Book I (Lesson 37) and II (Lessons 86–87, 90); the
# examples are real Tatoeba sentence pairs (CC BY 2.0 FR) chosen by
# tools/tense_examples.py — none is written for this course. Exercise
# choices are the other forms of the same verb, produced by pymorphy3.
import io, json, os, random, re
from kit import *

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
PAIRS = os.path.join(HERE, "tense_pairs.json")
DLI = "From the DLI Grammar Reference Book"

try:
    import pymorphy3
    MORPH = pymorphy3.MorphAnalyzer()
except Exception:
    MORPH = None

def _partners():
    try:
        idx = json.load(io.open(os.path.join(ROOT, "public/vocab/verbs/index.json"), encoding="utf-8"))
        rank = {v: i for i, (v, n) in enumerate(idx["top"])}
        out = {}
        for v, pr in (idx.get("pairs") or {}).items():
            ps = sorted(pr[1] or [], key=lambda x: rank.get(x, 1e9))
            if ps:
                out[v] = (pr[0], ps[0])
        return out
    except Exception:
        return {}
PART = _partners()

PRON = {"я": ("1per", "sing"), "ты": ("2per", "sing"), "он": ("3per", "sing"), "она": ("3per", "sing"),
        "оно": ("3per", "sing"), "мы": ("1per", "plur"), "вы": ("2per", "plur"), "они": ("3per", "plur")}

def _forms(p):
    """The verb in other tenses and aspects, as it would stand in this sentence."""
    if not MORPH:
        return []
    lem, asp = p["lemma"], p["aspect"]
    pr = PART.get(lem)
    impf = lem if asp == "impf" else (pr[1] if pr else None)
    pf = lem if asp == "perf" else (pr[1] if pr else None)
    words = [w.lower() for w in re.findall(r"[А-Яа-яЁё]+", p["ru"])]
    per, num = "3per", (p.get("number") or "sing")
    for w in words:
        if w in PRON:
            per, num = PRON[w]
            break
    if p.get("person"):
        per = p["person"]
    gen = p.get("gender") or ("femn" if re.search(r"(ла|лась)\b", p["form"]) else "masc")
    def inf(v, tags):
        try:
            q = MORPH.parse(v)
            q = next((x for x in q if x.tag.POS in ("INFN", "VERB")), None)
            r = q.inflect(set(tags)) if q else None
            return r.word if r else None
        except Exception:
            return None
    out = []
    for v in (impf, pf):
        if not v:
            continue
        if num == "plur":
            out.append(inf(v, {"past", "plur"}))
        else:
            out.append(inf(v, {"past", "sing", gen if gen in ("masc", "femn", "neut") else "masc"}))
        t = "pres" if v == impf else "futr"
        out.append(inf(v, {t, per, num}))
    if impf and impf not in ("мочь", "хотеть", "уметь"):
        aux = {"1per": {"sing": "буду", "plur": "будем"}, "2per": {"sing": "будешь", "plur": "будете"},
               "3per": {"sing": "будет", "plur": "будут"}}[per][num]
        out.append(aux + " " + impf)
    return [x for x in dict.fromkeys(out) if x]

def _exercise(p, why):
    form = p["form"]
    ru = p["ru"]
    i = ru.find(form)
    if i < 0:
        return None
    blank = ru[:i] + "___" + ru[i + len(form):]
    norm = lambda x: x.lower().replace("ё", "е")
    seen, opts = {norm(form)}, []
    for f in _forms(p):
        if norm(f) not in seen:
            seen.add(norm(f)); opts.append(f)
    # Type the verb as the sentence has it; the hint is its infinitive.
    blank = ru[:i] + "___ (" + p["lemma"] + ")" + ru[i + len(form):]
    return FILL(blank, [form], why, prompt=p["en"])

def _examples(key, limit=12):
    try:
        d = json.load(io.open(PAIRS, encoding="utf-8"))
    except Exception:
        return [], []
    rows = (d.get(key) or {}).get("pairs") or []
    ex = [(r["ru"], r["en"]) for r in rows[:limit]]
    asp = {"impf": "imperfective", "perf": "perfective"}
    tn = {"pres": "present", "past": "past", "futr": "future", "inf": "infinitive"}
    exs = []
    for r in rows[:limit]:
        why = "Sentence and translation from Tatoeba (CC BY 2.0 FR)."
        e = _exercise(r, why)
        if e:
            exs.append(e)
    return ex, exs

TATOEBA = NOTE("Examples: sentence pairs from Tatoeba (tatoeba.org), CC BY 2.0 FR.")

DLI_TENSES = [
  P("As it can be seen from the above explanations English tenses may be rendered in Russian by either the imperfective or the perfective aspect of the corresponding Russian verbs. However, the following hints may be helpful:"),
  T(["English", "Russian"], [
    ["1. Present: I write letters.", "Present, imperfective: Я пишу письма."],
    ["2. Present Perfect Progressive: I have been writing all morning.", "Present, imperfective: Я пишу уже всё утро. («уже» usually added)"],
    ["3. Any progressive tense: I am writing a letter. I was writing a letter. I will be writing a letter.", "Imperfective aspect of the corresponding verb: Я пишу письмо. Я писал письмо. Я буду писать письмо."],
  ], row_heads=False),
  P("Also present perfect if it means that the action continues through the present: *I have lived here for one year already.* — **Я живу здесь уже год.**"),
  NOTE("DLI, Lesson 37."),
]

DLI_ASPECT = [
  P("In Russian almost every action is expressed by a pair of verbs. Such twin-verbs differ only in what we call aspect, and otherwise have the same basic meaning. The imperfective aspect emphasizes the action itself. The perfective aspect places the emphasis on the result of the action."),
  P("The verb писать is called imperfective and has the following two meanings: 1. to be writing, to be in the process of writing for a certain period of time (in the present, past or future): *Я сейчас пишу.* — I am writing right now. *Вчера я весь вечер писал.* — Yesterday I wrote (was writing) all evening. *Завтра я всё утро буду писать.* — Tomorrow I will write (will be writing) all morning. 2. to write habitually (often, always, etc.): *Я каждый день пишу. Я каждый день писал. Я каждый день буду писать.*"),
  P("The verb написать is called perfective and expresses a single action with emphasis on its completion (either in the past or in the future, since the present tense deals only with actions in progress): *Я написал письмо; вот оно на столе.* *Ему я написал по-английски.*"),
  P("Often the use of the proper aspect is clearly indicated by the context. For instance, the following words and phrases require the use of an imperfective verb: I. indicating duration of an action: долго, недолго, всё утро, весь день, etc. II. indicating habitual action: обычно, всегда, иногда, часто, редко, каждый день, каждую неделю, etc."),
  H("The five tenses of a \"twin-verb\" (3 + 2)"),
  P("The imperfective verb has 3 tenses: the present, the past, and the future. The perfective verb has 2 tenses: the past and the future."),
  T(["", "infinitive", "present", "past", "future"], [
    ["imperf.", "писать", "пишу, -ешь", "писал", "буду писать"], ["perf.", "написать", "—", "написал", "напишу, -ешь"],
  ]),
  P("The perfective future consists of one word only and resembles in form the present tense."),
  NOTE("DLI, Lesson 37."),
]

DLI_FUTURE = [
  P("**Future tense after «когда» and «как только».** In a sentence referring to the future with a subordinate clause introduced by \"when\" or \"as soon as\" the verbs of both clauses are in the future:"),
  EX(("Я буду читать письма, когда ты будешь учить диалог.", "")),
  P("An action of the subordinate clause which is to be completed before the action of the main clause is rendered by the perfective future:"),
  EX(("Когда я сделаю уроки, я буду слушать радио.", ""), ("Как только я получу от него письмо, я напишу вам.", "")),
  NOTE("DLI, Lesson 37."),
  P("The future condition is expressed in English by the present tense, whereas in Russian it is expressed by the future: *Я пойду в школу завтра, если я буду здоров.* — I'll go to school tomorrow if I am well."),
  NOTE("DLI, Lesson 90."),
]

DLI_WOULD = [
  P("When the action is regarded only as supposed or desirable, the conditional-subjunctive mood is used. The Russian Conditional Subjunctive mood is formed by the combination of the Past tense of the verb and the particle бы (which after a vowel sometimes shortens into \"б\")."),
  EX(("(Я) пошёл бы", "would go, would have gone"), ("(Она) играла бы", "would play, would have played"), ("(Здесь) было бы", "would be, would have been"), ("(Они) купили бы", "would buy, would have bought")),
  P("In English a distinction is made between 1) the supposition referring to the present or future: *If I were well, I would go to school.* and 2) the supposition referring to the past: *If I had been well, I would have gone to school.* The English language expresses this difference by using special forms of the verb for each of these two types of supposition, whereas the Russian language, making no grammatical distinction between them, uses one form which may express either type, depending on the context: *Если бы я был здоров, я пошёл бы в школу.*"),
  P("Caution: Not every English construction with \"would\" expresses the conditional mood. \"Would\" may also denote the \"future-in-the-past\" after the past tense in the main clause. The Russian equivalent for such constructions is the future tense: *He said (that) he would come later.* — **Он сказал, что он придёт позже.**"),
  P("A polite request: *Я хотел бы попросить вашего совета.* (= I would like to ask your advice)."),
  NOTE("DLI, Lesson 90."),
]

DLI_PASSIVE = [
  P("It may be generally stated that for each set of 2 parallel English constructions there is only one construction in Russian:"),
  T(["English", "Russian"], [
    ["The letter is written. / The letter has been written.", "Письмо написано."],
    ["The letter was written. / The letter had been written.", "Письмо было написано."],
    ["The letter will be written. / The letter will have been written.", "Письмо будет написано."],
  ], row_heads=False),
  P("The different shades of meaning expressed in English by the form of the auxiliary verb are expressed in Russian by some additional words: *The school was built when we arrived there.* — Школа была построена, когда мы приехали туда. *The school had been built when we arrived there.* — Школа **уже** была построена, когда мы приехали туда."),
  P("A passive construction, in which the actor is not mentioned, may often be expressed in Russian by an impersonal construction with the verb in the 3rd person plural and with the direct object usually preceding the verb: *Работа была кончена вчера.* — *Работу кончили вчера.* They finished the work yesterday."),
  P("Passive constructions with the indirect object of the verb taking the part of grammatical subject are impossible in Russian: *I was given a book.* — Мне дали книгу. / Мне была дана книга. *He was told this.* — Ему сказали это. / Это было ему сказано. *He was laughed at.* — Над ним смеялись. *The doctor was sent for.* — За доктором послали. *He was helped by his friends.* — Ему помогли друзья."),
  T(["English", "Russian"], [
    ["It is (was) said that …", "Говорят (говорили), что …"], ["It is reported that …", "Сообщают, что …"], ["It is known that …", "Известно, что …"],
    ["He is said to be a good student.", "Говорят, что он хороший студент."], ["We were told that the train had left.", "Нам сказали (нам было сказано), что поезд уже ушёл."],
  ], row_heads=False),
  NOTE("DLI, Lessons 86 and 87."),
]
PASSIVE_EX = [
  MC("The letter has been written.", ["Письмо написано.", "Письмо было написано.", "Письмо будет написано."], 0, DLI + ", Lesson 86."),
  MC("The letter had been written.", ["Письмо написано.", "Письмо было написано.", "Письмо будет написано."], 1, DLI + ", Lesson 86."),
  MC("The letter will have been written.", ["Письмо написано.", "Письмо было написано.", "Письмо будет написано."], 2, DLI + ", Lesson 86."),
  MC("I was given a book.", ["Я был дан книгу.", "Мне дали книгу."], 1, "Passive constructions with the indirect object as subject are impossible in Russian. " + DLI + ", Lesson 87."),
  MC("He was helped by his friends.", ["Он был помогнут друзьями.", "Ему помогли друзья."], 1, DLI + ", Lesson 87."),
  MC("The doctor was sent for.", ["За доктором послали.", "Доктор был послан."], 0, DLI + ", Lesson 87."),
  FILL("It is said that … — ___ , что …", ["Говорят"], DLI + ", Lesson 87."),
  FILL("Работу ___ вчера. (They finished the work yesterday.)", ["кончили"], DLI + ", Lesson 87."),
]

def _sec(id, title, sub, key, intro):
    ex, exs = _examples(key)
    blocks = list(intro)
    if ex:
        blocks += [H("Real examples"), EX(*ex), TATOEBA]
    return SEC(id, title, blocks, exs, sub=sub)

SECTIONS = []
if os.path.exists(PAIRS):
    SECTIONS = [
        SEC("x01-overview", "English tenses, Russian aspects", DLI_ASPECT + DLI_TENSES, [
            MC("I am writing a letter.", ["Я пишу письмо.", "Я напишу письмо.", "Я написал письмо."], 0, "Any progressive tense → imperfective. " + DLI + ", Lesson 37."),
            MC("I have been writing all morning.", ["Я написал всё утро.", "Я пишу уже всё утро.", "Я писал всё утро."], 1, "Present perfect progressive → present, imperfective («уже» usually added). " + DLI + ", Lesson 37."),
            MC("I will be writing a letter.", ["Я напишу письмо.", "Я буду писать письмо.", "Я буду написать письмо."], 1, DLI + ", Lesson 37."),
            MC("I have lived here for one year already.", ["Я живу здесь уже год.", "Я жил здесь уже год."], 0, DLI + ", Lesson 37."),
            MC("Yesterday I wrote (was writing) all evening.", ["Вчера я весь вечер писал.", "Вчера я весь вечер написал."], 0, DLI + ", Lesson 37."),
            MC("How many tenses does a perfective verb have?", ["two: past and future", "three: present, past and future"], 0, DLI + ", Lesson 37."),
        ], sub="DLI Lesson 37 · imperfective and perfective · the five tenses of a twin verb"),
        _sec("x02-present", "Present simple: I write", "→ imperfective present", "pres", DLI_TENSES[:2]),
        _sec("x03-present-prog", "Present progressive: I am writing", "→ imperfective present", "pres-prog", DLI_TENSES[:2]),
        _sec("x04-pres-perf-prog", "Present perfect progressive: I have been writing", "→ imperfective present (often with уже)", "pres-perf-prog", DLI_TENSES[:3]),
        _sec("x05-pres-perf", "Present perfect: I have written", "→ past tense, mostly perfective", "pres-perf", DLI_ASPECT[2:4]),
        _sec("x06-past", "Past simple: I wrote", "→ past tense, imperfective or perfective", "past", DLI_ASPECT[1:4]),
        _sec("x07-past-prog", "Past progressive: I was writing", "→ imperfective past", "past-prog", DLI_TENSES[:2]),
        _sec("x08-past-perf", "Past perfect: I had written", "→ perfective past", "past-perf", DLI_ASPECT[2:3]),
        _sec("x09-used-to", "Used to: I used to write", "→ imperfective past", "used-to", DLI_ASPECT[1:2] + DLI_ASPECT[3:4]),
        _sec("x10-future", "Future: I will write, I'm going to write", "→ perfective future, or буду + imperfective", "fut", DLI_ASPECT[4:7] + DLI_FUTURE),
        _sec("x11-going-to", "Going to", "→ the future", "going-to", DLI_ASPECT[4:7]),
        _sec("x12-would", "Would: the conditional", "→ past tense + бы; future-in-the-past → future", "would", DLI_WOULD),
        SEC("x13-passive", "The passive: is written, was written, will be written", DLI_PASSIVE, PASSIVE_EX, sub="DLI Lessons 86–87"),
    ]
    # A tense with no examples found keeps only its rules.
    fp = _examples("fut-prog")
    if fp[0]:
        SECTIONS.insert(11, _sec("x10b-fut-prog", "Future progressive: I will be writing", "→ буду + imperfective", "fut-prog", DLI_TENSES[:3]))
