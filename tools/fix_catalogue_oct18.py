#!/usr/bin/env python3
"""Put back what two scripts running at once took out of the catalogue.

tales.py and world_lit.py (and en_videos.py) each read private/books/index.json,
worked, and wrote their copy back — so whichever wrote last undid the other's
changes. This restores them; it needs no network and is safe to run twice.

  * grimm-skazki's entry (its FB2 and English were built; the entry was lost)
  * covers and descriptions for the Mandelstam and Gumilyov collections

    cd /mnt/c/Users/david/projects/govorim-app
    python3 tools/fix_catalogue_oct18.py
"""
import io, json, os, sys, urllib.parse
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.chdir(ROOT)
sys.path.insert(0, "tools")
import tales
from reader_chapters import reader_chapters

P = "private/books/index.json"
C = lambda f: "https://commons.wikimedia.org/wiki/Special:FilePath/" + urllib.parse.quote(f.replace(" ", "_")) + "?width=500"
WM = "https://ru.wikipedia.org/wiki/Мандельштам,_Осип_Эмильевич"
WG = "https://ru.wikipedia.org/wiki/Гумилёв,_Николай_Степанович"
POETRY = {
    "mandelshtam-kamen": ("Stone (1916) by Mandelstam - Front Cover.jpg", "«Камень» — первая книга стихов Осипа Мандельштама (1913; второе, расширенное издание — 1916). Здесь — по изданию 1916 года.", WM),
    "gumilev-zhemchuga": ("Pearls by Gumilev - Front Cover.jpg", "«Жемчуга» — третья книга стихов Николая Гумилёва, вышедшая в 1910 году.", WG),
    "gumilev-chuzhoe-nebo": (None, "«Чужое небо» — сборник стихов Николая Гумилёва, вышедший в 1912 году.", WG),
    "gumilev-kolchan": (None, "«Колчан» — сборник стихов Николая Гумилёва, вышедший в 1916 году.", WG),
    "gumilev-koster": (None, "«Костёр» — сборник стихов Николая Гумилёва, вышедший в 1918 году.", WG),
    "gumilev-ognennyy-stolp": ("Гумилёв Н.С. Огненный столп. (1921). — Обложка.jpg", "«Огненный столп» (1921) — последний прижизненный сборник стихов Николая Гумилёва.", WG),
}

idx = json.load(io.open(P, encoding="utf-8"))
by = {b.get("slug"): b for b in idx}
if "grimm-skazki" not in by:
    m = tales.BOOKS_META["grimm-skazki"]
    chs, _ = reader_chapters("public/books/novel/grimm-skazki.fb2")
    first = json.load(io.open("tools/tales_config.json", encoding="utf-8"))["grimm"][0][0]
    e = {"filename": "novel/grimm-skazki.fb2", "title": m["title"], "author": m["author"], "category": "Fairytales",
         "slug": "grimm-skazki", "public": True, "words": sum(len(" ".join(c["paras"]).split()) for c in chs),
         "_note": "Text from Russian Wikisource: https://ru.wikisource.org/wiki/" + urllib.parse.quote(first.replace(" ", "_")),
         "alsoIn": ["Translations"], "translator": m["translator"], "year": m["year"], "parallelEn": "grimm-skazki-en",
         "enTitle": m["enTitle"], "enAuthor": m["enAuthor"], "translationNote": m["note"], "cover": C(m["cover"]),
         "blurb": m["blurb"], "blurbSrc": m["blurbSrc"], "blurbLang": "ru"}
    at = next((k for k, b in enumerate(idx) if b.get("slug") == "andersen-skazki"), len(idx) - 1)
    idx.insert(at + 1, e)
    print("restored grimm-skazki (%d tales, %s words)" % (len(chs), format(e["words"], ",")))
else:
    print("grimm-skazki already in the catalogue")
for s, (cov, bl, src) in POETRY.items():
    b = by.get(s)
    if not b:
        print("!! %s not in the catalogue" % s); continue
    if cov and not b.get("cover"):
        b["cover"] = C(cov)
    if not b.get("blurb"):
        b.update({"blurb": bl, "blurbSrc": src, "blurbLang": "ru"})
io.open(P, "w", encoding="utf-8").write(json.dumps(idx, ensure_ascii=False, indent=2) + "\n")
print("done")
