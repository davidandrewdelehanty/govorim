// Reading and practice statistics: one record per local calendar day.
//
//   stats = { "2026-09-01": { read: 1840, practiced: 12 }, ... }
//
// `read` is Russian words the reader scrolled through in the reader,
// `practiced` is vocabulary-quiz answers. A day counts toward the streak when
// either reaches its goal — the same rule Readlang uses, and for the same
// reason: a day with ten flashcards on the train is still a day of Russian.

export var GOAL_WORDS = 500;
export var GOAL_CARDS = 10;

var DAY = 86400000;

// "2026-09-01" in the reader's own timezone — a day ends at their midnight,
// not UTC's, or an evening session in Chicago would land on tomorrow.
export function dayKey(ts) {
  var d = new Date(ts == null ? Date.now() : ts);
  var m = d.getMonth() + 1, day = d.getDate();
  return d.getFullYear() + "-" + (m < 10 ? "0" : "") + m + "-" + (day < 10 ? "0" : "") + day;
}

export function keyToDate(key) {
  var p = String(key).split("-");
  return new Date(+p[0], +p[1] - 1, +p[2]);
}

function shiftKey(key, days) {
  var d = keyToDate(key);
  d.setDate(d.getDate() + days);
  return dayKey(d.getTime());
}

export function dayMet(rec, goals) {
  var g = goals || {};
  var words = (g.words != null ? g.words : GOAL_WORDS);
  var cards = (g.cards != null ? g.cards : GOAL_CARDS);
  return !!rec && (((rec.read || 0) >= words) || ((rec.practiced || 0) >= cards));
}

// Add to today's record. Returns a new stats object.
export function bump(stats, field, n, ts) {
  var key = dayKey(ts);
  var next = Object.assign({}, stats || {});
  var rec = Object.assign({}, next[key] || {});
  rec[field] = (rec[field] || 0) + n;
  next[key] = rec;
  return next;
}

// Two copies of the same log, from two devices: per day, take the larger
// figure. Neither device saw the other's session, so the larger of the two is
// the closest thing to the truth that can be recovered.
export function mergeStats(a, b) {
  var out = {};
  [a, b].forEach(function (src) {
    Object.keys(src || {}).forEach(function (k) {
      var rec = src[k] || {};
      var cur = out[k] || {};
      out[k] = {
        read: Math.max(cur.read || 0, rec.read || 0),
        practiced: Math.max(cur.practiced || 0, rec.practiced || 0),
      };
    });
  });
  return out;
}

// Current streak: consecutive days ending today (or yesterday — today isn't
// lost until midnight) on which the goal was met. Longest: over all history.
export function streaks(stats, goals, ts) {
  var today = dayKey(ts);
  var current = 0;
  var cursor = today;
  if (!dayMet(stats && stats[cursor], goals)) cursor = shiftKey(cursor, -1);   // today still open
  while (dayMet(stats && stats[cursor], goals)) { current++; cursor = shiftKey(cursor, -1); }

  var keys = Object.keys(stats || {}).filter(function (k) { return dayMet(stats[k], goals); }).sort();
  var longest = 0, run = 0, prev = null;
  keys.forEach(function (k) {
    run = (prev && shiftKey(prev, 1) === k) ? run + 1 : 1;
    if (run > longest) longest = run;
    prev = k;
  });
  return { current: current, longest: Math.max(longest, current), todayMet: dayMet(stats && stats[today], goals) };
}

// The last seven days, oldest first, for the weekly chart.
export function lastWeek(stats, goals, ts) {
  var out = [];
  var today = dayKey(ts);
  for (var i = 6; i >= 0; i--) {
    var k = shiftKey(today, -i);
    var rec = (stats && stats[k]) || {};
    out.push({ key: k, date: keyToDate(k), read: rec.read || 0, practiced: rec.practiced || 0,
               met: dayMet(rec, goals), isToday: i === 0 });
  }
  return out;
}

// Every day of a year, for the dot grid: [{key, read, practiced, level}] where
// level is 0–4 by words read (or practiced), relative to a fixed scale rather
// than the reader's own maximum, so a good day looks the same in a slow month.
export function yearGrid(stats, year, ts) {
  var out = [];
  var start = new Date(year, 0, 1);
  var today = dayKey(ts);
  for (var d = new Date(start); d.getFullYear() === year; d.setDate(d.getDate() + 1)) {
    var k = dayKey(d.getTime());
    if (k > today) break;
    var rec = (stats && stats[k]) || {};
    var v = (rec.read || 0) + (rec.practiced || 0) * 25;   // a card ≈ 25 words of reading
    var level = v <= 0 ? 0 : v < 250 ? 1 : v < 750 ? 2 : v < 2000 ? 3 : 4;
    out.push({ key: k, date: new Date(d), read: rec.read || 0, practiced: rec.practiced || 0, level: level });
  }
  return out;
}

export function totals(stats) {
  var read = 0, practiced = 0, days = 0;
  Object.keys(stats || {}).forEach(function (k) {
    var r = stats[k] || {};
    read += r.read || 0; practiced += r.practiced || 0;
    if ((r.read || 0) > 0 || (r.practiced || 0) > 0) days++;
  });
  return { read: read, practiced: practiced, days: days };
}
