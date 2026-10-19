#!/usr/bin/env python3
"""Aspect and aspectual partner for the Grammar tab's verbs, from English
Wiktionary's Russian verb headers:
    {{ru-verb|говори́ть|impf|pf=сказа́ть|pf2=поговори́ть}}
Fetched 50 pages at a time for the 1,500 commonest verbs in
public/vocab/verbs/index.json and every verb in src/verbs-irregular.json, and
written into that index as "pairs": { verb: ["impf"|"pf"|"both", [partners]] }.
Run after tools/verb_stats.py (which rewrites the index).

    cd /mnt/c/Users/david/projects/govorim-app
    python3 tools/verb_pairs.py
"""
import io, json, os, re, time, urllib.parse, urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.chdir(ROOT)
IDX = "public/vocab/verbs/index.json"
API = "https://en.wiktionary.org/w/api.php"
UA = "SamovarVerbPairs/1.0 (https://samovar.live) python-urllib"


def get(params, tries=5):
    url = API + "?" + urllib.parse.urlencode(dict(params, format="json", formatversion=2))
    for i in range(tries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": UA})
            return json.loads(urllib.request.urlopen(req, timeout=60).read().decode("utf-8"))
        except Exception:
            time.sleep(4 * (i + 1))
    return {}


def russian_section(text):
    m = re.search(r"(?ms)^==\s*Russian\s*==\s*$(.*?)(?=^==[^=]|\Z)", text)
    return m.group(1) if m else ""


def parse(text):
    """First {{ru-verb}} header in the Russian section → (aspect, partners)."""
    sec = russian_section(text)
    m = re.search(r"\{\{ru-verb\|([^{}]*)\}\}", sec)
    if not m:
        return None
    parts = m.group(1).split("|")
    pos = [p for p in parts if "=" not in p]
    named = dict(p.split("=", 1) for p in parts if "=" in p)
    asp = ""
    for p in pos[1:] + [named.get("a", "")]:
        p = p.strip()
        if p in ("impf", "pf", "both", "biasp", "impf-pf", "pf-impf"):
            asp = {"biasp": "both", "impf-pf": "both", "pf-impf": "both"}.get(p, p)
            break
    partners = []
    for k in sorted(named, key=lambda k: (re.sub(r"\d", "", k), int(re.sub(r"\D", "", k) or 1))):
        if re.match(r"^(pf|impf)\d*$", k):
            v = named[k].replace("́", "").strip()
            if v and v not in partners and v != "-":
                partners.append(v)
    return (asp, partners) if asp or partners else None


def main():
    idx = json.load(io.open(IDX, encoding="utf-8"))
    verbs = [v for v, n in idx["top"][:1500]]
    try:
        for g in json.load(io.open("src/verbs-irregular.json", encoding="utf-8"))["groups"]:
            verbs += [v[0] for v in g["verbs"]]
    except Exception:
        pass
    verbs = list(dict.fromkeys(verbs))
    pairs = {}
    for i in range(0, len(verbs), 50):
        batch = verbs[i:i + 50]
        j = get({"action": "query", "prop": "revisions", "rvprop": "content", "rvslots": "main",
                 "titles": "|".join(batch), "redirects": 1})
        for p in (j.get("query") or {}).get("pages", []):
            revs = p.get("revisions") or []
            if not revs:
                continue
            r = parse(revs[0]["slots"]["main"]["content"])
            if r:
                pairs[p["title"]] = [r[0], r[1]]
        print("  %d/%d · %d with a pair" % (min(i + 50, len(verbs)), len(verbs), len(pairs)), flush=True)
        time.sleep(1.0)
    idx = json.load(io.open(IDX, encoding="utf-8"))   # re-read: never clobber a newer index
    idx["pairs"] = pairs
    io.open(IDX, "w", encoding="utf-8").write(json.dumps(idx, ensure_ascii=False, separators=(",", ":")))
    print("\nDone: %d of %d verbs have an aspect; %d have a partner." % (
        len(pairs), len(verbs), sum(1 for v in pairs.values() if v[1])))
    for v in verbs[:12]:
        print("  ", v, pairs.get(v))


if __name__ == "__main__":
    main()
