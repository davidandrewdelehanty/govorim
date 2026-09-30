#!/usr/bin/env python3
"""Everything Викитека carries for one author, written out as an import list.

tools/add_wikisource.py takes a TSV and puts each row on the shelf. Filling
that TSV by hand means knowing every page title an author has there, which is
how a shelf ends up with the three famous works and none of the rest. This
asks Wikisource instead: it reads the author's page, keeps the links that are
that author's own texts, notices which of them are collections, and writes the
list in the shape the importer already reads.

    python3 tools/wikisource_author.py                       # Bulgakov
    python3 tools/wikisource_author.py --author "Автор:Иван Алексеевич Бунин" \
        --marker "(Бунин" --out tools/bunin.tsv

Then read the file. The page titles come from Wikisource and are right; the
category and the blurb are this script's guess and are meant to be edited.
Rows for works already on the shelf are written out commented with #have, so
nothing is imported twice by accident. When it looks right:

    python3 tools/add_wikisource.py --list tools/bulgakov.tsv

WHERE THIS RUNS: it needs ru.wikisource.org, so it runs on your machine —
same as add_wikisource.py, and for the same reason.
"""
import argparse
import json
import os
import re
import sys
import time
import urllib.parse
import urllib.request

API = "https://ru.wikisource.org/w/api.php"
UA = "govorim-app/1.0 (library import; contact via github)"
MANIFEST = "private/books/index.json"

# Reference works ABOUT the author sit on his page beside the works BY him.
DROP_PREFIX = ("ББСРП", "ЭСБЕ", "НЭС", "МЭСБЕ", "БСЭ", "РБС", "ЭЛ", "Викитека",
               "Литературная энциклопедия", "Большая советская")

TRANSLIT = {
    "а": "a", "б": "b", "в": "v", "г": "g", "д": "d", "е": "e", "ё": "yo",
    "ж": "zh", "з": "z", "и": "i", "й": "y", "к": "k", "л": "l", "м": "m",
    "н": "n", "о": "o", "п": "p", "р": "r", "с": "s", "т": "t", "у": "u",
    "ф": "f", "х": "kh", "ц": "ts", "ч": "ch", "ш": "sh", "щ": "shch",
    "ъ": "", "ы": "y", "ь": "", "э": "e", "ю": "yu", "я": "ya",
}

# What this script knows without being told. Everything else gets a guess and
# a blank blurb, which is the signal to go and write one.
KNOWN = {
    "Дьяволиада": ("dyavoliada", "Novellas",
        "A clerk at the Match Supply Depot is sacked over a misread signature, and chases the official who signed it through a Moscow that will not hold still."),
    "Роковые яйца": ("rokovye-yaytsa", "Novellas",
        "A zoologist finds a ray that makes living things grow at monstrous speed, and a state farm takes it away from him to save the country's chickens."),
    "Записки юного врача": ("zapiski-yunogo-vracha", "Short Stories",
        "A doctor of twenty-three, a month out of university, is sent alone to a country hospital forty versts from the railway and learns his trade on whoever is carried through the door."),
    "Морфий": ("morfiy", "Novellas",
        "The notebooks of a young country doctor who began with a quarter-syringe against a pain in the stomach, left to the colleague who reads them after his death."),
    "Записки на манжетах": ("zapiski-na-manzhetakh", "Novellas",
        "Cuffs written on in the Caucasus and in Moscow: a writer with typhus, no money and no papers, talking his way from one office to the next."),
    "Ханский огонь": ("khanskiy-ogon", "Short Stories",
        "A count's house, now a museum, is shown to day trippers by the old servant who stayed with it, and one visitor in dark glasses knows the rooms too well."),
    "Похождения Чичикова": ("pokhozhdeniya-chichikova", "Short Stories",
        "Gogol's Chichikov wakes up in Soviet Moscow, registers himself as a citizen, and finds the new institutions even easier to rob than the old."),
    "Красная корона": ("krasnaya-korona", "Short Stories",
        "From a room he is not allowed to leave, a man writes to his mother about the brother he watched ride away and did not call back."),
    "№ 13. — Дом Эльпит-Рабкоммуна": ("dom-elpit", "Short Stories",
        "A grand Moscow apartment house, requisitioned and packed to the attics, burns down because no one is permitted to light a stove."),
    "Китайская история": ("kitayskaya-istoriya", "Short Stories",
        "A Chinese man alone in Moscow with no language, no papers and no bread is taken in by a machine-gun detachment."),
    "Налёт": ("nalyot", "Short Stories",
        "Two sentries on a railway line in the freezing dark, and the raid that comes for them."),
    "Я убил": ("ya-ubil", "Short Stories",
        "At the end of an evening among doctors, one of them answers the question of whether he has ever killed a man."),
    "Псалом": ("psalom", "Short Stories",
        "A man in a Moscow room, the small boy from along the corridor who visits him, and the boy's mother."),
    "Самогонное озеро": ("samogonnoe-ozero", "Short Stories",
        "A writer trying to work in a communal flat, and the neighbours' still."),
    "Чаша жизни": ("chasha-zhizni", "Short Stories",
        "Three men set out for one more drink, and the evening goes where such evenings go."),
    "Богема": ("bogema", "Short Stories",
        "How the author survived the winter of 1920 in Vladikavkaz by writing a revolutionary play in three days."),
    "Театральный роман": ("teatralnyy-roman", "Novels",
        "A clerk's novel is made into a play, and he is drawn into the theatre staging it, where nothing is decided and everything is personal."),
    "Жизнь господина де Мольера": ("zhizn-molera", "Novels",
        "The life of Molière, told by a narrator who keeps interrupting himself to argue with the seventeenth century."),
    "Дни Турбиных": ("dni-turbinykh", "Plays"),
    "Зойкина квартира": ("zoykina-kvartira", "Plays"),
    "Бег": ("beg", "Plays"),
    "Багровый остров": ("bagrovyy-ostrov", "Plays"),
    "Кабала святош": ("kabala-svyatosh", "Plays"),
    "Иван Васильевич": ("ivan-vasilevich", "Plays"),
    "Блаженство": ("blazhenstvo", "Plays"),
    "Адам и Ева": ("adam-i-eva", "Plays"),
    "Александр Пушкин": ("aleksandr-pushkin", "Plays"),
    "Собачье сердце": ("sobache-serdtse", "Novellas"),
    "Белая гвардия": ("belaya-gvardiya", "Novels"),
    "Мастер и Маргарита": ("master-i-margarita", "Novels"),
}


