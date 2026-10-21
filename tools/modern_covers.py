#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Pictures for the Modern Russian shelf: the subject itself, where its
picture is free to use — the band, the writer, the city.

For each book on the shelf that has no cover yet:

  1. Wikipedia / Wikivoyage articles: the article's own pictures — its lead
     image, the Wikidata image of the subject, then the other files used on
     the page — kept when Commons says the file is free to republish: public
     domain, CC0, CC BY or CC BY-SA (a concert photograph of the band under
     CC BY-SA is what the shelf wants; a fair-use album cover is not). The
     article's own lead picture wins when it passes; the photographer and
     licence are written into the catalogue entry (coverCredit), as CC BY
     and BY-SA require, and the tile shows them.
  2. Anything left (a rock band with only CC BY-SA photographs, the monthly
     Wikinews books, the official documents) gets a public-domain painting
     of the right kind — gusli-players and singers for the rock articles, a
     city painting for a city guide, a Kremlin or a Petersburg view for the
     state documents, a reader of newspapers for the news — found as an
     artwork on Commons. No painting is used twice, here or in the other
     picture tools' state files.

Nothing is drawn or generated; every file is a Commons file and is named in
tools/modern_covers_state.json with its licence. Run where Wikimedia is
reachable (WSL):

    cd /mnt/c/Users/david/projects/govorim-app
    python3 tools/modern_covers.py            # books with no cover yet
    python3 tools/modern_covers.py --redo     # all of them again
    python3 tools/modern_covers.py --slug modern-wikipedia-kino-gruppa

