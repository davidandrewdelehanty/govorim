#!/usr/bin/env python3
"""Remove the source / imprint / e-library lines that some FB2s carry at the
start or end of their text («Собрание сочинений в тридцати томах»: …,
«Источник текста: …», «Подготовка текста …», URLs, «Электронная версия …»).
Only the reader's own text should be on the page.

The lines are listed per book below (reader paragraph indices in the first
chapter for HEAD, in the last chapter for TAIL), chosen by hand from a scan,
so titles, genre lines and dedications stay. Jump points
(audio-sync/<book>/NN.json) and parallel English (<dir>/NN.json) are re-keyed
so nothing slips out of line. Originals go to tools/format-orig/.

    python3 tools/strip_source_lines.py --dry
    python3 tools/strip_source_lines.py
    python3 tools/strip_source_lines.py --round2     # the lines found on a second look
"""
import io, json, os, re, shutil, sys
sys.path.insert(0, os.path.dirname(__file__))
from reader_chapters import reader_chapters

G30 = [0, 1]          # «Собрание сочинений в тридцати томах» + «Том N …»
HEAD = {
 "baryshnya-i-durak": [1, 2], "byk": G30, "v-teatre-i-tsirke": G30, "vassa-zheleznova-mat": [2, 3],
 "vragi": [1, 2], "deti-solntsa": [1, 2], "enblema": G30, "zametki-iz-dnevnika-vospominaniya": [2, 3],
 "zykovy": [1, 2], "iz-vospominaniy": G30, "iz-dnevnika": G30, "kak-ya-uchilsya": G30, "krazha": G30,
 "mamasha-kemskikh": G30, "misha": G30, "muzyka": G30, "nesoglasnyy": G30, "o-vrede-filosofii": [2, 3],
 "o-pervoy-lyubvi": [2, 3], "o-tarakanakh": G30, "oryol": G30, "pismo": G30, "pozhar": G30,
 "provodnik": [2, 3], "storozh": [2, 3], "teatralnoe": G30, "ubiytsy": G30, "falshivaya-moneta": [2, 3],
 "charli-men": [3, 4], "chudaki": [1, 2], "shornik-i-pozhar": G30, "ekzekutsiya": G30,
 "noch-nastupila-den-ugas": [1, 2], "duma": [1, 2, 3], "pugalo-leskov": [1],
 "khristos-v-gostyakh-u-muzhika": [0, 1], "les": [2, 3, 4, 5], "dokhodnoe-mesto": [2],
 "poslednyaya-zhertva": [2], "goryachee-serdtse": [2, 3, 4, 5], "semeynaya-khronika": [3, 4],
 "monastyrka": [1], "salamandra": [2, 3, 4, 5], "gorkaya-sudbina": [1, 2], "sokolinets": [3, 4],
 "gimnazisty": [2], "vlast-zemli": [0, 1, 2, 3, 4], "podlipovtsy": [1, 2], "kitay-gorod": [3],
 "listrigony": [1], "tot-kto-poluchaet-poshchyochiny": [1], "anatema": [1, 2, 3, 4],
 "ostrovityane": [2], "solntse-myortvykh": [1], "neupivaemaya-chasha": [1, 2, 3, 4, 5, 6],
 "shkola": [1, 2], "r-v-s": [1, 2], "sudba-barabanshchika": [0, 1], "tashkent-gorod-khlebnyy": [1],
 "smert-vazir-mukhtara": [3, 4, 5], "misteriya-buff": [3, 4, 5], "pepel": [1, 2],
}
# Found on a second look: lines that sat behind the first ones.
HEAD2 = {"semeynaya-khronika": [3, 4], "misteriya-buff": [3, 4, 5], "goryachee-serdtse": [2],
         "neupivaemaya-chasha": [1, 2, 3]}
# Last-chapter lines from a marker to the end (a «Ссылки» list, a repeated imprint).
TAIL_FROM = {"neupivaemaya-chasha": "{{***", "dnevnik-pisatelya-1876-god": "Ссылки",
             "dnevnik-pisatelya-1877-god": "Ссылки", "duma": "Дума («Печально я гляжу"}
