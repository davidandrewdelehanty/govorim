# -*- coding: utf-8 -*-
# Verbs of Motion, part A: the verbs without prefixes.
# Every explanation is quoted: the Defense Language Institute Russian Basic
# Course, Grammar Reference Books I and II (public domain; the lesson numbers
# are DLI's), the English Wikipedia's «Russian grammar» § Verbs of motion
# (CC BY-SA 4.0), and the English Wiktionary's entries (CC BY-SA 4.0), whose
# definitions and conjugation tables are drawn by motion_kit. The order of
# topics follows the one a Russian course on the subject takes: the pairs,
# their direction, the carrying verbs, the perfective with по-, the idioms.
# Exercises: real sentences, mined by motion_mine.py.
from kit import *
from motion_kit import *

SRC = "From the DLI Grammar Reference Book"

PAIRS = [("идти", "ходить"), ("ехать", "ездить"), ("лететь", "летать"), ("бежать", "бегать"), ("плыть", "плавать"),
         ("лезть", "лазить"), ("брести", "бродить"), ("ползти", "ползать"), ("нести", "носить"), ("вести", "водить"),
         ("везти", "возить"), ("гнать", "гонять"), ("катить", "катать"), ("тащить", "таскать")]

ex, more = drills("m01-pairs")
S01 = SEC("m01-pairs", "Two verbs for every way of going", sub="идти / ходить · ехать / ездить · лететь / летать — the fourteen pairs", blocks=[
  SOURCES,
  P("Verbs of motion are a distinct class of verbs found in several Slavic languages. Due to the extensive semantic information they contain, Russian verbs of motion pose difficulties for non-native learners at all levels of study. "
    "Unprefixed verbs of motion, which are all imperfective, divide into pairs based on the direction of the movement (uni- or multidirectional — sometimes referred to as determinate/indeterminate or definite/indefinite). "
    "Thus, the roots of motion verbs convey the lexical information of manner of movement, e.g. walking, crawling, running, whereas prefixes denote path, e.g. motion in and out of space. "
    "The roots also distinguish between means of conveyance, e.g. by transport or by one's own power, and in transitive verbs, the object or person being transported."),
  NOTE(WP),
  pair_table(PAIRS, caption="Pairs of Russian verbs of motion — one direction, and many directions (or there and back)"),
  cite(*[l for p in PAIRS for l in p]),
  H("The present tense has two jobs"),
  P("The present tense of all Russian verbs has a twofold function; it indicates: A. an action in progress (\"actual\" function); B. a repeated or habitual action (\"repeated\" function). "
    "However each action of going (to go on foot, to ride, to fly) is expressed in Russian by two parallel verbs: one for the function A — being on the way to … — иду, еду, лечу; "
    "another for the function B — usually, often, etc. to go to … (the motion to and from is understood) — хожу, езжу, летаю."),
  EX(("Капитан идёт в штаб.", "Он часто ходит в штаб."), ("Капитан едет в город.", "Он редко ездит в город."), ("Капитан летит в Вашингтон.", "Он иногда летает в Вашингтон.")),
  NOTE("DLI, Lesson 22."),
  H("How they conjugate"),
  P("The verb идти means \"to go, be going\". It refers to going on foot. This verb belongs to the 1st conjugation (characterized by the vowel -ё-, like живу, -ёшь, -ёт …)."),
  P("The verb ехать refers to going by some means of transportation, i.e. riding, driving: Я еду на поезде. (Я иду пешком.) Я еду в Европу. (Я иду в комнату.) This verb belongs to the 1st (Е) type of conjugation. "
    "Note. — The motion of a vehicle is expressed by идёт (not едет) when time-table and regular route are involved: Куда идёт этот автобус? Когда идёт поезд в Сан-Франциско? Notice also: Танк идёт (not едет)."),
  P("Лететь: this verb belongs to the 2nd (И) type of conjugation. Notice that т changes into ч in the first person singular."),
  NOTE("DLI, Lessons 19–20."),
  P("Ходить, ездить: these two verbs belong to the 2nd (И) type of conjugation. Notice that the consonant д changes into ж in the first person singular (like видеть — вижу — видишь). "
    "Летать: this verb belongs to the 1st (Е) type of conjugation."),
  NOTE("DLI, Lesson 22."),
  conj_table(["идти", "ходить", "ехать", "ездить", "лететь", "летать"], caption="The going verbs, in Wiktionary's forms (stress marked)"),
  cite("идти", "ходить", "ехать", "ездить", "лететь", "летать"),
  H("Where to?"),
  P("The goal of motion after the verb идти is usually indicated by the preposition в + Acc. The corresponding question is куда: Куда они идут? Они идут в школу. "
    "With certain nouns the preposition на (instead of в) is used to indicate goal of motion: Куда вы идёте? — Я иду на вокзал."),
  P("The adverbs здесь (here), там (there), дома (at home) indicate location and answer the question где. They are not used after the verb идти. "
    "The adverbs сюда (here), туда (there), домой (home) indicate direction and answer the question куда. They are used after the verb идти."),
  EX(("Где он был? — Он был здесь, там, дома.", "Куда он идёт? — Он идёт сюда, туда, домой.")),
  P("The expression \"to go by …\" (means of transportation) is rendered in Russian by на + prepositional case: ехать на поезде (на автобусе, на автомобиле), лететь на самолёте. The corresponding question is на чём? (На чём вы едете?)"),
  NOTE("DLI, Lessons 19–20."),
], exercises=ex, more=more)

