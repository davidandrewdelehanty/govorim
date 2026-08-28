#!/usr/bin/env python3
"""Download the Russian originals for the Самовар sourcing ledger, from az.lib.ru.

Why this exists as a second script: the first pass proved az.lib.ru is the only
source that reliably yields a whole work. ru.wikisource splits novels across
subpages, so fetching the page named "Игрок (Достоевский)" gets a 2 kB table of
contents, not the novel — every "wikitext" line in that run was a TOC. Wikimedia
also serves its EPUB exporter behind an anti-bot challenge that a script cannot
pass. az.lib.ru (Библиотека Максима Мошкова) has essentially the whole canon as
one plain-text file per work, and it has no such defences.

The only hard part is finding the right page, which this does by fetching the
author's index once and matching the work's title against the links on it.

    python3 tools/fetch_ru.py                # fill in everything still missing
    python3 tools/fetch_ru.py --redo-junk    # also replace the tiny TOC files
    python3 tools/fetch_ru.py --dry-run      # resolve titles, download nothing

Everything is windows-1251 on that site and is written back out as UTF-8.
"""
import argparse, csv, difflib, io, os, re, sys, time
import urllib.request, urllib.error, urllib.parse

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MANIFEST = os.path.join(ROOT, "tools", "data", "sources.tsv")
OUT = os.path.abspath(os.path.join(ROOT, "..", "govorim-sources", "ru"))
UA = ("Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/126.0 Safari/537.36")
PAUSE = 1.0
MIN_BYTES = 1500          # below this it is a stub, not a text

# Authors whose index the manifest never names, with the path Moshkov uses.
# Anything wrong here fails loudly at the fetch, it cannot silently mis-file.
FALLBACK = {
    "Чехов": "/c/chehow_a_p/", "Тургенев": "/t/turgenew_i_s/",
    "Гоголь": "/g/gogolx_n_w/", "Гончаров": "/g/goncharow_i_a/",
    "Лесков": "/l/leskow_n_s/", "Некрасов": "/n/nekrasow_n_a/",
    "Чернышевский": "/c/chernyshewskij_n_g/", "Карамзин": "/k/karamzin_n_m/",
    "Крылов": "/k/krylow_i_a/", "Салтыков-Щедрин": "/s/saltykow_m_e/",
    "Островский": "/o/ostrowskij_a_n/", "Лермонтов": "/l/lermontow_m_j/",
    "Пушкин": "/p/pushkin_a_s/", "Тютчев": "/t/tutchew_f_i/",
    "Фет": "/f/fet_a_a/", "А. К. Толстой": "/t/tolstoj_a_k/",
    "Блок": "/b/blok_a_a/", "Брюсов": "/b/brjusow_w_j/",
    "Бальмонт": "/b/balxmont_k_d/", "Есенин": "/e/esenin_s_a/",
    "Жуковский": "/z/zhukowskij_w_a/", "Батюшков": "/b/batjushkow_k_n/",
    "Аксаков": "/a/aksakow_s_t/", "Гаршин": "/g/garshin_w_m/",
    "Герцен": "/g/gercen_a_i/", "Короленко": "/k/korolenko_w_g/",
}

def get(url, timeout=90):
    """Returns (bytes, charset-from-header-or-None)."""
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        try:
            cs = r.headers.get_content_charset()
        except Exception:
            cs = None
        return r.read(), cs

# The ten commonest letters in Russian. Any single-byte codec decodes any byte
# sequence without complaint, so "did it raise?" cannot tell KOI8-R from
# windows-1251 — the wrong one just yields plausible-looking gibberish. What
# separates them is letter frequency: decoded correctly, these ten account for
# roughly 60% of the Cyrillic; decoded wrongly, far less.
COMMON = set("оаеинтсрвл")

def _score(text):
    cyr = [c for c in text.lower() if "\u0400" <= c <= "\u04ff"]
    if len(cyr) < 40:
        return 0.0
    return sum(c in COMMON for c in cyr) / len(cyr)

def to_utf8(raw, hint=None):
    """Decode a Russian page whose declared encoding is often absent or a lie.

    az.lib.ru serves KOI8-R — the encoding lib.ru has used since the nineties.
    Getting this wrong is silent: windows-1251 renders KOI8-R Cyrillic as a
    different, equally valid-looking run of Cyrillic, so titles simply never
    match and every work reports "not found in index".
    """
    order = []
    if hint:
        order.append(hint)
    m = re.search(rb'charset=["\']?\s*([\w-]+)', raw[:2000], re.I)
    if m:
        order.append(m.group(1).decode("ascii", "ignore"))
    order += ["koi8-r", "windows-1251", "utf-8"]

    best, best_score = None, -1.0
    seen = set()
    for enc in order:
        e = (enc or "").lower().strip()
        if not e or e in seen:
            continue
        seen.add(e)
        try:
            text = raw.decode(e)
        except (UnicodeDecodeError, LookupError):
            continue
        sc = _score(text)
        if sc > best_score:
            best, best_score = text, sc
        if sc > 0.55:            # unambiguously right, stop looking
            return text
    return best if best is not None else raw.decode("koi8-r", "replace")

