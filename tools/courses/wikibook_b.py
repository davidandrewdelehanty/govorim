# The Russian Wikibook course, part 2: verbs.
from kit import *

SECTIONS = [

SEC("present", "The present tense", sub="the two conjugations", blocks=[
  P("A Russian verb changes its ending for each person. Take off the infinitive's **-ть** and add the endings. There are two patterns — the **first conjugation** (endings with **е**) and the **second** (endings with **и**):"),
  T(["", "1st: чита́ть (*read*)", "2nd: говори́ть (*speak*)"], [
    ["я", "чита́**ю**", "говор**ю́**"],
    ["ты", "чита́**ешь**", "говор**и́шь**"],
    ["он, она, оно", "чита́**ет**", "говор**и́т**"],
    ["мы", "чита́**ем**", "говор**и́м**"],
    ["вы", "чита́**ете**", "говор**и́те**"],
    ["они", "чита́**ют**", "говор**я́т**"],
  ]),
  P("Most verbs in **-ать** and **-ять** are first conjugation (знать, де́лать, гуля́ть, понима́ть). Most in **-ить** are second (люби́ть, звони́ть, ходи́ть), and so are a few in **-еть** and **-ать** you learn one by one (смотре́ть, ви́деть, слы́шать, держа́ть)."),
  H("The я-form of the second conjugation"),
  P("A second-conjugation verb whose stem ends in **б, в, п, м, ф** adds **л** in the я-form only: люби́ть → **люблю́**, but лю́бишь, лю́бит. And **д → ж**, **т → ч**, **с → ш**, **з → ж**: ходи́ть → **хожу́**, ви́деть → **ви́жу**, проси́ть → **прошу́**."),
  P("After **ж, ш, щ, ч** the endings are spelled **-у, -ат**: слы́шать → слы́ш**у**, слы́ш**ат**."),
], exercises=[
  FILL("Я ___ книгу. (читать)", ["читаю"], "1st conjugation, я → **-ю**: **читаю**."),
  FILL("Ты ___ по-русски? (говорить)", ["говоришь"], "2nd conjugation, ты → **-ишь**."),
  FILL("Они ___ в парке. (гулять)", ["гуляют"], "1st conjugation, они → **-ют**."),
  FILL("Мы ___ телевизор. (смотреть)", ["смотрим"], "**Смотреть** is 2nd conjugation: мы смотр**им**."),
  FILL("Я ___ музыку. (любить)", ["люблю"], "**б** adds **л** in the я-form: **люблю**."),
  FILL("Я ___ в школу. (ходить)", ["хожу"], "**д → ж** in the я-form: **хожу**."),
  FILL("Вы ___ меня? (понимать)", ["понимаете"], "1st conjugation, вы → **-ете**."),
  MC("Which ending does **они** take with **говорить**?", ["-ют", "-ят", "-ут"], 1, "2nd conjugation: они говор**ят**."),
  MC("*She knows* is…", ["она знаит", "она знает", "она знат"], 1, "**Знать** is 1st conjugation: она зна**ет**."),
  MC("Pick the right form: *Они ___ шум.* (слышать — to hear)", ["слышят", "слышат", "слышают"], 1, "After **ш**, **-ат** not -ят: **слышат**."),
]),

SEC("past", "The past tense", sub="-л, -ла, -ло, -ли", blocks=[
  P("The past tense is the easiest thing in Russian. Take off **-ть**, add **-л**, then match the **subject's gender and number** — not its person:"),
  T(["Subject", "Ending", "читать"], [
    ["он, я (a man), ты (a man)", "**-л**", "чита́**л**"],
    ["она, я (a woman), ты (a woman)", "**-ла**", "чита́**ла**"],
    ["оно", "**-ло**", "чита́**ло**"],
    ["они, мы, вы", "**-ли**", "чита́**ли**"],
  ]),
  P("So a woman says **я чита́ла**, a man says **я чита́л**. **Вы** always takes **-ли**, even said politely to one person: *Вы читали эту книгу?*"),
  H("Ones to learn"),
  T(["Infinitive", "он", "она", "они"], [
    ["идти́ (*go*)", "**шёл**", "шла", "шли"],
    ["мочь (*can*)", "**мог**", "могла́", "могли́"],
    ["есть (*eat*)", "**ел**", "е́ла", "е́ли"],
    ["нести́ (*carry*)", "**нёс**", "несла́", "несли́"],
  ]),
  P("Reflexive verbs keep **-ся** after a consonant and **-сь** after a vowel: он занима́л**ся**, она занима́ла**сь**."),
], exercises=[
  FILL("Вчера Анна ___ письмо. (писать)", ["писала"], "Анна → feminine → **-ла**."),
  FILL("Мой брат ___ в Москве. (жить)", ["жил"], "Masculine → **-л**: **жил**."),
  FILL("Мы ___ футбол. (смотреть)", ["смотрели"], "**Мы** → **-ли**."),
  FILL("Солнце ___ ярко. (светить — to shine)", ["светило"], "Neuter **солнце** → **-ло**."),
  FILL("Ты ___ мне? (звонить; you are speaking to a woman)", ["звонила"], "A woman → **-ла**."),
  MC("A man says: *I was reading.*", ["Я читала.", "Я читал.", "Я читали."], 1, "He matches the past to himself: **читал**."),
  MC("*Вы ___ этот фильм?* (смотреть, said to one person, politely)", ["смотрел", "смотрела", "смотрели"], 2, "**Вы** always takes **-ли**."),
  FILL("Он ___ домой. (идти)", ["шёл", "шел"], "**Идти** has an irregular past: **шёл**."),
  FILL("Она не ___ прийти. (мочь)", ["могла"], "**Мочь**: мог, **могла**, могли."),
  MC("*She was studying* (заниматься)…", ["она занималась", "она занималася", "она занималсь"], 0, "After a vowel, **-сь**: **занималась**."),
]),

SEC("future", "The future tense", sub="буду читать · прочитаю", blocks=[
  P("How you make the future depends on the verb's **aspect** (next section). With an **imperfective** verb — an action seen as a process, or repeated — use **буду** + the infinitive:"),
  T(["", "быть in the future", "+ infinitive"], [
    ["я", "**бу́ду**", "читать"], ["ты", "**бу́дешь**", "читать"], ["он, она", "**бу́дет**", "читать"],
    ["мы", "**бу́дем**", "читать"], ["вы", "**бу́дете**", "читать"], ["они", "**бу́дут**", "читать"],
  ]),
  P("A **perfective** verb — one action, done and finished — has no present tense. Its present-tense *form* means the future: **прочита́ю** = *I will read (it through)*. **Я напишу́ письмо** — *I'll write the letter.*"),
  EX(("Завтра я буду читать весь день.", "Tomorrow I'll be reading all day. (a process)"), ("Завтра я прочитаю эту книгу.", "Tomorrow I'll read this book (to the end). (one finished act)")),
  P("**Буду** on its own is the future of *to be*: **Я бу́ду до́ма.** *I'll be at home.*"),
], exercises=[
  FILL("Завтра мы ___ работать. (we will be working)", ["будем"], "мы → **будем**."),
  FILL("Что ты ___ делать вечером?", ["будешь"], "ты → **будешь**."),
  FILL("Они ___ дома в субботу.", ["будут"], "они → **будут**."),
  MC("*I will write (and finish) the letter* — which?", ["Я буду написать письмо.", "Я напишу письмо.", "Я пишу письмо."], 1, "A perfective verb's present form is its future: **напишу**. Never *буду* + a perfective infinitive."),
  MC("Which is wrong?", ["Я буду читать.", "Я прочитаю.", "Я буду прочитать."], 2, "**Буду** goes only with imperfective verbs."),
  MC("*Он ___ врачом.* (He will be a doctor.)", ["будет", "будут", "буду"], 0, "он → **будет**."),
  FILL("Я ___ тебе завтра. (позвонить, perfective — I'll call)", ["позвоню"], "Perfective → present form = future: **позвоню**."),
  MC("*Я буду смотреть фильм* means…", ["I watched the film.", "I'll be watching a film.", "I'll have watched the film."], 1, "Imperfective future: an ongoing action."),
]),

SEC("aspect", "Aspect", sub="imperfective and perfective", blocks=[
  P("Almost every Russian verb comes in a **pair**: an **imperfective** for the action as a process, a habit, or a fact; and a **perfective** for one action complete, with a result."),
  T(["Imperfective", "Perfective", ""], [
    ["де́лать", "**с**де́лать", "do"], ["писа́ть", "**на**писа́ть", "write"], ["чита́ть", "**про**чита́ть", "read"],
    ["реша́ть", "реш**и́**ть", "solve, decide"], ["покупа́ть", "куп**и́**ть", "buy"], ["говори́ть", "**сказа́ть**", "say"],
    ["брать", "**взять**", "take"],
  ]),
  P("Pairs are made by adding a prefix (**на**писать), changing the suffix (реш**а**ть / реш**и**ть), or are different words entirely (говорить / сказать)."),
  H("Which one?"),
  L("Process, how long, how often → **imperfective**: *Я **читал** весь вечер.* I was reading all evening. *Я **читаю** каждый день.*",
    "One finished act, a result → **perfective**: *Я **прочитал** книгу.* I read (finished) the book.",
    "Words like **всегда́, ча́сто, ка́ждый день, до́лго** call for the imperfective; **вдруг, наконе́ц, сра́зу** for the perfective."),
  EX(("Она долго писала письмо и наконец написала.", "She spent a long time writing the letter, and finally wrote it.")),
], exercises=[
  MC("*Я ___ эту книгу вчера и сегодня отдал её другу.* (finished it)", ["читал", "прочитал"], 1, "A finished act with a result → perfective **прочитал**."),
  MC("*Каждое утро он ___ кофе.*", ["пьёт", "выпьет"], 0, "**Каждое утро** — a habit → imperfective."),
  MC("*Мы ___ весь вечер.* (We were talking all evening.)", ["говорили", "сказали"], 0, "Duration → imperfective."),
  MC("*Вдруг он ___: «Стой!»*", ["говорил", "сказал"], 1, "**Вдруг** — one sudden act → perfective."),
  MC("The perfective partner of **делать** is…", ["выделать", "сделать", "поделать"], 1, "**Сделать**."),
  MC("The perfective partner of **покупать** is…", ["купить", "покупить", "закупать"], 0, "**Купить**."),
  MC("The perfective partner of **брать** is…", ["забрать", "взять", "брать"], 1, "**Взять** — a different word."),
  FILL("Я долго ___ задачу и наконец ___ её. (решать / решить)", ["решал решил"], "Process first (**решал**), then the result (**решил**). Type both words, separated by a space.", hint="Two words"),
  MC("*Я часто ___ домой поздно.* (возвращаться / вернуться)", ["возвращаюсь", "вернусь"], 0, "**Часто** — repeated → imperfective."),
]),

SEC("reflexive", "Reflexive verbs, and three ways to *study*", sub="-ся · учить, учиться, изучать, заниматься", blocks=[
  P("Verbs ending in **-ся** (after a consonant) or **-сь** (after a vowel) are **reflexive**. Often the action falls back on the subject — **мы́ться**, *to wash (oneself)* — but just as often **-ся** simply belongs to the verb: **смея́ться** (*laugh*), **нра́виться** (*please*)."),
  T(["", "занима́ться (*study, do*)"], [
    ["я", "занима́ю**сь**"], ["ты", "занима́ешь**ся**"], ["он, она", "занима́ет**ся**"],
    ["мы", "занима́ем**ся**"], ["вы", "занима́ете**сь**"], ["они", "занима́ют**ся**"],
  ]),
  H("Study, learn, do homework"),
  T(["Verb", "Means", "Example"], [
    ["**учи́ть** + acc.", "learn (by heart), memorise; teach", "Я учу́ слова́."],
    ["**учи́ться**", "be a student (somewhere)", "Я учу́сь в университе́те."],
    ["**изуча́ть** + acc.", "study a subject in depth", "Он изуча́ет исто́рию."],
    ["**занима́ться**", "do homework, study (and do sport)", "Мы занима́емся в библиоте́ке."],
  ]),
  H("Also: тоже and также"),
  P("**То́же** — *also, too*, when something else is said about a new subject: *Я студент. Он **тоже** студент.* **Та́кже** — *also, as well*, adding something new about the same subject: *Он студент и **также** работает.*"),
], exercises=[
  FILL("Я ___ в школе. (учиться — I'm a schoolchild)", ["учусь"], "я → **учусь**."),
  FILL("Они ___ спортом. (заниматься)", ["занимаются"], "они → **занимаются** (consonant before, so **-ся**)."),
  FILL("Вы ___ ? (заниматься — are you studying?)", ["занимаетесь"], "Vowel before → **-сь**: **занимаетесь**."),
  MC("*Я ___ новые слова каждый день.* (memorise)", ["учусь", "учу", "изучаюсь"], 1, "**Учить** + acc.: learn by heart."),
  MC("*Моя сестра ___ в Москве.* (is a student)", ["учит", "учится", "изучает"], 1, "**Учиться** — to be a student somewhere."),
  MC("*Он ___ русскую литературу в университете.* (studies the subject)", ["изучает", "учится", "занимается"], 0, "**Изучать** + acc. — study a subject."),
  MC("*Я люблю кофе. Она ___ любит кофе.*", ["тоже", "также"], 0, "New subject, same thing said → **тоже**."),
  MC("*Он поёт и ___ играет на гитаре.*", ["тоже", "также"], 1, "Same subject, something new → **также**."),
]),

SEC("going", "Going: идти, ехать, ходить, ездить", sub="on foot or by vehicle · now or habitually", blocks=[
  P("Russian splits *go* four ways. **On foot** or **by vehicle**? And **one way, now** — or **around, habitually, there and back**?"),
  T(["", "On foot", "By vehicle"], [
    ["One direction, now", "**идти́**: иду́, идёшь, иду́т", "**е́хать**: е́ду, е́дешь, е́дут"],
    ["Habitual, round trips", "**ходи́ть**: хожу́, хо́дишь, хо́дят", "**е́здить**: е́зжу, е́здишь, е́здят"],
  ]),
  EX(("Я иду в магазин.", "I'm going to the shop (on my way now)."), ("Я часто хожу в театр.", "I often go to the theatre."),
     ("Мы едем в Москву.", "We're going to Moscow (by train, car…)."), ("Каждое лето мы ездим на море.", "Every summer we go to the seaside.")),
  P("In the past, **ходил** / **ездил** means a round trip: *Вчера я ходил в кино* — *Yesterday I went to the cinema (and came back)*."),
  NOTE("**Где?** (*where?* — at a place) takes the prepositional: *в школ**е***. **Куда́?** (*where to?*) takes the accusative: *в школ**у***. You'll meet both in the case sections."),
], exercises=[
  MC("*Смотри, мама ___ к нам!* (Look, Mum is coming over — on foot.)", ["идёт", "ходит", "едет"], 0, "On foot, one way, now → **идёт**."),
  MC("*Я каждый день ___ на работу пешком.*", ["иду", "хожу", "езжу"], 1, "Every day, on foot → **хожу**."),
  MC("*Сейчас мы ___ в Петербург на поезде.*", ["едем", "ездим", "идём"], 0, "Now, by vehicle → **едем**."),
  MC("*Летом они часто ___ на дачу.* (by car)", ["едут", "ездят", "ходят"], 1, "Often, by vehicle → **ездят**."),
  FILL("Куда ты ___ ? (идти — where are you going?)", ["идёшь", "идешь"], "ты → **идёшь**."),
  FILL("Я ___ в школу. (ходить, habitually)", ["хожу"], "я → **хожу** (д → ж)."),
  FILL("Я ___ на машине. (ездить, I drive regularly)", ["езжу"], "я → **езжу** (зд → зж)."),
  MC("*Вчера я ___ в музей.* (went and came back)", ["шёл", "ходил"], 1, "A round trip in the past → **ходил**."),
]),

]
