#!/usr/bin/env bash
# Fetch Pushkin's narrative poems from ru.wikisource as FB2, one per work.
#
# The numbered tracks are from the LibriVox "Поэмы" recording in
# Downloads/audiobooks/books with librivox/poems - pushkin/. The last three
# entries are standalone lyrics whose audio lives in its OWN folder — they are
# not part of that recording, which is why they are labelled by folder.
#
#   bash tools/pushkin-poems.sh            # summary: what each page yields
#   bash tools/pushkin-poems.sh --fetch    # write the FB2s
#
# A page that cannot be found is reported with search suggestions rather than
# skipped silently — Wikisource titles are not always "<Название> (Пушкин)".
set -u
cd "$(dirname "$0")/.."
FETCH=0; for a in "$@"; do [ "$a" = "--fetch" ] && FETCH=1; done

# title on ru.wikisource | output slug | audio tracks
WORKS='
Руслан и Людмила (Пушкин)|pushkin-ruslan-i-lyudmila|01-07
Кавказский пленник (Пушкин)|pushkin-kavkazsky-plennik|08-11
Гавриилиада (Пушкин)|pushkin-gavriiliada|12
Братья разбойники (Пушкин)|pushkin-bratya-razboyniki|13
Бахчисарайский фонтан (Пушкин)|pushkin-bakhchisaraysky-fontan|14
Цыганы (поэма — Пушкин)|pushkin-tsygany|15
Граф Нулин (Пушкин)|pushkin-graf-nulin|16
Полтава (Пушкин)|pushkin-poltava|17-19
Тазит (Пушкин)|pushkin-tazit|20
Домик в Коломне (Пушкин)|pushkin-domik-v-kolomne|21
Анджело (Пушкин)|pushkin-andzhelo|22-24
Медный всадник (Пушкин)|pushkin-medny-vsadnik|25-27
Монах (Пушкин)|pushkin-monakh|28-30
Бова (Пушкин)|pushkin-bova|31
# «Исповедь» is titled by first line on Wikisource; a bare title search lands
# on «Исповедь бедного стихотворца», a different and much earlier piece.
Я вас люблю хоть я бешусь Пушкин|pushkin-ispoved|32|4
Вадим (Пушкин)|pushkin-vadim|34
# Езерский: ru.wikisource carries only «Родословная моего героя», the excerpt
# Pushkin published separately — not the whole poem. Left out rather than
# catalogued under a title whose text does not match the recording.
# Родословная моего героя (Пушкин)|pushkin-ezersky|36|4
Юдифь Пушкин|pushkin-yudif|37|4
Я вас любил Пушкин|pushkin-ya-vas-lyubil|folder: ya vas lyiubil|4
Истина Пушкин|pushkin-istina|folder: istina - pushkin|4
Красавице Пушкин|pushkin-krasavitsa|folder: krasavitsa pushkin|4
'

ok=0; missing=0; suspect=0
printf '  %-34s %-10s %5s %4s  %s\n' "work" "licence" "lines" "secs" "sections"
printf '  %-34s %-10s %5s %4s  %s\n' "----" "-------" "-----" "----" "--------"

while IFS='|' read -r title slug tracks min; do
  min=${min:-40}
  # A short lyric is resolved by search, since Wikisource titles it by first line.
  SEARCH=""; [ "$min" -lt 40 ] && SEARCH="--search"
  [ -z "${title:-}" ] && continue
  # WORKS is a quoted string, so a leading # is data, not a shell comment.
  case "$title" in \#*) continue;; esac
  out=$(node tools/wikisource-fb2.mjs show "$title" $SEARCH 2>&1)
  if echo "$out" | grep -q "^FAILED"; then
    missing=$((missing+1))
    printf '  %-40s %s\n' "$title" "NOT FOUND"
    printf '        (run: node tools/wikisource-fb2.mjs search "%s")\n' "${title%% (*}"
    continue
  fi
  res=$(echo "$out"  | sed -n 's/^resolved: *//p' | head -1)
  lic=$(echo "$out"  | sed -n 's/^licence *: *//p')
  lines=$(echo "$out"| sed -n 's/^lines *: *//p')
  secs=$(echo "$out" | sed -n 's/^sections: *//p')
  warn=""
  [ "${lines:-0}" -lt "$min" ] 2>/dev/null && warn="  <-- SUSPECT: too few lines, probably an index page"
  # The section COUNT is what has to match the audio track list, so it gets a
  # column of its own — the names are truncated and were hiding a miscount.
  nsec=$(echo "$secs" | awk -F'\\|' '{print NF}')
  [ -z "$secs" ] && nsec=0
  printf '  %-34s %-10s %5s %4s  %s%s\n' "$(echo "${res:-$title}" | cut -c1-34)" "${lic:0:10}" "${lines:-?}" "$nsec" "${secs:0:36}" "$warn"
  ok=$((ok+1))
  [ -n "$warn" ] && { suspect=$((suspect+1)); [ "$FETCH" = "1" ] && { printf '%8s skipped — refusing to write a near-empty FB2\n' ""; sleep 1.5; continue; }; }
  if [ "$FETCH" = "1" ]; then
    node tools/wikisource-fb2.mjs fetch "$title" \
      --out "public/books/novel/${slug}.fb2" --author "Александр Сергеевич Пушкин" $SEARCH >/dev/null 2>&1 \
      && printf '%38s-> public/books/novel/%s.fb2   (audio %s)\n' "" "$slug" "$tracks" \
      || printf '%38s!! fetch failed\n' ""
  fi
  sleep 1.5
done <<< "$WORKS"

echo
echo "found $ok   suspect $suspect   not found $missing"
[ "$FETCH" = "0" ] && echo "run again with --fetch to write the FB2s"