# A whole last section that is nothing but links to other sites.
DROP_LAST_SECTION = {"stikhotvoreniya-pushkina-1809-1825": "Ссылки", "stikhotvoreniya-pushkina-1826-1836": "Ссылки"}
# Tail lines are found by their text, since the last chapter's length varies.
TAIL = re.compile(r"Мошков: Lib\.Ru|^Google book Изд\.|^РВБ:|^Иллюстрированное полное собрание сочинений М\. Ю\. Лермонтова|"
                  r"^Источник текста:|^О найденных в тексте ошибках|^Новые редакции текста можно получить|"
                  r"^Из библиотеки Олега Колесникова|^Первая публикация перевода:")


def plain(x):
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", "", x)).strip()


def main():
    dry = "--dry" in sys.argv
    idx = json.load(io.open("private/books/index.json", encoding="utf-8"))
    for b in idx:
        f = str(b.get("filename", ""))
        if not f.endswith(".fb2"):
            continue
        path = "public/books/" + f
        if not os.path.exists(path):
            continue
        slug = b.get("slug")
        try:
            chs, _ = reader_chapters(path)
        except Exception:
            continue
        if not chs:
            continue
        drop = {}                                   # chapter -> set of para indices
        heads = HEAD2 if "--round2" in sys.argv else HEAD
        if slug in heads:
            drop[0] = set(i for i in heads[slug] if i < len(chs[0]["paras"]))
        if "--round2" in sys.argv and slug in DROP_LAST_SECTION and chs[-1]["heading"].strip() == DROP_LAST_SECTION[slug]:
            raw = io.open(path, encoding="utf-8").read()
            i = raw.rfind("<section>"); j = raw.find("</section>", i) + len("</section>")
            if "<title><p>%s</p></title>" % DROP_LAST_SECTION[slug] in raw[i:j]:
                print("%-36s whole «%s» section" % (slug[:36], DROP_LAST_SECTION[slug]))
                if not dry:
                    io.open(path, "w", encoding="utf-8", newline="\n").write(raw[:i] + raw[j:])
            continue
        last = len(chs) - 1
        P = chs[last]["paras"]
        if "--round2" in sys.argv:
            tail = []
            if slug in TAIL_FROM:
                k = max((i for i, p in enumerate(P) if p.startswith(TAIL_FROM[slug])), default=None)
                if k is not None:
                    tail = list(range(k, len(P)))
        else:
            tail = [i for i, p in enumerate(P) if i >= len(P) - 4 and TAIL.search(p)]
        if tail:
            drop.setdefault(last, set()).update(tail)
        if not drop:
            continue
        texts = [(c, chs[c]["paras"][i]) for c in drop for i in sorted(drop[c])]
        print("%-36s %s" % (slug[:36], " | ".join(t[:50] for _, t in texts)))
        if dry:
            continue
        raw = io.open(path, encoding="utf-8").read()
        new = raw
        for c, t in texts:
            # remove the first <p>/<subtitle>/<v> whose text is exactly this line
            for m in re.finditer(r"<(p|subtitle|v)(?:\s[^>]*)?>(.*?)</\1>\s*", new, re.S):
                if plain(m.group(2)) == t:
                    new = new[:m.start()] + new[m.end():]
                    break
        keep = os.path.join("tools/format-orig", os.path.basename(path))
        if not os.path.exists(keep):
            os.makedirs("tools/format-orig", exist_ok=True); shutil.copy(path, keep)
        io.open(path, "w", encoding="utf-8", newline="\n").write(new)
        after, _ = reader_chapters(path)
        for c, gone in drop.items():
            if len(after) != len(chs) or len(after[c]["paras"]) != len(chs[c]["paras"]) - len(gone):
                print("   !! paragraph count off in chapter %d — check by hand" % c); continue
            def rekey(fn, offset_name):
                if not os.path.exists(fn):
                    return
                d = json.load(io.open(fn, encoding="utf-8"))
                out = {}
                for k, v in d.items():
                    if not k.isdigit():
                        out[k] = v; continue
                    i = int(k)
                    if i in gone:
                        continue
                    out[str(i - sum(1 for g in gone if g < i))] = v
                io.open(fn, "w", encoding="utf-8").write(json.dumps(out, ensure_ascii=False))
                print("   re-keyed", fn)
            base = os.path.basename(f).rsplit(".", 1)[0]
            rekey("public/books/audio-sync/%s/%02d.json" % (base, c), "sync")
            if b.get("parallelEn"):
                n = c + 1
                rekey("public/books/%s/%s.json" % (b["parallelEn"], ("%02d" % n) if n < 100 else str(n)), "en")


if __name__ == "__main__":
    main()
