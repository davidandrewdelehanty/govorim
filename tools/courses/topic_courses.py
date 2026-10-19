"""Two courses that follow an intermediate and an advanced grammar syllabus,
topic by topic. Nothing in them is ours: each lesson's explanation is quoted
from the DLI Grammar Reference Book (public domain), the Wikibooks Russian
textbook (CC BY-SA 4.0) or Wiktionary (CC BY-SA 4.0); each exercise is a real
sentence (Tatoeba, CC BY 2.0 FR, or the library's public-domain books)."""
import io, json, os
from kit import *
import case_courses as cc
import adv_courses as ac
import cases_a, cases_b, forms_a, forms_b, count_a, count_b, count_c

HERE = os.path.dirname(os.path.abspath(__file__))
_T = os.path.join(HERE, "drills.json")
if os.path.exists(_T):
    for _c, _secs in json.load(io.open(_T, encoding="utf-8")).items():
        for _sid, _exs in _secs.items():
            cc.DRILLS["t:%s/%s" % (_c, _sid)] = _exs
SECD = cc.SECD
W = ac.wiktionary
_ALL = {}
for _m in (cases_a, cases_b, forms_a, forms_b, count_a, count_b, count_c):
    for _s in _m.SECTIONS:
        _ALL[_s["id"]] = _s
for _meta, _secs in ac.COURSE_DEFS + cc.COURSE_DEFS + [({}, cc.TIME_MORE)]:
    for _s in _secs:
        _ALL[_s["id"]] = _s


def B(sid):
    """The source blocks of a section built elsewhere (its own credit note included; the exercise note left out)."""
    return [b for b in _ALL[sid]["blocks"] if not (b["t"] == "note" and "exercises are real sentences" in b.get("text", ""))]


def Wk(*words):
    out = []
    for w in words:
        bl = W(w)
        if bl:
            out.append(H(w))
            out += bl
    return out


