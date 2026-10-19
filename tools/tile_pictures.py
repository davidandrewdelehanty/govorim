#!/usr/bin/env python3
"""A picture on every tile that still lacks a good one:

  1. the Courses tiles (Textbooks shelf): a famous public-domain Russian
     painting each, found on Wikidata by title and painter, copied onto our
     own site (public/books/img/crs-*.jpg) → src/course-pictures.json
  2. the Soviet textbooks on a plain printed cover or none: the two Vipper
     histories get an engraving from inside the book; the others a public-
     domain painting suited to the book
  3. English-library books whose fallback picture was a poor one (a logo, a
     modern edition's cover, a scanned page of "A history of painting"):
     picked again with those excluded

Public domain / CC0 only (english_covers.FREE). Run after
tools/fallback_pictures.py has finished — both write the catalogue.
    cd /mnt/c/Users/david/projects/govorim-app
    python3 tools/tile_pictures.py
Then open private/cover_review/tiles.html to look them over.
"""
import hashlib, io, json, os, re, sys, urllib.parse

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.chdir(ROOT)
sys.path.insert(0, os.path.join(ROOT, "tools"))
import english_covers as ec          # get, infos, save_cover, CM, MANIFEST, IMG
import fallback_pictures as fp       # pick, artworks

WD = "https://www.wikidata.org/w/api.php"

# (English title on Wikidata, painter's surname as Wikidata spells it)
COURSES = {
    "wikibook": [("At the School Doors", "Bogdanov-Belsky"), ("Sunday Reading in a Village School", "Bogdanov-Belsky")],
    "dli":      [("Sunday Reading in a Village School", "Bogdanov-Belsky"), ("Visitors", "Bogdanov-Belsky")],
    "motion":   [("Barge Haulers on the Volga", "Repin"), ("Troika", "Perov")],
    "time":     [("Morning in a Pine Forest", "Shishkin"), ("Rye", "Shishkin")],
    "count":    [("Mental Arithmetic", "Bogdanov-Belsky"), ("Mental Calculation", "Bogdanov-Belsky")],
    "cases":    [("Merchant's Wife at Tea", "Kustodiev"), ("Maslenitsa", "Kustodiev")],
    "forms":    [("Reply of the Zaporozhian Cossacks", "Repin"), ("Religious Procession in Kursk Province", "Repin")],
    "tenses":   [("They Did Not Expect Him", "Repin"), ("Unexpected Visitors", "Repin")],
    "case-nom": [("Golden Autumn", "Levitan"), ("March", "Levitan")],
    "case-gen": [("Bogatyrs", "Vasnetsov"), ("Knight at the Crossroads", "Vasnetsov")],
    "case-dat": [("Moonlit Night on the Dnieper", "Kuindzhi"), ("Birch Grove", "Kuindzhi")],
    "case-acc": [("The Ninth Wave", "Aivazovsky"), ("The Black Sea", "Aivazovsky")],
    "case-ins": [("The Rooks Have Come Back", "Savrasov"), ("Winter Road", "Savrasov")],
    "case-prp": [("Alyonushka", "Vasnetsov"), ("Above Eternal Peace", "Levitan")],
    "aspect":   [("Leo Tolstoy Ploughing", "Repin"), ("Mowers", "Myasoyedov")],
    "verbs":    [("Bathing of a Red Horse", "Petrov-Vodkin"), ("Troika", "Perov")],
    "compare":  [("The Vladimirka Road", "Levitan"), ("Evening Bells", "Levitan")],
    "pronouns": [("Unknown Woman", "Kramskoi"), ("Portrait of an Unknown Woman", "Kramskoi")],
    "complex":  [("Ivan Tsarevich Riding the Grey Wolf", "Vasnetsov"), ("The Knight at the Crossroads", "Vasnetsov")],
    "inter2":   [("The Swan Princess", "Vrubel"), ("Lilacs", "Vrubel")],
    "adv3":     [("The Demon Seated", "Vrubel"), ("Pan", "Vrubel")],
    "stories":  [("The Unequal Marriage", "Pukirev"), ("Tea-Drinking in Mytishchi", "Perov")],
}
TEXTBOOK_PAINTINGS = {
    "povarnin-iskusstvo-spora": [("Hunters at Rest", "Perov"), ("The School of Athens", "Raphael")],
    "povarnin-logika":          [("The School of Athens", "Raphael"), ("Philosopher in Meditation", "Rembrandt")],
    "rebelsky-azbuka":          [("Leo Tolstoy in His Study", "Repin"), ("Portrait of Leo Tolstoy", "Repin")],
    "povarnin-kak-chitat":      [("Sunday Reading in a Village School", "Bogdanov-Belsky"), ("Reading Girl", "Fragonard")],
    "shcherba-kak-izuchat":     [("The Tower of Babel", "Bruegel"), ("The Tower of Babel", "Valckenborch")],
}
# Pictures from inside the book itself.
TEXTBOOK_OWN = {
    "vipper-drevnost": "textbooks/vipper-drevnost/f150.webp",          # the Colosseum
    "vipper-srednie-veka": "textbooks/vipper-srednie-veka/f101.webp",  # castle and fields, a book of hours
    "vipper-novoe-vremya": "textbooks/vipper-novoe-vremya/f123.webp",  # the Peter and Paul Fortress
}
# English-library picks to do again, and pictures never to use.
REDO_TITLES = re.compile(r"^(Belgium|Anarchism and Other Essays|2 B R 0 2 B)$")
BANNED = re.compile(r"history of painting|\blogo\b|film fest|\b(19[3-9]\d|20\d\d)\b", re.I)


