#!/usr/bin/env python3
"""A batch of new books from Russian Wikisource, none of them with English:

  Древняя Русь   «Слово о полку Игореве» in Жуковский's translation,
                 «Житие протопопа Аввакума», «Повесть временных лет»
                 (the Old Russian text — left in its own orthography)
  Scripture      «Откровенные рассказы странника», «Лествица»
  Poetry         Мандельштам «Камень» (1916); Гумилёв — «Путь
                 конквистадоров», «Жемчуга», «Чужое небо», «Колчан», «Костёр»,
                 «Огненный столп»

The poetry collections are index pages linking to each poem as a page of its
own, so their member lists (read from the index pages, in order, with the
neighbouring collections and categories taken out) are in
tools/new_books_members.json, and the poems are fetched one by one.

    cd /mnt/c/Users/david/projects/govorim-app
    python3 tools/new_books.py
    python3 tools/gen_stress_maps.py
    python3 tools/make_case_drills.py --book avvakum-zhitie.fb2
    python3 tools/make_case_drills.py --book otkrovennye-rasskazy-strannika.fb2
    python3 tools/make_case_drills.py --book lestvitsa.fb2
"""
import io, json, os, re, subprocess, sys, time, urllib.parse

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.chdir(ROOT)
sys.path.insert(0, os.path.join(ROOT, "tools"))
from add_wikisource import api_html
from translations_build import modernise_fb2

MANIFEST = "private/books/index.json"
CACHE = ".ws-cache/new_books"
C = lambda f: "https://commons.wikimedia.org/wiki/Special:FilePath/" + urllib.parse.quote(f.replace(" ", "_")) + "?width=500"
WP = lambda t: "https://ru.wikipedia.org/wiki/" + t.replace(" ", "_")

WORKS = [
    dict(slug="slovo-o-polku-igoreve", page="Слово о полку Игореве (Жуковский)", title="Слово о полку Игореве",
         author="Жуковский В.А.", category="Poetry", alsoIn=["History"], year=1819, modern=True,
         translator="В. А. Жуковский", cover="Igorsvyat.jpg",
         blurb="«Слово о полку Игореве» — памятник литературы Древней Руси, рассказывающий о неудачном походе "
               "русских князей во главе с Игорем Святославичем Новгород-Северским на половцев в 1185 году. "
               "Здесь — в переводе В. А. Жуковского.",
         blurbSrc=WP("Слово о полку Игореве")),
    dict(slug="avvakum-zhitie", page="Житие протопопа Аввакума, им самим написанное (Аввакум)",
         title="Житие протопопа Аввакума, им самим написанное", author="Аввакум Петров", category="History",
         alsoIn=["Religious Texts"], year=1672, modern=True, cover="Avvakum by Pyotr Yevgenyevich Myasoyedov.jpg",
         blurb="«Житие протопопа Аввакума, им самим написанное» — уникальный памятник русской литературы XVII века. "
               "У «жития» есть главное отличие от других произведений того времени — грубый язык, нарочитая простота.",
         blurbSrc=WP("Житие протопопа Аввакума")),
    dict(slug="povest-vremennykh-let", page="Повесть временных лет (Нестор)/1997 (ДО)", title="Повесть временных лет",
         author="Нестор Летописец", category="History", year=1113, modern=False,
         cover="Radziwiłł Chronicle 005 (miniature of Saint Andrew prophesying Kyiv).jpg",
         blurb="«Повесть временных лет» — наиболее ранняя из сохранившихся в полном объёме русских летописей. "
               "Считается, что была создана в Киеве в 1110-х годах. Здесь — древнерусский текст по Ипатьевскому списку.",
         blurbSrc=WP("Повесть временных лет")),
    dict(slug="otkrovennye-rasskazy-strannika", page="Откровенные рассказы странника духовному своему отцу",
         title="Откровенные рассказы странника духовному своему отцу", author="Странник", category="Religious Texts",
         year=1881, modern=True, cover="Перов Странник(ГТГ).jpg",
         blurb="«Откровенные рассказы странника духовному своему отцу» — произведение XIX века некоего странника, "
               "путешествующего по России с Иисусовой молитвой.",
         blurbSrc=WP("Откровенные рассказы странника духовному своему отцу")),
    dict(slug="lestvitsa", page="Лествица", title="Лествица", author="Иоанн Лествичник", category="Religious Texts",
         year=600, modern=True, cover="The Ladder of Divine Ascent Monastery of St Catherine Sinai 12th century.jpg",
         blurb="«Лествица» (Лествица райская, Скрижали духовные) — основное сочинение Иоанна Лествичника.",
         blurbSrc=WP("Лествица")),
    dict(slug="mandelshtam-kamen", page="Камень (Мандельштам, 1916)", title="Камень", author="Мандельштам О.Э.",
         category="Poetry", year=1916, modern=True, members=True),
    dict(slug="gumilev-put-konkvistadorov", page="Путь конквистадоров (Гумилёв)", title="Путь конквистадоров",
         author="Гумилёв Н.С.", category="Poetry", year=1905, modern=True, members=True,
         cover="The Way of Conquistadors by Gumilev - Front Cover.jpg",
         blurb="«Путь конквистадоров» — первый поэтический сборник Николая Степановича Гумилёва, выпущенный в конце "
               "1905 года на средства родителей.", blurbSrc=WP("Путь конквистадоров")),
    dict(slug="gumilev-zhemchuga", page="Жемчуга (Гумилёв, 1910)", title="Жемчуга", author="Гумилёв Н.С.",
         category="Poetry", year=1910, modern=True, members=True),
    dict(slug="gumilev-chuzhoe-nebo", page="Чужое небо (Гумилёв)", title="Чужое небо", author="Гумилёв Н.С.",
         category="Poetry", year=1912, modern=True, members=True,
         blurb="«Чужое небо» — четвертый сборник стихов Николая Гумилёва, выпущенный в 1912 году в Петербурге "
               "журналом «Аполлон».", blurbSrc=WP("Чужое небо")),
    dict(slug="gumilev-kolchan", page="Колчан (Гумилёв)", title="Колчан", author="Гумилёв Н.С.", category="Poetry",
         year=1916, modern=True, members=True, cover="Quiver by Gumilev - Front Cover.jpg"),
    dict(slug="gumilev-koster", page="Костёр (Гумилёв)", title="Костёр", author="Гумилёв Н.С.", category="Poetry",
         year=1918, modern=True, members=True, cover="Bonfire by Gumilev - Front Cover.jpg"),
    dict(slug="gumilev-ognennyy-stolp", page="Огненный столп (Гумилёв)", title="Огненный столп",
         author="Гумилёв Н.С.", category="Poetry", year=1921, modern=True, members=True),
]


