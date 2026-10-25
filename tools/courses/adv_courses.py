"""Advanced grammar courses: aspect; conjugation, position verbs and -ся;
comparison and short adjectives; pronouns (-то/-нибудь, некого, себя, свой,
который, каков); complex sentences (чтобы, до того как, пока, ли).
Explanations: the DLI Grammar Reference Book (public domain), word for word;
каков from Wiktionary (CC BY-SA), when tools/fetch_wiktionary.py has fetched
it. Exercises: real sentences only (tools/courses/adv_drills.py)."""
import io, json, os, re
from kit import *
import case_courses as cc

HERE = os.path.dirname(os.path.abspath(__file__))
_A = os.path.join(HERE, "adv_drills.json")
if os.path.exists(_A):
    cc.DRILLS.update(json.load(io.open(_A, encoding="utf-8")))
SECD = cc.SECD
DLI = "From the DLI Grammar Reference Book"


def wiktionary(word):
    """Definitions and examples of a word from the copy tools/fetch_wiktionary.py saved."""
    p = os.path.join(os.path.dirname(os.path.dirname(HERE)), "private", "wiktionary", word + ".txt")
    if not os.path.exists(p):
        return []
    out, ex = [], []
    for line in io.open(p, encoding="utf-8"):
        line = line.rstrip()
        m = re.match(r"^#\s+(.*)", line)
        if m:
            t = re.sub(r"\{\{[^{}]*\}\}", "", m.group(1)); t = re.sub(r"\[\[(?:[^|\]]*\|)?([^\]]+)\]\]", r"\1", t).replace("''", "")
            if t.strip():
                out.append(t.strip())
        m = re.match(r"^#:\s*\{\{(?:uxi?|quote[^|]*)\|ru\|([^|}]+)(?:\|([^}]+))?\}\}", line)
        if m:
            ex.append((re.sub(r"\[\[(?:[^|\]]*\|)?([^\]]+)\]\]", r"\1", m.group(1)), (m.group(2) or "").replace("t=", "")))
    bl = []
    if out:
        bl.append(L(*out))
    if ex:
        bl.append(EX(*ex[:8]))
    if bl:
        bl.append(NOTE("From Wiktionary, «%s» (en.wiktionary.org, CC BY-SA 4.0)." % word))
    return bl


