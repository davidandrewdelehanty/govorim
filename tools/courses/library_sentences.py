#!/usr/bin/env python3
"""Short sentences from the library's own Russian books, for drills: native
Russian from writers whose work is in the public domain (died 1955 or
earlier), so nothing invented and nothing borrowed under licence.

    cd /mnt/c/Users/david/projects/govorim-app
    python3 tools/courses/library_sentences.py            # → tools/courses/library_sentences.tsv
    python3 tools/courses/tatoeba_drills.py ~/tatoeba/rus.txt
"""
import io, json, os, re, sys, html

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
# optional: first and last book to read (for running it in pieces); pieces append
START = int(sys.argv[1]) if len(sys.argv) > 1 else 0
END = int(sys.argv[2]) if len(sys.argv) > 2 else 0
SKIP_CATS = {"Translations", "Song Lyrics", "Speeches by Soviet Leaders", "Religious Texts", "Theatrical Performances"}

src = io.open(os.path.join(ROOT, "src", "authors.js"), encoding="utf-8").read()
DIED, NAME = {}, {}
for k, nm, y in re.findall(r'^\s+"([^"]+)":\s*\{"name":\s*"([^"]+)",\s*"years":\s*"[^"]*?(\d{4})"', src, re.M):
    DIED[k] = int(y); NAME[k] = nm

P = re.compile(r"<p[^>]*>(.*?)</p>", re.S)
TAG = re.compile(r"<[^>]+>")
SENT = re.compile(r"(?<=[.!?…])\s+(?=[—–-]?\s*[А-ЯЁ«])")
OLD = re.compile(r"[ѣіѳѵ]|ъ(?=[\s.,!?;:»)])", re.I)


def main():
    idx = json.load(io.open(os.path.join(ROOT, "private", "books", "index.json"), encoding="utf-8"))
    books = [b for b in idx if b.get("lang") != "en" and b.get("category") not in SKIP_CATS
             and (b.get("filename") or "").endswith(".fb2") and DIED.get((b.get("author") or "").strip(), 9999) <= 1955]
    total = len(books)
    books = books[START:END or None]
    out = io.open(os.path.join(HERE, "library_sentences.tsv"), "a" if START else "w", encoding="utf-8")
    n = 0
    seen = set()
    print("%d public-domain books; reading %d–%d" % (total, START, START + len(books)), flush=True)
    for bi, b in enumerate(books):
        path = os.path.join(ROOT, "public", "books", b["filename"])
        try:
            raw = io.open(path, encoding="utf-8", errors="replace").read()
        except Exception:
            continue
        body = raw.split("<body", 1)[-1]
        a = (b.get("author") or "").strip()
        cite = "%s, «%s»" % (NAME.get(a, a), b.get("title") or "")
        for para in P.findall(body):
            t = html.unescape(TAG.sub("", para)).replace("\xa0", " ").strip()
            if not t or OLD.search(t):
                continue
            for s in SENT.split(t):
                s = re.sub(r"^[—–-]\s*", "", s.strip())
                s = re.sub(r"\s*[—–]\s*(сказал|сказала|ответил|ответила|подумал|спросил|спросила|закричал)\b.*$", ".", s)
                if not (12 <= len(s) <= 110) or not s[0].isupper() or s[-1] not in ".!?" or s in seen:
                    continue
                if re.search(r"[A-Za-z\d\[\]{}*_/<>]", s) or s.count("—") > 1 or s.count("«") != s.count("»"):
                    continue
                seen.add(s)
                out.write(s + "\t\t" + cite + "\n"); n += 1
        if (bi + 1) % 100 == 0:
            print("%d/%d books, %d sentences" % (bi + 1, len(books), n), flush=True)
    print("%d books, %d sentences → tools/courses/library_sentences.tsv" % (len(books), n))


if __name__ == "__main__":
    main()
