#!/usr/bin/env python3
"""Put a Wikisource text on the shelf: fetch it, make it an FB2, catalogue it.

Every book in the library is an FB2, because that is what the reader parses.
Russian Wikisource is the one source that settles the copyright question by
existing — it hosts only what is public domain in Russia — but its export
service dropped FB2 support and now speaks EPUB. So this does the last step
itself: EPUB in, FB2 out, with the chapter structure kept rather than
flattened, because chapters are what the reader, the video map and the
reading record are all keyed to.

    python3 tools/add_wikisource.py --list tools/top100/wanted.tsv
    python3 tools/add_wikisource.py "Обломов (Гончаров)" --slug oblomov \
        --author "Иван Гончаров" --title "Обломов"

    # already downloaded them by hand, or the network is elsewhere:
    python3 tools/add_wikisource.py --list ... --epub-dir ~/Downloads

Re-running is safe. An entry that is already in the catalogue is updated in
place, never duplicated, and --keep-existing leaves its hand-edited fields
(blurb, category, videos) alone.

NOTE ON WHERE THIS RUNS: it needs to reach ru.wikisource.org and
ws-export.wmcloud.org, so it runs on your machine, not in a sandbox whose
egress is filtered. That is also why --epub-dir exists.
"""
import argparse
import csv
import html
import io
import json
import os
import re
import sys
import unicodedata
import urllib.parse
import urllib.request
import zipfile
from xml.etree import ElementTree as ET

EXPORT = "https://ws-export.wmcloud.org/?format=epub-3&lang=ru&page="
API = "https://ru.wikisource.org/w/api.php"
UA = "govorim-app/1.0 (library import; contact via github)"
MANIFEST = "private/books/index.json"
BOOKS_DIR = "public/books/novel"
RU_WORD = re.compile(r"[А-Яа-яЁё][А-Яа-яЁё-]*")

# Wikisource wraps every page in an edition header and a licence footer, and
# marks footnote anchors, edit links and page-scan links with classes that
# never belong in the reading text.
DROP_IDS = {"headertemplate", "footertemplate", "sub_nav", "disambigbox"}
DROP_CLASSES = {
    "ws-noexport", "noprint", "mw-editsection", "reference", "references",
    "printfooter", "catlinks", "navbox", "metadata", "ambox", "mw-empty-elt",
    "pagenum", "ws-pagenum", "mw-cite-backlink", "licence", "header_notes",
}
# Verse pages number every fifth line in the margin. The number is a reading
# aid on the web and a typo in a book — "5Был монастырь" — so it goes.
DROP_CLASS_RE = re.compile(r"^(linenum|lineno|ws-lineno)")
# Tables are NOT dropped: Wikisource lays several poems out in a table so the
# verse sits beside an illustration, and dropping the table drops the poem.
# Navigation and metadata tables carry classes that DROP_CLASSES already
# catches.
DROP_TAGS = {"style", "script", "sup", "figure", "figcaption", "img",
             "audio", "video"}
XH = "{http://www.w3.org/1999/xhtml}"
OPF = "{http://www.idpf.org/2007/opf}"
DC = "{http://purl.org/dc/elements/1.1/}"
NCX = "{http://www.daisy.org/z3986/2005/ncx/}"


# ----------------------------------------------------------------- fetching --
def fetch_epub(page, cache_dir=None):
    """The EPUB for one Wikisource page. Cached, because a big work takes the
    export service the better part of a minute to build and there is no reason
    to ask twice."""
    # A page title can contain "/" (an edition subpage); the cache is flat.
    name = page.replace(" ", "_").replace("/", "_") + ".epub"
    if cache_dir:
        path = os.path.join(cache_dir, name)
        if os.path.exists(path) and os.path.getsize(path) > 1000:
            return open(path, "rb").read()
    url = EXPORT + urllib.parse.quote(page.replace(" ", "_"))
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=300) as r:
        data = r.read()
    if not data.startswith(b"PK"):
        raise RuntimeError("export did not return an EPUB for %r" % page)
    if cache_dir:
        os.makedirs(cache_dir, exist_ok=True)
        open(os.path.join(cache_dir, name), "wb").write(data)
    return data


def api_html(title):
    """Rendered HTML of one Wikisource page."""
    q = urllib.parse.urlencode({
        "action": "parse", "prop": "text", "page": title,
        "format": "json", "formatversion": "2"})
    req = urllib.request.Request(API + "?" + q, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=120) as r:
        j = json.loads(r.read().decode("utf-8"))
    return (j.get("parse") or {}).get("text") or ""


