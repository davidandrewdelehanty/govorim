#!/usr/bin/env python3
"""EN pairing / sync-map / manifest consequences of the RU text cleanup."""
import json, os, re, sys
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
B = os.path.join(ROOT, "public", "books")
SY = os.path.join(B, "audio-sync")

def jload(p):  return json.load(open(p, encoding="utf-8"))
def jsave(p,d): json.dump(d, open(p,"w",encoding="utf-8"), ensure_ascii=False, indent=0)

def shift_keys(d, delta, from_idx=0):
    out={}
    for k,v in d.items():
        i=int(k)
        if i < from_idx: out[str(i)]=v
        else:
            ni=i+delta
            if ni>=from_idx if delta<0 else True:
                if ni>=0: out[str(ni)]=v
    return out

def shift_file(p, delta, from_idx=0, drop=()):
    if not os.path.exists(p): return "absent"
    d=jload(p)
    for k in drop: d.pop(str(k), None)
    d=shift_keys(d, delta, from_idx)
    jsave(p,d); return "ok n=%d"%len(d)

def sync_shift(base, delta, from_idx=0):
    p=os.path.join(SY, base, "01.json")
    print("  sync", base, shift_file(p, delta, from_idx))

log=print
# ---- head-trim shifts ----
log("asya:", shift_file(B+"/asya-en/01.json", -1, drop=[413])); sync_shift("asya", -1)
log("pervaya-lyubov:", shift_file(B+"/pervaya-lyubov-en/01.json", -2)); sync_shift("pervaya-lyubov", -2)
# remap 0 -> 1 (dedication row shift)
p=B+"/pervaya-lyubov-en/01.json"; d=jload(p)
if "0" in d and "1" not in d: d["1"]=d.pop("0")
jsave(p,d)
log("rudin:", shift_file(B+"/rudin-en/01.json", -2, drop=[0,1,2])); sync_shift("rudin", -2)
sync_shift("veshnie-vody", -2)
log("dym01 emptied"); jsave(B+"/dym-en/01.json", {})
log("dym02:", shift_file(B+"/dym-en/02.json", 0, drop=[0,1])); sync_shift("dym", -2)
sync_shift("nov", -2)
for base in ("moya-zhizn","skuchnaya-istoriya","kashtanka","falshivyy-kupon"):
    sync_shift(base, -1)
sync_shift("step", -1, from_idx=1)
log("mnogo-li:", shift_file(B+"/mnogo-li-cheloveku-zemli-nuzhno-en/01.json", -1)); sync_shift("mnogo-li-cheloveku-zemli-nuzhno", -1)
log("chem-lyudi:", shift_file(B+"/chem-lyudi-zhivy-en/01.json", -1)); sync_shift("chem-lyudi-zhivy", -1)
p=B+"/chem-lyudi-zhivy-en/01.json"; d=jload(p)
if "0" in d and "1" not in d: d["1"]=d.pop("0")
jsave(p,d)
log("belye-nochi:", shift_file(B+"/dostoevsky-belye-nochi-en/01.json", -1)); sync_shift("dostoevsky-belye-nochi", -1)
sync_shift("pushkin-graf-nulin", -1)
sync_shift("pushkin-ispoved", -1)
# inserts
sync_shift("pushkin-ruslan-i-lyudmila", +1)
log("bakh:", shift_file(B+"/pushkin-bakhchisaraysky-fontan-en/01.json", +3)); sync_shift("pushkin-bakhchisaraysky-fontan", +3)
p=B+"/pushkin-bakhchisaraysky-fontan-en/01.json"; d=jload(p)
if "4" in d and "2" not in d and "0" not in d: d["2"]=d.pop("4")
jsave(p,d)
# ---- tail-section deletions ----
for p in (B+"/vechnyy-muzh-en/18.json", SY+"/vechnyy-muzh/18.json", SY+"/dostoevsky-prestuplenie/42.json"):
    if os.path.exists(p): os.remove(p); log("removed", p[len(B)+1:])
# ---- EN junk edits ----
def edit(p, fn):
    d=jload(p); d=fn(d); jsave(p,d); log("edited", p[len(B)+1:], "n=%d"%len(d))
edit(B+"/viy-en/01.json", lambda d:(d.pop("275",None), d)[1])
edit(B+"/olesya-en/14.json", lambda d:(d.pop("16",None), d)[1])
jsave(B+"/na-dne-en/01.json", {}); log("na-dne 01 emptied")
def nadne5(d):
    d.pop("229",None)
    if "228" in d: d["228"]=d["228"].split("This transcription")[0].strip()
    return d
edit(B+"/na-dne-en/05.json", nadne5)
def golov(d):
    i=d["0"].find("One day the bailiff")
    if i>0: d["0"]=d["0"][i:]
    return d
edit(B+"/gospoda-golovlevy-en/01.json", golov)
def nak(d):
    i=d["2"].find("On one of the hottest days")
    if i>0: d["2"]=d["2"][i:]
    return d
edit(B+"/nakanune-en/01.json", nak)
jsave(B+"/yunost-en/01.json", {}); log("yunost 01 emptied")
edit(B+"/yunost-en/02.json", lambda d:(d.pop("0",None),d.pop("1",None),d)[2])
def poed(d):
    for k in ("4","5","6","7"): d.pop(k,None)
    return d
edit(B+"/poedinok-en/23.json", poed)
def krasny(d):
    d["50"]="THE END"
    return d
edit(B+"/krasnyy-smekh-en/18.json", krasny)
def sulam(d):
    for k in [k for k in d if int(k)>75]: d.pop(k)
    return d
edit(B+"/sulamif-en/13.json", sulam)
# son-makara restructure
p1,p2=B+"/son-makara-en/01.json",B+"/son-makara-en/02.json"
o1,o2=jload(p1),jload(p2)
first=o1.get("4","")
if first:
    n2=dict(o2)
    n2["0"]=(first+"\n\n"+o2.get("0","")).strip()
    jsave(p2,n2)
    jsave(p1,{"0":"A Christmas Story"})
    log("son-makara restructured")
print("done")
