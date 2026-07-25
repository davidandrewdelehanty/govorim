#!/usr/bin/env python3
# Rebuild the 4 Чайка act files with CORRECT timing.
# For each source recording it measures the real audio duration and auto-detects
# whether the segment's word_timings are shifted ahead of the audio (a phantom
# lead-in), corrects that, re-cuts the act MP3s in audio time, and writes the 4
# act JSONs with exact concat offsets. Run from the repo root:
#     python3 fix_chaika.py
# Needs: ffmpeg/ffprobe + aws CLI (same setup as recut_chaika.sh).
import json, subprocess, os, tempfile

REPO   = os.path.dirname(os.path.abspath(__file__))
SRC    = os.path.join(REPO, "public/books/audio/chaika6")
DST    = os.path.join(REPO, "public/books/audio/chaika-acts")
BUCKET = "s3://govorim-audio"
PUB    = "https://pub-84adcd23e17e4925a0ac7eca17ea2556.r2.dev/chaika-acts/"
os.environ.setdefault("AWS_ENDPOINT_URL",
    "https://34e5181838c8f719758264dbb7b02b46.r2.cloudflarestorage.com")

def sh(cmd): subprocess.run(cmd, check=True)
def dur(f):
    return float(subprocess.check_output(
        ["ffprobe","-v","error","-show_entries","format=duration",
         "-of","csv=p=0",f]).decode().strip())

work = tempfile.mkdtemp(); print("workdir:", work)
segs = ["01","02","03","04","05","06"]
mp3  = {}
print("== downloading 6 source recordings ==")
for s in segs:
    p = os.path.join(work, f"ch{s}.mp3")
    sh(["aws","s3","cp", f"{BUCKET}/chaika6/chaika-ch{s}.mp3", p]); mp3[s] = p

# --- load JSONs, auto-detect per-segment timing shift, rebase to match audio ---
data = {}
print("\n== detecting timing shift per segment ==")
for s in segs:
    d  = json.load(open(os.path.join(SRC, f"chaika-ch{s}.json"), encoding="utf-8"))
    wt = d["word_timings"]; fr = d.get("fragments") or []
    fwb, lastend, D = wt[0]["begin"], wt[-1]["end"], dur(mp3[s])
    # candidate A: mp3 keeps the lead-in -> timings already match audio (offset 0)
    # candidate B: mp3 was trimmed to the first word -> timings shifted by fwb
    offset = fwb if abs(D-(lastend-fwb)) <= abs(D-lastend) else 0.0
    print(f"  ch{s}: firstword@{fwb:6.2f}  lastword@{lastend:7.2f}  mp3={D:7.2f}"
          f"  -> shift {offset:5.2f}s ({'trimmed' if offset else 'has lead-in'})")
    reb = lambda t: round(t-offset, 3)
    data[s] = {
        "wt":  [{"word":w["word"], "begin":reb(w["begin"]), "end":reb(w["end"])} for w in wt],
        "fr":  [dict(f, begin=reb(f["begin"]),
                     **({"end":reb(f["end"])} if f.get("end") is not None else {}))
                for f in fr if f.get("begin") is not None],
        "dur": D, "offset": offset, "narr": d.get("narrator") or "Аудиокнига",
    }

# --- act-boundary cut points, in (rebased) audio time ---
def cut_at(seg, orig_begin):
    target = orig_begin - data[seg]["offset"]
    wt = data[seg]["wt"]
    i  = min(range(len(wt)), key=lambda k: abs(wt[k]["begin"]-target))
    return wt[i]["begin"]
cut1 = cut_at("02", 716.14)   # Act 2 opens "Встанете" (was @716.14 in raw timings)
cut2 = cut_at("05", 257.35)   # Act 4 opens "Константин" (was @257.35)
print(f"\ncut1 (ch02 @ {cut1:.2f}s)   cut2 (ch05 @ {cut2:.2f}s)")

