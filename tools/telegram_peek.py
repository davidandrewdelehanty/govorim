#!/usr/bin/env python3
"""Find the years of the undated textbooks without downloading them.

tools/telegram_textbooks.py lists a channel's files; most give no year in the
name. The year (and the authors) are printed on the title page, and Soviet
books repeat them in the imprint on the LAST page («Подписано к печати…»,
тираж, издательство, год). So this fetches only those two ends of each file —
a few megabytes, never the whole book — reads their text layer, or OCRs them
when the book is a scan, and writes what it finds.

Only Russian-language and humanities books are looked at (language, reading,
literature, history, art, music, philosophy, pedagogy), and each book once:
the channel posts many books several times, and reposts are skipped.

    sudo apt install tesseract-ocr tesseract-ocr-rus djvulibre-bin
    pip install telethon pymupdf
    python3 tools/telegram_peek.py              # resumable; Ctrl+C any time
    python3 tools/telegram_peek.py --max 20     # try a few first

Reads ~/telegram-textbooks/list.tsv (from telegram_textbooks.py) and writes
~/telegram-textbooks/peek.tsv: id, subject, likely year, every year seen,
the title-page text and the imprint text. Page images are kept in
~/telegram-textbooks/peek/<id>/ so a doubtful one can be looked at.
Uses the same TG_API_ID / TG_API_HASH and login as telegram_textbooks.py.
"""
import argparse
import asyncio
import csv
import io
import os
import re
import shutil
import struct
import subprocess
import sys
import zipfile
import zlib

try:
    from telethon import TelegramClient
    from telethon.errors import FloodWaitError
except ImportError:
    sys.exit("pip install telethon")
try:
    import fitz  # PyMuPDF
except ImportError:
    sys.exit("pip install pymupdf")
for tool in ("tesseract", "ddjvu", "djvutxt"):
    if not shutil.which(tool):
        sys.exit("missing %s:  sudo apt install tesseract-ocr tesseract-ocr-rus djvulibre-bin" % tool)

HOME = os.path.expanduser("~/telegram-textbooks")
SESSION = os.path.expanduser("~/.telegram/textbooks")
MB = 1024 * 1024
HEAD = 6 * MB          # bytes fetched from the start of a file
TAIL = 4 * MB          # and from the end

FOREIGN = re.compile(r"angl|англ|nemets|немец|frantsuz|француз|ispansk|испанск|latin|латин|"
                     r"italjan|итальян|kitajsk|китайск|hindi|хинди|urdu|урду|bengal|ukra[iї]n|tatar|татар", re.I)
SUBJECTS = [
    ("russian", r"russk|русск|bukvar|букв|azbuk|азбук|rodnaja|rodnoe|родн|chteni|чтени|hrestom|khrestom|хрестом|"
                r"grammat|граммат|orfograf|орфограф|pravopis|правопис|diktant|диктант|izlozhen|изложен|sochinen|сочинен|"
                r"razvitierechi|развити[ея] речи|propis|пропис|fonetik|фонетик|punktuats|пунктуац|slovoobraz|морфолог|morfologijaisint"),
    ("literature", r"literatur|литератур|poezi|поэз|poet|поэт|skazk|сказк|basn|басн|vneklassnoechteni|внеклассное чтени"),
    ("history", r"istori|истор|drevn|древн|srednihvek|средних век|arheolog|археолог|kraeved|краевед|letopis|летопис"),
    ("arts", r"iskusstv|искусств|muzyk|музык|teatr|театр|risovani|рисован|zhivopis|живопис|folklor|фольклор|"
             r"narodnajarezb|народн|ornament|орнамент"),
    ("humanities", r"filosof|философ|logik|логик|etik|этик|estetik|эстетик|obschestvoved|обществовед|pedagog|педагог|"
                   r"metodikaprepodavanijaliterat|metodikapravopis|psiholog|психолог|mifolog|мифолог|kulturolog|культуролог|jazykozn|языкозн"),
]
YEAR = re.compile(r"(?<!\d)(1[789]\d\d)(?!\d)")
IMPRINT = re.compile(r"тираж|подписано|сдано в набор|учпедгиз|издательств|госиздат|просвещени|типограф|"
                     r"заказ|цена|изд\.|печ\. л|уч\.-изд", re.I)


SCIENCE = re.compile(r"arifmet|арифмет|matemat|математ|fizik|физик|himi|хими|botanik|ботаник|zoolog|зоолог|"
                     r"algebr|алгебр|geometr|геометр|oruzh|оруж|astronom|астроном|biolog|биолог|anatom|анатом|"
                     r"geograf|географ|radio|радио|tehnik|техник|sport|спорт|fizkult|физкульт", re.I)


def subject_of(name, caption):
    t = name + " " + caption
    if SCIENCE.search(t) and not re.search(r"russk|русск|literatur|литератур|istori|истор", t, re.I):
        return None
    if FOREIGN.search(t) and not re.search(r"russk|русск", t, re.I):
        return None
    for subj, rx in SUBJECTS:
        if re.search(rx, t, re.I):
            return subj
    return None


