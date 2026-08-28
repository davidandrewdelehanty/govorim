#!/usr/bin/env bash
# Download every English translation and Russian original in the Самовар
# sourcing ledger, in one run.
#
#   bash tools/fetch_sources.sh              # everything
#   bash tools/fetch_sources.sh --tier1      # marquee works only, ~35 titles
#   bash tools/fetch_sources.sh --en         # English side only
#   bash tools/fetch_sources.sh --ru         # Russian side only
#   bash tools/fetch_sources.sh --retry      # re-attempt only what failed before
#
# Output:  ../govorim-sources/en/<slug>.epub   (or .txt where no EPUB exists)
#          ../govorim-sources/ru/<slug>.fb2    (or .epub / .txt)
#          ../govorim-sources/_log.tsv         every attempt, with HTTP status
#          ../govorim-sources/_manual.txt      what needs collecting by hand
#
# A sibling of the repo, so 160-odd source files never end up in git. Already
# downloaded files are skipped, so ctrl-C and re-run is always safe.
#
# There is no configuration and no probe step: for each host the script tries
# the candidate URL forms in turn and keeps the first that returns real data,
# reporting at the end which form worked. The 93 unique Gutenberg volumes are
# fetched once each and copied to the works that share them — 136 ledger rows
# come from those 93 files, so this is a third fewer requests than the naive
# loop, which matters because Gutenberg blocks IPs that hammer it.

set -uo pipefail
cd "$(dirname "$0")/.." || exit 1

MANIFEST="tools/data/sources.tsv"
OUT="../govorim-sources"
UA="Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0 Safari/537.36"
PAUSE_PG=2          # Gutenberg: be a good citizen, they ban scrapers
PAUSE_WS=1          # Wikimedia: fine with a steadier rate
DO_EN=1; DO_RU=1; ONLY_TIER=""; RETRY=0

for a in "$@"; do
  case "$a" in
    --en) DO_RU=0 ;;
    --ru) DO_EN=0 ;;
    --tier1) ONLY_TIER=1 ;;
    --tier2) ONLY_TIER=2 ;;
    --tier3) ONLY_TIER=3 ;;
    --retry) RETRY=1 ;;
  esac
done

[ -f "$MANIFEST" ] || { echo "Cannot find $MANIFEST — run this from the repo root."; exit 1; }
command -v curl >/dev/null || { echo "curl is required."; exit 1; }
HAVE_PY=0; command -v python3 >/dev/null && HAVE_PY=1
HAVE_ICONV=0; command -v iconv >/dev/null && HAVE_ICONV=1

mkdir -p "$OUT/en" "$OUT/ru" "$OUT/.cache"
LOG="$OUT/_log.tsv"; MAN="$OUT/_manual.txt"
[ -f "$LOG" ] || printf 'when\tside\tslug\tstatus\tbytes\tvia\n' > "$LOG"
# --retry re-attempts only what failed last time, so a run that lost twenty
# titles to a flaky connection costs twenty requests, not a hundred and sixty.
RETRY_SET=""
if [ "$RETRY" = "1" ] && [ -f "$MAN" ]; then
  RETRY_SET=$(awk '{print $2}' "$MAN" | sort -u)
  say_n=$(printf '%s\n' "$RETRY_SET" | grep -c . || true)
  echo "Retrying $say_n titles that failed on the last run."
fi
: > "$MAN"

log(){ printf '%s\t%s\t%s\t%s\t%s\t%s\n' "$(date +%H:%M:%S)" "$1" "$2" "$3" "$4" "$5" >> "$LOG"; }
manual(){ printf '%s\n' "$1" >> "$MAN"; }

urlenc(){
  if [ "$HAVE_PY" = "1" ]; then
    python3 -c 'import sys,urllib.parse;print(urllib.parse.quote(sys.argv[1],safe=""))' "$1"
  else
    printf '%s' "$1" | od -An -tx1 -v | tr ' ' '\n' | grep -v '^$' \
      | while read -r h; do
          case "$h" in
            3[0-9]|4[1-9a-f]|5[0-9a]|6[1-9a-f]|7[0-9a]|2d|2e|5f|7e) printf "\\x$h" ;;
            *) printf '%%%s' "$(printf '%s' "$h" | tr 'a-f' 'A-F')" ;;
          esac
        done
  fi
}

