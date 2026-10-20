#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Fill the "Modern Russian" shelf with present-day Russian that anyone may
republish.

Four sources, each free for a stated legal reason:

  wikinews    Russian Wikinews — real news articles, written as news, under a
              Creative Commons Attribution licence. Grouped one book per month,
              one chapter per article.
  wikipedia   Russian Wikipedia articles (CC BY-SA) named in
              tools/modern/wikipedia.txt — the Russian rock bands to start with.
  wikivoyage  Russian Wikivoyage city guides (CC BY-SA) named in
              tools/modern/wikivoyage.txt — transport, food, where to stay: the
              Russian of everyday life.
  official    Official documents of the Russian state from Russian Wikisource
              (the Constitution, laws, codes, presidential addresses), named in
              tools/modern/official.txt. Under ГК РФ ст. 1259 п. 6 official
              documents of state bodies are not objects of copyright at all.
              These go through tools/add_wikisource.py, which already turns
              Wikisource pages into the library's FB2s.

Nothing here writes Russian text. Every word on the shelf is the source's own;
the only lines added are the attribution each licence requires, made from the
page's own title, address and the licence the site itself reports.

    python3 tools/modern_russian.py --all
    python3 tools/modern_russian.py --wikinews --months 24
    python3 tools/modern_russian.py --wikipedia --wikivoyage --dry-run

