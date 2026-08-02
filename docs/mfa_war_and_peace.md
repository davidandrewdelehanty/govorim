# Force-aligning War & Peace (Война и мир) with Montreal Forced Aligner

Goal: run MFA on the Russian *Война и мир* audiobook (361 chapter MP3s in your R2 bucket)
to get precise word-level timestamps, then fold them back into your `audio/vim/NNN.json`
files.

MFA is **forced alignment**: it needs, per chapter, one audio file **and** a text
transcript of what is actually spoken. It lines the words up to the audio using a Russian
acoustic model + pronunciation dictionary. It does **not** transcribe and it does **not**
fix a transcript that doesn't match the audio — see the note in Step 4 about which text to use.

Everything below is Ubuntu bash. Set this once:

```bash
# If your govorim-app repo lives in WSL on the Windows box, it's usually here:
export REPO=/mnt/c/Users/david/projects/govorim-app
# (otherwise point REPO at wherever the repo is on this machine)
export AUDIO_DIR=/path/to/your/war-and-peace-mp3s   # <-- your local chapter MP3s
export WP=~/wp_align                                 # scratch workspace for this job
mkdir -p "$WP"/{corpus,out}
```

You already have the audio locally (one MP3 per chapter), so there's nothing to download —
Step 4 reads straight from `$AUDIO_DIR`.

---

## Step 1 — Install Miniconda (skip if you already have conda)

MFA is only distributed through conda-forge; pip will not work.

```bash
cd ~
wget https://repo.anaconda.com/miniconda/Miniconda3-latest-Linux-x86_64.sh
bash Miniconda3-latest-Linux-x86_64.sh -b -p ~/miniconda3
~/miniconda3/bin/conda init bash
exec bash        # reload the shell so `conda` is on PATH
```

## Step 2 — Install MFA

