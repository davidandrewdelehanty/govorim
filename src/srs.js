// Spaced repetition for the vocabulary list.
//
// The scheduler is FSRS-6 (Free Spaced Repetition Scheduler), the model Anki
// adopted in 2023 in place of SM-2. It keeps three numbers per word:
//
//   D  difficulty      1–10, how hard this word is for this reader
//   S  stability       days until the chance of recalling the word falls to 90%
//   R  retrievability  the chance of recalling it right now, from S and the
//                      time since the last review — this is what "due" means
//
// A right answer grows S (by more the longer you waited and the closer you
// were to forgetting); a wrong one shrinks it. A word is reviewed again when R
// drops below the target retention, and it is retired from the active list
// once S is long enough that the word is, for practical purposes, known.
//
// The quiz is multiple choice, so every answer is either Again (1) or Good (3)
// — FSRS's Hard and Easy grades are not used. Default weights are FSRS-6's
// published ones; the reader's own history is not used to refit them, which
// the reference implementations do with thousands of reviews and this app
// never has.
//
// Reference: https://github.com/open-spaced-repetition/awesome-fsrs/wiki/The-Algorithm

export var FSRS_W = [0.212, 1.2931, 2.3065, 8.2956, 6.4133, 0.8334, 3.0194, 0.001,
  1.8722, 0.1666, 0.796, 1.4835, 0.0614, 0.2629, 1.6483, 0.6014, 1.8729, 0.5425,
  0.0912, 0.0658, 0.1542];

export var TARGET_RETENTION = 0.9;   // review when the chance of recall drops below this
var DAY = 86400000;
var AGAIN = 1, GOOD = 3;

var DECAY = -FSRS_W[20];
var FACTOR = Math.pow(0.9, 1 / DECAY) - 1;   // makes R(S, S) come out at exactly 0.9

// Chance of recalling a word `days` after its last review, given stability S.
export function retrievability(S, days) {
  if (!S || S <= 0) return 0;
  return Math.pow(1 + FACTOR * Math.max(0, days) / S, DECAY);
}

// Days after a review at which R falls to the target: the next due date.
export function intervalFor(S, retention) {
  var r = retention || TARGET_RETENTION;
  var t = S / FACTOR * (Math.pow(r, 1 / DECAY) - 1);
  return Math.max(1, Math.round(t));
}

function clampD(d) { return Math.min(10, Math.max(1, d)); }
function initialDifficulty(grade) {
  return clampD(FSRS_W[4] - Math.exp(FSRS_W[5] * (grade - 1)) + 1);
}
function nextDifficulty(D, grade) {
  var delta = -FSRS_W[6] * (grade - 3);
  var linear = D + delta * (10 - D) / 9;
  // Mean reversion toward the difficulty of a word first rated Good, so a run
  // of bad days does not pin a word at 10 forever.
  return clampD(FSRS_W[7] * initialDifficulty(4) + (1 - FSRS_W[7]) * linear);
}
function stabilityAfterRecall(D, S, R, grade) {
  var hard = grade === 2 ? FSRS_W[15] : 1;
  var easy = grade === 4 ? FSRS_W[16] : 1;
  return S * (Math.exp(FSRS_W[8]) * (11 - D) * Math.pow(S, -FSRS_W[9]) *
              (Math.exp(FSRS_W[10] * (1 - R)) - 1) * hard * easy + 1);
}
function stabilityAfterForgetting(D, S, R) {
  var s = FSRS_W[11] * Math.pow(D, -FSRS_W[12]) *
          (Math.pow(S + 1, FSRS_W[13]) - 1) * Math.exp(FSRS_W[14] * (1 - R));
  // A lapse never leaves the word MORE stable than it was.
  return Math.min(s, S);
}

// The schedule after one answer. `srs` is the word's current state (or
// undefined for a first review); returns the new state. `now` is a timestamp.
export function review(srs, correct, now) {
  now = now || Date.now();
  var grade = correct ? GOOD : AGAIN;
  var prev = srs && srs.S > 0 ? srs : null;
  var D, S, R;
  if (!prev) {
    S = FSRS_W[grade - 1];
    D = initialDifficulty(grade);
    R = 0;
  } else {
    var days = (now - (prev.last || now)) / DAY;
    R = retrievability(prev.S, days);
    D = nextDifficulty(prev.D, grade);
    S = correct ? stabilityAfterRecall(prev.D, prev.S, R, grade)
                : stabilityAfterForgetting(prev.D, prev.S, R);
  }
  S = Math.max(0.1, S);
  var interval = intervalFor(S);
  return {
    D: Math.round(D * 100) / 100,
    S: Math.round(S * 100) / 100,
    reps: ((prev && prev.reps) || 0) + 1,
    lapses: ((prev && prev.lapses) || 0) + (correct ? 0 : 1),
    run: correct ? (((prev && prev.run) || 0) + 1) : 0,   // consecutive correct answers
    last: now,
    due: now + interval * DAY,
    interval: interval,
  };
}

// The chance the reader still knows the word right now.
export function recallNow(srs, now) {
  if (!srs || !srs.S) return 0;
  return retrievability(srs.S, ((now || Date.now()) - (srs.last || 0)) / DAY);
}

// A word is retired from the active list when it has been recalled across a
// spread of intervals and would now be trusted for three months without a
// review: stability of at least 90 days, four or more reviews, and no lapse in
// the last three answers. That is the point at which asking again spends the
// reader's time without telling either of you anything new.
export var LEARNED_STABILITY_DAYS = 90;
export function isLearned(srs) {
  return !!(srs && srs.S >= LEARNED_STABILITY_DAYS && srs.reps >= 4 && srs.run >= 3);
}

// Words to put in front of the reader now, most urgent first: never-reviewed
// words, then those whose recall has slipped furthest below the target. Words
// comfortably above the target are left alone — reviewing them early is what
// spaced repetition exists to avoid. `limit` caps the session.
export function dueWords(entries, now, limit) {
  now = now || Date.now();
  var scored = [];
  for (var i = 0; i < entries.length; i++) {
    var v = entries[i];
    if (!v || isLearned(v.srs)) continue;
    var r = recallNow(v.srs, now);
    var isNew = !(v.srs && v.srs.S);
    var overdue = v.srs && v.srs.due ? (now - v.srs.due) / DAY : 0;
    if (!isNew && r >= TARGET_RETENTION && overdue < 0) continue;
    // New words first (they have never been tested), then by how far recall
    // has fallen; ties broken by how long overdue.
    scored.push({ v: v, key: isNew ? -1 : r, overdue: overdue });
  }
  scored.sort(function (a, b) { return a.key - b.key || b.overdue - a.overdue; });
  var out = scored.map(function (x) { return x.v; });
  return limit ? out.slice(0, limit) : out;
}

// When nothing is due, the least-secure words are still the best use of a
// session someone wants to have anyway.
export function weakestWords(entries, now, limit) {
  now = now || Date.now();
  var pool = entries.filter(function (v) { return v && !isLearned(v.srs); });
  pool.sort(function (a, b) { return recallNow(a.srs, now) - recallNow(b.srs, now); });
  return limit ? pool.slice(0, limit) : pool;
}