def norm(t):
    """Title → comparison key: no ё/е split, no case, no punctuation."""
    t = t.lower().replace("ё", "е")
    t = re.sub(r"[«»\"'(),.!?\[\]—–\-:;]", " ", t)
    return re.sub(r"\s+", " ", t).strip()

# az.lib.ru writes its index links with UNQUOTED hrefs, which is why a naive
# href="..." regex finds nothing on it.
LINK = re.compile(r'<a\s+href=["\']?(text_\d+[^\s">\']*\.shtml)["\']?[^>]*>(.*?)</a>',
                  re.I | re.S)
TAGS = re.compile(r"<[^>]+>")

def index_entries(html):
    out = []
    for href, label in LINK.findall(html):
        title = TAGS.sub(" ", label)
        title = re.sub(r"\s+", " ", title).strip(" .·")
        if title and len(title) < 200:
            out.append((href, title))
    return out

def head(raw):
    """First clause of a RAW title: «Бесы. Роман в трёх частях» → «бесы».

    This must run on the raw title, before norm() flattens punctuation away —
    the punctuation is the whole signal. Without it «Обломов» matches «Обломов
    в критике» (a volume of criticism) just as readily as «Обломов. Роман в
    четырёх частях», and the shorter of the two wins.
    """
    return norm(re.split(r"[.,:;(]", raw, maxsplit=1)[0])

def best_match(title, entries, debug=False):
    """Exact, then first-clause, then prefix, then fuzzy.

    az.lib.ru titles routinely carry a descriptive tail — «Бесы. Роман в трёх
    частях», «Холстомер (История лошади)» — so a bare equality test finds almost
    nothing and a length-capped prefix test throws away the true match. Compare
    against both the full title and its first clause, and where several entries
    match, keep the SHORTEST, which is the work itself rather than a commentary
    or a variant edition.
    """
    want = norm(title.split("·")[0].split(" + ")[0])
    if not want:
        return None
    keyed = [(norm(t), head(t), h, t) for h, t in entries]

    for k, hd, h, t in keyed:                   # whole title, exactly
        if k == want:
            return h, t, "exact"
    cands = [(k, h, t) for k, hd, h, t in keyed if hd == want]
    if cands:                                   # first clause, exactly
        k, h, t = min(cands, key=lambda x: len(x[0]))
        return h, t, "clause"
    cands = [(k, h, t) for k, hd, h, t in keyed
             if k.startswith(want) or (len(k) >= 6 and want.startswith(k))]
    if cands:                                   # prefix, no length cap
        k, h, t = min(cands, key=lambda x: len(x[0]))
        return h, t, "prefix"
    pool = [k for k, _, _, _ in keyed] + [hd for _, hd, _, _ in keyed]
    close = difflib.get_close_matches(want, pool, n=1, cutoff=0.78)
    if close:
        for k, hd, h, t in keyed:
            if k == close[0] or hd == close[0]:
                return h, t, "fuzzy"
    if debug:
        near = difflib.get_close_matches(want, [k for k, _, _, _ in keyed], n=5, cutoff=0.4)
        print("      no match for «%s»; nearest index titles: %s"
              % (want, "; ".join(near) or "none"))
    return None

def fetch_text(base, href):
    """A work page has a .txt sibling; if not, a link to fb2/zip on the page."""
    page_url = base + href
    txt_url = page_url[:-len(".shtml")] + ".txt"
    try:
        raw, cs = get(txt_url)
        if len(raw) > MIN_BYTES:
            return to_utf8(raw, cs), "txt"
    except urllib.error.HTTPError:
        pass
    except Exception:
        pass
    try:
        raw, cs = get(page_url)
        html = to_utf8(raw, cs)
        m = re.search(r'href=["\']?([^\s">\']+\.(?:fb2\.zip|fb2|zip|txt))', html, re.I)
        if m:
            u = m.group(1)
            u = u if u.startswith("http") else (
                "http://az.lib.ru" + u if u.startswith("/") else base + u)
            raw, _ = get(u)
            if len(raw) > MIN_BYTES:
                return raw, os.path.splitext(u)[1].lstrip(".")
    except Exception:
        pass
    return None, None

WIKILINK = re.compile(r"\[\[([^\]|]*)(?:\|[^\]]*)?\]\]")

