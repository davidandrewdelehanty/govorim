# Counting Things. Transcribed from the DLI Russian Basic Course, Grammar
# Reference Book I (1970) and II (1965), a US Government work in the public
# domain: DLI's wording, tables and examples. Exercises are DLI's sentences
# and tables with the word in question left blank.
from kit import *

SRC = "From the DLI Grammar Reference Book"

SECTIONS = [

SEC("c1-numbers-nouns", "Numbers with nouns", sub="DLI Lesson 39 · один, два, три, четыре, пять + noun", blocks=[
  H("Cardinal numerals with nouns"),
  P("a) ОДИН, ОДНА, ОДНО. The numeral один has special forms for feminine and neuter nouns:"),
  EX(("один урок", ""), ("одна страница", ""), ("одно слово", "")),
  P("After all compound numbers ending with один the noun is in the nominative singular: *тридцать один урок; сорок одна страница; сто одно слово.*"),
  P("b) ДВА, ДВЕ. The numeral два has a special form for feminine nouns — две. The noun after два, две (also after 22, 32, 42, etc.) is in the genitive singular:"),
  EX(("два урока, тридцать два урока", ""), ("два слова, сорок два слова", ""), ("две страницы, сто две страницы", "")),
  P("Likewise: оба урока, оба слова, обе страницы."),
  P("c) ТРИ, ЧЕТЫРЕ. After три and четыре (also after: двадцать три, тридцать четыре, сорок три etc.) the noun is also in the genitive singular: *3 урока, 33 урока; 4 слова, 44 слова; 4 страницы, 104 страницы.*"),
  P("d) ПЯТЬ, ШЕСТЬ, СЕМЬ etc. After all other numerals (пять, шесть, семь, etc.) as well as after all compound numbers with 5, 6, 7, etc. as last word, the noun is in the genitive plural: *5 уроков, 35 уроков; 10 страниц, 40 страниц; 11 слов, 111 слов.*"),
  P("Note — 1) Russian compound numerals are never connected by и: hundred and five — сто пять."),
  NOTE("DLI, Lesson 39."),
], exercises=[
  MC("___ страница", ["один", "одна", "одно"], 1, "The numeral один has special forms for feminine and neuter nouns. " + SRC + ", Lesson 39."),
  MC("___ слово", ["один", "одна", "одно"], 2, SRC + ", Lesson 39."),
  MC("___ страницы (2)", ["два", "две"], 1, "The numeral два has a special form for feminine nouns — две. " + SRC + ", Lesson 39."),
  MC("тридцать один ___", ["урок", "урока", "уроков"], 0, "After all compound numbers ending with один the noun is in the nominative singular. " + SRC + ", Lesson 39."),
  MC("два ___", ["урок", "урока", "уроков"], 1, "The noun after два, две is in the genitive singular. " + SRC + ", Lesson 39."),
  MC("сорок два ___", ["слово", "слова", "слов"], 1, SRC + ", Lesson 39."),
  MC("пять ___", ["урок", "урока", "уроков"], 2, "After пять, шесть, семь, etc. the noun is in the genitive plural. " + SRC + ", Lesson 39."),
  MC("10 ___", ["страница", "страницы", "страниц"], 2, SRC + ", Lesson 39."),
  MC("111 ___", ["слово", "слова", "слов"], 2, SRC + ", Lesson 39."),
  FILL("33 ___ (урок)", ["урока"], "After три and четыре (also after тридцать три…) the noun is in the genitive singular. " + SRC + ", Lesson 39."),
  FILL("___ страницы (both)", ["обе"], "Likewise: оба урока, оба слова, обе страницы. " + SRC + ", Lesson 39."),
  MC("«a hundred and five»", ["сто и пять", "сто пять"], 1, "Russian compound numerals are never connected by и. " + SRC + ", Lesson 39."),
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
