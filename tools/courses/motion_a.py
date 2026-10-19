# Verbs of Motion, part A: the unprefixed verbs.
# Written for this site from the DLI Russian Basic Course (Grammar Reference
# Book I, lessons 19–21, 54, 56, 62–63; Student Workbook for Homework
# Assignments, lessons 44–78), a US Government work in the public domain.
from kit import *

SECTIONS = [

SEC("m01-two-kinds", "One way, or round and about", sub="идти / ходить · ехать / ездить · лететь / летать", blocks=[
  P("Russian has two verbs for every kind of going. DLI calls them the **actual** and the **repeated** function:"),
  T(["", "Actual — one trip, one direction, in progress", "Repeated — habits, round trips, back and forth, ability"], [
    ["on foot", "**идти́** — иду́, идёшь, иду́т; шёл, шла", "**ходи́ть** — хожу́, хо́дишь, хо́дят"],
    ["by vehicle", "**е́хать** — е́ду, е́дешь, е́дут", "**е́здить** — е́зжу, е́здишь, е́здят"],
    ["by air", "**лете́ть** — лечу́, лети́шь, летя́т", "**лета́ть** — лета́ю, лета́ешь"],
  ]),
  H("When to use which"),
  T(["Use the actual verb (идти)", "Use the repeated verb (ходить)"], [
    ["Now, on the way: *Я иду домой.*", "Regularly: *Я всегда хожу пешком.*"],
    ["One direction at a moment in the past: *Когда я шёл домой, я встретил друга.*", "A round trip in the past (= был): *Вчера я ходил в кино.*"],
    ["A plan, in the present: *Завтра я иду в театр.*", "Moving about with no single direction: *Он ходит по комнате.*"],
    ["", "Ability or habit: *Ребёнок уже ходит. Птицы летают.*"],
  ], row_heads=False),
  P("Look at the **direction** words: *в, на* + accusative, *куда, домой, сюда, туда* go with both; *по* + dative (*around, about*) usually means the repeated verb."),
], exercises=[
  MC("*Куда ты ___?* (Where are you going — right now?)", ["идёшь", "ходишь"], 0, "Now, on the way → **идёшь**."),
  MC("*Я каждый день ___ на работу пешком.*", ["иду", "хожу"], 1, "Habit → **хожу**."),
  MC("*Вчера мы ___ в музей.* (went and came back)", ["шли", "ходили"], 1, "A round trip in the past → **ходили**."),
  MC("*Когда я ___ на работу, пошёл дождь.* (was on my way)", ["шёл", "ходил"], 0, "In progress, one direction → **шёл**."),
  MC("*Самолёт ___ в Москву.* (is flying now)", ["летит", "летает"], 0, "Now → **летит**."),
  MC("*Я люблю ___ на велосипеде.* (riding in general)", ["ехать", "ездить"], 1, "In general → **ездить**."),
  MC("*Он нервно ___ по комнате.*", ["шёл", "ходил"], 1, "Back and forth → **ходил**."),
  FILL("Сейчас мы ___ в Петербург. (ехать)", ["едем"], "мы → **едем**."),
  FILL("Летом они часто ___ на море. (ездить)", ["ездят"], "они → **ездят**."),
  FILL("Я ___ в школу. (ходить — I go regularly)", ["хожу"], "я → **хожу**."),
  FILL("Ты ___ на самолётах? (летать — do you fly, ever?)", ["летаешь"], "ты → **летаешь**."),
]),

SEC("m02-setting-out", "Setting out: пойти, поехать", sub="the perfective по- · ходил and ездил for был", blocks=[
  P("**По-** added to the actual verb makes the perfective: **пойти́, пое́хать, полете́ть**. It stresses the **start** of a trip — *to set off, to leave for*:"),
  EX(("Где старшина? — Он пошёл в штаб.", "Where's the sergeant? — He's gone to HQ (set off, and hasn't come back)."), ("Завтра мы поедем в Москву.", "Tomorrow we'll go to Moscow.")),
  T(["", "пойти́", "пое́хать"], [
    ["Past", "пошёл, пошла́, пошло́, пошли́", "пое́хал, пое́хала, пое́хали"],
    ["Future", "пойду́, пойдёшь, пойду́т", "пое́ду, пое́дешь, пое́дут"],
    ["Imperative", "пойдём(те)! — let's go!", "поезжа́й(те)! — go!"],
  ]),
  NOTE("**ё** in the past of пойти appears only in the masculine: **пошёл** — but пошла, пошло, пошли."),
  H("Пошёл or ходил?"),
  P("**Он пошёл в магазин** — he left for the shop (and is there, or on his way). **Он ходил в магазин** — he went and came back. And **ходил / ездил** can replace **был**: *Вы были на почте? — Да, я **ходил** туда утром.*"),
], exercises=[
  MC("*Где мама? — Она ___ в магазин.* (has gone, isn't back)", ["пошла", "ходила"], 0, "Set off, not back → **пошла**."),
  MC("*Где ты был? — Я ___ в магазин.* (went and came back)", ["пошёл", "ходил"], 1, "Round trip → **ходил**."),
  FILL("Завтра я ___ к врачу. (пойти)", ["пойду"], "я → **пойду**."),
  FILL("Летом мы ___ на юг. (поехать)", ["поедем"], "мы → **поедем**."),
  FILL("После обеда они ___ гулять. (пойти — past)", ["пошли"], "они → **пошли**."),
  FILL("___ в кино! (пойти — let's go, to friends)", ["Пойдёмте", "Пойдемте", "Пойдём", "Пойдем"], "**Пойдём(те)!**"),
  MC("*Вы были в Москве? — Да, я ___ туда в прошлом году.*", ["ездил", "поехал", "ехал"], 0, "**Ездил** = был там."),
  MC("Which is wrong?", ["Я пошёл домой.", "Я пошол домой."], 1, "Spelled **пошёл**."),
]),

SEC("m03-carry-lead-drive", "Carrying, leading, driving, running, swimming", sub="нести / носить · вести / водить · везти / возить · бежать / бегать · плыть / плавать", blocks=[
  P("The same two-way split runs through every verb of motion:"),
  T(["Actual", "Repeated", "Meaning"], [
    ["**нести́** — несу́, несёшь; нёс, несла́", "**носи́ть** — ношу́, но́сишь", "carry (on foot); носить also *wear*"],
    ["**вести́** — веду́, ведёшь; вёл, вела́", "**води́ть** — вожу́, во́дишь", "lead, take (on foot); водить машину — *drive*"],
    ["**везти́** — везу́, везёшь; вёз, везла́", "**вози́ть** — вожу́, во́зишь", "transport, take by vehicle"],
    ["**бежа́ть** — бегу́, бежи́шь, бегу́т", "**бе́гать** — бе́гаю", "run"],
    ["**плыть** — плыву́, плывёшь", "**пла́вать** — пла́ваю", "swim, sail"],
  ]),
  EX(("Он несёт чемодан на вокзал.", "He's carrying the suitcase to the station."), ("Мама ведёт детей в школу.", "Mum is taking the children to school."), ("Автобус везёт туристов в музей.", "The bus is taking the tourists to the museum."), ("Я бегаю каждое утро.", "I run every morning."), ("Ты умеешь плавать?", "Can you swim?")),
  P("Their perfectives are made with **по-** too: **понести́, повести́, повезти́, побежа́ть, поплы́ть** — *set off carrying, start running*."),
], exercises=[
  MC("*Смотри, он ___ большой ящик.* (carrying, now)", ["несёт", "носит"], 0, "Now → **несёт**."),
  MC("*Она всегда ___ очки.* (wears)", ["несёт", "носит"], 1, "*Wear* → **носит**."),
  MC("*Отец ___ сына к врачу.* (taking, on foot, now)", ["ведёт", "везёт"], 0, "On foot → **ведёт**."),
  MC("*Такси ___ нас в аэропорт.*", ["ведёт", "везёт"], 1, "By vehicle → **везёт**."),
  MC("*Мой брат хорошо ___ машину.* (drives)", ["водит", "везёт", "ведёт"], 0, "*Drive a car* → **водить машину**."),
  FILL("Почему ты ___ ? (бежать — why are you running?)", ["бежишь"], "ты → **бежишь**."),
  FILL("Мы ___ в бассейне каждую неделю. (плавать)", ["плаваем"], "мы → **плаваем**."),
  FILL("Вчера он ___ сумку домой. (нести — was carrying)", ["нёс", "нес"], "Past of нести → **нёс**."),
  FILL("Дети ___ к реке. (побежать — ran off)", ["побежали"], "они → **побежали**."),
]),

]
