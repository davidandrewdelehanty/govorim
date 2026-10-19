#!/usr/bin/env python3
"""Pictures for what is still bare in the English library:

  1. books still on Project Gutenberg's plain printed cover — a public-domain
     painting suited to the book, found from its Gutenberg subjects (sea
     stories → a painting of ships at sea, westerns → Remington and Russell,
     detective stories → a gaslit street at night, Mars → the night sky …);
     only Commons files that are artworks (structured data "digital
     representation of" a work) and public domain or CC0. No painting is used
     twice.
  2. authors with no portrait — the cover of their best-known book in the
     library (the first of theirs in the catalogue, which is in popularity
     order), preferring a painting or film still over a printed cover.

Run after tools/english_covers.py. Uses its helpers.
    cd /mnt/c/Users/david/projects/govorim-app
    python3 tools/fallback_pictures.py
"""
import io, json, os, re, sys, urllib.parse

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.chdir(ROOT)
sys.path.insert(0, os.path.join(ROOT, "tools"))
import english_covers as ec            # get, infos, look, save_cover, set_covers, CM, MANIFEST

STATE = "tools/fallback_pictures_state.json"

# Gutenberg subject words → what to look for. First match wins.
THEMES = [
    (r"detective|mystery|crime|murder|police", ["night street gaslight", "London fog night", "nocturne city"]),
    (r"sea stor|seafaring|ships|sailors|pirat|whal|naval|voyages", ["ship at sea storm", "sailing ship", "harbour ships"]),
    (r"western|cowboy|ranch|frontier|indians of north america|west \(u\.s\.\)", ["Remington cowboy", "Charles Marion Russell", "prairie west"]),
    (r"science fiction|mars|interplanetary|space|moon|future", ["night sky stars", "comet", "moonlight"]),
    (r"ghost|horror|supernatural|occult|vampire|haunted", ["gothic ruins moonlight", "ghost", "graveyard night"]),
    (r"war|battle|military|soldier|army|campaign|revolution", ["battle", "cavalry charge", "soldiers"]),
    (r"love stor|romance|courtship|marriage|man-woman", ["lovers", "couple garden", "romantic"]),
    (r"fairy|folklore|legends|mythology|tales", ["fairy tale", "legend knight", "mythology"]),
    (r"children|juvenile|girls|boys|school", ["children playing", "girl reading", "schoolroom"]),
    (r"slave|african american|negro|abolition", ["Henry Ossawa Tanner", "plantation", "freedom"]),
    (r"religio|christian|bible|god|church|theolog|mystic", ["prayer", "church interior", "religious"]),
    (r"philosoph|ethics|logic|psycholog|metaphysic", ["philosopher", "scholar study", "thinker"]),
    (r"poetry|poems|verse|ballad", ["romantic landscape", "poet", "muse"]),
    (r"econom|finance|money|wall street|business|stock", ["merchant", "counting house", "bank"]),
    (r"garden|plant|botan|vegetable|flower|agricult", ["garden flowers", "botanical", "harvest"]),
    (r"travel|description and travel|voyage|journey|explor", ["traveller landscape", "expedition", "caravan"]),
    (r"history|historical|kings|queens|court", ["royal court", "palace interior", "battle scene"]),
    (r"humor|humorous|satire|comic", ["genre painting tavern", "humorous", "caricature"]),
    (r"art|drawing|painting|architecture", ["artist studio", "painter at work", "architecture"]),
    (r"science|chemistry|physics|geology|natural history|evolution", ["laboratory", "naturalist", "fossils"]),
]
CATEGORY = {"Novels": ["woman reading", "interior lamp"], "Short Stories": ["village street", "interior"],
            "Poetry": ["romantic landscape"], "Plays": ["theatre stage"], "History": ["royal court", "palace interior"],
            "Philosophy": ["philosopher"], "Religious Texts": ["religious"], "Fairytales": ["fairy tale"],
            "Novellas": ["landscape figure"]}
# A place is only trusted in Gutenberg's own form for one: "London (England)".
PLACE = re.compile(r"^([A-Z][\w'.]+(?: [A-Z][\w'.]+){0,2}) \((?:England|Scotland|Ireland|Wales|France|Italy|Spain|Germany|Russia|N\.Y\.|Mass\.|Calif\.|Ill\.|Pa\.|Va\.|India|Egypt|Greece|Japan|China|Canada|Mexico|[A-Z][a-z]+\.?)\)$")


def subjects(gid):
    j = ec.get("https://gutendex.com/books/%d" % gid) if gid else None
    if not j:
        return [], []
    return j.get("subjects") or [], j.get("bookshelves") or []


def queries_for(b):
    subs, shelves = subjects(b.get("gutenberg"))
    text = " | ".join(subs + shelves).lower()
    qs = []
    for pat, kws in THEMES:
        if re.search(pat, text):
            qs += kws
            break
    # A place in the subjects: "London (England) -- Fiction" → "London"
    for s in subs:
        for part in s.split("--"):
            part = part.strip()
            mm = PLACE.match(part)
            if mm and not re.search(r"fiction|history|biography|english|american|juvenile", part, re.I):
                place = mm.group(1).strip()
                if 3 < len(place) < 30:
                    qs.insert(0, place + " view")
                break
    qs += CATEGORY.get(b.get("category") or "", ["landscape"])
    out = []
    for q in qs:
        if q not in out:
            out.append(q)
    return out[:5], subs