ASPECT = [
    SECD("a1-process-result", "Two aspects: the process and the result", [
        P("In Russian almost every action is expressed by a pair of verbs. Such twin-verbs differ only in what we call aspect, "
          "and otherwise have the same basic meaning. The imperfective aspect emphasizes the action itself. The perfective aspect "
          "places the emphasis on the result of the action."),
        P("The verb писать is called imperfective and has the following two meanings: 1. to be writing, to be in the process of "
          "writing for a certain period of time (in the present, past or future): *Я сейчас пишу. Вчера я весь вечер писал. Завтра я "
          "всё утро буду писать.* 2. to write habitually (often, always, etc.): *Я каждый день пишу.*"),
        P("The verb написать is called perfective and expresses a single action with emphasis on its completion (either in the past or "
          "in the future, since the present tense deals only with actions in progress)."),
        T(["The general idea of an imperfective verb is:", "of a perfective verb is:"], [
            ["1. to do (to be doing) something for a period of time: *Я долго писал письмо.*", "1. to complete the action and thus to achieve a result: *Я написал письмо; вот оно на столе.*"],
            ["2. to do something habitually: *Я всегда пишу письма по-русски.*", "2. to do something once: *Ему я написал по-английски.*"]], row_heads=False),
        P("Both the imperfective and perfective forms of a Russian verb are to be memorized as a pair because there are no definite rules "
          "of forming one aspect from the other one: some twin-verbs differ only by a prefix in the perfective aspect; some have other "
          "changes: читать — прочитать, получать — получить. Sometimes, even two quite different verbs make an imperfective-perfective "
          "pair: говорить — сказать.")],
         ["asp:past"], sub="писал или написал? — the past tense", note=DLI + ", Lesson 37."),
    SECD("a2-context", "Words that call for the imperfective", [
        P("Often the use of the proper aspect is clearly indicated by the context. For instance, the following words and phrases require "
          "the use of an imperfective verb: I. indicating duration of an action: долго, недолго, всё утро, весь день, etc. II. indicating "
          "habitual action: обычно, всегда, иногда, часто, редко, каждый день, каждую неделю, etc."),
        T(["English", "Russian"], [["1. Present: I write letters.", "Present, imperfective: Я пишу письма."],
                                   ["2. Present perfect progressive: I have been writing all morning.", "Present, imperfective: Я пишу уже всё утро. (\"уже\" usually added)"],
                                   ["3. Any progressive tense: I am writing a letter. I was writing a letter. I will be writing a letter.", "Imperfective aspect: Я пишу письмо. Я писал письмо. Я буду писать письмо."]], row_heads=False)],
         ["asp:inf"], sub="делать или сделать? — the infinitive", note=DLI + ", Lesson 37."),
    SECD("a3-commands", "Aspect in commands", [
        P("The imperative may be formed from both the imperfective and the perfective verbs."),
        P("The negative imperative is, as a rule, in the imperfective aspect: *Берите! Возьмите! — Не берите!* The negative imperative "
          "in the perfective aspect is relatively rare and has the meaning of a strict warning against acts which might lead to "
          "detrimental results: *Смотрите, не забудьте, что сегодня у нас важное собрание. Здесь скользко, не упадите!*")],
         ["asp:imp", "asp:neg"], sub="возьмите — не берите · не забудьте!", note=DLI + ", Lessons 42, 84."),
    SECD("a4-future", "The perfective future", [
        P("The imperfective verb has 3 tenses: the present, the past, and the future. The perfective verb has 2 tenses: the past and the "
          "future. The perfective future consists of one word only and resembles in form the present tense. It is formed from the "
          "perfective infinitive: напишу, напишешь … напишут; сделаю; получу; выучу."),
        T(["", "infinitive", "present", "past", "future"], [["imperf.", "писать", "пишу, -ешь", "писал", "буду писать"], ["perf.", "написать", "—", "написал", "напишу, -ешь"]]),
        P("In a sentence referring to the future with a subordinate clause introduced by \"when\" or \"as soon as\" the verbs of both "
          "clauses are in the future: *Я буду читать письма, когда ты будешь учить диалог.* An action of the subordinate clause which is "
          "to be completed before the action of the main clause is rendered by the perfective future: *Когда я сделаю уроки, я буду "
          "слушать радио. Как только я получу от него письмо, я напишу вам.*")],
         ["conj:fut"], sub="напишу, сделаю · когда я сделаю уроки…", note=DLI + ", Lesson 37."),
    SECD("a5-po-s", "по- and с- with ходить, ездить, летать", [
        P("Adding a prefix to the repeated function verbs: ходить, ездить, летать usually does not form the perfective aspect but merely "
          "changes the meaning of the original verb. However, prefixes \"по-\" and \"с-\" may form the perfective aspect with the "
          "\"repeated function\" verbs."),
        P("a) Prefix \"по-\" denoting a perfective action of limited duration (an action \"for a while\"): походить, поездить, полетать. "
          "*Он походил по комнате и сел за стол. Мы поездили по городу и поехали домой.* b) Prefix \"с-\" implying a single round trip: "
          "сходить, съездить, слетать. These verbs denote a single trip (going to and coming from a place), especially when a quick "
          "return is implied. *Мне надо сходить на почту за письмами. Я съезжу на вокзал и узнаю, когда отходит поезд.*")],
         [], sub="походить · сходить · съездить", note=DLI + ", Lesson 63."),
]

