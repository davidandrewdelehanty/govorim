# DLI Basic Russian Grammar, part E (Grammar Reference Book II, lessons 66–80).
from kit import *

SECTIONS = [

SEC("d29-ca-verbs", "More -ся verbs: meeting, marrying, each other", sub="Lessons 66–68 · встречаться · знакомиться · бояться · жениться, выйти замуж", blocks=[
  P("**-ся** does several jobs:"),
  T(["Kind", "Examples"], [
    ["**Reflexive** — onto oneself", "мы́ться, бри́ться, одева́ться — *wash, shave, dress (oneself)*"],
    ["**Reciprocal** — each other", "встреча́ться, знако́миться, здоро́ваться, целова́ться — *meet, get acquainted, greet, kiss (each other)*"],
    ["**Intransitive** — no object", "начина́ться, конча́ться, открыва́ться — *begin, end, open*"],
    ["**Never without -ся**", "боя́ться (*fear* + gen.), смея́ться (*laugh*), стара́ться (*try*), нра́виться (*please*)"],
  ]),
  EX(("Мы встречаемся в шесть.", "We're meeting at six."), ("Познакомьтесь, это моя жена.", "Let me introduce you — this is my wife."), ("Я боюсь собак.", "I'm afraid of dogs. (бояться + genitive)")),
  H("Getting married"),
  T(["", "Getting married", "Being married"], [
    ["A man", "**жени́ться на** + prep. — *Он женился на Анне.*", "**жена́т** — *Он женат.*"],
    ["A woman", "**вы́йти за́муж за** + acc. — *Она вышла замуж за Ивана.*", "**за́мужем** — *Она замужем.*"],
    ["A couple", "**пожени́ться** — *Они поженились.*", "—"],
  ]),
], exercises=[
  FILL("Мы ___ в кафе. (встречаться)", ["встречаемся"], "мы → **встречаемся**."),
  FILL("Я ___ темноты. (бояться — I'm afraid of)", ["боюсь"], "**Бояться**: я **боюсь**."),
  FILL("Он ___ каждое утро. (бриться)", ["бреется"], "**Бриться**: он **бреется**."),
  MC("*Иван ___ на Марии.*", ["женился", "вышел замуж", "поженился"], 0, "A man **женится на** + prepositional."),
  MC("*Мария вышла замуж ___ Ивана.*", ["на", "за", "с"], 1, "**выйти замуж за** + accusative."),
  MC("*Is she married?*", ["Она жената?", "Она замужем?"], 1, "A woman is **замужем**."),
  MC("*Дети ___ над клоуном.* (laugh)", ["смеются", "смеют"], 0, "**Смеяться** always has -ся."),
  FILL("Я ___ говорить медленно. (стараться — I try)", ["стараюсь"], "я → **стараюсь**."),
]),

SEC("d30-positions", "Sitting down, lying down, standing up", sub="Lessons 68–70 · сидеть / садиться / сесть · лежать / ложиться / лечь · стоять / вставать / встать", blocks=[
  P("Russian separates **being in a position** from **getting into it**:"),
  T(["Being (impf.)", "Getting into it: impf.", "Getting into it: pf.", "Where? / Where to?"], [
    ["сиде́ть — be sitting", "сади́ться", "сесть (ся́ду, ся́дешь; сел)", "сидеть **на сту́ле** / сесть **на стул**"],
    ["лежа́ть — be lying", "ложи́ться", "лечь (ля́гу, ля́жешь; лёг)", "лежать **на дива́не** / лечь **на дива́н**"],
    ["стоя́ть — be standing", "встава́ть", "встать (вста́ну; встал)", "стоять **у окна́** / встать **у окна́**"],
  ]),
  P("Being: **where?** + prepositional. Getting into: **where to?** + accusative. *Он **сел** за стол* — *he sat down at the table*; *Он **сидит** за столом* — *he is sitting at the table*."),
  H("Stopping and raising"),
  P("Transitive and **-ся** pairs: **останови́ть** машину (*stop the car*) / машина **останови́лась** (*the car stopped*); **подня́ть** руку (*raise a hand*) / **подня́ться** на пятый этаж (*go up*); **разде́ть** ребёнка / **разде́ться** (*undress*)."),
], exercises=[
  MC("*Садитесь, пожалуйста!* means…", ["Please stay seated.", "Please sit down.", "Please stand up."], 1, "**Садиться** — to sit down."),
  MC("*Он ___ на диване и читает.* (is lying)", ["лежит", "ложится", "лёг"], 0, "A state → **лежит**."),
  MC("*Вечером он ___ на диван.* (lay down)", ["лежал", "лёг"], 1, "Getting into the position → **лёг**."),
  MC("*Она села ___ стул.*", ["на", "на стуле"], 0, "*Sat down onto* → **на** + accusative (стул)."),
  FILL("Во сколько ты ___ ? (вставать — when do you get up?)", ["встаёшь", "встаешь"], "ты → **встаёшь**."),
  FILL("Я ___ спать в одиннадцать. (ложиться)", ["ложусь"], "я → **ложусь**."),
  FILL("Автобус ___ у школы. (остановиться — stopped)", ["остановился"], "Masculine past → **остановился**."),
  MC("*Он ___ руку.* (raised)", ["поднял", "поднялся"], 0, "With an object → **поднял**."),
]),

SEC("d31-numerals", "Numbers in every case", sub="Lessons 69–73 · один, два, пять in all cases · двое, трое · полтора · about ten", blocks=[
  P("Numbers decline. In the nominative and accusative (for things) they govern the noun as you know; in **every other case**, the number and noun simply both go into that case:"),
  EX(("У меня пять книг.", "Nominative: пять + genitive plural."), ("Я говорил с пятью студентами.", "Instrumental: both instrumental."), ("в двух домах", "Prepositional: both prepositional.")),
  T(["", "два / две", "три", "четы́ре", "пять"], [
    ["Nom.", "два, две", "три", "четы́ре", "пять"], ["Gen.", "двух", "трёх", "четырёх", "пяти́"], ["Dat.", "двум", "трём", "четырём", "пяти́"],
    ["Instr.", "двумя́", "тремя́", "четырьмя́", "пятью́"], ["Prep.", "о двух", "о трёх", "о четырёх", "о пяти́"],
  ]),
  P("**Пять** to **два́дцать** and **три́дцать** decline like **тетра́дь**: пяти́, пятью́. With **два, три, четыре**, an adjective goes in the **genitive plural**: **два но́вых** стола́; with feminine nouns usually nominative plural: **две но́вые** кни́ги."),
  H("About — and in groups"),
  P("Put the noun **before** the number to make it approximate: **лет пять** — *about five years*, **часа́ через два** — *in about two hours*."),
  P("**Дво́е, тро́е, че́тверо** (+ genitive plural) count people and pairs: **у них дво́е дете́й**; **нас бы́ло тро́е**. **Полтора́** (m./n.) / **полторы́** (f.) — *one and a half* + genitive singular: полтора́ часа́, полторы́ неде́ли."),
], exercises=[
  FILL("Я был в ___ городах. (два — prepositional)", ["двух"], "Prepositional → **двух**."),
  FILL("Он работает с ___ друзьями. (три — instrumental)", ["тремя"], "Instrumental → **тремя**."),
  FILL("Мы ждали около ___ часов. (пять — genitive)", ["пяти"], "Genitive → **пяти**."),
  MC("*два ___ дома*", ["новые", "новых", "новый"], 1, "Masculine with 2–4: adjective genitive plural → **новых**."),
  MC("*Мы ждали ___ .* (about two hours)", ["два часа", "часа два", "два часов"], 1, "Noun before the number makes it approximate: **часа два**."),
  MC("*У них ___ детей.* (two)", ["два", "двое", "двух"], 1, "Children are counted with **двое**."),
  FILL("___ часа (one and a half)", ["полтора"], "**Час** is masculine → **полтора**."),
  FILL("___ недели (one and a half)", ["полторы"], "**Неделя** is feminine → **полторы**."),
]),

SEC("d32-fractions", "Ordinals, fractions, equal to", sub="Lessons 73–75 · ordinals · половина, треть, четверть · часть · равен", blocks=[
  P("Ordinals are adjectives: **пе́рвый, второ́й, тре́тий, четвёртый, пя́тый, шесто́й, седьмо́й, восьмо́й, девя́тый, деся́тый … двадца́тый, сто́тый**. In compounds, only the last word is ordinal: **два́дцать пе́рвый** (21st)."),
  T(["Fraction", "Russian"], [
    ["½", "полови́на (+ gen.) — *полови́на дня*"], ["⅓", "треть"], ["¼", "че́тверть — *че́тверть ча́са*"],
    ["⅔", "две тре́ти"], ["¾", "три че́тверти"], ["0.5", "ноль це́лых пять деся́тых"],
  ]),
  P("**Часть** — *part, a share*: **бо́льшая часть** студентов — *most of the students*."),
  P("**Ра́вен** (ра́вна, ра́вно, ра́вны) — *equals*, with the dative: **Два плюс два ра́вно четырём.** In everyday speech: *Два плюс два — четыре.*"),
  P("**Ско́лько, не́сколько** decline too: gen. **ско́льких, не́скольких**; *в нескольких городах*."),
], exercises=[
  FILL("Это мой ___ раз в Москве. (second)", ["второй"], "**Второй**."),
  FILL("Мы живём на ___ этаже. (seventh — prepositional)", ["седьмом"], "Prepositional m. → **седьмом**."),
  FILL("Я ждал ___ часа. (a quarter of an hour)", ["четверть"], "**четверть часа**."),
  FILL("Он съел ___ торта. (half)", ["половину"], "Accusative of **половина** → **половину**."),
  MC("*Три плюс два равно ___.*", ["пять", "пяти"], 1, "**равно** + dative → **пяти**."),
  MC("*21st* (m.)", ["двадцатый первый", "двадцать первый", "двадцать один"], 1, "Only the last part is ordinal."),
  MC("*Большая ___ студентов живёт в общежитии.*", ["часть", "половина", "часов"], 0, "**Большая часть** — most of."),
]),

SEC("d33-time", "Telling the time and when things happen", sub="Lessons 74–78 · в, на, до in time expressions · hours and minutes · dates in full", blocks=[
  T(["When?", "Case", "Example"], [
    ["Days of the week", "**в** + acc.", "в понеде́льник, в сре́ду"], ["Months, years", "**в** + prep.", "в январе́, в 1970 (семидеся́том) году́"],
    ["Weeks", "**на** + prep.", "на э́той / про́шлой / сле́дующей неде́ле"], ["Times of day", "instrumental", "у́тром, ве́чером"],
    ["Hours", "**в** + acc.", "в два часа́, в пять мину́т тре́тьего"], ["Before", "**до** + gen. / **за** + acc. **до**", "до обе́да; за час до обе́да (an hour before)"],
    ["Ago", "acc. + **наза́д**", "два го́да наза́д"], ["In (from now)", "**че́рез** + acc.", "че́рез неде́лю"],
  ]),
  H("What time is it?"),
  L("**Ско́лько сейча́с вре́мени? / Кото́рый час?** — What time is it?",
    "**Час. Два часа́. Пять часо́в.**",
    "Past the hour, Russians count *into the next* hour: 2:10 — **де́сять мину́т тре́тьего** (*ten minutes of the third*); 2:30 — **полови́на тре́тьего** or **полтре́тьего**.",
    "To the hour: 2:50 — **без десяти́ три** (*three without ten*); 2:45 — **без че́тверти три**.",
    "Officially: **четы́рнадцать со́рок** — 14:40."),
  P("A complete date: **Он роди́лся пя́того ма́рта ты́сяча девятьсо́т со́рок второ́го го́да** — *on 5 March 1942* (day and year in the genitive)."),
], exercises=[
  MC("*___ среду*", ["в", "на", "во"], 0, "Days: **в** + acc. (но *во вторник*)."),
  MC("*___ прошлой неделе*", ["в", "на"], 1, "Weeks: **на** + prep."),
  FILL("Мы приехали в ___ . (июль — prepositional)", ["июле"], "Months: **в** + prepositional."),
  FILL("Это было три года ___ . (ago)", ["назад"], "**наза́д**."),
  MC("**3:30** in words:", ["половина третьего", "половина четвёртого", "три с половиной"], 1, "Count into the next hour: **половина четвёртого**."),
  MC("**4:50** in words:", ["без десяти пять", "пятьдесят минут четвёртого", "без десяти четыре"], 0, "**Без десяти пять**."),
  MC("**1:15** in words:", ["четверть первого", "четверть второго", "пятнадцать первого"], 1, "**Четверть второго** — a quarter into the second hour."),
  FILL("Урок начнётся через ___ . (минута — accusative)", ["минуту"], "**через** + accusative."),
]),

SEC("d34-carrying", "Carrying, leading, transporting, running, swimming", sub="Lessons 76–82 · нести / носить · вести / водить · везти / возить · бежать / бегать · плыть / плавать", blocks=[
  P("Like **идти / ходить**, these come in **one-way** and **multi-way** pairs:"),
  T(["", "One way, now", "Many ways, habitual", "Means"], [
    ["", "**нести́** (несу́, несёшь; нёс)", "**носи́ть** (ношу́, но́сишь)", "carry (on foot); wear (носить)"],
    ["", "**вести́** (веду́, ведёшь; вёл)", "**води́ть** (вожу́, во́дишь)", "lead, take (a person on foot); drive (a car — водить)"],
    ["", "**везти́** (везу́, везёшь; вёз)", "**вози́ть** (вожу́, во́зишь)", "transport (by vehicle)"],
    ["", "**бежа́ть** (бегу́, бежи́шь, бегу́т)", "**бе́гать** (бе́гаю)", "run"],
    ["", "**плыть** (плыву́, плывёшь)", "**пла́вать** (пла́ваю)", "swim, sail"],
  ], row_heads=False),
  EX(("Я несу́ сумку домой.", "I'm carrying the bag home."), ("Мама ведёт сына в школу.", "Mum is taking her son to school."), ("Он хорошо водит машину.", "He drives well."), ("Она носит очки.", "She wears glasses."), ("Ты умеешь плавать?", "Can you swim?")),
  P("Prefixes work as with **идти**: **принести́** (*bring*), **привести́** (*bring a person*), **привезти́** (*bring by vehicle*), **унести́** (*take away*)…"),
  P("Words built on **дава́ть / дать**: **передава́ть** (*pass on*), **продава́ть** (*sell*), **издава́ть** (*publish*), **сдава́ть экза́мен** (*take an exam*) / **сдать** (*pass it*)."),
], exercises=[
  MC("*Смотри, он ___ большой чемодан.* (is carrying, now)", ["несёт", "носит"], 0, "One way, now → **несёт**."),
  MC("*Она всегда ___ красную шапку.* (wears)", ["несёт", "носит"], 1, "*Wear* → **носит**."),
  MC("*Отец ___ детей в парк.* (is taking, on foot)", ["ведёт", "везёт"], 0, "Leading people on foot → **ведёт**."),
  MC("*Поезд ___ туристов в Москву.*", ["ведёт", "везёт"], 1, "By vehicle → **везёт**."),
  MC("*Ты умеешь ___ машину?* (drive)", ["водить", "вести", "ехать"], 0, "*Drive a car* → **водить машину**."),
  FILL("Я ___ каждое утро в парке. (бегать)", ["бегаю"], "я → **бегаю**."),
  FILL("___ мне, пожалуйста, воды. (принести — bring)", ["Принеси", "Принесите"], "Imperative of **принести**."),
  FILL("Вчера я ___ экзамен. (сдать — passed; a man)", ["сдал"], "**сдал** — passed."),
]),

SEC("d35-comparison", "Comparing", sub="Lessons 82–86 · больше, лучше · чем · самый, -ейший · всех, всего", blocks=[
  P("The simple comparative ends in **-ее** and never changes: **но́вый → нове́е**, **интере́сный → интере́снее**, **бы́стро → быстре́е**."),
  T(["Positive", "Comparative", ""], [
    ["хоро́ший, хорошо́", "**лу́чше**", "better"], ["плохо́й, пло́хо", "**ху́же**", "worse"], ["большо́й, мно́го", "**бо́льше**", "bigger, more"],
    ["ма́ленький, ма́ло", "**ме́ньше**", "smaller, less"], ["молодо́й", "**моло́же**", "younger"], ["ста́рый", "**ста́рше**", "older"],
    ["высо́кий", "**вы́ше**", "taller"], ["дорого́й", "**доро́же**", "dearer"], ["дешёвый", "**деше́вле**", "cheaper"], ["бли́зкий", "**бли́же**", "nearer"],
  ]),
  P("*Than*: **чем** — or put the second thing in the **genitive**: *Москва больше, **чем** Киев* = *Москва больше **Киева***. **Ста́рший** and **мла́дший** mean *elder, younger (brother, sister)* and *senior, junior (rank)*. **По-** softens: **побольше** — *a bit more*."),
  H("The most"),
  L("**са́мый** + adjective: **са́мый интере́сный** фильм — the most interesting film",
    "**-ейший / -айший**, bookish, often *extremely*: **нове́йший**, **важне́йший**, **ближа́йший** (the nearest)",
    "comparative + **всех / всего́**: Он бе́гает **быстре́е всех**. *He runs fastest (of all).* Я люблю́ э́то **бо́льше всего́**. *I like this most of all.*"),
], exercises=[
  FILL("Эта книга ___ , чем та. (интересный)", ["интереснее"], "**-ее**."),
  FILL("Сегодня погода ___ , чем вчера. (хороший)", ["лучше"], "**лучше**."),
  FILL("Мой брат ___ меня. (старый — older)", ["старше"], "**старше**."),
  MC("*Москва больше ___ .*", ["Петербург", "Петербурга", "чем Петербурга"], 1, "Without **чем** → genitive: **Петербурга**."),
  MC("*Это ___ высокое здание в городе.*", ["самое", "самый", "больше"], 0, "**Самое** agrees with neuter **здание**."),
  FILL("Он говорит по-русски лучше ___ . (of all)", ["всех"], "**лучше всех** — better than everyone."),
  MC("*my younger sister*", ["моя молодая сестра", "моя младшая сестра", "моя моложе сестра"], 1, "**Младшая** — younger (sibling)."),
  FILL("Говорите, пожалуйста, ___ . (медленно — more slowly)", ["медленнее"], "**медленнее**."),
]),

]