def index_members(index_title, index_html):
    """The pages that make up a collection, in the order its index lists them.

    Some works are one Wikisource page with chapter subpages, which the export
    service handles by itself. Others — Записки охотника, Вечера на хуторе —
    are an index page linking out to each story as a page in its own right,
    and exporting the index gives you a list of titles and no text at all.
    This reads the index the way a reader would: the links, in order.
    """
    # Each story is titled "<Story> (<Author>)", so the author in the index's
    # own title says which links belong to the work and which are, say, a
    # Pushkin review of it sitting in the see-also list.
    m = re.search(r"\(([^()]+)\)\s*$", index_title)
    author = m.group(1) if m else ""
    out, seen = [], set()
    for href in re.findall(r'href="([^"]+)"', index_html):
        mm = re.search(r"/wiki/(.+)$", href)
        if not mm:
            continue
        t = urllib.parse.unquote(mm.group(1)).replace("_", " ").split("#")[0]
        if t in seen or t == index_title:
            continue
        # Namespaces, interwiki, Wikidata items, the licence boilerplate.
        if ":" in t.split("/")[0] or re.match(r"^Q\d+$", t):
            continue
        if t.startswith("Гражданский кодекс"):
            continue
        is_sub = t.startswith(index_title + "/")
        if is_sub and re.search(r"/(ДО|Версия|Оглавление|Содержание)\b", t):
            continue
        if not (is_sub or (author and t.endswith("(" + author + ")"))):
            continue
        seen.add(t)
        out.append(t)
    return out


def chapters_from_pages(pages):
    """[(page title, html)] -> chapters, one per page."""
    chapters = []
    for title, h in pages:
        try:
            doc = ET.fromstring("<div>" + _strip_bad_xml(h) + "</div>")
        except ET.ParseError:
            doc = ET.fromstring("<div>" + _strip_bad_xml(h, hard=True) + "</div>")
        blocks = _clean_chunks(_blocks(doc))
        if not blocks:
            continue
        name = page_chapter_name(title)
        if blocks[0][0] == "h" and _same(blocks[0][1], name):
            blocks = blocks[1:]
        chapters.append({"title": name, "blocks": blocks})
    if len(chapters) == 1:
        # A one-page work still has to be chaptered from the inside.
        chapters = split_at_headings(chapters[0]["title"],
                                     chapters[0]["blocks"])
    return [drop_self_title(c) for c in chapters if not is_front_matter(c)]


def _strip_bad_xml(h, hard=False):
    """The API returns HTML, not XML: void tags are unclosed and entities are
    HTML ones. Make it parseable without pulling in a parser dependency."""
    h = re.sub(r"<!--.*?-->", "", h, flags=re.S)
    h = re.sub(r"<(br|hr|img|link|meta|input|col|source)\b([^>]*?)/?>",
               r"<\1\2/>", h)
    h = re.sub(r"&(?!#\d+;|#x[0-9a-fA-F]+;|amp;|lt;|gt;|quot;|apos;)",
               "&amp;", h)
    if hard:
        h = re.sub(r"<(script|style)\b.*?</\1>", "", h, flags=re.S | re.I)
        h = re.sub(r"</?(font|center|big|small|tt|nobr)\b[^>]*>", "", h)
    return h


# --------------------------------------------------------------- EPUB → text --
def _text_of(el):
    """Visible text of an element, with the bits Wikisource adds for the web
    left out."""
    out = []

    def walk(e):
        cls = set((e.get("class") or "").split())
        if e.get("id") in DROP_IDS or (cls & DROP_CLASSES):
            return
        if any(DROP_CLASS_RE.match(c) for c in cls):
            return
        tag = e.tag.replace(XH, "")
        if tag in DROP_TAGS:
            return
        if tag == "br":
            out.append("\n")
        # A div, or a span set to display:block, is a line of its own —
        # Wikisource builds epigraphs out of nested divs, and without this the
        # epigraph runs straight into its attribution.
        if tag == "div" or "display:block" in (e.get("style") or "").replace(" ", ""):
            out.append("\n")
        if e.text:
            out.append(e.text)
        for c in e:
            walk(c)
            if c.tail:
                out.append(c.tail)

    walk(el)
    s = "".join(out)
    s = s.replace(" ", " ").replace("​", "")
    # Wikisource emits entity spans that become stray spaces around dashes.
    s = re.sub(r"[ \t]+", " ", s)
    return s


