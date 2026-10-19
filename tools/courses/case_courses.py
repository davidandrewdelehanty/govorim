"""Six courses, one per case — what each case does, every preposition that
takes it, the verbs that govern it — and more time expressions for the Time
course. The explanations are the Wikibooks Russian textbook (CC BY-SA 4.0)
and the DLI Basic Course grammar (public domain), word for word; the
exercises are real sentences, from Tatoeba (CC BY 2.0 FR) and from the
library's public-domain Russian books (tools/courses/case_drills.py).

A section's first exercises are in the section; the rest follow as practice
sets of PRACTICE_SIZE (build_courses.py makes them)."""
import io, json, os, re
from kit import *
from wiki_blocks import wiki
import cases_a, cases_b

HERE = os.path.dirname(os.path.abspath(__file__))
_P = os.path.join(HERE, "case_drills.json")
DRILLS = json.load(io.open(_P, encoding="utf-8")) if os.path.exists(_P) else {}
IN_SECTION = 20
MAX_PER_SECTION = 420
WB = "From the Wikibooks Russian textbook (CC BY-SA 4.0)."
DLI = "From the DLI Grammar Reference Book."
_SECS = {s["id"]: s for s in cases_a.SECTIONS + cases_b.SECTIONS}


def dli(sid, *heads):
    """Blocks of a DLI section of the Cases course: all, or from each named heading to the next."""
    bl = [b for b in _SECS[sid]["blocks"] if b["t"] != "note"]
    if not heads:
        return bl
    out = []
    for h in heads:
        on = False
        for b in bl:
            if b["t"] == "h":
                if on:
                    break
                on = (b["text"] == h)
            if on or (h == "" and b["t"] != "h" and not out):
                out.append(b)
        if h == "":
            out = [b for b in bl[:next((k for k, b in enumerate(bl) if b["t"] == "h"), len(bl))]] + out[len(out):]
    return out