# fetch URL FILE → echoes "httpcode bytes"; leaves FILE on disk
fetch(){
  curl -sSL --compressed -A "$UA" --max-time 240 --retry 1 --retry-delay 3 \
       -w '%{http_code} %{size_download}' -o "$2" "$1" 2>/dev/null || echo "000 0"
}
is_zip(){ [ -s "$1" ] && [ "$(head -c 2 "$1" 2>/dev/null)" = "PK" ]; }
# a real text file: big enough, and actually contains letters of the right script
# 1200 bytes, not 3000: a short lyric or a two-page Chekhov sketch is a real
# text, and the HTML check is what actually rejects error pages.
is_text(){ [ -s "$1" ] && [ "$(wc -c < "$1")" -gt 1200 ] && ! grep -qi '<!doctype html' "$1" 2>/dev/null; }
has_cyrillic(){ head -c 20000 "$1" 2>/dev/null | grep -qP '[\x{0400}-\x{04FF}]' 2>/dev/null || \
                head -c 20000 "$1" 2>/dev/null | grep -q $'\xd0\|\xd1'; }

n_en=0; n_ru=0; skip=0; fail_en=0; fail_ru=0
declare -A PG_CACHE          # pg id → file in .cache that already worked
via_pg=""; via_ru=""

say(){ printf '%s\n' "$*"; }
say "Downloading into $(cd "$OUT" && pwd)"
say "English: Project Gutenberg + archive.org · Russian: az.lib.ru + ru.wikisource"
say "─────────────────────────────────────────────────────────────────────"