NEVER = re.compile(r"history of painting|\blogo\b|film fest", re.I)


def artworks(q, n=15):
    p = urllib.parse.urlencode({"action": "query", "format": "json", "list": "search", "srnamespace": 6,
                                "srlimit": n, "srsearch": q + " haswbstatement:P6243 filetype:bitmap"})
    j = ec.get(ec.CM + "?" + p)
    return [h["title"][5:] for h in ((j or {}).get("query") or {}).get("search") or []]


def pick(b, used):
    qs, subs = queries_for(b)
    for q in qs:
        names = [x for x in artworks(q) if x not in used and not NEVER.search(x)]
        if not names:
            continue
        inf = ec.infos(names[:30])
        ok = []
        for nme in names[:30]:
            i = inf.get(nme)
            if not i or not i["free"] or not re.match(r"image/(jpeg|png)", i["mime"]):
                continue
            if i["w"] < 500 or i["h"] < 500 or not (0.5 <= i["w"] / float(i["h"]) <= 1.9):
                continue
            if ec.BAD.search(nme) or ec.PORTRAIT.search(nme):
                continue
            # About what was asked for: a whole word of the query in its name,
            # description or categories ("Mass" must not pass for Massachusetts).
            blob = (nme + " " + i["desc"] + " " + i["cats"]).lower()
            words = [w for w in re.findall(r"[a-z]{4,}", q.lower()) if w not in ("view", "painting")]
            if words and not any(re.search(r"\b" + re.escape(w) + r"s?\b", blob) for w in words):
                continue
            ok.append((nme, i))
        scored = []
        for nme, i in ok[:5]:
            data = ec.get(i["thumb"], binary=True)
            v = ec.look(data) if data else None
            if v is not None:
                scored.append((v + min(1.5, i["w"] * i["h"] / 3e6), nme, i))
        scored.sort(reverse=True)
        if scored and scored[0][0] > -0.5:
            return scored[0][1], scored[0][2], q, subs
    return None, None, None, subs


def main():
    state = json.load(io.open(STATE, encoding="utf-8")) if os.path.exists(STATE) else {"books": {}}
    idx = json.load(io.open(ec.MANIFEST, encoding="utf-8"))
    en = [b for b in idx if b.get("lang") == "en"]
    used = {v["file"] for v in state["books"].values() if v and v.get("file")}
    todo = [b for b in en if re.match(r"^img/pg\d+\.jpg$", b.get("cover") or "") and b["slug"] not in state["books"]]
    print("%d book(s) on a plain cover" % len(todo), flush=True)
    changes = {}
    for i, b in enumerate(todo, 1):
        nme, inf, q, subs = pick(b, used)
        path = ec.save_cover(nme, inf) if nme else None
        state["books"][b["slug"]] = {"file": nme, "path": path, "q": q} if path else None
        if path:
            used.add(nme); changes[b["slug"]] = path
        print("[%d/%d] %-44s %s" % (i, len(todo), (b.get("title") or "")[:44],
              ("✓ %s  ← %s" % (nme[:46], q)) if path else "— nothing suitable"), flush=True)
        if i % 10 == 0 or i == len(todo):
            ec.set_covers(changes); changes = {}
            io.open(STATE, "w", encoding="utf-8").write(json.dumps(state, ensure_ascii=False))
    ec.set_covers(changes)
    io.open(STATE, "w", encoding="utf-8").write(json.dumps(state, ensure_ascii=False))

    # Authors with no portrait: their best-known book's picture.
    idx = json.load(io.open(ec.MANIFEST, encoding="utf-8"))
    en = [b for b in idx if b.get("lang") == "en"]
    out_p = "src/authors-en.json"
    out = json.load(io.open(out_p, encoding="utf-8")) if os.path.exists(out_p) else {}
    src = io.open("src/authors.js", encoding="utf-8").read()
    have = set(re.findall(r'^\s+"([^"]+)":\s*\{', src, re.M)) | set(out)
    ru_en = {re.sub(r"\s*\(.*\)", "", b.get("enAuthor") or "").strip() for b in idx if b.get("lang") != "en"}
    books_of = {}
    for b in en:                                  # catalogue order = Gutenberg popularity
        a = (b.get("author") or "").strip()
        if a:
            books_of.setdefault(a, []).append(b)
    n = 0
    for a, bs in books_of.items():
        if a in have or a in ru_en:
            continue
        best = next((b for b in bs if re.match(r"^img/(cv-|wk-)", b.get("cover") or "")), None) or bs[0]
        if not best.get("cover"):
            continue
        out[a] = {"name": a, "years": best.get("authorYears") or "", "file": "/books/" + best["cover"],
                  "fromBook": best.get("title") or ""}
        n += 1
        print("author  %-34s ← %s (%s)" % (a[:34], (best.get("title") or "")[:40], best["cover"][4:7]))
    io.open(out_p, "w", encoding="utf-8").write(json.dumps(out, ensure_ascii=False, indent=1))
    done = sum(1 for v in state["books"].values() if v)
    print("\nDone: %d book(s) given a painting; %d author(s) pictured by their book." % (done, n))


if __name__ == "__main__":
    main()