# --- build the 4 act MP3s (trim + concat in audio time) ---
FMT = "aresample=44100,aformat=sample_fmts=fltp:channel_layouts=stereo,asetpts=PTS-STARTPTS"
def atrim(inp, a, b): return f"[{inp}:a]atrim={a}" + (f":{b}" if b is not None else "") + f",{FMT}"
def build(n, s1, a1, b1, s2, a2, b2):
    out = os.path.join(work, f"chaika-act{n}.mp3")
    fc  = f"{atrim(0,a1,b1)}[a];{atrim(1,a2,b2)}[b];[a][b]concat=n=2:v=0:a=1[o]"
    sh(["ffmpeg","-y","-i",mp3[s1],"-i",mp3[s2],"-filter_complex",fc,
        "-map","[o]","-c:a","libmp3lame","-q:a","3",out]); return out

D1,D2,D4,D5 = data["01"]["dur"],data["02"]["dur"],data["04"]["dur"],data["05"]["dur"]
print("\n== building act MP3s ==")
act_mp3 = {
    1: build(1,"01",0,None,"02",0,cut1),      # ch01(full) + ch02[:cut1]
    2: build(2,"02",cut1,None,"03",0,None),   # ch02[cut1:] + ch03(full)
    3: build(3,"04",0,None,"05",0,cut2),      # ch04(full) + ch05[:cut2]
    4: build(4,"05",cut2,None,"06",0,None),   # ch05[cut2:] + ch06(full)
}

# --- write the 4 act JSONs with exact concat offsets ---
def wt_before(seg, t):  return [w for w in data[seg]["wt"] if w["begin"] <  t]
def wt_after(seg, t, sub): return [dict(w, begin=round(w["begin"]-sub,3), end=round(w["end"]-sub,3))
                                   for w in data[seg]["wt"] if w["begin"] >= t]
def shift(ws, off): return [dict(w, begin=round(w["begin"]+off,3), end=round(w["end"]+off,3)) for w in ws]
def fr_before(seg,t): return [f for f in data[seg]["fr"] if f["begin"] < t]
def fr_after(seg,t,sub): return [dict(f, begin=round(f["begin"]-sub,3),
                                   **({"end":round(f["end"]-sub,3)} if f.get("end") is not None else {}))
                                 for f in data[seg]["fr"] if f["begin"] >= t]
def fshift(fs,off): return [dict(f, begin=round(f["begin"]+off,3),
                            **({"end":round(f["end"]+off,3)} if f.get("end") is not None else {})) for f in fs]

o1, o2, o3, o4 = D1, (D2-cut1), D4, (D5-cut2)   # second-segment offsets = first-seg durations
acts = {
 1: (data["01"]["wt"] + shift(wt_before("02",cut1), o1),
     data["01"]["fr"] + fshift(fr_before("02",cut1), o1)),
 2: (wt_after("02",cut1,cut1) + shift(data["03"]["wt"], o2),
     fr_after("02",cut1,cut1) + fshift(data["03"]["fr"], o2)),
 3: (data["04"]["wt"] + shift(wt_before("05",cut2), o3),
     data["04"]["fr"] + fshift(fr_before("05",cut2), o3)),
 4: (wt_after("05",cut2,cut2) + shift(data["06"]["wt"], o4),
     fr_after("05",cut2,cut2) + fshift(data["06"]["fr"], o4)),
}
os.makedirs(DST, exist_ok=True)
print("\n== writing act JSONs ==")
for n,(wt,fr) in acts.items():
    wt = [dict(w, begin=max(0.0,w["begin"]), end=max(0.0,w["end"])) for w in wt]
    obj = {"audio_url": PUB+f"chaika-act{n}.mp3", "narrator": data["01"]["narr"],
           "fragments": fr, "word_timings": wt}
    json.dump(obj, open(os.path.join(DST,f"chaika-act{n}.json"),"w",encoding="utf-8"), ensure_ascii=False)
    print(f"  act{n}: {len(wt)} words | first '{wt[0]['word']}'@{wt[0]['begin']}  last '{wt[-1]['word']}'@{wt[-1]['end']}")

print("\n== uploading act MP3s to R2 ==")
for n in (1,2,3,4):
    sh(["aws","s3","cp",act_mp3[n],f"{BUCKET}/chaika-acts/chaika-act{n}.mp3","--content-type","audio/mpeg"])
print("\nDONE. Now commit the JSONs and push:")
print("  git add public/books/audio/chaika-acts && git commit -m 'Чайка: fix act timing' && git push origin main")
