# Govorim — Adding & Aligning a Book / Audiobook (Runbook)

How to add a new book to the library and, optionally, wire up a real-narration
audiobook with sentence-level highlighting. Written from the Тёмные аллеи build.
Follow the conventions exactly — most failures come from breaking one of them.

---

## 0. Golden rules (read first)

- **Two shells, strict split:**
  - **WSL** (Ubuntu) — all alignment / ML work. The `aeneas` conda env has
    `faster-whisper`, `aeneas`, and `ffmpeg` installed. Activate it:
    `source ~/miniforge3/bin/activate && conda activate aeneas`
  - **Git Bash** — **all git commands.** Never run git from WSL (it churns line
    endings / permissions on the Windows-checked-out repo and Vercel sees phantom diffs).
- **Paths:**
  - Git Bash: `/c/Users/david/projects/govorim-app`
  - WSL:      `/mnt/c/Users/david/projects/govorim-app` (same files, different mount)
- **Do not rely on browser downloads** to move helper files onto the machine —
  they land in unpredictable folders. Create files *in place* by pasting a heredoc
  (or `base64 -d` for anything with tricky characters). Examples are in §6.
- **Deploy = push to `main`.** Vercel auto-builds; live in ~1–2 min. Always
  hard-refresh (Ctrl+Shift+R) before testing, or you'll see a cached bundle/audio.

---

## 1. Repo layout & formats (quick reference)

```
public/books/
  index.json                       # library manifest (array of book entries)
  <name>.fb2                       # single-story book text
  novel/<name>-pN-chM.fb2|.txt     # novels (per-chapter text lives here)
  audio/
    <name>.mp3                     # audio (self-hosted) — also archive.org for big books
    <name>-ch1.json                # alignment for chapter 1 (sentence-level)
    <name>-pN-chM.json             # alignment per chapter for multi-chapter books
scripts/alignment/
  run_chapter.py                   # atomic aligner (one chapter)
  run_book.py                      # bulk driver (multi-chapter books)
  transcribe.py                    # faster-whisper small -> word timings (cached)
  align.py                         # snaps canonical text onto whisper words; emits confidence
  cache/<audiokey>.<model>.words.json   # cached transcript (keyed by mp3 basename)
```

**`index.json` entry:**
```json
{
  "filename": "darkalleys.fb2",
  "title": "Тёмные аллеи",
  "author": "Иван Бунин",
  "category": "Short Stories",
  "audiobook": {
    "narrator": "audiostories.ru",
    "chapters": ["audio/darkalleys-ch1.json"]
  }
}
```
- `filename` is relative to `public/books/` (no leading folder unless the file is in a subfolder).
- `audiobook.chapters[i]` is the alignment file for book-chapter *i*, path relative to `/books/`
  → **must be `"audio/<name>-chM.json"`** (the JSONs live flat in `public/books/audio/`).
- **Omit `audiobook`** entirely for a TTS-only book (Dmitry voice still highlights, no alignment needed).

**Alignment JSON (what the app loads):**
```json
{
  "audio_url": "/books/audio/darkalleys.mp3",
  "narrator": "audiostories.ru",
  "fragments": [
    { "begin": 1.55, "end": 12.0, "text": "В холодное осеннее ненастье…", "confidence": "high" }
  ]
}
```
- `begin`/`end` in **seconds**, relative to that mp3.
- `audio_url`: self-hosted same-origin `"/books/audio/<name>.mp3"` (personal use), OR an
  `https://archive.org/download/<item>/<file>.mp3` URL (the big books).

**Three invariants that WILL bite if broken:**
1. **The aligner's `--text` file is ONE SENTENCE PER LINE.** `align.py` makes one
   fragment per line. Paragraphs-per-line → each fragment spans a whole paragraph →
   the highlight lights the first sentence and sits there for the whole paragraph.
2. **Fragment text must match the app's `parseSentences` output.** At runtime the app
   re-splits each page into sentences and matches them to fragments by normalized
   prefix (`buildSentenceTimings`). Use the splitter in §6-A (it mirrors `parseSentences`,
   including Russian abbreviation/initial handling) so the two agree.
3. **Cross-page highlight depends on `currentPageRef` in App.jsx.** The audiobook RAF
   loop reads the page from `currentPageRef.current`, not the closed-over `currentPage`.
   If audiobook highlighting ever freezes *right after a page flip*, that ref/sync is
   the thing to check.

---

## 2. Add a book (TTS-first — do this before any audio)

1. **Get the text** as `.fb2` / `.epub` / `.txt` / `.html` (the app parses all of these).
   - Public-domain Russian sources: az.lib.ru, ru.wikisource.org; Litres for paid/legal.
   - FB2 is often **windows-1251** — see §6-G if it won't parse.
   - Extracting one story from an anthology → §4.
