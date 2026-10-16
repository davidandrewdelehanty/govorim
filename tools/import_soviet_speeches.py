#!/usr/bin/env python3
"""Add the speeches in tools/soviet_speeches.json to the library, each with its
YouTube recording embedded. Runs in WSL (it needs the network); no AI involved.

For every speech it:
  1. fetches the text — Russian Wikisource (key "ws", via the API), a
     marxists.org page (key "mia"), or a local plain-text file ("text_file",
     one paragraph per line);
  2. checks the YouTube candidates with yt-dlp and keeps the first one that is
     playable and allowed to be embedded;
  3. writes public/books/novel/<slug>.fb2 and adds (or updates) the catalogue
     entry: category "Speeches by Soviet Leaders", year, words, public, and
     videos {"0": {youtube, heading, start, end}};
then builds stress maps for the new books.

    python3 tools/import_soviet_speeches.py            # everything
    python3 tools/import_soviet_speeches.py --only lenin-o-prodnaloge
    python3 tools/import_soviet_speeches.py --dry      # fetch and report, write nothing

Each speech's text is printed (first and last lines) so a bad extraction is
easy to spot; fix the source in the JSON and run it again — it overwrites.
"""
import html, io, json, os, re, subprocess, sys, time, urllib.parse, urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SPEC = os.path.join(ROOT, "tools", "soviet_speeches.json")
MANIFEST = os.path.join(ROOT, "private", "books", "index.json")
NOVEL = os.path.join(ROOT, "public", "books", "novel")
UA = {"User-Agent": "SamovarSpeechImporter/1.0 (personal library; contact via samovar.live)"}
CAT = "Speeches by Soviet Leaders"


def get(url, tries=4):
    for k in range(tries):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=40) as r:
                return r.read()
        except Exception as e:
            if k == tries - 1:
                raise
            time.sleep(3 * (k + 1))


def clean(t):
    t = re.sub(r"\[\d+\]|\[\*\]", "", t)
    t = t.replace("\xa0", " ").replace("‎", "")
    return re.sub(r"\s+", " ", t).strip()


def paras_from_html(h):
    """Text paragraphs of an article: <p> blocks, notes and navigation left out."""
    h = re.sub(r"(?is)<(script|style|table|sup)[^>]*>.*?</\1>", " ", h)
    out = []
    for m in re.finditer(r"(?is)<p[^>]*>(.*?)</p>", h):
        t = clean(html.unescape(re.sub(r"(?s)<[^>]+>", " ", m.group(1))))
        if t:
            out.append(t)
    return out


def from_wikisource(title):
    q = urllib.parse.urlencode({"action": "parse", "format": "json", "prop": "text",
                                "redirects": 1, "page": title})
    d = json.loads(get("https://ru.wikisource.org/w/api.php?" + q))
    h = d["parse"]["text"]["*"]
    # drop the header/licence boxes and the "См. также" tail
    h = re.split(r'(?i)<h2[^>]*>\s*(?:<span[^>]*>)?\s*См\. также', h)[0]
    h = re.sub(r'(?is)<div[^>]*class="[^"]*(?:licenseContainer|ws-noexport|noprint|mw-references-wrap)[^"]*".*?</div>', " ", h)
    return [p for p in paras_from_html(h) if not re.search(r"общественное достояние|ГК РФ|Если произведение является переводом", p)]


def from_marxists(url):
    raw = get(url)
    m = re.search(rb'charset=["\']?([\w-]+)', raw[:2000])
    enc = m.group(1).decode() if m else "utf-8"
    try:
        h = raw.decode(enc, errors="replace")
    except LookupError:
        h = raw.decode("utf-8", errors="replace")
    ps = paras_from_html(h)
    # cut the volume's navigation and the editors' notes
    out = []
    for p in ps:
        if re.match(r"^(Примечания|ПРИМЕЧАНИЯ|Печатается по|Источник:|Сочинения|Том \d|Оглавление|←|Следующая|Предыдущая)", p):
            if out:
                break
            continue
        if re.search(r"marxists\.org|MIA|Русский отдел", p):
            continue
        out.append(p)
    # a trailing newspaper credit («Правда» 10 мая 1945 г.) is not the speech
    while out and re.match(r"^[«\"]?(Правда|Известия|Большевик)\b.*\d{4}", out[-1]) and len(out[-1]) < 80:
        out.pop()
    return out


def review_pdf(s):
    """Pull a newspaper scan's text layer into tools/speech-src/<slug>.txt.
    Newspaper columns and OCR need a human eye, so this is never published."""
    d = os.path.join(ROOT, "tools", "speech-src")
    os.makedirs(d, exist_ok=True)
    for i, url in enumerate(s["pdf"]):
        pdf = os.path.join(d, "%s-%d.pdf" % (s["slug"], i))
        if not os.path.exists(pdf):
            io.open(pdf, "wb").write(get(url))
        txt = os.path.join(d, "%s-%d.txt" % (s["slug"], i))
        subprocess.run(["pdftotext", "-layout", pdf, txt])
        n = os.path.getsize(txt) if os.path.exists(txt) else 0
        print("   scan text for review: %s (%d bytes)" % (os.path.relpath(txt, ROOT), n))


def current_text(entry):
    if not entry:
        return []
    sys.path.insert(0, os.path.join(ROOT, "tools"))
    from reader_chapters import reader_chapters
    chs, _ = reader_chapters(os.path.join(ROOT, "public", "books", entry["filename"]))
    return [p for c in chs for p in c["paras"]]


