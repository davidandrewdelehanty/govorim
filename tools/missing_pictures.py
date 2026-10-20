#!/usr/bin/env python3
"""The last bare tiles (19 Oct 2026):

  1. the English-library books still on Project Gutenberg's plain printed
     cover, and Love-at-arms (whose picture file never landed): a
     public-domain painting found with subjects chosen for each book by hand,
     through fallback_pictures.pick (artworks only, PD/CC0, no painting used
     twice);
  2. the authors pictured only by one of their books: a portrait from the
     person's Commons category (Wikidata P373), or Wikipedia's lead image,
     when it is free and the person is a human whose life years agree.

    cd /mnt/c/Users/david/projects/govorim-app
    python3 tools/missing_pictures.py
"""
import io, json, os, re, sys, urllib.parse

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.chdir(ROOT)
sys.path.insert(0, os.path.join(ROOT, "tools"))
import english_covers as ec
import english_pictures as ep
import fallback_pictures as fp

STATE = "tools/missing_pictures_state.json"

QUERIES = {
    "en-love-at-arms-sabatini": ["condottiere", "Paolo Uccello battle", "Renaissance cavalry"],
    "en-pragmatism-james": ["philosopher", "thinker", "scholar study"],
    "en-the-essays-or-counsels-civil-and-moral-bacon": ["scholar study", "philosopher", "Renaissance interior"],
    "en-whose-body-a-lord-peter-wimsey-novel-sayers": ["London fog night", "night street gaslight"],
    "en-monte-cristo-s-daughter-flagg": ["Marseille harbour", "Mediterranean coast", "ship at sea"],
    "en-mr-standfast-buchan": ["Scottish highlands", "First World War", "soldiers trenches"],
    "en-the-prairie-wife-stringer": ["prairie homestead", "prairie landscape", "wheat field"],
    "en-the-insidious-dr-fu-manchu-rohmer": ["Thames night", "London fog night", "nocturne"],
    "en-the-two-magics-james": ["English country house", "gothic ruins moonlight", "ghost"],
    "en-friday-the-thirteenth-lawson": ["Wall Street", "stock exchange", "New York street"],
    "en-terminal-compromise-schwartau": ["city night lights", "nocturne city", "telegraph"],
    "en-concrete-construction-gillette": ["bridge construction", "construction workers", "building site"],
    "en-microcosmography-or-a-piece-of-the-world-discovered-earle": ["genre painting tavern", "Dutch genre painting", "London street"],
    "en-the-air-pirate-thorne": ["airship", "balloon flight", "aeroplane"],
    "en-the-camp-fire-girls-solve-a-mystery-frey": ["campfire", "girls camping", "lake forest"],
    "en-unnatural-death-sayers": ["English village", "night street gaslight"],
    "en-palmistry-for-all-cheiro": ["fortune teller", "palm reading", "gypsy fortune"],
    "en-the-samurai-strategy-hoover": ["samurai", "ukiyo-e warrior", "Japanese castle"],
    "en-sally-of-missouri-young": ["Missouri river", "American farm", "prairie"],
    "en-life-blood-hoover": ["laboratory", "physician", "surgery"],
    "en-by-advice-of-counsel-train": ["courtroom", "lawyer", "trial"],
    "en-peter-the-brazen-worts": ["Chinese junk", "Shanghai", "Chinese harbour"],
    "en-occasion-for-disaster-garrett": ["night sky stars", "comet", "moonlight"],
    "en-the-hand-in-the-dark-rees": ["country house night", "moonlight", "candlelight interior"],
    "en-essays-second-series-emerson": ["New England landscape", "Hudson River School", "forest stream"],
    "en-the-yellow-crayon-oppenheim": ["Paris boulevard night", "London street", "nocturne"],
    "en-the-son-of-monte-cristo-lermina": ["Paris boulevard", "Marseille harbour", "Mediterranean coast"],
    "en-the-girl-philippa-chambers": ["First World War", "Paris street", "soldiers"],
    "en-the-zeppelin-s-passenger-oppenheim": ["zeppelin", "Norfolk coast", "airship"],
    "en-children-of-the-whirlwind-scott": ["New York street", "nocturne city", "city night"],
    "en-a-case-in-camera-onions": ["artist studio", "courtroom", "painter at work"],
    "en-the-entailed-hat-townsend": ["Chesapeake", "Maryland landscape", "plantation"],
    "en-in-connection-with-the-de-willoughby-claim-burnett": ["Tennessee mountains", "country store", "Appalachian"],
}


