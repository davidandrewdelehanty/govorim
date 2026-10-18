#!/usr/bin/env python3
"""Philosophy, French, German and American books in Russian translation,
with the English beside them where Gutenberg has it:

  Платон     «Государство» (В. Н. Карпов, 1863), ten books; English: Jowett (pg1497)
  Аристотель «Политика» (С. А. Жебелёв, 1911) — Wikisource has books I–IV;
             English: Jowett (pg6762), cut where Book V begins
  Бальзак    «Евгения Гранде» — Ф. М. Достоевский's translation (1844); English: Wormeley (pg1715)
  Стендаль   «Красное и чёрное» (А. Н. Чеботаревская, 1915); English: Horace B. Samuel (pg44747)
  Гёте       «Страдания юного Вертера» (А. Н. Струговщиков); English: Boylan (pg2527)
  Гёте       «Фауст», часть первая (Н. А. Холодковский), scene by scene; English: Bayard Taylor (pg14591)
  Шиллер     «Разбойники» (М. М. Достоевский, 1901 ed.); English: pg6782
  Гофман     «Крошка Цахес, по прозванью Циннобер» (Н. Х. Кетчер) — Russian only;
             Gutenberg has no English translation
  Уитмен     «Стихотворения» — К. Д. Бальмонт's selection (Poetry, also on Translations)

    cd /mnt/c/Users/david/projects/govorim-app
    python3 tools/world_lit.py
    python3 tools/gen_stress_maps.py
    for b in plato-gosudarstvo aristotle-politika balzac-evgeniya-grande stendhal-krasnoe-i-chernoe \\
             goethe-verter goethe-faust-1 schiller-razboyniki hoffmann-tsakhes; do
      python3 tools/make_case_drills.py --book $b.fb2; done
"""
import csv, io, json, os, re, subprocess, sys, urllib.parse

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.chdir(ROOT)
DIR = "tools/translations"
LIST = os.path.join(DIR, "list.tsv")
CHAP = os.path.join(DIR, "chapters.json")
EN = os.path.join(DIR, "en")
MANIFEST = "private/books/index.json"
C = lambda f: "https://commons.wikimedia.org/wiki/Special:FilePath/" + urllib.parse.quote(f.replace(" ", "_")) + "?width=500"
WP = lambda t: "https://ru.wikipedia.org/wiki/" + urllib.parse.quote(t.replace(" ", "_"))

FS = "Фауст (Гёте; Холодковский)/Часть первая/"
FAUST_SCENES = ["Ночь", "У городских ворот", "Кабинет Фауста", "Кабинет Фауста", "Погреб Ауэрбаха в Лейпциге",
                "Кухня ведьмы", "Улица", "Вечер", "Гулянье", "Дом соседки", "Улица", "Сад", "Беседка",
                "Лес и пещера", "Комната Гретхен", "Сад Марты", "У колодца", "У городской стены",
                "Ночь. Улица перед домом Гретхен", "Собор", "Вальпургиева ночь", None,
                "Пасмурный день. Поле", "Ночь. Открытое поле", "Тюрьма"]
ORD = ["первая", "вторая", "третья", "четвертая", "пятая", "шестая", "седьмая", "восьмая", "девятая", "десятая"]
AR = "Политика (Аристотель)/"

CHAPTERS = {
    "plato-gosudarstvo": ["Политика или государство. Книга %s (Платон; Карпов)" % w for w in ORD],
    "aristotle-politika": [AR + p for p in ("О том, что такое государство", "О домохозяйстве и рабстве",
                                            "Об искусстве наживать состояние", "Разбор политических проектов Платона",
                                            "Разбор проектов Фалея и Гипподама",
                                            "Разбор государственного устройства лакедемонян",
                                            "Разбор государственного устройства критян и карфагенян", "Г", "Δ")],
    "goethe-faust-1": [FS + "Посвящение", FS + "Пролог в театре", FS + "Пролог на небесах"] +
                      [FS + "Сцена %d. %s" % (i, t) for i, t in enumerate(FAUST_SCENES, 1) if t],
}