# The explanation shown after each exercise: the source's own sentence for
# the rule (DLI, public domain; Wikibooks, CC BY-SA), never a line of ours.
RULE = [
    (r"^gent:prep:", "«List of prepositions which are followed by the genitive case: без, вдоль, вместо, для, до, из, из-за, из-под, кроме, мимо, около, от, после, против, с, у.» — DLI, Lesson 60."),
    (r"^datv:prep:", "«The preposition к (to, towards, in the direction of …) always requires the dative case … The preposition по means \"along\" and is used with the dative case.» — DLI, Lessons 28–29."),
    (r"^accs:prep:", "«Prepositions \"В\", \"НА\", \"ПОД\" and \"ЗА\" are followed by the Accusative case when they indicate the goal of motion.» — DLI, Lesson 61."),
    (r"^ablt:prep:", "«Prepositions \"ПОД\" and \"ЗА\" are followed by the Instrumental case when they indicate location … Prepositions \"НАД\", \"ПЕРЕД\", \"МЕЖДУ\" and \"С\".» — DLI, Lesson 61."),
    (r"^loct:prep:", "«The prepositional case is always used with a preposition. With the prepositions в and на it denotes a location … With the preposition о, об this case answers the questions о ком? о чём?» — DLI, Lesson 16."),
    (r"^loct:loc2$", "«Some masculine nouns take the ending -у (always with a stress) in the prepositional-locative case, i.e. after the prepositions В or НА. The same nouns have the regular ending -е after О, ОБ.» — DLI, Lesson 27."),
    (r"^loct:transport$", "«With the prepositions в and на it denotes a location.» — DLI, Lesson 16."),
    (r"^gent:poss$", "«The genitive case is used to denote the possessor or owner … A noun in the genitive case is sometimes used to qualify (modify) another noun.» — DLI, Lesson 23."),
    (r"^gent:neg$", "«The direct object of a verb with negation (with не) is often in the genitive case instead of the accusative.» «Conversely, to say 'There isn't...', 'There aren't...', we use the word нет followed by the genitive case.» — DLI, Lesson 27; Wikibooks, «Genitive case»."),
    (r"^gent:count$", "«If the number ends in 2, 3 or 4 use the genitive singular … If the number ends in 5, 6, 7, 8, 9, 0 or -надцать use the genitive plural.» «There are also other quantity words that take the genitive, either singular or plural according to meaning: Много, Несколько, Мало, Сколько.» — Wikibooks, «Genitive case»."),
    (r"^gent:verb$", "«The person or thing feared is in the Genitive case: Я боюсь этого человека.» «The object (of ждать) is in the accusative case if animate and in the genitive case if inanimate.» — DLI, Lessons 27, 66."),
    (r"^datv:io$", "«The dative case is used mostly to denote the person to whom something is given, sent, told, shown, etc.» — DLI, Lesson 28."),
    (r"^datv:impers$", "«The person who needs something (or someone) is in the dative case … The logical subject, when used with можно or нельзя, is in the dative case.» «This verb (нравиться) is used with the agent in the Dative case and the object (of the liking) in the Nominative case.» — DLI, Lessons 35, 36, 66."),
    (r"^datv:verb$", "«After the verb помогать the person to whom help or assistance is given is in the dative case.» — DLI, Lesson 35."),
    (r"^accs:obj$", "«The accusative case is used to denote the direct object of the preceding verb and answers the questions кого? — whom? or что? — what?» — DLI, Lesson 18."),
    (r"^ablt:tool$", "«The Instrumental without С is used when an instrument or agent of the action is denoted.» — DLI, Lesson 30."),
    (r"^ablt:pred$", "«After the verbs быть (past and future) and работать the noun indicating some person's occupation, rank or position is in the instrumental case.» — DLI, Lesson 30."),
    (r"^ablt:verb$", "«After the verbs командовать and заведовать the units or persons being commanded … are denoted by the instrumental case.» «This verb (заниматься) may be followed by the Instrumental case.» «The object following this verb (пользоваться) is in the Instrumental case.» — DLI, Lessons 30, 65, 99."),
    (r"^ablt:time$", "«The adverbs утром, вечером and днём … are nothing but the instrumental case of the nouns утро, вечер and день.» — DLI, Lesson 30."),
    (r"^nomn:subject$", "«The main functions of the nominative case are: a. The nominative of the subject: Студент читает.» — DLI, Lesson 16."),
    (r"^nomn:eto$", "«b. The nominative of the predicate: Мой брат — студент.» — DLI, Lesson 16."),
    (r":adj$", "«All adjectives agree in gender, number and case with the noun they modify.» — DLI, Lesson 46."),
    (r"^time:в:accs$", "«The preposition В + Acc. is used: (a) to indicate the time of the day … (b) to indicate the day of the week … (c) to indicate how frequently something occurs.» — DLI, Lesson 73."),
    (r"^time:в:loct$", "«The preposition В + Prepositional is used: (a) to indicate the year or the month (but never the week) … (b) to indicate the beginning, the middle, the end or any other phase of a period.» — DLI, Lesson 73."),
    (r"^time:на:accs$", "«The preposition НА + Acc. is used to indicate the length of time one expects to stay some place, or the time something is expected to last.» — DLI, Lesson 73."),
    (r"^time:на:loct$", "«The preposition НА + Prep. is used to indicate the week during which an event takes place.» — DLI, Lesson 73."),
    (r"^time:по:datv$", "«The preposition по + Dat. Pl. is used to indicate that something occurs periodically.» — DLI, Lesson 74."),
    (r"^time:с:gent$", "«С + Gen. meaning \"from\" or \"since\".» — DLI, Lesson 76."),
    (r"^time:до:gent$", "«ДО + Gen. meaning \"till\" (indicating a time limit of an action).» — DLI, Lesson 76."),
    (r"^time:за:accs$", "«The preposition ЗА + Acc. denotes the time that it takes to accomplish an action.» — DLI, Lesson 77."),
    (r"^time:к:datv$", "«The preposition К + Dat. denotes the time by which an event takes place.» — DLI, Lesson 77."),
    (r"^time:(перед|после):", "«\"Перед\" means immediately before, whereas \"до\" can cover a longer space of time before.» — DLI, Lesson 43."),
    (r"^time:every$", "«The word \"every\" in time expressions answering the question \"how often\" … каждый день, каждое утро, каждую среду (acc.)»; «весь день, всё утро, всю неделю (accus.)». — DLI, Lessons 22, 37."),
    (r"^time:season$", "«The adverbs утром, вечером and днём … are nothing but the instrumental case of the nouns утро, вечер and день.» — DLI, Lesson 30."),
    (r"^time:date$", "«In denoting the time of an event (in answering the question \"when?\") the date and the month are both in the Genitive case.» — DLI, Lesson 75."),
]


def rule_for(key):
    for rx, q in RULE:
        if re.search(rx, key):
            return q
    return None