def search_ids(q, n=8):
    r = subprocess.run(["yt-dlp", "--flat-playlist", "--print", "%(id)s\t%(duration)s\t%(title)s",
                        "ytsearch%d:%s" % (n, q)], capture_output=True, text=True, timeout=180)
    rows = [l.split("\t", 2) for l in r.stdout.splitlines() if l.count("\t") >= 2]
    for vid, dur, title in rows:
        print("     search hit: %s %ss %s" % (vid, dur, title[:70]))
    # longest first: the full speech, not a clip of it
    rows.sort(key=lambda x: -float(x[1]) if x[1] not in ("NA", "None", "") else 0)
    return [x[0] for x in rows]


def check_video(cands):
    for vid in cands:
        try:
            j = json.loads(subprocess.run(["yt-dlp", "-J", "--skip-download", "--no-warnings",
                                           "https://www.youtube.com/watch?v=" + vid],
                                          capture_output=True, text=True, timeout=120).stdout or "{}")
        except Exception as e:
            print("     yt-dlp failed on", vid, e); continue
        if not j.get("id"):
            print("     unavailable:", vid); continue
        if j.get("playable_in_embed") is False:
            print("     not embeddable:", vid); continue
        return vid, j.get("duration"), j.get("title", "")
    return None, None, None


def esc(t):
    return t.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def fb2(s, paras):
    last, first = (s["author"].split(" ", 1) + [""])[:2]
    body = "\n".join("<p>%s</p>" % esc(p) for p in paras)
    return ('<?xml version="1.0" encoding="utf-8"?>\n'
            '<FictionBook xmlns="http://www.gribuser.ru/xml/fictionbook/2.0" xmlns:l="http://www.w3.org/1999/xlink">\n'
            "<description><title-info><genre>nonfiction</genre>"
            "<author><first-name>%s</first-name><last-name>%s</last-name></author>"
            "<book-title>%s</book-title><date>%s</date><lang>ru</lang></title-info></description>\n"
            "<body>\n<section>\n<title><p>%s</p></title>\n%s\n</section>\n</body>\n</FictionBook>\n"
            % (esc(first), esc(last), esc(s["title"]), s["year"], esc(s["title"]), body))


def main():
    a = sys.argv[1:]
    only = set(a[a.index("--only") + 1:]) if "--only" in a else None
    dry = "--dry" in a
    spec = json.load(io.open(SPEC, encoding="utf-8"))["speeches"]
    idx = json.load(io.open(MANIFEST, encoding="utf-8"))
    by = {b.get("slug"): b for b in idx}
    done, failed = [], []
    for s in spec:
        if only and s["slug"] not in only:
            continue
        print("==", s["slug"])
        try:
            if s.get("pdf") and not s.get("text_file"):
                review_pdf(s)
                paras = None
            elif s.get("ws"):
                paras, src = from_wikisource(s["ws"]), "https://ru.wikisource.org/wiki/" + urllib.parse.quote(s["ws"].replace(" ", "_"))
            elif s.get("mia"):
                paras, src = from_marxists(s["mia"]), s["mia"]
            else:
                paras = [clean(l) for l in io.open(os.path.join(ROOT, s["text_file"]), encoding="utf-8") if clean(l)]
                src = s.get("source", "")
        except Exception as e:
            print("   !! text:", e); failed.append(s["slug"]); continue
        if paras is None:
            paras = current_text(by.get(s["slug"]))
            src = (by.get(s["slug"]) or {}).get("_note", "").replace("Text: ", "")
            print("   text kept as it is until the scan's text is checked")
        words = len(re.findall(r"[А-Яа-яЁё][А-Яа-яЁё-]*", " ".join(paras)))
        if words < 40:
            print("   !! only %d words — extraction failed, skipped" % words); failed.append(s["slug"]); continue
        print("   %d paragraphs, %d words" % (len(paras), words))
        print("   first:", paras[0][:110])
        print("   last: ", paras[-1][:110])
        vid, dur, vtitle = check_video(s["youtube"])
        if not vid and s.get("youtube_search"):
            print("   listed videos failed; searching YouTube — CHECK the pick below")
            vid, dur, vtitle = check_video(search_ids(s["youtube_search"]))
        if not vid:
            print("   !! no playable, embeddable video"); failed.append(s["slug"]); continue
        print("   video: %s (%ss) %s" % (vid, dur, vtitle[:70]))
        if dry:
            continue
        e = by.get(s["slug"])
        fn = e["filename"] if (s.get("existing") and e) else "novel/%s.fb2" % s["slug"]
        io.open(os.path.join(ROOT, "public", "books", fn), "w", encoding="utf-8", newline="\n").write(fb2(s, paras))
        seg = {"youtube": vid, "heading": s["title"], "start": s.get("start") or 0}
        if s.get("end"):
            seg["end"] = s["end"]
        e = by.get(s["slug"])
        if e is None:
            e = {"slug": s["slug"]}
            idx.append(e); by[s["slug"]] = e
        e.update({"filename": fn, "title": s["title"], "author": s["author"], "category": CAT,
                  "year": s["year"], "public": True, "blurb": s["blurb"], "words": words,
                  "videos": {"0": seg}, "_note": "Text: " + src})
        if s.get("existing"):
            # the YouTube recording replaces the R2 player
            e.pop("audiobook", None); e.pop("publicAudio", None)
        done.append(s["slug"])
    if done and not dry:
        io.open(MANIFEST, "w", encoding="utf-8").write(json.dumps(idx, ensure_ascii=False, indent=2) + "\n")
        print("\nstress marks for the new books:")
        subprocess.run([sys.executable, os.path.join(ROOT, "tools", "gen_stress_maps.py")])
    print("\n%d added/updated%s" % (len(done), ("; FAILED: " + " ".join(failed)) if failed else ""))


if __name__ == "__main__":
    main()
