#!/usr/bin/env bash
# Generate case drills for every catalogue book that is missing them.
#
# It used to require a parallelEn translation, because a drill once showed the
# English of the sentence it had blanked. It no longer does — see the RETIRED
# note in make_case_drills.py — so that requirement was guarding a field that
# does not exist and holding two thirds of the library out of drills. Gone.
#
# What remains is the verse rule: a drill blanks an adjective-noun pair out of
# a running sentence, and a line of Пушкин is not one. The index has no `verse`
# flag (an earlier version of this comment claimed otherwise; nothing sets it),
# so the category is the test and Poetry is verse.
#
# Books that already have drill files are left alone (the tool never overwrites
# without --force anyway, but skipping them keeps the run short).
#
# The SKIP list below is for individual exceptions — works still in copyright,
# and anything deliberately left alone. The run always prints what it skipped,
# so nothing goes missing quietly; --no-skip turns the list off.
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
# The verse works are caught by the category test now, so this list is what
# it was always for: the individual exceptions. The copyright dates are the
# Russian term, life of the author plus seventy, with the four-year wartime
# extension where it applies — a drill quotes one sentence, which is a small
# use, but committing extracts of a work still in copyright is a decision to
# take deliberately rather than by running a script over the whole shelf.
SKIP_REASONS=$(cat <<'SKIPLIST'
lermontov-demon.fb2|verse, and its English is keyed per section not per paragraph
keyes-tsvety-dlya-eldzhernona.fb2|left alone deliberately
zhivago-parts.fb2|Pasternak d.1960 — still in copyright in Russia
tixi don.fb2|Sholokhov d.1984 — still in copyright in Russia
«Денискины рассказы».fb2|Dragunsky d.1972 — still in copyright in Russia
patriot.fb2|authorship and term not established
Новый Русский Перевод Библии — по главам.fb2|modern translation, still in copyright
bible-synodal.fb2|the Bible has its own keying — use make_case_drills.py --bible
brezhnev-oktyabr-60-1977.fb2|Brezhnev d.1982 — still in copyright in Russia
brezhnev-den-pobedy-1975.fb2|Brezhnev d.1982 — still in copyright in Russia
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
    # Case drills need prose sentences, and the shelf a book sits on is the
    # only thing in the catalogue that says whether it is verse.
    if e.get('category') == 'Poetry':
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
  echo "Nothing to do — every prose book already has drills."
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