VERBS = [
    SECD("v1-present", "The present tense: the Е and И types", [
        P("The following verbs belong to the \"Е\" type of conjugation: думать — я думаю, ты думаешь … они думают; слушать; спрашивать. "
          "The verb лежать belongs to the \"И\" type of conjugation: я лежу, ты лежишь … они лежат."),
        P("The verbs писать and жить belong to the first \"Е\" type of conjugation, but do not follow exactly the pattern: я пишу, ты "
          "пишешь … они пишут; я живу, ты живёшь … они живут. The letter с in the infinitive form писать is replaced by the letter ш in "
          "all forms of the present tense. The letter в is inserted in all present tense forms of the verb жить."),
        P("The verbs сидеть and видеть belong to the 2nd \"И\" type of conjugation. Notice that the consonant д changes into ж in the first "
          "person singular: я сижу, ты сидишь; я вижу, ты видишь.")],
         ["conj:pres"], sub="думаю, думаешь · лежу, лежишь", note=DLI + ", Lessons 16–18."),
    SECD("v2-past", "The past tense", [
        P("The past tense is formed by dropping -ть from the infinitive and adding -л for the masculine, -ла for the feminine, -ло for the "
          "neuter, -ли for the plural: работал, работала, работало, работали. Thus, the past does not have special endings for each "
          "person, but shows the gender and the number."),
        P("Some verbs change the stress in the past tense: жил, жила, жило, жили; спал, спала; ждал, ждала; пил, пила — like: был, была, "
          "было, были. Verbs which have in the infinitive a consonant before -ть (-ти) or end with -чь have the past tense as follows: "
          "есть — ел, ела; идти — шёл, шла, шло, шли; мочь — мог, могла, могло, могли.")],
         ["conj:past"], sub="работал, работала, работали", note=DLI + ", Lessons 36, 42."),
    SECD("v3-position", "Standing, lying, sitting — and putting", [
        P("ставить — поставить: to put, to place in a vertical position or on the base of the object; to park (a car). Phrases meaning "
          "direction are used to denote the place where something is put (\"на\" + Acc., \"в\" + Acc., etc.): *Я поставил лампу на стол. "
          "Я поставил автомобиль в гараж.* However, when something is put in a wide or open space, phrases meaning location are mostly "
          "used: *Я поставил автомобиль на площади.*"),
        P("класть — положить: to put, to place, to lay in a horizontal position: *Я кладу книги в ящик. Я кладу книги на стол.*"),
        P("садиться — сесть: to sit down. Literally садиться means \"to seat oneself\". It implies movement to a \"seat\" and, therefore, "
          "answers the question \"куда?\": *Садитесь на стул. Садитесь в кресло.* The same is applicable to the verbs ложиться — лечь "
          "(to lie down) and становиться — стать (to take a standing position)."),
        P("The verbs \"сидеть\", \"лежать\" and \"стоять\" form their perfective aspect by adding prefix \"по-\": посидеть, полежать, "
          "постоять. These perfective verbs denote a completed action of limited duration: *Я хочу посидеть здесь 5 минут.*")],
         ["pos"], sub="стоит · поставил · встал · лежит · положил · лёг", note=DLI + ", Lessons 42, 68."),
    SECD("v4-sya", "Verbs in -ся", [
        P("The suffix \"-ся\" with some verbs indicates action of two or more actors upon one another (reciprocal action). Thus: "
          "встречаться (to meet), знакомиться (to become acquainted), здороваться (to greet each other) etc. The second actor (if mentioned) "
          "is always in the Instrumental case with the preposition \"с\": *Я не хочу встречаться с этим человеком.* Note that without "
          "\"-ся\" the verb встречать — встретить is used with the direct object in the Accusative case: *Вчера я встретил моего друга.* "
          "but: *Мы встретились на улице.*"),
        P("We already know that the verbs in \"-ся\" may be divided into several groups. Group 1. Reflexive verbs. These verbs express an "
          "action which is directed back upon the agent or subject: *Я моюсь. Мы готовимся к экзамену.* Group 2: *Наступление начинается. "
          "Урок продолжается 50 минут.* Group 3. Reciprocal verbs: *Мы часто встречаемся. Он хочет с вами познакомиться.* Group 4. Verbs "
          "which never occur without the ending \"-ся\": *Я боюсь вашего брата. Он смеётся над вами.*")],
         ["sya"], sub="встретил — встретились · моет — моется", note=DLI + ", Lessons 66–67."),
]