Review sheet: private/cover_review/modern.html
"""
import argparse, io, json, os, re, sys, urllib.parse

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.chdir(ROOT)
sys.path.insert(0, os.path.join(ROOT, "tools"))
import english_covers as ec          # get, infos, look, save_cover, set_covers, BAD, CM
import fallback_pictures as fp       # artworks

STATE = "tools/modern_covers_state.json"
WD = "https://www.wikidata.org/w/api.php"
# Free to republish with credit — wider than english_covers' public-domain-only test.
OK_LIC = re.compile(r"public domain|\bpd\b|pd-|cc0|cc zero|cc[- ]by(?:[- ]sa)?(?:[- ]\d)?|attribution(?!.*non)|gfdl|gnu free doc|free art|no restrictions|общественн", re.I)
UNFREE = re.compile(r"fair.?use|non-?free|несвободн|non-?commercial|\bnc\b|no derivative|\bnd\b|all rights", re.I)
SHUN = re.compile(r"\.svg$|\.gif$|\.tiff?$|\.webm$|\.ogg$|\.ogv$|\.pdf$|flag|icon|logo|symbol|commons-|wiki|"
                  r"coat[_ ]of[_ ]arms|герб|флаг|\bmap\b|карта|signature|подпись|ambox|edit-|question|"
                  r"disambig|stub|crystal|nuvola|folder|speaker|play|audio|noimage|no[_ ]image|"
                  r"album|single|\bcd\b|\bdvd\b|обложка|\.jpg\.jpeg", re.I)

# Fallback pictures: Commons artwork searches, tried in this order for a kind.
# `named` are (title, painter) pairs looked up on Wikidata first.
FALLBACK = {
    "rock": dict(
        named=[("Гусляры", "Васнецов|Vasnetsov"), ("Баян", "Васнецов|Vasnetsov"),
               ("Песня", "Малявин|Malyavin"), ("Вихри", "Малявин|Malyavin"),
               ("Крестьянка с гармонью", "Малявин|Malyavin")],
        qs=["gusli player painting", "balalaika painting", "singer guitar painting 19th century",
            "folk musicians painting Russia", "street musicians painting", "troubadour painting",
            "concert hall painting", "violinist painting", "choir painting"]),
    "author": dict(
        named=[("Читатель", "Крамской|Kramskoi"), ("Неизвестная", "Крамской|Kramskoi"),
               ("Поэт", "Бакст|Bakst")],
        qs=["writer at desk painting", "poet painting portrait 19th century", "reading woman painting",
            "library interior painting", "man reading book painting", "study with books painting"]),
    "city": dict(
        named=[],
        qs=["Russian town view painting", "Russian city street painting", "panorama of a Russian city painting",
            "Russian church and river painting", "winter town Russia painting", "old Russian town painting"]),
    "state": dict(
        named=[("Московский Кремль", "Верещагин|Vereshchagin"), ("Красная площадь", "Юон|Yuon"),
               ("Вид на Кремль", "Саврасов|Savrasov")],
        qs=["Moscow Kremlin painting", "Saint Petersburg Palace Embankment painting", "Winter Palace painting",
            "Red Square painting", "Peter and Paul Fortress painting"]),
    "news": dict(
        named=[("Читатели газет", "Маковский|Makovsky")],
        qs=["newspaper reader painting", "Moscow street painting 19th century", "Nevsky Prospect painting",
            "people reading newspaper painting", "market square Russia painting"]),
    "other": dict(named=[], qs=["Russian landscape painting", "birch grove painting", "Russian village painting"]),
}


def kind_of(b, authors):
    src = b.get("blurbSrc") or ""
    note = b.get("_note") or ""
    a = b.get("author") or ""
    if "ru.wikipedia.org" in src or "ru.wikipedia.org" in note:
        return "author" if (b.get("title") in authors or b.get("slug") in authors) else "rock"
    if "wikivoyage" in src or "wikivoyage" in note:
        return "city"
    if "Викиновости" in a:
        return "news"
    if "Российская Федерация" in a:
        return "state"
    return "other"


def wiki_title(b):
    """(host, title) of the article a Wikipedia/Wikivoyage book came from."""
    for s in (b.get("blurbSrc") or "", b.get("_note") or ""):
        m = re.search(r"https?://(ru\.wiki(?:pedia|voyage)\.org)/wiki/([^\s,;]+)", s)
        if m:
            return m.group(1), urllib.parse.unquote(m.group(2)).replace("_", " ")
    return None, None


def api(host, **p):
    p.setdefault("format", "json"); p.setdefault("formatversion", "2")
    return ec.get("https://%s/w/api.php?%s" % (host, urllib.parse.urlencode(p)))


def article_files(host, title):
    """Files of an article, best first: lead image, Wikidata image, the rest."""
    j = api(host, action="query", prop="pageimages|pageprops|images", piprop="name", imlimit="60",
            redirects="1", titles=title, ppprop="wikibase_item")
    pages = ((j or {}).get("query") or {}).get("pages") or []
    if not pages or pages[0].get("missing"):
        return []
    p = pages[0]
    out = []
    if p.get("pageimage"):
        out.append(p["pageimage"].replace("_", " "))
    qid = (p.get("pageprops") or {}).get("wikibase_item")
    if qid:
        q = ec.get(WD + "?" + urllib.parse.urlencode({"action": "wbgetentities", "format": "json", "ids": qid,
                                                       "props": "claims"}))
        try:
            for c in q["entities"][qid]["claims"].get("P18", []):
                v = c["mainsnak"]["datavalue"]["value"]
                if v not in out:
                    out.append(v.replace("_", " "))
        except Exception:
            pass
    for im in p.get("images") or []:
        n = im["title"].split(":", 1)[-1].replace("_", " ")
        if n not in out:
            out.append(n)
    return [n for n in out if not SHUN.search(n)][:24]


def artist_of(name):
    """The file's author, as Commons records it, for the credit line."""
    q = urllib.parse.urlencode({"action": "query", "format": "json", "prop": "imageinfo", "iiprop": "extmetadata",
                                "iiextmetadatafilter": "Artist|Credit", "titles": "File:" + name})
    j = ec.get(ec.CM + "?" + q)
    try:
        em = list(j["query"]["pages"].values())[0]["imageinfo"][0]["extmetadata"]
        a = (em.get("Artist") or {}).get("value") or (em.get("Credit") or {}).get("value") or ""
    except Exception:
        return ""
    a = re.sub(r"<[^>]+>", " ", a)
    a = re.sub(r"\s+", " ", a).strip()
    a = re.sub(r"^(User|Участник):", "", a)
    return a[:60]


