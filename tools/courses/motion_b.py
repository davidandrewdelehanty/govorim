# -*- coding: utf-8 -*-
# Verbs of Motion, part B: the prefixes. Quoted from the DLI Russian Basic
# Course, Grammar Reference Books I and II (public domain), the English
# Wikipedia's «Russian grammar» § Verbs of motion (CC BY-SA 4.0) and the
# English Wiktionary (CC BY-SA 4.0); exercises mined by motion_mine.py.
from kit import *
from motion_kit import *

ex, more = drills("m08-how-prefixes-work")
S08 = SEC("m08-how-prefixes-work", "How a prefix changes a verb of motion", sub="the new aspect pair · -йти, -ехать / -езжать, -бегать, -плывать · stress on вы-", blocks=[
  SOURCES,
  P("Motion verbs combine with prefixes to form new aspectual pairs, which lose the distinction of directionality, but gain spatial or temporal meanings. The unidirectional verb serves as the base for the perfective, and the multidirectional as the base for the imperfective. "
    "In addition to the meanings conveyed by the prefix and the simplex motion verb, prepositional phrases also contribute to the expression of path in Russian. Thus, it is important to consider the whole verb phrase when examining verbs of motion."),
  P("In some verbs of motion, adding a prefix requires a different stem shape: A. идти → -йти 'go (on foot)': For prefixes ending in a consonant, an -o- is added in all forms, e.g.: войти. й is lost in the conjugated forms of прийти, e.g.: приду 'I will come'. "
    "B. ездить → -езжать 'go (by conveyance)': For prefixes ending in a consonant, a hard sign (ъ) is added before –ехать and –езжать, e.g.: въезжать 'enter (by conveyance)'. "
    "C. бе́гать → -бега́ть 'run': The formation of the verb remains the same, but stress shifts from the stem to the endings, e.g.: убега́ть 'run away'. "
    "D. пла́вать → -плыва́ть 'swim': The vowel in the root changes to -ы- and the stress shifts to the endings. "
    "E. As with non-motion verbs, in perfective verbs with the prefix вы-, the prefix is stressed in all forms, e.g. вы́йдешь 'you will go out'."),
  NOTE(WP),
  P("Any prefix (except \"по-\"), added to the imperf. pair of \"going verbs\" (to both, repeated and actual functions), makes them an ordinary imperfective-perfective pair. Thus: "
    "Original pair, imperfective: repeated — ходить, ездить, летать; actual — идти, ехать, лететь. New pair: imperfective — приходить, приезжать, прилетать; уходить, уезжать, улетать; perfective — прийти, приехать, прилететь; уйти, уехать, улететь."),
  EX(("Он всегда приезжает сюда на грузовике.", "Imperfective"), ("Он всегда приезжал сюда на грузовике.", ""), ("Он всегда будет приезжать сюда на грузовике.", ""),
     ("Сегодня он приехал сюда на автобусе.", "Perfective"), ("Сегодня он приедет сюда на автобусе.", "")),
  P("Notice that with the verb \"идти\" -о- is inserted between the verb and the prefix if the prefix ends in a consonant."),
  NOTE("DLI, Lesson 56."),
  P("All prefixed verbs derived from ходить belong to the 2nd (И) type of conjugation and have the same change in the stress pattern: ходить — я хожу, ты ходишь, etc.; отходить — я отхожу, ты отходишь; подходить — я подхожу, ты подходишь; приходить — я прихожу, ты приходишь; уходить — я ухожу, ты уходишь. "
    "All prefixed verbs derived from езжать (which is not used without prefix) belong to the 1st (Е) type of conjugation and have a fixed stress."),
  NOTE("DLI, Lesson 29."),
  P("Any prefix (except \"по-\") added to the imperfective pair of these verbs (носить, возить, водить — to both \"repeated\" and \"actual\" functions) makes them an ordinary imperfective-perfective pair which carries the meaning governed by the prefix. "
    "The verbs \"носить\", \"возить\" and \"водить\" have basically the same prefixes as the verbs of motion we have studied previously with corresponding changes in meaning. However, many of the prefixed verbs have also secondary meanings, some of which are more important than the basic meanings."),
  NOTE("DLI, Lesson 79."),
  T(["unprefixed pair", "perfective stem", "imperfective stem", "example"], [
    ["идти / ходить", "-йти (войти, обойти; прийти — приду)", "-ходить", "уйти — уходить"],
    ["ехать / ездить", "-ехать (въехать, объехать)", "-езжать", "приехать — приезжать"],
    ["лететь / летать", "-лететь", "-летать", "улететь — улетать"],
    ["бежать / бегать", "-бежать", "-бега́ть", "прибежать — прибегать"],
    ["плыть / плавать", "-плыть", "-плыва́ть", "переплыть — переплывать"],
    ["нести / носить", "-нести", "-носить", "принести — приносить"],
    ["вести / водить", "-вести", "-водить", "перевести — переводить"],
    ["везти / возить", "-везти", "-возить", "отвезти — отвозить"],
    ["лезть / лазить", "-лезть", "-лезать", "влезть — влезать"],
    ["ползти / ползать", "-ползти", "-ползать", "уползти — уползать"],
  ], caption="The stems the prefixes attach to (Wiktionary's entries)", row_heads=False),
  conj_table(["прийти", "приходить", "приехать", "приезжать", "выйти", "выходить"], caption="Three pairs in full, in Wiktionary's forms — note вы́йду, вы́йдешь"),
  cite("прийти", "приходить", "приехать", "приезжать", "выйти", "выходить"),
], exercises=ex, more=more)


