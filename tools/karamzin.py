#!/usr/bin/env python3
"""Karamzin, «История государства Российского», from Russian Wikisource.

Twelve volumes, each a book on the shelf with its chapters. The work is a
tree on Wikisource — main page > Том N > Глава M — two levels deeper than
add_wikisource.py's index mode walks, so this walks it, fetches every chapter
page through the API, and hands the HTML to add_wikisource.py (--html-json)
to become FB2s and catalogue entries. The volumes' «Примечания» (thousands of
source notes per volume) are left out.

    cd /mnt/c/Users/david/projects/govorim-app
    python3 tools/karamzin.py --probe      # print the structure, fetch nothing else
    python3 tools/karamzin.py              # fetch, build, catalogue

Needs the network (ru.wikisource.org), so it runs in WSL. Re-running is safe:
pages are cached in .ws-cache/karamzin/.
"""
import json, os, re, subprocess, sys, time, urllib.parse
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from add_wikisource import api_html, API, UA
import urllib.request

MAIN_CANDIDATES = ["История государства Российского (Карамзин)", "История государства Российского"]
CACHE = ".ws-cache/karamzin"
ROMAN = ["I", "II", "III", "IV", "V", "VI", "VII", "VIII", "IX", "X", "XI", "XII"]
SKIP = re.compile(r"(Примечани|Оглавление|Содержание|/ДО$|/ВТ$|Версия)", re.I)


def cached_html(title):
    os.makedirs(CACHE, exist_ok=True)
    p = os.path.join(CACHE, re.sub(r'[\\/:*?"<>| ]', "_", title) + ".html")
    if os.path.exists(p) and os.path.getsize(p) > 200:
        return open(p, encoding="utf-8").read()
    h = api_html(title)
    open(p, "w", encoding="utf-8").write(h)
    time.sleep(0.4)
    return h


def links(html, prefix):
    out, seen = [], set()
    for href in re.findall(r'href="([^"]+)"', html):
        m = re.search(r"/wiki/([^\"#?]+)", href)
        if not m:
            continue
        t = urllib.parse.unquote(m.group(1)).replace("_", " ")
        if t.startswith(prefix + "/") and t not in seen:
            seen.add(t); out.append(t)
    return out


def allpages(prefix):
    out, cont = [], None
    while True:
        q = {"action": "query", "list": "allpages", "apprefix": prefix + "/", "apnamespace": 0,
             "aplimit": "500", "format": "json", "formatversion": "2"}
        if cont: q["apcontinue"] = cont
        req = urllib.request.Request(API + "?" + urllib.parse.urlencode(q), headers={"User-Agent": UA})
        j = json.loads(urllib.request.urlopen(req, timeout=60).read().decode("utf-8"))
        out += [p["title"] for p in j["query"]["allpages"]]
        cont = (j.get("continue") or {}).get("apcontinue")
        if not cont: return out


def main():
    probe = "--probe" in sys.argv
    main_title, main_html = None, ""
    for t in MAIN_CANDIDATES:
        h = cached_html(t)
        if h:
            main_title, main_html = t, h; break
    if not main_title:
        sys.exit("Could not find the work's main page on Wikisource.")
    every = allpages(main_title)
    print("main page: %s   (%d subpages on Wikisource)" % (main_title, len(every)))
    vols = []
    for n, r in enumerate(ROMAN, 1):
        cand = [t for t in every if re.fullmatch(re.escape(main_title) + r"/Том " + r + r"(/ВТ)?", t)]
        if not cand:
            # Some volumes have chapter pages but no volume page (VI, X).
            vol = main_title + "/Том " + r
            subs = [t for t in every if t.startswith(vol + "/") and not SKIP.search(t[len(vol):])]
            if len(subs) < 2:
                print("  Том %-4s only %d chapter page(s) on Wikisource — left out" % (r, len(subs))); continue
            def rn(t):
                m = re.search(r"Глава ([IVXL]+)$", t)
                if not m: return 999
                v, tot = {"I": 1, "V": 5, "X": 10, "L": 50}, 0
                q = m.group(1)
                for i, ch in enumerate(q):
                    tot += -v[ch] if i + 1 < len(q) and v[q[i + 1]] > v[ch] else v[ch]
                return tot
            chs = sorted(subs, key=rn)
            vols.append((n, r, vol, chs))
            print("  Том %-4s (no volume page)  %3d chapters   %s … %s" % (r, len(chs),
                  chs[0][len(vol) + 1:], chs[-1][len(vol) + 1:]))
            continue
        vt = [c for c in cand if c.endswith("/ВТ")]
        vol = (vt or cand)[0]
        vh = cached_html(vol)
        chs = [t for t in links(vh, vol) if not SKIP.search(t[len(vol):])]
        if not chs:
            # no links on the volume page: take its subpages, in Wikisource order
            chs = [t for t in every if t.startswith(vol + "/") and not SKIP.search(t[len(vol):])]
        vols.append((n, r, vol, chs))
        print("  Том %-4s %-60s %3d chapters   %s … %s" % (r, vol[-40:], len(chs),
              chs[0][len(vol) + 1:][:30] if chs else "-", chs[-1][len(vol) + 1:][:30] if chs else "-"))
    if probe:
        found = [v for _, _, v, _ in vols]
        rest = [t for t in every if not any(t == v or t.startswith(v + "/") for v in found)]
        print("\nsubpages not under any volume above (%d):" % len(rest))
        for t in rest: print("   " + t[len(main_title):])
        print("\n--probe: nothing fetched beyond the volume pages."); return
    data, rows = {}, []
    for n, r, vol, chs in vols:
        slug = "karamzin-igr-%02d" % n
        pages = []
        for i, c in enumerate(chs, 1):
            h = cached_html(c)
            if h: pages.append({"page": c, "html": h})
            print("\r  Том %s: %d/%d" % (r, i, len(chs)), end="", flush=True)
        print()
        data[slug] = pages
        rows.append("\t".join([slug, vol, "Карамзин Н.М.", "История государства Российского. Том " + r, "History",
                               ""]))
    json.dump(data, open(os.path.join(CACHE, "pages.json"), "w", encoding="utf-8"), ensure_ascii=False)
    open(os.path.join(CACHE, "list.tsv"), "w", encoding="utf-8").write("\n".join(rows) + "\n")
    rc = subprocess.call([sys.executable, "tools/add_wikisource.py", "--list", os.path.join(CACHE, "list.tsv"),
                          "--html-json", os.path.join(CACHE, "pages.json"), "--allow-duplicate"])
    sys.exit(rc)


if __name__ == "__main__":
    main()