def painting(title, painter):
    """The Commons file of a painting on Wikidata, by its English title and painter."""
    q = urllib.parse.urlencode({"action": "wbsearchentities", "format": "json", "language": "en",
                                "type": "item", "limit": 10, "search": title})
    hits = [h["id"] for h in ((ec.get(WD + "?" + q) or {}).get("search") or [])]
    if not hits:
        return None
    q = urllib.parse.urlencode({"action": "wbgetentities", "format": "json", "ids": "|".join(hits),
                                "props": "claims|labels|descriptions", "languages": "en"})
    ents = (ec.get(WD + "?" + q) or {}).get("entities") or {}
    for i in hits:
        e = ents.get(i) or {}
        desc = ((e.get("descriptions") or {}).get("en") or {}).get("value", "")
        if painter.split("-")[0].lower() not in desc.lower():
            continue
        imgs = [((c.get("mainsnak") or {}).get("datavalue") or {}).get("value") for c in (e.get("claims") or {}).get("P18", [])]
        imgs = [x for x in imgs if x]
        if imgs:
            return imgs[0]
    # Not on Wikidata under that title: an artwork search on Commons.
    for n in fp.artworks(painter + " " + title, 10):
        if painter.split("-")[0].lower() in n.lower():
            return n
    return None


def fetch(cands, prefix):
    for title, painter in cands:
        f = painting(title, painter)
        if not f:
            print("   · not found: %s (%s)" % (title, painter))
            continue
        inf = ec.infos([f]).get(f)
        if not inf or not inf["free"]:
            print("   · not public domain: %s [%s]" % (f, inf and inf["lic"]))
            continue
        path = ec.save_cover(f, inf, width=900)
        if path:
            name = "%s-%s.jpg" % (prefix, hashlib.sha1(f.encode("utf-8")).hexdigest()[:12])
            os.replace(os.path.join(ec.IMG, os.path.basename(path)), os.path.join(ec.IMG, name))
            return {"img": "/books/img/" + name, "file": f, "title": title, "by": painter, "lic": inf["lic"]}
    return None