def prefix_section(sid, title, sub, pf_ipf, blocks, caption=None):
    ex, more = drills(sid)
    tbl = prefixed_table(pf_ipf, caption=caption or "Verbs with this prefix, and Wiktionary's definitions")
    return SEC(sid, title, sub=sub, blocks=blocks + [tbl, cite(*[l for p in pf_ipf for l in p])], exercises=ex, more=more)


S09 = prefix_section("m09-v-vy", "в- and вы-: in, and out", "войти в комнату · выйти из дома · вынести, ввезти", [
    ("войти", "входить"), ("въехать", "въезжать"), ("влететь", "влетать"), ("вбежать", "вбегать"), ("внести", "вносить"), ("ввести", "вводить"), ("ввезти", "ввозить"), ("влезть", "влезать"),
    ("выйти", "выходить"), ("выехать", "выезжать"), ("вылететь", "вылетать"), ("выбежать", "выбегать"), ("вынести", "выносить"), ("вывести", "выводить"), ("вывезти", "вывозить"), ("вылезть", "вылезать"),
  ], [
  T(["prefix / primary meanings", "examples / additional meanings", "prepositional phrases"], [
    ["**в-, во-** — Movement inwards across a threshold, entering. Antonym: вы-", "Трамвай остановился, и девушка вошла. — The tram stopped and the girl entered.", "в / на + acc."],
    ["**вы-** — Movement out of something across a threshold, exiting. Antonym: в-", "Она вышла из кабинета. — She exited the office. Other: 1. Step out for a short period of time: Секретарь вышел на десять минут. — The secretary left for ten minutes. 2. Leave at a specific time frame: Они выехали рано утром, чтобы успеть на поезд/самолёт. — They left early in the morning to catch their train/plane.", "из / с / от + gen.; в / на + acc.; к + dat."],
  ], row_heads=False),
  NOTE(WP),
  P("The verbs входить (to enter, to come in, to go in) and выходить (to come out, to go out) belong to the 2nd (\"-и-\") type of conjugation. They are conjugated exactly like the verb ходить: я вхожу, ты входишь … они входят; я выхожу, ты выходишь … они выходят. "
    "The verbs въезжать (to drive in) and выезжать (to drive out) belong to the 1st (\"-е-\") type of conjugation (like читать): я въезжаю, ты въезжаешь … они въезжают."),
  NOTE("DLI, Lesson 33."),
  EX(("Я вхожу в эту комнату каждый день.", "Imperfective"), ("Я входил в эту комнату каждый день.", ""), ("Я буду входить в эту комнату каждый день.", ""),
     ("Я вошёл в комнату и открыл окно.", "Perfective"), ("Я войду в комнату и открою окно.", "")),
  NOTE("DLI, Lesson 56."),
  P("Ввозить — ввезти — to haul in, to import; вывозить — вывезти — to haul out, to export. Note the special use of the verbs \"ввозить\" and \"вывозить\": Англия ввозит зерно, а вывозит машины. — England imports grain and exports machinery. Note also the nouns: ввоз — import; вывоз — export."),
  NOTE("DLI, Lesson 79."),
])

