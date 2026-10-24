// Lists the site's accounts and approves or revokes them. Admin only.
//
// Accounts live in R2 (see lib/auth.js) rather than in a third-party user
// directory, so this reads the account index and returns one row each.
// New accounts start unapproved and cannot sign in until approved here;
// accounts that predate the approval flow have no `approved` field and are
// treated as approved, so existing readers keep working untouched.
import fs from "node:fs";
import path from "node:path";
import { requireAdmin } from "./helpers.js";
import COURSE_OUTLINE from "../../src/courses-outline.js";
import { courseState } from "../../src/courses.js";
import { listAccounts, readBoardRows, setApproval, isAdminEmail, findAccount, userIdFor, r2GetJson,
         r2PutJson, userDataKey, readDaily, todayKey } from "../auth.js";

// The daily reading log, summed. Deliberately a copy of what src/stats.js
// does on the client rather than an import of it: that module is bundled for
// the browser and this runs in a serverless function, and the arithmetic is
// six lines. A day counts as active when anything at all was recorded on it —
// a lower bar than the streak's, because the question here is "were they here"
// rather than "did they hit the goal".
//
// The streak uses the app's own default goals (500 words or 10 cards). A
// reader who has set their own goals will see a streak here computed against
// the defaults; the panel says which, rather than quietly showing a figure
// that does not match the one on their own page.
function logTotals(stats) {
  const s = (stats && typeof stats === "object" && !Array.isArray(stats)) ? stats : {};
  const keys = Object.keys(s).filter(function (k) { return /^\d{4}-\d{2}-\d{2}$/.test(k); }).sort();
  let read = 0, practiced = 0, days = 0, last = null;
  for (const k of keys) {
    const r = s[k] || {};
    read += Number(r.read) || 0;
    practiced += Number(r.practiced) || 0;
    if ((Number(r.read) || 0) > 0 || (Number(r.practiced) || 0) > 0) { days++; last = k; }
  }
  // Consecutive met days ending today or yesterday — today is not lost until
  // midnight, so an unfinished today does not break the run.
  const met = {};
  for (const k of keys) met[k] = ((Number((s[k] || {}).read) || 0) >= 500) ||
                                 ((Number((s[k] || {}).practiced) || 0) >= 10);
  const shift = function (key, n) {
    const d = new Date(key + "T12:00:00Z");
    d.setUTCDate(d.getUTCDate() + n);
    return d.toISOString().slice(0, 10);
  };
  let cursor = new Date().toISOString().slice(0, 10);
  if (!met[cursor]) cursor = shift(cursor, -1);
  let streak = 0;
  while (met[cursor]) { streak++; cursor = shift(cursor, -1); }
  const recent = keys.slice(-56).map(function (k) {
    const r = s[k] || {};
    return { date: k, read: Number(r.read) || 0, practiced: Number(r.practiced) || 0 };
  });
  return { read, practiced, days, last, streak, recent };
}

// One reader's progress through the Courses tab, a row per course: how many of
// its sections they have opened and finished, how many exercises they have
// answered right (and how many of those at the first try), the sections
// finished without a mistake, and when they last did anything in it. `prog` is
// their "courses" file (see src/courses.js for its shape). Every course in the
// outline gets a row, so the panel can say "has not started" as well as count.
function courseRows(prog) {
  const p = (prog && typeof prog === "object" && !Array.isArray(prog)) ? prog : {};
  return COURSE_OUTLINE.map(function (c) {
    let started = 0, right = 0, first = 0, firstOf = 0, perfect = 0, last = 0;
    (c.sections || []).forEach(function (s) {
      const rec = p[c.id + "/" + s.id];
      if (!rec || typeof rec !== "object") return;
      const rr = rec.right && typeof rec.right === "object" ? rec.right : {};
      const nr = Object.keys(rr).length;
      if (nr || rec.read || rec.done) started++;
      right += nr;
      const ff = rec.first && typeof rec.first === "object" ? rec.first : {};
      Object.keys(ff).forEach(function (k) { firstOf++; if (ff[k] === 1) first++; });
      if (rec.perfect) perfect++;
      last = Math.max(last, Number(rec.done) || 0, Number(rec.read) || 0);
      Object.keys(rr).forEach(function (k) { last = Math.max(last, Number(rr[k]) || 0); });
    });
    const st = courseState(c, p);
    return { id: c.id, title: c.title, short: c.short, repeat: !!c.repeat, sections: (c.sections || []).length,
             started: started, done: st.done, of: st.of, right: right, first: first, firstOf: firstOf,
             perfect: perfect, last: last };
  });
}

// A reader's courses in one line, for the list.
function courseSummary(rows) {
  const s = { started: 0, finished: 0, lessons: 0, right: 0, last: 0 };
  rows.forEach(function (r) {
    if (r.started) s.started++;
    if (r.of > 0 && r.done === r.of) s.finished++;
    s.lessons += r.done; s.right += r.right; s.last = Math.max(s.last, r.last);
  });
  return s;
}

