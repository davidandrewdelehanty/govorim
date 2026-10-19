# Verbs of Motion, part B: prefixes.
from kit import *

SECTIONS = [

SEC("m04-prefixes", "How prefixes work: при- and у-", sub="arriving and leaving · the new aspect pairs", blocks=[
  P("**По-** makes the plain perfective (пойти). **Any other prefix**, added to *both* verbs of the pair, makes a new verb with a direction — and an ordinary imperfective / perfective pair:"),
  T(["", "Imperfective (from ходить, ездить, летать)", "Perfective (from идти, ехать, лететь)"], [
    ["**при-** — arrive, come", "приходи́ть · приезжа́ть · прилета́ть", "прийти́ · прие́хать · прилете́ть"],
    ["**у-** — leave, go away", "уходи́ть · уезжа́ть · улета́ть", "уйти́ · уе́хать · улете́ть"],
  ]),
  NOTE("Two spellings to learn: **-ездить** becomes **-езжать** (приезжа́ть), and **идти** becomes **-йти** (прийти́ — приду́, придёшь; пришёл, пришла́)."),
  P("Now the usual rules of aspect apply: the imperfective for habits and processes, the perfective for one completed act:"),
  EX(("Он всегда приезжает сюда на грузовике.", "He always comes here by truck. (habit)"), ("Сегодня он приехал на автобусе.", "Today he came by bus. (one time)"), ("Когда ты уходишь на работу?", "When do you leave for work? (usually)"), ("Он ушёл час назад.", "He left an hour ago.")),
  P("Directions: **при-** goes *to* (в / на + acc., к + dat.); **у-** goes *from* (из / с + gen., от + gen.)."),
], exercises=[
  FILL("Когда вы ___ домой? (прийти — will you get home)", ["придёте", "придете"], "вы → **придёте**."),
  FILL("Поезд ___ в восемь часов. (прийти — arrived)", ["пришёл", "пришел"], "**пришёл**."),
  FILL("Он ___ из Москвы вчера. (приехать)", ["приехал"], "**приехал**."),
  FILL("Она ___ час назад. (уйти — she left)", ["ушла"], "Feminine past → **ушла**."),
  MC("*Каждый день отец ___ с работы в шесть.*", ["приходит", "придёт"], 0, "Every day → imperfective."),
  MC("*Сегодня отец ___ поздно.* (will come, once)", ["будет приходить", "придёт"], 1, "One act → perfective future."),
  MC("*Не ___ ! Подожди меня.* (don't leave)", ["уходи", "уйди"], 0, "*Don't* → imperfective."),
  MC("*Обычно самолёт в Лондон ___ в 9 часов.* (usually leaves)", ["улетает", "улетит"], 0, "Usually → imperfective **улетает**."),
  MC("Pick the right spelling: *Они ___ из Киева.*", ["уехали", "уезжали", "ушли"], 0, "By vehicle, completed → **уехали**."),
]),

SEC("m05-in-out", "Going in and going out: в- and вы-", sub="входить / войти · выходить / выйти", blocks=[
  T(["", "Imperfective", "Perfective", "Where?"], [
    ["**в(о)-** — go in", "входи́ть · въезжа́ть · влета́ть", "войти́ · въе́хать · влете́ть", "**в / на** + acc."],
    ["**вы-** — go out", "выходи́ть · выезжа́ть · вылета́ть", "вы́йти · вы́ехать · вы́лететь", "**из / с** + gen."],
  ]),
  P("Before **-йти**, a prefix ending in a consonant adds **о**: **войти́** (войду́, вошёл), **подойти́**, **отойти́**, **обойти́**. Before **-ехать**, it adds a hard sign **ъ**: **въе́хать**, **подъе́хать**, **объе́хать**."),
  P("In the perfective, **вы-** always takes the stress: **вы́йти, вы́ехать, вы́шел, вы́йду**."),
  EX(("Я вхожу в эту комнату каждый день.", "I come into this room every day."), ("Я вошёл в комнату и открыл окно.", "I came into the room and opened the window."), ("Мы въезжаем в город.", "We're driving into town."), ("Автомобиль въехал в гараж.", "The car drove into the garage."), ("Он вышел из дома в семь.", "He left the house at seven.")),
], exercises=[
  FILL("Он ___ в комнату и сел. (войти)", ["вошёл", "вошел"], "**вошёл**."),
  FILL("Мы ___ из дома в восемь. (выйти — we left)", ["вышли"], "мы → **вышли**."),
  FILL("Машина ___ в гараж. (въехать)", ["въехала"], "Hard sign: **въехала**."),
  FILL("Я ___ на следующей остановке. (выйти — I'll get off)", ["выйду"], "я → **выйду**."),
  MC("*Вы ___ на следующей?* (Are you getting off at the next stop? — a common bus question)", ["выходите", "выйдете"], 0, "The everyday question uses the imperfective: **Вы выходите?**"),
  MC("*Кто-то ___ в комнату.* (someone came in)", ["вошёл", "входил", "войшёл"], 0, "**вошёл**."),
  MC("Which spelling is right?", ["вьехать", "въехать", "вехать"], 1, "**въехать** — with ъ."),
  MC("*Он ___ из Москвы рано утром.* (drove out)", ["выехал", "выезжал", "въехал"], 0, "Out, once → **выехал**."),
]),

SEC("m06-toward-away", "Approaching and moving off: под- and от-", sub="подходить к · отходить от", blocks=[
  T(["", "Imperfective", "Perfective", "Takes"], [
    ["**под(о)-** — approach, come up to", "подходи́ть · подъезжа́ть · подлета́ть", "подойти́ · подъе́хать · подлете́ть", "**к** + dat."],
    ["**от(о)-** — move away from", "отходи́ть · отъезжа́ть · отлета́ть", "отойти́ · отъе́хать · отлете́ть", "**от** + gen."],
  ]),
  EX(("Я подошёл к учителю.", "I went up to the teacher."), ("Я отошёл от учителя.", "I moved away from the teacher."), ("Мы подъехали к гаражу.", "We drove up to the garage."), ("Поезд отходит в десять.", "The train leaves (pulls out) at ten.")),
  P("**Отходи́ть** is the word for a train or bus leaving the platform: *Когда отходит поезд?*"),
], exercises=[
  FILL("Он ___ к окну. (подойти — went up to)", ["подошёл", "подошел"], "**подошёл**."),
  FILL("Автобус ___ к остановке. (подъехать — drove up)", ["подъехал"], "Hard sign: **подъехал**."),
  FILL("___ от двери! (отойти — step away, to one person)", ["Отойди"], "Imperative → **отойди**."),
  MC("*Мы подошли ___ дому.*", ["к", "от", "до"], 0, "**подойти к** + dative."),
  MC("*Он отошёл ___ окна.*", ["к", "от", "из"], 1, "**отойти от** + genitive."),
  MC("*Когда ___ поезд на Москву?* (When does the train leave?)", ["отходит", "уходит", "выходит"], 0, "Trains **отходят** from the platform."),
  MC("*Машина ___ от дома и поехала по улице.*", ["отъехала", "отехала", "отьехала"], 0, "**отъехала**."),
]),

SEC("m07-reach-cross", "Reaching and crossing: до- and пере-", sub="доходить до · переходить через · moving house", blocks=[
  T(["", "Imperfective", "Perfective", "Takes"], [
    ["**до-** — go as far as; reach", "доходи́ть · доезжа́ть · долета́ть", "дойти́ · дое́хать · долете́ть", "always **до** + gen."],
    ["**пере-** — cross; move from one place to another", "переходи́ть · переезжа́ть · перелета́ть", "перейти́ · перее́хать · перелете́ть", "**через** + acc., or a direct object"],
  ]),
  EX(("Я доехал до угла и повернул направо.", "I drove as far as the corner and turned right."), ("У меня было мало бензина, но я всё-таки доехал до города.", "I was low on petrol, but I reached the town all the same."), ("Танки дошли до леса.", "The tanks reached the forest."), ("Когда вы дойдёте до почты, поверните направо.", "When you get to the post office, turn right.")),
  EX(("Мы перешли (через) улицу.", "We crossed the street."), ("Линдберг перелетел через Атлантический океан.", "Lindbergh flew across the Atlantic."), ("Завтра мы переедем в наш новый дом.", "Tomorrow we move into our new house.")),
  P("**Переезжа́ть / перее́хать** on its own means *to move house*: *Мы переехали в Москву.*"),
], exercises=[
  FILL("Как ___ до вокзала? (дойти — how do I get to the station on foot?)", ["дойти"], "Infinitive: **Как дойти до вокзала?**"),
  FILL("Мы ___ до города за час. (доехать)", ["доехали"], "мы → **доехали**."),
  FILL("Осторожно ___ улицу! (перейти — cross, imperative to one person)", ["перейди", "переходи"], "**Перейди** (or *переходи*)."),
  FILL("В прошлом году они ___ в Киев. (переехать — moved)", ["переехали"], "**переехали**."),
  MC("*Я дошёл ___ угла.*", ["до", "к", "в"], 0, "**до** always follows доходить / дойти."),
  MC("*Не ___ улицу на красный свет!*", ["переходите", "перейдите"], 0, "*Don't* → imperfective."),
  MC("*Самолёт ___ через океан за семь часов.*", ["перелетел", "прилетел", "долетел"], 0, "Across → **перелетел**."),
  MC("*We moved to a new apartment.*", ["Мы перешли на новую квартиру.", "Мы переехали на новую квартиру."], 1, "Moving house → **переехать**."),
]),

SEC("m08-through-around", "Through, past and around: про- and об-", sub="проходить мимо · обходить вокруг", blocks=[
  T(["", "Imperfective", "Perfective", "Meanings"], [
    ["**про-**", "проходи́ть · проезжа́ть · пролета́ть", "пройти́ · прое́хать · пролете́ть", "through (**через** + acc.), past (**ми́мо** + gen.), between (**ме́жду** + instr.); a distance; go too far"],
    ["**об(о)-**", "обходи́ть · объезжа́ть · облета́ть", "обойти́ · объе́хать · облете́ть", "around (**вокру́г** + gen.); round an obstacle; make the rounds of (+ acc.)"],
  ]),
  EX(("Мы проехали через лес.", "We drove through the forest."), ("Мы прошли мимо вашего дома.", "We walked past your house."), ("Я проехал свою остановку.", "I missed my stop (went past it)."), ("Мы прошли пять километров.", "We walked five kilometres.")),
  EX(("Самолёт облетел вокруг аэродрома.", "The plane circled the airfield."), ("Мы объехали это место.", "We drove round (avoided) that spot."), ("Я обошёл все магазины.", "I went round all the shops.")),
  P("**Проходи́те!** — *Come in! Go through!* — is what you say to a guest at the door."),
], exercises=[
  MC("*Мы прошли ___ вашего дома.* (past)", ["мимо", "через", "вокруг"], 0, "Past → **мимо** + gen."),
  MC("*Мы проехали ___ лес.* (through)", ["мимо", "через", "вокруг"], 1, "Through → **через** + acc."),
  MC("*Самолёт облетел ___ аэродрома.* (around)", ["мимо", "через", "вокруг"], 2, "Around → **вокруг** + gen."),
  FILL("Я ___ свою остановку! (проехать — I missed my stop)", ["проехал", "проехала"], "**проехал(а)**."),
  FILL("Я ___ все магазины, но ничего не нашёл. (обойти)", ["обошёл", "обошел", "обошла"], "**обошёл**."),
  FILL("___ , пожалуйста! (проходить — come on in, politely)", ["Проходите"], "**Проходите!**"),
  MC("*Мы ___ десять километров.* (walked — a distance)", ["прошли", "перешли", "обошли"], 0, "A distance → **прошли**."),
  MC("*На дороге была яма, и мы её ___.* (drove round it)", ["объехали", "проехали", "переехали"], 0, "Round an obstacle → **объехали**."),
]),

SEC("m09-drop-by-down", "Dropping in, going down: за- and с-", sub="заходить за · сходить с · за + instrumental", blocks=[
  T(["", "Imperfective", "Perfective", "Meanings"], [
    ["**за-**", "заходи́ть · заезжа́ть · залета́ть", "зайти́ · зае́хать · залете́ть", "drop in, call on (**к** + dat., **в / на** + acc.); go behind (**за** + acc.); go to fetch (**за** + instr.)"],
    ["**с(о)-**", "сходи́ть · съезжа́ть · слета́ть", "сойти́ · съе́хать · слете́ть", "go down, get off (**с** + gen.)"],
  ]),
  EX(("Зайди ко мне вечером!", "Drop by this evening!"), ("Солнце зашло за тучу.", "The sun went behind a cloud."), ("Я зайду за тобой в семь.", "I'll call for you at seven.")),
  EX(("Мы съезжаем с горы.", "We're driving down the hill."), ("Автомобиль съехал с дороги.", "The car went off the road."), ("Он сошёл с поезда.", "He got off the train.")),
  H("за + instrumental — to fetch"),
  P("After any going-verb, **за** + instrumental means *for, to get*: **Он пошёл за газе́той.** *He went for a newspaper.* **Пошли́те за до́ктором!** *Send for the doctor!*"),
], exercises=[
  FILL("___ ко мне завтра! (зайти — drop by, to a friend)", ["Зайди"], "**Зайди**."),
  FILL("Я ___ за тобой в восемь. (зайти — I'll call for you)", ["зайду"], "я → **зайду**."),
  FILL("Он пошёл за ___ . (хлеб — to get bread)", ["хлебом"], "**за** + instrumental."),
  FILL("Мы ___ с горы на лыжах. (съехать — skied down)", ["съехали"], "Hard sign: **съехали**."),
  MC("*Солнце ___ за тучу.*", ["зашло", "вошло", "ушло"], 0, "Behind → **зашло за**."),
  MC("*На какой остановке вы ___?* (get off)", ["сходите", "заходите", "уходите"], 0, "Get off → **сходить с**."),
  MC("*Пошлите ___ врачом!* (send for the doctor)", ["за", "к", "по"], 0, "**за** + instrumental."),
]),

SEC("m10-round-trips", "Quick trips and a while: сходить, походить", sub="с- and по- with ходить, ездить, летать", blocks=[
  P("A prefix added to **ходить / ездить / летать** usually just makes the imperfective of a new pair (приходить). But two prefixes make **perfectives** of these verbs instead:"),
  T(["", "on foot", "by vehicle", "by air", "Means"], [
    ["**с-**", "сходи́ть", "съе́здить", "слета́ть", "one quick round trip — there and back"],
    ["**по-**", "походи́ть", "пое́здить", "полета́ть", "for a while, a bit"],
  ]),
  EX(("Мне надо сходить на почту за письмами.", "I need to pop to the post office for the letters."), ("Я съезжу на вокзал и узнаю, когда отходит поезд.", "I'll run over to the station and find out when the train leaves."), ("Он сходил в библиотеку и взял книгу.", "He went to the library and got a book.")),
  EX(("Он походил по комнате и сел за стол.", "He walked around the room for a bit and sat down at the table."), ("Мы поездили по городу и поехали домой.", "We drove around town for a while and went home.")),
  NOTE("Don't confuse **сходи́ть** (*pop over and back*, perfective — схожу́, схо́дишь) with **сходи́ть** (*get off, go down*, imperfective — схожу́, схо́дишь)! Context tells them apart."),
  T(["Imperfective pair", "Plain perfective", "For a while", "Round trip"], [
    ["идти́ — ходи́ть", "пойти́", "походи́ть", "сходи́ть"], ["е́хать — е́здить", "пое́хать", "пое́здить", "съе́здить"], ["лете́ть — лета́ть", "полете́ть", "полета́ть", "слета́ть"],
  ], caption="The whole family"),
], exercises=[
  FILL("Мне надо ___ в магазин за хлебом. (quick trip, on foot)", ["сходить"], "**сходить**."),
  FILL("В выходные мы ___ к бабушке. (съездить — we went and came back)", ["съездили"], "**съездили**."),
  FILL("Он немного ___ по парку и пошёл домой. (походить — walked around a bit)", ["походил"], "**походил**."),
  MC("*Я ___ на вокзал и вернусь через час.*", ["съезжу", "поеду", "езжу"], 0, "There and back → **съезжу**."),
  MC("*Он пошёл в библиотеку* vs *Он сходил в библиотеку*: which means he is back already?", ["пошёл", "сходил"], 1, "**Сходил** — a round trip, completed."),
  MC("*Мы ___ по Европе две недели.* (travelled around for a while)", ["поездили", "поехали", "съездили"], 0, "For a while → **поездили**."),
  MC("*Я хочу ___ на вертолёте.* (have a flight, for a bit)", ["полетать", "полететь", "слетать"], 0, "For a while → **полетать**."),
]),

]