S10 = prefix_section("m10-pri-u", "при- and у-: arriving, and leaving", "прийти, приехать, принести · уйти, уехать, унести", [
    ("прийти", "приходить"), ("приехать", "приезжать"), ("прилететь", "прилетать"), ("прибежать", "прибегать"), ("приплыть", "приплывать"), ("принести", "приносить"), ("привести", "приводить"), ("привезти", "привозить"),
    ("уйти", "уходить"), ("уехать", "уезжать"), ("улететь", "улетать"), ("убежать", "убегать"), ("уплыть", "уплывать"), ("унести", "уносить"), ("увести", "уводить"), ("увезти", "увозить"),
  ], [
  P("Notice that the prefix при- expresses the idea of arriving, while the prefix у- expresses the idea of leaving. Note. — The verbs приходить and приезжать usually refer to the habitual or repeated actions: Он приходит (приезжает) сюда каждый день. — He comes here every day. "
    "These verbs, as the other verbs of motion, may be used to express a single action in the future: Он приходит на работу завтра утром. — He is coming to work tomorrow morning. Она приезжает из Москвы сегодня вечером. — She is coming (arriving) from Moscow this evening. "
    "When the action is in progress in the present such expressions as \"He is coming\" or \"He is on the way here\" are expressed in Russian in the following way: Кто это идёт (едет) сюда? — Это старшина. Лейтенант в штабе? — Нет, он уже идёт (едет) сюда. "
    "Приходить and приезжать are not used to denote an action in progress."),
  NOTE("DLI, Lesson 24."),
  T(["prefix / primary meanings", "examples / additional meanings", "prepositional phrases"], [
    ["**при-** — Intended arrival, signals presence of the agent at a location as a result of motion. Antonym: у-", "Он приехал в Москву неделю назад. — He arrived in Moscow a week ago.", "в / на + acc.; к + dat.; из / с / от + gen."],
    ["**у-** — Intended departure, signals absence. Antonym: при-", "Они улетят из Владивостока через месяц. — They will leave Vladivostok in a month. Где Игорь? Он уже ушёл. — Where is Igor? He already left.", "в / на + acc.; к + dat.; из / с / от + gen."],
  ], row_heads=False),
  NOTE(WP),
  P("With the carrying verbs: приносить — принести — to bring (on foot); привозить — привезти — to bring (by vehicle); приводить — привести — to bring (along), to lead; уносить — унести — to take (carry) away; увозить — увезти — to take (haul) away; уводить — увести — to take (lead) away."),
  NOTE("DLI, Lesson 79."),
  P("Prepositions of location and direction: Куда? — иду в магазин, на вокзал (acc.); к доктору (dat.). Где? — был в магазине, на вокзале (loc.); у доктора (gen.). Откуда? — иду из магазина, с вокзала (gen.); от доктора (gen.). "
    "Adverbs: Куда? сюда, туда, домой. Где? здесь, тут, там, дома. Откуда? отсюда, оттуда, из дому."),
  NOTE("DLI, Lesson 29."),
])

S11 = prefix_section("m11-pod-ot", "под- and от-: up to, and away from", "подойти к столу · отойти от окна · отнести письмо на почту · подвезти", [
    ("подойти", "подходить"), ("подъехать", "подъезжать"), ("подлететь", "подлетать"), ("подбежать", "подбегать"), ("подплыть", "подплывать"), ("поднести", "подносить"), ("подвести", "подводить"), ("подвезти", "подвозить"),
    ("отойти", "отходить"), ("отъехать", "отъезжать"), ("отлететь", "отлетать"), ("отбежать", "отбегать"), ("отплыть", "отплывать"), ("отнести", "относить"), ("отвести", "отводить"), ("отвезти", "отвозить"),
  ], [
  P("The preposition к (to, towards, in the direction of …) always requires the dative case and is widely used with verbs of motion (the so-called \"going verbs\"). a) After a verb of motion, к, followed by a noun denoting a person, indicates going to see that person at his place: Я иду к полковнику. (I am going to the Colonel; to the Colonel's — his office, home, place). "
    "b) After a verb of motion, к, followed by a noun denoting an object or a place, indicates motion toward that object or place: Студент идёт к доске. Самолёты летят к морю. Мы идём к реке (к озеру)."),
  P("Verbs of motion with the prefix под- denote approaching to an object, a place or a person and require the preposition к + dative case: Я подхожу к столу. Рядовой подходит к сержанту. Мы подъезжаем к городу. "
    "Verbs of motion with the prefix от- denote moving away from an object, a place or a person and require the preposition от + genitive case: Я отхожу от автомобиля. Студент отходит от учителя. Грузовик отъезжает от магазина."),
  NOTE("DLI, Lesson 29."),
  T(["prefix / primary meanings", "examples / additional meanings", "prepositional phrases"], [
    ["**под-, подо-** — Approach. Antonym: от-", "Он подошёл к девушке, чтобы спросить её номер. — He approached the girl to ask for her number. Other: Подвезти – give someone a lift: Он подвёз меня до центра. — He took me (as far as) downtown.", "к + dat.; до + gen."],
    ["**от-, ото-** — Withdrawal a short distance away. Antonym: под-", "Мальчик отошёл от незнакомца, который предложил ему конфеты. — The boy stepped back from the stranger who had offered him candy. Other: With transitive verbs, delivering or dropping something off (agent does not remain): Я отнесу книги в библиотеку, потом приду. — I'll drop the book off at the library, then come.", "от + gen."],
  ], row_heads=False),
  NOTE(WP),
  P("Подвозить — подвезти — to bring up to (by vehicle), to haul up to, to give a lift; относить — отнести — to take to (on foot); отвозить — отвезти — to take (haul) to; отводить — отвести — to take (lead) to. "
    "Note that the verbs \"относить\", \"отвозить\" and \"отводить\" are seldom used as opposites of the verbs with the prefix \"под-\". Their most common meaning is: \"to take an object (or person) to a certain place and leave it there\". Thus:"),
  EX(("Я отнёс письмо на почту.", "I took (on foot) the letter to the post office."), ("Я отвёз деньги в банк.", "I took (by vehicle) money to the bank."), ("Я отвёл сына в школу.", "I took (walked with) my son to school.")),
  NOTE("DLI, Lesson 79."),
])