BLOCKISH = {"p", "dd", "dt", "li", "blockquote",
            "h1", "h2", "h3", "h4", "h5", "h6"}
# A chapter number on Wikisource is often not a heading at all but a centred
# div holding "I" or "Глава 3". It reads as a heading, so it is treated as one.
NUMERAL = re.compile(
    r"^(?:[IVXLCDM]{1,7}|\d{1,3}|"
    r"(?:Глава|Часть|Действие|Явление|Запись|Книга|Том|Песнь|Сцена)"
    r"\s+[^\s]{1,20})\.?$", re.I)


def _has_block_descendant(e):
    for c in e.iter():
        if c is e:
            continue
        if c.tag.replace(XH, "") in BLOCKISH:
            return True
    return False


def _blocks(body):
    """Reading-order blocks of one page: paragraphs, verse lines, headings.

    Verse is the reason this is not simply "every <p>": Мцыри, Конёк-Горбунок
    and Двенадцать are poems, where a <br/> inside a paragraph is a line of
    verse and joining them would destroy the poem.

    And divs are the reason it is not "every block tag": Wikisource writes
    epigraphs, attributions and — crucially — chapter numbers as bare styled
    divs with no paragraph inside, so a walker that only looks for <p> loses
    the chapter divisions of Пиковая дама and every work marked up like it.
    """
    out = []

    def walk(e):
        cls = set((e.get("class") or "").split())
        if e.get("id") in DROP_IDS or (cls & DROP_CLASSES):
            return
        if any(DROP_CLASS_RE.match(c) for c in cls):
            return
        tag = e.tag.replace(XH, "")
        if tag in DROP_TAGS:
            return
        if tag in ("p", "dd", "dt", "li", "blockquote"):
            t = _text_of(e)
            for line in t.split("\n"):
                line = line.strip()
                if line:
                    out.append(("n" if NUMERAL.match(line) else "p", line))
            return
        if tag in ("h1", "h2", "h3", "h4", "h5", "h6"):
            t = _text_of(e).strip()
            if t:
                out.append(("h", t))
            return
        if tag == "div" and "heading" in (e.get("role") or ""):
            t = _text_of(e).strip()
            if t:
                out.append(("h", t))
            return
        # A container with nothing block-level inside it IS the block: its
        # text would otherwise be thrown away.
        if tag in ("div", "span", "center", "section", "td", "th") and \
                not _has_block_descendant(e):
            t = _text_of(e)
            for line in t.split("\n"):
                line = line.strip()
                if line:
                    out.append(("n" if NUMERAL.match(line) else "p", line))
            return
        for c in e:
            walk(c)

    walk(body)
    return out


NOTES_HEAD = re.compile(r"^(Примечани|Комментари|Сноски|Источники)", re.I)
FRONT_MATTER = re.compile(
    r"^(Содержание|Оглавление|Редакции|Список редакций|Издания|Версии)\b", re.I)
LEADERS = re.compile(r"[.\u2024\u2027]\s*[.\u2024\u2027]\s*[.\u2024\u2027]")


def is_front_matter(chapter):
    """A contents page is not chapter one.

    The export keeps the work's own table of contents and its list of
    editions, which arrive looking like a chapter of thirty-eight lines and
    twenty-nine words — enough to survive an emptiness check, and enough to
    make the first thing a reader opens a page of dot leaders.
    """
    blocks = chapter["blocks"]
    if not blocks:
        return True
    texts = [t for _k, t in blocks]
    if any(FRONT_MATTER.match(t) for t in texts[:3]):
        return True
    if len(texts) >= 5 and sum(1 for t in texts if LEADERS.search(t)) > len(texts) * 0.5:
        return True
    return False


def drop_self_title(chapter):
    """A chapter whose first line repeats its own heading prints the number
    twice — once in the contents, once at the top of the page."""
    b = chapter["blocks"]
    while b and b[0][0] in ("h", "n") and _same(b[0][1], chapter["title"] or ""):
        b = b[1:]
    chapter["blocks"] = b
    return chapter