INTER = [
    SECD("i01-acc-or-gen", "Accusative or genitive?", B("k3-genitive")[-6:] , ["gent:neg", "gent:verb", "accs:obj"], sub="я не пью молока · я жду письма · я жду жену"),
    SECD("i02-adjectival-nouns", "Adjectives used as nouns", [P("*Больной, раненый and знакомый are often used as adjectival nouns.*"), NOTE("From the DLI Grammar Reference Book, Lesson 57.")],
         ["subst"], sub="больной · знакомый · столовая · русский"),
    SECD("i03-short-complement", "Short adjectives and what follows them", B("c7-short"), ["shortcomp"], sub="похож на · готов к · доволен результатом · рад вам"),
    SECD("i04-numerals-adjectives", "Numerals, nouns and adjectives together", B("c4-one-two-three-four") + B("k10-adjectives-plural")[-6:],
         ["gent:count", "t:count/c4-one-two-three-four", "t:count/c1-numbers-nouns"], sub="два новых самолёта · пять ваших новых машин"),
    SECD("i05-compound-numerals", "Compound numerals in every case", B("c5-five-and-up") + B("c6-hundreds-thousands"),
         ["t:count/c5-five-and-up", "t:count/c2-genitive-plural"], sub="двадцати одного · ста сорока пяти"),
    SECD("i06-fractions-collective", "Fractions, двое, трое, оба", B("c7-ordinals-fractions")[:8] + B("c8-collective-half") + B("f6-past-active")[-2:],
         ["t:count/c8-collective-half", "t:count/c7-ordinals-fractions"], sub="две седьмых · трое детей · обоих братьев"),
    SECD("i07-sam-samyi", "сам and самый", B("c5-samyi") + Wk("сам", "самый"), ["sam", "sup:samyi"], sub="я сам · самый новый"),
    SECD("i08-aspect-past", "Aspect in the past tense", B("a1-process-result"), ["asp:past"], sub="писал или написал?"),
    SECD("i09-aspect-infinitive", "Aspect in the infinitive", B("a2-context"), ["asp:inf"], sub="надо делать или сделать?"),
    SECD("i10-aspect-imperative", "Aspect in the imperative", B("a3-commands"), ["asp:imp", "asp:neg"], sub="возьмите · не берите · не забудьте!"),
    SECD("i11-prefixed-motion", "Prefixed verbs of motion, and their other meanings", B("a5-po-s"),
         ["t:motion/m04-prefixes", "t:motion/m05-in-out", "t:motion/m06-toward-away", "t:motion/m07-reach-cross", "t:motion/m08-through-around", "t:motion/m09-drop-by-down", "prefix"],
         sub="принести · отвезти · сходить · проходить"),
    SECD("i12-participles-active", "Active participles", B("f5-present-active") + B("f6-past-active"), ["t:forms/f5-present-active", "t:forms/f6-past-active"],
         sub="читающий · прочитавший"),
    SECD("i13-participles-passive", "Passive participles", B("f3-short-passive")[:6] + B("f4-long-passive") + B("f7-passive-present")[-4:],
         ["t:forms/f3-short-passive", "t:forms/f4-long-passive", "t:forms/f7-passive-present"], sub="написан · написанный · издаваемый"),
    SECD("i14-gerunds", "Деепричастия", B("f8-gerund-imperfective") + B("f9-gerund-perfective"), ["t:forms/f8-gerund-imperfective", "t:forms/f9-gerund-perfective"],
         sub="читая · прочитав"),
    SECD("i15-passive", "The passive voice", B("f3-short-passive")[:2] + B("f7-passive-present")[:5], ["t:forms/f3-short-passive", "t:forms/f7-passive-present"],
         sub="книга куплена · книга читается всеми"),
    SECD("i16-time", "Expressing time", B("t8-this-next-last") + B("t9-every-all-on") + B("t10-in-ago-for"),
         ["time:на:loct", "time:в:loct", "time:every", "time:по:datv", "time:через:accs", "time:назад", "time:за:accs"], sub="на этой неделе · по субботам · через час"),
    SECD("i17-cause", "Expressing cause", Wk("из-за", "благодаря", "потому что", "так как", "поскольку", "поэтому"), ["cause:prep", "causeconj"],
         sub="из-за дождя · благодаря вам · потому что · так как"),
    SECD("i18-condition", "Expressing condition", B("f2-conditional")[:6], ["condconj"], sub="если · если бы"),
    SECD("i19-concession", "Expressing concession", Wk("хотя", "несмотря на", "несмотря на то что", "зато"), ["concession"], sub="хотя · несмотря на"),
    SECD("i20-comparison", "Expressing comparison", B("c1-comparative")[:3] + B("c3-than"), ["comp", "comp:irr", "comp:obj"], sub="новее · лучше · чем · новее моего"),
    SECD("i21-also", "тоже, также — and и, а, но", Wk("тоже", "также") + [
        P("1. И (and) indicates: a) Addition: *Он пилот и механик. Он читает и курит.* b) Similarity: *Он капитан, и я капитан. Здесь хорошо, и там хорошо.* "
          "2. А (and, but) indicates: a) Difference, contrast: *Он пишет, а я читаю. Здесь хорошо, а там плохо.* b) Denial: *Он капитан, а не лейтенант. "
          "Он не пишет, а читает.* 3. Но (but) is used when the second statement somewhat limits the significance of the first one or when it "
          "introduces a statement contrary to it."), NOTE("From the DLI Grammar Reference Book, Lesson 19.")],
         ["tozhe", "iano"], sub="я тоже · а также · и, а, но"),
    SECD("i22-negation", "Expressing negation", B("p2-nekogo") + B("p3-negde"), ["negpron", "negadv", "gent:neg"], sub="никого · некого · нигде · негде · нет времени"),
    SECD("i23-where", "Где? Куда? Откуда?", [P("The adverbs здесь (here), там (there), дома (at home) indicate location and answer the question где. They are not used "
          "after the verb идти. The adverbs сюда (here), туда (there), домой (home) indicate direction and answer the question куда. They are used after "
          "the verb идти: *Где он был? — Он был здесь (там, дома). Куда он идёт? — Он идёт сюда (туда, домой).*"), NOTE("From the DLI Grammar Reference Book, Lesson 19.")]
         + Wk("откуда"), ["where", "here", "there", "home"], sub="где · куда · откуда · здесь · сюда · дома · домой"),
    SECD("i24-uncertainty", "Expressing uncertainty", B("p1-to-nibud"), ["indef"], sub="кто-то · кто-нибудь · где-то"),
    SECD("i25-many-some", "много, многие, несколько, некоторые", [
        P("*На лекции было (не)много студентов.* — (few) many students (as a group). *(Не)многие студенты были на лекции.* — (few) many of the students (as individuals). "
          "Thus \"многие\" (немногие) expresses 2 ideas: some + many (few). The adjectives \"многие\" — \"немногие\" behave like other adjectival modifiers: "
          "*У многих студентов нет словарей. Во многих случаях он был прав.* Like some other adjectives \"многие\" — \"немногие\" can be used as nouns; in "
          "this function the neuter singular \"многое\" is also used: *Многие не любят спорта. После этого разговора я многое понял.*"),
        NOTE("From the DLI Grammar Reference Book, Lesson 88.")] + Wk("некоторый"), ["mnogie"], sub="много студентов · многие студенты · некоторые"),
    SECD("i26-imperative-types", "Kinds of imperative: давай, пусть", B("f1-imperative")[4:9], ["imptypes", "asp:imp"], sub="давайте пойдём · пусть он пишет"),
]

