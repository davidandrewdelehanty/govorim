#!/usr/bin/env python3
"""Save the Russian entries of the English Wiktionary (CC BY-SA 4.0) for the
function words the grammar courses explain — conjunctions, particles,
pronouns — into private/wiktionary/<word>.txt. The courses quote their
definitions and examples word for word, with credit.

    cd /mnt/c/Users/david/projects/govorim-app
    python3 tools/fetch_wiktionary.py
    python3 tools/courses/build_courses.py
"""
import io, json, os, re, time, urllib.parse, urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "private", "wiktionary")
UA = "SamovarCourses/1.0 (https://samovar.live; course explanations, credited) python-urllib"
WORDS = ["каков", "каково", "сам", "самый", "хотя", "несмотря на", "несмотря на то что", "поскольку", "так как", "потому что",
         "поэтому", "из-за", "благодаря", "зато", "а то", "да", "либо", "или", "то ... то", "не то", "же", "ведь", "разве",
         "неужели", "даже", "тоже", "также", "давай", "пусть", "прежде чем", "с тех пор как", "как только", "так что",
         "настолько", "столько", "такой", "там", "если", "раз", "многие", "некоторый", "несколько", "много", "где", "куда",
         "откуда", "тот же", "такой же", "один и тот же", "вроде", "будто", "словно", "как будто", "пока не", "чтобы"]


def get(title):
    url = "https://en.wiktionary.org/w/index.php?" + urllib.parse.urlencode({"title": title, "action": "raw"})
    for i in range(5):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": UA})
            return urllib.request.urlopen(req, timeout=30).read().decode("utf-8")
        except urllib.error.HTTPError as e:
            if e.code == 404:
                return None
            time.sleep(5 * (i + 1))
        except Exception:
            time.sleep(5 * (i + 1))
    return None


def russian_section(text):
    m = re.search(r"^==Russian==\s*$(.*?)(?=^==[^=].*==\s*$|\Z)", text, re.M | re.S)
    return m.group(1) if m else ""


def main():
    os.makedirs(OUT, exist_ok=True)
    for w in WORDS:
        path = os.path.join(OUT, w + ".txt")
        if os.path.exists(path):
            continue
        t = get(w)
        sec = russian_section(t or "")
        if sec:
            io.open(path, "w", encoding="utf-8").write(sec)
        print(("✓ " if sec else "— ") + w, flush=True)
        time.sleep(1)


if __name__ == "__main__":
    main()
