// Courses: progress through the lessons of the Courses tab, shared by the app
// and the server so both read it the same way.
//
// A reader's progress is one object, keyed "<course>/<section>":
//   { right: { [exerciseId]: firstRightAt },   exercises answered correctly
//     first: { [exerciseId]: 1 | 0 },          right at the first try, or not
//     read: at,                                 the lesson opened and read
//     done: at,                                 every exercise answered (or,
//                                               for a lesson without any, read)
//     perfect: at,                              every exercise right with no
//                                               wrong answer, in one go
//     grade: 92 }                               the exam: the best mark so far,
//                                               per cent (done = passed)
// Nothing is ever taken back: merging two devices' records keeps every right
// answer and the earliest time for each.

export function mergeCourseProg(a, b) {
  var out = Object.assign({}, a || {});
  var inc = b || {};
  Object.keys(inc).slice(0, 8000).forEach(function (k) {
    if (!/^[a-z0-9-]{1,40}\/[a-z0-9-]{1,60}$/.test(k)) return;
    var x = out[k] || {}, y = inc[k] || {};
    var right = Object.assign({}, x.right || {});
    Object.keys(y.right || {}).forEach(function (e) {
      var t = Number(y.right[e]) || 0;
      if (!t) return;
      right[e] = right[e] ? Math.min(right[e], t) : t;
    });
    var first = Object.assign({}, y.first || {}, x.first || {});     // the earlier record wins
    var early = function (p, q) { p = Number(p) || 0; q = Number(q) || 0; return p && q ? Math.min(p, q) : (p || q); };
    out[k] = { right: right, first: first, read: early(x.read, y.read), done: early(x.done, y.done) };
    var pf = early(x.perfect, y.perfect);
    if (pf) out[k].perfect = pf;
    var g = Math.max(Number(x.grade) || 0, Number(y.grade) || 0);
    if (g) out[k].grade = g;
    // The best score in the section's own review drill (the grammar terms):
    // 90 or more opens the next section.
    var d = Math.max(Number(x.drill) || 0, Number(y.drill) || 0);
    if (d) out[k].drill = d;
    // The best score on the section's exercises, right at the first try;
    // 90 or more opens the next section.
    var sc = Math.max(Number(x.score) || 0, Number(y.score) || 0);
    if (sc) out[k].score = sc;
  });
  return out;
}

// Is this section finished, given its exercise ids?
export function sectionDone(rec, exerciseIds) {
  if (!rec) return false;
  if (rec.done) return true;
  if (!exerciseIds || !exerciseIds.length) return !!rec.read;
  return exerciseIds.every(function (id) { return rec.right && rec.right[id]; });
}

// Was every exercise of this section answered right with no mistakes — in a
// clean run (rec.perfect), or all right at the very first try?
export function sectionPerfect(rec, n) {
  if (!rec || !n) return false;
  if (rec.perfect) return true;
  for (var i = 1; i <= n; i++) if (!rec.first || rec.first["q" + i] !== 1) return false;
  return true;
}
function perfectAt(rec, n) {
  if (!sectionPerfect(rec, n)) return 0;
  if (rec.perfect) return rec.perfect;
  var at = 0;
  for (var i = 1; i <= n; i++) at = Math.max(at, Number(rec.right && rec.right["q" + i]) || 0);
  return at || rec.done || 1;
}

// How far along a course is: { done, of, at } — `at` when the last section was finished.
export function courseState(course, prog) {
  // A course to repeat as often as you like (the clock) is never finished.
  if (course.repeat) return { done: 0, of: 0, at: 0 };
  var done = 0, at = 0;
  // An endless practice stream (one drill after another, as many as you like) is never finished and is not counted.
  var secs = (course.sections || []).filter(function (s) { return !(s.stream && !s.n); });
  secs.forEach(function (s) {
    var rec = (prog || {})[course.id + "/" + s.id];
    if (rec && rec.done) { done++; at = Math.max(at, rec.done); }
  });
  return { done: done, of: secs.length, at: done === secs.length ? at : 0 };
}

// A practice set that follows a lesson ("<lesson>-practice", "-practice-2" …).
export function isPractice(id) { return /-practice(-\d+)?$/.test(String(id || "")); }

// Badges: one for every lesson finished, one for every course — earned by
// passing its exam (85% or better) where it has one, by finishing every
// section where it has not — and a ★ for a lesson, or a whole course's
// lessons, answered without a mistake. Practice sets count toward finishing a
// course but carry no badge of their own.
export function courseBadges(outline, prog) {
  var out = [];
  (outline || []).forEach(function (c) {
    if (c.repeat) return;
    var lessonNo = 0;
    (c.sections || []).forEach(function (s) {
      if (isPractice(s.id) || (s.stream && !s.n)) return;
      var i = lessonNo++;
      var rec = (prog || {})[c.id + "/" + s.id];
      out.push({
        id: "course:" + c.id + ":" + s.id, group: "course", tier: 1, mark: String(i + 1),
        title: c.short + " · " + s.title, desc: "Finish “" + s.title + "” in " + c.title,
        earned: !!(rec && rec.done), n: rec && rec.done ? 1 : 0, of: 1, at: (rec && rec.done) || 0,
        course: c.id, section: s.id,
      });
    });
    var withEx = (c.sections || []).filter(function (s) { return s.n > 0 && !isPractice(s.id); });
    var pDone = 0, pAt = 0;
    withEx.forEach(function (s, i) {
      var rec = (prog || {})[c.id + "/" + s.id];
      var at = perfectAt(rec, s.n);
      if (at) { pDone++; pAt = Math.max(pAt, at); }
      out.push({
        id: "course:" + c.id + ":" + s.id + ":perfect", group: "course", tier: 2, mark: "★",
        title: c.short + " · " + s.title + " · perfect", desc: "Answer every exercise in “" + s.title + "” right, without a single mistake",
        earned: !!at, n: at ? 1 : 0, of: 1, at: at, course: c.id, section: s.id, perfect: true,
      });
    });
    if (withEx.length) out.push({
      id: "course:" + c.id + ":perfect", group: "course", tier: 5, mark: "★",
      title: c.title + " · perfect", desc: "Answer every exercise in every lesson of " + c.title + " without a mistake",
      earned: pDone === withEx.length, n: pDone, of: withEx.length, at: pDone === withEx.length ? pAt : 0, course: c.id, perfect: true,
    });
    var st = courseState(c, prog);
    var exam = (c.sections || []).filter(function (s) { return s.exam; })[0];
    var xr = exam ? (prog || {})[c.id + "/" + exam.id] : null;
    out.push(exam ? {
      id: "course:" + c.id, group: "course", tier: 4, mark: c.mark || "★",
      title: c.title, desc: "Pass the exam of " + c.title + " — 85% or better",
      earned: !!(xr && xr.done), n: xr && xr.done ? 1 : 0, of: 1, at: (xr && xr.done) || 0, course: c.id,
      grade: (xr && xr.grade) || 0,
    } : {
      id: "course:" + c.id, group: "course", tier: 4, mark: c.mark || "★",
      title: c.title, desc: "Finish every section of " + c.title,
      earned: st.of > 0 && st.done === st.of, n: st.done, of: st.of, at: st.at, course: c.id,
    });
  });
  return out;
}