S12 = prefix_section("m12-do", "до-: as far as, reaching", "дойти до угла · доехать до города · до + genitive", [
    ("дойти", "доходить"), ("доехать", "доезжать"), ("долететь", "долетать"), ("добежать", "добегать"), ("доплыть", "доплывать"), ("донести", "доносить"), ("довести", "доводить"), ("довезти", "довозить"),
  ], [
  P("\"Going verbs\" with prefix \"до-\" indicate motion up to a certain point and may mean: a) going as far as …; b) reaching of a destination. Я доехал до угла и повернул направо. (went as far as…) У меня было мало бензина, но я всё-таки доехал до города. (reached the destination) "
    "These verbs are always followed by the preposition до + Gen."),
  EX(("Мы обычно доходим до этой остановки, а дальше едем на трамвае.", "Imperfective, present"), ("Во время дождей вода доходила до нашего дома.", "past"), ("Зимой температура будет доходить до нуля.", "future"),
     ("Танки дошли до леса.", "Perfective, past"), ("Когда вы дойдёте до почты, поверните направо.", "future")),
  NOTE("DLI, Lesson 62."),
  T(["prefix / primary meanings", "examples / additional meanings", "prepositional phrases"], [
    ["**до-** — Reaching a limit or destination", "Пассажиры доехали до последней остановки и вышли из автобуса. — The passengers reached the last station and exited the bus. Other: Characterizing the duration of a journey, especially when it is long: Мы наконец доехали до дачи. — We finally reached the dacha.", "до + gen."],
  ], row_heads=False),
  NOTE(WP),
])

S13 = prefix_section("m13-pere", "пере-: across, and over to another place", "перейти через улицу · переехать в другой город · перевести, перенести", [
    ("перейти", "переходить"), ("переехать", "переезжать"), ("перелететь", "перелетать"), ("перебежать", "перебегать"), ("переплыть", "переплывать"), ("перенести", "переносить"), ("перевести", "переводить"), ("перевезти", "перевозить"),
  ], [
  P("The prefix \"пере-\" implies the following meanings: a) Going across or over something. In this case the verb is commonly followed by the preposition через + Acc. However, sometimes this preposition is omitted and the verb takes a direct object: Мы перешли через улицу. Мы перешли улицу. — We crossed the street. "
    "b) Moving from one place to another. In this case the verb may be followed by any preposition indicating motion to or from a place: Мы переехали на другую квартиру. — moved to … Мы переехали из города в деревню. — moved from … to …"),
  EX(("Студент переходит через улицу.", "Imperfective, present"), ("Танки медленно переходили через поле.", "past"), ("Мы будем переходить реку в этом месте.", "future"),
     ("Линдберг перелетел через Атлантический океан.", "Perfective, past"), ("Завтра мы переедем в наш новый дом.", "future")),
  NOTE("DLI, Lesson 62."),
  T(["prefix / primary meanings", "examples / additional meanings", "prepositional phrases"], [
    ["**пере-** — Movement across, from one point to another; through", "Утки переплыли реку. — The ducks swam across the river. Other: Changing residence: Я переехала в другой город. — I moved to another city.", "через + acc.; without preposition + acc."],
  ], row_heads=False),
  NOTE(WP),
  P("Переносить — перенести — to carry over (on foot), to move; to endure; перевозить — перевезти — to haul over, to move, to transport; переводить — перевести — to lead over; to transfer, to translate. Note the following meanings:"),
  EX(("Перенесите этот стол в мою комнату.", "to move"), ("В прошлом году я перенёс тяжёлую болезнь.", "to endure"), ("Мы перевозим боеприпасы со станции на склад.", "to transport"),
     ("Я перевёл детей через дорогу.", "to lead over (across)"), ("Меня перевели в другой полк.", "to transfer"), ("Я не могу перевести этого слова.", "to translate")),
  NOTE("DLI, Lesson 79."),
])

