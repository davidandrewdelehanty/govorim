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
RETRY_PARTIAL = "--retry-partial" in sys.argv
MARK_DONE = "--mark-done" in sys.argv
# MFA routinely leaves ~0.5% of segments unaligned (beam failures on a bad
# transcript match). Chasing them costs a full batch re-run for a few files that
# will fail again, and apply_timings.py interpolates + flags them anyway. So a
# batch counts as finished once this share of it aligned.
COMPLETE_AT = float(opt("complete-at", 0.98))

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


def stem(p):
    return os.path.splitext(os.path.basename(p))[0]


def missing_ids(b):
    ins = {stem(p) for p in glob.glob(f"{SEGROOT}/{b}/*.wav")}
    outs = {stem(p) for p in glob.glob(f"{OUTROOT}/{b}/*.json")}
    return sorted(ins - outs)


def marker(b):
    return f"{OUTROOT}/{b}/.complete"


def record_done(b):
    """Write the completion marker + the list of segments MFA could not align."""
    miss = missing_ids(b)
    os.makedirs(f"{OUTROOT}/{b}", exist_ok=True)
    n_in, n_out = counts(b)
    with open(marker(b), "w") as fh:
        fh.write(f"{n_out}/{n_in}\n")
    if miss:
        with open(f"{LOGDIR}/{b}.missing.txt", "w") as fh:
            fh.write("\n".join(miss) + "\n")
    return miss


def is_done(b):
    n_in, n_out = counts(b)
    if n_in == 0:
        return False
    if os.path.exists(marker(b)) and not RETRY_PARTIAL:
        return True
    if n_out >= n_in:
        return True
    # tolerate MFA's normal handful of unalignable segments
    return (not RETRY_PARTIAL) and n_out >= n_in * COMPLETE_AT


if MARK_DONE:
    # Backfill markers for batches aligned by an earlier run of this script.
    n = 0
    for b in batches:
        _, n_out = counts(b)
        if n_out:
            miss = record_done(b)
            n += 1
            print(f"{b}: marked done"
                  + (f" ({len(miss)} segment(s) unaligned -> {LOGDIR}/{b}.missing.txt)"
                     if miss else ""))
    print(f"\nmarked {n} batch(es). Future runs will skip them.")
    sys.exit(0)

print(f"batches: {len(batches)}   jobs={JOBS}   acoustic={ACOUSTIC}   "
      f"complete-at={COMPLETE_AT:.0%}")
print(f"{'batch':8} {'wavs':>6} {'aligned':>8} {'pct':>6}  status")
todo = []
for b in batches:
    n_in, n_out = counts(b)
    done = is_done(b)
    pct = (n_out / n_in) if n_in else 0.0
    print(f"{b:8} {n_in:6} {n_out:8} {pct:6.1%}  {'done' if done else 'pending'}")
    if not done:
        todo.append(b)

if STATUS_ONLY:
    tot_in = sum(counts(b)[0] for b in batches)
    tot_out = sum(counts(b)[1] for b in batches)
    print(f"\n{tot_out}/{tot_in} segments aligned ({(tot_out/tot_in if tot_in else 0):.1%})"
          f"   {len(batches)-len(todo)}/{len(batches)} batches done")
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

    if rc == 0 or n_out >= n_in * COMPLETE_AT:
        record_done(b)

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
        miss = missing_ids(b)
        note = "" if not miss else (
            f"  ({len(miss)} of {n_in} unaligned — listed in {LOGDIR}/{b}.missing.txt)")
        print(f"   ok in {dt/60:.1f}m — {n_out} aligned{note}")
        if not is_done(b):
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
    print("A few unaligned segments per batch is normal — apply_timings.py "
          "interpolates them and flags the chapter.")
    print("To force a retry of those anyway:  align_segments.py --retry-partial")
print("\nNext: python apply_timings.py        # dry run")
print("      python apply_timings.py --write")
