#!/usr/bin/env bash
# The public-domain US government Russian courses, fetched for the course
# builder: the DLI Russian Basic Course (text and tapes), the FSI Russian FAST
# course (text and tapes), the FSI Active Introduction, the Peace Corps manuals,
# and the DLI intermediate–advanced volumes. All are works of the US
# government, in the public domain.
#
# Run in WSL (the Cowork sandbox cannot reach the file host):
#     bash tools/pd_courses/fetch.sh            # → _to_delete/pd/ (ignored by git; Cowork can read it there)
#
# Re-running skips files already fetched at full size. The PDFs are scanned
# images with no text layer; tools/pd_courses/ocr.py reads them.
set -u
OUT="${PD_OUT:-$(cd "$(dirname "$0")/../.." && pwd)/_to_delete/pd}"
B1="https://fsi-language-courses-media.nyc3.cdn.digitaloceanspaces.com/languages-dli/Russian/Russian-Basic"
A1="https://fsi-language-courses-media.nyc3.digitaloceanspaces.com/languages-dli/Russian/Russian-Basic"
B2="https://fsi-language-courses-media.nyc3.cdn.digitaloceanspaces.com/languages/Russian"
B3="https://fsi-language-courses-media.nyc3.cdn.digitaloceanspaces.com/languages-peacecorps/Russian-General"
B4="https://fsi-language-courses-media.nyc3.cdn.digitaloceanspaces.com/languages-dli/Russian/Russian-Intermediate-Advanced-Course"
get() {  # get <subdir> <url>
  local d="$OUT/$1" u="$2" f
  f="$(printf '%s' "${u##*/}" | sed 's/%20/ /g; s/%2C/,/g; s/%2520/ /g')"
  mkdir -p "$d"
  if [ -s "$d/$f" ]; then echo "   have  $1/$f"; return; fi
  echo "   fetch $1/$f"
  curl -sS -L --retry 4 --retry-delay 5 -o "$d/$f.part" "$u" && mv "$d/$f.part" "$d/$f" || { echo "   ! failed: $u"; rm -f "$d/$f.part"; }
}

echo "== DLI Russian Basic Course: text"
for p in 01; do get dli-basic/phase1 "$B1/Courses/Phase%201/Mod%20$p.pdf"; done
for p in 02 03 04 05 06 07 08 09 10 11 12 13 14; do get dli-basic/phase2 "$B1/Courses/Phase%202/Mod%20$p.pdf"; done
get dli-basic/phase2 "$B1/Courses/Phase%202/Student%20Workbook%20Mods%2008-14.pdf"
for p in 01 02 03 04; do get dli-basic/phase3 "$B1/Courses/Phase%203/Mod%20$p.pdf"; done
get dli-basic/grammar "$B1/Grammar/Grammar%20Refrence%20Book%20Vol%2001.pdf"
get dli-basic/grammar "$B1/Grammar/Grammar%20Refrence%20Book%20Vol%2002.pdf"
for v in "01%20Units%2001-04" "02%20Units%2005-08" "03%20Units%2009-12" "04%20Units%2013-16" "05%20Units%2017-20" "06%20Units%2021-25"; do
  get dli-basic/taped "$B1/Exercises/Taped%20Exercises%20Vol%20$v.pdf"
done
get dli-basic/reader "$B1/Reader/Reader%20%20Two%20Captains.pdf"
get dli-basic/reader "$B1/Reader/Reader%20Vol%2002.pdf"

echo "== DLI Russian Basic Course: tapes"
get dli-basic/audio "$A1/Courses/Phase%201/Audio/Mod%2001%20Tape%2002%20Less%2003-04.mp3"
get dli-basic/audio "$A1/Courses/Phase%201/Audio/Mod%2001%20Tape%2003%20Less%2005-06.mp3"
get dli-basic/audio "$A1/Courses/Phase%201/Audio/Mod%2001%20Tape%2004%20Less%2007-08.mp3"
get dli-basic/audio "$A1/Courses/Phase%201/Audio/Mod%2001%20Tape%2005%20Less%2009-10.mp3"
for t in "02%20Tape%2006%20Less%2011-12" "02%20Tape%2008%20Less%2015-16" "03%20Tape%2009%20Less%2017-18" "03%20Tape%2010%20Less%2019-20" \
         "03%20Tape%2011%20Less%2021-22" "04%20Tape%2012%20Less%2023-24" "04%20Tape%2013%20Less%2025-26" "05%20Tape%2014%20Less%2027-28" \
         "05%20Tape%2015%20Less%2029-30" "05%20Tape%2016%20Less%2031-32" "06%20Tape%2017%20Less%2033-34" "06%20Tape%2018%20Less%2035-36" \
         "06%20Tape%2019%20Less%2037-38" "07%20Tape%2020%20Less%2039-40" "07%20Tape%2021%20Less%2041-42" "07%20Tape%2022%20Less%2043-44" \
         "08%20Tape%2023%20Less%2045-46"; do
  get dli-basic/audio "$A1/Courses/Phase%202/Audio/Mod%20$t.mp3"
done
for t in "HW%2001%20Mod%2001%20L001" "HW%2001%20Mod%2001%20Less" "HW%2001%20Mod%2002%20L001" "HW%2001%20Mod%2002%20Less" "HW%2001%20Mod%2002%2C0001" \
         "HW%2001%20Mod%2002%2C03%20L" "HW%2001%20Mod%2004%20Less" "HW%2002%20Mod%2001%20L001" "HW%2002%20Mod%2001%20Less" "HW%2003%20Mod%2004%20Less" \
         "Prac%20Dict%20Less%2001" "Prac%20Dict%20Less%2005" "Prac%20Dict%20Less%2009" "Prac%20Dict%20Less%2013" "Prac%20Dict%20Less%2017" \
         "Prac%20Dict%20Less001" "Prac%20Dict%20Less002" "Prac%20Dict%20Less003" "Prac%20Dict%20Less004"; do
  get dli-basic/audio-phase3 "$A1/Courses/Phase%203/Audio/Phase%20III%20$t.mp3"
done

echo "== FSI Russian FAST: text and tapes"
get fsi-fast "$B2/FAST/FsiRussianFast-Lessons1-5.pdf"
get fsi-fast "$B2/FAST/FsiRussianFast-Lessons6-8.pdf"
get fsi-fast "$B2/FAST/FsiRussianFast-Lessons9-11.pdf"
for t in 1 2 3 4 5 6 7 8; do get fsi-fast/audio "$B2/FAST/FSI%20Russian%20FAST%20-%20Tape%20$t.mp3"; done
get fsi-fast/audio "$B2/FAST/FSI%20Russian%20FAST%20-%20Supplement.mp3"

echo "== FSI Russian: an Active Introduction"
get fsi-active "$B2/Active%20Introduction/FSI%20-%20Russian%20Active%20Introduction%20-%20Student%20Text.pdf"

echo "== Peace Corps Russian"
get peace-corps "$B3/ED402767.pdf"
get peace-corps "$B3/Peace%2520Corps%2520Russian%2520Language%2520Competencies%2520Workbook.pdf"

echo "== DLI Russian intermediate–advanced"
get dli-adv "$B4/Vol%2001%20Less%2001-20.pdf"
get dli-adv "$B4/Vol%2002%20Less%2021-35.pdf"
get dli-adv "$B4/Government%20Structure.pdf"
get dli-adv "$B4/Through%20the%20eyes%20of%20a%20Soviet%20Citizen.pdf"

echo
echo "Done → $OUT"
du -sh "$OUT"/* 2>/dev/null
