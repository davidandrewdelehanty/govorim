#!/bin/bash
# Run align_video.py over a slice of tools/captions/signature-books.txt.
#   bash tools/align_batch.sh 0 5      # books 0..4
set -u
from=$1; to=$2
mapfile -t SLUGS < tools/captions/signature-books.txt
for ((i=from; i<to && i<${#SLUGS[@]}; i++)); do
  s="${SLUGS[$i]}"
  out="tools/timings-$s.csv"
  res=$(timeout 150 python3 tools/align_video.py --slug "$s" --vtt-dir tools/captions --out "$out" 2>&1)
  line=$(echo "$res" | grep -E "chapters matched|counts differ|FATAL|no book" | head -2 | tr '\n' ' ')
  printf "%-3d %-38s %s\n" "$i" "$s" "${line:-no output}"
done
