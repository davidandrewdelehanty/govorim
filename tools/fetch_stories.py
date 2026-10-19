#!/usr/bin/env python3
"""Public-domain stories that are not yet in the library, from Russian
Wikisource (ru.wikisource.org), as plain paragraphs in private/stories/<slug>.txt
for the Classic Stories course (tools/courses/story_drills.py reads them).
Texts in the old orthography are skipped.

    cd /mnt/c/Users/david/projects/govorim-app
    python3 tools/fetch_stories.py
"""
import html, io, json, os, re, time, urllib.parse, urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "private", "stories")
API = "https://ru.wikisource.org/w/api.php"
UA = "SamovarCourses/1.0 (https://samovar.live) python-urllib"
WANT = [("sostyazanie", "Вересаев Состязание"), ("zhemchuzhnoe-ozherelie", "Лесков Жемчужное ожерелье"),
        ("pismo-bratu-nikolayu", "Чехов письмо Н. П. Чехову 1886 воспитанные люди")]


def get(params):
    url = API + "?" + urllib.parse.urlencode(dict(params, format="json"))
    for i in range(4):
        try:
            return json.loads(urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": UA}), timeout=30).read())
        except Exception:
            time.sleep(4 * (i + 1))
    return {}


def main():
    os.makedirs(OUT, exist_ok=True)
    for slug, q in WANT:
        hits = (get({"action": "query", "list": "search", "srsearch": q, "srlimit": 5}).get("query") or {}).get("search") or []
        done = False
        for h in hits:
            j = get({"action": "parse", "page": h["title"], "prop": "text"})
            t = ((j.get("parse") or {}).get("text") or {}).get("*", "")
            paras = [html.unescape(re.sub(r"<[^>]+>", "", p)).strip() for p in re.findall(r"<p>(.*?)</p>", t, re.S)]
            paras = [p for p in paras if len(p) > 40]
            if len(paras) < 5 or re.search(r"[ѣіѳ]", " ".join(paras)):
                continue
            io.open(os.path.join(OUT, slug + ".txt"), "w", encoding="utf-8").write(h["title"] + "\n" + "\n".join(paras))
            print("✓", slug, "←", h["title"], len(paras), "paragraphs"); done = True
            break
        if not done:
            print("—", slug, "not found in the modern spelling")


if __name__ == "__main__":
    main()
