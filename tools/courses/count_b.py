# Counting Things, part B (DLI Grammar Reference Book II, Lessons 68–72).
from kit import *

SRC = "From the DLI Grammar Reference Book"

SECTIONS = [

SEC("c5-five-and-up", "Five to a hundred in every case", sub="DLI Lesson 71 · 5–20 and 30 · 40, 90, 100 · 50–80 · compound numerals · the accusative", blocks=[
  H("Five and up with a noun"),
  P("d) ПЯТЬ, ШЕСТЬ, СЕМЬ etc. After all other numerals (пять, шесть, семь, etc.) as well as after all compound numbers with 5, 6, 7, etc. as last word, the noun is in the genitive plural: *5 уроков, 35 уроков; 10 страниц, 40 страниц; 11 слов, 111 слов.*"),
  P("Note — 1) Russian compound numerals are never connected by и: hundred and five — сто пять."),
  H("Declension of 5–20 and 30"),
  P("Numerals ending in soft sign (5–20 and 30) are declined like feminine nouns ending in soft sign (ночь, площадь etc.)."),
  T(["", "5 + adjective + noun", "8 + adjective + noun"], [
    ["N.", "пять новых танков", "восемь хороших машин"], ["G.", "пяти новых танков", "восьми хороших машин"], ["D.", "пяти новым танкам", "восьми хорошим машинам"],
    ["A.", "пять новых танков", "восемь хороших машин"], ["I.", "пятью новыми танками", "восемью хорошими машинами"], ["P.", "о пяти новых танках", "о восьми хороших машинах"],
  ]),
  P("Note that the Accusative of both animate and inanimate is always the same as the Nominative: *Я вижу пять новых самолётов. Я вижу пять новых студентов.*"),
  H("The accusative case of compound numerals ending in 1, 2, 3, 4"),
  P("The word один follows the rule of animate and inanimate nouns even when it appears at the end of a compound numeral: *Я вижу двадцать один самолёт. Я вижу двадцать одного студента.* However, два (две), три, четыре appearing at the end of the compound numerals do not follow the above pattern in the Accusative case. Their Accusative (both animate and inanimate) is usually the same as the Nominative: *Я вижу двадцать два самолёта. Я вижу двадцать два студента. Я знаю тридцать пять человек.*"),
  H("Declension of 50, 60, 70, 80"),
  T(["", "50", "60"], [
    ["N.", "пятьдесят самолётов", "шестьдесят пилотов"], ["G.", "пятидесяти самолётов", "шестидесяти пилотов"], ["D.", "пятидесяти самолётам", "шестидесяти пилотам"],
    ["A.", "пятьдесят самолётов", "шестьдесят пилотов"], ["I.", "пятьюдесятью самолётами", "шестьюдесятью пилотами"], ["P.", "о пятидесяти самолётах", "о шестидесяти пилотах"],
  ]),
  P("Note that both parts of these four numerals (50, 60, 70, 80) are declined separately but are written together."),
  H("Declension of 40, 90 and 100"),
  P("Note that there are only two forms: 1) N. & A. сорок, девяносто, сто; 2) In all other cases — сорока, девяноста, ста."),
  H("Declension of compound numerals"),
  T(["", "21", "145"], [
    ["N.", "двадцать один танк", "сто сорок пять танков"], ["G.", "двадцати одного танка", "ста сорока пяти танков"], ["D.", "двадцати одному танку", "ста сорока пяти танкам"],
    ["A.", "двадцать один танк / двадцать одного студента", "сто сорок пять танков / студентов"], ["I.", "двадцатью одним танком", "ста сорока пятью танками"], ["P.", "о двадцати одном танке", "о ста сорока пяти танках"],
  ]),
  P("Note that each component of a compound numeral is declined separately."),
  NOTE("DLI, Lesson 71."),
], exercises=[
  FILL("___ новых танков (пять — Gen.)", ["пяти"], SRC + ", Lesson 71."),
  FILL("___ новыми танками (пять — Instr.)", ["пятью"], SRC + ", Lesson 71."),
  FILL("___ хорошими машинами (восемь — Instr.)", ["восемью"], SRC + ", Lesson 71."),
  MC("Я вижу пять новых ___ .", ["студентов", "студента", "студенты"], 0, "The Accusative of both animate and inanimate is always the same as the Nominative. " + SRC + ", Lesson 71."),
  MC("Я вижу двадцать ___ студента.", ["один", "одного"], 1, "The word один follows the rule even at the end of a compound numeral. " + SRC + ", Lesson 71."),
  MC("Я вижу двадцать ___ студента.", ["два", "двух"], 0, "два, три, четыре at the end of compound numerals: Accusative = Nominative. " + SRC + ", Lesson 71."),
  FILL("___ самолётов (пятьдесят — Gen.)", ["пятидесяти"], SRC + ", Lesson 71."),
  FILL("о ___ танках (сорок)", ["сорока"], "In all other cases — сорока, девяноста, ста. " + SRC + ", Lesson 71."),
  FILL("___ сорока пяти танков (сто — Gen.)", ["ста"], SRC + ", Lesson 71."),
  FILL("двадцатью ___ танком (один — Instr.)", ["одним"], "Each component of a compound numeral is declined separately. " + SRC + ", Lesson 71."),
]),

SEC("c6-hundreds-thousands", "Hundreds, thousands, millions, and «about»", sub="DLI Lessons 68, 69, 72 · 200–900 · тысяча, миллион · reverse word order", blocks=[
  H("Cardinal numerals"),
  T(["", ""], [["200", "двести"], ["300", "триста"], ["400", "четыреста"], ["500", "пятьсот"], ["600", "шестьсот"], ["700", "семьсот"], ["800", "восемьсот"], ["900", "девятьсот"], ["1.000", "тысяча"], ["1.000.000", "миллион"]], row_heads=False),
  P("Тысяча (fem.) and миллион (masc.) are used and declined as nouns and have both singular and plural forms: *одна тысяча, две тысячи, пять тысяч; один миллион, два миллиона, пять миллионов.* Тысяча and миллион are followed in all cases by the Genitive plural of the noun and its qualifier. Тысяча is quite commonly pronounced (but never spelled) like «тыща». Five hundred and fifty five = пятьсот пятьдесят пять."),
  NOTE("DLI, Lesson 69."),
  H("Declension of 200–900"),
  T(["", "200", "500"], [
    ["N.", "двести самолётов", "пятьсот самолётов"], ["G.", "двухсот самолётов", "пятисот самолётов"], ["D.", "двумстам самолётам", "пятистам самолётам"],
    ["A. = N.", "двести самолётов", "пятьсот самолётов"], ["I.", "двумястами самолётами", "пятьюстами самолётами"], ["P.", "о двухстах самолётах", "о пятистах самолётах"],
  ]),
  P("Both parts of these numerals are declined separately but are written together. Note that the second part has plural endings (-стам, -стами, -стах)."),
  NOTE("DLI, Lesson 72."),
  H("Numerical approximation by reverse word order"),
  EX(("Посидите здесь пять минут.", "five minutes"), ("Посидите здесь минут пять.", "about five minutes"), ("10 километров — километров 10", "10 kilometers — about 10 kilometers"), ("25 лет — лет 25", "25 years — about 25 years")),
  P("Note that the preposition (if used) always remains before the numeral:"),
  EX(("Я вернусь через три дня. — Я вернусь дня через три.", ""), ("Он ложится спать в 12 часов. — Он ложится спать часов в 12.", "")),
  NOTE("DLI, Lesson 68."),
], exercises=[
  MC("300", ["тристо", "триста", "трёхсот"], 1, SRC + ", Lesson 69."),
  MC("500", ["пятьсот", "пятисот", "пятсот"], 0, SRC + ", Lesson 69."),
  FILL("две ___ (тысяча)", ["тысячи"], SRC + ", Lesson 69."),
  FILL("пять ___ (тысяча)", ["тысяч"], SRC + ", Lesson 69."),
  FILL("пять ___ (миллион)", ["миллионов"], SRC + ", Lesson 69."),
  FILL("___ самолётов (двести — Gen.)", ["двухсот"], SRC + ", Lesson 72."),
  FILL("о ___ самолётах (пятьсот)", ["пятистах"], "The second part has plural endings (-стам, -стами, -стах). " + SRC + ", Lesson 72."),
  MC("«about five minutes»", ["пять минут", "минут пять"], 1, "The reversed word order shows approximation. " + SRC + ", Lesson 68."),
  MC("«I'll be back in about three days.»", ["Я вернусь через дня три.", "Я вернусь дня через три."], 1, "The preposition always remains before the numeral. " + SRC + ", Lesson 68."),
]),

SEC("c7-ordinals-fractions", "Ordinals, fractions, «equal to»", sub="DLI Lesson 72 · сто тридцать второй · дроби · равен · сколько, несколько in every case", blocks=[
  H("Ordinal numerals"),
  P("Ordinal numerals are used and declined as Adjectives in both Singular and Plural. In compound ordinal numerals only the last element is actually an ordinal, and only this element is declined."),
  EX(("Сто тридцать второй полк.", ""), ("Я служу в сто тридцать втором полку.", ""), ("Он командует сто тридцать вторым полком.", "")),
  P("Note that the Ordinals 50th, 60th, 70th, 80th and 200th–900th are made of two parts. The first part is in the Genitive case: пятидесятый, двухсотый. This part does not change in declension: Gen. пятидесятого, двухсотого. The ordinal numerals «тысячный» and «миллионный» follow the same pattern: пятитысячный, двухмиллионный."),
  H("Fractions (дроби)"),
  T(["", ""], [["1/2", "одна вторая — половина"], ["1/3", "одна третья — треть"], ["1/4", "одна четвёртая — четверть"], ["1/5", "одна пятая"], ["2/7", "две седьмых"], ["3/8", "три восьмых"], ["5/100 (0,05)", "пять сотых"], ["1/1000 (0,001)", "одна тысячная"]], row_heads=False),
  P("(a) In Russian, as in English, numerators are cardinal and denominators are ordinal numbers. Note that the feminine gender is used: одна вторая, две седьмых, etc. This is because the word «ЧАСТЬ» (part) is implied. (b) Both the numerator and the denominator are declined; the noun to which the fraction refers is always in the Genitive case: *три восьмых дюйма; трёх восьмых дюйма; тремя восьмыми дюйма.* (c) The conjunction «и» is used to link the fraction to a whole number: *3 7/8 — три и семь восьмых.* When decimal fractions are used with the whole number, the word «целый» is commonly used: *0,7 — ноль целых и семь десятых; 3,15 — три целых и пятнадцать сотых.* Note that the decimal point in Russian is a comma. (d) The words «ПОЛОВИНА», «ТРЕТЬ» and «ЧЕТВЕРТЬ» are feminine nouns: *5 1/2 — пять с половиной; 3 1/4 — три с четвертью; 2 1/3 — два с третью* (с + Instr.)."),
  H("The word «РАВЕН»"),
  P("РАВЕН (РАВНА, РАВНО, РАВНЫ) is a short adjective commonly used as a predicate: *Здесь все равны.* — Everybody is equal here. A noun or a numeral which follows this word is in the Dative case: *Шесть плюс три равно девяти. Эта скорость равна скорости звука.* Note also: *Мне всё равно.* — I don't care (It's all the same to me)."),
  H("Declension of «сколько», «несколько»"),
  T(["", "сколько", "несколько"], [["N.", "сколько танков", "несколько танков"], ["G.", "скольких танков", "нескольких танков"], ["D.", "скольким танкам", "нескольким танкам"], ["A.", "сколько танков / скольких студентов", "несколько танков / нескольких студентов"], ["I.", "сколькими танками", "несколькими танками"], ["P.", "о скольких танках", "о нескольких танках"]]),
  P("«Сколько» and «несколько» are declined like Adjectives in the plural: *На скольких самолётах есть радары? — Не знаю точно, но на нескольких есть.*"),
  NOTE("DLI, Lesson 72."),
], exercises=[
  FILL("Я служу в сто тридцать ___ полку. (второй)", ["втором"], "Only the last element is declined. " + SRC + ", Lesson 72."),
  FILL("Он командует сто тридцать ___ полком. (второй)", ["вторым"], SRC + ", Lesson 72."),
  MC("1/3", ["одна третья", "один третий", "одна третьих"], 0, "The feminine gender is used, because «часть» is implied. " + SRC + ", Lesson 72."),
  MC("2/7", ["две седьмых", "два седьмых", "две седьмые"], 0, SRC + ", Lesson 72."),
  MC("3,15", ["три и пятнадцать сотых", "три целых и пятнадцать сотых"], 1, "With decimal fractions the word «целый» is commonly used. " + SRC + ", Lesson 72."),
  FILL("пять с ___ (5 1/2)", ["половиной"], "с + Instr. " + SRC + ", Lesson 72."),
  FILL("три с ___ (3 1/4)", ["четвертью"], SRC + ", Lesson 72."),
  FILL("Шесть плюс три равно ___ . (9)", ["девяти"], "A numeral which follows «равен» is in the Dative case. " + SRC + ", Lesson 72."),
  FILL("На ___ самолётах есть радары? (сколько)", ["скольких"], "«Сколько» is declined like an adjective in the plural. " + SRC + ", Lesson 72."),
]),

]