// Everything the site knows about one reader, gathered for the admin panel.
// Reads the same per-user R2 files the app itself writes (vocab, tips,
// progress, finished, settings) plus the account record, and returns totals
// with enough detail for the panel's drill-down windows — but never the
// password hash, which has no business leaving the bucket.
async function userDetail(email) {
  const account = await findAccount(email);
  if (!account) return null;
  const uid = account.id || userIdFor(email);
  const [vocab, tips, progress, finished, settings, stats, learned, songs, drills] = await Promise.all([
    r2GetJson(userDataKey(uid, "vocab")),
    r2GetJson(userDataKey(uid, "tips")),
    r2GetJson(userDataKey(uid, "progress")),
    r2GetJson(userDataKey(uid, "finished")),
    r2GetJson(userDataKey(uid, "settings")),
    r2GetJson(userDataKey(uid, "stats")),
    r2GetJson(userDataKey(uid, "learned")),
    r2GetJson(userDataKey(uid, "songs")),
    r2GetJson(userDataKey(uid, "drills")),
  ]);
  const [badgeFile, bibleread, annots, coursesFile] = await Promise.all([
    r2GetJson(userDataKey(uid, "badges")).catch(function () { return null; }),
    r2GetJson(userDataKey(uid, "bibleread")).catch(function () { return null; }),
    r2GetJson(userDataKey(uid, "annots")).catch(function () { return null; }),
    r2GetJson(userDataKey(uid, "courses")).catch(function () { return null; }),
  ]);
  const courseList = courseRows(coursesFile);
  const courseSum = courseSummary(courseList);
  const prog = (progress && typeof progress === "object" && !Array.isArray(progress)) ? progress : {};
  const fin  = (finished && typeof finished === "object" && !Array.isArray(finished)) ? finished : {};
  // One row per book the reader has opened, newest first. cidx/totalChapters
  // give the panel a position; lastRead orders the list.
  const reading = Object.keys(prog).filter(function (k) {
    return prog[k] && !prog[k].removed;
  }).map(function (k) {
    const p = prog[k] || {};
    return {
      key: k,
      title: p.title || k,
      author: p.author || "",
      cidx: p.cidx || 0,
      pidx: p.pidx || 0,
      totalChapters: p.totalChapters || 0,
      lastRead: p.lastRead || 0,
    };
  }).sort(function (a, b) { return (b.lastRead || 0) - (a.lastRead || 0); });
  // Unmarked books stay in the map as tombstones ({removed:true}) so the
  // unmark can win cross-device merges — they are not finished books.
  const finishedList = Object.keys(fin).filter(function (k) {
    return fin[k] && !fin[k].removed;
  }).map(function (k) {
    const f = fin[k] || {};
    return { key: k, title: f.title || k, author: f.author || "", at: f.at || 0 };
  }).sort(function (a, b) { return (b.at || 0) - (a.at || 0); });
  const vocabList = Array.isArray(vocab) ? vocab : [];
  const learnedList = Array.isArray(learned) ? learned : [];
  const log = logTotals(stats);
  const dr = (drills && typeof drills === "object" && !Array.isArray(drills)) ? drills : {};
  // Songs from the Music tab, most recently opened first. `n` is how many
  // times that song was opened, so the list doubles as what they keep
  // returning to rather than merely what they once clicked.
  const songMap = (songs && typeof songs === "object" && !Array.isArray(songs)) ? songs : {};
  const songList = Object.keys(songMap).map(function (k) {
    const v = songMap[k] || {};
    return { id: k, title: v.title || k, artist: v.artist || "", n: v.n || 1, at: v.at || 0 };
  }).sort(function (a, b) { return (b.at || 0) - (a.at || 0); });
  // Which books they drilled, so "forty questions" can be asked of where.
  const drillBooks = Object.keys(dr.byBook || {}).map(function (k) {
    const v = dr.byBook[k] || {};
    return { key: k, title: v.title || k, runs: v.runs || 0,
             questions: v.questions || 0, correct: v.correct || 0 };
  }).sort(function (a, b) { return (b.questions || 0) - (a.questions || 0); });
  return {
    email: account.email,
    id: uid,
    createdAt: account.createdAt || null,
    lastLoginAt: account.lastLoginAt || null,
    lastSeenAt: account.lastSeenAt || null,
    loginCount: account.loginCount || 0,
    approvedAt: account.approvedAt || null,
    passwordChangedAt: account.passwordChangedAt || null,
    isAdmin: isAdminEmail(account.email),
    counts: {
      vocab: vocabList.length,
      tips: Array.isArray(tips) ? tips.length : 0,
      booksOpened: reading.length,
      booksFinished: finishedList.length,
      hasSettings: !!settings,
      // The daily log behind the streak dots: Russian words scrolled through
      // in the reader, vocabulary-quiz answers, and days on which either
      // happened at all.
      wordsRead: log.read,
      practiced: log.practiced,
      daysActive: log.days,
      lastActive: log.last,
      streak: log.streak,
      learned: learnedList.length,
      songs: songList.length,
      songPlays: songList.reduce(function (n, x) { return n + (x.n || 0); }, 0),
      drillRuns: dr.runs || 0,
      drillQuestions: dr.questions || 0,
      drillCorrect: dr.correct || 0,
      coursesStarted: courseSum.started,
      coursesFinished: courseSum.finished,
      courseLessons: courseSum.lessons,
      courseRight: courseSum.right,
    },
    // A zero means two very different things and the panel must not conflate
    // them. Vocabulary, tips and marked-read have been written to R2 since the
    // beginning, so zero there is a real zero. Reading progress was never sent
    // to the server until now, so a missing file means "never measured" — and
    // the login counter did not exist at all, though lastLoginAt did, so an
    // account with a last-visit date and no count has certainly signed in.
    recorded: {
      progress: progress !== null,
      finished: finished !== null,
      vocab: vocab !== null,
      tips: tips !== null,
      settings: settings !== null,
      stats: stats !== null,
      learned: learned !== null,
      // Songs and case drills were kept in the browser until September 2026,
      // so a missing file here means the site never asked, not that the reader
      // never opened a song or finished a drill.
      songs: songs !== null,
      drills: drills !== null,
      logins: (account.loginCount || 0) > 0 || !account.lastLoginAt,
    },
    // Where the panel looked. Without this, an empty reader is ambiguous: no
    // data, or data filed under another id? Govorim predates the current auth,
    // and accounts carried over from the Clerk setup have their files under a
    // user_2… id that no longer derives from the email — see
    // /api/admin/import-userdata, which exists for exactly that. Showing the
    // id and which files answered turns the question into a fact.
    // Badges as the reader's own page last published them.
    badges: (badgeFile && Array.isArray(badgeFile.badges)) ? badgeFile.badges : [],
    // Their courses, those they have touched first, the most recent on top.
    courses: courseList.filter(function (r) { return r.started; })
      .sort(function (a, b) { return (b.last || 0) - (a.last || 0); }),
    badgeTotal: (badgeFile && badgeFile.total) || 0,
    badgesAt: (badgeFile && badgeFile.at) || 0,
    bibleChapters: (bibleread && typeof bibleread === "object") ? Object.keys(bibleread).length : 0,
    annotations: (annots && typeof annots === "object") ? Object.keys(annots.items || annots).length : 0,
    storage: { prefix: userDataKey(uid, "*").replace(/\*\.json$/, "") },
    reading: reading.slice(0, 100),
    finished: finishedList.slice(0, 100),
    songs: songList.slice(0, 200),
    drillBooks: drillBooks.slice(0, 100),
    // The last eight weeks of the daily log, for the little strip in the
    // window — the same shape the site trend uses.
    days: log.recent,
    // The words themselves, newest last as the app appends them. Capped: the
    // panel shows a scrollable window, not the whole dictionary in one JSON.
    vocab: vocabList.slice(-500).map(function (v) {
      if (typeof v === "string") return { ru: v, en: "" };
      return { ru: v.ru || "", en: v.en || "", addedAt: v.addedAt || 0 };
    }),
  };
}