ROWS = [
    ["plato-gosudarstvo", "Политика или государство (Платон; Карпов)", "Платон", "Государство", "The Republic",
     "Plato", "1497", "В. Н. Карпов", "1863", ""],
    ["aristotle-politika", "Политика (Аристотель)", "Аристотель", "Политика. Книги I–IV", "Politics",
     "Aristotle", "6762", "С. А. Жебелёв", "1911", ""],
    ["balzac-evgeniya-grande", "Евгения Гранде (Бальзак; Достоевский)", "Бальзак О.", "Евгения Гранде",
     "Eugénie Grandet", "Balzac", "1715", "Ф. М. Достоевский", "1844", ""],
    ["stendhal-krasnoe-i-chernoe", "Красное и черное (Стендаль)", "Стендаль", "Красное и чёрное",
     "The Red and the Black", "Stendhal", "44747", "А. Н. Чеботаревская", "1915", ""],
    ["goethe-verter", "Страдания юного Вертера (Гёте; Струговщиков)/ДО", "Гёте И.В.", "Страдания юного Вертера",
     "The Sorrows of Young Werther", "Goethe", "2527", "А. Н. Струговщиков", "1865", ""],
    ["goethe-faust-1", "Фауст (Гёте; Холодковский)", "Гёте И.В.", "Фауст. Часть первая", "Faust, Part I",
     "Goethe/Taylor", "14591", "Н. А. Холодковский", "1878", ""],
    ["schiller-razboyniki", "Разбойники (Шиллер)/Версия 4/ДО", "Шиллер Ф.", "Разбойники", "The Robbers",
     "Schiller", "6782", "М. М. Достоевский", "1901", ""],
    # gid 0: there is no English on Gutenberg; the Russian alone goes on the shelf
    ["hoffmann-tsakhes", "Крошка Цахес, по прозванью Циннобер (Гофман; Кетчер)/1884 (ВТ)", "Гофман Э.Т.А.",
     "Крошка Цахес, по прозванью Циннобер", "Little Zaches, Great Zinnober", "Hoffmann", "0", "Н. Х. Кетчер",
     "1844", ""],
]
SLUGS = [r[0] for r in ROWS]

META = {
    "plato-gosudarstvo": ("Platon Cave Sanraedam 1604.jpg",
        "«Государство» — диалог Платона, посвящённый проблеме идеального государства. Написан около 360 г. до н. э. "
        "С точки зрения Платона, государство является выражением идеи справедливости.",
        WP("Государство (Платон)"), "Philosophy", ["Translations"]),
    "aristotle-politika": ("Aristotle Altemps Inv8575.jpg",
        "«Политика» — трактат Аристотеля о государстве, содержащий начала социальной и политической философии.",
        WP("Политика (Аристотель)"), "Philosophy", ["Translations"]),
    "balzac-evgeniya-grande": ("BalzacEugenieGrandet01.jpg",
        "«Евгения Гранде» — роман Оноре де Бальзака из цикла «Сцены провинциальной жизни». Журнальная публикация "
        "состоялась в 1833—1834 годах; первый русский перевод выполнил молодой Ф. М. Достоевский.",
        WP("Евгения Гранде"), "Translations", None),
    "stendhal-krasnoe-i-chernoe": ("StendhalRedandBlack03.jpg",
        "«Красное и чёрное» — роман французского писателя Стендаля, опубликованный в 1830 году. Действие происходит "
        "в 1820-е годы во Франции.", WP("Красное и чёрное"), "Translations", None),
    "goethe-verter": ("Werther ziet vanuit de deuropening hoe Lotte brood snijdt voor de kinderen, RP-P-OB-56.513.jpg",
        "«Страдания юного Вертера» — сентиментальный роман в письмах Иоганна Вольфганга Гёте 1774 года.",
        WP("Страдания юного Вертера"), "Translations", None),
    "goethe-faust-1": ("Eugène Delacroix - Illustrations for Faust- Méphistophélés in the air - 1933.145.2 - Cleveland Museum of Art.jpg",
        "«Фауст» — философская поэма для чтения, которая считается главным трудом Иоганна Вольфганга фон Гёте. "
        "Первая часть была закончена в 1806 году.", WP("Фауст (трагедия)"), "Translations", ["Plays"]),
    "schiller-razboyniki": ("Schiller Die Räuber 1781.jpg",
        "«Разбойники» — первая опубликованная драма Фридриха Шиллера, написанная в 1781 году и впервые поставленная "
        "в Мангейме 13 января 1782 года.", WP("Разбойники"), "Translations", ["Plays"]),
    "hoffmann-tsakhes": ("Klein Zaches Theodor Hosemann 1.jpg",
        "«Крошка Цахес, по прозванию Циннобер» — сказочная повесть-гротеск немецкого романтика Э. Т. А. Гофмана.",
        WP("Крошка Цахес, по прозванию Циннобер"), "Translations", ["Fairytales"]),
}