COMPARE = [
    SECD("c1-comparative", "The comparative: новее, интереснее", [
        P("In both English and Russian adjectives and adverbs have three forms, which are called degrees: positive, comparative, "
          "superlative — good, better, best; fast, faster, fastest."),
        P("The comparative degree of Russian adjectives is formed by adding \"-ее\" (sometimes shortened to \"-ей\") to the stem of the "
          "adjective: новый — новее; красивый — красивее. This comparative form is the same for all genders and the plural. It is not "
          "declined and can be used as a predicate only."),
        P("Note the stress. If the word consists of two syllables, the stress is on the comparative ending \"-ее\": новый — новее; старый — "
          "старее. Other adjectives as a rule have the same stress in both the basic and the comparative forms: свободный — свободнее; "
          "интересный — интереснее. There are some exceptions: здоровый — здоровее, тяжёлый — тяжелее, холодный — холоднее, весёлый — "
          "веселее, горячий — горячее."),
        P("Many adverbs which end in \"о\" are formed from adjectives … The comparative degree of these adverbs is formed in the same way as "
          "the comparative of adjectives: *Он идёт быстро. Я иду быстрее. Там было холодно. Здесь ещё холоднее.*")],
         ["comp"], sub="новее · интереснее · холоднее", note=DLI + ", Lessons 80, 82."),
    SECD("c2-irregular", "Irregular comparatives: лучше, больше, старше", [
        T(["", "", ""], [["high", "высокий", "выше"], ["low", "низкий", "ниже"], ["wide", "широкий", "шире"], ["narrow", "узкий", "уже"],
                         ["short", "короткий", "короче"], ["light; easy", "лёгкий", "легче"], ["deep", "глубокий", "глубже"], ["shallow", "мелкий", "мельче"],
                         ["dear, expensive", "дорогой", "дороже"], ["cheap", "дешёвый", "дешевле"]], row_heads=False),
        P("хороший — лучше — лучший; плохой — хуже — худший; большой — больше — больший; маленький — меньше — меньший. The forms \"лучший\" "
          "and \"худший\" are used as modifiers and are declined like regular adjectives."),
        P("\"старее\" and \"более старый\" are comparative forms from \"старый\". They mean \"older\" mainly as the opposite of \"newer\". "
          "\"старше\" and \"старший\", however, mean \"older\" in age or \"senior\" in rank: *Мой брат старше меня на два года.* The forms "
          "\"моложе\" and \"более молодой\" mean \"younger\" in age, while \"младше\" and \"младший\" may mean either younger in age or junior in rank."),
        T(["", ""], [["рано", "раньше"], ["поздно", "позже"], ["редко", "реже"], ["часто", "чаще"], ["близко", "ближе"], ["далеко", "дальше"],
                     ["много", "больше"], ["мало", "меньше"], ["хорошо", "лучше"], ["плохо", "хуже"], ["легко", "легче"], ["громко", "громче"],
                     ["долго", "дольше"], ["высоко", "выше"], ["низко", "ниже"], ["жарко", "жарче"], ["дорого", "дороже"]], row_heads=False)],
         ["comp:irr"], sub="выше · лучше · раньше · дороже", note=DLI + ", Lessons 80–82."),
    SECD("c3-than", "Than: чем, or the genitive", [
        P("An adjective in the comparative degree may be followed by the object of comparison in the Genitive case, or by a phrase "
          "consisting of \"чем\" plus the object of comparison in the Nominative case: *Ваш автомобиль новее моего автомобиля. Ваш "
          "автомобиль новее, чем мой автомобиль.*"),
        P("Note the use of the preposition \"на + Acc.\" in such expressions as: старше на два года — 2 years older; длиннее на пять метров — "
          "5 meters longer.")],
         ["comp:obj"], sub="новее моего · старше меня на два года", note=DLI + ", Lessons 80–81."),
    SECD("c4-bolee", "более and менее", [
        P("The comparative degree may also be formed by using \"более\" (more) or \"менее\" (less) with the basic form of an adjective: более "
          "трудный — more difficult; менее трудный — less difficult. This construction is commonly used when the object of comparison is "
          "not mentioned. It can be used either (1) as a predicate: *Этот мотор более сильный.* or (2) as a modifier: *Мне нужен более "
          "сильный мотор.* In the latter case the adjective after \"более\" or \"менее\" must agree in case, gender and number with the noun "
          "modified: *У нас нет более сильного мотора. Вот машина с более сильным мотором.*")],
         ["comp:bolee"], sub="более сильный мотор · с более сильным мотором", note=DLI + ", Lesson 80."),
    SECD("c5-samyi", "The superlative: самый", [
        P("To get the superlative degree in Russian place the word \"самый\" (-ая, -ое, -ые) before the adjective: *Это самый тяжёлый танк. "
          "Это самая красивая девушка. Это самое трудное задание.* \"Самый\" is declined like regular adjective: *Это самый новый "
          "автомобиль. Мы ехали на самом новом автомобиле.*"),
        P("The English preposition \"of\" after the superlative degree is rendered in Russian by the preposition \"из\" + Gen.: *Здесь три "
          "аэродрома. Самый большой из них за городом.* The three Russian equivalents of \"the best\": самый хороший, самый лучший, лучший "
          "are interchangeable.")],
         ["sup:samyi"], sub="самый новый · на самом новом", note=DLI + ", Lesson 83."),
    SECD("c6-eishiy", "-ейший, and лучше всех", [
        P("The superlative degree of qualitatives can be formed by changing the ending of an adjective to \"-ейший\" (or \"-айший\" after "
          "sibilants): *Это очень трудный урок. Это труднейший урок.* *Где самый близкий аэродром? Где ближайший аэродром?* This form, "
          "however, is less frequently used than the form with \"самый\". It is used less in comparison than in showing the possession of "
          "a quality in a very high degree: *Это интереснейшая книга.* — It's a most interesting book."),
        P("To form the superlative degree of adverbs place the words \"всех\" or \"всего\" after the comparative form: *Он знает это лучше "
          "всех* (better than anyone else); *Он знает это лучше всего* (better than anything else).")],
         ["sup:eish"], sub="интереснейший · ближайший · лучше всех", note=DLI + ", Lesson 83."),
    SECD("c7-short", "Short adjectives: занят, готов, рад", [
        P("Many Russian adjectives have two forms, the long form and the short form: здоровый — здоров; молодой — молод; свободный — "
          "свободен. By far the most common is the long form which can be used either as a modifier or as a predicate: *Это новый "
          "автомобиль. Этот автомобиль новый.* There is, however, a limited number of adjectives that normally take the short form when "
          "used predicatively: *Это больной человек.* but *Этот человек болен.* The past and future are formed by the use of the verb "
          "\"быть\": *Вчера я был занят. Завтра я буду свободен.* The short form of an adjective can never be used as a modifier."),
        T(["Long form", "", "Short form"], [["готовый", "ready", "готов, готова, готово, готовы"], ["свободный", "free", "свободен, свободна, свободно, свободны"],
                                            ["занятой", "busy", "занят, занята, занято, заняты"], ["здоровый", "healthy", "здоров, здорова, здорово, здоровы"],
                                            ["больной", "sick, ill", "болен, больна, больно, больны"], ["голодный", "hungry", "голоден, голодна, голодно, голодны"],
                                            ["сытый", "full", "сыт, сыта, сыто, сыты"], ["знакомый", "acquainted", "знаком, знакома, знакомо, знакомы"],
                                            ["живой", "alive", "жив, жива, живо, живы"], ["", "satisfied", "доволен, довольна, довольно, довольны"],
                                            ["", "in agreement with", "согласен, согласна, согласно, согласны"], ["", "glad", "рад, рада, рады"]], row_heads=False)],
         ["short"], sub="я занят · она готова · мы рады", note=DLI + ", Lesson 57."),
]