ADV = [
    SECD("v01-time-clauses", "Time in a complex sentence", B("a4-future")[2:] + B("x2-do-togo-kak") + B("x3-poka") + Wk("как только", "с тех пор как", "прежде чем"),
         ["timeconj", "complex", "poka"], sub="когда · как только · с тех пор как · пока не"),
    SECD("v02-condition", "Condition in a complex sentence", B("f2-conditional") + Wk("если", "раз"), ["condconj"], sub="если · если бы · раз"),
    SECD("v03-cause", "Cause in a complex sentence", Wk("потому что", "так как", "поскольку", "поэтому", "так что"), ["causeconj", "cause:prep"],
         sub="потому что · так как · поскольку · поэтому"),
    SECD("v04-concession", "Concession in a complex sentence", Wk("хотя", "несмотря на то что"), ["concession"], sub="хотя · несмотря на то что"),
    SECD("v05-nechego-delat", "«Нечего делать», «некуда поехать»", B("p2-nekogo") + B("p3-negde"), ["negpron", "negadv"], sub="мне нечего делать · некуда поехать"),
    SECD("v06-no-subject", "Sentences without a subject", B("d2-mne-nravitsya") if "d2-mne-nravitsya" in _ALL else [], ["datv:impers"], sub="мне холодно · надо идти · нельзя курить"),
    SECD("v07-coord", "да, зато, а то", Wk("зато", "а то", "да"), ["coord"], sub="дорого, зато хорошо · поторопись, а то опоздаешь"),
    SECD("v08-disj", "либо, или … или, то … то, не то … не то", Wk("либо", "или", "то ... то", "не то"), ["disj"], sub="либо … либо · то дождь, то снег"),
    SECD("v09-object-clauses", "Object clauses: что, чтобы, ли", B("x1-chtoby") + B("x4-li"), ["chtoby", "li"], sub="он сказал, что… · чтобы… · спроси, придёт ли он"),
    SECD("v10-attributive", "Attributive clauses: который", B("p6-kotoryi") + B("f4-long-passive")[-3:], ["kotoryi"], sub="книга, которую я читаю"),
    SECD("v11-correlatives", "там … где, такой … какой, так … что", Wk("такой", "там", "настолько", "столько", "так что"), ["corr"],
         sub="там, где · такой, какой · так, что · столько, сколько"),
    SECD("v12-particles", "Particles: же, ведь, разве, неужели, даже", Wk("же", "ведь", "разве", "неужели", "даже"), ["particles", "li"],
         sub="ведь · же · разве · неужели · даже"),
    SECD("v13-prefixes", "Verbs with prefixes", B("a5-po-s") + B("v4-sya")[:1], ["prefix", "sya"], sub="заговорить · поговорить · проговорить · отговорить"),
]

CREDIT = "Explanations: the DLI Basic Course (public domain), the Wikibooks Russian textbook and Wiktionary (CC BY-SA 4.0); sentences: Tatoeba (CC BY 2.0 FR) and the library's public-domain books"


def _c(id, title, short, mark, blurb, secs):
    return ({"id": id, "title": title, "short": short, "mark": mark, "blurb": blurb, "credit": CREDIT,
             "creditUrl": "https://www.fsi-language-courses.org/russian/courses/dli-russian-basic-course",
             "license": "Public domain · CC BY-SA 4.0 · CC BY 2.0 FR", "licenseUrl": "https://creativecommons.org/licenses/by-sa/4.0/"}, secs)


COURSE_DEFS = [
    _c("inter2", "Intermediate Grammar, Topic by Topic", "Intermediate", "II", "Twenty-six intermediate topics in order — accusative or genitive, "
       "adjectival nouns, numerals, сам and самый, aspect, participles, cause, condition, concession, negation, где/куда, многие — explained "
       "from open sources and practised on real sentences.", INTER),
    _c("adv3", "Advanced Grammar, Topic by Topic", "Advanced", "III", "Complex sentences of time, condition, cause and concession, нечего делать, "
       "subjectless sentences, да/зато/а то, либо/то…то, object and attributive clauses, correlatives, particles and prefixed verbs — explained "
       "from open sources and practised on real sentences.", ADV),
]
