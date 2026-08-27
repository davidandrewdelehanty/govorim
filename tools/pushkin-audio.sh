#!/usr/bin/env bash
# Stage LibriVox Pushkin audio: upload the mp3s to R2 and write the per-chapter
# JSONs the catalogue points at.
#
# No alignment is involved. The JSONs carry audio_url with empty fragments —
# the same shape gore-ot-uma uses — so the reader gets a working player with a
# time scrubber. MFA alignment can be added later without changing these files.
#
#   bash tools/pushkin-audio.sh            # show the plan, touch nothing
#   bash tools/pushkin-audio.sh --upload   # copy to R2 and write the JSONs
#
# RCLONE_S3_NO_CHECK_BUCKET is set below because the R2 token is bucket-scoped:
# without it a single-file copy probes CreateBucket and R2 answers 403.
set -u
cd "$(dirname "$0")/.."
LV="$HOME/mnt/audiobooks/books with librivox"
[ -d "$LV" ] || LV="/mnt/c/Users/david/Downloads/audiobooks/books with librivox"
R2_PUBLIC="https://pub-84adcd23e17e4925a0ac7eca17ea2556.r2.dev"
UPLOAD=0; for a in "$@"; do [ "$a" = "--upload" ] && UPLOAD=1; done

# slug | source folder | space-separated source files, in reading order
WORKS='
pushkin-gavriiliada|poems - pushkin|poemi_12_pushkin_64kb.mp3
pushkin-bratya-razboyniki|poems - pushkin|poemi_13_pushkin_64kb.mp3
pushkin-bakhchisaraysky-fontan|poems - pushkin|poemi_14_pushkin_64kb.mp3
pushkin-graf-nulin|poems - pushkin|poemi_16_pushkin_64kb.mp3
pushkin-tazit|poems - pushkin|poemi_20_pushkin_64kb.mp3
pushkin-domik-v-kolomne|poems - pushkin|poemi_21_pushkin_64kb.mp3
pushkin-bova|poems - pushkin|poemi_31_pushkin_64kb.mp3
pushkin-vadim|poems - pushkin|poemi_34_pushkin_64kb.mp3
pushkin-ya-vas-lyubil|ya vas lyiubil - pushkin|msw013_18yavaslyubil_pushkin_eep_64kb.mp3
pushkin-istina|istina - pushkin|msw010_istina_pushkin_sap_64kb.mp3
pushkin-krasavitsa|krasavitsa pushkin|alexander-pushkin-krasavitse_64kb.mp3
pushkin-tsygany|poems - pushkin|poemi_15_pushkin_64kb.mp3
pushkin-ispoved|poems - pushkin|poemi_32_pushkin_64kb.mp3
pushkin-yudif|poems - pushkin|poemi_37_pushkin_64kb.mp3
pushkin-poltava|poems - pushkin|poemi_17_pushkin_64kb.mp3 poemi_18_pushkin_64kb.mp3 poemi_19_pushkin_64kb.mp3
pushkin-kavkazsky-plennik|poems - pushkin|poemi_08_pushkin_64kb.mp3 poemi_09_pushkin_64kb.mp3 poemi_10_pushkin_64kb.mp3 poemi_11_pushkin_64kb.mp3
pushkin-andzhelo|poems - pushkin|poemi_22_pushkin_64kb.mp3 poemi_23_pushkin_64kb.mp3 poemi_24_pushkin_64kb.mp3
pushkin-medny-vsadnik|poems - pushkin|poemi_25_pushkin_64kb.mp3 poemi_26_pushkin_64kb.mp3 poemi_27_pushkin_64kb.mp3
pushkin-monakh|poems - pushkin|poemi_28_pushkin_64kb.mp3 poemi_29_pushkin_64kb.mp3 poemi_30_pushkin_64kb.mp3
pushkin-ruslan-i-lyudmila|poems - pushkin|poemi_01_pushkin_64kb.mp3 poemi_02_pushkin_64kb.mp3 poemi_03_pushkin_64kb.mp3 poemi_04_pushkin_64kb.mp3 poemi_05_pushkin_64kb.mp3 poemi_06_pushkin_64kb.mp3 poemi_07_pushkin_64kb.mp3
'

ok=0; miss=0
while IFS='|' read -r slug folder files; do
  [ -z "${slug:-}" ] && continue
  n=0; bad=0
  for f in $files; do
    [ -f "$LV/$folder/$f" ] || { echo "  !! missing: $folder/$f"; bad=1; }
    n=$((n+1))
  done
  [ "$bad" = "1" ] && { miss=$((miss+1)); continue; }
  printf '  %-32s %d track(s)\n' "$slug" "$n"
  ok=$((ok+1))

  [ "$UPLOAD" = "0" ] && continue

  mkdir -p "public/books/audio/$slug"
  i=0; chapters=""
  for f in $files; do
    i=$((i+1)); nn=$(printf '%02d' "$i")
    RCLONE_S3_NO_CHECK_BUCKET=true rclone copyto "$LV/$folder/$f" \
      "r2:govorim-audio/$slug/$nn.mp3" 2>&1 | sed 's/^/       /'
    printf '{"audio_url": "%s/%s/%s.mp3", "narrator": "LibriVox", "fragments": []}\n' \
      "$R2_PUBLIC" "$slug" "$nn" > "public/books/audio/$slug/$slug-ch$nn.json"
    chapters="$chapters\"audio/$slug/$slug-ch$nn.json\", "
  done
  printf '       chapters: [%s]\n' "${chapters%, }"
done <<< "$WORKS"

echo
echo "ready $ok   missing files $miss"
if [ "$UPLOAD" = "0" ]; then
  echo "run again with --upload to copy to R2 and write the chapter JSONs"
else
  echo "JSONs written under public/books/audio/ — commit them from Git Bash."
fi
