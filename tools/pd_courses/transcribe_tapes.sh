#!/usr/bin/env bash
# Word timings for the course tapes, with faster-whisper — the same transcriber
# the audiobooks use (scripts/alignment/transcribe.py). The timings are what
# the lesson text is matched against, so each dialogue can be cut out of its
# tape as a clip of its own.
#
# Run in WSL, in the aeneas conda environment from the audiobook runbook:
#     source ~/miniforge3/bin/activate && conda activate aeneas
#     bash tools/pd_courses/transcribe_tapes.sh            # the FSI FAST tapes
#     bash tools/pd_courses/transcribe_tapes.sh dli-basic  # the DLI tapes, once they come down
#
# A tape already transcribed is skipped, so the script can be stopped and
# run again. The FAST tapes are about an hour each; expect a few hours in all.
set -u
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
WHICH="${1:-fsi-fast}"
case "$WHICH" in
  fsi-fast)  AUDIO="$ROOT/_to_delete/pd/fsi-fast/audio" ;;
  dli-basic) AUDIO="$ROOT/_to_delete/pd/dli-basic/audio" ;;
  *) echo "which tapes? fsi-fast | dli-basic"; exit 1 ;;
esac
OUT="$AUDIO/../words"; mkdir -p "$OUT"
MODEL="${MODEL:-small}"
for mp3 in "$AUDIO"/*.mp3; do
  base="$(basename "$mp3" .mp3)"
  json="$OUT/$base.$MODEL.words.json"
  if [ -s "$json" ]; then echo "   have  $base"; continue; fi
  echo "== $base"
  python3 "$ROOT/scripts/alignment/transcribe.py" --audio "$mp3" --output "$json" --model "$MODEL" --language ru || echo "   ! failed: $base"
done
echo "Done → $OUT"; ls -la "$OUT"