def split_at_headings(title, blocks, min_parts=3):
    """One Wikisource page, several chapters.

    Борис Годунов is twenty-three scenes on one page; Путешествие is
    twenty-seven posting stations. The headings are right there in the markup,
    so the book should arrive chaptered rather than as one scroll the reading
    record can only ever be 0% or 100% through.

    Real headings win over bare numerals. A play's page carries both — the act
    as a heading and every явление as a centred numeral — and splitting on the
    numerals would file Бесприданница as ninety-eight chapters of forty words.
    Numerals are only the divider when the page has no headings at all, which
    is the case for Пиковая дама and for most verse.
    """
    heads = [i for i, (k, _t) in enumerate(blocks) if k == "h"]
    if len(heads) < min_parts:
        heads = [i for i, (k, _t) in enumerate(blocks) if k in ("h", "n")]
    if len(heads) < min_parts:
        return [{"title": title, "blocks": blocks}]
    out = []
    lead = blocks[:heads[0]]
    if any(k == "p" for k, _ in lead):
        out.append({"title": title, "blocks": lead})
    for n, start in enumerate(heads):
        end = heads[n + 1] if n + 1 < len(heads) else len(blocks)
        body = blocks[start + 1:end]
        if not any(k in ("p", "n") for k, _ in body):
            continue
        out.append({"title": blocks[start][1], "blocks": body})
    return out or [{"title": title, "blocks": blocks}]


def _drop_notes(blocks):
    """Footnotes are apparatus, not the book."""
    for i, (k, t) in enumerate(blocks):
        if k == "h" and NOTES_HEAD.match(t):
            return blocks[:i]
    return blocks


def _clean_chunks(blocks):
    """Drop the licence boilerplate and the edition header that survive as
    ordinary paragraphs."""
    bad = re.compile(
        r"(Это произведение перешло в общественное достояние"
        r"|Public ?Domain|Creative Commons|GNU Free Documentation"
        r"|Внимание! Данная страница|Источник:|См\. также|Викитека"
        r"|Оригинал (?:находится|здесь))", re.I)
    return _drop_notes([(k, t) for (k, t) in blocks if not bad.search(t)])


# The reader treats a chapter heading of exactly "Глава 7" as no heading at
# all — it reads it as filler and falls back to splitting on in-text numerals,
# which for Белая гвардия produced twenty-four "chapters", most of them one
# line long. The library's own convention (see Anna Karenina) is the bare
# numeral, so that is what gets written. Part names — Часть, Действие, Запись —
# say something a number does not, and are left alone.
BARE_NUMBER = re.compile(r"^(?:глава|chapter)\s+(\d{1,3})\.?$", re.I)


def tidy_heading(t):
    m = BARE_NUMBER.match((t or "").strip())
    return m.group(1) if m else t


# A page path like "Левша (Лесков)/ПСС 1902—1903 (ВТ:Ё)" names an edition in
# its last segment, not a chapter. The book is what the first segment says.
EDITION_SEGMENT = re.compile(
    r"^(ПСС|СС\d?|ВТ|ДО|Изд|Издание|Редакция|Версия|\d{4})\b", re.I)


def page_chapter_name(title):
    parts = [p for p in title.split("/") if p]
    last = re.sub(r"\s*\([^()]*\)\s*$", "", parts[-1]).strip()
    if len(parts) > 1 and EDITION_SEGMENT.match(last):
        return re.sub(r"\s*\([^()]*\)\s*$", "", parts[0]).strip()
    return last


def _same(a, b):
    """Same heading, allowing for the word the navigation adds.

    The export's table of contents calls a chapter "Глава I Предсказание"
    while the page itself heads it "I Предсказание"; printing both puts the
    title on screen twice.
    """
    def n(s):
        s = re.sub(r"^\s*(глава|часть|chapter)\s+", "",
                   (s or "").strip(), flags=re.I)
        return re.sub(r"[^a-zа-я0-9]+", "", s.lower().replace("ё", "е"))
    return n(a) == n(b)