ex, more = drills("m02-direction")
S02 = SEC("m02-direction", "One direction, or round and about", sub="идёт or ходит? · habits, round trips, ability · ходил and ездил for был", blocks=[
  P("Unidirectional verbs describe motion in progress in one direction, e.g.:"),
  EX(("Мы идём в библиотеку.", "We are headed to the library."), ("Я шла на работу.", "I was on my way to work."), ("Птицы летят на юг.", "The birds are flying south.")),
  P("Multidirectional verbs describe: 1. General motion, referring to ability or habitual motion, without reference to direction or destination; 2. Movement in various directions; 3. Repetition of completed trips; 4. In the past tense, a single completed round trip."),
  EX(("Ребёнок ходит шесть месяцев.", "The child has been walking for six months."), ("Птицы летают, рыбы плавают, а собаки ходят.", "Birds fly, fish swim, and dogs walk."),
     ("Мы ходили по городу весь день.", "We walked around the city all day."), ("Она ходит в супермаркет каждую неделю.", "She goes to the supermarket every week."),
     ("В прошлом году я ездил в Россию.", "I went to Russia (and returned) last year.")),
  NOTE(WP),
  H("The basic meaning"),
  P("The basic meaning of the verbs идти, ехать, лететь is being actually on the way to some place: Мы идём в кино. Мы едем в город. Мы летим в Нью-Йорк. — right now."),
  NOTE("DLI, Lesson 20."),
  H("In the past"),
  EX(("Мы встретили его, когда он шёл в школу.", "We met him when he was walking (on his way) to school."), ("Они каждый день ходили в клуб.", "They went to the club every day. (Repeated action.)"),
     ("Она пошла в библиотеку.", "She went to (left for) the library.")),
  P("Note — that the English \"went\" is commonly rendered in Russian by either: a) ходил (for the repeated action) or b) пошёл (for the single perfective action)."),
  H("ходил and ездил instead of был"),
  P("The verbs \"ходил\" and \"ездил\" are sometimes used instead of the verb \"был\". When so used, \"ходил\" and \"ездил\" may indicate a single completed trip (going to and coming from a place). This use is possible in the past tense only."),
  EX(("Вы были на почте?", "Have you been at the post office?"), ("Да, я ходил (ездил) туда утром.", "Yes, I went there in the morning.")),
  NOTE("DLI, Lesson 54."),
  H("Motion without a definite goal"),
  P("Like the verb \"ходить\" (по комнате) the verb \"летать\" may be used to indicate motion without a definite goal. Note. — Do not confuse the following: Самолёт летает над городом. (motion without a definite goal) — Самолёт летит над городом. (motion towards a definite goal) — both: The aircraft is flying over the city."),
  EX(("Студент ходит по комнате.", "The student walks about the room."), ("Самолёт летает над городом.", "The aircraft is flying over the city.")),
  P("The verb \"летал\" (like the verbs \"ходил\" and \"ездил\") is sometimes used instead of the verb \"был\". When so used, \"летал\" may indicate a single completed trip. This use is possible in the past tense only: Вы были в Москве? — Да, я летал туда месяц тому назад."),
  NOTE("DLI, Lesson 55."),
  H("In the future"),
  EX(("Я буду идти медленно (долго, 2 часа).", "I shall be walking slowly (for a long time, for 2 hours) (action in its progress)."),
     ("Зимой мы часто будем ходить в театр.", "In winter we shall often go to the theater. (Repeated action.)"),
     ("После завтрака они пойдут в магазин.", "After breakfast they will go to (leave for) the store.")),
  P("Note — that the form \"буду идти\" is seldom used. It occurs mostly when the duration or manner of the action is described. A single action in the future tense is commonly rendered by — \"я пойду\"."),
  NOTE("DLI, Lesson 54."),
], exercises=ex, more=more)

