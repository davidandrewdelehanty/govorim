// Courses: progress through the lessons of the Courses tab, shared by the app
// and the server so both read it the same way.
//
// A reader's progress is one object, keyed "<course>/<section>":
//   { right: { [exerciseId]: firstRightAt },   exercises answered correctly
//     first: { [exerciseId]: 1 | 0 },          right at the first try, or not
//     read: at,                                 the lesson opened and read
//     done: at }                                every exercise answered (or,
//                                               for a lesson without any, read)
// Nothing is ever taken back: merging two devices' records keeps every right
// answer and the earliest time for each.

export function mergeCourseProg(a, b) {
  var out = Object.assign({}, a || {});
  var inc = b || {};
  Object.keys(inc).slice(0, 2000).forEach(function (k) {
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

// How far along a course is: { done, of, at } — `at` when the last section was finished.
export function courseState(course, prog) {
  var done = 0, at = 0;
  (course.sections || []).forEach(function (s) {
    var rec = (prog || {})[course.id + "/" + s.id];
    if (rec && rec.done) { done++; at = Math.max(at, rec.done); }
  });
  return { done: done, of: (course.sections || []).length, at: done === (course.sections || []).length ? at : 0 };
}

// Badges: one for every section finished, one for every course finished.
export function courseBadges(outline, prog) {
  var out = [];
  (outline || []).forEach(function (c) {
    (c.sections || []).forEach(function (s, i) {
      var rec = (prog || {})[c.id + "/" + s.id];
      out.push({
        id: "course:" + c.id + ":" + s.id, group: "course", tier: 1, mark: String(i + 1),
        title: c.short + " · " + s.title, desc: "Finish “" + s.title + "” in " + c.title,
        earned: !!(rec && rec.done), n: rec && rec.done ? 1 : 0, of: 1, at: (rec && rec.done) || 0,
        course: c.id, section: s.id,
      });
    });
    var st = courseState(c, prog);
    out.push({
      id: "course:" + c.id, group: "course", tier: 4, mark: c.mark || "★",
      title: c.title, desc: "Finish every section of " + c.title,
      earned: st.of > 0 && st.done === st.of, n: st.done, of: st.of, at: st.at, course: c.id,
    });
  });
  return out;
}
