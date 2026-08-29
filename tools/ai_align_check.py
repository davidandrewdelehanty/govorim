#!/usr/bin/env python3
"""Have a model read the pairings the free checks cannot settle.

tools/scan_alignment.py finds files where the English does not belong beside
the Russian, and tools/realign_by_names.py fixes the ones with a mechanical
cause. What is left — around 195 files — is misaligned in no pattern a script
can undo, and the only way to know what is wrong with each is to read it.

This sends those files to Claude Haiku through the Batch API, in windows of
consecutive rows, and turns the answers into a ranked report. Windows, not
single rows, because drift is invisible one row at a time and obvious across
ten.

    export ANTHROPIC_API_KEY=sk-ant-...          # your Console key
    python3 tools/ai_align_check.py --build      # no key needed: what it would send
    python3 tools/ai_align_check.py --build --limit 20 --submit --wait --report
    python3 tools/ai_align_check.py --submit --wait --report

--build writes the requests and prints what they will cost before anything is
sent. --limit takes the worst N windows, which is the way to spend twenty cents
finding out whether the whole run is worth eight dollars.

A Console key is separate from a Claude subscription and is billed separately;
a Pro or Max plan does not include API access.
"""
import argparse, glob, io, json, os, re, sys, time, urllib.error, urllib.request

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from scan_alignment import BOOKS, INDEX, chapters, score_file

HERE = os.path.dirname(os.path.abspath(__file__))
REQS = os.path.join(HERE, "ai-align-requests.jsonl")
STATE = os.path.join(HERE, "ai-align-batch.json")
MAP = os.path.join(HERE, "ai-align-map.json")
OUT = os.path.join(HERE, "ai-align-findings.json")

MODEL = "claude-haiku-4-5-20251001"
MODELS = {"haiku": ("claude-haiku-4-5-20251001", 0.50, 2.50),
          "sonnet": ("claude-sonnet-5", 1.00, 5.00)}
# A Message Batch takes at most 100,000 requests or 256 MB, whichever comes
# first. The whole library is about 9,000 windows, so the count is never the
# problem and the size very nearly never is — but a batch refused for size
# after a long upload is a miserable way to find out.
MAX_BYTES = 240 * 1024 * 1024
API = "https://api.anthropic.com/v1/messages/batches"
WINDOW, OVERLAP = 12, 2
IN_RATE, OUT_RATE = 0.50, 2.50        # batch pricing, $/MTok

SYSTEM = """You check a parallel-reading app. Each Russian paragraph of a work has been
paired with an English paragraph by index. Say whether the PAIRING is right.
You are not judging translation quality.

You get a numbered window of consecutive pairs from one chapter. Judge the
window as a whole — the consecutive rows are your evidence.

NOT errors. Do not report these:
- A loose or Victorian translation (Garnett, the Maudes). Wording, idiom and
  sentence order differ freely; that is what those translations are.
- One side much longer, including 2:1 or 3:1 compression, where the content
  still corresponds.
- A verse translation that keeps the sense but not the line structure.
- A blank or missing English row.
- Names spelled differently: Alexey/Aleksei, Sonia/Sonya, Nicholas/Nikolai.

Errors. Report only these:
- DIFFERENT_WORK: the English is another story or novel entirely — different
  characters, setting, events. Happens when an anthology was sliced wrongly.
- OFFSET: right work, shifted. Row N's English belongs to row N+k. Give k
  (positive = the English runs ahead). It shows as a RUN of rows each matching
  a fixed distance away, not one odd row.
- PARTIAL: correct for part of the window, breaking part way. Give the row.
- SCRAMBLED: right work, rows out of order with no fixed pattern.

If you cannot tell — too little text, too free a translation, a window of bare
dialogue — answer UNSURE. UNSURE is worth more than a guess: a person reads
these flags, and a wrong flag costs more than a missing one.

Reply with JSON and nothing else:
{"verdict":"OK|DIFFERENT_WORK|OFFSET|PARTIAL|SCRAMBLED|UNSURE",
 "offset":<int or null>,"breaks_at":<row or null>,
 "confidence":"high|medium|low",
 "why":"<one sentence, max 25 words, naming the specific mismatch>"}"""