S03 = SEC("m03-now-and-lets-go", "The present for the future, and «let's go»", sub="Завтра мы идём в кино · Идёмте! · Иди(те)! Поезжай(те)! · Приходите!", blocks=[
  P("As in English, the present tense of these verbs may also refer to the future:"),
  EX(("Завтра мы идём в кино.", ""), ("Сегодня вечером мы едем в город.", ""), ("В субботу мы летим в Нью-Йорк.", "")),
  NOTE("DLI, Lesson 20."),
  P("Note. — The present tense of the verbs иду, еду, лечу may also refer to a non-repetitive future action: Завтра он идёт на лекцию. В субботу мы едем в Нью-Йорк, а оттуда летим в Европу."),
  H("Идёмте! Едемте!"),
  P("The forms идёмте and едемте mean \"let's go\" (let's drive): Идёмте, майор! Едемте, господа! Идём and едем (let's go, let's drive) are familiar forms of address (addressing one or several persons)."),
  NOTE("DLI, Lesson 22."),
  H("The imperative"),
  P("The imperative of идти is идите; the imperative of ехать is поезжайте. Идите в класс! (on foot) Поезжайте в штаб! (by vehicle) The familiar forms do not have the ending -те: Иди! Поезжай!"),
  NOTE("DLI, Lesson 28."),
  P("The Imperative is: идите! — (не) ходите! — пойдите! For ехать: (не) ездите! — поезжайте!"),
  NOTE("DLI, Lesson 54."),
  P("Note the expressions in which the verb \"to come\" is translated into Russian with the verb идти (when the subject is in sight): Come here! — Иди(те) сюда! I see him. He is coming here. — Я вижу его. Он идёт сюда."),
  NOTE("DLI, Lesson 19."),
  P("Приходите and приезжайте both mean \"come\" (on foot, by vehicle). Идите means both \"go\" and \"come\" (on foot), and is used only when immediate action of the person (who is normally in sight) is expected. Compare:"),
  EX(("Приходите сюда завтра!", "Come here tomorrow!"), ("Идите сюда!", "Come here!"), ("Идите туда!", "Go there!")),
  P("The familiar form of the imperative does not have the ending -те: войдите — войди, идите — иди, приезжайте — приезжай, приходите — приходи."),
  NOTE("DLI, Lesson 24."),
  conj_table(["пойти", "поехать"], caption="The perfective future and imperative — пойдём(те)!, поезжай(те)!"),
  cite("пойти", "поехать"),
], exercises=drills("m03-now-and-lets-go")[0], more=drills("m03-now-and-lets-go")[1])