WHITMAN = ["whitman-balmont", "Стихотворения (Уитмен)", "Уитмен У.", "Стихотворения (перевод К. Бальмонта)",
           "Poetry", "«Листья травы» — поэтический сборник американского поэта Уолта Уитмена (1819—1892). "
           "Здесь — стихотворения из него в переводе К. Д. Бальмонта."]


def cut_before(slug, start_re):
    p = os.path.join(EN, slug + ".txt")
    mark = os.path.join(EN, slug + ".cut")
    if not os.path.exists(p) or os.path.exists(mark):
        return "already cut" if os.path.exists(mark) else "no English"
    t = io.open(p, encoding="utf-8-sig", errors="replace").read().replace("\r\n", "\n")
    ms = list(re.finditer(start_re, t, flags=re.M))
    if not ms:
        return "!! no split point found — English left whole"
    io.open(p, "w", encoding="utf-8").write(t[:ms[0].start()])
    io.open(mark, "w").write(start_re)
    return "cut at %d of %d characters" % (ms[0].start(), len(t))


def main():
    have = {r[0] for r in csv.reader(io.open(LIST, encoding="utf-8"), delimiter="\t") if r}
    with io.open(LIST, "a", encoding="utf-8") as f:
        for r in ROWS:
            if r[0] not in have:
                f.write("\t".join(r) + "\n")
    chap = json.load(io.open(CHAP, encoding="utf-8"))
    chap.update(CHAPTERS)
    io.open(CHAP, "w", encoding="utf-8").write(json.dumps(chap, ensure_ascii=False, indent=1))

    subprocess.call([sys.executable, "tools/translations.py", "--only"] + SLUGS)
    print("  aristotle-politika: " + cut_before("aristotle-politika", r"^\s*BOOK V\s*$"))
    subprocess.call([sys.executable, "tools/translations_build.py", "--only"] + SLUGS)

    # Whitman: verse, no line-by-line English
    if not os.path.exists("public/books/novel/%s.fb2" % WHITMAN[0]):
        wl = os.path.join(DIR, "whitman.tsv")
        io.open(wl, "w", encoding="utf-8").write("\t".join(WHITMAN) + "\n")
        subprocess.call([sys.executable, "tools/add_wikisource.py", "--list", wl, "--allow-duplicate"])

    idx = json.load(io.open(MANIFEST, encoding="utf-8"))
    by = {b.get("slug"): b for b in idx}
    for s, (f, bl, src, cat, also) in META.items():
        b = by.get(s)
        if not b:
            print("!! %-28s not in the catalogue" % s); continue
        b.update({"cover": C(f), "blurb": bl, "blurbSrc": src, "blurbLang": "ru", "category": cat, "public": True})
        if also:
            b["alsoIn"] = also
        if s == "hoffmann-tsakhes":
            b["translator"] = "Н. Х. Кетчер"
        print("ok %-28s %8s words  English: %s" % (s, format(b.get("words", 0), ","), "yes" if b.get("parallelEn") else "no"))
    w = by.get(WHITMAN[0])
    if w:
        w.update({"cover": C("Whitman 1855 Samuel Hollyer engraved portrait frontispiece to first ed Leaves.jpg"),
                  "blurb": WHITMAN[5], "blurbSrc": WP("Листья травы"), "blurbLang": "ru", "category": "Poetry",
                  "alsoIn": ["Translations"], "translator": "К. Д. Бальмонт", "enTitle": "Leaves of Grass",
                  "enAuthor": "Walt Whitman", "public": True})
        print("ok %-28s %8s words" % (WHITMAN[0], format(w.get("words", 0), ",")))
    else:
        print("!! whitman-balmont not in the catalogue")
    io.open(MANIFEST, "w", encoding="utf-8").write(json.dumps(idx, ensure_ascii=False, indent=2) + "\n")
    print("\nDone. Next: python3 tools/gen_stress_maps.py, then the case drills (see the top of this file).")


if __name__ == "__main__":
    main()