def _src(why):
    m = re.search(r"(Sentence and translation from Tatoeba[^.]*\\.|From [^.]*«[^»]*»\\.?)\s*$", why or "")
    return m.group(1) if m else ""


def drills(*keys):
    """Exercises from several keys, interleaved so each set mixes them."""
    pools = [[dict(e, why=((rule_for(k) or "") + " " + _src(e.get("why"))).strip()) if rule_for(k) else e
              for e in (DRILLS.get(k) or [])] for k in keys]
    out, seen = [], set()
    while any(pools) and len(out) < MAX_PER_SECTION:
        for p in pools:
            if p:
                e = p.pop(0)
                k = e.get("q", "") + e.get("ru", "")
                if k not in seen:
                    seen.add(k); out.append(e)
    return out


def SECD(id, title, blocks, keys, sub=None, note=None):
    exs = drills(*keys)
    blocks = list(blocks) + ([NOTE(note)] if note else [])
    if exs:
        blocks.append(NOTE("Exercises: sentences from Tatoeba (tatoeba.org, CC BY 2.0 FR) and from the library's public-domain books."))
    s = SEC(id, title, blocks, exercises=exs[:IN_SECTION], sub=sub)
    s["more"] = exs[IN_SECTION:]
    return s


# ── Nominative ──
NOM = [
    SECD("n1-subject", "The subject", wiki("Nominative", "What is a case?") + wiki("Nominative", "Usage") + dli("k1-nom-prep", "Nominative case"),
         ["nomn:subject"], sub="who or what does it", note=WB + " " + DLI + " Lesson 16."),
    SECD("n2-eto", "Это…, вот…: naming things", wiki("Nominative", "Nouns"), ["nomn:eto"], sub="это книга · вот мой дом", note=WB),
    SECD("n3-adjectives", "Adjectives with the subject", wiki("Nominative", "Adjectives"), ["nomn:adj"], sub="новый, новая, новое, новые", note=WB),
    SECD("n4-pronouns", "Pronouns in the nominative", wiki("Nominative", "Personal Pronouns") + wiki("Nominative", "Possessive pronouns")
         + wiki("Nominative", "Demonstrative Pronouns"), [], sub="я, ты, мой, этот", note=WB),
]
# ── Genitive ──
GEN = [
    SECD("g1-possession", "Whose, and of what", wiki("Genitive_case", "") + dli("k3-genitive")[:3], ["gent:poss"],
         sub="книга студента · улицы города", note=WB + " " + DLI + " Lesson 23."),
    SECD("g2-no", "Нет, не было: having none", wiki("Genitive_case", "Usage/Possession and Negation") + dli("k3-genitive", "Genitive instead of accusative"),
         ["gent:neg"], sub="у меня нет брата · не было времени", note=WB + " " + DLI + " Lesson 27."),
    SECD("g3-counting", "Counting and how much", wiki("Genitive_case", "Usage/Counting"), ["gent:count"], sub="два дня · пять лет · много работы", note=WB),
    SECD("g4-from", "From: из, с, от", dli("k3-genitive", "Prepositions with the genitive"),
         ["gent:prep:из", "gent:prep:с", "gent:prep:от"], sub="из школы · с почты · от брата", note=DLI + " Lessons 24, 27."),
    SECD("g5-u-dlya-bez", "у, для, без", wiki("Genitive_case", "Usage/Prepositions"), ["gent:prep:у", "gent:prep:для", "gent:prep:без"],
         sub="у окна · для друга · без молока", note=WB),
    SECD("g6-more-prepositions", "до, после, около, мимо, кроме, вместо, против…", dli("k11-prepositions", "Prepositions followed by the genitive case"),
         ["gent:prep:до", "gent:prep:после", "gent:prep:около", "gent:prep:мимо", "gent:prep:кроме", "gent:prep:вместо", "gent:prep:против",
          "gent:prep:среди", "gent:prep:вокруг", "gent:prep:возле", "gent:prep:из-за", "gent:prep:из-под", "gent:prep:вдоль", "gent:prep:напротив"],
         sub="every other preposition that takes the genitive", note=DLI + " Lesson 60."),
    SECD("g7-verbs", "Verbs that take the genitive", [
        P("To be afraid, to fear — бояться. a) The person or thing feared is in the Genitive case: *Я боюсь этого человека.* "
          "b) The verb «бояться» denotes the state or condition of the agent."),
        P("The verb ждать takes no preposition. The object is in the accusative case if animate and in the genitive case if inanimate: "
          "*Я жду жену. Я жду письма.*")], ["gent:verb"], sub="бояться, ждать, достигать, требовать…", note=DLI + " Lessons 27, 66."),
    SECD("g8-endings", "Genitive endings: nouns, adjectives, pronouns", wiki("Genitive_case", "Nouns") + wiki("Genitive_case", "Adjectives")
         + wiki("Genitive_case", "Personal Pronouns"), ["gent:adj"], sub="-а, -ы, -ов, -ей · -ого, -ой, -ых", note=WB),
]
# ── Dative ──
DAT = [
    SECD("d1-to-whom", "To whom: giving, telling, showing", wiki("Dative_case", "Usage") [:4] + dli("k4-dative", "")[:3] + [
        P("After the verb давать-дать the object given is in the accusative case; the person to whom the object is given is in the dative case: "
          "*Он даст словарь сыну.* After посылать-послать the object sent is in the accusative case; the person to whom the object is sent "
          "is in the dative case: *Я пошлю книгу брату.* After говорить-сказать the person to whom something is said is in the dative case: "
          "*Я скажу ему, что вы уже здесь.*")], ["datv:io"], sub="дать брату · сказать учителю", note=WB + " " + DLI + " Lessons 28, 39."),
    SECD("d2-mne-nravitsya", "Мне нравится, нужно, надо, можно", [
        P("The logical subject, that is the person who has to do something, is in the dative case: *Надо идти в класс.* "
          "The logical subject, when used with можно or нельзя, is in the dative case: *Вам можно курить, а мне нельзя. "
          "Отцу нельзя пить вино, а брату можно.*"),
        P("The person who needs something (or someone) is in the dative case. The thing (or person) needed is in the nominative case, "
          "and the word нужен (-а, -о, -ы) agrees in gender and number with the thing (or person) needed: *Мне нужна книга. Нам нужны книги.*"),
        P("To like — нравиться. This verb is used with the agent in the Dative case and the object (of the liking) in the Nominative case: "
          "*Мне нравится эта книга.* — I like this book. (Lit.: This book appeals to me.)"),
        P("The person whose age is in question is in the dative case: *Сколько вам лет? — Мне двадцать лет.*")],
         ["datv:impers"], sub="мне холодно · детям нужно · сколько тебе лет", note=DLI + " Lessons 35, 36, 41, 66."),
    SECD("d3-verbs", "Verbs that take the dative", [
        P("After the verb помогать the person to whom help or assistance is given is in the dative case: *Я помогаю ему. Она помогает брату.*"),
        P("After the verb обещать the person to whom something is promised is in the dative case: *Капитан обещал старшине отпуск.*")]
         + wiki("Dative_case", "Usage")[1:3], ["datv:verb"], sub="помогать, верить, звонить, советовать…", note=DLI + " Lessons 35, 36. " + WB),
    SECD("d4-k", "к: towards, to someone's", dli("k4-dative", "Dative with к") + wiki("Dative_case", "Usage/Prepositions")[:1],
         ["datv:prep:к"], sub="к доске · к врачу · к вечеру", note=DLI + " Lesson 29. " + WB),
    SECD("d5-po", "по, благодаря, вопреки, согласно", dli("k4-dative", "Dative after по") + wiki("Dative_case", "Usage/Prepositions")[1:],
         ["datv:prep:по", "datv:prep:благодаря", "datv:prep:вопреки", "datv:prep:согласно", "datv:prep:навстречу"],
         sub="по улице · по телефону · благодаря вам", note=DLI + " Lesson 28. " + WB),
    SECD("d6-endings", "Dative endings: nouns, adjectives, pronouns", wiki("Dative_case", "Nouns") + wiki("Dative_case", "Adjectives")
         + wiki("Dative_case", "Pronouns"), ["datv:adj"], sub="-у, -е, -ам · -ому, -ой, -ым", note=WB),
]
# ── Accusative ──
ACC = [
    SECD("a1-object", "The direct object", wiki("Accusative_case", "") + wiki("Accusative_case", "Usage")[:5] + dli("k2-accusative", "Endings"),
         ["accs:obj"], sub="читать книгу · видеть сестру", note=WB + " " + DLI + " Lesson 18."),
    SECD("a2-v-na", "Where to: в and на", wiki("Accusative_case", "Prepositions/Direction of motion, в, на, за, & под"),
         ["accs:prep:в", "accs:prep:на"], sub="в школу · на работу", note=WB),
    SECD("a3-za-pod", "за and под: going behind, under", dli("k11-prepositions", "Prepositions used with the accusative case"),
         ["accs:prep:за", "accs:prep:под"], sub="за дверь · под газету · за книгу (for)", note=DLI + " Lesson 61."),
    SECD("a4-cherez-pro", "через, про, сквозь", wiki("Accusative_case", "Prepositions/The remaining six: по, с, про, о, сквозь, через"),
         ["accs:prep:через", "accs:prep:про", "accs:prep:сквозь"], sub="через реку · про него", note=WB),
    SECD("a5-time", "Time in the accusative", [
        P("The word \"every\" in time expressions answering the question \"how often\" is rendered as follows: каждый день (понедельник, "
          "вторник, четверг) — masc. (acc.); каждое утро (воскресенье) — neut. (acc.); каждую среду (пятницу, субботу) — fem. (acc.)"),
        P("The word \"all\" in time expressions answering the question \"how long\" is rendered as follows: весь день (год, месяц, вторник) — "
          "masc. (accus.); всё утро (воскресенье, лето) — neut.; все дни (годы) — plur.; всю неделю (зиму, осень, ночь) — fem."),
        P("The preposition в + acc. is used to indicate the time of the day (*Собрание начинается в три часа.*), the day of the week "
          "(*Я был там в пятницу.*), and how frequently something occurs (*Я хожу в штаб два раза в день.*). The preposition на + acc. is "
          "used to indicate the length of time one expects to stay some place: *Он приехал сюда на два дня.*")],
         ["time:every", "time:в:accs", "time:на:accs", "time:через:accs", "time:за:accs", "time:назад"],
         sub="каждый день · всю неделю · в пятницу · на два дня", note=DLI + " Lessons 22, 37, 73."),
    SECD("a6-endings", "Accusative endings: nouns, adjectives, pronouns", wiki("Accusative_case", "Nouns") + wiki("Accusative_case", "Adjectives")
         + wiki("Accusative_case", "Personal Pronouns"), ["accs:adj"], sub="-у, -ю, = nom., = gen. · -ую, -ого", note=WB),
]
# ── Instrumental ──
INS = [
    SECD("i1-with", "With: с + instrumental", wiki("Instrumental_case", "")[:1] + wiki("Instrumental_case", "Usage")[:3] + dli("k5-instrumental", "")[:2],
         ["ablt:prep:с"], sub="с другом · чай с молоком", note=WB + " " + DLI + " Lesson 30."),
    SECD("i2-means", "By means of: the instrument", dli("k5-instrumental", "")[2:3], ["ablt:tool"], sub="писать карандашом · ехать поездом",
         note=DLI + " Lesson 30."),
    SECD("i3-being", "Being, becoming, working as", dli("k5-instrumental", "Instrumental after быть and работать"), ["ablt:pred"],
         sub="был офицером · стал врачом · работает переводчиком", note=DLI + " Lesson 30."),
    SECD("i4-where", "Where: над, под, за, перед, между", wiki("Instrumental_case", "Usage")[3:], ["ablt:prep:над", "ablt:prep:под", "ablt:prep:за",
         "ablt:prep:перед", "ablt:prep:между"], sub="над городом · под деревом · за рекой", note=WB),
    SECD("i5-verbs", "Verbs that take the instrumental", dli("k5-instrumental", "командовать, заведовать, разговаривать") + [
        P("To occupy (busy) oneself with, to be engaged in, to study — заниматься. This verb may be followed by the Instrumental case: "
          "*Он занимается политикой. Я занимаюсь спортом. Чем вы занимаетесь?*"),
        P("To make use of; to enjoy (the rights, privileges, confidence, etc.) — пользоваться. The object following this verb is in the "
          "Instrumental case: *Они пользуются всеми правами. Я часто пользуюсь его словарём.*"),
        P("The expression \"to laugh at…\" is rendered in Russian by «смеяться над» + Instr.: *Он смеётся над вами.*")],
         ["ablt:verb"], sub="заниматься, пользоваться, интересоваться…", note=DLI + " Lessons 30, 65, 66, 99."),
    SECD("i6-time", "When: утром, зимой, этим летом", [P("These endings are easily remembered when associated with the adverbs утром, вечером and "
         "днём, which are nothing but the instrumental case of the nouns утро, вечер and день.")], ["ablt:time", "time:season"],
         sub="утром · весной · прошлой зимой", note=DLI + " Lesson 30."),
    SECD("i7-endings", "Instrumental endings: nouns, adjectives, pronouns", wiki("Instrumental_case", "Nouns") + wiki("Instrumental_case", "Adjectives")
         + wiki("Instrumental_case", "Pronouns"), ["ablt:adj"], sub="-ом, -ой, -ью, -ами · -ым, -ой, -ыми", note=WB),
]
# ── Prepositional ──
PRP = [
    SECD("p1-where", "Where: в and на", wiki("Prepositional_case", "") + wiki("Prepositional_case", "Usage/At a place") + dli("k1-nom-prep", "Prepositional (locative) case"),
         ["loct:prep:в", "loct:prep:на"], sub="в школе · на работе", note=WB + " " + DLI + " Lesson 16."),
    SECD("p2-about", "About: о, об, обо", wiki("Prepositional_case", "Usage/Prepositions"), ["loct:prep:о"], sub="о погоде · об отце · обо мне", note=WB),
    SECD("p3-v-lesu", "в лесу, на берегу: the stressed -у", dli("k1-nom-prep", "Prepositional-locative in -у"), ["loct:loc2"],
         sub="в саду · в году · на мосту", note=DLI + " Lesson 27."),
    SECD("p4-pri-transport", "при, на поезде, в этом году", [
        P("The preposition в + prepositional is used to indicate the year or the month (but never the week) in which an event takes place: "
          "*Я был там в этом месяце. Я был там в январе. Я поеду туда в будущем году.* It is also used to indicate the beginning, the middle, "
          "the end or any other phase of a period: *Он был здесь в начале года. Он был здесь в конце месяца.* The preposition на + prep. is "
          "used to indicate the week during which an event takes place: *Я поеду туда на этой неделе.*")],
         ["loct:prep:при", "loct:transport", "time:в:loct", "time:на:loct"], sub="при входе · на машине · в прошлом году", note=DLI + " Lesson 73."),
    SECD("p5-endings", "Prepositional endings: nouns, adjectives, pronouns", wiki("Prepositional_case", "Nouns") + wiki("Prepositional_case", "Adjectives")
         + wiki("Prepositional_case", "Pronouns"), ["loct:adj"], sub="-е, -и, -ах · -ом, -ой, -ых", note=WB),
]

