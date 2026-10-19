# Verbs of Motion, part C: prefixed carrying verbs and review.
from kit import *

SECTIONS = [

SEC("m11-bring-take", "Bringing and taking away", sub="принести, привести, привезти · унести, увести, увезти · and the rest", blocks=[
  P("The prefixes work on the carrying verbs exactly as on the going verbs. The **actual** verb gives the perfective, the **repeated** verb the imperfective:"),
  T(["", "carry (нести / носить)", "lead (вести / водить)", "transport (везти / возить)"], [
    ["**при-** bring", "приноси́ть / принести́", "приводи́ть / привести́", "привози́ть / привезти́"],
    ["**у-** take away", "уноси́ть / унести́", "уводи́ть / увести́", "увози́ть / увезти́"],
    ["**в-** bring in", "вноси́ть / внести́", "вводи́ть / ввести́", "ввози́ть / ввезти́ (import)"],
    ["**вы-** take out", "выноси́ть / вы́нести", "выводи́ть / вы́вести", "вывози́ть / вы́везти (export)"],
    ["**пере-** carry across; translate", "переноси́ть / перенести́", "переводи́ть / перевести́", "перевози́ть / перевезти́"],
  ]),
  P("Things you carry by hand: **нести**. People or animals you lead: **вести**. Anything by vehicle: **везти**."),
  EX(("Принеси мне воды, пожалуйста.", "Bring me some water, please."), ("Я привёл друга на вечер.", "I brought a friend to the party."), ("Он привёз подарки из Франции.", "He brought presents back from France."), ("Он перевёл книгу на английский.", "He translated the book into English.")),
  NOTE("**Переводи́ть / перевести́** also means *to translate*: *переводить с русского на английский*."),
], exercises=[
  FILL("___ мне книгу, пожалуйста! (принести — to one person)", ["Принеси"], "**Принеси**."),
  FILL("Она ___ детей в парк. (повести — set off taking)", ["повела"], "Feminine past → **повела**."),
  FILL("Что ты ___ из Москвы? (привезти — brought back)", ["привёз", "привез", "привезла"], "**привёз** (by vehicle)."),
  FILL("Кто ___ мою сумку? (унести — took away)", ["унёс", "унес", "унесла"], "**унёс**."),
  MC("*Я ___ на вечер свою подругу.* (brought, on foot)", ["принёс", "привёл", "привёз"], 1, "A person on foot → **привёл**."),
  MC("*Он ___ цветы маме.* (brought, by hand)", ["принёс", "привёл", "привёз"], 0, "Carried by hand → **принёс**."),
  MC("*Россия ___ нефть.* (exports)", ["вывозит", "выводит", "выносит"], 0, "By vehicle out → **вывозит** (export)."),
  MC("*Кто ___ этот текст на английский?* (translated)", ["перевёз", "перевёл", "перенёс"], 1, "*Translate* → **перевести**."),
]),

SEC("m12-review", "Verbs of motion: putting it together", sub="mixed practice in the DLI style", blocks=[
  P("A summary of everything in this course:"),
  T(["Question", "Then use"], [
    ["Now, one direction? A single trip at a moment?", "**идти, ехать, лететь, нести, вести, везти**"],
    ["Habit, round trip, around and about, ability?", "**ходить, ездить, летать, носить, водить, возить**"],
    ["Setting off?", "**пойти, поехать, полететь, понести…**"],
    ["A direction (in, out, up to, across…)?", "prefix + verb: **при-, у-, в-, вы-, под-, от-, до-, пере-, про-, об-, за-, с-** — then choose the aspect as for any verb"],
    ["A quick trip there and back? A while?", "**сходить, съездить, слетать** · **походить, поездить, полетать**"],
  ]),
  P("Remember the spellings: **-йти** (прийти, уйти, найти), **о** before **-йти** after a consonant (войти, подойти, отойти, обойти), **ъ** before **-ехать** (въехать, подъехать, отъехать, объехать, съехать), and **-езжать** for the imperfective (приезжать, уезжать)."),
], exercises=[
  FILL("Эта дорога ___ в город. (вести — leads)", ["ведёт", "ведет"], "A road **ведёт** somewhere."),
  FILL("Что вы ___ в портфеле? (носить — carry, habitually)", ["носите"], "вы → **носите**."),
  FILL("Этот автобус ___ пассажиров на станцию. (возить — regularly)", ["возит"], "Regular service → **возит**."),
  FILL("Кто ___ этот грузовик? (водить — drives)", ["водит"], "**водит** — drives."),
  FILL("Он ___ это пальто только зимой. (носить — wears)", ["носит"], "**носит** — wears."),
  MC("*Я обычно ___ детей в парк в выходной.*", ["веду", "вожу"], 1, "Usually → **вожу**."),
  MC("*Самолёт ___ из Москвы в 6 утра.* (took off, once)", ["вылетел", "вылетал", "вылетит"], 0, "Once, past → **вылетел**."),
  MC("*Когда ты ___ домой, позвони мне.* (get home — future)", ["придёшь", "приходишь", "пришёл"], 0, "Future after **когда** → **придёшь**."),
  MC("*Не ___ из комнаты!* (don't go out)", ["выходи", "выйди"], 0, "*Don't* → imperfective."),
  MC("*Мы ___ через мост и повернули налево.*", ["перешли", "прошли", "дошли"], 0, "Across → **перешли**."),
  FILL("Сестра ___ младшего брата в парк через десять минут. (повести — will take)", ["поведёт", "поведет"], "Perfective future: **поведёт**."),
  MC("*Вера любит ___ на поезде, но не любит ___.* (travel / fly — in general)", ["ездить / летать", "ехать / лететь"], 0, "In general → **ездить**, **летать**."),
]),

]