def tokens(ru_chars, en_chars):
    """Cyrillic runs about 2.6 characters to the token, English about 4."""
    return ru_chars / 2.6 + en_chars / 4.0


def windows_for(book, chs, path):
    ci = int(re.match(r"(\d+)", os.path.basename(path)).group(1)) - 1
    if not (0 <= ci < len(chs)):
        return []
    m = json.load(io.open(path, encoding="utf-8"))
    idx = sorted(int(k) for k in m
                 if k != "_note" and str(k).lstrip("-").isdigit())
    rows = []
    for pos, i in enumerate(idx):
        if i >= len(chs[ci]):
            continue
        nxt = idx[pos + 1] if pos + 1 < len(idx) else len(chs[ci])
        ru = " ".join(chs[ci][i:min(nxt, len(chs[ci]))]).strip()
        en = str(m[str(i)]).strip()
        if ru and en:
            rows.append((i, ru, en))
    out, step = [], WINDOW - OVERLAP
    for s in range(0, max(1, len(rows) - OVERLAP), step):
        chunk = rows[s:s + WINDOW]
        if len(chunk) >= 4:
            out.append(chunk)
    return out


def build(limit, floor, min_names, model=MODEL, in_rate=IN_RATE, out_rate=OUT_RATE):
    cat = json.load(io.open(INDEX, encoding="utf-8"))
    picked = []
    for b in cat:
        d = b.get("parallelEn")
        if not d or d == "bible-kjv":
            continue
        chs = chapters(os.path.join(BOOKS, b["filename"]))
        if not chs:
            continue
        for f in sorted(glob.glob(os.path.join(BOOKS, d, "[0-9]*.json"))):
            ci = int(re.match(r"(\d+)", os.path.basename(f)).group(1)) - 1
            if not (0 <= ci < len(chs)):
                continue
            r = score_file(chs[ci], json.load(io.open(f, encoding="utf-8")))
            on, placed = r.get("onrow"), r.get("placed", 0)
            if on is None or placed < min_names or on >= floor:
                continue
            picked.append((on, b, chs, f))
    picked.sort(key=lambda t: t[0])

    reqs, index, ru_chars, en_chars = [], {}, 0, 0
    for on, b, chs, f in picked:
        for w in windows_for(b, chs, f):
            lines = []
            for i, ru, en in w:
                lines.append("[%d] RU: %s" % (i, ru))
                lines.append("[%d] EN: %s" % (i, en))
                ru_chars += len(ru)
                en_chars += len(en)
            head = "Work: %s%s\nFile: %s/%s, rows %d–%d\n\n" % (
                b.get("title", ""),
                (" — " + b["author"]) if b.get("author") else "",
                b["parallelEn"], os.path.basename(f), w[0][0], w[-1][0])
            # custom_id takes letters, digits, dashes and underscores only —
            # a folder name with a dot in it is a 400 with no other symptom. The
            # real identity lives in a map beside the requests.
            cid = "w%05d" % len(reqs)
            index[cid] = {"dir": b["parallelEn"], "file": os.path.basename(f),
                          "row": w[0][0]}
            reqs.append({
                "custom_id": cid,
                "params": {
                    "model": model,
                    "max_tokens": 200,
                    "temperature": 0,
                    # No cache_control: Haiku 4.5 will not cache a prompt under
                    # 4,096 tokens and this system prompt is a sixth of that, so
                    # the marker bought nothing.
                    "system": SYSTEM,
                    "messages": [{"role": "user", "content": head + "\n".join(lines)}],
                },
            })
            if limit and len(reqs) >= limit:
                break
        if limit and len(reqs) >= limit:
            break

    with io.open(REQS, "w", encoding="utf-8") as fh:
        for r in reqs:
            fh.write(json.dumps(r, ensure_ascii=False) + "\n")
    json.dump(index, io.open(MAP, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    tin = tokens(ru_chars, en_chars) + len(reqs) * 60
    tout = len(reqs) * 70
    cost = tin / 1e6 * in_rate + tout / 1e6 * out_rate
    print("%d file(s) need reading, %d window(s) to send" % (len(picked), len(reqs)))
    print("about %.1fM input tokens and %.0fk output" % (tin / 1e6, tout / 1e3))
    print("estimated cost at batch rates on %s: $%.2f" % (model, cost))
    print("wrote %s" % REQS)
    return len(reqs)


# Overloaded, rate-limited, or a blip on the way — none of which mean the
# request was wrong. A poll loop that quits on the first 503 abandons a batch
# that is running perfectly well on the other end.
TRANSIENT = (408, 409, 429, 500, 502, 503, 504, 529)


def call(url, data=None, key=None, method=None, tries=6):
    for attempt in range(tries):
        try:
            return _once(url, data, key, method)
        except _Transient as t:
            if attempt == tries - 1:
                sys.exit("the API kept failing (HTTP %d): %s" % (t.code, t.msg))
            naptime = min(60, 2 ** attempt * 5)
            print("  ...HTTP %d (%s) — retrying in %ds" % (t.code, t.msg[:60], naptime))
            time.sleep(naptime)


class _Transient(Exception):
    def __init__(self, code, msg):
        self.code, self.msg = code, msg


def _once(url, data=None, key=None, method=None):
    req = urllib.request.Request(url, data=data, method=method)
    req.add_header("x-api-key", key)
    req.add_header("anthropic-version", "2023-06-01")
    req.add_header("content-type", "application/json")
    try:
        with urllib.request.urlopen(req, timeout=120) as r:
            return r.read()
    except urllib.error.HTTPError as e:
        # The API says what is wrong in the body. Swallowing it and showing a
        # bare "HTTP Error 400: Bad Request" wastes everyone's afternoon.
        body = ""
        try:
            body = e.read().decode("utf-8", "replace")
        except Exception:
            pass
        try:
            msg = json.loads(body)["error"]["message"]
        except Exception:
            msg = body[:600] or str(e.reason)
        if e.code in TRANSIENT:
            raise _Transient(e.code, msg)
        sys.exit("the API refused the request (HTTP %d):\n  %s" % (e.code, msg))
    except urllib.error.URLError as e:
        raise _Transient(0, str(e.reason))


def submit(key):
    reqs = [json.loads(l) for l in io.open(REQS, encoding="utf-8") if l.strip()]
    if not reqs:
        sys.exit("no requests — run --build first")
    body = json.dumps({"requests": reqs}).encode("utf-8")
    if len(body) > MAX_BYTES:
        sys.exit("this batch is %.0f MB and the limit is 256 MB — narrow it with\n"
                 "--floor or --limit and run it in parts." % (len(body) / 1e6))
    got = json.loads(call(API, body, key))
    # Keep the id-to-file map WITH the batch. Rebuilding the requests for a
    # different run replaces the map on disk, and results fetched against the
    # wrong map are not an error — they are wrong answers with confident
    # filenames on them.
    got["index"] = json.load(io.open(MAP, encoding="utf-8"))
    json.dump(got, io.open(STATE, "w", encoding="utf-8"), indent=1)
    print("submitted %d window(s) as %s" % (len(reqs), got["id"]))
    return got["id"]


def wait(key, every=30):
    bid = json.load(io.open(STATE, encoding="utf-8"))["id"]
    while True:
        got = json.loads(call(API + "/" + bid, key=key))
        counts = got.get("request_counts", {})
        got["index"] = json.load(io.open(STATE, encoding="utf-8")).get("index")
        print("  %s  %s" % (got.get("processing_status"),
                            " ".join("%s=%s" % kv for kv in sorted(counts.items()))))
        if got.get("processing_status") == "ended":
            json.dump(got, io.open(STATE, "w", encoding="utf-8"), indent=1)
            return got
        time.sleep(every)


def fetch(key):
    saved = json.load(io.open(STATE, encoding="utf-8"))
    got = saved
    url = got.get("results_url")
    if not url:
        got = json.loads(call(API + "/" + saved["id"], key=key))
        url = got.get("results_url")
    if not url:
        sys.exit("the batch has no results yet")
    raw = call(url, key=key).decode("utf-8")
    index = saved.get("index") or json.load(io.open(MAP, encoding="utf-8"))
    found = []
    for line in raw.splitlines():
        if not line.strip():
            continue
        r = json.loads(line)
        res = r.get("result", {})
        if res.get("type") != "succeeded":
            continue
        text = "".join(c.get("text", "") for c in res["message"]["content"])
        m = re.search(r"\{.*\}", text, re.S)
        if not m:
            continue
        try:
            v = json.loads(m.group(0))
        except ValueError:
            continue
        who = index.get(r["custom_id"])
        if not who:
            continue
        v.update(who)
        found.append(v)
    json.dump(found, io.open(OUT, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print("read %d verdict(s) -> %s" % (len(found), OUT))
    return found


def report(found=None):
    found = found if found is not None else json.load(io.open(OUT, encoding="utf-8"))
    bad = [v for v in found if v.get("verdict") not in ("OK", "UNSURE")]
    unsure = [v for v in found if v.get("verdict") == "UNSURE"]
    order = {"DIFFERENT_WORK": 0, "SCRAMBLED": 1, "OFFSET": 2, "PARTIAL": 3}
    conf = {"high": 0, "medium": 1, "low": 2}
    bad.sort(key=lambda v: (order.get(v["verdict"], 9), conf.get(v.get("confidence"), 9)))
    print("%d window(s) read: %d wrong, %d unsure, %d fine\n"
          % (len(found), len(bad), len(unsure), len(found) - len(bad) - len(unsure)))
    print("%-24s %-10s %5s %-14s %-6s %s"
          % ("folder", "file", "row", "verdict", "conf", "why"))
    for v in bad:
        print("%-24s %-10s %5d %-14s %-6s %s"
              % (v["dir"][:24], v["file"], v["row"], v["verdict"],
                 (v.get("confidence") or "")[:6], (v.get("why") or "")[:70]))
    byfile = {}
    for v in bad:
        byfile.setdefault((v["dir"], v["file"]), []).append(v)
    print("\n%d file(s) with at least one bad window" % len(byfile))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--build", action="store_true")
    ap.add_argument("--submit", action="store_true")
    ap.add_argument("--wait", action="store_true")
    ap.add_argument("--fetch", action="store_true")
    ap.add_argument("--report", action="store_true")
    ap.add_argument("--limit", type=int, default=0, help="send only the worst N windows")
    ap.add_argument("--floor", type=float, default=0.80,
                    help="read files scoring below this on names (default 0.80)")
    ap.add_argument("--min-names", type=int, default=4)
    ap.add_argument("--model", choices=sorted(MODELS), default="haiku",
                    help="haiku is the cheap sweep; sonnet judges literary "
                         "prose better and costs about twice as much")
    ap.add_argument("--everything", action="store_true",
                    help="read every paired file, not only the ones that fail "
                         "the free checks")
    a = ap.parse_args()
    if not any((a.build, a.submit, a.wait, a.fetch, a.report)):
        ap.error("nothing to do — try --build")

    key = os.environ.get("ANTHROPIC_API_KEY")
    if (a.submit or a.wait or a.fetch) and not key:
        sys.exit("ANTHROPIC_API_KEY is not set. A Console key is separate from a\n"
                 "Claude subscription: https://platform.claude.com/settings/keys")

    model, in_rate, out_rate = MODELS[a.model]
    if a.everything:
        a.floor, a.min_names = 1.1, 0
    if a.build:
        build(a.limit, a.floor, a.min_names, model, in_rate, out_rate)
    if a.submit:
        submit(key)
    if a.wait:
        wait(key)
    if a.fetch or (a.wait and a.report):
        fetch(key)
    if a.report:
        report()
    return 0


if __name__ == "__main__":
    sys.exit(main())
