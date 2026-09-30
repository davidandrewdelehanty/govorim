import sys
p=sys.argv[1]; s=open(p,encoding="utf-8").read()
def rep(old,new,count=1):
    global s
    n=s.count(old); assert n==count,(n,old[:70]); s=s.replace(old,new)
rep('''function sectionLabel(heading) {''','''// The number shown beside a chapter in the contents. The author's own number
// when the heading carries one, so an epigraph or a preface standing before
// chapter I does not push "I" to 2; nothing at all for an unnumbered section
// of a numbered book (an epigraph, ВАРИАНТЫ, an epilogue — their headings
// speak for themselves); and the plain position, as before, in a book whose
// sections are not numbered at all.
function chapterOrdinal(chs, i) {
  var n = authorChapterNo(chs[i] && chs[i].heading);
  if (n) return String(n);
  for (var j = 0; j < chs.length; j++) if (authorChapterNo(chs[j] && chs[j].heading)) return "";
  return String(i + 1);
}

function sectionLabel(heading) {''')
rep('''<div className="lcn">{i+1}{i===cbm?" · bookmarked":""}{i===cidx?" · here":""}</div>''',
    '''<div className="lcn">{[chapterOrdinal(chapters, i), i===cbm?"bookmarked":"", i===cidx?"here":""].filter(Boolean).join(" · ")}</div>''',2)
rep('''<div className="lcn">{i+1}{i===cbm?" · bookmarked":""}</div>''',
    '''<div className="lcn">{[chapterOrdinal(chapters, i), i===cbm?"bookmarked":""].filter(Boolean).join(" · ")}</div>''')
rep('''        .lit-left.has-vid .chvid-scrub{margin:-26px -32px 22px;padding:8px 32px;border-top:0;border-bottom:1px solid var(--rule-soft)}''',
    '''        /* Only where the video sits in its own rail (see the 1250px rule
           above): applied at every width, the negative margins pulled the
           transport up underneath the docked video on a phone or a narrow
           window, and the player looked as if it had no controls at all. */
        @media (min-width:1250px){
          .lit-left.has-vid .chvid-scrub{margin:-26px -32px 22px;padding:8px 32px;border-top:0;border-bottom:1px solid var(--rule-soft)}
        }''')
# Cyrillic look-alike numerals after «Глава» too («Глава Х» in Дядюшкин сон)
rep('''    if (ROMANISH.test(h)) {
      h = h.replace(/\\.$/, "").replace(/[ХІѴСМД]/g, function (ch) { return FB2_ROMAN_HOMOGLYPHS[ch]; });
      c.heading = h; last = h; run = 1;
      continue;
    }''','''    if (ROMANISH.test(h)) {
      h = h.replace(/\\.$/, "").replace(/[ХІѴСМД]/g, function (ch) { return FB2_ROMAN_HOMOGLYPHS[ch]; });
      c.heading = h; last = h; run = 1;
      continue;
    }
    var gl = h.match(/^(глава\\s+)([IVXLCDMХІѴСМД]{1,8})(\\.?)$/i);
    if (gl) {
      h = gl[1] + gl[2].replace(/[ХІѴСМД]/g, function (ch) { return FB2_ROMAN_HOMOGLYPHS[ch]; }) + gl[3];
      c.heading = h; last = h; run = 1;
      continue;
    }''')
open(p,"w",encoding="utf-8",newline="\n").write(s); print("ok")