ex, more = drills("m04-carrying")
S04 = SEC("m04-carrying", "Carrying, leading, driving", sub="нести / носить · вести / водить · везти / возить", blocks=[
  P("The verb \"to carry\" in Russian is rendered in two ways depending upon the way of carrying: on foot — носить-нести, понести; by vehicle — возить-везти, повезти. "
    "Note that these verbs directly correspond in their usage to the \"going verbs\" ходить-идти, пойти and ездить-ехать, поехать."),
  T(["", "Repeated function", "Actual function", "Perfective"], [
    ["to carry (on foot)", "носить — ношу, -сишь; носил; буду носить", "нести — несу, -ёшь; нёс; буду нести", "понести — понёс; понесу, -ёшь"],
    ["to carry (by vehicle)", "возить — вожу, -зишь; возил; буду возить", "везти — везу, -ёшь; вёз; буду везти", "повезти — повёз; повезу, -ёшь"],
    ["to lead, to conduct", "водить — вожу, -дишь; водил; буду водить", "вести — веду, -ёшь; вёл; буду вести", "повести — повёл; поведу, -ёшь"],
  ], caption="DLI, Lesson 78"),
  P("Note some special uses of these verbs: нести ответственность — to bear responsibility; нести потери — to suffer casualties; носить костюм (пальто, шляпу, ботинки etc.) — to wear (habitually); носить очки — to wear glasses."),
  P("Note also the following idiomatic construction: Мне не везёт. — I am not lucky. Ему везёт. — He is lucky. Вам повезло. — You were lucky. "
    "The \"carrying verbs\" (just like the \"going verbs\") form their perfectives by adding the prefix \"по-\" to the actual function verbs."),
  H("Водить — вести: to lead, to take, to drive, to conduct"),
  P("This verb also follows the pattern of \"going verbs\". Note the following meanings: 1. to lead, to take: Я веду моего сына в школу. Я каждый день вожу его в школу. 2. to drive: Кто ведёт эту машину? Он не умеет водить машину. "
    "3. to conduct: Противник ведёт огонь. 4. to behave oneself: Этот мальчик плохо ведёт себя. Note that in the last two examples (3 and 4) only the actual function verb \"вести\" can be used. (Never \"водить\")."),
  NOTE("DLI, Lesson 78."),
  H("Going versus taking"),
  P("Three pairs of motion verbs generally refer to 'taking', 'leading' with additional lexical information on manner of motion and object of transport encoded in the verb stem. These are нести/носить, вести/водить, and везти/возить."),
  EX(("Он носит портфель.", "He carries a briefcase."), ("Она несёт домашнее задание на занятия.", "She is taking her assignment to class."),
     ("Учитель вёл школьников на экскурсию.", "The teacher was taking the children to a field trip."), ("Она водила свою подругу в театр.", "She took her friend to the theatre."),
     ("Она умеет водить машину.", "She knows how to drive a car."), ("Она везёт бабушку в инвалидном кресле.", "She is wheeling her grandmother in a wheelchair."),
     ("Поезд возил пассажиров в Англию.", "The train took the passengers to England (and back).")),
  NOTE(WP),
  conj_table(["нести", "носить", "вести", "водить", "везти", "возить"], caption="The carrying verbs, in Wiktionary's forms"),
  cite("нести", "носить", "вести", "водить", "везти", "возить"),
], exercises=ex, more=more)

ex, more = drills("m05-other-pairs")
S05 = SEC("m05-other-pairs", "Running, swimming, climbing, crawling, dragging", sub="бежать / бегать · плыть / плавать · лезть / лазить · брести / бродить · ползти / ползать · гнать / гонять · катить / катать · тащить / таскать · the -ся verbs", blocks=[
  H("бегать — бежать, побежать"),
  P("The verbs бегать-бежать, побежать belong to the group of \"going verbs\" similar to the verbs ходить-идти, пойти. Note that in the conjugation of the verb \"бежать\", the consonants \"ж\" and \"г\" are alternated: я бегу, ты бежишь, они бегут. "
    "Note also that in all persons, except the 3rd person plural, it belongs to the 2nd conjugation: ты бежишь, он бежит, мы бежим, вы бежите. In the 3rd person plural it belongs to the 1st conjugation: они бегут."),
  NOTE("DLI, Lesson 82."),
  H("плавать — плыть, поплыть"),
  P("The verb плавать — плыть, поплыть belong to the group of \"going verbs\" similar to the verbs ходить — идти, пойти; \"плавать\" (like \"ходить\") is a \"repeated function\" verb. Note the ways in which it is used: "
    "Я умею плавать. — I know how to swim. Дерево плавает в воде. — Wood floats in water. Я плаваю на этом корабле. — I sail (work) on this ship. "
    "In naval terminology the verb \"идти\" instead of \"плыть\" is commonly used: Я иду на этом корабле. Наш корабль идёт по Чёрному морю. Мы шли в Архангельск."),
  NOTE("DLI, Lesson 73."),
  conj_table(["бежать", "бегать", "плыть", "плавать", "лезть", "лазить"], caption="Wiktionary's forms"),
  cite("бежать", "бегать", "плыть", "плавать", "лезть", "лазить"),
  conj_table(["брести", "бродить", "ползти", "ползать", "гнать", "гонять"]),
  cite("брести", "бродить", "ползти", "ползать", "гнать", "гонять"),
  conj_table(["катить", "катать", "тащить", "таскать"]),
  cite("катить", "катать", "тащить", "таскать"),
  H("With -ся"),
  P("Researchers have also included the reflexive verbs катиться/кататься, гнаться/гоняться, нестись/носиться, and тащиться/таскаться."),
  NOTE(WP),
  T(["", "one direction", "many directions", "Wiktionary's definition"], [
    ["to roll, to ride", "**%s**" % head("катиться"), "**%s**" % head("кататься"), defs("кататься", 3)],
    ["to rush, to race", "**%s**" % head("нестись"), "**%s**" % head("носиться"), defs("нестись", 2)],
    ["to chase", "**%s**" % head("гнаться"), "**%s**" % head("гоняться"), defs("гнаться", 2)],
    ["to drag oneself", "**%s**" % head("тащиться"), "**%s**" % head("таскаться"), defs("тащиться", 2)],
  ]),
  cite("катиться", "кататься", "нестись", "носиться", "гнаться", "гоняться", "тащиться", "таскаться"),
  P("Мне нравится кататься на лыжах, на коньках, на велосипеде и на лодке. — I like to ski, skate, cycle, and row."),
  NOTE(WP),
], exercises=ex, more=more)