S14 = prefix_section("m14-pro", "про-: through, past, and a distance covered", "пройти мимо дома · проехать через лес · пройти два километра · провести время", [
    ("пройти", "проходить"), ("проехать", "проезжать"), ("пролететь", "пролетать"), ("пробежать", "пробегать"), ("проплыть", "проплывать"), ("пронести", "проносить"), ("провести", "проводить"), ("провезти", "провозить"),
  ], [
  P("The prefix \"про-\" implies the following meanings: a) Going through — через + Acc.: Мы проехали через лес. b) Passing by — мимо + Gen.: Мы прошли мимо вашего дома. c) Passing between — между + Instr.: Войска противника прошли между лесом и рекой. "
    "d) Covering a distance — verb + Acc.: Они прошли два километра. e) Passing (missing) a place or leaving it behind — verb + Acc.: Мы проехали нашу станцию. (missed it) Мы уже проехали этот город. (left it behind) "
    "Notice also the following expressions: Прошла неделя. — A week went by. Дождь прошёл. — The rain stopped."),
  NOTE("DLI, Lesson 62."),
  T(["prefix / primary meanings", "examples / additional meanings", "prepositional phrases"], [
    ["**про-** — Movement across, through, or past something", "Мы проехали через город. — We drove through the city. Мы прошли мимо станции метро. — We passed the metro station. Other: 1. Movement beyond one's destination (possibly unintentional): Я боюсь, что мы уже прошли магазин. — I'm afraid we already passed the store. 2. Movement forward with the distance covered specified: Вы проедете три остановки и выйдете из трамвая. — You'll go three stops and get off the tram.", "сквозь / через / в + acc.; мимо + gen.; without preposition"],
    ["**про-** (temporal) — Prolonged multidirectional movement, with multidirectional verb of motion", "Мы проходили по лесу весь день. — We walked around the woods all day.", "without prep + acc."],
  ], row_heads=False),
  NOTE(WP),
  P("Проводить — провести — to lead through, to spend (time), to lay (a road). Note the expression: \"проводить время\" — to spend the time."),
  EX(("Как вы проводите время?", "How do you spend your time?"), ("Я хорошо провёл время.", "I had a good time."), ("Мы провели в Европе два месяца.", "We spent two months in Europe."), ("В прошлом году здесь провели несколько новых дорог.", "They built several new roads here last year.")),
  NOTE("DLI, Lesson 79."),
])

S15 = prefix_section("m15-za", "за-: behind, and dropping in", "зайти за угол · зайти в магазин · зайти за книгой · забегать", [
    ("зайти", "заходить"), ("заехать", "заезжать"), ("залететь", "залетать"), ("забежать", "забегать"), ("заплыть", "заплывать"), ("занести", "заносить"), ("завести", "заводить"), ("завезти", "завозить"), ("залезть", "залезать"),
  ], [
  P("The prefix \"за-\" implies the following meaning: (a) Getting (disappearing) behind something — заходить, зайти за + Acc.: Солнце заходит за облака. Автомашина заезжает за дом. "
    "(b) Dropping in on somebody or stopping by at a certain place: заходить, зайти — в магазин, на почту, к учителю. (c) Dropping in or stopping by to fetch something or someone — заходить, зайти за + Instr.: Я зайду за вами. — I'll stop by to pick you up. Он зашёл за книгой. — He dropped in to pick up the book. "
    "Also note the combination of subparagraphs (b) and (c): Он зашёл ко мне за книгой. — He stopped by at my place to pick up the book. Я заехал на почту за письмами. — I stopped by at the post office to get my mail."),
  NOTE("DLI, Lesson 63."),
  T(["prefix / primary meanings", "examples / additional meanings", "prepositional phrases"], [
    ["**за-** — Movement behind an object; stopping off on the way", "Старушка зашла за угол и исчезла. — The old woman walked behind the corner and disappeared. Other: 1. Action performed on the way to a destination: По дороге домой я зашла в магазин за хлебом. — On the way home I stopped at the store for bread. 2. A short visit: Молодой человек часто заходит к маме. — The young man often stops by his mother's place. 3. Movement deep into something, at a great distance (inside, upwards or downwards): Мяч залетел на крышу дома. — The ball flew onto the roof of the house.", "в / на / за + acc.; к + dat.; за + inst."],
    ["**за-** (temporal) — Beginning of multidirectional movement, with multidirection verb of motion", "Она забегала по комнате. — She started running around the room.", "по + dat."],
  ], row_heads=False),
  NOTE(WP),
])