def judge(names, used, bonus_first=True, loose=False):
    """The best free file of `names`: (name, info) or (None, None). `loose`:
    CC BY and BY-SA pass too (with credit), not only public domain and CC0."""
    if not names:
        return None, None
    inf = ec.infos(names)
    scored = []
    for k, n in enumerate(names):
        i = inf.get(n)
        if not i or n in used:
            continue
        ok = i["free"] or (loose and OK_LIC.search(i["lic"] or "") and not UNFREE.search(i["lic"] or ""))
        if not ok:
            continue
        if not re.match(r"image/(jpeg|png)", i["mime"]):
            continue
        if i["w"] < 380 or i["h"] < 380:
            continue
        ar = i["w"] / float(i["h"])
        if not (0.45 <= ar <= 2.2) or ec.BAD.search(n):
            continue
        data = ec.get(i["thumb"], binary=True)
        v = ec.look(data) if data else None
        if v is None:
            continue
        # a lead image is the article's own choice of what it is about — the band, the writer, the city
        scored.append((v + (4.0 if (k == 0 and bonus_first) else 1.0 if (k == 1 and bonus_first) else 0) + min(1.5, i["w"] * i["h"] / 3e6)
                       + (0.8 if 0.6 <= ar <= 1.5 else 0), n, i))
        if len(scored) >= 6:
            break
    scored.sort(reverse=True)
    if scored and scored[0][0] > -0.8:
        return scored[0][1], scored[0][2]
    return None, None


def from_queries(kind, used, seed):
    spec = FALLBACK.get(kind) or FALLBACK["other"]
    try:
        import tile_pictures as tp
    except Exception:
        tp = None
    named = list(spec["named"])
    if named:
        r = seed % len(named)
        named = named[r:] + named[:r]
    for t, painter in named:
        if tp is None:
            break
        try:
            f = tp.painting(t, painter)
        except Exception:
            f = None
        if f and f not in used:
            i = ec.infos([f]).get(f)
            if i and i["free"] and re.match(r"image/(jpeg|png)", i["mime"]) and i["w"] >= 500:
                return f, i, "painting: %s (%s)" % (t, painter.split("|")[0])
    qs = list(spec["qs"])
    r = seed % len(qs)
    qs = qs[r:] + qs[:r]
    for q in qs:
        names = [x for x in fp.artworks(q, 20) if x not in used and not fp.NEVER.search(x)]
        n, i = judge([x for x in names if not ec.PORTRAIT.search(x)][:20], used, bonus_first=False)
        if n:
            return n, i, "search: " + q
    return None, None, None