def main():
    review = []
    # 1. Courses
    out_p = "src/course-pictures.json"
    cp = json.load(io.open(out_p, encoding="utf-8")) if os.path.exists(out_p) else {}
    for cid, cands in COURSES.items():
        if cid in cp:
            continue
        r = fetch(cands, "crs")
        print("course %-9s %s" % (cid, ("✓ " + r["file"]) if r else "— nothing"), flush=True)
        if r:
            cp[cid] = r; review.append(("Course: " + cid, r["img"], r["file"]))
    io.open(out_p, "w", encoding="utf-8").write(json.dumps(cp, ensure_ascii=False, indent=1) + "\n")

    # 2. Textbooks, and 3. English redos — both write the catalogue.
    idx = json.load(io.open(ec.MANIFEST, encoding="utf-8"))
    by = {b.get("slug"): b for b in idx if b.get("slug")}
    changes = {}
    for slug, path in TEXTBOOK_OWN.items():
        if slug in by and os.path.exists(os.path.join("public/books", path)):
            changes[slug] = path; review.append(("Textbook: " + by[slug]["title"], "/books/" + path, "from the book"))
    for slug, cands in TEXTBOOK_PAINTINGS.items():
        b = by.get(slug)
        if not b or (b.get("cover") or "").startswith("img/tb-"):
            continue
        r = fetch(cands, "tb")
        print("textbook %-26s %s" % (slug, ("✓ " + r["file"]) if r else "— nothing"), flush=True)
        if r:
            changes[slug] = r["img"][len("/books/"):]; review.append(("Textbook: " + b["title"], r["img"], r["file"]))

    st_p = "tools/fallback_pictures_state.json"
    st = json.load(io.open(st_p, encoding="utf-8")) if os.path.exists(st_p) else {"books": {}}
    used = {v["file"] for v in st["books"].values() if v and v.get("file")}
    redo = [b for b in idx if b.get("lang") == "en" and (
        REDO_TITLES.match(b.get("title") or "") or
        ((st["books"].get(b.get("slug")) or {}).get("file") and BANNED.search(st["books"][b["slug"]]["file"])))]
    old_bad = ec.BAD
    ec.BAD = re.compile(old_bad.pattern + r"|history of painting|film fest|\blogo\b", re.I)
    for b in redo:
        nme, inf, q, subs = fp.pick(b, used)
        if nme and not BANNED.search(nme):
            path = ec.save_cover(nme, inf)
            if path:
                used.add(nme); changes[b["slug"]] = path
                st["books"][b["slug"]] = {"file": nme, "path": path, "q": q}
                review.append(("Redo: " + b["title"], "/books/" + path, nme))
        print("redo %-40s %s" % (b["title"][:40], ("✓ " + nme) if nme else "— nothing"), flush=True)
    io.open(st_p, "w", encoding="utf-8").write(json.dumps(st, ensure_ascii=False))

    fresh = json.load(io.open(ec.MANIFEST, encoding="utf-8"))
    for b in fresh:
        if b.get("slug") in changes:
            b["cover"] = changes[b["slug"]]
    io.open(ec.MANIFEST, "w", encoding="utf-8").write(json.dumps(fresh, ensure_ascii=False, indent=2) + "\n")

    os.makedirs("private/cover_review", exist_ok=True)
    html = ["<!doctype html><meta charset=utf-8><title>Tile pictures</title><style>body{font:14px sans-serif;display:flex;flex-wrap:wrap;gap:16px;padding:16px}"
            "figure{width:220px;margin:0}img{width:220px;height:293px;object-fit:cover;border:1px solid #ccc}</style>"]
    for t, src, f in review:
        html.append("<figure><img src='../../public%s'><figcaption><b>%s</b><br>%s</figcaption></figure>" % (src, t, f))
    io.open("private/cover_review/tiles.html", "w", encoding="utf-8").write("\n".join(html))
    print("\nDone: %d course picture(s), %d catalogue change(s). Review: private/cover_review/tiles.html" % (len(cp), len(changes)))


if __name__ == "__main__":
    main()
