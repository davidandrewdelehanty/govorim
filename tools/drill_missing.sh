#!/usr/bin/env bash
# Generate case drills for every catalogue book that is missing them.
#
# A book qualifies only if it has a parallelEn translation — make_case_drills.py
# pulls each drill's English sentence from there, and skips books without one.
# Books that already have drill files are left alone (the tool never overwrites
# without --force anyway, but skipping them keeps the run short).
#
# Usage:   bash tools/drill_missing.sh           # run them
#          bash tools/drill_missing.sh --list    # just show what would run
set -u
cd "$(dirname "$0")/.."

mapfile -t BOOKS < <(python3 - << 'PY'
import json, os, re
d = json.load(open('private/books/index.json', encoding='utf-8'))
ex = os.listdir('public/books/exercises') if os.path.isdir('public/books/exercises') else []
for e in d:
    if not e.get('parallelEn'):
        continue
    fn = e.get('filename', '')
    slug = re.sub(r'[^A-Za-z0-9_-]', '_', re.sub(r'\.[^.]+$', '', os.path.basename(fn)))
    if any(f.startswith(slug + '__') for f in ex):
        continue
    print('%s\t%s' % (os.path.basename(fn), e.get('title', '')))
PY
)

if [ "${#BOOKS[@]}" -eq 0 ]; then
  echo "Nothing to do — every parallelEn book already has drills."
  exit 0
fi

echo "${#BOOKS[@]} book(s) missing drills:"
for row in "${BOOKS[@]}"; do
  printf '   %s\n' "${row#*$'\t'}"
done
echo

if [ "${1:-}" = "--list" ]; then exit 0; fi

for row in "${BOOKS[@]}"; do
  fb2="${row%%$'\t'*}"
  title="${row#*$'\t'}"
  echo "=== $title  ($fb2)"
  python3 tools/make_case_drills.py --book "$fb2" || echo "  !! failed: $fb2"
  echo
done

echo "Done. Review public/books/exercises/, then commit from Git Bash."
