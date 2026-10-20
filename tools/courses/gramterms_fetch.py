#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""The raw material for the Grammar Terms course: real Russian text that
uses the terms. Nothing here is written by a program.

  1. The Russian Wikipedia's article on each term (CC BY-SA 4.0 — the same
     licence as the OpenCorpora dictionary the site already uses), as plain
     text through the MediaWiki API, with the article's revision id so the
     course can say exactly which text it quotes.
  2. Sentences from the library's public-domain books that use a term
     (tools/courses/library_sentences.tsv, with author and title) — only the
     terms that mean nothing else («существительное», «именительный падеж»),
     never «время» or «лицо», which in a novel are time and a face.

Run where Wikipedia is reachable (WSL):
    cd /mnt/c/Users/david/projects/govorim-app
    python3 tools/courses/gramterms_fetch.py          → tools/courses/gramterms_src.json

The terms themselves, their English and the article each comes from are in
gramterms_course.py (TERMS); this script only fetches.
"""
import io, json, os, re, sys, time, urllib.parse, urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from gramterms_course import TERMS, GROUPS, SAFE_IN_PROSE

HOST = "ru.wikipedia.org"
UA = "govorim-app/1.0 (grammar-terms course; contact via github)"


def api(**params):
    params.setdefault("format", "json")
    params.setdefault("formatversion", "2")
    url = "https://%s/w/api.php?%s" % (HOST, urllib.parse.urlencode(params))
    wait = 4
    for attempt in range(6):
        req = urllib.request.Request(url, headers={"User-Agent": UA})
        try:
            with urllib.request.urlopen(req, timeout=120) as r:
                return json.loads(r.read().decode("utf-8"))
        except urllib.error.HTTPError as e:
            if e.code not in (429, 500, 502, 503, 504) or attempt == 5:
                raise
            ra = e.headers.get("Retry-After") if e.headers else None
            pause = int(ra) if (ra or "").isdigit() else wait
            print("   … %s, waiting %ds" % (e.code, pause), flush=True)
            time.sleep(pause)
            wait = min(wait * 2, 120)
        except urllib.error.URLError:
            if attempt == 5:
                raise
            time.sleep(wait)
            wait = min(wait * 2, 120)


def article(titles):
    """The first of `titles` that exists: (title, revision id, plain text), or None."""
    for t in titles:
        j = api(action="query", prop="extracts|revisions", explaintext="1", exsectionformat="plain",
                exlimit="1", rvprop="ids", redirects="1", titles=t)
        pages = (j.get("query") or {}).get("pages") or []
        if not pages or pages[0].get("missing"):
            continue
        p = pages[0]
        text = p.get("extract") or ""
        if len(text) < 300:
            continue
        rev = ((p.get("revisions") or [{}])[0]).get("revid")
        return p.get("title"), rev, text
    return None


# Where a term's name has several spellings in the text (ё/е), the lemma
# comparison in the course builder takes care of it; here the library is
# searched for the plain words.
def library_sentences(terms):
    """`terms`: {canonical term: [spellings to look for]}. A sentence is kept
    once, for the first term found in it."""
    import pymorphy3
    M = pymorphy3.MorphAnalyzer()
    lib = os.path.join(HERE, "library_sentences.tsv")
    if not os.path.exists(lib):
        print("no library_sentences.tsv — library sentences skipped")
        return []
    want = {}        # first word's lemma → [(term words lemmas, canonical term)]
    keys = set()     # a cheap test before any parsing: the start of the term's longest word
    for canon, spellings in terms.items():
        for t in spellings:
            words = t.split()
            lem = [M.parse(w)[0].normal_form.replace("ё", "е") for w in words]
            want.setdefault(lem[0], []).append((lem, canon))
            k = max(words, key=len).lower()[:6]
            keys.add(k); keys.add(k.replace("ё", "е"))
    W = re.compile(r"[А-Яа-яЁё]+(?:-[А-Яа-яЁё]+)?")
    out, seen = [], set()
    cache = {}

    def lemma(w):
        w = w.lower()
        if w not in cache:
            cache[w] = {p.normal_form.replace("ё", "е") for p in M.parse(w) if p.score > 0.05}
        return cache[w]

    n = 0
    for line in io.open(lib, encoding="utf-8"):
        c = line.rstrip("\n").split("\t")
        if len(c) < 3:
            continue
        ru, cite = c[0], c[2]
        if ru in seen or not (30 <= len(ru) <= 170):
            continue
        low = ru.lower()
        if not any(k in low for k in keys):
            continue
        ws = list(W.finditer(ru))
        lows = [w.group() for w in ws]
        for i, w in enumerate(lows):
            for first, cands in want.items():
                if first not in lemma(w):
                    continue
                for lem, term in cands:
                    if i + len(lem) > len(lows):
                        continue
                    if all(lem[k] in lemma(lows[i + k]) for k in range(len(lem))):
                        s, e = ws[i].span()[0], ws[i + len(lem) - 1].span()[1]
                        if s and ru[s - 1] in "-‑":
                            continue
                        seen.add(ru)
                        out.append({"ru": ru, "s": s, "e": e, "term": term, "src": cite})
                        n += 1
                        break
                else:
                    continue
                break
    print("%d library sentences" % n)
    return out


def main():
    src = {"host": HOST, "licence": "CC BY-SA 4.0",
           "licence_url": "https://creativecommons.org/licenses/by-sa/4.0/", "articles": {}, "library": []}
    want = {}
    for g in GROUPS:
        for t in g["terms"]:
            want.setdefault(TERMS[t]["articles"][0], TERMS[t]["articles"])
    for key, titles in want.items():
        got = article(titles)
        if not got:
            print("   · not found: %s" % " / ".join(titles), flush=True)
            continue
        title, rev, text = got
        src["articles"][key] = {"title": title, "revid": rev, "text": text,
                                "url": "https://%s/wiki/%s" % (HOST, urllib.parse.quote(title.replace(" ", "_"), safe="()_,"))}
        print("%-40s %7d chars  rev %s" % (title, len(text), rev), flush=True)
        time.sleep(0.5)
    # in a novel only the spellings that can mean nothing else: «совершенный»
    # alone is "perfect", not the aspect
    src["library"] = library_sentences({t: [t] + [a for a in (TERMS[t].get("also") or []) if a in SAFE_IN_PROSE]
                                        for t in TERMS if t in SAFE_IN_PROSE})
    dst = os.path.join(HERE, "gramterms_src.json")
    io.open(dst, "w", encoding="utf-8").write(json.dumps(src, ensure_ascii=False, separators=(",", ":")))
    print("→ %s: %d articles, %d library sentences" % (dst, len(src["articles"]), len(src["library"])))


if __name__ == "__main__":
    main()