NOTE ON WHERE THIS RUNS: it needs ru.wikipedia.org, ru.wikinews.org,
ru.wikivoyage.org and ru.wikisource.org, so run it in WSL on your machine —
the Cowork sandboxes cannot reach them.
"""
import argparse
import datetime
import io
import json
import os
import re
import subprocess
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from xml.etree import ElementTree as ET

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import add_wikisource as W          # the tested HTML -> blocks -> FB2 code

CATEGORY = "Modern Russian"
UA = "govorim-app/1.0 (Modern Russian shelf import)"
LISTS = os.path.join(HERE, "modern")

# The Wikimedia pages carry furniture that is not reading text. Tables go
# too: on these sites they are infoboxes, discographies and line-ups, never
# prose (add_wikisource keeps tables, because Wikisource lays poems out in
# them — which is why these are added here, in this process only).
W.DROP_CLASSES |= {"infobox", "thumb", "tright", "tleft", "gallery", "toc", "hatnote",
                   "dablink", "navbox", "vertical-navbox", "sistersitebox", "reflist",
                   "mw-references-wrap", "mw-kartographer-maplink", "mw-kartographer-map",
                   "noviewer", "shortdescription", "ts-Родственный_проект", "plainlist",
                   "wikinews-share", "infobox-wrapper", "sister-project", "ambox",
                   "listing-metadata", "listing-lastedit", "pagebanner", "wv-banner"}
W.DROP_TAGS |= {"table"}

# Sections that are lists of references, links or names rather than prose.
STOP = re.compile(
    r"^(Примечания|Комментарии|Сноски|Литература|Ссылки|См\. также|Источники|"
    r"Дискография|Видеография|Фильмография|Библиография|Галерея|Состав|"
    r"Состав группы|Бывшие участники|Награды|Награды и номинации|Хронология|"
    r"Связь|Внешние ссылки|Дополнительная литература|Публикации|"
    r"Альбомы|Синглы|Концертные альбомы|Сборники|Видео)\b", re.I)


# ----------------------------------------------------------------- network --
def api(host, **params):
    params.setdefault("format", "json")
    params.setdefault("formatversion", "2")
    url = "https://%s/w/api.php?%s" % (host, urllib.parse.urlencode(params))
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
            print("   … %s from %s, waiting %ds" % (e.code, host, pause), flush=True)
            time.sleep(pause)
            wait = min(wait * 2, 120)
        except urllib.error.URLError as e:
            if attempt == 5:
                raise
            time.sleep(wait)
            wait = min(wait * 2, 120)


_RIGHTS = {}


def rights(host):
    """The licence the site itself states, e.g. ('Creative Commons
    Attribution-Share Alike 4.0', 'https://creativecommons.org/...')."""
    if host not in _RIGHTS:
        j = api(host, action="query", meta="siteinfo", siprop="rightsinfo")
        ri = (j.get("query") or {}).get("rightsinfo") or {}
        _RIGHTS[host] = (ri.get("text") or "", ri.get("url") or "")
    return _RIGHTS[host]


def page_html(host, title):
    j = api(host, action="parse", page=title, prop="text|displaytitle",
            redirects="1", disableeditsection="1", disabletoc="1")
    p = j.get("parse") or {}
    return p.get("title") or title, p.get("text") or ""


def page_url(host, title):
    """The page's address as a reader would type it — Cyrillic kept, not
    %-escaped, since it is printed in the book as the attribution. Only the
    characters that would break a link are escaped."""
    t = title.replace(" ", "_")
    for ch, esc in (("%", "%25"), ("?", "%3F"), ("#", "%23"), ('"', "%22")):
        t = t.replace(ch, esc)
    return "https://%s/wiki/%s" % (host, t)


# ------------------------------------------------------------------ text --
def blocks_of(html):
    try:
        doc = ET.fromstring("<div>" + W._strip_bad_xml(html) + "</div>")
    except ET.ParseError:
        doc = ET.fromstring("<div>" + W._strip_bad_xml(html, hard=True) + "</div>")
    out, skipping = [], False
    for kind, text in W._clean_chunks(W._blocks(doc)):
        if kind == "h":
            skipping = bool(STOP.match(text.strip()))
            if skipping:
                continue
        if not skipping:
            out.append((kind, text))
    # A heading with nothing under it (the section was all table) is dropped.
    tidy = []
    for i, (k, t) in enumerate(out):
        if k == "h" and (i + 1 == len(out) or out[i + 1][0] == "h"):
            continue
        tidy.append((k, t))
    return tidy


def lead(blocks, limit=420):
    """The page's own first paragraph, as the shelf blurb — never one written
    here."""
    for k, t in blocks:
        if k == "p" and len(W.RU_WORD.findall(t)) >= 12:
            if len(t) <= limit:
                return t
            cut = t[:limit]
            m = list(re.finditer(r"[.!?…](?=\s)", cut))
            return cut[:m[-1].end()] if m else cut.rsplit(" ", 1)[0] + "…"
    return ""


def attribution(site, title, url, host):
    text, lurl = rights(host)
    lic = text + (" (" + lurl + ")" if lurl else "")
    return ("p", "Источник: «%s» — %s, %s. Лицензия: %s." % (title, site, url, lic))


def slugify(s):
    tr = dict(zip("абвгдеёжзийклмнопрстуфхцчшщъыьэюя",
                  ["a", "b", "v", "g", "d", "e", "yo", "zh", "z", "i", "y", "k", "l", "m", "n", "o",
                   "p", "r", "s", "t", "u", "f", "kh", "ts", "ch", "sh", "shch", "", "y", "", "e",
                   "yu", "ya"]))
    s = "".join(tr.get(c, c) for c in s.lower())
    return re.sub(r"[^a-z0-9]+", "-", s).strip("-")[:60]


# ----------------------------------------------------------------- output --
def write_book(slug, title, author, chapters, source_url, blurb, blurb_src, note, a):
    words = W.count_words(chapters)
    if words < 120:
        print("   skipped %s — only %d words of prose" % (title, words))
        return False
    fn = "novel/modern-%s.fb2" % slug
    entry = {"filename": fn, "title": title, "author": author, "category": CATEGORY,
             "slug": "modern-" + slug, "words": words, "public": True, "_note": note}
    if blurb:
        entry.update({"blurb": blurb, "blurbSrc": blurb_src, "blurbLang": "ru"})
    if a.dry_run:
        print("   [dry run] %-50s %3d ch %6d words" % (title[:50], len(chapters), words))
        return True
    path = os.path.join(a.books_dir, os.path.basename(fn))
    io.open(path, "w", encoding="utf-8", newline="\n").write(
        W.build_fb2(title, author, chapters, source_url))
    W.upsert(a.manifest, entry, keep_existing=True)
    print("   %-50s %3d ch %6d words" % (title[:50], len(chapters), words), flush=True)
    return True


def read_list(name):
    p = os.path.join(LISTS, name)
    if not os.path.exists(p):
        return []
    out = []
    for line in io.open(p, encoding="utf-8"):
        line = line.split("#", 1)[0].strip()
        if line:
            out.append(line)
    return out


# ---------------------------------------------------- Wikipedia, Wikivoyage --
def import_articles(host, site, listfile, author, a):
    titles = read_list(listfile)
    print("\n== %s: %d articles from tools/modern/%s" % (site, len(titles), listfile), flush=True)
    done = 0
    have = set()
    if not a.refresh and os.path.exists(a.manifest):
        have = {b.get("slug") for b in json.load(io.open(a.manifest, encoding="utf-8"))}
    for t in titles:
        if "modern-" + slugify(host.split(".")[1] + "-" + t) in have:
            continue                                   # already on the shelf
        try:
            real, html = page_html(host, t)
        except Exception as e:
            print("   ! %s — %s" % (t, e))
            continue
        if not html:
            print("   ! %s — no such page" % t)
            continue
        bl = blocks_of(html)
        url = page_url(host, real)
        chapters = W.split_at_headings(real, bl) if bl else []
        if not chapters:
            continue
        chapters[-1]["blocks"].append(attribution(site, real, url, host))
        note = "%s, %s — %s" % (site, rights(host)[0], url)
        if write_book(slugify(host.split(".")[1] + "-" + real), real, author, chapters, url,
                      lead(bl), url, note, a):
            done += 1
        time.sleep(a.pause)
    return done


# --------------------------------------------------------------- Wikinews --
MONTHS = ["январь", "февраль", "март", "апрель", "май", "июнь", "июль", "август",
          "сентябрь", "октябрь", "ноябрь", "декабрь"]


def published_category(host):
    """The category every published article is in. Found, not assumed: the
    likely names are tried, then the category list is searched."""
    for name in ("Опубликовано", "Опубликованные новости", "Published"):
        j = api(host, action="query", list="categorymembers", cmtitle="Категория:" + name,
                cmtype="page", cmlimit="1")
        if (j.get("query") or {}).get("categorymembers"):
            return "Категория:" + name
    j = api(host, action="query", list="allcategories", acprefix="Опубликован", aclimit="20",
            acprop="size")
    cats = sorted(((c.get("size") or 0, c.get("category")) for c in
                   (j.get("query") or {}).get("allcategories") or []), reverse=True)
    if cats and cats[0][0]:
        return "Категория:" + cats[0][1]
    raise RuntimeError("could not find the category of published Wikinews articles")


def import_wikinews(a):
    host = "ru.wikinews.org"
    cat = published_category(host)
    print("\n== Викиновости: %s, the last %d months" % (cat, a.months), flush=True)
    today = datetime.date.today()
    first = (today.replace(day=1) - datetime.timedelta(days=31 * (a.months - 1))).replace(day=1)
    by_month = {}
    cont = {}
    while True:
        j = api(host, action="query", list="categorymembers", cmtitle=cat, cmtype="page",
                cmsort="timestamp", cmdir="desc", cmlimit="500", cmprop="title|timestamp",
                **cont)
        stop = False
        for m in (j.get("query") or {}).get("categorymembers") or []:
            d = datetime.date.fromisoformat(m["timestamp"][:10])
            if d < first:
                stop = True
                break
            by_month.setdefault((d.year, d.month), []).append((d, m["title"]))
        if stop or "continue" not in j:
            break
        cont = j["continue"]
    done = 0
    for (y, mo) in sorted(by_month):
        items = sorted(by_month[(y, mo)])
        chapters = []
        for d, t in items:
            try:
                real, html = page_html(host, t)
            except Exception as e:
                print("   ! %s — %s" % (t, e))
                continue
            bl = [b for b in blocks_of(html) if b[0] != "h"]
            if len(W.RU_WORD.findall(" ".join(x for _, x in bl))) < a.min_words:
                continue
            bl.append(attribution("Викиновости", real, page_url(host, real), host))
            chapters.append({"title": real, "blocks": bl})
            if len(chapters) >= a.per_month:
                break
            time.sleep(a.pause)
        if not chapters:
            continue
        title = "Викиновости: %s %d" % (MONTHS[mo - 1], y)
        note = "Викиновости, %s — %s" % (rights(host)[0], page_url(host, cat))
        if write_book("wikinews-%d-%02d" % (y, mo), title, "Викиновости", chapters,
                      "https://ru.wikinews.org/", "", "", note, a):
            done += 1
    return done


# ---------------------------------------------------- official documents --
def import_official(a):
    """Find each wanted document on Wikisource, then hand the pages to
    add_wikisource.py, which already makes good FB2s of Wikisource pages."""
    host = "ru.wikisource.org"
    wanted = read_list("official.txt")
    print("\n== Официальные документы: %d wanted, from Wikisource" % len(wanted), flush=True)
    rows = []
    for q in wanted:
        j = api(host, action="query", list="search", srsearch=q, srnamespace="0", srlimit="5")
        hits = [h["title"] for h in (j.get("query") or {}).get("search") or []]
        exact = [h for h in hits if h.lower().startswith(q.lower())]
        pick = (exact or hits or [None])[0]
        if not pick:
            print("   ! not on Wikisource: %s" % q)
            continue
        print("   %s  ->  %s" % (q, pick))
        rows.append([("modern-" + slugify(pick))[:70], pick, "Российская Федерация", pick, CATEGORY, ""])
        time.sleep(a.pause)
    if not rows or a.dry_run:
        return 0
    tsv = os.path.join(LISTS, "official.found.tsv")
    with io.open(tsv, "w", encoding="utf-8", newline="\n") as f:
        for r in rows:
            f.write("\t".join(r) + "\n")
    subprocess.check_call([sys.executable, os.path.join(HERE, "add_wikisource.py"),
                           "--list", tsv, "--category", CATEGORY])
    # add_wikisource writes entries without "public"; these are official
    # documents, outside copyright, so they belong on the public site too.
    man = json.load(io.open(a.manifest, encoding="utf-8"))
    slugs = {r[0] for r in rows}
    for b in man:
        if b.get("slug") in slugs:
            b["public"] = True
            b["category"] = CATEGORY
    io.open(a.manifest, "w", encoding="utf-8", newline="\n").write(
        json.dumps(man, ensure_ascii=False, indent=2) + "\n")
    return len(rows)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--all", action="store_true")
    ap.add_argument("--wikinews", action="store_true")
    ap.add_argument("--wikipedia", action="store_true")
    ap.add_argument("--wikivoyage", action="store_true")
    ap.add_argument("--official", action="store_true")
    ap.add_argument("--authors", action="store_true", help="Wikipedia articles on writers, tools/modern/authors.txt")
    ap.add_argument("--refresh", action="store_true", help="fetch articles already on the shelf again")
    ap.add_argument("--months", type=int, default=12, help="Wikinews: how many months back")
    ap.add_argument("--per-month", type=int, default=120, help="Wikinews: most articles in one month's book")
    ap.add_argument("--min-words", type=int, default=60, help="Wikinews: skip shorter items")
    ap.add_argument("--pause", type=float, default=0.5)
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--manifest", default=W.MANIFEST)
    ap.add_argument("--books-dir", default=W.BOOKS_DIR)
    a = ap.parse_args()
    if not (a.all or a.wikinews or a.wikipedia or a.wikivoyage or a.official or a.authors):
        ap.error("say which: --all, or any of --wikinews --wikipedia --wikivoyage --official")
    os.chdir(os.path.dirname(HERE))           # repo root, where the manifest paths start
    n = 0
    if a.all or a.wikipedia:
        n += import_articles("ru.wikipedia.org", "Википедия", "wikipedia.txt", "Википедия", a)
    if a.all or a.authors:
        n += import_articles("ru.wikipedia.org", "Википедия", "authors.txt", "Википедия", a)
    if a.all or a.wikivoyage:
        n += import_articles("ru.wikivoyage.org", "Викигид", "wikivoyage.txt", "Викигид", a)
    if a.all or a.wikinews:
        n += import_wikinews(a)
    if a.all or a.official:
        n += import_official(a)
    print("\n%d books on the Modern Russian shelf%s." % (n, " (dry run — nothing written)" if a.dry_run else ""))


if __name__ == "__main__":
    main()
