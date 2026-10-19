# Counting Things, part C (DLI Grammar Reference Book II, Lessons 98–99): collective numerals, полтора.
from kit import *

SRC = "From the DLI Grammar Reference Book"

SECTIONS = [

SEC("c8-collective-half", "двое, трое… and полтора", sub="DLI Lessons 98–99 · collective numerals · полтора, полторы, полутора · полтораста", blocks=[
  H("Collective numerals"),
  P("a) Cardinal numerals 2–7 have parallel forms, which are known under the name of collective numerals, which have exactly the same meaning: двое — 2, трое — 3, четверо — 4, пятеро — 5, шестеро — 6, семеро — 7. Collective numerals 8, 9, 10 are rarely used. The collective numerals may be used without nouns: *Трое вошли в комнату. Двое ушли домой.* If followed by a noun, the noun is in the genitive plural: *двое друзей (два друга), трое студентов (три студента).*"),
  P("b) The use of двое, трое, четверо is mandatory: 1. with nouns that have no singular: *двое суток, четверо детей,* but: *пятеро детей or пять детей.* 2. with masculine nouns ending in -а: *двое старшин, трое мужчин,* but: *пятеро or пять старшин.*"),
  P("Collective numerals are also used with personal pronouns: *Нас было пятеро в семье.* — There were five of us in the family. *Мы двое пошли вперёд, а они остались позади.*"),
  P("c) Collective numerals are preferable with masculine adjectival nouns: *двое рядовых, четверо служащих, трое рабочих.* With other masculine nouns denoting persons the use is optional: *двое товарищей, два товарища.* They are not used with feminine nouns, masculine inanimate nouns and nouns denoting animals: *две девочки, два учебника, два тигра.*"),
  P("d) Collective numerals are declined like adjectives in the plural, however in oblique cases they are usually replaced by the corresponding form of the cardinal numerals: *двое детей,* but: *Я не вижу двух её детей. Она дала яблоки двум детям. Мы приехали с двумя детьми.*"),
  H("полтора, полторы, полтораста"),
  P("a) \"One and a half\" is полтора when modifying a masculine or neuter noun and полторы for feminine nouns. Modified nouns are in the genitive singular: *полтора часа, полторы минуты.* These forms are used for nominative-accusative only. For all other cases the form «полутора» is used for all genders; the modified noun takes the form of the corresponding case in plural:"),
  T(["", "", ""], [["Nom.", "полтора часа", "полторы минуты"], ["Gen.", "полутора часов", "полутора минут"], ["Dat.", "полутора часам", "полутора минутам"], ["Acc.", "полтора часа", "полторы минуты"], ["Instr.", "полутора часами", "полутора минутами"], ["Prep.", "о полутора часах", "о полутора минутах"]]),
  P("Numerals like 1500 (человек) can be read either way: полторы тысячи человек, or тысяча пятьсот человек. b) The cardinal numeral полтораста means 150 (сто пятьдесят). The noun modified by it is in the genitive plural: *полтораста рублей.*"),
  NOTE("DLI, Lessons 98 and 99."),
], exercises=[
  FILL("___ вошли в комнату. (3)", ["Трое"], SRC + ", Lesson 98."),
  FILL("двое ___ (друг)", ["друзей"], "If followed by a noun, the noun is in the genitive plural. " + SRC + ", Lesson 98."),
  MC("___ суток", ["два", "двое"], 1, "Mandatory with nouns that have no singular. " + SRC + ", Lesson 98."),
  MC("___ мужчин", ["три", "трое"], 1, "Mandatory with masculine nouns ending in -а. " + SRC + ", Lesson 98."),
  MC("___ девочки", ["две", "двое"], 0, "Not used with feminine nouns. " + SRC + ", Lesson 98."),
  FILL("Нас было ___ в семье. (5)", ["пятеро"], SRC + ", Lesson 98."),
  FILL("Мы приехали с ___ детьми. (2)", ["двумя"], "In oblique cases the cardinal numeral is used. " + SRC + ", Lesson 98."),
  FILL("___ часа (1½)", ["полтора"], SRC + ", Lesson 99."),
  FILL("___ минуты (1½)", ["полторы"], SRC + ", Lesson 99."),
  FILL("о ___ часах (1½)", ["полутора"], SRC + ", Lesson 99."),
  FILL("полутора ___ (минута — Gen.)", ["минут"], "The noun takes the corresponding case in plural. " + SRC + ", Lesson 99."),
  FILL("___ рублей (150)", ["полтораста"], SRC + ", Lesson 99."),
]),

]