ex, more = drills("m06-po")
S06 = SEC("m06-po", "Setting out: пойти, поехать — and сходить, съездить", sub="по- + the one-direction verb · походить, поездить (for a while) · сходить, съездить (there and back)", blocks=[
  P("The perfective aspect of \"Going Verbs\" is formed by adding the prefix \"по\" to the actual function verbs (\"идти\", \"ехать\", etc.). The perfective verbs пойти and поехать denote a single action with emphasis on the completed start. "
    "(Similar to the English concept of \"to leave for\"; \"to set out\")."),
  EX(("Где старшина?", "Where is the M/Sgt?"), ("Он пошёл в штаб.", "He went to (left for) HQ.")),
  P("Note. — that the vowel -ё- in the verb \"пойти\" occurs in the masculine form only: пошёл, пошла, пошло, пошли. The future perfective (пойду, пойдёшь) belongs to the 1st -ё- type of conjugation. The future perfective (поеду, поедешь) belongs to the 1st -е- type of conjugation."),
  NOTE("DLI, Lesson 54."),
  P("The perfective verb полететь (like пойти and поехать) denotes single action with the emphasis on the completed start. The past perfective (полетел, -ла, -ло, -ли) is formed in a regular way. "
    "The future perfective (полечу, полетишь) belongs to the 2nd (-и-) type of conjugation. The consonant \"т\" changes into \"ч\" in the first person singular only."),
  EX(("Полковник полетел в Вашингтон.", "The Colonel flew to Washington. (single action; completed start)"), ("Завтра я полечу на фронт.", "Tomorrow I'll fly to the front. (single action)")),
  NOTE("DLI, Lesson 55."),
  P("The addition of the prefix по- to a unidirectional verb of motion makes the verb perfective, denoting the beginning of a movement, i.e. 'setting out'. These perfectives imply that the agent has not yet returned at the moment of speech, e.g.:"),
  EX(("Он пошёл к другу.", "He went to a friend's place (and has not returned; unidirectional perfective)."), ("Он шёл к другу.", "He was on his way to a friend's place (unidirectional imperfective)."),
     ("Он ходил к другу.", "He used to go to a friend's place (multidirectional)."), ("Он сходил к другу.", "He went to a friend's place (and has returned; see prefixed perfective forms of motion verbs below).")),
  NOTE(WP),
  conj_table(["пойти", "поехать", "полететь", "побежать", "понести", "повезти"], caption="The perfectives with по-: future and past, in Wiktionary's forms"),
  cite("пойти", "поехать", "полететь", "побежать", "понести", "повезти"),
  H("по- and с- with ходить, ездить, летать"),
  P("Adding a prefix to the repeated function verbs: ходить, ездить/езжать/, летать usually does not form the perfective aspect but merely changes the meaning of the original verb: ходить — to go, уходить — to leave. "
    "However, prefixes \"по-\" and \"с-\" may form the perfective aspect with the \"repeated function\" verbs."),
  P("a) Prefix \"по-\" denoting a perfective action of limited duration (an action \"for a while\"). The prefix \"по-\" when added to the \"repeated function\" verbs — ходить, ездить, летать — forms perfective verbs: походить, поездить, полетать. "
    "These verbs denote a single completed action of limited duration, similar to the verb \"погулять\"."),
  EX(("Он походил по комнате и сел за стол.", ""), ("Мы поездили по городу и поехали домой.", ""), ("Я хочу полетать на самолёте.", "")),
  P("b) Prefix \"с-\" implying a single round trip. The prefix \"с-\" when added to the \"repeated function\" verbs — ходить, ездить, летать — forms perfective verbs: сходить, съездить, слетать. "
    "These verbs denote a single trip (going to and coming from a place), especially when a quick return is implied."),
  EX(("Мне надо сходить на почту за письмами.", ""), ("Я съезжу на вокзал и узнаю, когда отходит поезд.", ""), ("Он сходил в библиотеку и взял книгу.", "")),
  T(["Imperfective", "Perfective", "a) \"for a while\"", "b) \"round trip\""], [
    ["идти — ходить", "пойти", "походить", "сходить"], ["ехать — ездить", "поехать", "поездить", "съездить"], ["лететь — летать", "полететь", "полетать", "слетать"],
  ], caption="Thus we have (DLI, Lesson 63)", row_heads=False),
  NOTE("DLI, Lesson 63."),
  P("Note the preposition: after \"going verbs\" or the verb \"to send\" the preposition \"за\" + Instr. is used to indicate the idea of \"going after\" or \"sending for\" something or somebody: Он пошёл за газетой. — He went after the newspaper. Пошлите за доктором. — Send for the doctor."),
  NOTE("DLI, Lesson 63."),
], exercises=ex, more=more)