PRONOUNS = [
    SECD("p1-to-nibud", "-то and -нибудь", [
        P("The particles \"-нибудь\" and \"-то\" are used with certain pronouns and adverbs. These particles give an element of "
          "indefiniteness to the meaning of the pronouns and adverbs with which they are used: кто-нибудь — anybody, somebody; кто-то — "
          "someone, somebody; что-нибудь — anything, something; что-то — something."),
        P("Кто-нибудь and что-нибудь are used mainly in interrogative and imperative sentences: *Здесь был кто-нибудь? Дайте мне что-нибудь "
          "выпить!* Кто-то and что-то are used in statements of an evident fact (in the present or in the past): *Кто-то идёт сюда. Я что-то "
          "знаю о вас.* Only the first part (кто and что) is declined; -нибудь and -то remain unchanged: *Вы видели кого-нибудь? Он "
          "разговаривал с кем-то по телефону.*"),
        P("In general, the particle \"-нибудь\" implies complete indefiniteness; the particle \"-то\" implies some degree of certainty, that "
          "something was said or done, or exists, though the speaker does not say exactly what. General hints: a) In interrogative and "
          "imperative sentences use -нибудь. b) In positive statements referring to the past or present use -то. c) In statements referring "
          "to the future either \"-нибудь\" or \"-то\" may be used, depending on the degree of certainty: *Завтра я расскажу вам что-то "
          "интересное* (I already know what). *Завтра я расскажу вам что-нибудь интересное* (but I still don't know what)."),
        P("In addition to \"кто\" and \"что\" the particles -нибудь and -то are also used with какой, чей, куда, где, когда, откуда, как, "
          "почему: *Есть на столе какие-нибудь журналы? — Да, на столе лежит какой-то журнал. Вы едете куда-нибудь сегодня вечером? Они "
          "куда-то ушли. Вы были где-нибудь вчера? Я где-то его видел. Он ездил когда-нибудь в Нью-Йорк? — Да, он когда-то был там.*")],
         ["indef"], sub="кто-то · кто-нибудь · когда-то · когда-нибудь", note=DLI + ", Lesson 59."),
    SECD("p2-nekogo", "некого, нечего — and никого, ничего", [
        P("*Некому было помогать ему.* — There was no one who could help him. Note that the order of the words shows the intended meaning."),
        P("НЕЧЕГО is sometimes used colloquially as an equivalent to НЕ НАДО, НЕ НУЖНО, НЕ СТОИТ (no need to, one should not, is no use, not "
          "worth): *Нечего о нём беспокоиться, он скоро придёт. Нечего спать, надо вставать! Нечего было с ним разговаривать!* Memorize also: "
          "*Делать нечего, надо начинать работать. От нечего делать мы сели играть в карты.*")],
         ["negpron"], sub="мне некому писать · я никому не пишу", note=DLI + ", Lesson 104."),
    SECD("p3-negde", "негде, некуда, некогда — and нигде, никуда, никогда", [
        P("Negative adverbs НЕГДЕ, НЕКУДА, НЕОТКУДА, НЕКОГДА are formed by the same principle as negative pronouns НЕКОГО, НЕЧЕГО. They are "
          "used in impersonal constructions with the infinitive of the verb and the logical subject, if any, in the Dative case: *Ему негде "
          "спрятаться. Нам некуда было пойти вечером. Им неоткуда получать сведения. Ей некогда будет писать письма.*"),
        T(["Used with the infinitive of the verb (without НЕ) in impersonal constructions", "Used with any negative (НЕ) form of the verb, both in personal and impersonal constructions"], [
            ["Нам негде было учить русский язык.", "Мы нигде не учили русский язык."], ["Мне некуда идти сегодня.", "Я никуда не иду сегодня."],
            ["Нам неоткуда получать советских журналов.", "Мы ниоткуда не получаем советских журналов."], ["Ему некогда будет ходить в кино.", "Он никогда не будет ходить в кино."]], row_heads=False),
        P("НЕКОГДА has also another meaning — когда-то, очень давно = a long time ago: *Весь север Европы некогда был покрыт льдом.* This "
          "word is very rarely used now.")],
         ["negadv"], sub="мне некогда · я никогда не…", note=DLI + ", Lesson 105."),
    SECD("p4-sebya", "себя", [
        P("The English reflexive pronouns \"myself\", \"yourself\", etc. are rendered in Russian by the pronoun \"себя\", which is the same "
          "for all the genders, persons and numbers. \"Себя\" has no nominative case, since it can never be the subject of a sentence. In "
          "oblique cases it is declined like the pronoun \"ты\": себя, себе, себя, собой, о себе."),
        EX(("Я взял эту книгу для себя.", "I took this book for myself."), ("Возьмите это себе.", "Take this for yourself."),
           ("Она посмотрела на себя в зеркало.", "She looked at herself in the mirror."), ("Учитель взял с собой карту.", "The teacher took the map with him."),
           ("Он писал мне о себе.", "He wrote me about himself.")),
        P("The idiomatic forms \"у себя\" and \"к себе\" are commonly used in the meaning of \"at (or to) one's place\": *Командир у себя "
          "в кабинете. Я иду к себе в комнату.* The verb \"чувствовать\" is used together with the accusative form \"себя\" in describing "
          "one's state of being: *Как вы чувствуете себя? — Я чувствую себя хорошо.*")],
         ["sebya"], sub="для себя · с собой · о себе · чувствую себя", note=DLI + ", Lesson 64."),
    SECD("p5-svoi", "свой", [
        P("The word \"свой\" is declined like \"мой\". The preposition \"с\" becomes \"со\" before the word \"свой\": со своего стола, со "
          "своим братом. The possessive \"свой\" indicates that the object belongs to the performer of the action: *Я взял свои книги. Он "
          "взял свои книги. Вы взяли свои книги.*"),
        P("a) When the performer of the action is in the 3rd person: 1) the possessives \"его, её, их\" are used if the object does not "
          "belong to the performer of the action; 2) if the object belongs to the performer of the action, the possessive \"свой\" must be "
          "used: *Он говорил с его женой* (someone else's, not his own). *Он говорил со своей женой* (his own wife). b) When the performer "
          "of the action is the 1st or 2nd person either \"мой, твой, наш, ваш\" or \"свой\" may be used without any change of meaning: *Я "
          "взял мою книгу.* or *Я взял свою книгу.* c) As a rule \"свой\" modifies the object only.")],
         ["svoi"], sub="он взял свою книгу · он взял его книгу", note=DLI + ", Lesson 49."),
    SECD("p6-kotoryi", "который", [
        P("\"Который\" in subordinate clauses agrees in gender and number with the noun it refers to in the main sentence, but its case is "
          "determined by its function in the subordinate clause: a) *Где книга, которая лежала здесь на столе?* (Книга is the subject of "
          "the subordinate clause and the case is therefore nominative.) b) *Где книга, которую я только что положил на стол?* (Книга is the "
          "direct object in the subordinate clause and the case is therefore accusative.)")],
         ["kotoryi"], sub="книга, которая… · книга, которую…", note=DLI + ", Lesson 53."),
    SECD("p7-kakov", "каков, какова, каково, каковы", wiktionary("каков") + wiktionary("каково"), ["kakov"],
         sub="Каково ваше мнение? · Каковы ваши впечатления?"),
]