S16 = prefix_section("m16-s-raz", "с-: down, and together — раз-: apart", "сойти с горы · съехать с дороги · сойтись, разойтись · съехаться, разъехаться", [
    ("сойти", "сходить"), ("съехать", "съезжать"), ("слететь", "слетать"), ("сбежать", "сбегать"), ("снести", "сносить"), ("свести", "сводить"), ("свезти", "свозить"), ("слезть", "слезать"),
    ("сойтись", "сходиться"), ("съехаться", "съезжаться"), ("сбежаться", "сбегаться"), ("разойтись", "расходиться"), ("разъехаться", "разъезжаться"), ("разлететься", "разлетаться"), ("разбежаться", "разбегаться"),
    ("разнести", "разносить"), ("развести", "разводить"), ("развезти", "развозить"),
  ], [
  P("The prefix \"с-\" implies the following meanings: (a) to descend, to go down: Мы съезжаем с горы. Он сходит вниз по лестнице. (b) to come off, to drive off: Автомобиль съехал с дороги. Поезд сошёл с пути. "
    "Note that these verbs (сходить, съезжать, etc.) are usually followed by the preposition с + Gen."),
  NOTE("DLI, Lesson 63."),
  T(["prefix / primary meanings", "examples / additional meanings", "prepositional phrases"], [
    ["**с-, со-** — Movement downwards. Antonym: вз-", "После представления актёр сошёл со сцены. — After the performance, the actor got off the stage.", "с + gen.; на + acc.; к + dat.; за + inst."],
    ["**с-, со- (+сь, +ся)** — Convergent movement from various directions towards one center. Antonym: раз-, разо-, рас- (+сь, +ся)", "Чтобы заниматься, студентка снесла все учебники из других комнат на письменный стол. — In order to study, the student brought all her textbooks from other rooms to her desk. Дети сбежались на детскую площадь. — The children ran (from all directions) to the playground.", "в / на + acc.; к + dat."],
    ["**раз-, разо-, рас- (+сь, +ся)** — Divergent movement in various directions from one center. Antonym: с-, со- (+сь, +ся)", "Дед Мороз разнёс подарки по домам. — Grandfather Frost brought the gifts to the (various) houses. После ужина, мы разошлись по домам. — After dinner, we went to our separate homes.", "по + dat. pl.; в + acc. pl."],
    ["**с-** (resultative) — Completed semelfactive movement in opposite directions, there and back; only formed with multidirectional verb of motion", "Я сходил в аптеку за лекарством и лёг спать. — I went to the pharmacy for medicine and went to bed.", "в / на + acc.; к + dat."],
  ], row_heads=False),
  NOTE(WP),
  P("Wiktionary's two entries for «сходить»: %s — %s; %s — %s." % (
      (entry("сходить", "impf") or {}).get("head", ""), defs("сходить", 2, "impf"), (entry("сходить", "pf") or {}).get("head", ""), defs("сходить", 2, "pf"))),
  cite("сходить"),
])

S17 = prefix_section("m17-ob-iz", "об-: around — из-: all over", "обойти лужу · объехать вокруг озера · обойти все магазины · изъездить весь мир", [
    ("обойти", "обходить"), ("объехать", "объезжать"), ("облететь", "облетать"), ("обежать", "обегать"), ("обнести", "обносить"), ("обвести", "обводить"), ("оплыть", "оплывать"),
    ("исходить", "исходить"), ("изъездить", "изъездить"),
  ], [
  P("The prefix \"об-\" indicates a motion around a place and may mean: a) Circling a place. The verb is followed by the preposition вокруг + Gen.: Самолёт облетел вокруг аэродрома. Я хочу объехать вокруг озера. "
    "b) Making a detour. No preposition is used; the verb is followed by the Accusative case: Мы объехали это место. Противник обошёл наш город. "
    "c) Making the rounds of … or going all over … No preposition is used; the verb is followed by the Accusative case: Я обошёл все магазины. — I made the rounds of all the stores. Я обошёл весь город. — I walked all over town."),
  NOTE("DLI, Lesson 62."),
  T(["prefix / primary meanings", "examples / additional meanings", "prepositional phrases"], [
    ["**о-, об-, обо-** — Movement around an object or involving a consecutive number of objects, circling, covering a whole place", "Девочка обошла лужу. — The little girl walked around the puddle. Я обхожу все магазины в центре. — I'm going around to all the stores in the mall.", "вокруг + gen.; without preposition + acc."],
    ["**из-, изо-, ис-** — Movement involving the entire area concerned and carried out in all directions; only formed from multidirectional verb of motion", "Я изъездил весь мир. — I traveled over the whole world.", "without preposition + acc."],
  ], row_heads=False),
  NOTE(WP),
])