def fetch(title):
    os.makedirs(CACHE, exist_ok=True)
    fp = os.path.join(CACHE, re.sub(r'[\\/:*?"<>| ]', "_", title) + ".html")
    if os.path.exists(fp) and os.path.getsize(fp) > 200:
        return io.open(fp, encoding="utf-8").read()
    h = api_html(title)
    io.open(fp, "w", encoding="utf-8").write(h)
    time.sleep(1.0)
    return h


def main():
    a = sys.argv[1:]
    only = a[a.index("--only") + 1:] if "--only" in a else None
    works = [w for w in WORKS if not only or w["slug"] in only]
    members = json.load(io.open("tools/new_books_members.json", encoding="utf-8"))
    pages = {}
    for w in works:
        if not w.get("members"):
            continue
        got = []
        lst = members[w["page"]]
        for i, t in enumerate(lst, 1):
            h = fetch(t)
            if h:
                got.append({"page": t, "html": h})
            print("\r  %s: %d/%d poems" % (w["slug"], i, len(lst)), end="", flush=True)
        print()
        pages[w["slug"]] = got
    pj = os.path.join(CACHE, "pages.json")
    os.makedirs(CACHE, exist_ok=True)
    io.open(pj, "w", encoding="utf-8").write(json.dumps(pages, ensure_ascii=False))
    lst = os.path.join(CACHE, "ws.tsv")
    with io.open(lst, "w", encoding="utf-8") as f:
        for w in works:
            f.write("\t".join([w["slug"], w["page"], w["author"], w["title"], w["category"], ""]) + "\n")
    subprocess.call([sys.executable, "tools/add_wikisource.py", "--list", lst, "--allow-duplicate", "--html-json", pj])

    idx = json.load(io.open(MANIFEST, encoding="utf-8"))
    by = {b.get("slug"): b for b in idx}
    for w in works:
        fb2 = "public/books/novel/%s.fb2" % w["slug"]
        if not os.path.exists(fb2) or w["slug"] not in by:
            print("!! %-32s not imported" % w["slug"]); continue
        mod = modernise_fb2(w["slug"]) if w.get("modern") else False
        b = by[w["slug"]]
        b.update({"category": w["category"], "author": w["author"], "title": w["title"], "public": True})
        for k in ("year", "translator"):
            if w.get(k):
                b[k] = w[k]
        if w.get("alsoIn"):
            b["alsoIn"] = w["alsoIn"]
        if w.get("cover"):
            b["cover"] = C(w["cover"])
        if w.get("blurb"):
            b.update({"blurb": w["blurb"], "blurbSrc": w["blurbSrc"], "blurbLang": "ru"})
        print("ok %-32s %7s words%s" % (w["slug"], format(b.get("words", 0), ","), "  (spelling modernised)" if mod else ""))
    io.open(MANIFEST, "w", encoding="utf-8").write(json.dumps(idx, ensure_ascii=False, indent=2) + "\n")
    print("\nDone. Next: python3 tools/gen_stress_maps.py, then the case drills (see the top of this file).")


if __name__ == "__main__":
    main()