COMPLEX = [
    SECD("x1-chtoby", "чтобы — and что", [
        P("The conjunction \"чтобы\" (sometimes contracted to \"чтоб\") introduces subordinate clauses or phrases expressing goal, intention, "
          "order, suggestion, wish and necessity: a) goal, intention: *Отец прислал нам деньги, чтобы мы купили телевизор.* b) order, "
          "suggestion, wish: *Начальник требует, чтобы мы приходили на службу вовремя.* c) necessity: *Необходимо, чтобы вы зашли к нему "
          "сегодня.*"),
        P("When the subject of the subordinate clause is mentioned or the clause is an impersonal construction, \"чтобы\" is followed by the "
          "verb in the past tense regardless of the tense of the verb in the main sentence: *Учитель говорит громко, чтобы все его слышали.* "
          "But when the subject of the subordinate clause is not mentioned, being in such a case mostly the same as the subject of the main "
          "clause, then \"чтобы\" is followed by the infinitive: *Мой брат взял отпуск, чтобы поехать в Европу.*"),
        P("English expressions implying wish or idea, such as \"I want you to (do something)\" or \"Tell him to (do something)\", are rendered "
          "in Russian with the aid of \"чтобы\" + past tense: *Я хочу, чтобы вы помогли мне.* (But: *Я хочу помочь вам.*) *Скажите студентам, "
          "чтобы они сдали магнитофоны.*"),
        P("After the verbs \"сказать\", \"написать\", \"передать\" and also after such words as \"сказано\", \"написано\", \"важно\", \"чтобы\" "
          "is used to express an order or a wish, whereas \"что\" would be used to make a statement or convey information: *Брат пишет, чтобы "
          "его семья переехала в Москву.* (…that his family should move) *Брат пишет, что его семья переезжает в Москву.* (…is moving)")],
         ["chtoby"], sub="я хочу, чтобы вы… · он пишет, что…", note=DLI + ", Lesson 92."),
    SECD("x2-do-togo-kak", "до того как, после того как, о том что…", [
        P("Every Russian preposition demands a noun in a special case. But sometimes a preposition refers not to a single noun, but to a "
          "clause, thus forming a complex sentence: a) *Мы успели приехать домой до начала грозы.* (simple sentence) b) *Мы успели приехать "
          "домой до того, как гроза началась.* (complex sentence)"),
        P("When a preposition refers to a whole clause, a complex conjunction is used consisting of: 1) the preposition, 2) the pronoun \"то\" "
          "in the case required by the preposition, 3) a linking word."),
        T(["Preposition", "\"то\"", "Linking word"], [["после, до", "того (Gen.)", "как"], ["перед", "тем (Instr.)", "как"], ["о", "том (Prep.)", "что"],
                                                       ["за", "то (Acc.)", "что"], ["из-за", "того (Gen.)", "что"], ["(не) для", "того (Gen.)", "чтобы"], ["вместо", "того (Gen.)", "чтобы"]], row_heads=False),
        P("Examples: *Они ушли из дома до того, как в него попала бомба. Я расскажу вам о том, что было на собрании.* Complex conjunctions "
          "have to be used when the preposition refers to a clause. However it is preferable to avoid them if the meaning of the clause can "
          "be clearly expressed by a simple preposition and a noun: *Мы все поедем в Европу после окончания школы.*")],
         ["complex"], sub="до того как · перед тем как · о том, что · за то, что", note=DLI + ", Lesson 92."),
    SECD("x3-poka", "пока and пока не", [
        P("Пока is used as an adverb of time and as a conjunction. Пока не (until) is a conjunction. A. The adverb of time — пока — means: "
          "1) *Никому не говорите об этом пока!* — for the time being; 2) *Сведений о самолёте пока (ещё) нет.* — as yet; 3) *Я посижу здесь, "
          "а ты пока сбегай в лавку.* — in the meantime."),
        P("B. The conjunction ПОКА — while — introduces adverbial clauses of time. The action of both the main and the subordinate clauses "
          "can: a) completely coincide in time (imperfective verbs are used in both): *Пока шёл дождь, мы стояли под деревом.* b) partly "
          "coincide in time (perfective aspect is used in one of the clauses or in both): *Пока она готовила обед, я написал 2 письма.*"),
        P("C. The construction ПОКА НЕ (until, before) is used as a unit to introduce subordinate adverbial clauses of time. ПОКА НЕ has no "
          "negative meaning and the particle НЕ is not translated: *Он читал, пока не устали глаза. Я посижу здесь, пока вы не придёте.* "
          "Sometimes a compound conjunction — ДО ТЕХ ПОР ПОКА НЕ — is used instead: *Ученик повторял адрес до тех пор, пока не выучил его "
          "наизусть.*")],
         ["poka"], sub="пока шёл дождь · пока не устали глаза", note=DLI + ", Lesson 105."),
    SECD("x4-li", "ли: whether", [
        P("The English conjunction \"if\" introducing a conditional clause has the Russian equivalent ЕСЛИ. But the English \"if\", equivalent "
          "of \"whether\", expresses an indirect question or doubt and has the Russian equivalent ЛИ. The particle ЛИ never begins the "
          "clause; it takes the second place in the clause following the word to which the question or doubt refers: *Спроси его, говорит "
          "ли он по-немецки. Он спросил меня, живу ли я здесь. Я не знаю, сделают ли они это.* But: *Мы дадим ему работу, если он говорит "
          "по-немецки.*"),
        P("Sometimes ЛИ is used in direct questions, especially in those expressing a doubt: *Был ли он там? Не опоздал ли он на поезд?* "
          "Notice also constructions: negative infinitive + ЛИ, which express suggestions or invitations: *Не поехать ли нам в ресторан? "
          "Не взять ли тебе такси?*")],
         ["li"], sub="спроси его, говорит ли он… · не поехать ли нам…", note=DLI + ", Lesson 91."),
]

