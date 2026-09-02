#!/bin/bash
# Run align_video.py over a slice of a slug list.
#   bash tools/align_batch.sh <listfile> 0 7
set -u
list=$1; from=$2; to=$3
mapfile -t SLUGS < "$list"
for ((i=from; i<to && i<${#SLUGS[@]}; i++)); do
  s="${SLUGS[$i]}"
  res=$(timeout 150 python3 tools/align_video.py --slug "$s" --vtt-dir tools/captions --out "tools/timings-$s.csv" 2>&1)
  line=$(echo "$res" | grep -E "chapters matched|counts differ|FATAL|no book" | head -2 | tr '\n' ' ')
  printf "%-3d %-44s %s\n" "$i" "$s" "${line:-no output}"
done
