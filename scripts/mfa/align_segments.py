#!/usr/bin/env python3
"""
align_segments.py — run `mfa align` over the short segments, one batch at a time.

Resumable: a batch whose outputs are already complete is skipped, so if the run
dies (or you Ctrl-C it) you just re-run this and it picks up where it left off.
Each batch is a separate MFA process, so a crash costs one batch, not the run.

USAGE
  python align_segments.py                 # align everything not yet done
  python align_segments.py --jobs=2        # fewer parallel jobs = less RAM
  python align_segments.py --only=b003     # redo one batch
  python align_segments.py --status        # just report progress, align nothing

ENV: WP  (and the `aligner` conda env must be active)
"""
import glob
import json
import os
import subprocess
import sys
import time

WP = os.environ.get("WP", "")
if not WP:
    sys.exit("ERROR: export WP first")

SEGROOT = f"{WP}/seg"
OUTROOT = f"{WP}/segout"
LOGDIR = f"{WP}/logs"
DICT = f"{WP}/wp.dict"
ACOUSTIC = os.environ.get("MFA_ACOUSTIC", "russian_mfa")


def opt(name, default):
    for a in sys.argv[1:]:
        if a.startswith(f"--{name}="):
            return a.split("=", 1)[1]
    return default


JOBS = opt("jobs", "3")
ONLY = opt("only", "")
STATUS_ONLY = "--status" in sys.argv
BEAM = opt("beam", "")           # e.g. --beam=100 for stubborn batches
RETRY_BEAM = opt("retry-beam", "")

if not os.path.isdir(SEGROOT):
    sys.exit(f"ERROR: {SEGROOT} missing — run split_corpus.py --build first")
if not os.path.exists(DICT):
    sys.exit(f"ERROR: {DICT} missing — see the g2p/OOV step in the guide")

batches = sorted(d for d in os.listdir(SEGROOT) if os.path.isdir(f"{SEGROOT}/{d}"))
if ONLY:
    want = {x.strip() for x in ONLY.split(",") if x.strip()}
    batches = [b for b in batches if b in want]

os.makedirs(OUTROOT, exist_ok=True)
os.makedirs(LOGDIR, exist_ok=True)


def counts(b):
    n_in = len(glob.glob(f"{SEGROOT}/{b}/*.wav"))
    n_out = len(glob.glob(f"{OUTROOT}/{b}/*.json"))
    return n_in, n_out


print(f"batches: {len(batches)}   jobs={JOBS}   acoustic={ACOUSTIC}")
print(f"{'batch':8} {'wavs':>6} {'aligned':>8}  status")
todo = []
for b in batches:
    n_in, n_out = counts(b)
    done = n_out >= n_in and n_in > 0
    print(f"{b:8} {n_in:6} {n_out:8}  {'done' if done else 'pending'}")
    if not done:
        todo.append(b)

if STATUS_ONLY:
    sys.exit(0)

if not todo:
    print("\nEverything is already aligned. Next: python apply_timings.py")
    sys.exit(0)

print(f"\n{len(todo)} batch(es) to align\n" + "=" * 60)

failed = []
for i, b in enumerate(todo, start=1):
    out = f"{OUTROOT}/{b}"
    os.makedirs(out, exist_ok=True)
    log = f"{LOGDIR}/{b}.log"
    n_in, _ = counts(b)

    cmd = ["mfa", "align", f"{SEGROOT}/{b}", DICT, ACOUSTIC, out,
           "--single_speaker", "--output_format", "json",
           "--num_jobs", str(JOBS), "--clean"]
    if BEAM:
        cmd += ["--beam", BEAM]
    if RETRY_BEAM:
        cmd += ["--retry_beam", RETRY_BEAM]

    print(f"\n[{i}/{len(todo)}] {b}  ({n_in} segments)  log -> {log}")
    t0 = time.time()
    with open(log, "w") as lf:
        rc = subprocess.call(cmd, stdout=lf, stderr=subprocess.STDOUT)
    _, n_out = counts(b)
    dt = time.time() - t0

    if rc != 0 and n_out < n_in:
        print(f"   FAILED rc={rc} after {dt/60:.1f}m — {n_out}/{n_in} written. "
              f"tail of log:")
        try:
            with open(log) as lf:
                for line in lf.readlines()[-6:]:
                    print("     " + line.rstrip())
        except Exception:
            pass
        failed.append(b)
    else:
        note = "" if n_out >= n_in else f"  (partial {n_out}/{n_in}, rc={rc})"
        print(f"   ok in {dt/60:.1f}m — {n_out} aligned{note}")
        if n_out < n_in:
            failed.append(b)

print("\n" + "=" * 60)
total_in = sum(counts(b)[0] for b in batches)
total_out = sum(counts(b)[1] for b in batches)
print(f"aligned {total_out}/{total_in} segments")
if failed:
    print(f"incomplete batches: {', '.join(failed)}")
    print("Re-run this script to retry them, or for a stubborn one:")
    print(f"  python align_segments.py --only={failed[0]} --jobs=1 --beam=100 --retry-beam=400")
else:
    print("all batches complete.")
print("\nNext: python apply_timings.py        # dry run")
print("      python apply_timings.py --write")