def read_epub(data):
    """(title, author, [ {title, blocks} ]) — one entry per spine document,
    in reading order, with the export service's own front matter dropped."""
    z = zipfile.ZipFile(io.BytesIO(data))
    container = ET.fromstring(z.read("META-INF/container.xml"))
    opf_path = container.find(".//{*}rootfile").get("full-path")
    base = os.path.dirname(opf_path)
    opf = ET.fromstring(z.read(opf_path))

    title = (opf.findtext(".//" + DC + "title") or "").strip()
    author = (opf.findtext(".//" + DC + "creator") or "").strip()
    author = re.sub(r"^автор\s+", "", author).strip()

    href = {}
    for item in opf.findall(".//" + OPF + "item"):
        href[item.get("id")] = item.get("href")

    # Chapter names come from the navigation document, which carries the
    # Wikisource page titles; the XHTML headings are often absent or are the
    # work's own title repeated.
    labels = {}
    try:
        ncx_id = [i for i, h in href.items() if h.endswith("toc.ncx")]
        if ncx_id:
            ncx = ET.fromstring(z.read(os.path.join(base, href[ncx_id[0]])))
            for np in ncx.findall(".//" + NCX + "navPoint"):
                lab = np.findtext(".//" + NCX + "text") or ""
                src = np.find(NCX + "content").get("src", "").split("#")[0]
                if src:
                    labels[src] = lab.strip()
    except Exception:
        pass

    chapters = []
    for ref in opf.findall(".//" + OPF + "itemref"):
        h = href.get(ref.get("idref"))
        if not h or not h.endswith((".xhtml", ".html")):
            continue
        if os.path.basename(h) in ("title.xhtml", "about.xhtml", "nav.xhtml"):
            continue
        try:
            doc = ET.fromstring(z.read(os.path.join(base, h)))
        except Exception:
            continue
        body = doc.find(XH + "body")
        if body is None:
            continue
        blocks = _clean_chunks(_blocks(body))
        if not blocks:
            continue
        name = labels.get(h) or labels.get(os.path.basename(h)) or ""
        # The page repeats its own title as the first heading. Keeping it
        # would print every chapter's name twice.
        if name and blocks and blocks[0][0] == "h" and \
                _same(blocks[0][1], name):
            blocks = blocks[1:]
        if not name and blocks and blocks[0][0] == "h":
            name, blocks = blocks[0][1], blocks[1:]
        chapters.append({"title": name, "blocks": blocks})
    # When the export gave several documents, those ARE the chapters and the
    # numerals inside them are scene breaks; only a single-document work needs
    # splitting from the inside.
    if len(chapters) == 1:
        chapters = split_at_headings(chapters[0]["title"],
                                     chapters[0]["blocks"])
    chapters = [drop_self_title(c) for c in chapters if not is_front_matter(c)]
    return title, author, chapters


