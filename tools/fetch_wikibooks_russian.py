#!/usr/bin/env python3
"""Download the Wikibooks Russian textbook (en.wikibooks.org/wiki/Russian and
every page under it) as wikitext, for adapting into the Grammar tab.

Wikibooks text is CC BY-SA 4.0: whatever the site adapts from it is credited
to Wikibooks and carries the same licence. The pages' authors are kept in
_meta.json (from each page's history) so the credit can name the source.

    cd /mnt/c/Users/david/projects/govorim-app
    python3 tools/fetch_wikibooks_russian.py
Writes private/wikibooks-russian/<page>.wiki and _meta.json.
"""
import json, os, re, time, urllib.parse, urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "private", "wikibooks-russian")
API = "https://en.wikibooks.org/w/api.php"
UA = "SamovarGrammar/1.0 (https://samovar.live; adapting the CC BY-SA Russian textbook) python-urllib"


def get(params, tries=5):
    params = dict(params, format="json", formatversion=2)
    url = API + "?" + urllib.parse.urlencode(params)
    for i in range(tries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": UA})
            return json.loads(urllib.request.urlopen(req, timeout=60).read().decode("utf-8"))
        except Exception as e:
            time.sleep(3 * (i + 1))
    return {}


def main():
    os.makedirs(OUT, exist_ok=True)
    titles, cont = ["Russian"], {}
    while True:
        j = get(dict({"action": "query", "list": "allpages", "apprefix": "Russian/", "apnamespace": 0, "aplimit": 500}, **cont))
        titles += [p["title"] for p in j.get("query", {}).get("allpages", [])]
        if "continue" not in j:
            break
        cont = j["continue"]
    print("%d pages" % len(titles), flush=True)
    meta = {}
    for i in range(0, len(titles), 40):
        batch = titles[i:i + 40]
        j = get({"action": "query", "prop": "revisions|info", "rvprop": "content|timestamp", "rvslots": "main",
                 "titles": "|".join(batch)})
        for p in j.get("query", {}).get("pages", []):
            revs = p.get("revisions") or []
            if not revs:
                continue
            text = revs[0]["slots"]["main"]["content"]
            if re.match(r"#REDIRECT", text, re.I):
                continue
            name = re.sub(r"[^\w\-]+", "_", p["title"]).strip("_")
            open(os.path.join(OUT, name + ".wiki"), "w", encoding="utf-8").write(text)
            meta[p["title"]] = {"file": name + ".wiki", "rev": revs[0]["timestamp"], "bytes": len(text.encode("utf-8")),
                                "url": "https://en.wikibooks.org/wiki/" + urllib.parse.quote(p["title"].replace(" ", "_"))}
        print("  %d/%d" % (min(i + 40, len(titles)), len(titles)), flush=True)
        time.sleep(0.5)
    # Who wrote it, for the credit line.
    for t in list(meta)[:400]:
        j = get({"action": "query", "prop": "contributors", "titles": t, "pclimit": 50})
        pg = (j.get("query", {}).get("pages") or [{}])[0]
        meta[t]["contributors"] = [c["name"] for c in pg.get("contributors", [])]
        time.sleep(0.2)
    json.dump(meta, open(os.path.join(OUT, "_meta.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print("\nSaved %d pages (%.0f KB) to private/wikibooks-russian/" % (len(meta), sum(m["bytes"] for m in meta.values()) / 1e3))


if __name__ == "__main__":
    main()