def _strip(w, keep_template_text):
    w = re.sub(r"<ref[^>]*>.*?</ref>", "", w, flags=re.S)
    for _ in range(2):                              # templates, incl. one nesting
        if keep_template_text:
            # {{poemx|title|THE POEM}} → keep the longest pipe-segment
            def body(m):
                parts = m.group(1).split("|")
                return max(parts, key=len) if parts else ""
            w = re.sub(r"\{\{([^{}]*)\}\}", body, w)
        else:
            w = re.sub(r"\{\{[^{}]*\}\}", "", w)
    w = WIKILINK.sub(r"\1", w)                     # [[Link|text]] → text
    w = re.sub(r"</?[a-zA-Z][^>]*>", "", w)         # stray html
    w = re.sub(r"^=+.*=+\s*$", "", w, flags=re.M)    # section headings, whole line
    # Strip the MARKER, keep the line. Russian Wikisource indents verse with
    # ":" — deleting those lines deletes the poem, which is how «Внимая ужасам
    # войны» came back too short to accept.
    w = re.sub(r"^[*#:;]+\s*", "", w, flags=re.M)
    w = re.sub(r"'{2,}", "", w)                     # bold/italic marks
    return re.sub(r"\n{3,}", "\n\n", w).strip()

def wikitext_to_prose(w):
    """Wikitext → readable text.

    Templates are usually chrome ({{Отексте|…}} headers) and get dropped — but
    Russian Wikisource also wraps verse INSIDE a template, {{poemx|title|the
    poem}}, and dropping those deletes the poem. So strip it both ways and keep
    whichever yields more text.
    """
    a = _strip(w, keep_template_text=False)
    b = _strip(w, keep_template_text=True)
    return b if len(b) > len(a) else a