def review(state, books):
    rows = []
    for b in books:
        s = state["books"].get(b["slug"]) or {}
        pic = b.get("cover") or ""
        rows.append('<figure><img src="../../public/books/%s" loading="lazy"><figcaption><b>%s</b><br>%s<br>'
                    '<small>%s · %s</small></figcaption></figure>' % (
                        pic, b.get("title", ""), s.get("how", ""), (s.get("file") or "—")[:60], s.get("lic", "")))
    os.makedirs("private/cover_review", exist_ok=True)
    io.open("private/cover_review/modern.html", "w", encoding="utf-8").write(
        "<meta charset=utf-8><style>body{font:14px sans-serif;background:#222;color:#ddd;display:flex;flex-wrap:wrap;gap:12px;padding:12px}"
        "figure{margin:0;width:200px}img{width:200px;height:260px;object-fit:cover;background:#000}small{color:#999}</style>"
        + "".join(rows))


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--redo", action="store_true")
    ap.add_argument("--slug")
    a = ap.parse_args()
    state = json.load(io.open(STATE, encoding="utf-8")) if os.path.exists(STATE) else {"books": {}}
    used = {v["file"] for v in state["books"].values() if v and v.get("file")}
    for other in ("tools/fallback_pictures_state.json", "tools/english_covers_state.json"):
        try:
            for v in json.load(io.open(other, encoding="utf-8")).get("books", {}).values():
                if isinstance(v, dict) and v.get("file"):
                    used.add(v["file"])
        except Exception:
            pass
    authors = set()
    ap_ = os.path.join("tools", "modern", "authors.txt")
    if os.path.exists(ap_):
        for line in io.open(ap_, encoding="utf-8"):
            line = line.split("#", 1)[0].strip()
            if line:
                authors.add(line)
                authors.add(re.sub(r"\s*\(.*\)$", "", line))
    idx = json.load(io.open(ec.MANIFEST, encoding="utf-8"))
    shelf = [b for b in idx if b.get("category") == "Modern Russian"]
    # an article title as the book carries it: «Пушкин, Александр Сергеевич»
    for b in shelf:
        h, t = wiki_title(b)
        if t and b.get("title") == t:
            pass
    todo = [b for b in shelf if (a.redo or not b.get("cover")) and (not a.slug or b["slug"] == a.slug)]
    print("%d book(s) on the shelf, %d to picture" % (len(shelf), len(todo)), flush=True)
    changes, credits, n_own, n_fb = {}, {}, 0, 0
    for k, b in enumerate(todo, 1):
        slug = b["slug"]
        kind = kind_of(b, authors)
        host, title = wiki_title(b)
        name = info = how = None
        if host and title:
            name, info = judge(article_files(host, title), used, True, True)
            if name:
                how = "article image"
        if not name:
            name, info, how = from_queries(kind, used, k)
            n_fb += 1 if name else 0
        else:
            n_own += 1
        path = ec.save_cover(name, info) if name else None
        if path:
            used.add(name)
            changes[slug] = path
            artist = artist_of(name) if how == "article image" else ""
            credits[slug] = (artist + (", " if artist else "") + (info["lic"] or "")).strip(", ") if how == "article image" else ""
            state["books"][slug] = {"file": name, "path": path, "lic": info["lic"], "how": how, "kind": kind, "credit": credits[slug]}
            print("[%d/%d] %-44s ✓ %-8s %s  [%s]" % (k, len(todo), (b.get("title") or "")[:44], kind, name[:40], how), flush=True)
        else:
            print("[%d/%d] %-44s — nothing suitable (%s)" % (k, len(todo), (b.get("title") or "")[:44], kind), flush=True)
        if k % 10 == 0 or k == len(todo):
            ec.set_covers(changes); changes = {}
            io.open(STATE, "w", encoding="utf-8").write(json.dumps(state, ensure_ascii=False, indent=1))
    ec.set_covers(changes)
    # the credit each licence asks for, on the entry beside the cover
    man = json.load(io.open(ec.MANIFEST, encoding="utf-8"))
    for b in man:
        st = state["books"].get(b.get("slug"))
        if st and st.get("credit") is not None and b.get("category") == "Modern Russian":
            if st["credit"]:
                b["coverCredit"] = st["credit"]
            elif "coverCredit" in b:
                del b["coverCredit"]
    io.open(ec.MANIFEST, "w", encoding="utf-8").write(json.dumps(man, ensure_ascii=False, indent=2) + "\n")
    io.open(STATE, "w", encoding="utf-8").write(json.dumps(state, ensure_ascii=False, indent=1))
    idx = json.load(io.open(ec.MANIFEST, encoding="utf-8"))
    review(state, [b for b in idx if b.get("category") == "Modern Russian"])
    left = sum(1 for b in idx if b.get("category") == "Modern Russian" and not b.get("cover"))
    print("\nDone: %d from the article's own pictures, %d from a painting; %d still bare. Review: private/cover_review/modern.html"
          % (n_own, n_fb, left))


if __name__ == "__main__":
    main()