2. **Drop it in** `public/books/<name>.fb2` (root of that folder, matching `filename`).
3. **Register it** in `index.json` → §6-B.
4. **Ship** (Git Bash):
   ```bash
   cd /c/Users/david/projects/govorim-app
   git add public/books/<name>.fb2 public/books/index.json
   git commit -m "Add <book> for TTS reading"
   git push
   ```
   Now it reads in TTS (Dmitry) with synced highlighting, no alignment required.

---

## 3. Add the audiobook (real narration + sentence-level alignment)

All of §3 except the final commit is **WSL**, inside the `aeneas` env.

1. **Get the audio** and self-host it:
   ```bash
   cd /mnt/c/Users/david/projects/govorim-app
   mkdir -p public/books/audio
   curl -L -o public/books/audio/<name>.mp3 "<MP3_URL>"
   ls -lh public/books/audio/<name>.mp3
   head -c 4 public/books/audio/<name>.mp3 | xxd   # ID3 or FF FB = real audio, not an HTML error
   ```
   (Personal use → keep it self-hosted; don't republish someone else's recording to a public archive.)

2. **Trim any intro music** (otherwise Whisper transcribes the music and the alignment
   drifts). Find where narration starts by ear (or the silence probe in §6-D), then:
   ```bash
   START=18    # seconds where the voice begins (decimals/mm:ss ok)
   ffmpeg -y -ss $START -i public/books/audio/<name>.mp3 -c:a libmp3lame -q:a 2 /tmp/trim.mp3
   mv /tmp/trim.mp3 public/books/audio/<name>.mp3
   ```

3. **Build the one-sentence-per-line text file** → §6-A. Confirm it reports a sentence
   count (e.g. ~143), not a paragraph count.

4. **Align** with the existing pipeline:
   ```bash
   python3 scripts/alignment/run_chapter.py \
     --audio public/books/audio/<name>.mp3 \
     --text  scripts/alignment/<name>.txt \
     --output public/books/audio/<name>-ch1.json \
     --audio-url /books/audio/<name>.mp3 \
     --narrator "<narrator or source>" \
     --model small
   ```
   - First run on a given mp3 transcribes with Whisper small on CPU (a few minutes); the
     transcript caches at `scripts/alignment/cache/<name>.small.words.json`, so re-aligns
     are seconds.
   - **Add `--force-transcribe` ONLY when the audio file changed** (e.g. after trimming) —
     the cache key is the mp3 basename, so the same filename would otherwise reuse the
     stale transcript.

5. **Verify** → §6-F. You want: fragment count ≈ sentence count, monotonic begins, no
   zero/negative-length fragments, first `begin` ≈ 0 (or ≈ your trim residual), last `end`
   ≈ recording length. Long single fragments are fine if the prose has long sentences.

6. **Wire the `audiobook` field** into `index.json` → §6-C.