def wikisource(title, author):
    """Last resort for works az.lib.ru files inside a collection, and for poems.

    Wikisource splits a NOVEL across subpages, so its top page is a table of
    contents — which is exactly the trap that produced a crop of 5 kB "texts"
    earlier. A poem or a short story, though, lives on one page, and that page
    is the real thing. So: fetch it, and refuse anything that still looks like
    an index once the markup is stripped.
    """
    want = title.split("·")[0].split(" + ")[0].strip()
    # «Кавказский пленник» belongs to both Pushkin and Tolstoy, and the bare
    # title is a disambiguation page. Wikisource's convention for that is
    # "Title (Author)", so ask for it directly first.
    surname = author.replace("А. К. ", "").strip()
    for cand in ("%s (%s)" % (want, surname), want):
        try:
            raw, _ = get("https://ru.wikisource.org/w/index.php?action=raw&title="
                         + urllib.parse.quote(cand.replace(" ", "_")))
            wiki = raw.decode("utf-8", "replace")
            if len(wiki) > 200 and "#перенаправление" not in wiki.lower():
                prose = wikitext_to_prose(wiki)
                targets = [t.strip() for t in WIKILINK.findall(wiki)]
                nav = [t for t in targets if "/" in t and not t.startswith(
                    ("Категория:", "Файл:", "Шаблон:", "Викитека:", "Изображение:", ":"))]
                if not (len(nav) >= 4 and len(prose) < 3000) and len(prose) >= 140:
                    return prose, cand
        except Exception:
            pass
        time.sleep(0.3)
    q = urllib.parse.quote('intitle:"%s" %s' % (want, author))
    api = ("https://ru.wikisource.org/w/api.php?action=query&list=search"
           "&format=json&srlimit=1&srnamespace=0&srsearch=" + q)
    try:
        import json
        raw, cs = get(api)
        hits = json.loads(raw.decode("utf-8")).get("query", {}).get("search", [])
        if not hits:
            return None, None
        page = hits[0]["title"]
        raw, cs = get("https://ru.wikisource.org/w/index.php?action=raw&title="
                      + urllib.parse.quote(page.replace(" ", "_")))
        wiki = raw.decode("utf-8", "replace")
    except Exception:
        return None, None
    # What marks a contents page is not link COUNT — a short poem carries a
    # pile of category and interwiki links too — but links pointing at
    # SUBPAGES of itself: [[Обломов/Часть первая]]. Count only those.
    targets = [t.strip() for t in WIKILINK.findall(wiki)]
    nav = [t for t in targets
           if "/" in t and not t.startswith(("Категория:", "Файл:", "Шаблон:",
                                             "Викитека:", "Изображение:", ":"))]
    prose = wikitext_to_prose(wiki)
    if len(nav) >= 4 and len(prose) < 3000:
        return None, "toc:" + page
    # 140 chars, not 350: Лермонтов's «Парус» is twelve lines and about 320
    # characters of actual poem. The contents-page test above is what guards
    # against junk; this only catches genuinely empty pages.
    if len(prose) < 140:
        return None, "stub:" + page
    return prose, page

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--redo-junk", action="store_true",
                    help="also replace files under 15 kB (the Wikisource TOCs)")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--only", help="one slug, for testing")
    ap.add_argument("--no-wiki", action="store_true",
                    help="skip the Wikisource fallback, az.lib.ru only")
    ap.add_argument("--debug", action="store_true",
                    help="on a failed match, print the nearest index titles")
    a = ap.parse_args()

    os.makedirs(OUT, exist_ok=True)
    rows = list(csv.DictReader(io.open(MANIFEST, encoding="utf-8"), delimiter="\t"))
    for r in rows:
        for k, v in list(r.items()):
            if v == "-":
                r[k] = ""

    # author → az.lib.ru index, learned from the manifest where possible
    bases = {}
    for r in rows:
        u = r.get("ru_url", "")
        if "az.lib.ru" in u:
            bases.setdefault(r["author"], u[:u.rfind("/") + 1])
    # A fallback entry may list alternates separated by "|" — Moshkov's
    # transliteration of a surname is not always guessable, and a 404 here
    # silently loses every work by that author.
    for k, v in FALLBACK.items():
        bases.setdefault(k, "|".join("http://az.lib.ru" + p for p in v.split("|")))

    cache, got, failed, skipped = {}, [], [], 0
    for r in rows:
        slug, author, title = r["slug"], r["author"], r["ru_title"]
        if a.only and slug != a.only:
            continue
        have = [f for f in (slug + ".txt", slug + ".fb2", slug + ".zip",
                            slug + ".epub") if os.path.exists(os.path.join(OUT, f))]
        if have:
            size = os.path.getsize(os.path.join(OUT, have[0]))
            if size >= 15000 or not a.redo_junk:
                skipped += 1
                continue
        base = bases.get(author)
        if not base:
            failed.append((slug, title, "no az.lib.ru index known for " + author))
            continue
        if base not in cache:
            entries, used = [], None
            for cand in base.split("|"):
                try:
                    raw, cs = get(cand)
                    entries = index_entries(to_utf8(raw, cs))
                    if entries:
                        used = cand
                        break
                except Exception:
                    continue
                finally:
                    time.sleep(PAUSE)
            cache[base] = entries
            cache[base + "#url"] = used or base.split("|")[0]
            if entries:
                print("  index  %-22s %d works" % (author, len(entries)))
            else:
                print("  index  %-22s FAILED — no index found at %s"
                      % (author, base.replace("|", " or ")))
        hit = best_match(title, cache[base], debug=a.debug)
        if not hit:
            prose, page = (None, None) if a.no_wiki else wikisource(title, author)
            time.sleep(PAUSE)
            if prose:
                path = os.path.join(OUT, slug + ".txt")
                io.open(path, "w", encoding="utf-8", newline="\n").write(prose)
                got.append(slug)
                print("  RU  %-42s %9d B  %s [wikisource]"
                      % (slug, os.path.getsize(path), str(page)[:34]))
            else:
                why = "not in %s index" % author
                if page and page.startswith("toc:"):
                    why += "; Wikisource has only a contents page"
                elif page and page.startswith("stub:"):
                    why += "; Wikisource page too short to be the text"
                failed.append((slug, title, why))
                print("  --  %-42s %s" % (slug, why))
            continue
        href, matched, how = hit
        if a.dry_run:
            print("  %-42s → %s  [%s]" % (slug, matched[:44], how))
            got.append(slug)
            continue
        data, ext = fetch_text(cache.get(base + "#url", base), href)
        time.sleep(PAUSE)
        if not data:
            failed.append((slug, title, "found «%s» but nothing downloadable" % matched))
            print("  --  %-42s matched «%s» but no file" % (slug, matched[:32]))
            continue
        path = os.path.join(OUT, "%s.%s" % (slug, "txt" if ext == "txt" else ext))
        if isinstance(data, str):
            io.open(path, "w", encoding="utf-8", newline="\n").write(data)
        else:
            open(path, "wb").write(data)
        n = os.path.getsize(path)
        got.append(slug)
        print("  RU  %-42s %9d B  %s [%s]" % (slug, n, matched[:38], how))

    print("\n" + "─" * 69)
    print("  downloaded %d · skipped %d already good · %d unresolved"
          % (len(got), skipped, len(failed)))
    if failed:
        print("\n  Unresolved:")
        for s, t, why in failed:
            print("    %-40s %s" % (s, why))
    print("  Files: %s" % OUT)
    print("─" * 69)

if __name__ == "__main__":
    main()
