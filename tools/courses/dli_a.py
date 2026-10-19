# DLI Basic Russian Grammar, part A (Grammar Reference Book I, lessons 12–19).
# Written for this site, following the topics and order of the Defense
# Language Institute Russian Basic Course, Grammar Reference Book (1970),
# a US Government work.
from kit import *

SECTIONS = [

SEC("d01-gender", "Gender, это and вот", sub="Lesson 12 · gender · agreement · это · вот", blocks=[
  P("Every Russian noun has a gender, and the last letter usually tells you which: a **consonant** — masculine (стол); **-а, -я** — feminine (ка́рта, ку́хня); **-о, -е** — neuter (окно́, по́ле, зда́ние). Nouns in **-ь** must be memorised: masculine **слова́рь, автомоби́ль, день, учи́тель**; feminine **тетра́дь, дверь**."),
  NOTE("**И́мя** (*name*) ends in -я but is neuter: **моё** имя. So is **вре́мя** (*time*)."),
  P("Words that go with a noun **agree** with its gender: **мой** стол, **моя́** ка́рта, **моё** окно́; **твой** каранда́ш, **твоя́** кни́га, **твоё** письмо́."),
  H("это and вот"),
  P("**Э́то** introduces something — *this is, that is, it is* — and never changes: **Это** стол. **Это** ка́рта. **Это** окно́. **Вот** points something out — *here is, there is*: **Вот** мой каранда́ш. *Here's my pencil.*"),
  EX(("Что это? — Это словарь.", "What is this? — It's a dictionary."), ("Где твоя книга? — Вот она.", "Where's your book? — Here it is.")),
], exercises=[
  MC("What gender is **словарь**?", ["masculine", "feminine", "neuter"], 0, "One to memorise: **словарь** is masculine."),
  MC("What gender is **тетрадь**?", ["masculine", "feminine", "neuter"], 1, "**Тетрадь** — feminine."),
  MC("What gender is **здание**?", ["masculine", "feminine", "neuter"], 2, "Ends in **-е** — neuter."),
  MC("What gender is **имя**?", ["masculine", "feminine", "neuter"], 2, "An exception: **имя** is neuter."),
  FILL("___ автомобиль (my)", ["мой"], "**Автомобиль** is masculine → **мой**."),
  FILL("___ дверь (your — informal)", ["твоя"], "**Дверь** is feminine → **твоя**."),
  FILL("___ поле (my)", ["моё", "мое"], "Neuter → **моё**."),
  MC("*___ мой дом.* (Here's my house.)", ["Это", "Вот"], 1, "Pointing out: **вот**."),
]),

SEC("d02-plurals", "Plurals, его, её, их", sub="Lesson 13 · plural · agreement in number · они оба", blocks=[
  T(["Singular", "Plural", "Rule"], [
    ["стол, журна́л", "стол**ы́**, журна́л**ы**", "consonant **+ы**"],
    ["ка́рта", "ка́рт**ы**", "**-а → -ы**"],
    ["слова́рь, дверь, ку́хня, музе́й", "словар**и́**, две́р**и**, ку́хн**и**, музе́**и**", "**-ь, -я, -й → -и**"],
    ["окно́, по́ле", "о́кн**а**, пол**я́**", "**-о → -а, -е → -я**"],
    ["кни́га, каранда́ш", "кни́г**и**, карандаш**и́**", "after г к х ж ч ш щ: **-и**"],
  ]),
  P("Plurals agree, but have one form for all genders: **мои́** кни́ги, **мои́** столы́, **твои́** о́кна. **Это** stays the same: *Это мои книги* — *These are my books*."),
  H("его, её, их"),
  P("**Его́** (*his, its*), **её** (*her*), **их** (*their*) never change: его стол, его карта, его окна. In **его** the **г** is said like **в** — [yevó]."),
  H("они оба, они обе"),
  P("*Both* is **о́ба** with masculine and neuter nouns, **о́бе** with feminine: *Где карандаши?* — *Они оба здесь.* *Где карты?* — *Они обе там.*"),
], exercises=[
  FILL("журнал → ___", ["журналы"], "**+ы**.", prompt="Plural:"),
  FILL("кухня → ___", ["кухни"], "**-я → -и**.", prompt="Plural:"),
  FILL("поле → ___", ["поля"], "**-е → -я**.", prompt="Plural:"),
  FILL("карандаш → ___", ["карандаши"], "After **ш**, **-и**.", prompt="Plural:"),
  FILL("___ книги (my)", ["мои"], "Plural → **мои**."),
  MC("*her pencils*", ["её карандаши", "ей карандаши", "еи карандаши"], 0, "**Её** never changes."),
  MC("*Где мои сёстры?* — *Они ___ здесь.* (both)", ["оба", "обе"], 1, "Feminine → **обе**."),
  MC("*Где словари?* — *Они ___ на столе.* (both)", ["оба", "обе"], 0, "Masculine → **оба**."),
]),

SEC("d03-adjectives", "Adjectives, какой, first and second", sub="Lessons 13–14 · hard, soft and mixed adjectives · ordinals", blocks=[
  P("Adjectives end in two letters that agree with the noun. There are three types:"),
  T(["Type", "m.", "f.", "n.", "pl."], [
    ["hard", "но́в**ый**", "но́в**ая**", "но́в**ое**", "но́в**ые**"],
    ["hard, stressed ending", "больш**о́й**", "больш**а́я**", "больш**о́е**", "больш**и́е**"],
    ["soft", "си́н**ий**", "си́н**яя**", "си́н**ее**", "си́н**ие**"],
    ["mixed (г к х)", "ру́сск**ий**", "ру́сск**ая**", "ру́сск**ое**", "ру́сск**ие**"],
    ["mixed (ж ч ш щ)", "хоро́ш**ий**", "хоро́ш**ая**", "хоро́ш**ее**", "хоро́ш**ие**"],
  ]),
  P("Nationality: the adjective is **ру́сский, америка́нский**; the person is a noun — **америка́нец** (m.), **америка́нка** (f.), **америка́нцы** (pl.). But a Russian *person* is also **ру́сский / ру́сская** — the adjective used as a noun."),
  H("какой? and ordinals"),
  P("**Како́й** (кака́я, како́е, каки́е) asks *what kind of, which*. Ordinal numbers are adjectives: **пе́рвый** (1st), **второ́й**, **тре́тий**, **четвёртый**, **пя́тый**: *Это первый урок.*"),
  NOTE("**Пальто́** (*overcoat*) is neuter and never changes: моё пальто, мои пальто."),
], exercises=[
  FILL("___ дом (big: большой → m.)", ["большой"], "The dictionary form."),
  FILL("___ квартира (big)", ["большая"], "Feminine → **большая**."),
  FILL("___ небо (blue: синий)", ["синее"], "Soft neuter → **синее**."),
  FILL("___ газеты (Russian)", ["русские"], "Mixed type: **-ие** after к."),
  MC("*She is an American.*", ["Она американская.", "Она американка.", "Она американец."], 1, "The person is a noun: **американка**."),
  MC("*___ это журнал?* (What kind of magazine?)", ["Какой", "Какая", "Какое"], 0, "Masculine → **какой**."),
  FILL("Это ___ урок. (first)", ["первый"], "**Первый**."),
  MC("*my coats*", ["мои пальто", "мои пальта", "мои пальты"], 0, "**Пальто** never changes."),
]),

SEC("d04-conjugation", "The two conjugations", sub="Lesson 14 · infinitive · е-type and и-type · по-русски · весь", blocks=[
  P("The **infinitive** — the dictionary form — usually ends in **-ть** (чита́ть, говори́ть), sometimes **-ти** (идти́) or **-чь** (мочь). Present-tense endings follow one of two patterns:"),
  T(["", "е-type: де́лать", "и-type: звони́ть"], [
    ["я", "де́ла**ю**", "звон**ю́**"], ["ты", "де́ла**ешь**", "звон**и́шь**"], ["он", "де́ла**ет**", "звон**и́т**"],
    ["мы", "де́ла**ем**", "звон**и́м**"], ["вы", "де́ла**ете**", "звон**и́те**"], ["они", "де́ла**ют**", "звон**я́т**"],
  ]),
  P("When the ending is stressed, **е** becomes **ё**: живу́, жив**ё**шь, жив**ё**т."),
  H("по-русски"),
  P("*In Russian* (with a verb) is **по-ру́сски**; *in English* — **по-англи́йски**: *Вы говорите по-русски?* — *Да, немного.* No capital letter, and the hyphen is part of the word."),
  H("весь — all"),
  P("**Весь** (*all, the whole*) agrees: **весь** класс, **вся** гру́ппа, **всё** письмо́, **все** студе́нты. On their own, **всё** means *everything* and **все** means *everybody*: *Всё хорошо. Все здесь.*"),
], exercises=[
  FILL("Мы ___ упражнение. (делать)", ["делаем"], "е-type, мы → **-ем**."),
  FILL("Они ___ домой. (звонить)", ["звонят"], "и-type, они → **-ят**."),
  FILL("Ты ___ по-английски? (говорить)", ["говоришь"], "и-type, ты → **-ишь**."),
  FILL("Вы ___ ? (понимать)", ["понимаете"], "е-type, вы → **-ете**."),
  MC("*Do you speak Russian?*", ["Вы говорите русский?", "Вы говорите по-русски?", "Вы говорите Русский?"], 1, "With *говорить*, use **по-русски**."),
  MC("*___ группа здесь.* (The whole group is here.)", ["Весь", "Вся", "Всё"], 1, "**Группа** is feminine → **вся**."),
  MC("*___ знают это.* (Everybody knows it.)", ["Всё", "Все"], 1, "*Everybody* → **все**."),
  MC("*___ в порядке.* (Everything is fine.)", ["Всё", "Все"], 0, "*Everything* → **всё**."),
]),

SEC("d05-location", "Where? The prepositional", sub="Lessons 15–16 · cases · в, на + prepositional · быть · стоять, лежать", blocks=[
  P("A noun changes its ending — its **case** — to show its role. The **nominative** is the subject and the dictionary form. To say **where** something is, use **в** (*in*) or **на** (*on, at*) with the **prepositional** case:"),
  T(["Nominative", "Where?", ""], [
    ["стол", "на стол**е́**", "consonant **+е**"], ["шко́ла", "в шко́л**е**", "**-а → -е**"], ["окно́", "на окн**е́**", "**-о → -е**"],
    ["тетра́дь", "в тетра́д**и**", "f. **-ь → -и**"], ["ле́кция", "на ле́кци**и**", "**-ия → -ии**"], ["зда́ние", "в зда́ни**и**", "**-ие → -ии**"],
    ["лес, сад, шкаф", "в лес**у́**, в сад**у́**, в шкаф**у́**", "some m. nouns: **-у́**"],
  ]),
  P("Foreign nouns in **-о, -и, -у** never change: в кино́, в метро́, в такси́."),
  H("быть — to be, in the past"),
  P("*Is* is left out in the present (*Он дома*), but the past is needed: **был, была́, бы́ло, бы́ли** — *Вчера я был в кино.*"),
  H("стоять, лежать, сидеть"),
  P("Russian says how things are placed: upright things **стоя́т** (стол, шкаф, ла́мпа, маши́на), flat things **лежа́т** (кни́га на столе́, ковёр), people **сидя́т** or **стоя́т**. All three are и-type: стою́, стои́шь; лежу́, лежи́шь; сижу́, сиди́шь."),
  EX(("Как называется эта улица?", "What is this street called?"), ("Где находится библиотека?", "Where is the library (located)?")),
], exercises=[
  FILL("Карта на ___ . (стена)", ["стене"], "**-а → -е**."),
  FILL("Мы были в ___ . (кино)", ["кино"], "**Кино** never changes."),
  FILL("Он сейчас на ___ . (лекция)", ["лекции"], "**-ия → -ии**."),
  FILL("Словарь в ___ . (шкаф)", ["шкафу"], "**Шкаф** takes **-у́**: в шкафу."),
  FILL("Вчера она ___ дома. (быть)", ["была"], "Past, feminine → **была**."),
  MC("*Книга ___ на столе.*", ["стоит", "лежит", "сидит"], 1, "A book lying flat → **лежит**."),
  MC("*Лампа ___ на столе.*", ["стоит", "лежит", "сидит"], 0, "Upright → **стоит**."),
  MC("*Как ___ этот город?* (What's this town called?)", ["называется", "находится", "зовут"], 0, "Things are named with **называется**; people with **зовут**."),
]),

SEC("d06-accusative", "The accusative", sub="Lessons 16–18 · the object · pronouns · masculine nouns in -а", blocks=[
  P("The **accusative** is the direct object: *I see **the map***, *I read **the newspaper***."),
  T(["", "Nominative", "Accusative"], [
    ["f. -а / -я", "ка́рта, неде́ля", "ка́рт**у**, неде́л**ю**"],
    ["f. -ь", "тетра́дь", "тетра́дь"],
    ["m. inanimate, n.", "стол, окно́", "стол, окно́"],
    ["m. animate", "студе́нт, учи́тель", "студе́нт**а**, учи́тел**я**"],
  ]),
  NOTE("Stress can move: **рука́ → ру́ку**, **нога́ → но́гу**, **стена́ → сте́ну**, **зима́ → зи́му**."),
  T(["я", "ты", "он", "она", "мы", "вы", "они"], [["меня́", "тебя́", "его́", "её", "нас", "вас", "их"]], caption="Pronouns in the accusative", row_heads=False),
  P("Masculine nouns in **-а, -я** — **старшина́** (*sergeant major*), **па́па**, **дя́дя** — decline like feminine nouns but stay masculine: *Я вижу старшин**у**. Наш старшина хороший.*"),
  P("**Слу́шать** (*listen to*) takes a direct object — no *to*: *Я слушаю радио. Слушайте меня!*"),
], exercises=[
  FILL("Я читаю ___ . (газета)", ["газету"], "**-а → -у**."),
  FILL("Мы видим ___ . (учитель)", ["учителя"], "Animate masculine → **учителя**."),
  FILL("Вы знаете ___ ? (он)", ["его"], "он → **его**."),
  FILL("Они слушают ___ . (лекция)", ["лекцию"], "**-я → -ю**."),
  FILL("Я давно жду ___ . (вы)", ["вас"], "вы → **вас**."),
  FILL("Солдаты видят ___ . (старшина)", ["старшину"], "Masculine in -а declines like **-а → -у**."),
  MC("*Я слушаю ___ .* (радио)", ["радио", "радиу", "к радио"], 0, "No preposition, and **радио** doesn't change."),
  MC("*Он открывает ___ .* (дверь)", ["дверь", "дверю", "двери"], 0, "Feminine **-ь**: no change."),
]),

SEC("d07-going", "Going: идти, ехать, лететь", sub="Lessons 19–20 · where to? · on foot, by vehicle, by air · хотеть", blocks=[
  T(["", "идти́ (on foot)", "е́хать (by vehicle)", "лете́ть (by air)"], [
    ["я", "иду́", "е́ду", "лечу́"], ["ты", "идёшь", "е́дешь", "лети́шь"], ["он", "идёт", "е́дет", "лети́т"],
    ["мы", "идём", "е́дем", "лети́м"], ["вы", "идёте", "е́дете", "лети́те"], ["они", "иду́т", "е́дут", "летя́т"],
  ], caption="Going in one direction, now"),
  P("**Идти** is used for much more than walking: **идёт дождь** (*it's raining*), **идёт снег**, **фильм идёт** (*the film is on*), **урок идёт**. And *come here!* is **иди(те) сюда!**"),
  H("Where to? — куда?"),
  P("The goal of motion is **в / на + accusative**: *Куда вы идёте?* — *В школу. На лекцию.* Adverbs come in pairs:"),
  T(["Where? (где)", "Where to? (куда)"], [["здесь, тут — here", "сюда́ — (to) here"], ["там — there", "туда́ — (to) there"], ["до́ма — at home", "домо́й — home(wards)"]]),
  P("*By train, by plane* — **на по́езде, на самолёте, на маши́не, на авто́бусе**."),
  H("хотеть"),
  P("**Хоте́ть** (*want*) mixes both conjugations: хочу́, хо́чешь, хо́чет — but хоти́м, хоти́те, хотя́т."),
], exercises=[
  FILL("Куда вы ___ ? (идти)", ["идёте", "идете"], "вы → **идёте**."),
  FILL("Мы ___ в Москву. (ехать)", ["едем"], "мы → **едем**."),
  FILL("Они ___ в Париж. (лететь)", ["летят"], "они → **летят**."),
  FILL("Я ___ домой. (идти)", ["иду"], "я → **иду**."),
  MC("*Он ___ дома.* / *Он идёт ___ .*", ["дома / домой", "домой / дома"], 0, "Location **дома**; direction **домой**."),
  MC("*Иди ___ !* (Come here!)", ["здесь", "сюда"], 1, "Motion → **сюда**."),
  MC("*Сегодня ___ дождь.*", ["идёт", "едет", "ходит"], 0, "Rain **идёт**."),
  FILL("Они ___ чай. (хотеть)", ["хотят"], "**Хотеть**: они **хотят**."),
  FILL("Ты ___ кофе? (хотеть)", ["хочешь"], "ты → **хочешь**."),
]),

]