7. **Ship** (Git Bash):
   ```bash
   cd /c/Users/david/projects/govorim-app
   git add public/books/audio/<name>.mp3 public/books/audio/<name>-ch1.json public/books/index.json
   git commit -m "Add audiobook alignment for <book>"
   git push
   ```
   (`scripts/alignment/<name>.txt` and the Whisper cache are build inputs — don't commit them.)

8. **Test:** hard-refresh, open the book, play. It defaults to audiobook mode; the
   highlight should step sentence by sentence and survive page flips. TTS stays available
   via the toggle in the audio bar.

---

## 4. Isolating one story from an anthology into a clean FB2

When the source FB2 is a collection (e.g. "Том 7 … Тёмные аллеи") and you want one story:

1. Decode (FB2 is usually cp1251) and map the `<body>/<section>` tree to find the target
   story (it's a leaf `<section>` with a `<title>` and `<p>` children).
2. Deep-copy that one section, drop it into a fresh minimal FB2 with a clean
   `<description><title-info>` (genre, author split into first/middle/last, book-title, lang ru),
   and a single `<body><section>`.
3. Validate it parses to **one chapter** (mirror the app's `parseFb2`: 0 `<subtitle>`s →
   heading from the section `<title>`, body = `<p>/<v>/<subtitle>` joined by `\n\n`).

Compact builder (run in WSL from repo root; edit the find-path to the target section):
```bash
python3 - <<'PY'
import xml.etree.ElementTree as ET, copy
URI='http://www.gribuser.ru/xml/fictionbook/2.0'; ns='{'+URI+'}'
ET.register_namespace('', URI)
raw=open("SOURCE_ANTHOLOGY.fb2","rb").read()
import re
s=raw.decode("cp1251")                       # most Russian FB2s; use utf-8 if declared so
s=re.sub(r'encoding=["\']windows-1251["\']','encoding="utf-8"',s,1,re.I)
root=ET.fromstring(s)
body0=root.findall(ns+'body')[0]
# --- locate the target leaf <section> by walking titles (adjust indices/title match) ---
story=body0.findall(ns+'section')[0].findall(ns+'section')[0].findall(ns+'section')[0]
def E(t,x=None):
    e=ET.Element(ns+t); e.text=x; return e
fb=ET.Element(ns+'FictionBook'); d=ET.SubElement(fb,ns+'description'); ti=ET.SubElement(d,ns+'title-info')
ti.append(E('genre','prose_classic'))
au=ET.SubElement(ti,ns+'author'); [au.append(E(k,v)) for k,v in [('first-name','Иван'),('middle-name','Алексеевич'),('last-name','Бунин')]]
ti.append(E('book-title','Тёмные аллеи')); ti.append(E('lang','ru'))
b=ET.SubElement(fb,ns+'body'); b.append(copy.deepcopy(story))
t=ET.ElementTree(fb); ET.indent(t,'  ')
t.write("public/books/<name>.fb2", encoding="utf-8", xml_declaration=True)
print("wrote public/books/<name>.fb2")
PY
```

---

## 5. Troubleshooting (symptom → cause → fix)

| Symptom | Cause | Fix |
|---|---|---|
| Highlight lights the first sentence and **doesn't move** (then jumps much later) | `--text` was paragraph-per-line, so fragment count = paragraph count and each fragment spans a whole paragraph | Regenerate `--text` as **one sentence per line** (§6-A), realign **without** `--force-transcribe` (audio unchanged) |
| Highlight is **offset / lags** behind the voice the whole time | Intro music/announcer at the head of the mp3; Whisper aligned to that | Trim the head with ffmpeg (§3.2), realign **with** `--force-transcribe` |
| Fragment **count ≠ sentence count** | `align.py` split differently than expected, or text not one-per-line | Re-check §6-A produced N lines; if still off, read `align.py` to see its line/sentence rule |
| Audiobook mode never engages (falls back to TTS) | `audiobook.chapters` path wrong / file 404s | Path must be `"audio/<name>-chM.json"`; file must exist at `public/books/audio/...` |
| Cyrillic comes out as mojibake | Source FB2 is cp1251 but read as utf-8 | Decode cp1251 and rewrite the XML declaration to utf-8 (§6-G) |
| Highlight freezes **right after a page flip** only | `currentPage` stale-closure in the RAF loop | Confirm App.jsx mirrors `currentPage` into `currentPageRef` and `highlightSentence` reads the ref |
| `cp ~/Downloads/...: No such file` | Download landed elsewhere | Don't download — create the file in place (§6 heredocs) |

---

## 6. Snippets

### 6-A. FB2 → one-sentence-per-line text (the aligner's `--text`)
Run in WSL from repo root. Edit the two paths. Mirrors the app's `parseSentences`.
```bash
python3 - <<'PY'
import xml.etree.ElementTree as ET, re, copy
FB2="public/books/<name>.fb2"; OUT="scripts/alignment/<name>.txt"
NS="{http://www.gribuser.ru/xml/fictionbook/2.0}"
def text_of(el): return "".join(el.itertext()) if el is not None else ""
norm=lambda s: re.sub(r"\s+"," ",s).strip()
root=ET.parse(FB2).getroot()
secc=copy.deepcopy(root.find(NS+"body/"+NS+"section"))
te=secc.find(NS+"title")
if te is not None: secc.remove(te)
paras=[norm(text_of(e)) for e in secc.iter() if e.tag in (NS+"p",NS+"v",NS+"subtitle")]
chapter_text="\n\n".join(p for p in paras if p)
ABBR=set("г т д п е ч с н тт вв гг сс пр ст до стр рис табл напр тов акад проф имп ген пол св ул пл пер просп обл млн млрд тыс руб коп сек мин см мм км кг вып изд гл им век напис опубл род ум mr mrs ms dr vs etc".split())
TERM=set(".!?…")
def parse_sentences(text):
    out=[]
    for line in re.split(r"\n+",text):
        line=line.strip()
        if not line: continue
        sentStart=pos=0; L=len(line)
        while pos<L:
            if line[pos] in TERM:
                endTerm=pos
                while endTerm+1<L and line[endTerm+1] in TERM: endTerm+=1
                nxt=endTerm+1
                if nxt>=L: boundary=True
                elif not line[nxt].isspace(): boundary=False
                else:
                    k=nxt
                    while k<L and line[k].isspace(): k+=1
                    if k>=L: boundary=True
                    elif re.match(r'[А-ЯЁA-Z«"„(\[—–]',line[k]):
                        wEnd=endTerm
                        while wEnd>0 and line[wEnd-1] in TERM: wEnd-=1
                        wStart=wEnd-1
                        while wStart>=0 and re.match(r'[а-яёА-ЯЁa-zA-Z]',line[wStart]): wStart-=1
                        wStart+=1
                        wb=line[wStart:wEnd]
                        is_initial=len(wb)==1 and re.match(r'[А-ЯЁA-Z]',wb)
                        is_abbrev=len(wb)>0 and wb.lower() in ABBR
                        boundary=not(is_initial or is_abbrev)
                    else: boundary=False
                if boundary:
                    s=line[sentStart:endTerm+1].strip()
                    if s: out.append(s)
                    sw=endTerm+1
                    while sw<L and line[sw].isspace(): sw+=1
                    sentStart=pos=sw
                else: pos=endTerm+1
            else: pos+=1
        tail=line[sentStart:].strip()
        if tail: out.append(tail)
    return out
sents=parse_sentences(chapter_text)
open(OUT,"w",encoding="utf-8").write("\n".join(sents)+"\n")
print("wrote", OUT, "with", len(sents), "lines (one sentence each)")
PY
```
For a `.txt`/`.epub` source instead of FB2, just set `chapter_text` to the plain text and keep `parse_sentences`.

### 6-B. index.json — add a book (idempotent; Git Bash)
```bash
node -e "const fs=require('fs'),p='public/books/index.json',a=JSON.parse(fs.readFileSync(p,'utf8'));const fn='<name>.fb2';if(a.some(b=>b.filename===fn)){console.log('already present');}else{a.push({filename:fn,title:'<TITLE>',author:'<AUTHOR>',category:'<CATEGORY>'});fs.writeFileSync(p,JSON.stringify(a,null,2)+'\n');console.log('added; total',a.length);}"
```

### 6-C. index.json — add/fix the audiobook field (idempotent; Git Bash)
```bash
node -e "const fs=require('fs'),p='public/books/index.json',a=JSON.parse(fs.readFileSync(p,'utf8'));const b=a.find(x=>x.filename==='<name>.fb2');if(b){b.audiobook={narrator:'<NARRATOR>',chapters:['audio/<name>-ch1.json']};fs.writeFileSync(p,JSON.stringify(a,null,2)+'\n');console.log('ok ->',JSON.stringify(b.audiobook));}else{console.log('entry not found');}"
```

### 6-D. ffmpeg — find candidate trim point (WSL)
```bash
ffmpeg -i public/books/audio/<name>.mp3 -af silencedetect=noise=-30dB:d=0.4 -f null - 2>&1 | grep -E 'silence_(start|end)' | head
```
A `silence_end` right where speech kicks in is a good `START` value for §3.2.

### 6-E. run_chapter.py — invocation template (WSL)
```bash
python3 scripts/alignment/run_chapter.py \
  --audio public/books/audio/<name>.mp3 \
  --text  scripts/alignment/<name>.txt \
  --output public/books/audio/<name>-ch1.json \
  --audio-url /books/audio/<name>.mp3 \
  --narrator "<narrator>" \
  --model small        # add --force-transcribe ONLY if the mp3 changed
```

### 6-F. Verify an alignment file (WSL)
```bash
python3 -c "
import json
d=json.load(open('public/books/audio/<name>-ch1.json',encoding='utf-8'))
f=d['fragments']
print('count', len(f))
print('span %.1f .. %.1f s' % (f[0]['begin'], f[-1]['end']))
print('zero/neg-length:', [i for i,x in enumerate(f) if x['end']<=x['begin']][:15])
print('non-monotonic begins at:', [i for i in range(1,len(f)) if f[i]['begin'] < f[i-1]['begin']][:15])
for x in f[:6]:
    print('  %7.2f - %7.2f  %s  | %s' % (x['begin'], x['end'], x.get('confidence'), x['text'][:40]))
"
```

### 6-G. Convert a cp1251 FB2 to utf-8 (WSL)
```bash
python3 - <<'PY'
raw=open("INPUT.fb2","rb").read()
s=raw.decode("cp1251")     # if this errors, it's already utf-8
import re
s=re.sub(r'encoding=["\']windows-1251["\']','encoding="utf-8"',s,1,re.I)
open("INPUT.utf8.fb2","w",encoding="utf-8").write(s)
print("ok")
PY
```

---

## 7. Multi-chapter books (novels)

`run_book.py` drives many chapters: per-chapter `.txt` in `public/books/novel/`,
per-chapter audio (one mp3 each), and one alignment JSON per chapter named
`<name>-pN-chM.json`, all listed in order under `audiobook.chapters`. It resumes
(skips chapters whose output JSON exists; `--force` to redo) and caches transcripts
per audio file. Same one-sentence-per-line rule applies to every chapter `.txt`.
For a single short story, `run_chapter.py` (§3) is all you need.
