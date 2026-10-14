#!/usr/bin/env python3
"""List, then download, the textbooks posted to a Telegram channel.

Logs in as YOUR Telegram account (Telethon) and reads a channel you have
joined. By default it only LISTS what is there — every file with its name,
size, date, a year guessed from the name or caption, and the message id — so
you can choose before anything is fetched.

    # once: keys from https://my.telegram.org → API development tools
    pip install telethon
    export TG_API_ID=1234567
    export TG_API_HASH=0123456789abcdef0123456789abcdef

    python3 tools/telegram_textbooks.py                      # list → ~/telegram-textbooks/list.tsv
    python3 tools/telegram_textbooks.py --download --year-max 1930
    python3 tools/telegram_textbooks.py --download --ids 512 513 600
    python3 tools/telegram_textbooks.py --download --match "Киселёв|Ушинский"

The first run asks for your phone number and the login code Telegram sends;
the session is then kept in ~/.telegram/ so later runs do not ask again.
The keys and the session are yours: they are read from your environment and
your home folder, never written into this repository.

Files land in ~/telegram-textbooks/, outside the repo. Nothing here decides
what may be published: a file only goes on the sites after its authors'
dates are checked (Russia: all authors died by 1955; Samovar also needs it
published in 1930 or earlier).

Re-running is safe — a file already downloaded at the right size is skipped —
and Telegram's "wait N seconds" answers are waited out, not treated as errors.
"""
import argparse
import asyncio
import csv
import os
import re
import sys
import time

try:
    from telethon import TelegramClient
    from telethon.errors import FloodWaitError
    from telethon.tl.types import DocumentAttributeFilename
except ImportError:
    sys.exit("Telethon is not installed:  pip install telethon")

CHANNEL = "Советские учебники"
OUT = os.path.expanduser("~/telegram-textbooks")
SESSION = os.path.expanduser("~/.telegram/textbooks")
KEEP = (".pdf", ".djvu", ".djv", ".fb2", ".epub", ".doc", ".docx", ".rtf", ".txt", ".zip", ".rar", ".7z")
YEAR = re.compile(r"(?<!\d)(1[89]\d\d)(?!\d)")


def norm(s):
    return re.sub(r"[^a-zа-я0-9]+", " ", (s or "").lower().replace("ё", "е")).strip()


def file_name(msg):
    doc = msg.document
    if not doc:
        return None
    for a in doc.attributes:
        if isinstance(a, DocumentAttributeFilename):
            return a.file_name
    return "message-%d%s" % (msg.id, msg.file.ext or "")


def guess_year(*texts):
    years = [int(y) for t in texts for y in YEAR.findall(t or "") if 1800 <= int(y) <= 1999]
    return min(years) if years else ""


async def find_channel(client, name):
    """By @username or t.me link if given, otherwise by title among the
    channels you have joined — loosely, so a typo or ё/е does not matter."""
    if name.startswith("@") or "t.me/" in name:
        return await client.get_entity(name)
    want = norm(name)
    best, best_score = None, 0.0
    import difflib
    async for d in client.iter_dialogs():
        if not d.is_channel:
            continue
        score = difflib.SequenceMatcher(None, want, norm(d.name)).ratio()
        if want and want in norm(d.name):
            score = max(score, 0.95)
        if score > best_score:
            best, best_score = d, score
    if not best or best_score < 0.6:
        sys.exit("No joined channel looks like «%s». Join it in Telegram first, "
                 "or pass its @username / t.me link with --channel." % name)
    print("channel: %s  (match %.0f%%)" % (best.name, best_score * 100))
    return best.entity


async def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--channel", default=CHANNEL, help="title, @username or t.me link")
    ap.add_argument("--out", default=OUT)
    ap.add_argument("--download", action="store_true", help="fetch files (default: list only)")
    ap.add_argument("--ids", type=int, nargs="*", help="only these message ids")
    ap.add_argument("--match", help="only files whose name or caption matches this regex")
    ap.add_argument("--year-max", type=int, help="only files with a guessed year at or before this")
    ap.add_argument("--limit", type=int, default=0, help="read at most this many messages")
    ap.add_argument("--pause", type=float, default=2.0, help="seconds between downloads")
    a = ap.parse_args()

    api_id, api_hash = os.environ.get("TG_API_ID"), os.environ.get("TG_API_HASH")
    if not api_id or not api_hash:
        sys.exit("Set TG_API_ID and TG_API_HASH first (from https://my.telegram.org).")
    os.makedirs(os.path.dirname(SESSION), exist_ok=True)
    os.makedirs(a.out, exist_ok=True)

    async with TelegramClient(SESSION, int(api_id), api_hash) as client:
        chan = await find_channel(client, a.channel)
        rows = []
        async for msg in client.iter_messages(chan, limit=a.limit or None):
            name = file_name(msg)
            if not name or not name.lower().endswith(KEEP):
                continue
            cap = (msg.message or "").replace("\n", " ").strip()
            rows.append({"id": msg.id, "file": name, "mb": round((msg.file.size or 0) / 1e6, 1),
                         "posted": msg.date.strftime("%Y-%m-%d"), "year": guess_year(name, cap),
                         "caption": cap[:300], "msg": msg})
        rows.reverse()                            # oldest post first

        listing = os.path.join(a.out, "list.tsv")
        with open(listing, "w", encoding="utf-8", newline="") as f:
            w = csv.writer(f, delimiter="\t")
            w.writerow(["id", "year?", "MB", "posted", "file", "caption"])
            for r in rows:
                w.writerow([r["id"], r["year"], r["mb"], r["posted"], r["file"], r["caption"]])
        print("%d files listed → %s" % (len(rows), listing))
        dated = [r for r in rows if r["year"]]
        print("   %d with a year in the name or caption, %d of them 1930 or earlier"
              % (len(dated), sum(1 for r in dated if r["year"] <= 1930)))
        if not a.download:
            print("\nNothing downloaded. Read the list, then add --download with --ids, --match or --year-max.")
            return

        pick = rows
        if a.ids:
            pick = [r for r in pick if r["id"] in set(a.ids)]
        if a.match:
            rx = re.compile(a.match, re.I)
            pick = [r for r in pick if rx.search(r["file"]) or rx.search(r["caption"])]
        if a.year_max:
            pick = [r for r in pick if r["year"] and r["year"] <= a.year_max]
        print("\n%d to download → %s" % (len(pick), a.out))
        for i, r in enumerate(pick, 1):
            dest = os.path.join(a.out, "%d - %s" % (r["id"], re.sub(r'[\\/:*?"<>|]', "_", r["file"])))
            size = r["msg"].file.size or 0
            if os.path.exists(dest) and os.path.getsize(dest) == size:
                print("[%d/%d] have   %s" % (i, len(pick), r["file"]))
                continue
            while True:
                try:
                    print("[%d/%d] fetch  %s  (%.1f MB)" % (i, len(pick), r["file"], r["mb"]), flush=True)
                    await client.download_media(r["msg"], file=dest)
                    break
                except FloodWaitError as e:
                    print("   Telegram asks for a %ds pause — waiting" % e.seconds, flush=True)
                    time.sleep(e.seconds + 1)
            time.sleep(a.pause)
        print("\ndone.")


if __name__ == "__main__":
    asyncio.run(main())