while IFS=$'\t' read -r slug author ru_title en_title pg pg2 en_url en_src ru_url tier; do
  [ "$slug" = "slug" ] && continue
  # Bash counts tab as IFS *whitespace*, so runs of tabs collapse and blank
  # columns would silently shift every later field one to the left — which is
  # how a Russian URL ends up in the tier column. The manifest therefore writes
  # "-" for an empty cell, and it is turned back into "" here.
  for v in pg pg2 en_url en_src ru_url; do
    [ "${!v}" = "-" ] && printf -v "$v" '%s' ""
  done
  [ -n "$ONLY_TIER" ] && [ "$tier" != "$ONLY_TIER" ] && continue
  if [ "$RETRY" = "1" ]; then
    printf '%s\n' "$RETRY_SET" | grep -qx "$slug" || continue
  fi

  # ══ ENGLISH ════════════════════════════════════════════════════════════
  if [ "$DO_EN" = "1" ]; then
    if [ -s "$OUT/en/$slug.epub" ] || [ -s "$OUT/en/$slug.txt" ]; then
      skip=$((skip+1))
    elif [ -n "$pg" ]; then
      # One download per Gutenberg volume, however many works share it.
      if [ -n "${PG_CACHE[$pg]:-}" ] && [ -s "${PG_CACHE[$pg]}" ]; then
        cp "${PG_CACHE[$pg]}" "$OUT/en/$slug.${PG_CACHE[$pg]##*.}"
        n_en=$((n_en+1)); log en "$slug" 200 "$(wc -c < "${PG_CACHE[$pg]}")" "PG$pg (cached)"
        printf '  EN  %-42s PG %-6s from cache\n' "$slug" "$pg"
      else
        got=""
        for form in "ebooks/$pg.epub3.images" "ebooks/$pg.epub.noimages" \
                    "cache/epub/$pg/pg$pg.epub" "ebooks/$pg.txt.utf-8"; do
          ext=epub; case "$form" in *txt*) ext=txt ;; esac
          tmp="$OUT/.cache/pg$pg.$ext"
          r=$(fetch "https://www.gutenberg.org/$form" "$tmp")
          code=${r%% *}; bytes=${r##* }
          if { [ "$ext" = "epub" ] && is_zip "$tmp"; } || { [ "$ext" = "txt" ] && is_text "$tmp"; }; then
            got="$tmp"; via_pg="$form"; break
          fi
          rm -f "$tmp"; sleep "$PAUSE_PG"
        done
        if [ -n "$got" ]; then
          PG_CACHE[$pg]="$got"
          cp "$got" "$OUT/en/$slug.${got##*.}"
          n_en=$((n_en+1)); log en "$slug" "$code" "$(wc -c < "$got")" "PG$pg"
          printf '  EN  %-42s PG %-6s %8s B\n' "$slug" "$pg" "$(wc -c < "$got")"
        else
          fail_en=$((fail_en+1)); log en "$slug" "${code:-000}" 0 "PG$pg FAILED"
          manual "EN  $slug — https://www.gutenberg.org/ebooks/$pg"
        fi
        sleep "$PAUSE_PG"
      fi
    elif printf '%s' "$en_url" | grep -q 'archive.org/details/'; then
      id=$(printf '%s' "$en_url" | sed 's#.*/details/##; s#[/?].*##')
      got=""
      for cand in "${id}_djvu.txt" "${id}.epub" "${id}_text.pdf"; do
        ext=${cand##*.}
        tmp="$OUT/en/$slug.$ext"
        r=$(fetch "https://archive.org/download/$id/$cand" "$tmp")
        code=${r%% *}
        if { [ "$ext" = "epub" ] && is_zip "$tmp"; } || { [ "$ext" = "txt" ] && is_text "$tmp"; }; then
          got="$tmp"; break
        fi
        rm -f "$tmp"; sleep 1
      done
      if [ -n "$got" ]; then
        n_en=$((n_en+1)); log en "$slug" "$code" "$(wc -c < "$got")" "archive/$id"
        printf '  EN  %-42s archive.org %8s B\n' "$slug" "$(wc -c < "$got")"
      else
        fail_en=$((fail_en+1)); log en "$slug" "${code:-000}" 0 "archive FAILED"
        manual "EN  $slug — $en_url"
      fi
      sleep 1
    else
      log en "$slug" - 0 "manual (${en_src:-?})"
      manual "EN  $slug — ${en_url:-no link} (${en_src:-manual})"
      fail_en=$((fail_en+1))
    fi
  fi

  # ══ RUSSIAN ════════════════════════════════════════════════════════════
  if [ "$DO_RU" = "1" ]; then
    if [ -s "$OUT/ru/$slug.fb2" ] || [ -s "$OUT/ru/$slug.epub" ] || [ -s "$OUT/ru/$slug.txt" ]; then
      skip=$((skip+1)); continue
    fi
    got=""

    # ── 1. az.lib.ru — read the download link off the work page ──────────
    if printf '%s' "$ru_url" | grep -q 'az\.lib\.ru.*text_'; then
      page="$OUT/.cache/az.html"
      fetch "$ru_url" "$page" >/dev/null
      if [ -s "$page" ]; then
        body="$page"
        if [ "$HAVE_ICONV" = "1" ]; then
          iconv -f windows-1251 -t utf-8//TRANSLIT "$page" > "$page.u8" 2>/dev/null && body="$page.u8"
        fi
        href=$(grep -oiE 'href="[^"]*"' "$body" 2>/dev/null \
               | sed 's/^href="//I; s/"$//' \
               | grep -iE '\.(fb2|zip|txt)(\?|$)' | head -1)
        if [ -n "$href" ]; then
          case "$href" in
            http*) full="$href" ;;
            /*)    full="http://az.lib.ru$href" ;;
            *)     full="$(dirname "$ru_url")/$href" ;;
          esac
          ext=$(printf '%s' "$href" | sed 's/.*\.\([a-z0-9]*\)$/\1/I' | tr 'A-Z' 'a-z')
          case "$ext" in fb2|zip|txt) : ;; *) ext=fb2 ;; esac
          tmp="$OUT/ru/$slug.$ext"
          r=$(fetch "$full" "$tmp"); code=${r%% *}
          if [ -s "$tmp" ] && [ "$(wc -c < "$tmp")" -gt 2000 ]; then
            got="$tmp"; via_ru="az.lib.ru $href"
            n_ru=$((n_ru+1)); log ru "$slug" "$code" "$(wc -c < "$tmp")" "az.lib.ru"
            printf '  RU  %-42s az.lib.ru   %8s B\n' "$slug" "$(wc -c < "$tmp")"
          else
            rm -f "$tmp"
          fi
        fi
        # Moshkov always keeps a plain .txt beside the .shtml page
        if [ -z "$got" ]; then
          tmp="$OUT/ru/$slug.txt"
          r=$(fetch "$(printf '%s' "$ru_url" | sed 's/\.shtml$/.txt/')" "$tmp"); code=${r%% *}
          if is_text "$tmp"; then
            if [ "$HAVE_ICONV" = "1" ]; then
              iconv -f windows-1251 -t utf-8 "$tmp" > "$tmp.u8" 2>/dev/null && mv "$tmp.u8" "$tmp"
            fi
            got="$tmp"; via_ru="az.lib.ru .txt"
            n_ru=$((n_ru+1)); log ru "$slug" "$code" "$(wc -c < "$tmp")" "az.lib.ru txt"
            printf '  RU  %-42s az.lib.ru   %8s B (txt)\n' "$slug" "$(wc -c < "$tmp")"
          else
            rm -f "$tmp"
          fi
        fi
        rm -f "$page" "$page.u8"
        sleep 1
      fi
    fi

    # ── 2. ru.wikisource — find the page, then export it ─────────────────
    if [ -z "$got" ]; then
      title=$(printf '%s' "$ru_title" | sed 's/ ·.*//; s/ + .*//' | sed 's/^ *//; s/ *$//')
      q=$(urlenc "intitle:\"$title\" $author")
      api="https://ru.wikisource.org/w/api.php?action=query&list=search&format=json&srlimit=1&srnamespace=0&srsearch=$q"
      resp="$OUT/.cache/ws.json"
      fetch "$api" "$resp" >/dev/null
      wpage=""
      if [ -s "$resp" ]; then
        if [ "$HAVE_PY" = "1" ]; then
          wpage=$(python3 -c '
import json,sys
try:
    d=json.load(open(sys.argv[1],encoding="utf-8"))
    r=d.get("query",{}).get("search",[])
    print(r[0]["title"] if r else "")
except Exception: print("")' "$resp")
        else
          wpage=$(sed -n 's/.*"title":"\([^"]*\)".*/\1/p' "$resp" | head -1)
        fi
      fi
      if [ -n "$wpage" ]; then
        enc=$(urlenc "$(printf '%s' "$wpage" | sed 's/ /_/g')")
        tmp="$OUT/ru/$slug.epub"
        r=$(fetch "https://ws-export.wmcloud.org/?format=epub&lang=ru&page=$enc" "$tmp"); code=${r%% *}
        if is_zip "$tmp" && [ "$(wc -c < "$tmp")" -gt 2000 ]; then
          got="$tmp"; via_ru="ws-export"
          n_ru=$((n_ru+1)); log ru "$slug" "$code" "$(wc -c < "$tmp")" "wikisource: $wpage"
          printf '  RU  %-42s wikisource  %8s B  %s\n' "$slug" "$(wc -c < "$tmp")" "$wpage"
        else
          rm -f "$tmp"
          # ws-export challenges non-browser clients; the raw wikitext never does
          tmp="$OUT/ru/$slug.txt"
          r=$(fetch "https://ru.wikisource.org/w/index.php?action=raw&title=$enc" "$tmp"); code=${r%% *}
          if is_text "$tmp" && has_cyrillic "$tmp"; then
            got="$tmp"; via_ru="wikisource raw"
            n_ru=$((n_ru+1)); log ru "$slug" "$code" "$(wc -c < "$tmp")" "wikisource raw: $wpage"
            printf '  RU  %-42s wikitext    %8s B  %s\n' "$slug" "$(wc -c < "$tmp")" "$wpage"
          else
            rm -f "$tmp"
          fi
        fi
        sleep "$PAUSE_WS"
      fi
      rm -f "$resp"
    fi

    if [ -z "$got" ]; then
      fail_ru=$((fail_ru+1)); log ru "$slug" - 0 "manual"
      manual "RU  $slug ($ru_title) — ${ru_url:-no link}"
    fi
  fi
done < "$MANIFEST"

rm -rf "$OUT/.cache"

# ══ report ═══════════════════════════════════════════════════════════════
say "─────────────────────────────────────────────────────────────────────"
say "  English  $n_en downloaded, $fail_en to collect by hand"
say "  Russian  $n_ru downloaded, $fail_ru to collect by hand"
say "  Skipped  $skip already on disk"
say ""
[ -n "$via_pg" ] && say "  Gutenberg URL form that worked:  $via_pg"
[ -n "$via_ru" ] && say "  Last Russian source that worked: $via_ru"
say ""
say "  Files      $(cd "$OUT" && pwd)"
say "  Log        $LOG"
if [ -s "$MAN" ]; then
  say "  Manual     $MAN  ($(wc -l < "$MAN") entries)"
  say ""
  say "  First few to collect by hand:"
  head -12 "$MAN" | sed 's/^/    /'
fi
say "─────────────────────────────────────────────────────────────────────"