CREDIT = "Explanations: the Wikibooks Russian textbook (CC BY-SA 4.0) and the DLI Basic Course (public domain); sentences: Tatoeba (CC BY 2.0 FR) and the library's public-domain books"
WB_URL = "https://en.wikibooks.org/wiki/Russian"


def _c(id, title, short, mark, blurb, secs):
    return ({"id": id, "title": title, "short": short, "mark": mark, "blurb": blurb, "credit": CREDIT, "creditUrl": WB_URL,
             "license": "CC BY-SA 4.0 · CC BY 2.0 FR · public domain", "licenseUrl": "https://creativecommons.org/licenses/by-sa/4.0/"}, secs)


COURSE_DEFS = [
    _c("case-nom", "The Nominative Case", "Nominative", "И", "The subject, это…, and the dictionary form — with real sentences to practise.", NOM),
    _c("case-gen", "The Genitive Case", "Genitive", "Р", "Whose, of what, none, how many, and the twenty prepositions and the verbs that take the genitive — "
       "practised on real sentences.", GEN),
    _c("case-dat", "The Dative Case", "Dative", "Д", "To whom, мне нравится and мне нужно, к and по, and the verbs that take the dative — "
       "practised on real sentences.", DAT),
    _c("case-acc", "The Accusative Case", "Accusative", "В", "The direct object, where to (в, на, за, под), через and про, and time — "
       "practised on real sentences.", ACC),
    _c("case-ins", "The Instrumental Case", "Instrumental", "Т", "With, by means of, being and becoming, над, под, за, перед, между, and the verbs "
       "that take it — practised on real sentences.", INS),
    _c("case-prp", "The Prepositional Case", "Prepositional", "П", "Where (в, на), about (о), в лесу and на берегу, при, and time — "
       "practised on real sentences.", PRP),
]