def stem(name):
    s = name.rsplit(".", 1)[0]
    return re.sub(r"\d+$", "", s).lower()


async def fetch(client, msg, ranges, size):
    """The given byte ranges of the file, as one sparse buffer of full size."""
    buf = bytearray()
    parts = {}
    req = 512 * 1024
    for start, length in ranges:
        start = max(0, start)
        length = min(length, size - start)
        if length <= 0:
            continue
        a = start - start % req                    # Telegram wants aligned offsets
        n = (start + length - a + req - 1) // req
        data = bytearray()
        while True:
            try:
                async for chunk in client.iter_download(msg.media, offset=a, request_size=req, limit=n):
                    data += chunk
                break
            except FloodWaitError as e:
                print("   pause %ds (Telegram)" % e.seconds, flush=True)
                await asyncio.sleep(e.seconds + 1)
        parts[a] = bytes(data)
    out = bytearray(size)
    for a, d in parts.items():
        out[a:a + len(d)] = d[:max(0, size - a)]
    return bytes(out)


def ocr(png):
    r = subprocess.run(["tesseract", png, "-", "-l", "rus+eng", "--psm", "3"],
                       capture_output=True, text=True, timeout=180)
    return r.stdout


def pdf_pages(data, outdir):
    """Text of the first two pages and the last two, OCR when there is no text."""
    texts = []
    try:
        doc = fitz.open(stream=data, filetype="pdf")
    except Exception:
        return texts
    n = doc.page_count
    for i in sorted({0, 1, n - 2, n - 1} - {-1, -2}) if n else []:
        if i >= n:
            continue
        try:
            page = doc.load_page(i)
            t = page.get_text().strip()
            if len(t) < 40:
                png = os.path.join(outdir, "p%d.png" % (i + 1))
                page.get_pixmap(dpi=200).save(png)
                t = ocr(png)
            texts.append((i + 1, t))
        except Exception:
            continue
    return texts


def djvu_pages(path, outdir):
    texts = []
    r = subprocess.run(["djvused", path, "-e", "n"], capture_output=True, text=True)
    try:
        n = int(r.stdout.strip())
    except ValueError:
        n = 1
    for p in sorted({1, 2, n - 1, n} - {0, -1}):
        t = subprocess.run(["djvutxt", "--page=%d" % p, path], capture_output=True, text=True).stdout.strip()
        if len(t) < 40:
            tif = os.path.join(outdir, "p%d.tif" % p)
            subprocess.run(["ddjvu", "-format=tiff", "-page=%d" % p, "-scale=200", path, tif],
                           capture_output=True)
            t = ocr(tif) if os.path.exists(tif) and os.path.getsize(tif) > 0 else ""
        texts.append((p, t))
    return texts


def djvu_ranges(head, size):
    """A bundled DjVu lists every page's offset in its DIRM chunk at the
    start; return ranges covering the first two pages and the last two."""
    try:
        if head[:4] != b"AT&T" or head[12:16] != b"DJVM":
            return []
        pos = 16
        if head[pos:pos + 4] != b"DIRM":
            return []
        nfiles = struct.unpack(">H", head[pos + 9:pos + 11])[0]
        offs = [struct.unpack(">I", head[pos + 11 + 4 * k:pos + 15 + 4 * k])[0] for k in range(nfiles)]
        offs.append(size)
        want = sorted({0, 1, nfiles - 2, nfiles - 1} - {-1, -2})
        return [(offs[k], offs[k + 1] - offs[k]) for k in want if k < nfiles]
    except Exception:
        return []


async def peek_one(client, msg, name, size, outdir):
    ext = name.rsplit(".", 1)[-1].lower()
    path = os.path.join(outdir, "file." + ext)
    if ext == "pdf":
        data = await fetch(client, msg, [(0, HEAD), (size - TAIL, TAIL)], size)
        return pdf_pages(data, outdir)
    if ext in ("djvu", "djv"):
        head = await fetch(client, msg, [(0, 256 * 1024)], size)
        extra = djvu_ranges(head, size)
        data = await fetch(client, msg, [(0, 256 * 1024)] + extra, size)
        open(path, "wb").write(data)
        return djvu_pages(path, outdir)
    if ext == "zip":
        # The zip's own directory sits at its end: read it, then take the
        # first PDF or DjVu inside (or the first and last page images).
        tail = await fetch(client, msg, [(size - 2 * MB, 2 * MB)], size)
        try:
            z = zipfile.ZipFile(io.BytesIO(tail))
            infos = z.infolist()
        except Exception:
            return []
        books = [i for i in infos if i.filename.lower().endswith((".pdf", ".djvu", ".djv"))]
        imgs = sorted([i for i in infos if i.filename.lower().endswith((".jpg", ".jpeg", ".png", ".tif", ".tiff"))],
                      key=lambda i: i.filename)
        texts = []
        if books:
            inner = max(books, key=lambda i: i.file_size)
            hdr = 30 + len(inner.filename.encode()) + len(inner.extra) + 64
            take = min(inner.compress_size, 12 * MB)
            raw = await fetch(client, msg, [(inner.header_offset, hdr + take)], size)
            seg = raw[inner.header_offset:inner.header_offset + hdr + take]
            fn_len, ex_len = struct.unpack("<HH", seg[26:30])
            body = seg[30 + fn_len + ex_len:]
            if inner.compress_type == zipfile.ZIP_DEFLATED:
                body = zlib.decompressobj(-15).decompress(body)
            ipath = os.path.join(outdir, "inner." + inner.filename.rsplit(".", 1)[-1].lower())
            open(ipath, "wb").write(body)
            if ipath.endswith(".pdf"):
                texts = pdf_pages(body, outdir)
            else:
                texts = djvu_pages(ipath, outdir)
        elif imgs:
            for k, inf in enumerate([imgs[0], imgs[-1]] if len(imgs) > 1 else imgs):
                hdr = 30 + len(inf.filename.encode()) + len(inf.extra) + 64
                raw = await fetch(client, msg, [(inf.header_offset, hdr + inf.compress_size)], size)
                seg = raw[inf.header_offset:]
                fn_len, ex_len = struct.unpack("<HH", seg[26:30])
                body = seg[30 + fn_len + ex_len:30 + fn_len + ex_len + inf.compress_size]
                if inf.compress_type == zipfile.ZIP_DEFLATED:
                    body = zlib.decompressobj(-15).decompress(body)
                img = os.path.join(outdir, "img%d%s" % (k, os.path.splitext(inf.filename)[1]))
                open(img, "wb").write(body)
                texts.append((k, ocr(img)))
        return texts
    return []