ex, more = drills("m07-idioms")
S07 = SEC("m07-idioms", "Rain falls, time flies, luck comes: the idioms", sub="идёт дождь · часы идут · время летит · мне везёт · вести себя · носить очки", blocks=[
  P("Note the following expressions: Идёт дождь. Фильм идёт. Разговор идёт. Идёт снег. Урок идёт. Работа идёт. Поезд идёт. Дорога идёт. Собрание идёт."),
  NOTE("DLI, Lesson 19."),
  P("The uni- and multidirectional distinction rarely figures into the metaphorical and idiomatic use of motion verbs, because such phrases typically call for one or the other verb. See below for examples:"),
  T(["verb", "example"], [
    ["идти", "Идёт не дождь, а снег. — It's snowing, not raining. · Часы идут. — The clock is ticking. · Идёт фильм. — A film is on. · Это платье тебе идёт. — That dress suits you. · Правительство идёт к демократии. — The government is moving towards democracy."],
    ["вести", "Страна ведёт войну. — The country is waging a war. · Девочка ведёт дневник. — The girl keeps a diary. · Дорога ведёт в город. — The road leads to the city. · Ложь к добру не ведёт. — No good comes from lying."],
    ["нести", "Женщина несёт ответственность за детей. — The woman bears the responsibility of her children. · Фермер несёт потери от засухи. — The farmer bears the losses from the drought. · Оратор несёт чушь. — The speaker is talking nonsense."],
    ["лететь", "Время летит. — Time flies. · Акции летят от экономического кризиса. — Shares are plummeting because of the economic crisis."],
    ["лезть", "Хулиганы лезут в драку. — The hooligans are getting into a brawl."],
    ["везти", "Ей везёт / повезло. — She is lucky/got lucky."],
    ["бежать", "Кровь бежит из раны. — Blood is flowing from the wound. · Дни бегут. — The days fly past."],
    ["носить", "Иван Иванович носит имя отца. — Ivan Ivanovich bears the name of his father. · Она носит красивую одежду. — She wears pretty clothing."],
    ["ходить", "Ходит слух, что она бросила мужа. — Rumor has it that she left her husband."],
    ["водить", "Он долго водил меня за нос, когда говорил, что в нашей фирме всё хорошо. — He fooled me for a long time when he said that everything was fine in our firm."],
  ], caption="Idiomatic uses of motion verbs", row_heads=True),
  NOTE(WP),
  P("Note some special uses of these verbs: нести ответственность — to bear responsibility; нести потери — to suffer casualties; носить костюм (пальто, шляпу, ботинки etc.) — to wear (habitually); носить очки — to wear glasses. "
    "Note also the following idiomatic construction: Мне не везёт. — I am not lucky. Ему везёт. — He is lucky. Вам повезло. — You were lucky. To behave oneself: Этот мальчик плохо ведёт себя."),
  NOTE("DLI, Lesson 78."),
], exercises=ex, more=more)

SECTIONS = [S01, S02, S03, S04, S05, S06, S07]
