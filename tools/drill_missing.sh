#!/usr/bin/env bash
# Generate case drills for every catalogue book that is missing them.
#
# A book qualifies only if it has a parallelEn translation — make_case_drills.py
# pulls each drill's English sentence from there, and skips books without one.
# Books that already have drill files are left alone (the tool never overwrites
# without --force anyway, but skipping them keeps the run short).
#
# Some books are skipped by default (see SKIP below) — verse works, where the
# drills want prose sentences, plus anything deliberately left alone. The run
# always prints what it skipped, so nothing goes missing quietly; --no-skip
# turns the list off.
#
# Usage:   bash tools/drill_missing.sh              # every catalogue book
#          bash tools/drill_missing.sh --list       # just show what would run
#          bash tools/drill_missing.sh --public     # only books on Samovar
#          bash tools/drill_missing.sh --no-skip    # ignore the skip list
set -u
ONLY_PUBLIC=0
NO_SKIP=0
for a in "$@"; do
  [ "$a" = "--public" ] && ONLY_PUBLIC=1
  [ "$a" = "--no-skip" ] && NO_SKIP=1
done
export ONLY_PUBLIC NO_SKIP
cd "$(dirname "$0")/.."

# Skipped unless --no-skip. Keyed on the FB2 filename, with the reason, so a
# future reader can tell a deliberate omission from an oversight.
SKIP_REASONS=$(cat <<'SKIPLIST'
pushkin-bakhchisaraysky-fontan.fb2|verse — drills need prose sentences
pushkin-medny-vsadnik.fb2|verse — drills need prose sentences
pushkin-kavkazsky-plennik.fb2|verse — drills need prose sentences
pushkin-tsygany.fb2|verse — drills need prose sentences
pushkin-poltava.fb2|verse — drills need prose sentences
pushkin-ya-vas-lyubil.fb2|verse — drills need prose sentences
lermontov-demon.fb2|verse, and its English is keyed per section not per paragraph
keyes-tsvety-dlya-eldzhernona.fb2|left alone deliberately
SKIPLIST
)
export SKIP_REASONS

mapfile -t BOOKS < <(python3 - << 'PY'
import json, os, re
d = json.load(open('private/books/index.json', encoding='utf-8'))
ex = os.listdir('public/books/exercises') if os.path.isdir('public/books/exercises') else []
only_public = os.environ.get('ONLY_PUBLIC') == '1'
no_skip = os.environ.get('NO_SKIP') == '1'
skip = {}
for line in (os.environ.get('SKIP_REASONS') or '').splitlines():
    if '|' in line:
        k, _, why = line.partition('|')
        skip[k.strip()] = why.strip()
for e in d:
    if not e.get('parallelEn'):
        continue
    if only_public and not e.get('public'):
        continue
    fn = e.get('filename', '')
    base = os.path.basename(fn)
    slug = re.sub(r'[^A-Za-z0-9_-]', '_', re.sub(r'\.[^.]+$', '', base))
    if any(f.startswith(slug + '__') for f in ex):
        continue
    if not no_skip and base in skip:
        print('SKIP\t%s\t%s' % (e.get('title', ''), skip[base]))
        continue
    print('%s\t%s' % (base, e.get('title', '')))
PY
)

# Split the skip notices out of the work list.
SKIPPED=()
KEEP=()
for row in "${BOOKS[@]:-}"; do
  case "$row" in
    SKIP$'\t'*) SKIPPED+=("${row#SKIP$'\t'}") ;;
    "") ;;
    *) KEEP+=("$row") ;;
  esac
done
if [ "${#SKIPPED[@]}" -gt 0 ]; then
  echo "Skipping ${#SKIPPED[@]} book(s) (--no-skip to include them):"
  for row in "${SKIPPED[@]}"; do
    printf '   %-34s %s\n' "${row%%$'\t'*}" "${row#*$'\t'}"
  done
  echo
fi
BOOKS=("${KEEP[@]:-}")
[ -z "${BOOKS[0]:-}" ] && BOOKS=()

if [ "${#BOOKS[@]}" -eq 0 ]; then
  echo "Nothing to do — every parallelEn book already has drills."
  exit 0
fi

echo "${#BOOKS[@]} book(s) missing drills:"
for row in "${BOOKS[@]}"; do
  printf '   %s\n' "${row#*$'\t'}"
done
echo

for a in "$@"; do [ "$a" = "--list" ] && exit 0; done

for row in "${BOOKS[@]}"; do
  fb2="${row%%$'\t'*}"
  title="${row#*$'\t'}"
  echo "=== $title  ($fb2)"
  python3 tools/make_case_drills.py --book "$fb2" || echo "  !! failed: $fb2"
  echo
done

echo "Done. Review public/books/exercises/, then commit from Git Bash."
