#!/usr/bin/env python3
# Definitive Чайка act rebuild.
# The source recordings start on speech almost immediately (~0.3-1.3s of silence)
# but their word_timings place the first word 7-11s in — a constant per-segment
# shift. This measures where speech actually begins (silencedetect), rebases each
# segment's timings by (first_word_begin - speech_start), trims trailing silence,
# and rebuilds the 4 act MP3s + JSONs so audio and highlight line up.
# Run from repo root:  python3 fix_chaika2.py   (needs ffmpeg + aws)
import json, subprocess, os, tempfile, re

REPO = os.path.dirname(os.path.abspath(__file__))
SRC  = os.path.join(REPO, "public/books/audio/chaika6")
DST  = os.path.join(REPO, "public/books/audio/chaika-acts")
BUCKET = "s3://govorim-audio"
PUB    = "https://pub-84adcd23e17e4925a0ac7eca17ea2556.r2.dev/chaika-acts/"
os.environ.setdefault("AWS_ENDPOINT_URL",
    "https://34e5181838c8f719758264dbb7b02b46.r2.cloudflarestorage.com")
PAD = 0.4   # seconds of tail kept after a segment's last word

def sh(c): subprocess.run(c, check=True)
def ffdur(f):
    return float(subprocess.check_output(["ffprobe","-v","error","-show_entries",
        "format=duration","-of","csv=p=0",f]).decode().strip())
def speech_start(f):
    out = subprocess.run(["ffmpeg","-hide_banner","-nostats","-i",f,"-t","25",
        "-af","silencedetect=noise=-35dB:d=0.3","-f","null","-"],
        capture_output=True, text=True).stderr
    st, en = [], []
    for ln in out.splitlines():
        m = re.search(r"silence_start:\s*([-\d.]+)", ln)
        if m: st.append(float(m.group(1)))
        m = re.search(r"silence_end:\s*([-\d.]+)", ln)
        if m: en.append(float(m.group(1)))
    return en[0] if (st and st[0] < 0.05 and en) else 0.0

work = tempfile.mkdtemp(); print("workdir:", work)
segs = ["01","02","03","04","05","06"]; mp3 = {}
print("== downloading 6 source recordings ==")
for s in segs:
    p = os.path.join(work, f"ch{s}.mp3")
    sh(["aws","s3","cp", f"{BUCKET}/chaika6/chaika-ch{s}.mp3", p]); mp3[s] = p

# --- measure shift per segment and rebase timings to audio time ---
data = {}
print("\n== measuring speech-start and rebasing ==")
for s in segs:
    d  = json.load(open(os.path.join(SRC, f"chaika-ch{s}.json"), encoding="utf-8"))
    wt = d["word_timings"]; fr = d.get("fragments") or []
    fwb, D, sp = wt[0]["begin"], ffdur(mp3[s]), speech_start(mp3[s])
    shift = fwb - sp                       # timings run this much ahead of audio
    lastA = wt[-1]["end"] - shift          # audio time of last word
    print(f"  ch{s}: firstword@{fwb:6.2f}  speech@{sp:4.2f}  -> shift {shift:5.2f}s"
          f"   (lastword audio {lastA:7.2f}, file {D:7.2f})")
    reb = lambda t: round(t - shift, 3)
    data[s] = {
        "wt": [{"word":w["word"], "begin":reb(w["begin"]), "end":reb(w["end"])} for w in wt],
        "fr": [dict(f, begin=reb(f["begin"]),
                    **({"end":reb(f["end"])} if f.get("end") is not None else {}))
               for f in fr if f.get("begin") is not None],
        "lastA": lastA, "dur": D, "narr": d.get("narrator") or "Аудиокнига",
    }

# per-segment shift (raw first-word begin minus measured speech start), used to
# map the known act-boundary times (in raw-timing space) into audio time.
def raw_shift(seg):
    d = json.load(open(os.path.join(SRC, f"chaika-ch{seg}.json"), encoding="utf-8"))
    return d["word_timings"][0]["begin"] - speech_start(mp3[seg])
cut1 = round(716.14 - raw_shift("02"), 3)   # Act 2 opens "Встанете"
cut2 = round(257.35 - raw_shift("05"), 3)   # Act 4 opens "Константин"
print(f"\ncut1 (ch02 audio @ {cut1}s)   cut2 (ch05 audio @ {cut2}s)")