// The catalogue's titles by filename, for turning a stored key back into a
// name. Read once per request; the keys are shown bare when the file is
// missing.
function catalogueTitles() {
  const titles = {};
  try {
    const man = JSON.parse(fs.readFileSync(path.join(process.cwd(), "private", "books", "index.json"), "utf8"));
    for (const b of man) if (b && b.filename) titles[b.filename] = { title: b.title || b.filename, author: b.author || "" };
  } catch (e) { /* the keys are shown bare */ }
  return titles;
}
function titleOf(titles, key) {
  const bare = String(key || "").replace(/^en:/, "");
  const info = titles[bare] || titles[bare.replace(/^novel\//, "")] || null;
  return { title: info ? info.title : bare, author: info ? info.author : "", en: /^en:/.test(String(key || "")) };
}

// A reader's name for the panel: their username, else their email.
function nameOf(a) {
  return a.username || a.email;
}

// The site day by day, assembled from every reader's own files: which books
// were opened (the shared tally), who read what and how much (the per-day
// log each reader's app keeps, with its books since October 2026), who marked
// which book read, which lessons and courses were finished, which badges were
// earned, and who was here at all. Days are UTC, like the shared tally.
async function dayLog(nDays) {
  const accounts = await listAccounts();
  const daily = await readDaily();
  const titles = catalogueTitles();
  const since = todayKey(Date.now() - Math.max(1, nDays) * 86400000);
  const days = {};
  const day = function (k) {
    if (!days[k]) days[k] = { date: k, opened: [], read: [], finished: [], lessons: [], courses: [], badges: [], active: [],
                              visits: 0, logins: 0, opens: 0, anonOpens: 0 };
    return days[k];
  };
  for (const k of Object.keys(daily)) {
    if (k < since) continue;
    const v = daily[k] || {};
    const d = day(k);
    d.visits = v.visits || 0; d.logins = v.logins || 0; d.opens = v.opens || 0; d.anonOpens = v.anonOpens || 0;
    d.opened = Object.keys(v.books || {}).map(function (key) {
      const t = titleOf(titles, key);
      return { key: key, n: v.books[key], title: t.title, author: t.author, en: t.en };
    }).sort(function (a, b) { return b.n - a.n || String(a.title).localeCompare(String(b.title), "ru"); });
  }
  const sectionTitle = {};
  COURSE_OUTLINE.forEach(function (c) {
    (c.sections || []).forEach(function (s) { sectionTitle[c.id + "/" + s.id] = { course: c.title, section: s.title, exam: !!s.exam }; });
  });
  for (const a of accounts) {
    const uid = a.id || userIdFor(a.email);
    const name = nameOf(a);
    const [stats, finished, courses, badges] = await Promise.all([
      r2GetJson(userDataKey(uid, "stats")).catch(function () { return null; }),
      r2GetJson(userDataKey(uid, "finished")).catch(function () { return null; }),
      r2GetJson(userDataKey(uid, "courses")).catch(function () { return null; }),
      r2GetJson(userDataKey(uid, "badges")).catch(function () { return null; }),
    ]);
    const st = (stats && typeof stats === "object" && !Array.isArray(stats)) ? stats : {};
    for (const k of Object.keys(st)) {
      if (!/^\d{4}-\d{2}-\d{2}$/.test(k) || k < since) continue;
      const r = st[k] || {};
      const any = ["read", "readEn", "practiced", "drills", "course", "sections"].some(function (f) { return (Number(r[f]) || 0) > 0; });
      if (any) day(k).active.push({ name: name, read: Number(r.read) || 0, readEn: Number(r.readEn) || 0, practiced: Number(r.practiced) || 0,
                                   drills: Number(r.drills) || 0, course: Number(r.course) || 0, sections: Number(r.sections) || 0 });
      const books = (r.books && typeof r.books === "object") ? r.books : {};
      for (const key of Object.keys(books)) {
        const t = titleOf(titles, key);
        day(k).read.push({ name: name, key: key, title: t.title, author: t.author, words: Number(books[key]) || 0 });
      }
    }
    const fin = (finished && typeof finished === "object" && !Array.isArray(finished)) ? finished : {};
    for (const key of Object.keys(fin)) {
      const f = fin[key];
      if (!f || f.removed || !f.at) continue;
      const k = todayKey(f.at);
      if (k < since) continue;
      day(k).finished.push({ name: name, title: f.title || key, author: f.author || "", at: f.at });
    }
    const cf = (courses && typeof courses === "object" && !Array.isArray(courses)) ? courses : {};
    const doneBy = {};        // course id → latest section done, to date a course's completion
    for (const key of Object.keys(cf)) {
      const rec = cf[key];
      if (!rec || typeof rec !== "object" || !rec.done) continue;
      const meta = sectionTitle[key];
      const k = todayKey(rec.done);
      const cid = key.split("/")[0];
      doneBy[cid] = Math.max(doneBy[cid] || 0, Number(rec.done) || 0);
      if (k < since || !meta) continue;
      if (meta.exam) day(k).courses.push({ name: name, title: meta.course, grade: rec.grade || null, at: rec.done });
      else day(k).lessons.push({ name: name, course: meta.course, section: meta.section, at: rec.done });
    }
    // a course with no exam counts as done the day its last lesson was
    COURSE_OUTLINE.forEach(function (c) {
      if (c.repeat || (c.sections || []).some(function (s) { return s.exam; })) return;
      const st2 = courseState(c, cf);
      if (st2.of > 0 && st2.done === st2.of && doneBy[c.id]) {
        const k = todayKey(doneBy[c.id]);
        if (k >= since) day(k).courses.push({ name: name, title: c.title, grade: null, at: doneBy[c.id] });
      }
    });
    const bl = (badges && Array.isArray(badges.badges)) ? badges.badges : [];
    for (const b of bl) {
      if (!b || !b.at) continue;
      const k = todayKey(b.at);
      if (k < since) continue;
      day(k).badges.push({ name: name, title: b.title || b.id, mark: b.mark || "", tier: b.tier || 0, at: b.at });
    }
  }
  const out = Object.keys(days).sort().reverse().map(function (k) {
    const d = days[k];
    d.read.sort(function (a, b) { return b.words - a.words; });
    d.active.sort(function (a, b) { return (b.read + b.practiced * 25) - (a.read + a.practiced * 25); });
    d.finished.sort(function (a, b) { return b.at - a.at; });
    d.lessons.sort(function (a, b) { return b.at - a.at; });
    d.badges.sort(function (a, b) { return b.at - a.at; });
    return d;
  });
  return { since: since, days: out, readers: accounts.length };
}

// Site-wide totals, summed across every account plus whatever the anonymous
// counter has seen. Accounts are read one at a time — the R2 token is
// object-scoped and cannot list a bucket, so there is no bulk read to be had —
// which is fine at this library's scale and would want caching at a thousand.
async function siteTotals() {
  const accounts = await listAccounts();
  const t = { accounts: accounts.length, booksOpened: 0, vocab: 0, finished: 0, tips: 0,
              readersWithProgress: 0, wordsRead: 0, practiced: 0, daysActive: 0,
              learned: 0, songs: 0, songPlays: 0, drillRuns: 0, drillQuestions: 0,
              drillCorrect: 0, readersWithDrills: 0, readersWithSongs: 0 };
  // Which books are marked read, across every account: title → how many readers.
  const finishedBy = {};
  for (const a of accounts) {
    const uid = a.id || userIdFor(a.email);
    const [vocab, tips, progress, finished, stats, learned, songs, drills] = await Promise.all([
      r2GetJson(userDataKey(uid, "vocab")),
      r2GetJson(userDataKey(uid, "tips")),
      r2GetJson(userDataKey(uid, "progress")),
      r2GetJson(userDataKey(uid, "finished")),
      r2GetJson(userDataKey(uid, "stats")),
      r2GetJson(userDataKey(uid, "learned")),
      r2GetJson(userDataKey(uid, "songs")),
      r2GetJson(userDataKey(uid, "drills")),
    ]);
    const lg = logTotals(stats);
    t.wordsRead += lg.read;
    t.practiced += lg.practiced;
    t.daysActive += lg.days;
    if (Array.isArray(learned)) t.learned += learned.length;
    if (songs && typeof songs === "object") {
      const ks = Object.keys(songs);
      if (ks.length) t.readersWithSongs += 1;
      t.songs += ks.length;
      for (const k of ks) t.songPlays += Number((songs[k] || {}).n) || 0;
    }
    if (drills && typeof drills === "object") {
      if (drills.runs) t.readersWithDrills += 1;
      t.drillRuns += Number(drills.runs) || 0;
      t.drillQuestions += Number(drills.questions) || 0;
      t.drillCorrect += Number(drills.correct) || 0;
    }
    if (Array.isArray(vocab)) t.vocab += vocab.length;
    if (Array.isArray(tips))  t.tips  += tips.length;
    if (progress && typeof progress === "object") {
      const n = Object.keys(progress).filter(function (k) {
        return progress[k] && !progress[k].removed;
      }).length;
      t.booksOpened += n;
      if (n) t.readersWithProgress += 1;
    }
    if (finished && typeof finished === "object") {
      for (const k of Object.keys(finished)) {
        const f = finished[k];
        if (!f || f.removed) continue;
        t.finished += 1;
        const id = f.filename || k;
        if (!finishedBy[id]) finishedBy[id] = { key: id, title: f.title || k, author: f.author || "", readers: 0, last: 0 };
        finishedBy[id].readers += 1;
        finishedBy[id].last = Math.max(finishedBy[id].last, Number(f.at) || 0);
      }
    }
  }
  // Signed-out readers keep everything in their own browser, so the only thing
  // the server can know about them is a count it was told about. See the
  // ?anon= branch in api/user-data.js.
  const anon = await r2GetJson(userDataKey("_stats", "anon"));
  t.anonBooksOpened = (anon && anon.booksOpened) || 0;
  t.anonSince = (anon && anon.since) || null;
  t.totalBooksOpened = t.booksOpened + t.anonBooksOpened;
  // Today, from the per-day tallies. Dates are UTC so the day does not shift
  // under whoever is reading the panel.
  const daily = await readDaily();
  const k = todayKey();
  const d0 = daily[k] || {};
  // The day's opens, book by book, titled from the catalogue where the key is a filename.
  const titles = catalogueTitles();
  const openedToday = Object.keys(d0.books || {}).map(function (key) {
    const t = titleOf(titles, key);
    return { key: key, n: d0.books[key], title: t.title, author: t.author, en: t.en };
  }).sort(function (a, b) { return b.n - a.n || String(a.title).localeCompare(String(b.title), "ru"); });
  t.finishedBooks = Object.values(finishedBy).sort(function (a, b) { return b.readers - a.readers || b.last - a.last; }).slice(0, 300);
  t.today = {
    date: k,
    books: openedToday,
    opens: d0.opens || 0,
    anonOpens: d0.anonOpens || 0,
    accountOpens: Math.max(0, (d0.opens || 0) - (d0.anonOpens || 0)),
    logins: d0.logins || 0,
    visits: d0.visits || 0,
    counting: Object.keys(daily).length > 0,
  };
  const site = await r2GetJson(userDataKey("_stats", "site"));
  t.visits = (site && site.visits) || 0;
  t.visitsSince = (site && site.since) || null;
  // Presses on the two donate buttons. A press is intent, not money: neither
  // PayPal nor Memorial reports back what happened after the reader left, so
  // these say how many people set out to give, never how many did.
  const clicks = await r2GetJson(userDataKey("_stats", "donate-clicks"));
  t.donate = {
    memorial: (clicks && clicks.memorial) || 0,
    costs: (clicks && clicks.costs) || 0,
    since: (clicks && clicks.since) || null,
  };
  t.today.donateMemorial = d0.donateMemorial || 0;
  t.today.donateCosts = d0.donateCosts || 0;
  t.today.songOpens = d0.songOpens || 0;
  // The last fortnight, for the little trend strip.
  t.recent = Object.keys(daily).sort().slice(-14).map(function (day) {
    const v = daily[day] || {};
    return { date: day, visits: v.visits || 0, opens: v.opens || 0, logins: v.logins || 0,
             donateMemorial: v.donateMemorial || 0, donateCosts: v.donateCosts || 0 };
  });
  return t;
}

// How many times each book has been opened, and how many accounts currently
// hold a saved position in it. The first is an event tally written when a book
// opens; the second is derived from the progress files and answers a different
// question — "how many readers are in the middle of this" rather than "how
// often has it been picked up". Both are useful and they are not the same, so
// the panel shows both rather than passing one off as the other.
// Opens recorded before the key filter was fixed had every Cyrillic letter
// stripped out of the filename, so «novel/<Cyrillic title>.fb2» was stored as
// «novel/ - .fb2» and several books shared one nonsense row. Where exactly one
// title in the catalogue collapses to such a key, its count belongs to that
// title and is moved there — and the repaired map is written back, so the row
// is gone for good rather than re-derived on every load. Where more than one
// title collapses to the same key the count cannot be attributed to either, so
// it is dropped: a row nobody can act on is worse than no row.
const OLD_FILTER = /[^\w.\/\- ]+/g;
async function repairLegacyBookKeys(opens) {
  const keys = Object.keys(opens);
  const damaged = keys.filter(function (k) {
    return k && !/[\u0400-\u04FF]/.test(k) && /(^|[\/\-])\s{1,}([\-.]|$)/.test(k);
  });
  if (!damaged.length) return { opens: opens, changed: false };
  let manifest = [];
  try {
    manifest = JSON.parse(fs.readFileSync(path.join(process.cwd(), "private", "books", "index.json"), "utf8"));
  } catch (e) { return { opens: opens, changed: false }; }
  const collapsed = {};
  for (const b of manifest) {
    const fn = (b && b.filename) || "";
    if (!/[\u0400-\u04FF]/.test(fn)) continue;
    const k = fn.replace(OLD_FILTER, "").slice(0, 160);
    (collapsed[k] = collapsed[k] || []).push(fn);
  }
  const next = Object.assign({}, opens);
  let changed = false;
  for (const k of damaged) {
    const owners = collapsed[k];
    if (owners && owners.length === 1) next[owners[0]] = (next[owners[0]] || 0) + next[k];
    delete next[k];
    changed = true;
  }
  return { opens: next, changed: changed };
}

async function bookStats() {
  let opens = (await r2GetJson(userDataKey("_stats", "books"))) || {};
  const repaired = await repairLegacyBookKeys(opens);
  if (repaired.changed) {
    opens = repaired.opens;
    try { await r2PutJson(userDataKey("_stats", "books"), opens); } catch (e) { /* display still works */ }
  }
  const readers = {};
  const accounts = await listAccounts();
  for (const a of accounts) {
    const uid = a.id || userIdFor(a.email);
    const progress = await r2GetJson(userDataKey(uid, "progress"));
    if (!progress || typeof progress !== "object") continue;
    for (const k of Object.keys(progress)) {
      const p = progress[k] || {};
      if (p.removed) continue;
      // Progress is keyed by the reader's own book key; the filename is the
      // stable thing both sides share.
      const id = p.filename || k;
      if (!readers[id]) readers[id] = { readers: 0, title: p.title || "", author: p.author || "" };
      readers[id].readers += 1;
    }
  }
  // The music, counted the same way and returned beside the books: the panel
  // asks one question — what does the library get opened for — and songs are
  // half the answer on a site that ships twenty-two of them.
  const songs = (await r2GetJson(userDataKey("_stats", "songs"))) || {};
  return { opens, readers, songs,
           since: (await r2GetJson(userDataKey("_stats", "anon")) || {}).since || null };
}

// The funding figures the public progress bar reads. Kept here rather than in
// a route of its own because Vercel's function budget is the reason the whole
// admin lives behind one dispatcher.
async function readFunding() {
  return (await r2GetJson(userDataKey("_stats", "funding"))) || { goal: 0, raised: 0, period: "", note: "" };
}

// One day on the site, whole. Everything the other panels split up — who came,
// what was opened and read, which words were saved and reviewed, which course
// exercises were answered — for a single UTC day, assembled from the shared
// tally plus every reader's own files. Nothing here is a new counter except the
// signed-out book list: the words, answers and timestamps were already being
// written by the app, they were just never read back together.
//
// Limits worth stating in the panel: a reader's own word count and card count
// are filed under THEIR calendar day, while timestamps (saved, reviewed,
// answered) are exact; a course exercise keeps the time it was FIRST answered
// right, so re-doing one does not show up there (the reader's course-answer
// count, which counts every answer, does); a word keeps only its latest review
// time, so "reviewed" is words, not answers; and signed-out visitors keep their
// reading in their own browser, so for them the server knows visits and which
// books were opened, never how much was read.
async function todayLog(dateArg) {
  const dkey = /^\d{4}-\d{2}-\d{2}$/.test(String(dateArg || "")) ? String(dateArg) : todayKey();
  const t0 = Date.parse(dkey + "T00:00:00Z");
  const t1 = t0 + 86400000;
  const inDay = function (ts) { const n = Number(ts) || 0; return n >= t0 && n < t1; };
  const hours = new Array(24).fill(0);
  const tick = function (ts) { hours[new Date(Number(ts)).getUTCHours()]++; };
  const titles = catalogueTitles();
  const sectionMeta = {};
  COURSE_OUTLINE.forEach(function (c) {
    (c.sections || []).forEach(function (s) {
      sectionMeta[c.id + "/" + s.id] = { cid: c.id, course: c.title, section: s.title, exam: !!s.exam };
    });
  });
  const accounts = await listAccounts();
  const daily = await readDaily();
  const d0 = daily[dkey] || {};
  const num = function (x) { return Number(x) || 0; };
  const asObj = function (x) { return (x && typeof x === "object" && !Array.isArray(x)) ? x : {}; };

  async function oneReader(a) {
    const uid = a.id || userIdFor(a.email);
    const get = function (n) { return r2GetJson(userDataKey(uid, n)).catch(function () { return null; }); };
    const [stats, vocab, tips, progress, finished, courses, badges, songs, learned] = await Promise.all([
      get("stats"), get("vocab"), get("tips"), get("progress"), get("finished"), get("courses"),
      get("badges"), get("songs"), get("learned"),
    ]);
    const u = {
      name: nameOf(a), email: a.email,
      createdAt: a.createdAt || 0, lastSeenAt: a.lastSeenAt || 0, lastLoginAt: a.lastLoginAt || 0,
      newToday: inDay(a.createdAt), signedInToday: inDay(a.lastLoginAt), seenToday: inDay(a.lastSeenAt),
    };
    if (u.signedInToday) tick(a.lastLoginAt);
    // the reader's own daily record
    const st = asObj(asObj(stats)[dkey]);
    u.read = num(st.read); u.readEn = num(st.readEn); u.practiced = num(st.practiced);
    u.drills = num(st.drills); u.courseAnswers = num(st.course); u.sections = num(st.sections);
    u.books = Object.keys(asObj(st.books)).map(function (key) {
      const t = titleOf(titles, key);
      return { key: key, title: t.title, author: t.author, en: t.en, words: num(st.books[key]) };
    }).sort(function (x, y) { return y.words - x.words; });
    // vocabulary: saved, reviewed, retired
    const vl = (Array.isArray(vocab) ? vocab : []).filter(function (v) { return v && typeof v === "object"; });
    const ll = (Array.isArray(learned) ? learned : []).filter(function (v) { return v && typeof v === "object"; });
    const all = vl.concat(ll);
    const srcOf = function (v) {
      if (v.srcTitle) return v.srcTitle;
      if (v.srcBook) return titleOf(titles, v.srcBook).title;
      return "";
    };
    const savedAll = all.filter(function (v) { return inDay(v.created || v.addedAt); });
    savedAll.forEach(function (v) { tick(v.created || v.addedAt); });
    u.vocabSaved = savedAll.length;
    u.saved = savedAll.slice(0, 80).map(function (v) {
      return { ru: v.ru || "", en: v.en || "", pos: v.pos || "", from: srcOf(v), lang: v.site === "en" ? "en" : "ru" };
    });
    const revAll = all.filter(function (v) { return v.srs && inDay(v.srs.last); });
    revAll.forEach(function (v) { tick(v.srs.last); });
    u.vocabReviewed = revAll.length;
    u.vocabFirstSeen = revAll.filter(function (v) { return num(v.srs.reps) === 1; }).length;
    u.vocabMissed = revAll.filter(function (v) { return num(v.srs.run) === 0; }).length;
    u.reviewed = revAll.slice(0, 80).map(function (v) {
      return { ru: v.ru || "", en: v.en || "", reps: num(v.srs.reps), ok: num(v.srs.run) > 0 };
    });
    const retired = ll.filter(function (v) { return inDay(v.learnedAt); });
    retired.forEach(function (v) { tick(v.learnedAt); });
    u.retired = retired.map(function (v) { return { ru: v.ru || "", en: v.en || "" }; }).slice(0, 40);
    const tipsToday = (Array.isArray(tips) ? tips : []).filter(function (t) { return t && inDay(t.created || t.id); });
    tipsToday.forEach(function (t) { tick(t.created || t.id); });
    u.tips = tipsToday.length;
    // course exercises answered right for the first time today, by lesson
    const cf = asObj(courses);
    u.course = [];
    Object.keys(cf).forEach(function (key) {
      const rec = cf[key];
      const meta = sectionMeta[key];
      if (!rec || typeof rec !== "object" || !meta) return;
      const rr = asObj(rec.right), ff = asObj(rec.first);
      let solved = 0, first = 0;
      Object.keys(rr).forEach(function (e) {
        if (!inDay(rr[e])) return;
        solved++; tick(rr[e]);
        if (ff[e] === 1) first++;
      });
      const doneToday = inDay(rec.done), readToday = inDay(rec.read);
      if (doneToday) tick(rec.done);
      if (!solved && !doneToday && !readToday) return;
      u.course.push({ cid: meta.cid, course: meta.course, section: meta.section, exam: meta.exam, solved: solved,
                      first: first, done: doneToday, opened: readToday, grade: doneToday && rec.grade != null ? rec.grade : null });
    });
    // books whose saved position moved today
    const pm = asObj(progress);
    u.positions = Object.keys(pm).map(function (k) {
      const p = pm[k];
      if (!p || p.removed || !inDay(p.lastRead)) return null;
      tick(p.lastRead);
      return { title: p.title || k, author: p.author || "", chapter: (num(p.cidx) + 1), of: num(p.totalChapters), at: num(p.lastRead) };
    }).filter(Boolean).sort(function (x, y) { return y.at - x.at; });
    const fm = asObj(finished);
    u.finished = Object.keys(fm).map(function (k) {
      const f = fm[k];
      if (!f || f.removed || !inDay(f.at)) return null;
      tick(f.at);
      return { title: f.title || k, author: f.author || "", at: num(f.at) };
    }).filter(Boolean);
    u.badges = ((badges && Array.isArray(badges.badges)) ? badges.badges : []).filter(function (b) { return b && inDay(b.at); })
      .map(function (b) { tick(b.at); return { title: b.title || b.id || "", mark: b.mark || "", tier: num(b.tier), at: num(b.at) }; });
    const sm = asObj(songs);
    u.songs = Object.keys(sm).map(function (k) {
      const v = sm[k];
      if (!v || !inDay(v.at)) return null;
      tick(v.at);
      return { title: v.title || k, artist: v.artist || "", n: num(v.n) || 1 };
    }).filter(Boolean);
    u.active = !!(u.read || u.readEn || u.practiced || u.drills || u.courseAnswers || u.sections || u.books.length ||
                  u.vocabSaved || u.vocabReviewed || u.retired.length || u.tips || u.course.length || u.positions.length ||
                  u.finished.length || u.badges.length || u.songs.length);
    u.score = u.read + u.readEn + u.practiced * 25 + u.drills * 10 + u.courseAnswers * 10 + u.vocabSaved * 10;
    return u;
  }

  const users = [];
  let next = 0;
  async function worker() {
    while (next < accounts.length) {
      const a = accounts[next++];
      try { users.push(await oneReader(a)); } catch (e) { /* one unreadable account must not blank the day */ }
    }
  }
  await Promise.all(Array.from({ length: Math.min(6, accounts.length) }, worker));
  const readers = users.filter(function (u) { return u.active; }).sort(function (x, y) { return y.score - x.score; });

  // the library, by book: opened (everyone, from the shared tally), opened signed
  // out, words read (account holders), how many readers, words saved from it
  const bare = function (k) { return String(k || "").replace(/^en:/, ""); };
  const bk = {};
  const bookRow = function (key) {
    const b = bare(key);
    if (!bk[b]) {
      const t = titleOf(titles, key);
      bk[b] = { key: b, title: t.title, author: t.author, en: t.en, opens: 0, anonOpens: 0, words: 0, readers: [], saved: 0 };
    }
    return bk[b];
  };
  Object.keys(d0.books || {}).forEach(function (k) { bookRow(k).opens += num(d0.books[k]); });
  Object.keys(d0.anonBooks || {}).forEach(function (k) { bookRow(k).anonOpens += num(d0.anonBooks[k]); });
  readers.forEach(function (u) {
    u.books.forEach(function (b) { const r = bookRow(b.key); r.words += b.words; r.readers.push(u.name); });
  });
  const books = Object.values(bk).map(function (b) {
    b.readerCount = b.readers.length; b.readers = b.readers.slice(0, 12); return b;
  }).sort(function (x, y) { return y.words - x.words || y.opens - x.opens || String(x.title).localeCompare(String(y.title), "ru"); });

  // vocabulary saved, by the book it came from
  const src = {};
  readers.forEach(function (u) {
    u.saved.forEach(function (w) { const k = w.from || "(no source recorded)"; src[k] = (src[k] || 0) + 1; });
  });
  const vocabSources = Object.keys(src).map(function (k) { return { title: k, n: src[k] }; })
    .sort(function (x, y) { return y.n - x.n; }).slice(0, 40);

  // the courses, lesson by lesson
  const cmap = {};
  readers.forEach(function (u) {
    u.course.forEach(function (r) {
      const c = cmap[r.cid] || (cmap[r.cid] = { id: r.cid, title: r.course, users: {}, solved: 0, first: 0, lessons: 0, exams: 0, secs: {} });
      c.users[u.name] = 1; c.solved += r.solved; c.first += r.first;
      if (r.done) { if (r.exam) c.exams++; else c.lessons++; }
      const sk = r.section + (r.exam ? " (exam)" : "");
      const s = c.secs[sk] || (c.secs[sk] = { title: sk, exam: r.exam, users: {}, solved: 0, first: 0, done: 0, grades: [] });
      s.users[u.name] = 1; s.solved += r.solved; s.first += r.first;
      if (r.done) { s.done++; if (r.grade != null) s.grades.push(r.grade); }
    });
  });
  const courses = Object.values(cmap).map(function (c) {
    return { id: c.id, title: c.title, readers: Object.keys(c.users), solved: c.solved, first: c.first, lessons: c.lessons, exams: c.exams,
             sections: Object.values(c.secs).map(function (s) {
               return { title: s.title, exam: s.exam, readers: Object.keys(s.users).length, solved: s.solved, first: s.first, done: s.done, grades: s.grades };
             }).sort(function (x, y) { return y.solved - x.solved; }) };
  }).sort(function (x, y) { return y.solved - x.solved; });

  const sum = function (f) { return readers.reduce(function (t, u) { return t + f(u); }, 0); };
  const songMap = {};
  readers.forEach(function (u) { u.songs.forEach(function (s) { const k = s.title + "|" + s.artist; songMap[k] = songMap[k] || { title: s.title, artist: s.artist, who: [] }; songMap[k].who.push(u.name); }); });
  const totals = {
    activeReaders: readers.length,
    newAccounts: users.filter(function (u) { return u.newToday; }).length,
    signedIn: users.filter(function (u) { return u.signedInToday; }).length,
    seen: users.filter(function (u) { return u.seenToday; }).length,
    wordsRead: sum(function (u) { return u.read; }), wordsReadEn: sum(function (u) { return u.readEn; }),
    cards: sum(function (u) { return u.practiced; }), drillAnswers: sum(function (u) { return u.drills; }),
    courseAnswers: sum(function (u) { return u.courseAnswers; }), lessonsFinished: sum(function (u) { return u.sections; }),
    exercisesSolved: sum(function (u) { return u.course.reduce(function (t, r) { return t + r.solved; }, 0); }),
    firstTry: sum(function (u) { return u.course.reduce(function (t, r) { return t + r.first; }, 0); }),
    vocabSaved: sum(function (u) { return u.vocabSaved; }), vocabReviewed: sum(function (u) { return u.vocabReviewed; }),
    vocabFirstSeen: sum(function (u) { return u.vocabFirstSeen; }), vocabMissed: sum(function (u) { return u.vocabMissed; }),
    retired: sum(function (u) { return u.retired.length; }), tips: sum(function (u) { return u.tips; }),
    booksFinished: sum(function (u) { return u.finished.length; }), badges: sum(function (u) { return u.badges.length; }),
    songsPlayed: sum(function (u) { return u.songs.length; }), booksTouched: books.filter(function (b) { return b.words || b.opens; }).length,
  };
  const trend = Object.keys(daily).filter(function (k) { return k <= dkey; }).sort().slice(-8).map(function (k) {
    const v = daily[k] || {};
    return { date: k, visits: num(v.visits), anonVisits: num(v.anonVisits), logins: num(v.logins), opens: num(v.opens), anonOpens: num(v.anonOpens) };
  });
  return {
    date: dkey, isToday: dkey === todayKey(), now: Date.now(), accounts: accounts.length,
    site: { visits: num(d0.visits), anonVisits: num(d0.anonVisits), logins: num(d0.logins), opens: num(d0.opens), anonOpens: num(d0.anonOpens),
            songOpens: num(d0.songOpens), donateMemorial: num(d0.donateMemorial), donateCosts: num(d0.donateCosts),
            anonBooksKnown: !!d0.anonBooks },
    totals: totals, readers: readers, quiet: users.length - readers.length, books: books, vocabSources: vocabSources,
    courses: courses, songs: Object.values(songMap), hours: hours, trend: trend,
  };
}

export async function handleUsers(req, res) {
  const a = await requireAdmin(req, res);
  if (!a) return;

  if (req.method === "GET") {
    // /api/admin/users?totals=1 — the whole site at once.
    if (req.query && req.query.totals) {
      try {
        return res.status(200).json({ totals: await siteTotals() });
      } catch (err) {
        return res.status(500).json({ error: "Failed to total: " + (err.message || err) });
      }
    }
    // /api/admin/users?today=1[&date=YYYY-MM-DD] — one day on the site, whole.
    if (req.query && req.query.today) {
      try {
        return res.status(200).json(await todayLog(req.query.date));
      } catch (err) {
        return res.status(500).json({ error: "Failed to read the day: " + (err.message || err) });
      }
    }
    // /api/admin/users?days=30 — the site day by day.
    if (req.query && req.query.days) {
      try {
        return res.status(200).json(await dayLog(Math.min(90, Number(req.query.days) || 30)));
      } catch (err) {
        return res.status(500).json({ error: "Failed to read the days: " + (err.message || err) });
      }
    }
    // /api/admin/users?funding=1 — the cost target and what has come in.
    if (req.query && req.query.funding) {
      try { return res.status(200).json({ funding: await readFunding() }); }
      catch (err) { return res.status(500).json({ error: "Failed to read funding: " + (err.message || err) }); }
    }
    // /api/admin/users?books=1 — the per-book tallies.
    if (req.query && req.query.books) {
      try {
        return res.status(200).json(await bookStats());
      } catch (err) {
        return res.status(500).json({ error: "Failed to read book stats: " + (err.message || err) });
      }
    }
    // /api/admin/users?email=… — one reader in full.
    const email = req.query && req.query.email;
    if (email) {
      try {
        const detail = await userDetail(String(email).trim().toLowerCase());
        if (!detail) return res.status(404).json({ error: "No account with that email." });
        return res.status(200).json({ user: detail });
      } catch (err) {
        return res.status(500).json({ error: "Failed to load user: " + (err.message || err) });
      }
    }
    try {
      const users = await listAccounts();
      // Each row carries the reader's counts (from the leaderboard file, one
      // read for everyone) and their badges (one small file each), so the
      // list itself says who reads what without opening anyone.
      const rows = await readBoardRows().catch(function () { return {}; });
      const badgeFiles = await Promise.all(users.map(function (u) {
        return r2GetJson(userDataKey(u.id, "badges")).catch(function () { return null; });
      }));
      // Their course progress, one small file each, folded into a line per
      // reader and into a table per course for the whole site.
      const courseFiles = await Promise.all(users.map(function (u) {
        return r2GetJson(userDataKey(u.id, "courses")).catch(function () { return null; });
      }));
      // And what each is reading now: their saved positions, the latest first.
      const progressFiles = await Promise.all(users.map(function (u) {
        return r2GetJson(userDataKey(u.id, "progress")).catch(function () { return null; });
      }));
      const site = COURSE_OUTLINE.map(function (c) {
        return { id: c.id, title: c.title, short: c.short, repeat: !!c.repeat, sections: (c.sections || []).length,
                 readers: 0, finished: 0, lessons: 0, right: 0, first: 0, firstOf: 0, perfect: 0, last: 0 };
      });
      users.forEach(function (u, i) {
        const rows = courseRows(courseFiles[i]);
        u.courses = courseSummary(rows);
        // The courses themselves, those touched, the most recent first.
        u.courseList = rows.filter(function (r) { return r.started; })
          .sort(function (a, b) { return (b.last || 0) - (a.last || 0); })
          .map(function (r) { return { id: r.id, title: r.title, short: r.short, done: r.done, of: r.of, right: r.right,
                                        finished: r.of > 0 && r.done === r.of, repeat: r.repeat, last: r.last }; });
        const prog = progressFiles[i];
        const pm = (prog && typeof prog === "object" && !Array.isArray(prog)) ? prog : {};
        u.reading = Object.keys(pm).filter(function (k) { return pm[k] && !pm[k].removed; }).map(function (k) {
          const p = pm[k] || {};
          return { key: k, filename: p.filename || k, title: p.title || k, author: p.author || "", cidx: p.cidx || 0,
                   totalChapters: p.totalChapters || 0, lastRead: p.lastRead || 0 };
        }).sort(function (a, b) { return (b.lastRead || 0) - (a.lastRead || 0); }).slice(0, 12);
        rows.forEach(function (r, k) {
          const t = site[k];
          if (r.started) t.readers++;
          if (r.of > 0 && r.done === r.of) t.finished++;
          t.lessons += r.done; t.right += r.right; t.first += r.first; t.firstOf += r.firstOf;
          t.perfect += r.perfect; t.last = Math.max(t.last, r.last);
        });
      });
      users.forEach(function (u, i) {
        const r = rows[u.id] || {};
        u.stats = { words: r.words || 0, read: r.read || 0, learned: r.learned || 0,
                    reviewed: r.reviewed || 0, drills: r.drills || 0, songs: r.songs || 0, at: r.at || 0 };
        const bf = badgeFiles[i];
        const list = (bf && Array.isArray(bf.badges)) ? bf.badges : [];
        u.badges = {
          n: list.length, total: (bf && bf.total) || 0,
          top: list.slice().sort(function (a, b) { return (b.tier || 0) - (a.tier || 0) || (b.at || 0) - (a.at || 0); })
            .slice(0, 10).map(function (b) { return { mark: b.mark, tier: b.tier, title: b.title }; }),
          // every badge, so the panel can say who holds which
          all: list.map(function (b) { return { id: b.id || b.title, mark: b.mark, tier: b.tier || 0, title: b.title, at: b.at || 0 }; }),
        };
      });
      return res.status(200).json({ users, courses: site });
    } catch (err) {
      return res.status(500).json({ error: "Failed to list users: " + (err.message || err) });
    }
  }

  if (req.method === "POST" && req.query && req.query.funding) {
    let body = req.body;
    if (typeof body === "string") { try { body = JSON.parse(body); } catch (_) { body = {}; } }
    body = body || {};
    const f = {
      goal: Math.max(0, Number(body.goal) || 0),
      raised: Math.max(0, Number(body.raised) || 0),
      period: String(body.period || "").slice(0, 60),
      note: String(body.note || "").slice(0, 200),
      updatedAt: Date.now(),
    };
    try {
      await r2PutJson(userDataKey("_stats", "funding"), f);
      return res.status(200).json({ ok: true, funding: f });
    } catch (err) {
      return res.status(500).json({ error: "Failed to save funding: " + (err.message || err) });
    }
  }

  if (req.method === "POST") {
    let body = req.body;
    if (typeof body === "string") { try { body = JSON.parse(body); } catch (_) { body = {}; } }
    body = body || {};
    const email = String(body.email || "").trim().toLowerCase();
    if (!email) return res.status(400).json({ error: "email is required" });
    if (isAdminEmail(email)) {
      return res.status(400).json({ error: "The admin account cannot be changed here." });
    }
    const approved = body.approved !== false;
    try {
      const { error } = await setApproval(email, approved);
      if (error) return res.status(404).json({ error });
      const users = await listAccounts();
      return res.status(200).json({ ok: true, users });
    } catch (err) {
      return res.status(500).json({ error: "Failed to update user: " + (err.message || err) });
    }
  }

  return res.status(405).json({ error: "Method not allowed" });
}