CREDIT = "Explanations: the DLI Basic Course grammar (public domain); sentences: Tatoeba (CC BY 2.0 FR) and the library's public-domain books; word forms analysed with the OpenCorpora dictionary (CC BY-SA 4.0)"
DLI_URL = "https://www.fsi-language-courses.org/russian/courses/dli-russian-basic-course"


VERB_CREDIT = ("; verb forms from the OpenCorpora dictionary, stress marks from the OpenRussian CSV export (CC BY-SA 4.0) "
               "and Koziev's accent list, kept where the two agree")


def _c(id, title, short, mark, blurb, secs):
    return ({"id": id, "title": title, "short": short, "mark": mark, "blurb": blurb, "credit": CREDIT + (VERB_CREDIT if id == "verbs" else ""), "creditUrl": DLI_URL,
             "license": "Public domain · CC BY 2.0 FR", "licenseUrl": ""}, secs)


COURSE_DEFS = [
    _c("aspect", "Verbal Aspect", "Aspect", "Вид", "Imperfective and perfective: process and result, the words that call for each, aspect in commands, "
       "the perfective future, по- and с- — in DLI's words, practised on real sentences.", ASPECT),
    _c("verbs", "Conjugation, Position Verbs and -ся", "Verbs", "Гл", "The Е and И conjugations, the past tense, стоять — ставить — встать "
       "and their kin, and the verbs in -ся — practised on real sentences.", VERBS),
    _c("compare", "Comparatives, Superlatives, Short Adjectives", "Compare", "≷", "Новее, лучше, старше, чем or the genitive, более, самый, "
       "-ейший, and the short adjectives — practised on real sentences.", COMPARE),
    _c("pronouns", "Pronouns in Depth", "Pronouns", "Мест", "-то and -нибудь, некого and никого, негде and нигде, себя, свой, который, "
       "каков — practised on real sentences.", PRONOUNS),
    _c("complex", "Complex Sentences", "Complex", "§", "Чтобы and что, до того как and the other complex conjunctions, пока and пока не, "
       "and ли — practised on real sentences.", COMPLEX),
]
