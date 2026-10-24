# Counting Things. Transcribed from the DLI Russian Basic Course, Grammar
# Reference Book I (1970) and II (1965), a US Government work in the public
# domain: DLI's wording, tables and examples. Exercises are DLI's sentences
# and tables with the word in question left blank.
from kit import *

SRC = "From the DLI Grammar Reference Book"

SECTIONS = [

SEC("c4-one-two-three-four", "один, два, три, четыре: with nouns and in every case", sub="DLI Lessons 39 and 70 · the noun after 1–4 · declension · with adjectives · special meanings of один", blocks=[
  H("1–4 with a noun"),
  P("a) ОДИН, ОДНА, ОДНО. The numeral один has special forms for feminine and neuter nouns:"),
  EX(("один урок", ""), ("одна страница", ""), ("одно слово", "")),
  P("After all compound numbers ending with один the noun is in the nominative singular: *тридцать один урок; сорок одна страница; сто одно слово.*"),
  P("b) ДВА, ДВЕ. The numeral два has a special form for feminine nouns — две. The noun after два, две (also after 22, 32, 42, etc.) is in the genitive singular:"),
  EX(("два урока, тридцать два урока", ""), ("два слова, сорок два слова", ""), ("две страницы, сто две страницы", "")),
  P("Likewise: оба урока, оба слова, обе страницы."),
  P("c) ТРИ, ЧЕТЫРЕ. After три and четыре (also after: двадцать три, тридцать четыре, сорок три etc.) the noun is also in the genitive singular: *3 урока, 33 урока; 4 слова, 44 слова; 4 страницы, 104 страницы.*"),
  H("The same numerals in every case"),
  P("Numerals are declined in Russian. They have their own pattern of declension."),
  H("Declension of «один», «одна», «одно»"),
  P("The number «ОДИН» acts as an adjective. It agrees with the nouns to which it refers in gender, number and case. ОДИН (ОДНА, ОДНО) declines like этот (ЭТА, ЭТО)."),
  T(["", "Masculine", "Feminine"], [
    ["Nom.", "один самолёт", "одна рота"], ["Gen.", "одного самолёта", "одной роты"], ["Dat.", "одному самолёту", "одной роте"],
    ["Acc. (inanim.)", "один самолёт", "одну роту"], ["Acc. (animate)", "одного пилота", "одну медсестру"],
    ["Instr.", "одним самолётом", "одной ротой"], ["Prep.", "об одном самолёте", "об одной роте"],
  ]),
  P("Note that with masculine inanimate nouns the Accusative of «ОДИН» is the same as the Nominative. With animate nouns it is the same as the Genitive: *Я вижу один грузовик. Я вижу одного человека.* The feminine Accusative is always «ОДНУ»: *Я вижу одну книгу. Я вижу одну девушку.* The neuter form «ОДНО» is declined like «ОДИН»."),
  H("Declension of «два», «две», «три», «четыре»"),
  T(["", "два (masc., neut.)", "две (fem.)", "три", "четыре"], [
    ["Nom.", "два часа", "две минуты", "три урока", "четыре пары"], ["Gen.", "двух часов", "двух минут", "трёх уроков", "четырёх пар"],
    ["Dat.", "двум часам", "двум минутам", "трём урокам", "четырём парам"], ["Acc. inan. = N.", "два часа", "две минуты", "три урока", "четыре пары"],
    ["Acc. anim. = G.", "двух студентов", "двух девушек", "трёх студентов", "четырёх студенток"], ["Instr.", "двумя часами", "двумя минутами", "тремя уроками", "четырьмя парами"],
    ["Prep.", "о двух часах", "о двух минутах", "о трёх уроках", "о четырёх парах"],
  ]),
  P("Note that the rule: \"2, 3, 4 + Gen. sing.\" concerns the Nominative (or Accusative inanimate) construction only. In oblique cases the numbers always agree in case with the noun to which they refer (двум студентам; с тремя книгами; на четырёх грузовиках). Note also the «ь» and the stress in the Instrumental case of «ЧЕТЫРЕ» — «ЧЕТЫРЬМЯ»."),
  H("Два, три, четыре + adjective + noun"),
  T(["", "Example", "Adjective and noun"], [
    ["Nom.", "два новых самолёта · три больших комнаты · четыре русских студента", "adj. Gen. pl., noun Gen. sing."],
    ["Gen.", "двух новых самолётов · трёх больших комнат", "Gen. pl."], ["Dat.", "двум новым самолётам · трём большим комнатам", "Dat. pl."],
    ["Instr.", "двумя новыми самолётами · тремя большими комнатами", "Instr. pl."], ["Prep.", "о двух новых самолётах · о трёх больших комнатах", "Prep. pl."],
  ], row_heads=True),
  P("Note the complete agreement of numerals and adjectives with the nouns they modify in all cases except the Nominative. As we already know, the numerals «два», «три» and «четыре» in the Nominative case are followed by nouns in the Genitive singular, but the adjectives are in the Genitive plural."),
  H("Special meanings of the word «один»"),
  EX(("Один он знает это. (= Только он знает это.)", "Only he knows this."), ("Он летал один.", "He was flying alone."), ("Я с ним в одном классе.", "I'm in the same class with him."), ("Ни один человек не знает этого.", "No (not a single) man knows this."), ("Сколько книг вы прочитали? — Ни одной.", "How many books did you read? — None."), ("Я познакомился с одним студентом, который знает вас.", "I met a (certain) student who knows you.")),
  NOTE("DLI, Lessons 39 and 70."),
], exercises=[
  FILL("33 ___ (урок)", ["урока"], "After три and четыре (also after тридцать три…) the noun is in the genitive singular. " + SRC + ", Lesson 39."),
  FILL("___ страницы (both)", ["обе"], "Likewise: оба урока, оба слова, обе страницы. " + SRC + ", Lesson 39."),
  FILL("Я вижу ___ человека. (один — animate)", ["одного"], "With animate nouns it is the same as the Genitive. " + SRC + ", Lesson 70."),
  FILL("Я вижу ___ девушку. (одна)", ["одну"], "The feminine Accusative is always «ОДНУ». " + SRC + ", Lesson 70."),
  FILL("об ___ самолёте (один)", ["одном"], SRC + ", Lesson 70."),
  FILL("___ часов (два — Gen.)", ["двух"], SRC + ", Lesson 70."),
  FILL("___ урокам (три — Dat.)", ["трём", "трем"], SRC + ", Lesson 70."),
  FILL("___ парами (четыре — Instr.)", ["четырьмя"], "Note the «ь» and the stress — «ЧЕТЫРЬМЯ». " + SRC + ", Lesson 70."),
  MC("два ___ самолёта", ["новый", "новых", "новые"], 1, "The adjectives are in the Genitive plural. " + SRC + ", Lesson 70."),
  FILL("с тремя ___ (книги — Instr.)", ["книгами"], "In oblique cases the numbers always agree in case with the noun. " + SRC + ", Lesson 70."),
  MC("«He was flying alone.»", ["Он летал один.", "Один он летал."], 0, "In this meaning «один» never precedes the noun modified. " + SRC + ", Lesson 70."),
  FILL("Сколько книг вы прочитали? — Ни ___ .", ["одной"], SRC + ", Lesson 70."),
]),


SEC("c2-genitive-plural", "The genitive plural", sub="DLI Lessons 38–41 · the four basic types · deviations · человек, год", blocks=[
  H("Genitive plural of nouns (4 basic types)"),
  T(["", "I", "II", "III", "IV"], [
    ["Nom. sing.", "consonant: стол, нож", "-ь, sibilants: словарь, тетрадь", "-а, -о: газета, слово", "-(и)я, -(и)е: лекция, здание"],
    ["Gen. plur.", "-ов: столов", "-ей: словарей, тетрадей, ножей", "—: газет, слов", "-й: лекций, зданий"],
  ]),
  NOTE("DLI, Lesson 38."),
  H("Genitive plural — deviation from the regular chart"),
  P("Type I. a) After Ц the stressed ending is -ов, the unstressed is -ев: отцов, продавцов, but: американцев, немцев, месяцев. b) Masculine nouns in -й have -ев in the genitive plural: трамвай — трамваев."),
  P("Type II. a) The nouns мать and дочь keep -ер- throughout the plural: N. pl.: матери, дочери; G. pl.: матерей, дочерей. b) The noun соседи (which is soft in the plural), also the nouns люди, дети, and родители (used in plural only) belong to type II: G. pl.: соседей, людей, родителей, детей."),
  P("Type III. a) The genitive plural of feminine and neuter nouns of this type often has an inserted -е- or -о- between any two consonants at the end of the word. 1. They always take -е- between a sibilant and к: чашка — чашек; девочка — девочек. 2. They take -о- between any other consonant and к: ошибка — ошибок; машинка — машинок. 3. Memorize: число — чисел; окно — окон; письмо — писем; also: деньги — денег. Remember: сестра — сёстры — сестёр; but: место — мест; лампа — ламп; буква — букв; карта — карт. b) The genitive plural of неделя, деревня, туфля, as a soft variation of type III, is: недель, деревень, туфель."),
  P("Type IV. a) The neuter nouns поле and море have the following genitive plural endings: полей, морей. b) семья has the genitive plural семей."),
  NOTE("DLI, Lesson 39."),
  H("Irregular genitive plural"),
  P("a) англичанин — англичане — англичан; крестьянин — крестьяне — крестьян. b) имя — имена — имён; время — времена — времён. Some masculine and neuter nouns with the irregular nom. plural ending -ья have the following genitive plural: стулья — стульев; братья — братьев; перья — перьев; and друзья — друзей; сыновья — сыновей; мужья — мужей."),
  P("РАЗ, ЧЕЛОВЕК, СОЛДАТ. The genitive plural of раз, человек, солдат is the same as the nominative singular: один раз — пять раз; один человек — пять человек; один солдат — пять солдат."),
  H("ЧЕЛОВЕК — ЛЮДИ"),
  P("a) The word «люди» is used as nominative plural for «человек»: *Около дома стоял человек. — Около дома стояли люди.* b) The genitive plural of «человек» is used after numerals and the words «сколько» and «несколько»: *Сколько там человек? Там несколько человек. Там шесть человек.* c) In all other constructions the word «люди» is used: *Там мало людей. Там много людей. Там нет людей.*"),
  NOTE("DLI, Lessons 40 and 41."),
], exercises=[
  FILL("пять ___ (стол)", ["столов"], "Type I: -ов. " + SRC + ", Lesson 38."),
  FILL("пять ___ (словарь)", ["словарей"], "Type II: -ей. " + SRC + ", Lesson 38."),
  FILL("пять ___ (газета)", ["газет"], "Type III: no ending. " + SRC + ", Lesson 38."),
  FILL("пять ___ (лекция)", ["лекций"], "Type IV: -й. " + SRC + ", Lesson 38."),
  FILL("много ___ (месяц)", ["месяцев"], "After Ц the unstressed ending is -ев. " + SRC + ", Lesson 39."),
  FILL("много ___ (ошибка)", ["ошибок"], "-о- between any other consonant and к. " + SRC + ", Lesson 39."),
  FILL("много ___ (девочка)", ["девочек"], "-е- between a sibilant and к. " + SRC + ", Lesson 39."),
  FILL("много ___ (письмо)", ["писем"], "Memorize: письмо — писем. " + SRC + ", Lesson 39."),
  FILL("пять ___ (неделя)", ["недель"], SRC + ", Lesson 39."),
  FILL("много ___ (друзья)", ["друзей"], SRC + ", Lesson 40."),
  MC("пять ___ (солдат)", ["солдатов", "солдат", "солдата"], 1, "The genitive plural of раз, человек, солдат is the same as the nominative singular. " + SRC + ", Lesson 40."),
  MC("Там шесть ___ .", ["людей", "человек", "человеков"], 1, "The genitive plural of «человек» is used after numerals. " + SRC + ", Lesson 40."),
  MC("Там много ___ .", ["людей", "человек"], 0, "In all other constructions the word «люди» is used. " + SRC + ", Lesson 41."),
]),

SEC("c3-how-many", "Much, many, few, how many, several", sub="DLI Lesson 38 · много, мало, сколько, несколько · есть and нет", blocks=[
  H("МНОГО, МАЛО, СКОЛЬКО + genitive singular or plural"),
  T(["", "+ gen. sing.", "+ gen. plur."], [
    ["много", "много молока — much", "много стаканов — many"],
    ["мало", "мало молока — little", "мало стаканов — few"],
    ["сколько", "сколько молока — how much", "сколько стаканов — how many"],
  ]),
  P("Such phrases as above are used in the following \"NEUTER\" constructions:"),
  EX(("У меня мало времени.", ""), ("У меня было много уроков.", ""), ("Сколько у вас было учебников?", ""), ("Нам нужно будет много бумаги.", "")),
  H("НЕСКОЛЬКО + genitive plural"),
  EX(("Сколько учебников у вас было? — У нас было несколько учебников.", ""), ("Сколько механиков вам нужно будет? — Нам нужно будет несколько механиков.", "")),
  H("У меня есть, у меня нет"),
  T(["", "есть", "нет"], [
    ["Present", "У меня есть учебник. У меня есть учебники.", "У меня нет учебника. У меня нет учебников."],
    ["Past", "У меня был учебник. У меня были учебники.", "У меня не было учебника. У меня не было учебников."],
    ["Future", "У меня будет учебник. У меня будут учебники.", "У меня не будет учебника. У меня не будет учебников."],
  ]),
  EX(("Я был дома. — Меня не было дома.", ""), ("Я буду дома. — Меня не будет дома.", "")),
  P("Note — Pay special attention to the \"NEUTER\" construction «не было (не будет) + gen.»"),
  NOTE("DLI, Lesson 38."),
], exercises=[
  FILL("много ___ (молоко)", ["молока"], "+ g. sing. = much. " + SRC + ", Lesson 38."),
  FILL("мало ___ (стакан)", ["стаканов"], "+ g. plur. = few. " + SRC + ", Lesson 38."),
  FILL("сколько ___ ? (how many glasses)", ["стаканов"], SRC + ", Lesson 38."),
  FILL("У меня мало ___ . (время)", ["времени"], SRC + ", Lesson 38."),
  FILL("У нас было несколько ___ . (учебник)", ["учебников"], "НЕСКОЛЬКО + genitive plural. " + SRC + ", Lesson 38."),
  FILL("Нам нужно будет несколько ___ . (механик)", ["механиков"], SRC + ", Lesson 38."),
  FILL("У меня нет ___ . (учебник, sing.)", ["учебника"], SRC + ", Lesson 38."),
  MC("У меня ___ учебников.", ["не были", "не было", "не был"], 1, "The \"NEUTER\" construction «не было + gen.» " + SRC + ", Lesson 38."),
  MC("Я буду дома. — ___ не будет дома.", ["Я", "Меня", "Мне"], 1, SRC + ", Lesson 38."),
]),

]