# ── More time expressions, for the Time course ──
TIME_MORE = [
    SECD("t8-this-next-last", "This week, next month, last year", [
        P("The preposition В + Prepositional is used: (a) to indicate the year or the month (but never the week) in which an event takes place. "
          "*В каком месяце (когда) вы были там? Я был там в этом месяце. Я был там в прошлом месяце. Я был там в январе. В каком году "
          "(когда?) вы поедете туда? Я поеду туда в этом году. Я поеду туда в будущем году.*"),
        P("The preposition НА + Prep. is used to indicate the week during which an event takes place. *Я поеду туда на этой неделе. Я поеду "
          "туда на будущей неделе. Я был там на прошлой неделе.* (Compare with: \"в прошлом месяце\", \"в прошлом году\".) Note also the "
          "expression \"на (этих) днях\". When referred to the past \"на днях\" means \"a few days ago\", \"the other day\": *Я был там на "
          "днях.* When referred to the future, it means \"within a few days\": *Я буду там на днях.*")],
         ["time:на:loct", "time:в:loct", "time:season"], sub="на этой неделе · в прошлом году · этим летом", note=DLI + " Lesson 73."),
    SECD("t9-every-all-on", "Every day, all week, on Saturdays", [
        P("каждый день (понедельник, вторник, четверг) — masc. (acc.); каждое утро (воскресенье) — neut. (acc.); каждую среду "
          "(пятницу, субботу) — fem. (acc.). весь день (год, месяц) — masc. (accus.); всё утро (лето) — neut.; все дни (годы) — plur.; "
          "всю неделю (зиму, осень, ночь) — fem."),
        P("The preposition по + dat. pl. is used to indicate that something occurs periodically: 1. on a certain day of the week: "
          "*По понедельникам я работаю в штабе. По воскресеньям мы отдыхаем.* 2. during a certain time of a day: *По утрам я читаю газету. "
          "По вечерам его никогда нет дома.* Note: never «по дням» except when a modifier is used: по целым дням — days on end; "
          "по выходным дням — on off-days.")],
         ["time:every", "time:по:datv", "time:в:accs"], sub="каждый день · всю ночь · по субботам · в пятницу", note=DLI + " Lessons 22, 37, 74."),
    SECD("t10-in-ago-for", "In an hour, a week ago, for two days", [
        P("The preposition на + acc. is used to indicate the length of time one expects to stay some place, or the time something is "
          "expected to last: *Он приехал сюда на два дня. Я получил отпуск на неделю.* Note also: на следующий день — next day."),
        P("The preposition за + acc. denotes the time that it takes to accomplish an action: *Он сделает это за неделю. Я прочитал эту книгу "
          "за два дня.* «за + acc.» is also used in combination with «до + gen.» to denote the time of one event taking place before some "
          "other event: *Он умер за год до войны.*")],
         ["time:через:accs", "time:назад", "time:на:accs", "time:за:accs", "time:в течение:gent"],
         sub="через час · неделю назад · на два дня · за неделю · в течение года", note=DLI + " Lessons 73, 77."),
    SECD("t11-since-till-by", "Since, till, by, before, after", [
        P("С + gen. meaning \"from\" or \"since\": *Он живёт здесь с прошлого года. Сегодня с утра идёт дождь.* До + gen. meaning \"till\" "
          "(indicating a time limit of an action): *Дождь шёл до вечера. Мы работали до пяти часов.*"),
        P("The preposition к + dat. denotes the time by which an event takes place: *Он вернётся к двум часам. Приготовьте доклад к понедельнику.* "
          "\"Перед\" means immediately before, whereas \"до\" can cover a longer space of time before: *Он придёт до обеда. Он придёт перед обедом.*")],
         ["time:с:gent", "time:до:gent", "time:к:datv", "time:после:gent", "time:перед:ablt", "time:около:gent"],
         sub="с утра · до вечера · к понедельнику · после обеда · перед уроком", note=DLI + " Lessons 43, 76, 77."),
    SECD("t12-dates-years", "Dates and years in real sentences", [
        P("Note that in denoting the time of an event (in answering the question \"when?\") the date and the month are both in the Genitive case: "
          "*Это случилось пятого января.* The preposition в + prepositional indicates the year: *Я был там в 1958 году.*")],
         ["time:date"], sub="первого мая · в 1990 году", note=DLI + " Lessons 73, 75."),
    SECD("t13-time-words", "Yesterday, soon, always: words of time", wiki("Adverbs", "Adverbs of Time"), ["time:adv"],
         sub="вчера · скоро · всегда · иногда · давно", note=WB),
]
