# DLI Basic Russian Grammar, part C (lessons 30–45).
from kit import *

SECTIONS = [

SEC("d15-pronouns", "Pronouns, надо, можно, нельзя", sub="Lessons 30–32 · я, ты … они in every case · у меня = my · никто не", blocks=[
  T(["", "я", "ты", "мы", "вы", "он / оно", "она", "они"], [
    ["Nom.", "я", "ты", "мы", "вы", "он", "она́", "они́"],
    ["Gen./Acc.", "меня́", "тебя́", "нас", "вас", "его́", "её", "их"],
    ["Dat.", "мне", "тебе́", "нам", "вам", "ему́", "ей", "им"],
    ["Instr.", "мной", "тобо́й", "на́ми", "ва́ми", "им", "ей", "и́ми"],
    ["Prep.", "обо мне́", "о тебе́", "о нас", "о вас", "о нём", "о ней", "о них"],
  ]),
  P("After a preposition, the third-person forms add **н-**: у **него́**, к **ней**, с **ни́ми**. But **его, её, их** meaning *his, her, their* never take н-: у **его** брата."),
  P("Russian often says *at me* instead of *my*: **У меня́** боли́т голова́. *My head aches.* **У нас** в го́роде… *In our town…*"),
  H("надо, можно, нельзя"),
  P("With the person in the **dative**: **Мне на́до** (*I must, I need to*), **Мне мо́жно** (*I may*), **Мне нельзя́** (*I mustn't; I can't*). Past: **на́до бы́ло**, **мо́жно бы́ло**, **нельзя́ бы́ло**. Future: **бу́дет**."),
  P("**Никто́ не** — *nobody*: *Никто не знает.* It declines like кто: *Я **никого́ не** видел.*"),
], exercises=[
  FILL("Я думаю о ___ . (она)", ["ней"], "о + она → **о ней**."),
  FILL("Мы пойдём к ___ . (он)", ["нему"], "к + он → **к нему**."),
  FILL("Я говорил с ___ . (они)", ["ними"], "с + они → **с ними**."),
  FILL("___ надо работать. (я)", ["Мне"], "Dative **мне**."),
  FILL("Здесь ___ курить. (forbidden)", ["нельзя"], "**Нельзя**."),
  FILL("Вчера мне ___ было работать. (had to)", ["надо", "нужно"], "**Надо было**."),
  FILL("Я ___ не видел. (nobody)", ["никого"], "Accusative of никто → **никого**."),
  MC("*I went to his brother's.*", ["Я ходил к его брату.", "Я ходил к нему брату.", "Я ходил к него брату."], 0, "*His* never takes н-: **к его брату**."),
]),

SEC("d16-past-future", "Past and compound future", sub="Lessons 33–35 · -л, -ла, -ло, -ли · буду + infinitive · нужен · такой, так", blocks=[
  P("**Past tense**: infinitive stem + **-л, -ла, -ло, -ли**, agreeing with the subject's gender and number: *он работал, она работала, оно работало, они работали*."),
  P("**Compound future** (for imperfective verbs): **бу́ду, бу́дешь, бу́дет, бу́дем, бу́дете, бу́дут** + infinitive: *Завтра я буду работать.*"),
  H("нужен — needed"),
  P("*I need a book*: **Мне нужна́ книга** — *a book is necessary to me*. **Ну́жен** agrees with the thing needed: **нужен** словарь, **нужна** карта, **нужно** окно, **нужны** книги."),
  H("Accusative plural of things"),
  P("Inanimate plural nouns look the same in the accusative as the nominative: *Я читаю **газеты**. Он купил **книги***."),
  H("такой and так"),
  P("**Тако́й** (agreeing) goes with nouns and long adjectives: *Это **такой** хороший фильм!* **Так** goes with verbs and adverbs: *Он **так** хорошо говорит!*"),
], exercises=[
  FILL("Вчера мы ___ футбол. (играть)", ["играли"], "мы → **-ли**."),
  FILL("Моя сестра ___ в Киеве. (жить)", ["жила"], "Feminine → **жила**."),
  FILL("Завтра я ___ отдыхать.", ["буду"], "я → **буду**."),
  FILL("Они ___ работать в субботу.", ["будут"], "они → **будут**."),
  FILL("Мне ___ словарь. (need)", ["нужен"], "Masculine → **нужен**."),
  FILL("Нам ___ деньги. (need)", ["нужны"], "Plural → **нужны**."),
  MC("*Она ___ красивая!*", ["такая", "так"], 0, "With an adjective + (implied) noun → **такая**."),
  MC("*Вы ___ быстро говорите!*", ["такой", "так"], 1, "With an adverb → **так**."),
]),

SEC("d17-aspect", "Imperfective and perfective", sub="Lessons 35–37 · twin verbs · the five tenses · когда, если + future", blocks=[
  P("Most verbs are **twins**: an **imperfective** (the action itself — going on, repeated, or just named) and a **perfective** (one action completed, a result)."),
  T(["", "Imperfective (писа́ть)", "Perfective (написа́ть)"], [
    ["Present", "пишу́ — I write, am writing", "—"],
    ["Past", "писа́л — I wrote, was writing, used to write", "написа́л — I wrote (it, and finished)"],
    ["Future", "бу́ду писа́ть — I'll be writing", "напишу́ — I'll write (it)"],
  ], caption="The five tenses of a twin verb"),
  P("A perfective verb has **no present**: its present-type forms are the future. Never **буду** + perfective."),
  T(["Imperfective", "Perfective"], [["покупа́ть", "купи́ть"], ["реша́ть", "реши́ть"], ["посыла́ть", "посла́ть"], ["дава́ть", "дать"], ["начина́ть", "нача́ть"], ["конча́ть", "ко́нчить"], ["предлага́ть", "предложи́ть"]]),
  H("когда, как только, если"),
  P("Where English uses the present after *when, as soon as, if* about the future, Russian uses the **future**: **Когда́ я ко́нчу** работу, я позвоню. *When I finish…* **Е́сли бу́дет** дождь, мы не пойдём. *If it rains…*"),
], exercises=[
  MC("*Вчера я весь день ___ письма.*", ["писал", "написал"], 0, "All day — the process → imperfective."),
  MC("*Я ___ письмо и пошёл на почту.*", ["писал", "написал"], 1, "Finished, then the next action → perfective."),
  MC("*Завтра я ___ тебе.* (I'll call you once)", ["буду позвонить", "позвоню", "звоню"], 1, "Perfective future → **позвоню**."),
  MC("The perfective of **давать** is…", ["дать", "выдать", "давнуть"], 0, "**Дать**."),
  MC("The perfective of **кончать** is…", ["закончать", "кончить", "покончать"], 1, "**Кончить**."),
  MC("*Если завтра ___ хорошая погода, мы поедем за город.*", ["есть", "будет", "была"], 1, "Future after **если**: **будет**."),
  FILL("Когда я ___ эту книгу, я дам её тебе. (прочитать — I finish reading)", ["прочитаю"], "Future after **когда**: **прочитаю**."),
  FILL("Что ты ___ ? (купить — what will you buy?)", ["купишь"], "Perfective future: ты **купишь**."),
]),

SEC("d18-genitive-plural", "Counting: the genitive plural", sub="Lessons 37–40 · много, мало, сколько · numbers with nouns · который · один из", blocks=[
  T(["Nominative sg.", "Genitive pl.", "Ending"], [
    ["стол, студе́нт", "стол**о́в**, студе́нт**ов**", "m. consonant **+ов**"], ["музе́й", "музе́**ев**", "m. **-й → -ев**"],
    ["слова́рь, тетра́дь, ночь", "словар**е́й**, тетра́д**ей**, ноч**е́й**", "**-ь** (m. or f.) and **ж ч ш щ → -ей**"],
    ["ка́рта, окно́", "карт, о́кон", "f. **-а** and n. **-о**: no ending"], ["неде́ля, зда́ние", "неде́ль, зда́ний", "**-я → -ь**, **-ие → -ий**"],
  ]),
  P("With no ending, a vowel often appears to break up consonants: окно́ → **о́кон**, сестра́ → **сестёр**, ру́чка → **ру́чек**. Ones to learn: **люде́й** (people), **дете́й**, **раз** (times), **челове́к** (after numbers), **лет** (years)."),
  H("Quantity words"),
  P("**Мно́го** (*much, many*), **ма́ло** (*little, few*), **ско́лько** (*how many*), **не́сколько** (*several*) take the genitive — plural for things you count, singular for things you don't: **много книг**, **много времени**; **несколько студентов**."),
  H("Numbers with nouns"),
  L("**1** (21, 31…) — nominative singular: **один** стол, **одна** карта",
    "**2, 3, 4** — genitive singular: два стол**а́**, **две** карт**ы**",
    "**5–20, 25…** — genitive plural: пять стол**о́в**, десять карт"),
  P("**Оди́н из** + genitive plural — *one of*: *один из студентов*, *одна из книг*. **Кото́рый** (*which, who*) joins clauses and agrees with its noun: *Студент, **который** живёт здесь…*"),
], exercises=[
  FILL("много ___ (студент)", ["студентов"], "**+ов**."),
  FILL("пять ___ (неделя)", ["недель"], "**-я → -ь**."),
  FILL("сколько ___ ? (книга)", ["книг"], "No ending."),
  FILL("несколько ___ (словарь)", ["словарей"], "**-ь → -ей**."),
  FILL("мало ___ (время)", ["времени"], "Uncountable → genitive singular."),
  FILL("три ___ (карта)", ["карты"], "2–4 → genitive singular."),
  MC("*двадцать один ___* (студент)", ["студент", "студента", "студентов"], 0, "Ends in **один** → nominative singular."),
  MC("*Один из моих ___ живёт в Москве.*", ["друг", "друга", "друзей"], 2, "**Один из** + genitive plural."),
  MC("*Девушка, ___ сидит там, — моя сестра.*", ["который", "которая", "которое"], 1, "Agrees with **девушка** → **которая**."),
]),

SEC("d19-imperative", "Commands", sub="Lessons 40–42 · the imperative · don't! · irregular pasts · брать / взять", blocks=[
  P("Take the **они** form of the present (or perfective future), remove the ending, then:"),
  T(["Stem ends in…", "ты", "вы", "Example"], [
    ["a vowel", "**-й**", "**-йте**", "чита́-ют → **чита́й(те)**"],
    ["a consonant, ending stressed in я-form", "**-и́**", "**-и́те**", "говор-я́т → **говори́(те)**, пиш-ут → **пиши́(те)**"],
    ["a consonant, stem stressed", "**-ь**", "**-ьте**", "встан-ут → **встань(те)**"],
  ]),
  P("Ones to learn: **дай(те)** (give), **ешь(те)** (eat), **пей(те)** (drink), **встава́й(те)** (get up), **ляг(те)** (lie down)."),
  H("Don't!"),
  P("*Do!* is usually perfective: **Откро́йте окно!** *Don't!* is usually imperfective: **Не открыва́йте окно!**"),
  H("Irregular pasts and common twins"),
  T(["Imperfective", "Perfective", ""], [["брать", "взять (возьму́; взял)", "take"], ["ста́вить", "поста́вить", "put (upright)"], ["класть", "положи́ть", "put (lying)"], ["забыва́ть", "забы́ть", "forget"], ["меня́ть", "поменя́ть", "change"]]),
], exercises=[
  FILL("___ ! (читать — read, to one friend)", ["Читай"], "Vowel stem → **-й**."),
  FILL("___ медленнее! (говорить — to a group)", ["Говорите"], "**говори́те**."),
  FILL("___ письмо! (написать — to one person)", ["Напиши"], "**напиш-ут → напиши**."),
  FILL("___ мне книгу! (дать — politely)", ["Дайте"], "**Дайте**."),
  MC("*Don't close the door!*", ["Не закройте дверь!", "Не закрывайте дверь!"], 1, "*Don't* → imperfective."),
  MC("*Please sit down.*", ["Садитесь, пожалуйста.", "Сидите, пожалуйста."], 0, "**Садитесь** — take a seat (motion). *Сидите* means *stay seated*."),
  MC("The perfective of **класть** is…", ["покласть", "положить", "сложить"], 1, "**Положить**."),
  FILL("Он ___ мой словарь. (взять — he took)", ["взял"], "**взял**."),
]),

SEC("d20-plural-cases", "Plural nouns in every case", sub="Lessons 42–46 · dative, instrumental, prepositional plural · над, под, между, перед, за", blocks=[
  P("In the plural, the dative, instrumental and prepositional endings are the same for every gender:"),
  T(["", "Dative", "Instrumental", "Prepositional"], [
    ["Hard (стол, ка́рта, окно́)", "стол**а́м**, ка́рт**ам**", "стол**а́ми**, ка́рт**ами**", "о стол**а́х**, о ка́рт**ах**"],
    ["Soft (музе́й, неде́ля, тетра́дь)", "музе́**ям**, неде́л**ям**", "музе́**ями**, неде́л**ями**", "о музе́**ях**, о неде́л**ях**"],
  ]),
  P("A few: **людьми́, детьми́** (instr. of лю́ди, де́ти), **дочерьми́**."),
  T(["Nom.", "Gen.", "Dat.", "Acc.", "Instr.", "Prep."], [
    ["столы́", "столо́в", "стола́м", "столы́", "стола́ми", "о стола́х"],
    ["студе́нты", "студе́нтов", "студе́нтам", "студе́нтов", "студе́нтами", "о студе́нтах"],
    ["ка́рты", "карт", "ка́ртам", "ка́рты", "ка́ртами", "о ка́ртах"],
  ], caption="Whole plurals — animate accusative = genitive", row_heads=False),
  H("над, под, между, перед, за + instrumental"),
  P("**над** (above), **под** (under), **ме́жду** (between), **пе́ред** (in front of; before), **за** (behind; beyond): *Лампа висит **над столом**. **Перед домом** сад. **Между окнами** шкаф.*"),
  P("**Наверх / вниз** — upstairs, downstairs (direction); **наверху́ / внизу́** — upstairs, downstairs (location)."),
], exercises=[
  FILL("Я пишу ___ . (друзья — dative plural)", ["друзьям"], "**-ям**."),
  FILL("Мы говорили о ___ . (книги)", ["книгах"], "**-ах**."),
  FILL("Он гуляет с ___ . (дети)", ["детьми"], "Irregular: **детьми**."),
  FILL("Я знаю этих ___ . (студенты — animate accusative)", ["студентов"], "Animate plural accusative = genitive."),
  FILL("Самолёт летит над ___ . (город)", ["городом"], "**над** + instrumental."),
  FILL("Стол стоит между ___ . (окна — instrumental plural)", ["окнами"], "**-ами**."),
  MC("*Он живёт ___.* (upstairs — location)", ["наверх", "наверху"], 1, "Location → **наверху**."),
  MC("*Идите ___!* (Go downstairs!)", ["вниз", "внизу"], 0, "Direction → **вниз**."),
]),

SEC("d21-adjective-cases", "Adjectives and possessives in every case", sub="Lessons 46–52 · мой, наш, новый … · после чисел · через · за = for · свой", blocks=[
  T(["", "m. / n.", "f.", "pl."], [
    ["Nom.", "но́вый / но́вое", "но́вая", "но́вые"],
    ["Gen.", "но́в**ого**", "но́в**ой**", "но́в**ых**"],
    ["Dat.", "но́в**ому**", "но́в**ой**", "но́в**ым**"],
    ["Acc.", "= nom. or gen.", "но́в**ую**", "= nom. or gen."],
    ["Instr.", "но́в**ым**", "но́в**ой**", "но́в**ыми**"],
    ["Prep.", "о но́в**ом**", "о но́в**ой**", "о но́в**ых**"],
  ], caption="Adjectives (hard). In -ого, the г is said в."),
  T(["", "m. / n.", "f.", "pl."], [
    ["Nom.", "мой / моё", "моя́", "мои́"], ["Gen.", "моего́", "мое́й", "мои́х"], ["Dat.", "моему́", "мое́й", "мои́м"],
    ["Acc.", "= nom. or gen.", "мою́", "= nom. or gen."], ["Instr.", "мои́м", "мое́й", "мои́ми"], ["Prep.", "о моём", "о мое́й", "о мои́х"],
  ], caption="мой (also твой, свой); наш / ваш: на́шего, на́шему, на́шим, о на́шем…"),
  H("свой — one's own"),
  P("When *my, your, his…* refers back to the **subject**, Russian uses **свой**: *Он любит **свою** жену.* (his own wife). *Он любит **его** жену* would mean someone else's!"),
  H("Small prepositions"),
  L("**че́рез** + acc. — across, through; in (time): че́рез у́лицу, **через час** (*in an hour*)", "**за** + acc. — for (in return for): спаси́бо **за по́мощь**; заплати́ть **за биле́т**"),
], exercises=[
  FILL("Я живу в ___ доме. (новый — prepositional)", ["новом"], "Prepositional m. → **-ом**."),
  FILL("У ___ сестры есть машина. (моя — genitive)", ["моей"], "Genitive f. → **моей**."),
  FILL("Я позвонил ___ другу. (старый — dative)", ["старому"], "Dative m. → **-ому**."),
  FILL("Мы гуляли с ___ собакой. (наша)", ["нашей"], "Instrumental f. → **нашей**."),
  FILL("Она купила ___ сумку. (красная — accusative)", ["красную"], "Accusative f. → **-ую**."),
  MC("*Он взял ___ книгу.* (his own book)", ["его", "свою", "её"], 1, "Refers to the subject → **свою**."),
  MC("*Я приду ___ час.* (in an hour)", ["через", "за", "в"], 0, "**Через час**."),
  MC("*Спасибо ___ подарок!*", ["для", "за", "через"], 1, "Thanks **for** → **за** + acc."),
]),

]