def summarise(texts):
    alltext = "\n".join(t for _, t in texts)
    years = sorted({int(y) for y in YEAR.findall(alltext) if 1750 <= int(y) <= 1999})
    imprint_years = []
    for _, t in texts:
        for line in t.splitlines():
            if IMPRINT.search(line):
                imprint_years += [int(y) for y in YEAR.findall(line) if 1750 <= int(y) <= 1999]
    likely = max(imprint_years) if imprint_years else (max(years) if years else "")
    first = re.sub(r"\s+", " ", texts[0][1]).strip()[:400] if texts else ""
    imp = " | ".join(re.sub(r"\s+", " ", l).strip() for _, t in texts for l in t.splitlines() if IMPRINT.search(l))[:400]
    return likely, years, first, imp


async def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--channel", default="Советские учебники")
    ap.add_argument("--max", type=int, default=0, help="stop after this many books")
    a = ap.parse_args()
    api_id, api_hash = os.environ.get("TG_API_ID"), os.environ.get("TG_API_HASH")
    if not api_id or not api_hash:
        sys.exit("Set TG_API_ID and TG_API_HASH first.")

    rows = list(csv.DictReader(open(os.path.join(HOME, "list.tsv"), encoding="utf-8"), delimiter="\t"))
    todo, seen = [], set()
    for r in rows:
        if r["year?"]:
            continue
        subj = subject_of(r["file"], r["caption"])
        if not subj or stem(r["file"]) in seen:
            continue
        if not r["file"].lower().endswith((".pdf", ".djvu", ".djv", ".zip")):
            continue
        seen.add(stem(r["file"]))
        todo.append((int(r["id"]), subj, r["file"]))
    out_path = os.path.join(HOME, "peek.tsv")
    done = set()
    if os.path.exists(out_path):
        done = {int(l.split("\t")[0]) for l in open(out_path, encoding="utf-8") if l[:1].isdigit()}
    else:
        open(out_path, "w", encoding="utf-8").write("id\tsubject\tlikely_year\tall_years\tfile\ttitle_page\timprint\n")
    todo = [t for t in todo if t[0] not in done]
    if a.max:
        todo = todo[:a.max]
    print("%d books to peek at (%d already done)" % (len(todo), len(done)), flush=True)

    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    from telegram_textbooks import find_channel
    async with TelegramClient(SESSION, int(api_id), api_hash) as client:
        chan = await find_channel(client, a.channel)
        for k, (mid, subj, name) in enumerate(todo, 1):
            outdir = os.path.join(HOME, "peek", str(mid))
            os.makedirs(outdir, exist_ok=True)
            try:
                msg = await client.get_messages(chan, ids=mid)
                texts = await peek_one(client, msg, name, msg.file.size, outdir) if msg and msg.file else []
            except Exception as e:
                texts = []
                print("   !! %s" % e, flush=True)
            for f in os.listdir(outdir):          # keep the page images, not the file pieces
                if f.startswith(("file.", "inner.")):
                    os.remove(os.path.join(outdir, f))
            likely, years, first, imp = summarise(texts)
            print("[%d/%d] %-5s %-10s %s" % (k, len(todo), likely or "?", subj, name[:60]), flush=True)
            with open(out_path, "a", encoding="utf-8") as f:
                f.write("\t".join([str(mid), subj, str(likely), " ".join(map(str, years)), name,
                                   first.replace("\t", " "), imp.replace("\t", " ")]) + "\n")
            await asyncio.sleep(1.5)


if __name__ == "__main__":
    asyncio.run(main())
