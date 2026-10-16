#!/usr/bin/env python3
"""Fill the Fairytales shelf. Runs in WSL (network); no AI involved.

For each tale in tools/fairytales.json:
  * text from Russian Wikisource (the first listed page that exists, else the
    best search hit whose title starts with the tale's name); pre-reform
    spelling is modernised with the Translations rules;
  * up to n public-domain illustrations from Wikimedia Commons (licence
    checked on Commons: public domain or CC0 only), hotlinked through
    Special:FilePath so nothing is stored in the repo; the first is the
    shelf cover, the rest are set through the tale like a picture book;
  * an FB2 in public/books/novel/<slug>.fb2 with the pictures as <image>
    between paragraphs, and a catalogue entry (category Fairytales, public,
    cover, blurb, words). Stress maps are built at the end.

    python3 tools/import_fairytales.py --dry      # fetch and report only
    python3 tools/import_fairytales.py
    python3 tools/import_fairytales.py --only morozko kolobok
"""
import html, io, json, os, re, subprocess, sys, time, urllib.parse, urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.chdir(ROOT)
sys.path.insert(0, os.path.join(ROOT, "tools"))
UA = {"User-Agent": "SamovarFairytales/1.0 (personal reading library)"}
SPEC = "tools/fairytales.json"
MANIFEST = "private/books/index.json"


def get_json(url):
    for k in range(4):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=40) as r:
                return json.loads(r.read())
        except Exception:
            if k == 3:
                raise
            time.sleep(3 * (k + 1))


def ws(params):
    return get_json("https://ru.wikisource.org/w/api.php?" + urllib.parse.urlencode(dict(params, format="json")))


def commons(params):
    return get_json("https://commons.wikimedia.org/w/api.php?" + urllib.parse.urlencode(dict(params, format="json")))


def clean(t):
    t = re.sub(r"\[\d+\]", "", html.unescape(re.sub(r"(?s)<[^>]+>", " ", t)))
    return re.sub(r"\s+", " ", t.replace("\xa0", " ").replace("‎", "")).strip()


def text_of(title):
    d = ws({"action": "parse", "prop": "text", "redirects": 1, "page": title})
    if "parse" not in d:
        return None, None
    h = d["parse"]["text"]["*"]
    h = re.split(r'(?i)<h2[^>]*>\s*(?:<span[^>]*>)?\s*(?:См\. также|Примечания)', h)[0]
    h = re.sub(r"(?is)<(table|style|sup|script)[^>]*>.*?</\1>", " ", h)
    h = re.sub(r'(?is)<div[^>]*class="[^"]*(?:licenseContainer|ws-noexport|noprint|mw-references-wrap)[^"]*".*?</div>', " ", h)
    ps = [clean(m.group(1)) for m in re.finditer(r"(?is)<(?:p|dd)[^>]*>(.*?)</(?:p|dd)>", h)]
    ps = [p for p in ps if p and not re.search(r"общественное достояние|ГК РФ|Если произведение является переводом", p)]
    return d["parse"]["title"], ps


def find_text(t):
    for title in t.get("ws", []):
        got, ps = text_of(title)
        if ps:
            return got, ps
    hits = ws({"action": "query", "list": "search", "srlimit": 10, "srsearch": t["search"]})["query"]["search"]
    name = t["title"].lower().replace("ё", "е")
    for h in hits:
        if h["title"].lower().replace("ё", "е").startswith(name.split()[0]):
            got, ps = text_of(h["title"])
            # a versions page lists editions instead of telling the tale
            if ps and sum(len(p) for p in ps) > 400:
                return got, ps
    return None, None


def pictures(t):
    out = []
    for q in t.get("img", []):
        r = commons({"action": "query", "list": "search", "srnamespace": 6, "srlimit": 12, "srsearch": q})
        names = [x["title"] for x in r["query"]["search"] if re.search(r"\.(jpe?g|png)$", x["title"], re.I)]
        if not names:
            continue
        info = commons({"action": "query", "prop": "imageinfo", "iiprop": "extmetadata|size",
                        "titles": "|".join(names)})
        meta = {}
        for p in info["query"]["pages"].values():
            ii = (p.get("imageinfo") or [{}])[0]
            m = ii.get("extmetadata") or {}
            lic = (m.get("LicenseShortName") or {}).get("value", "")
            if not re.search(r"public domain|^PD|CC0", lic, re.I) or ii.get("width", 0) < 400:
                continue
            artist = clean((m.get("Artist") or {}).get("value", ""))[:60]
            meta[p["title"]] = (artist, ii.get("width"), ii.get("height"))
        for n in names:
            if n in meta and n not in [o[0] for o in out]:
                out.append((n,) + meta[n])
        if len(out) >= t.get("n", 2):
            break
    return out[:t.get("n", 2)]