S18 = prefix_section("m18-vz-na", "вз- (вс-): up — на-: onto, and a quantity covered", "взойти на гору · взлететь · всплыть · наехать на · налетать 2500 часов", [
    ("взойти", "всходить"), ("взлететь", "взлетать"), ("взбежать", "взбегать"), ("всплыть", "всплывать"), ("взвести", "взводить"),
    ("наехать", "наезжать"), ("налететь", "налетать"), ("набежать", "набегать"), ("наплыть", "наплывать"), ("нанести", "наносить"), ("навести", "наводить"), ("наползти", "наползать"),
  ], [
  T(["prefix / primary meanings", "examples / additional meanings", "prepositional phrases"], [
    ["**вз-, взо-, воз-, вс-, вос-** — Movement upwards. Antonym: с-", "Альпинист взошёл на гору. — The mountain climber walked up the mountain.", "в / на + acc."],
    ["**на-** — Movement onto the surface of an object; only formed from multidirectional verb of motion", "Туча наползла на солнце. — A cloud crept onto the sun. Other: Quantified movement: Водитель наездил 50 километров. — The driver covered 50 kilometers. Я налетал 2500 часов на Боинге 737. — I had 2500 flight hours in Boeing 737.", "в/на + acc.; without preposition + acc."],
  ], row_heads=False),
  NOTE(WP),
  P("Temporal and resultative prefixes, from the same table: по- — Beginning of unidirectional movement, with unidirectional verb of motion: Я пошла в университет. — I went to the university. Other: 1. Intention to carry out a movement in the future: Зимой я собираюсь поехать во Флориду. — In the winter I plan to go to Florida. 2. Approximate location of the agent at moment of speech: Где папа? Он пошёл на работу. — Where's Dad? He went to (is at) work. "
    "по- — Slow and measured multidirectional movement, with multidirectional verb of motion: Она задумчиво походила по квартире и наконец решила уйти. — She walked around the apartment pensively and finally decided to leave."),
  NOTE(WP),
])

ex, more = drills("m19-aspect")
S19 = SEC("m19-aspect", "Perfective or imperfective? The prefixed verbs in use", sub="пришёл or приходил · imperfective for habit and for what is under way · perfective for the one completed act", blocks=[
  P("Motion verbs combine with prefixes to form new aspectual pairs, which lose the distinction of directionality, but gain spatial or temporal meanings. The unidirectional verb serves as the base for the perfective, and the multidirectional as the base for the imperfective."),
  NOTE(WP),
  P("Any prefix (except \"по-\"), added to the imperf. pair of \"going verbs\" (to both, repeated and actual functions), makes them an ordinary imperfective-perfective pair."),
  EX(("Он всегда приезжает сюда на грузовике.", "Imperfective: always"), ("Он всегда приезжал сюда на грузовике.", ""), ("Он всегда будет приезжать сюда на грузовике.", ""),
     ("Сегодня он приехал сюда на автобусе.", "Perfective: today, once"), ("Сегодня он приедет сюда на автобусе.", ""),
     ("Я вхожу в эту комнату каждый день.", "Imperfective"), ("Я вошёл в комнату и открыл окно.", "Perfective"), ("Я войду в комнату и открою окно.", "")),
  NOTE("DLI, Lesson 56."),
  P("Note. — The verbs приходить and приезжать usually refer to the habitual or repeated actions: Он приходит (приезжает) сюда каждый день. — He comes here every day. These verbs, as the other verbs of motion, may be used to express a single action in the future: Он приходит на работу завтра утром. — He is coming to work tomorrow morning. "
    "Приходить and приезжать are not used to denote an action in progress."),
  NOTE("DLI, Lesson 24."),
  EX(("Мы обычно доходим до этой остановки, а дальше едем на трамвае.", "imperfective, present"), ("Во время дождей вода доходила до нашего дома.", "imperfective, past"),
     ("Танки дошли до леса.", "perfective, past"), ("Когда вы дойдёте до почты, поверните направо.", "perfective, future"),
     ("Студент переходит через улицу.", "imperfective, present"), ("Танки медленно переходили через поле.", "imperfective, past"), ("Линдберг перелетел через Атлантический океан.", "perfective, past")),
  NOTE("DLI, Lesson 62."),
  P("Imperatives: Приходите сюда завтра! — Come here tomorrow! Идите сюда! — Come here! (DLI, Lesson 24.) The Imperative is: идите! — (не) ходите! — пойдите! (DLI, Lesson 54.)"),
], exercises=ex, more=more)