# --- build the 4 act MP3s (audio-time trims; trailing silence removed) ---
FMT = "aresample=44100,aformat=sample_fmts=fltp:channel_layouts=stereo,asetpts=PTS-STARTPTS"
def af(inp,a,b): return f"[{inp}:a]atrim={a}:{b},{FMT}"
def build(n, s1,a1,b1, s2,a2,b2):
    out = os.path.join(work, f"chaika-act{n}.mp3")
    fc  = f"{af(0,a1,b1)}[a];{af(1,a2,b2)}[b];[a][b]concat=n=2:v=0:a=1[o]"
    sh(["ffmpeg","-y","-i",mp3[s1],"-i",mp3[s2],"-filter_complex",fc,
        "-map","[o]","-c:a","libmp3lame","-q:a","3",out]); return out

e1 = data["01"]["lastA"]+PAD; e2 = data["02"]["lastA"]+PAD
e3 = data["03"]["lastA"]+PAD; e4 = data["04"]["lastA"]+PAD
e5 = data["05"]["lastA"]+PAD; e6 = data["06"]["lastA"]+PAD
print("\n== building act MP3s ==")
mp3_act = {
    1: build(1,"01",0,e1,      "02",0,cut1),
    2: build(2,"02",cut1,e2,   "03",0,e3),
    3: build(3,"04",0,e4,      "05",0,cut2),
    4: build(4,"05",cut2,e5,   "06",0,e6),
}
o1 = e1; o2 = e2 - cut1; o3 = e4; o4 = e5 - cut2   # second-segment offsets

def wt_lt(seg,t):  return [w for w in data[seg]["wt"] if w["begin"] <  t]
def wt_ge(seg,t,sub): return [dict(w,begin=round(w["begin"]-sub,3),end=round(w["end"]-sub,3))
                              for w in data[seg]["wt"] if w["begin"] >= t]
def wsh(ws,o): return [dict(w,begin=round(w["begin"]+o,3),end=round(w["end"]+o,3)) for w in ws]
def fr_lt(seg,t): return [f for f in data[seg]["fr"] if f["begin"] < t]
def fr_ge(seg,t,sub): return [dict(f,begin=round(f["begin"]-sub,3),
                              **({"end":round(f["end"]-sub,3)} if f.get("end") is not None else {}))
                              for f in data[seg]["fr"] if f["begin"] >= t]
def fsh(fs,o): return [dict(f,begin=round(f["begin"]+o,3),
                       **({"end":round(f["end"]+o,3)} if f.get("end") is not None else {})) for f in fs]

acts = {
 1:(data["01"]["wt"]+wsh(wt_lt("02",cut1),o1),  data["01"]["fr"]+fsh(fr_lt("02",cut1),o1)),
 2:(wt_ge("02",cut1,cut1)+wsh(data["03"]["wt"],o2), fr_ge("02",cut1,cut1)+fsh(data["03"]["fr"],o2)),
 3:(data["04"]["wt"]+wsh(wt_lt("05",cut2),o3),  data["04"]["fr"]+fsh(fr_lt("05",cut2),o3)),
 4:(wt_ge("05",cut2,cut2)+wsh(data["06"]["wt"],o4), fr_ge("05",cut2,cut2)+fsh(data["06"]["fr"],o4)),
}
os.makedirs(DST, exist_ok=True)
print("\n== writing act JSONs ==")
for n,(wt,fr) in acts.items():
    wt = [dict(w,begin=max(0.0,w["begin"]),end=max(0.0,w["end"])) for w in wt]
    json.dump({"audio_url":PUB+f"chaika-act{n}.mp3","narrator":data["01"]["narr"],
               "fragments":fr,"word_timings":wt},
              open(os.path.join(DST,f"chaika-act{n}.json"),"w",encoding="utf-8"), ensure_ascii=False)
    print(f"  act{n}: {len(wt)} words | first '{wt[0]['word']}'@{wt[0]['begin']}  last '{wt[-1]['word']}'@{wt[-1]['end']}")

print("\n== uploading act MP3s ==")
for n in (1,2,3,4):
    sh(["aws","s3","cp",mp3_act[n],f"{BUCKET}/chaika-acts/chaika-act{n}.mp3","--content-type","audio/mpeg"])
print("\nDONE. Commit and push:")
print("  git add public/books/audio/chaika-acts && git commit -m 'Чайка: rebase act timings to audio' && git push origin main")