def api(params):
    params = dict(params, format="json", formatversion="2")
    req = urllib.request.Request(API + "?" + urllib.parse.urlencode(params),
                                 headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.load(r)


def slugify(title):
    t = title.lower()
    out = []
    for ch in t:
        if ch in TRANSLIT:
            out.append(TRANSLIT[ch])
        elif ch.isalnum():
            out.append(ch)
        else:
            out.append("-")
    s = re.sub(r"-{2,}", "-", "".join(out)).strip("-")
    return s[:60]


def bare_title(page):
    """«Роковые яйца (Булгаков)» → «Роковые яйца». Editions keep their suffix
    off the title but not off the page: «Левша (Лесков)/Издание 1902» is still
    Левша."""
    t = page.split("/")[0]
    t = re.sub(r"\s*\([^()]*\)\s*$", "", t).strip()
    return t


def has_subpages(page):
    """A collection is a page with children: Записки юного врача is an index
    and the seven stories are separate pages under it. The importer wants
    those marked with a leading @."""
    d = api({"action": "query", "list": "allpages", "apnamespace": 0,
             "apprefix": page + "/", "aplimit": 5})
    return bool(d.get("query", {}).get("allpages"))


def catalogue_titles(manifest):
    try:
        with open(manifest, encoding="utf-8") as f:
            data = json.load(f)
    except Exception:
        return set()
    books = data.get("books", data) if isinstance(data, dict) else data
    return set(str(b.get("title", "")).strip() for b in books if isinstance(b, dict))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--author", default="Автор:Михаил Афанасьевич Булгаков")
    ap.add_argument("--marker", default="(Булгаков",
                    help="keep only pages whose title carries this, the author's disambiguator")
    ap.add_argument("--name", default="Булгаков М.А.", help="author, as the catalogue writes it")
    ap.add_argument("--out", default="tools/bulgakov.tsv")
    ap.add_argument("--manifest", default=MANIFEST)
    ap.add_argument("--all", action="store_true",
                    help="keep every page linked from the author page, marker or not")
    a = ap.parse_args()

    d = api({"action": "parse", "page": a.author, "prop": "links"})
    links = d.get("parse", {}).get("links", [])
    pages = [l["title"] for l in links
             if l.get("ns") == 0 and l.get("exists") and
             not l["title"].startswith(DROP_PREFIX)]
    kept = [p for p in pages if a.all or a.marker in p]
    skipped = [p for p in pages if p not in kept]

    have = catalogue_titles(a.manifest)
    rows, seen = [], set()
    for p in sorted(kept):
        title = bare_title(p)
        if title in seen:
            continue           # a second edition of something already listed
        seen.add(title)
        known = KNOWN.get(title, ())
        slug = known[0] if known else slugify(title)
        cat = known[1] if len(known) > 1 else "Short Stories"
        blurb = known[2] if len(known) > 2 else ""
        page = ("@" + p) if has_subpages(p) else p
        time.sleep(0.2)
        rows.append(("#have\t" if title in have else "") +
                    "\t".join([slug, page, a.name, title, cat, blurb]))
        print(("have  " if title in have else "new   ") + p)

    os.makedirs(os.path.dirname(a.out) or ".", exist_ok=True)
    with open(a.out, "w", encoding="utf-8", newline="\n") as f:
        f.write("# Written by tools/wikisource_author.py from %s\n" % a.author)
        f.write("# Columns: slug, Wikisource page, author, title, category, blurb.\n")
        f.write("# A page beginning @ is a collection index — the importer reads its links.\n")
        f.write("# Rows marked #have are already on the shelf and are skipped.\n")
        f.write("# Check the category and write the blurbs, then:\n")
        f.write("#   python3 tools/add_wikisource.py --list %s\n#\n" % a.out)
        f.write("\n".join(rows) + "\n")
        if skipped:
            f.write("#\n# Linked from the author page but not kept (no %s in the title):\n" % a.marker)
            for p in sorted(skipped):
                f.write("#   %s\n" % p)

    print("\n%d rows → %s   (%d already on the shelf, %d set aside)"
          % (len(rows), a.out, sum(1 for r in rows if r.startswith("#have")), len(skipped)))


if __name__ == "__main__":
    main()