ex, more = drills("m20-prefixed-idioms")
S20 = SEC("m20-prefixed-idioms", "Prefixed verbs beyond motion", sub="провести время · перевести слово · перенести болезнь · сойти с ума · привести пример · довести до", blocks=[
  P("The verbs \"носить\", \"возить\" and \"водить\" have basically the same prefixes as the verbs of motion we have studied previously with corresponding changes in meaning. However, many of the prefixed verbs have also secondary meanings, some of which are more important than the basic meanings."),
  EX(("В прошлом году я перенёс тяжёлую болезнь.", "перенести — to endure"), ("Меня перевели в другой полк.", "перевести — to transfer"), ("Я не могу перевести этого слова.", "перевести — to translate"),
     ("Как вы проводите время?", "проводить время — to spend the time"), ("Я хорошо провёл время.", "I had a good time."), ("В прошлом году здесь провели несколько новых дорог.", "провести — to lay (a road)")),
  NOTE("DLI, Lesson 79."),
  P("Notice also the following expressions: Прошла неделя. — A week went by. Дождь прошёл. — The rain stopped."),
  NOTE("DLI, Lesson 62."),
  P("Other meanings from the prefix table: вы- — Step out for a short period of time: Секретарь вышел на десять минут. — The secretary left for ten minutes. под- — Подвезти – give someone a lift: Он подвёз меня до центра. — He took me (as far as) downtown. "
    "от- — With transitive verbs, delivering or dropping something off (agent does not remain): Я отнесу книги в библиотеку, потом приду. — I'll drop the book off at the library, then come. "
    "до- — Characterizing the duration of a journey, especially when it is long: Мы наконец доехали до дачи. — We finally reached the dacha. пере- — Changing residence: Я переехала в другой город. — I moved to another city. "
    "про- — Movement beyond one's destination (possibly unintentional): Я боюсь, что мы уже прошли магазин. — I'm afraid we already passed the store. на- — Quantified movement: Водитель наездил 50 километров. — The driver covered 50 kilometers."),
  NOTE(WP),
  T(["verb", "Wiktionary's definitions"], [
    ["**провести / проводить**", defs("провести", 4)], ["**перевести / переводить**", defs("перевести", 4)], ["**перенести / переносить**", defs("перенести", 4)],
    ["**привести / приводить**", defs("привести", 4)], ["**довести / доводить**", defs("довести", 3)], ["**завести / заводить**", defs("завести", 4)],
    ["**нанести / наносить**", defs("нанести", 3)], ["**сойти / сходить**", defs("сойти", 4)], ["**обойтись / обходиться**", defs("обойти", 3)], ["**выйти / выходить**", defs("выйти", 4)],
  ], row_heads=False),
  cite("провести", "перевести", "перенести", "привести", "довести", "завести", "нанести", "сойти", "обойти", "выйти"),
], exercises=ex, more=more)

ex, more = drills("m21-which-prefix")
S21 = SEC("m21-which-prefix", "Which prefix? — the whole table, as practice", sub="в-, вы-, при-, у-, под-, от-, до-, пере-, про-, за-, с-, об-", blocks=[
  P("See below for a table the prefixes, their primary meanings, and the prepositions that accompany them, adapted from Muravyova."),
  T(["prefix", "primary meaning", "prepositions"], [
    ["в-, во-", "Movement inwards across a threshold, entering. Antonym: вы-", "в / на + acc."],
    ["вы-", "Movement out of something across a threshold, exiting. Antonym: в-", "из / с / от + gen.; в / на + acc.; к + dat."],
    ["при-", "Intended arrival, signals presence of the agent at a location as a result of motion. Antonym: у-", "в / на + acc.; к + dat.; из / с / от + gen."],
    ["у-", "Intended departure, signals absence. Antonym: при-", "в / на + acc.; к + dat.; из / с / от + gen."],
    ["под-, подо-", "Approach. Antonym: от-", "к + dat.; до + gen."],
    ["от-, ото-", "Withdrawal a short distance away. Antonym: под-", "от + gen."],
    ["до-", "Reaching a limit or destination", "до + gen."],
    ["за-", "Movement behind an object; stopping off on the way", "в / на / за + acc.; к + dat.; за + inst."],
    ["про-", "Movement across, through, or past something", "сквозь / через / в + acc.; мимо + gen.; without preposition"],
    ["пере-", "Movement across, from one point to another; through", "через + acc.; without preposition + acc."],
    ["вз-, взо-, воз-, вс-, вос-", "Movement upwards. Antonym: с-", "в / на + acc."],
    ["с-, со-", "Movement downwards. Antonym: вз-", "с + gen.; на + acc.; к + dat.; за + inst."],
    ["о-, об-, обо-", "Movement around an object or involving a consecutive number of objects, circling, covering a whole place", "вокруг + gen.; without preposition + acc."],
    ["из-, изо-, ис-", "Movement involving the entire area concerned and carried out in all directions", "without preposition + acc."],
    ["на-", "Movement onto the surface of an object", "в/на + acc.; without preposition + acc."],
    ["с-, со- (+сь, +ся)", "Convergent movement from various directions towards one center. Antonym: раз-, разо-, рас- (+сь, +ся)", "в / на + acc.; к + dat."],
    ["раз-, разо-, рас- (+сь, +ся)", "Divergent movement in various directions from one center. Antonym: с-, со- (+сь, +ся)", "по + dat. pl.; в + acc. pl."],
    ["по-", "Beginning of unidirectional movement (with unidirectional verb of motion)", "в / на + acc.; к + dat.; из / с / от + gen.; по + dat."],
  ], caption="Prefixed verbs of motion", row_heads=False),
  NOTE(WP),
], exercises=ex, more=more)

SECTIONS = [S08, S09, S10, S11, S12, S13, S14, S15, S16, S17, S18, S19, S20, S21]
