import sys
p=sys.argv[1]; s=open(p,encoding="utf-8").read()
old="function sectionLabel(heading) {"
new='''// Uniform headings. Some FB2s cut a chapter into scenes with a "* * *"
// section of its own, and some open with an untitled stretch of text before
// their first numeral. In the contents and at the head of the page those
// read as a run of asterisks and a blank. Here a scene keeps its chapter's
// numeral with a count ("XII · 2", "XII · 3"), a Cyrillic look-alike numeral
// («Х» for X) becomes the Latin one so it is recognised as a number, and an
// untitled opening is named for what it is. Runs after the videos are
// attached, so the heading match there sees the file's own titles.
function uniformHeadings(chs, opts) {
  if (!chs || chs.length < 2) return chs;
  var STAR = /^[\\s\\*·•⁂—–\\-_.]+$/;
  var ROMANISH = /^[IVXLCDMХІѴСМД]{1,8}\\.?$/;
  var last = null, run = 1;
  for (var i = 0; i < chs.length; i++) {
    var c = chs[i];
    var h = String(c.heading || "").trim();
    if (ROMANISH.test(h)) {
      h = h.replace(/\\.$/, "").replace(/[ХІѴСМД]/g, function (ch) { return FB2_ROMAN_HOMOGLYPHS[ch]; });
      c.heading = h; last = h; run = 1;
      continue;
    }
    if (h && STAR.test(h)) {
      if (last) { run++; c.heading = last + " · " + run; }
      else { c.heading = "· " + (i + 1); }
      continue;
    }
    if (!h) {
      if (i === 0) {
        var nextNo = authorChapterNo(chs[1] && chs[1].heading);
        c.heading = nextNo === 2 ? "I"
                  : (opts && opts.play) ? "Действующие лица"
                  : "Вступление";
        last = c.heading; run = 1;
      }
      continue;
    }
    last = h; run = 1;
  }
  return chs;
}

function sectionLabel(heading) {'''
assert s.count(old)==1; s=s.replace(old,new)
old2='''      if (opts.play && !opts.videos && !opts.songs && !opts.audiobook) {
        chs = mergePlayActs(chs);
      }'''
new2='''      if (opts.play && !opts.videos && !opts.songs && !opts.audiobook) {
        chs = mergePlayActs(chs);
      }
      chs = uniformHeadings(chs, opts);'''
assert s.count(old2)==1; s=s.replace(old2,new2)
open(p,"w",encoding="utf-8",newline="\n").write(s); print("ok")