# ------------------------------------------------------------------ FB2 out --
def _esc(s):
    return (s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;"))


def build_fb2(title, author, chapters, source_url):
    """FB2 2.1 with one <section> per chapter.

    The reader chapters a book from these sections (walkSection), falling back
    to in-text numerals only when the sections turn out to be too small to be
    chapters — so getting them right here is what makes the contents list, the
    progress bar and the video map line up later.
    """
    out = []
    a = out.append
    a('<?xml version="1.0" encoding="utf-8"?>')
    a('<FictionBook xmlns="http://www.gribuser.ru/xml/fictionbook/2.1">')
    a("<description><title-info>")
    a("<book-title>%s</book-title>" % _esc(title))
    a("<author><nickname>%s</nickname></author>" % _esc(author))
    a("<lang>ru</lang>")
    a("</title-info><document-info>")
    a("<src-url>%s</src-url>" % _esc(source_url))
    a("<program-used>tools/add_wikisource.py</program-used>")
    a("</document-info></description>")
    a("<body>")
    a("<title><p>%s</p><p>%s</p></title>" % (_esc(author), _esc(title)))
    for ch in chapters:
        a("<section>")
        head = tidy_heading(ch["title"])
        if head:
            a("<title><p>%s</p></title>" % _esc(head))
        for kind, text in ch["blocks"]:
            if kind in ("h", "n"):
                # A heading inside the chapter body — a scene number, or a
                # part name the navigation did not carry. Kept as a plain
                # paragraph so the reader's own marker splitter can still see
                # it if it wants to.
                a("<p><strong>%s</strong></p>" % _esc(text))
            else:
                a("<p>%s</p>" % _esc(text))
        a("</section>")
    a("</body>")
    a("</FictionBook>")
    return "\n".join(out) + "\n"


# ------------------------------------------------------------------ catalogue --
def count_words(chapters):
    n = 0
    for ch in chapters:
        for _k, t in ch["blocks"]:
            n += len(RU_WORD.findall(t))
    return n


def upsert(manifest_path, entry, keep_existing=True):
    man = json.load(open(manifest_path, encoding="utf-8"))
    for i, b in enumerate(man):
        if b.get("slug") == entry["slug"]:
            if keep_existing:
                merged = dict(entry)
                merged.update({k: v for k, v in b.items()
                               if k not in ("words", "filename")})
                man[i] = merged
            else:
                man[i] = entry
            break
    else:
        man.append(entry)
    with open(manifest_path, "w", encoding="utf-8", newline="\n") as f:
        json.dump(man, f, ensure_ascii=False, indent=2)
        f.write("\n")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("page", nargs="?", help="Wikisource page title")
    ap.add_argument("--slug")
    ap.add_argument("--title")
    ap.add_argument("--author")
    ap.add_argument("--category", default="Novels & Stories")
    ap.add_argument("--list", dest="listfile",
                    help="TSV: slug, page, author, title, category, blurb")
    ap.add_argument("--epub-dir", help="use EPUBs already downloaded here")
    ap.add_argument("--html-json",
                    help='{"slug": [{"page":..,"html":..}]} fetched elsewhere')
    ap.add_argument("--cache", default=".ws-cache")
    ap.add_argument("--manifest", default=MANIFEST)
    ap.add_argument("--books-dir", default=BOOKS_DIR)
    ap.add_argument("--no-catalogue", action="store_true")
    ap.add_argument("--replace-entry", action="store_true",
                    help="overwrite an existing entry instead of merging")
    a = ap.parse_args()

    jobs = []
    if a.listfile:
        with open(a.listfile, encoding="utf-8") as f:
            for row in csv.reader(f, delimiter="\t"):
                if not row or row[0].startswith("#"):
                    continue
                row = (row + [""] * 6)[:6]
                jobs.append(dict(slug=row[0], page=row[1], author=row[2],
                                 title=row[3], category=row[4] or a.category,
                                 blurb=row[5]))
    elif a.page:
        jobs.append(dict(slug=a.slug, page=a.page, author=a.author,
                         title=a.title, category=a.category, blurb=""))
    else:
        ap.error("give a page title or --list")

    cached_html = {}
    if a.html_json:
        cached_html = json.load(open(a.html_json, encoding="utf-8"))

    os.makedirs(a.books_dir, exist_ok=True)
    ok = fail = 0
    for j in jobs:
        try:
            page = j["page"]
            if j["slug"] in cached_html:
                # Pages fetched somewhere with network access.
                pairs = [(x["page"], x["html"]) for x in cached_html[j["slug"]]]
                chapters = chapters_from_pages(pairs)
                t, au = j["title"], j["author"]
            elif page.startswith("@"):
                # A collection: the index page names the stories.
                idx = page[1:]
                members = index_members(idx, api_html(idx))
                if not members:
                    raise RuntimeError("index page listed no chapters")
                chapters = chapters_from_pages(
                    [(m, api_html(m)) for m in members])
                t, au = j["title"], j["author"]
                page = idx
            else:
                data = fetch_epub(page, a.epub_dir or a.cache)
                t, au, chapters = read_epub(data)
            if not chapters:
                raise RuntimeError("no readable chapters")
            title = j["title"] or t
            author = j["author"] or au
            src = "https://ru.wikisource.org/wiki/" + urllib.parse.quote(
                page.lstrip("@").replace(" ", "_"))
            fb2 = build_fb2(title, author, chapters, src)
            fn = j["slug"] + ".fb2"
            open(os.path.join(a.books_dir, fn), "w",
                 encoding="utf-8", newline="\n").write(fb2)
            words = count_words(chapters)
            print("%-28s %3d chapters  %8s words  %s"
                  % (j["slug"], len(chapters), format(words, ","), fn))
            if not a.no_catalogue:
                entry = {
                    "filename": "novel/" + fn,
                    "title": title,
                    "author": author,
                    "category": j["category"],
                    "slug": j["slug"],
                    "public": True,
                    "words": words,
                    "_note": "Text from Russian Wikisource: " + src,
                }
                if j.get("blurb"):
                    entry["blurb"] = j["blurb"]
                upsert(a.manifest, entry,
                       keep_existing=not a.replace_entry)
            ok += 1
        except Exception as e:
            print("!! %-25s %s" % (j.get("slug") or j["page"], e))
            fail += 1
    print("\n%d added, %d failed" % (ok, fail))
    return 1 if fail else 0


if __name__ == "__main__":
    sys.exit(main())