def url_for(file_title, w=900):
    f = file_title.split(":", 1)[1].replace(" ", "_")
    return "https://commons.wikimedia.org/wiki/Special:FilePath/%s?width=%d" % (urllib.parse.quote(f), w)


def esc(t):
    return t.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace('"', "&quot;")


def fb2(t, paras, pics):
    blocks = ["<p>%s</p>" % esc(p) for p in paras]
    # pictures through the tale: the first before the text, the rest evenly spaced
    for k, (name, artist, w, h) in reversed(list(enumerate(pics))):
        at = 0 if k == 0 else round(k * len(paras) / len(pics))
        cap = ("Иллюстрация: " + artist) if artist else ""
        blocks.insert(at, '<image l:href="%s" title="%s" width="%s" height="%s"/>' % (esc(url_for(name)), esc(cap), w or "", h or ""))
    return ('<?xml version="1.0" encoding="utf-8"?>\n'
            '<FictionBook xmlns="http://www.gribuser.ru/xml/fictionbook/2.0" xmlns:l="http://www.w3.org/1999/xlink">\n'
            "<description><title-info><genre>folk_tale</genre><author><last-name>%s</last-name></author>"
            "<book-title>%s</book-title><lang>ru</lang></title-info></description>\n"
            "<body>\n<section>\n<title><p>%s</p></title>\n%s\n</section>\n</body>\n</FictionBook>\n"
            % (esc(t["author"]), esc(t["title"]), esc(t["title"]), "\n".join(blocks)))


def main():
    a = sys.argv[1:]
    only = set(a[a.index("--only") + 1:]) if "--only" in a else None
    dry = "--dry" in a
    from translations_build import modern
    tales = json.load(io.open(SPEC, encoding="utf-8"))["tales"]
    idx = json.load(io.open(MANIFEST, encoding="utf-8"))
    by = {b.get("slug"): b for b in idx}
    done, failed = [], []
    for t in tales:
        if only and t["slug"] not in only:
            continue
        print("==", t["slug"])
        try:
            src, paras = find_text(t)
        except Exception as e:
            src, paras = None, None; print("   !! wikisource:", e)
        if not paras:
            print("   !! no text found"); failed.append(t["slug"]); continue
        if any("ѣ" in p or re.search(r"[бвгджзклмнпрстфхцчшщ]ъ\b", p) for p in paras):
            paras = [modern(p) for p in paras]
            print("   (pre-reform spelling modernised)")
        words = len(re.findall(r"[А-Яа-яЁё][А-Яа-яЁё-]*", " ".join(paras)))
        print("   text: %s — %d paragraphs, %d words" % (src, len(paras), words))
        print("   first:", paras[0][:100])
        print("   last: ", paras[-1][:100])
        try:
            pics = pictures(t)
        except Exception as e:
            pics = []; print("   !! commons:", e)
        for p in pics:
            print("   picture:", p[0][:90], "|", p[1][:40])
        if not pics:
            print("   (no public-domain picture found — text only)")
        if dry:
            continue
        io.open("public/books/novel/%s.fb2" % t["slug"], "w", encoding="utf-8", newline="\n").write(fb2(t, paras, pics))
        e = by.get(t["slug"])
        if e is None:
            e = {"slug": t["slug"]}; idx.append(e); by[t["slug"]] = e
        e.update({"filename": "novel/%s.fb2" % t["slug"], "title": t["title"], "author": t["author"],
                  "category": "Fairytales", "public": True, "blurb": t["blurb"], "words": words,
                  "_note": "Text: https://ru.wikisource.org/wiki/" + urllib.parse.quote(src.replace(" ", "_"))})
        if pics:
            e["cover"] = url_for(pics[0][0], 500)
        done.append(t["slug"])
    if done and not dry:
        io.open(MANIFEST, "w", encoding="utf-8").write(json.dumps(idx, ensure_ascii=False, indent=2) + "\n")
        subprocess.run([sys.executable, "tools/gen_stress_maps.py"])
    print("\n%d tale(s) %s%s" % (len(done) if not dry else len([t for t in tales if not only or t["slug"] in only]) - len(failed),
                                "added/updated" if not dry else "checked",
                                ("; FAILED: " + " ".join(failed)) if failed else ""))


if __name__ == "__main__":
    main()