def books(state):
    idx = json.load(io.open(ec.MANIFEST, encoding="utf-8"))
    used = set()
    for p in ("tools/fallback_pictures_state.json", STATE):
        if os.path.exists(p):
            s = json.load(io.open(p, encoding="utf-8"))
            used |= {v["file"] for v in (s.get("books") or {}).values() if v and v.get("file")}
    todo = [b for b in idx if b.get("slug") in QUERIES and b["slug"] not in state["books"]
            and (re.match(r"^img/pg\d+\.jpg$", b.get("cover") or "")
                 or not os.path.exists(os.path.join("public/books", b.get("cover") or "x")))]
    print("%d book(s) to picture" % len(todo), flush=True)
    changes = {}
    for i, b in enumerate(todo, 1):
        fp.queries_for = lambda bb, q=QUERIES[b["slug"]]: (q, [])
        nme, inf, q, _ = fp.pick(b, used)
        path = ec.save_cover(nme, inf) if nme else None
        state["books"][b["slug"]] = {"file": nme, "path": path, "q": q} if path else None
        if path:
            used.add(nme); changes[b["slug"]] = path
        print("[%d/%d] %-44s %s" % (i, len(todo), b["title"][:44], ("✓ %s  ← %s" % (nme[:50], q)) if path else "— nothing suitable"), flush=True)
    ec.set_covers(changes)


def is_portrait_name(f, person):
    sn = person.split()[-1].lower()
    return sn in f.lower() and not ec.BAD.search(f) and re.search(r"\.(jpe?g|png|tiff?)$", f, re.I)


def authors(state):
    out_p = "src/authors-en.json"
    out = json.load(io.open(out_p, encoding="utf-8"))
    todo = [a for a, v in out.items() if v.get("fromBook") and a not in state["authors"]]
    print("\n%d author(s) to picture" % len(todo), flush=True)
    for i, a in enumerate(todo, 1):
        ys = [int(y) for y in re.findall(r"\d{3,4}", out[a].get("years") or "")]
        ids = ep.wd_search('"%s"' % a, "haswbstatement:P31=Q5")[:5]
        ents = ep.wd_entities(ids)
        cands = []
        for qid in ids:
            e = ents.get(qid) or {}
            born = ep.year_of((ep.claim_vals(e, "P569") or [None])[0])
            died = ep.year_of((ep.claim_vals(e, "P570") or [None])[0])
            if not ys or not born or abs(born - ys[0]) > 2:
                continue            # only a person whose years we can match
            if len(ys) > 1 and died and abs(died - ys[1]) > 2:
                continue
            cands += ep.claim_vals(e, "P18")
            for cat in ep.claim_vals(e, "P373"):
                cands += [f for f in ec.cat_files(cat, depth=0, limit=40) if is_portrait_name(f, a)]
            title = ((e.get("sitelinks") or {}).get("enwiki") or {}).get("title")
            if not title:
                j = ec.get("https://www.wikidata.org/w/api.php?" + urllib.parse.urlencode(
                    {"action": "wbgetentities", "format": "json", "ids": qid, "props": "sitelinks", "sitefilter": "enwiki"}))
                title = (((((j or {}).get("entities") or {}).get(qid) or {}).get("sitelinks") or {}).get("enwiki") or {}).get("title")
            if title:
                j = ec.get("https://en.wikipedia.org/w/api.php?" + urllib.parse.urlencode(
                    {"action": "query", "format": "json", "prop": "pageimages", "piprop": "name", "titles": title}))
                for pg in (((j or {}).get("query") or {}).get("pages") or {}).values():
                    if pg.get("pageimage"):
                        cands.append(pg["pageimage"].replace("_", " "))
            break
        rec = None
        if cands:
            inf = ec.infos(cands[:20])
            for f in cands[:20]:
                k = inf.get(f)
                if k and k["free"] and re.match(r"image/(jpeg|png)", k["mime"]):
                    path = ep.save_thumb(f, "au")
                    if path:
                        rec = {"name": a, "years": out[a].get("years") or "", "file": "/books/" + path}
                        break
        if rec:
            out[a] = rec
        state["authors"][a] = bool(rec)
        print("[%d/%d] %-40s %s" % (i, len(todo), a[:40], "portrait" if rec else "— none free"), flush=True)
        io.open(out_p, "w", encoding="utf-8").write(json.dumps(out, ensure_ascii=False, indent=1))
        io.open(STATE, "w", encoding="utf-8").write(json.dumps(state, ensure_ascii=False))


def main():
    state = json.load(io.open(STATE, encoding="utf-8")) if os.path.exists(STATE) else {"books": {}, "authors": {}}
    books(state)
    io.open(STATE, "w", encoding="utf-8").write(json.dumps(state, ensure_ascii=False))
    authors(state)
    nb = sum(1 for v in state["books"].values() if v); na = sum(1 for v in state["authors"].values() if v)
    print("\nDone: %d book(s) given a painting; %d author(s) given a portrait." % (nb, na))


if __name__ == "__main__":
    main()
