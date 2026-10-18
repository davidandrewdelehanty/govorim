#!/usr/bin/env python3
"""«Беседа преподобного Серафима Саровского с Мотовиловым о цели христианской
жизни» on the Scripture (Religious Texts) shelf. Runs in WSL (network).

Н. А. Мотовилов's record (1831; he died 1879) of his talk with St Seraphim,
first printed by С. Нилус in 1903, from Russian Wikisource. There is no
public-domain English translation, so it goes up Russian-only.

    cd /mnt/c/Users/david/projects/govorim-app
    python3 tools/serafim.py
    python3 tools/gen_stress_maps.py
    python3 tools/make_case_drills.py --book serafim-motovilov.fb2
"""
import io, json, os, subprocess, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.chdir(ROOT)
sys.path.insert(0, os.path.join(ROOT, "tools"))
from translations_build import modernise_fb2

SLUG = "serafim-motovilov"
PAGE = "Беседа преподобного Серафима о цели христианской жизни (Мотовилов)"
TITLE = "Беседа преподобного Серафима Саровского с Мотовиловым о цели христианской жизни"
MANIFEST = "private/books/index.json"

r = subprocess.run([sys.executable, "tools/add_wikisource.py", PAGE, "--slug", SLUG, "--title", TITLE,
                    "--author", "Серафим Саровский", "--category", "Religious Texts", "--allow-duplicate"])
if r.returncode != 0 or not os.path.exists("public/books/novel/%s.fb2" % SLUG):
    sys.exit("import failed")
print("spelling modernised" if modernise_fb2(SLUG) else "spelling already modern")
idx = json.load(io.open(MANIFEST, encoding="utf-8"))
for b in idx:
    if b.get("slug") == SLUG:
        b.update({
            "category": "Religious Texts", "author": "Серафим Саровский", "title": TITLE, "year": 1831,
            "public": True,
            "cover": "https://commons.wikimedia.org/wiki/Special:FilePath/"
                     "Saint_Serafim_Of_Sarov_Portrait_Painted_During_His_Life.jpg?width=500",
            "blurb": "Серафим Саровский — иеромонах Саровского монастыря, основатель и покровитель Дивеевской "
                     "женской обители. Прославлен Русской православной церковью в 1903 году в лике преподобных. "
                     "Великий подвижник Русской церкви и один из наиболее почитаемых монахов в её истории.",
            "blurbSrc": "https://ru.wikipedia.org/wiki/Серафим_Саровский", "blurbLang": "ru",
        })
        print("catalogued: %s, %s words" % (b["filename"], format(b.get("words", 0), ",")))
io.open(MANIFEST, "w", encoding="utf-8").write(json.dumps(idx, ensure_ascii=False, indent=2) + "\n")
print("Done. Next: python3 tools/gen_stress_maps.py, then the case drills (see the top of this file).")
