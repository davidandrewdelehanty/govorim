# DLI Basic Russian Grammar, part F (lessons 86–107).
from kit import *

SECTIONS = [

SEC("d36-passive", "The passive: сделан, написан", sub="Lessons 86–90 · short past passive participles · быть + participle · при", blocks=[
  P("*The letter was written*: Russian uses a **short past passive participle** from a **perfective** verb, agreeing with the subject, plus **быть** for past and future:"),
  T(["Verb ends in…", "Participle (m. / f. / n. / pl.)", "Example"], [
    ["**-ать, -ять**", "**-ан, -ана, -ано, -аны**", "написа́ть → **напи́сан**: Письмо́ **напи́сано**."],
    ["**-ить, -еть**", "**-ен, -ена́, -ено́, -ены́**", "получи́ть → **полу́чен**: Пи́сьма **полу́чены**."],
    ["**-уть, -ыть** and short verbs", "**-т, -та, -то, -ты**", "закры́ть → **закры́т**: Дверь **закры́та**."],
  ]),
  P("The consonant changes as in the я-form: пригласи́ть → **приглашён**, купи́ть → **ку́плен**, постро́ить → **постро́ен**."),
  EX(("Дом был постро́ен в 1950 году.", "The house was built in 1950."), ("Магазин закрыт.", "The shop is closed."), ("Работа будет сделана завтра.", "The work will be done tomorrow.")),
  P("The person who did it goes in the **instrumental**: *Роман написан **Толстым**.* But Russian prefers active sentences without a named actor: **Здесь продаю́т** газе́ты — *newspapers are sold here*."),
  P("**При** + prepositional — *in the presence of; under (a ruler, a system); attached to*: **при мне**, **при Петре́ Пе́рвом**, **шко́ла при университе́те**."),
], exercises=[
  FILL("Письмо ___ вчера. (написать — was written)", ["написано"], "Neuter → **написано**."),
  FILL("Дверь ___ . (закрыть — is closed)", ["закрыта"], "Feminine → **закрыта**."),
  FILL("Билеты уже ___ . (купить — are bought)", ["куплены"], "**п → пл**: **куплены**."),
  FILL("Мост был ___ в прошлом году. (построить)", ["построен"], "Masculine → **построен**."),
  MC("*The novel was written by Tolstoy.*", ["Роман написан Толстой.", "Роман написан Толстым.", "Роман написан от Толстого."], 1, "Agent in the instrumental: **Толстым**."),
  MC("*Вы приглашены на вечер.* means…", ["You invited (someone) to the party.", "You are invited to the party."], 1, "Passive participle → *are invited*."),
  MC("*It happened in my presence.*", ["Это случилось при мне.", "Это случилось с мной."], 0, "**при** + prepositional."),
]),

SEC("d37-long-participles", "Participles as adjectives", sub="Lessons 90–92 · написанный · participial phrases · многие", blocks=[
  P("The **long** past passive participle is a full adjective: **напи́санный, прочи́танный, постро́енный, закры́тый** — with **нн** in the long form, one **н** in the short."),
  EX(("Это письмо, написанное моим братом.", "This is a letter written by my brother."), ("закрытая дверь", "a closed door"), ("Прочитанные книги лежат на столе.", "The books (that have been) read are on the table.")),
  P("A phrase built on a participle — a **participial phrase** — can stand after the noun, set off by commas, and replaces a **который** clause: *письмо, **кото́рое написа́л** мой брат* = *письмо, **напи́санное** мои́м бра́том*. Participles belong mostly to writing; in speech, **который** is more natural."),
  P("**Мно́гие** (*many people, many of*) is an adjective form of **мно́го**: **Мно́гие** ду́мают… *Many people think…*; **во мно́гих** города́х."),
], exercises=[
  FILL("___ дверь (закрыть — the closed door)", ["закрытая"], "Long feminine → **закрытая**."),
  FILL("___ книги (прочитать — the books read)", ["прочитанные"], "Long plural with **нн**: **прочитанные**."),
  MC("*Дом, построенный в 1900 году…* — which means the same?", ["Дом, который построили в 1900 году…", "Дом, который построил в 1900 году…"], 0, "Passive participle = *which they built* (impersonal **построили**)."),
  MC("Long or short? *Окно ___ .* (is open)", ["открыто", "открытое"], 0, "Predicate → short form **открыто**."),
  MC("Long or short? *___ окно* (an open window)", ["открыто", "открытое"], 1, "Before the noun → long form **открытое**."),
  FILL("___ считают, что это правда. (many people)", ["Многие"], "**Многие**."),
]),

SEC("d38-conditional", "If only: бы, если бы, чтобы", sub="Lessons 92–98 · the conditional · хотелось бы · чтобы · complex conjunctions", blocks=[
  P("The **conditional** is the **past tense + бы**, for every time — past, present or future: *Я **бы пошёл**, но нет времени.* *I would go, but there's no time.*"),
  P("**Е́сли бы** — *if* something unreal: **Е́сли бы** я **знал**, я **бы** сказа́л. *If I had known, I would have said.* / *If I knew, I'd tell you.*"),
  P("**Хоте́лось бы** (with the dative) — *I'd like*: **Мне хоте́лось бы** пое́хать в Москву. **Захоте́лось** — *(suddenly) felt like*: *Мне захотелось пить.*"),
  H("чтобы"),
  L("*In order to* — with the infinitive when the subject is the same: Я пришёл, **что́бы помо́чь**.",
    "*So that* — with the past tense when the subject changes: Я пришёл, **что́бы** ты **не скуча́л**.",
    "After wanting, asking, telling someone to: Я **хочу́, что́бы** ты **пришёл**. *I want you to come.* Скажи́ ему́, **что́бы** он позвони́л."),
  H("Joining clauses with a preposition"),
  P("A preposition can't stand before **что**; Russian adds **то**: **из-за того́, что** (*because*), **по́сле того́, как** (*after*), **до того́, как** / **пе́ред тем, как** (*before*), **для того́, что́бы** (*in order to*), **несмотря́ на то, что** (*although*)."),
], exercises=[
  FILL("Я ___ поехал, но у меня нет денег. (would)", ["бы"], "**бы** + past."),
  MC("*If I had time, I would read more.*", ["Если у меня будет время, я буду читать больше.", "Если бы у меня было время, я бы читал больше."], 1, "Unreal → **если бы** + past, **бы** + past."),
  FILL("Я хочу, ___ ты пришёл. (that — want someone to)", ["чтобы"], "**хочу, чтобы** + past."),
  MC("*Я пришёл, чтобы ___ тебе.* (to help you)", ["помочь", "помог", "помогу"], 0, "Same subject → infinitive."),
  MC("*Скажи ему, чтобы он ___ завтра.*", ["позвонит", "позвонил", "позвонить"], 1, "Different subject → past tense after **чтобы**."),
  FILL("Мне ___ бы отдохнуть. (I'd like)", ["хотелось"], "**хотелось бы**."),
  MC("*Мы поехали домой, после ___ как кончился фильм.*", ["того", "чего", "что"], 0, "**после того, как**."),
  MC("*Он опоздал из-за ___, что не было автобуса.*", ["того", "этого", "что"], 0, "**из-за того, что**."),
]),

SEC("d39-active-participles", "Active participles: читающий, читавший", sub="Lessons 98–100 · present and past active participles · instead of который", blocks=[
  P("An **active participle** describes someone **doing** the action — *the student (who is) reading*. Present: from the **они** form, drop **-т** and add **-щий**:"),
  T(["Verb", "они-form", "Present active participle"], [
    ["чита́ть", "чита́ю-т", "**чита́ющий** — reading"], ["говори́ть", "говоря́-т", "**говоря́щий** — speaking"], ["писа́ть", "пи́шу-т", "**пи́шущий** — writing"], ["учи́ться", "у́чат-ся", "**у́чащийся** — studying; a pupil"],
  ]),
  P("Past: infinitive stem + **-вший** (after a vowel) or **-ший** (after a consonant): **чита́вший, прочита́вший, говори́вший; нёсший, мо́гший**; идти́ → **ше́дший**."),
  P("They decline like **хоро́ший** and agree with their noun. A participial phrase replaces **кото́рый**: *Студент, **кото́рый чита́ет** книгу* = *Студент, **чита́ющий** книгу*; *Человек, **кото́рый звони́л**,* = *Человек, **звони́вший** …*"),
  P("The present participle doesn't change for time; the past participle can come from either aspect."),
], exercises=[
  FILL("Студент, ___ книгу, — мой брат. (читать — who is reading)", ["читающий"], "**читающий**."),
  FILL("Девушка, ___ по телефону, — моя сестра. (говорить — who is speaking)", ["говорящая"], "Feminine → **говорящая**."),
  FILL("Человек, ___ вчера, был врач. (звонить — who called)", ["звонивший"], "Past active → **звонивший**."),
  MC("*Я видел мальчика, ___ в парке.* (who was playing)", ["играющего", "игравшего"], 1, "Past action → **игравшего** (accusative, animate)."),
  MC("*пишущий* comes from…", ["писать", "пишут", "выписать"], 0, "From **писать** (они пишут)."),
  MC("*учащиеся* means…", ["teachers", "pupils, students", "lessons"], 1, "**учащиеся** — those studying: pupils."),
]),

SEC("d40-passive-present", "More passives: любимый, -ся", sub="Lessons 100–104 · present passive participles · -ся passives · the passive in summary", blocks=[
  P("The **present passive participle** — *being done, -able* — is made from the **мы** form of imperfective verbs, adding adjective endings: **люби́м**-ый → **люби́мый** (*beloved, favourite*), **уважа́емый** (*respected; Dear … in letters*), **изуча́емый** (*being studied*)."),
  EX(("мой любимый писатель", "my favourite writer"), ("Уважаемый Иван Петрович!", "Dear Ivan Petrovich,"), ("независимая страна", "an independent country")),
  P("**Imperfective passive** with **-ся**: things done regularly, in general: **Дом стро́ится.** *The house is being built.* **Здесь продаётся газета.** *Newspapers are sold here.* The actor, if named, is instrumental."),
  T(["", "Imperfective", "Perfective"], [
    ["Is / was being done", "**-ся**: Дом стро́ится / стро́ился", "—"],
    ["Has been / was done", "—", "short participle: Дом постро́ен / был постро́ен"],
    ["Impersonal *they*", "Дом стро́ят", "Дом постро́или"],
  ], caption="The passive in summary"),
], exercises=[
  FILL("Это мой ___ фильм. (любить — favourite)", ["любимый"], "**любимый**."),
  FILL("___ коллеги! (уважать — Dear colleagues)", ["Уважаемые"], "Plural → **уважаемые**."),
  MC("*The bridge is being built.*", ["Мост построен.", "Мост строится."], 1, "In progress → imperfective **-ся**."),
  MC("*The bridge has been built.*", ["Мост построен.", "Мост строится."], 0, "Completed → **построен**."),
  FILL("Здесь ___ книги. (продаваться — are sold)", ["продаются"], "Plural → **продаются**."),
  MC("*Пушкин ___ всеми.* (is loved)", ["любим", "любимый", "любят"], 0, "Short present passive: **любим** (bookish)."),
]),

SEC("d41-gerunds", "Gerunds: читая, прочитав", sub="Lessons 104–107 · imperfective and perfective деепричастия · будучи", blocks=[
  P("A **gerund** (деепричастие) is an adverb made from a verb — *while doing, having done*. Its subject must be the **same** as the main verb's."),
  T(["Kind", "How", "Example"], [
    ["**Imperfective** — while doing", "они-form stem + **-я** (**-а** after ж ч ш щ)", "чита́ть → **чита́я**; говори́ть → **говоря́**; слы́шать → **слы́ша**; занима́ться → **занима́ясь**"],
    ["**Perfective** — having done", "past stem + **-в** (-вшись for -ся)", "прочита́ть → **прочита́в**; верну́ться → **верну́вшись**"],
    ["Perfective in **-ти**", "like the imperfective", "прийти́ → **придя́**, принести́ → **принеся́**"],
  ]),
  EX(("Читая книгу, он слушал музыку.", "While reading the book, he listened to music."), ("Прочитав письмо, она заплакала.", "Having read the letter, she began to cry."), ("Будучи студентом, он жил в Москве.", "As a student (being a student), he lived in Moscow.")),
  P("**Быть** has the gerund **бу́дучи**. Some verbs (*писать, ждать, мочь*) have no imperfective gerund in use."),
  NOTE("Wrong: *Подходя к дому, пошёл дождь* — the rain didn't approach the house! The gerund's subject must be the sentence's subject: *Когда я подходил к дому, пошёл дождь.*"),
  P("Some gerunds have become prepositions: **благодаря́** (*thanks to*, + dative), **несмотря́ на** (*despite*, + accusative)."),
], exercises=[
  FILL("___ домой, я встретил друга. (идти — while going)", ["Идя"], "**Идя**."),
  FILL("___ работу, он пошёл домой. (кончить — having finished)", ["Кончив", "Закончив"], "Perfective → **кончив**."),
  FILL("___ по-русски, она часто ошибается. (говорить — when speaking)", ["Говоря"], "**Говоря**."),
  FILL("___ домой, она сразу легла спать. (вернуться — having returned)", ["Вернувшись"], "**-вшись** for -ся verbs."),
  MC("Which sentence is correct?", ["Выходя из дома, пошёл дождь.", "Выходя из дома, я увидел, что идёт дождь."], 1, "The gerund's subject must be the main subject — **я**."),
  MC("*___ врачу, он быстро выздоровел.* (thanks to)", ["Благодаря", "Несмотря на"], 0, "**Благодаря** + dative."),
  MC("*___ дождь, мы пошли гулять.* (despite)", ["Благодаря", "Несмотря на"], 1, "**Несмотря на** + accusative."),
]),

SEC("d42-nobody-to", "No one to ask, nowhere to go", sub="Lessons 105–107 · некого, нечего · негде, некуда, некогда", blocks=[
  P("**Не́кого, не́чего** + infinitive, with the person in the **dative**, mean *there is no one / nothing to …*. The stress is always on **не́-**, and there is no second **не**:"),
  EX(("Мне не́чего де́лать.", "I have nothing to do."), ("Ему́ не́кого спроси́ть.", "There's no one for him to ask."), ("Не́ с кем поговори́ть.", "There's no one to talk to."), ("Мне не́где жить.", "I have nowhere to live."), ("Нам не́куда идти́.", "We have nowhere to go."), ("Ему́ не́когда.", "He has no time.")),
  T(["", "nobody / nothing (+ не)", "no one / nothing to (+ infinitive)"], [
    ["", "Я **никого́ не** зна́ю.", "Мне **не́кого** спроси́ть."],
    ["", "Он **ничего́ не** де́лает.", "Ему **не́чего** де́лать."],
    ["", "Я **нигде́ не** был.", "Мне **не́где** спать."],
  ], caption="Compare", row_heads=False),
  P("Past and future add **бы́ло / бу́дет**: *Мне **не́чего бы́ло** де́лать.* With prepositions, it splits: **не́ с кем, не́ о чем, не́ к кому**."),
], exercises=[
  FILL("Мне ___ делать. (nothing to)", ["нечего"], "**нечего**."),
  FILL("Ей ___ позвонить. (no one to)", ["некого"], "**некого**."),
  FILL("Нам ___ жить. (nowhere to)", ["негде"], "Place → **негде**."),
  FILL("Мне ___ , я спешу. (no time)", ["некогда"], "**некогда**."),
  MC("*I don't know anybody here.*", ["Я некого здесь не знаю.", "Я никого здесь не знаю."], 1, "Plain negation → **никого не**."),
  MC("*There was nothing to eat.*", ["Нечего было есть.", "Ничего не было есть."], 0, "**Нечего было** + infinitive."),
  MC("*Не ___ поговорить.* (no one to talk to)", ["с кем", "кем", "с некем"], 0, "Split: **не с кем**."),
]),

SEC("d43-small-words-2", "Until, both, then, almost", sub="Lessons 106–107 · пока, пока не · оба, и тот и другой · потом, тогда · едва, чуть, почти · некоторый · дважды", blocks=[
  T(["Word", "Means", "Example"], [
    ["**пока́**", "while", "**Пока** ты спал, я работал."], ["**пока́ не**", "until", "Жди, **пока́** я **не** приду́."],
    ["**о́ба / о́бе**", "both (+ gen. sg.)", "**оба** брата, **обе** сестры; **у обо́их**"], ["**и тот и друго́й**", "both (things or people, separately)", "Я знаю **и того, и другого**."],
    ["**ни тот ни друго́й**", "neither", "**Ни тот, ни другой** не пришёл."],
    ["**пото́м**", "then, afterwards (next)", "Сначала обед, **потом** кино."], ["**тогда́**", "then, at that time; in that case", "**Тогда** я жил в Москве. — **Тогда** пойдём!"],
    ["**почти́**", "almost", "**Почти** все пришли."], ["**чуть не**", "nearly (but didn't)", "Я **чуть не** упа́л."], ["**едва́**", "barely, hardly", "Он **едва́** говорит по-русски."],
    ["**не́который**", "some, certain", "**Некоторые** студенты…"], ["**одна́жды, два́жды**", "once (upon a time), twice", "**Однажды** утром… · **вдвоём** — the two of us together"],
  ]),
  P("Dimensions: **длино́й в** пять ме́тров — *five metres long*; **ширино́й, высото́й, глубино́й**."),
], exercises=[
  MC("*Подожди, ___ я не вернусь.*", ["пока", "когда", "потом"], 0, "**пока не** — until."),
  MC("*Сначала мы поужинали, ___ пошли в кино.*", ["тогда", "потом"], 1, "Next in sequence → **потом**."),
  MC("*В 1990 году я жил в Киеве. ___ я был студентом.*", ["Тогда", "Потом"], 0, "At that time → **тогда**."),
  FILL("___ сестры живут в Москве. (both)", ["Обе"], "Feminine → **обе**."),
  MC("*Я ___ не опоздал на поезд.* (nearly missed it)", ["почти", "чуть", "едва"], 1, "**чуть не** — nearly (but didn't)."),
  FILL("___ все студенты сдали экзамен. (almost)", ["Почти"], "**Почти**."),
  FILL("Мы пошли гулять ___ . (the two of us)", ["вдвоём", "вдвоем"], "**вдвоём**."),
  FILL("Я был в Москве ___ . (twice)", ["дважды"], "**дважды**."),
]),

]