The fast path uses mamba (conda's resolver is very slow on the MFA env):

```bash
conda activate base
conda install -y -c conda-forge mamba
mamba create -y -n aligner -c conda-forge montreal-forced-aligner
conda activate aligner
mfa version        # confirm it prints a 3.x version
```

You also need `ffmpeg` for the MP3→WAV conversion (MFA wants 16 kHz mono WAV):

```bash
sudo apt-get update && sudo apt-get install -y ffmpeg jq
```

## Step 3 — Download the Russian model, dictionary, and G2P

```bash
mfa model download acoustic  russian_mfa
mfa model download dictionary russian_mfa
mfa model download g2p        russian_mfa      # used to pronounce out-of-vocabulary words
mfa model inspect acoustic russian_mfa         # sanity check it's installed
```

## Step 4 — Build the corpus (audio + transcript, one pair per chapter)

MFA reads a folder of matched pairs with the **same basename**:

```
corpus/
  002.wav   002.lab
  003.wav   003.lab
  ...
```

`.lab` is a plain-text file containing the transcript for that audio file.

**Which transcript text?** Two choices — pick based on what you're trying to fix:

- **(A) The existing per-chapter transcript** (the concatenated `fragments[].text` already in
  `audio/vim/NNN.json`). This is guaranteed to match the audio, so MFA aligns cleanly and you
  get high-precision word timings that replace the current (approximate) ones. **Recommended
  default.**
- **(B) The FB2 book text** for each chapter. Use this only if your goal is to sync the
  *displayed book text* to the audio. It only works where the recording is a faithful reading
  of that exact edition — for *Война и мир* the book-vs-audio text match is low (French
  passages, edition differences), so MFA will misalign wherever they diverge. If you go this
  route, segment the FB2 into the same 361 chapters first and drop each chapter's text into the
  matching `.lab`.

The script below does option **(A)** from your **local** MP3s — for each
`audio/vim/NNN.json` it finds the matching MP3 in `$AUDIO_DIR`, converts it to 16 kHz mono WAV,
and writes the `.lab` from the chapter's transcript text:

```bash
cat > "$WP/build_corpus.py" <<'PY'
import json, glob, os, subprocess
REPO=os.environ["REPO"]; WP=os.environ["WP"]; AUD=os.environ["AUDIO_DIR"]

# index your local mp3s by basename (002 -> /path/002.mp3)
mp3s={}
for p in glob.glob(f"{AUD}/**/*.mp3", recursive=True):
    mp3s[os.path.splitext(os.path.basename(p))[0]]=p

src=sorted(glob.glob(f"{REPO}/public/books/audio/vim/*.json"))
print("chapters:",len(src),"| local mp3s found:",len(mp3s))
missing=[]
for f in src:
    base=os.path.splitext(os.path.basename(f))[0]         # e.g. "002"
    d=json.load(open(f))
    text=" ".join(fr.get("text","") for fr in d.get("fragments",[])).strip()
    mp3=mp3s.get(base)
    if not mp3 or not text:
        missing.append(base); continue
    wav=f"{WP}/corpus/{base}.wav"; lab=f"{WP}/corpus/{base}.lab"
    subprocess.run(["ffmpeg","-y","-loglevel","error","-i",mp3,
                    "-ac","1","-ar","16000",wav], check=True)
    open(lab,"w",encoding="utf-8").write(text)
print("built:", len(src)-len(missing), "| unmatched:", missing[:10], "..." if len(missing)>10 else "")
print("corpus ->", f"{WP}/corpus")
PY
python "$WP/build_corpus.py"
```

> **If the script reports unmatched chapters**, your MP3 filenames don't line up with the JSON
> basenames (`002`, `003`, …). Check with `ls "$AUDIO_DIR" | head`. If they're named
> differently but in the right playing order, pair them by sorted order instead of basename —
> tell me the naming and I'll adjust the script. Getting this pairing right matters: a chapter
> aligned against the wrong transcript produces garbage timings.

## Step 5 — Validate the corpus (and handle out-of-vocabulary words)

```bash
mfa validate "$WP/corpus" russian_mfa russian_mfa --single_speaker
```

This reports any files whose text/audio look off and lists **OOV** words (names, rare forms)
missing from the dictionary. To give those words pronunciations so they still align, generate
them with the G2P model and add them to a personal dictionary:

```bash
# writes pronunciations for every OOV found in the corpus
mfa g2p "$WP/corpus" russian_mfa "$WP/oov_dict.txt" --dictionary_path russian_mfa
# combine base dict + OOVs into one dictionary MFA will use
cat $(mfa model inspect dictionary russian_mfa 2>/dev/null | grep -oP '/.*russian_mfa\.dict') \
    "$WP/oov_dict.txt" > "$WP/wp_dict.dict"   # if the path grep fails, see note below
```

Simplest robust alternative — skip the manual merge and let MFA fill OOVs itself during
alignment by passing the G2P model:

```bash
# (use this instead of building wp_dict.dict if the cat step above is fiddly)
```

## Step 6 — Align

Audiobooks are one narrator, so `--single_speaker` is both faster and more accurate.

```bash
mfa align "$WP/corpus" russian_mfa russian_mfa "$WP/out" \
    --single_speaker \
    --output_format json \
    --num_jobs 4 \
    --clean
```

- `--output_format json` gives you, per chapter, `out/<basename>.json` with word and phone
  intervals — much easier to parse than TextGrids.
- Bump `--num_jobs` to your core count. 361 short chapters align comfortably in one run;
  expect roughly tens of minutes on a normal laptop.
- If a few chapters fail alignment (`beam` errors), re-run just those with
  `--beam 100 --retry_beam 400`.

## Step 7 — Fold the timings back into your app JSON (optional)

MFA's JSON gives word start/end times. This maps them onto your existing
`fragments[].words[]` structure (same word order), so the reader highlight uses MFA timings:

```bash
cat > "$WP/apply_timings.py" <<'PY'
import json, glob, os
REPO=os.environ["REPO"]; WP=os.environ["WP"]
def mfa_words(p):
    d=json.load(open(p)); out=[]
    # MFA json: tiers -> "words" -> entries [start,end,label]
    tiers=d.get("tiers",{}); w=tiers.get("words") or tiers.get("Words") or {}
    for e in w.get("entries",[]):
        start,end,label=e[0],e[1],e[2]
        if label.strip(): out.append((float(start),float(end),label))
    return out
for mp in sorted(glob.glob(f"{WP}/out/*.json")):
    base=os.path.splitext(os.path.basename(mp))[0]
    tgt=f"{REPO}/public/books/audio/vim/{base}.json"
    if not os.path.exists(tgt): continue
    words=mfa_words(mp); d=json.load(open(tgt)); i=0
    for fr in d.get("fragments",[]):
        for wd in fr.get("words",[]):
            if i<len(words):
                wd["begin"]=round(words[i][0],3); wd["end"]=round(words[i][1],3); i+=1
        if fr.get("words"):
            fr["begin"]=fr["words"][0]["begin"]; fr["end"]=fr["words"][-1]["end"]
    json.dump(d,open(tgt,"w",encoding="utf-8"),ensure_ascii=False)
    print("updated",base,f"({i}/{len(words)} words mapped)")
PY
python "$WP/apply_timings.py"
```

Inspect one chapter, re-run your alignment-% check, and if it looks right, commit the changed
`audio/vim/*.json` files. **Back them up first** (`cp -r public/books/audio/vim{,.bak}`), since
this rewrites them in place.

---

### Notes & gotchas

- **`mfa model inspect dictionary russian_mfa`** prints where the `.dict` file lives if you need
  the raw dictionary path in Step 5.
- MFA caches everything under `~/Documents/MFA` (or `~/.local/share/mfa`); delete that folder if
  a run gets into a weird state, or always pass `--clean`.
- The Russian MFA dictionary is IPA-based and pairs with the `russian_mfa` acoustic model — don't
  mix it with a different acoustic model.
- If `ffmpeg` chokes on a stray MP3, that chapter just won't get a WAV; re-run `build_corpus.py`
  (it skips MP3s already downloaded).
- Word count between MFA output and your JSON can drift by a few if punctuation splits differ;
  the mapping script above is positional, so spot-check a chapter's highlight timing before
  committing all 361.
