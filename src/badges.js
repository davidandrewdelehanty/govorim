// Badges: worked out from records a reader already has — the finished
// shelf, the reading log, vocabulary, drills, songs, Bible chapters. Shared by
// the app (the reader's own page) and the server (another reader's badges,
// shown from a tap on their name), so both always agree.
function ruPlural(n, one, few, many) {
  var m10 = n % 10, m100 = n % 100;
  if (m10 === 1 && m100 !== 11) return one;
  if (m10 >= 2 && m10 <= 4 && (m100 < 12 || m100 > 14)) return few;
  return many;
}

// ── Badges ───────────────────────────────────────────────────────────────
// Rewards a reader collects, worked out entirely from records the page
// already holds — the finished shelf, the reading log, the vocabulary, the
// drills and the songs — so they can never disagree with the profile, and
// nothing new is stored but which ones the reader has already been shown.
//
//   · an author badge for finishing any work by that author, and higher
//     ones for finishing several of theirs (where they wrote that many);
//   · a badge for the first work finished of each kind — novel, play, poem —
//     and tiers for finishing more of that kind;
//   · milestones for words read, days in a row, cards reviewed, words
//     learned, case drills and songs.
var BADGE_KINDS = [
  { cat: "Novels", champ: "Чемпион романов", first: "Первый роман",                  ru: "Романы",          one: "роман",      tiers: [1, 3, 5, 10, 25] },
  { cat: "Novellas", champ: "Чемпион повестей", first: "Первая повесть",                ru: "Повести",         one: "повесть",    tiers: [1, 3, 5, 10, 25] },
  { cat: "Short Stories", champ: "Чемпион рассказов", first: "Первый рассказ",           ru: "Рассказы",        one: "рассказ",    tiers: [1, 10, 25, 50, 100, 250] },
  { cat: "Poetry", champ: "Чемпион поэзии", first: "Первое стихотворение",                  ru: "Стихи",           one: "стихотворение", tiers: [1, 10, 25, 50, 100, 250] },
  { cat: "Plays", champ: "Чемпион пьес", first: "Первая пьеса",                   ru: "Пьесы",           one: "пьесу",      tiers: [1, 3, 5, 10, 25] },
  { cat: "Theatrical Performances", champ: "Чемпион спектаклей", first: "Первый спектакль", ru: "Спектакли",       one: "спектакль",  tiers: [1, 3, 5] },
  { cat: "Religious Texts", champ: "Чемпион священных текстов", first: "Первая священная книга",         ru: "Священные тексты", one: "книгу",     tiers: [1] },
  { cat: "Speeches by Soviet Leaders", champ: "Чемпион речей", first: "Первая речь", ru: "Речи",         one: "речь",       tiers: [1, 5, 10, 25],
    en: "speech", enMany: "speeches" },
  { cat: "Fairytales", champ: "Чемпион сказок", first: "Первая сказка",             ru: "Сказки",          one: "сказку",     tiers: [1, 5, 10, 20],
    en: "fairy tale", enMany: "fairy tales" },
];
// Every kind also counts 5, 10, 15 and 20 finished, whatever else its own
// steps are (a tier larger than the shelf holds is never offered).
var BADGE_STEP_TIERS = [5, 10, 15, 20];
BADGE_KINDS.forEach(function(k) {
  k.tiers = k.tiers.concat(BADGE_STEP_TIERS).filter(function(t, i, a){ return a.indexOf(t) === i; })
    .sort(function(a, b){ return a - b; });
});
// The great long novels of Russian literature (catalogue entries carrying
// "great": true) earn a badge of their own on top of the novel badges.
var BADGE_GREAT_TIERS = [1, 3, 5, 10, 15, 20];
var BADGE_MILESTONES = [
  { id: "words",   ru: "Прочитано слов",       en: "Russian words read",    tiers: [10000, 50000, 100000, 250000, 500000, 1000000, 2500000] },
  { id: "streak",  ru: "Дней подряд",          en: "longest streak, in days", tiers: [3, 7, 14, 30, 100, 365] },
  { id: "cards",   ru: "Карточек повторено",   en: "vocabulary cards reviewed", tiers: [100, 500, 1000, 5000, 10000] },
  { id: "learned", ru: "Слов выучено",         en: "words learned and retired", tiers: [10, 50, 100, 250, 500, 1000] },
  { id: "saved",   ru: "Слов сохранено",       en: "words saved to your vocabulary", tiers: [25, 100, 250, 500, 1000] },
  { id: "drills",  ru: "Верных падежей",       en: "right answers in case drills", tiers: [10, 50, 100, 250, 500, 1000] },
  { id: "songs",   ru: "Песен прослушано",     en: "different songs listened to", tiers: [1, 10, 25, 50, 100] },
];
// Several works by one author: only offered where the author wrote that many.
var BADGE_AUTHOR_TIERS = [3, 10, 25, 50, 100];
var BADGE_SKIP_AUTHORS = { "Religious Texts": 1 };

function badgeShort(n) {
  if (n >= 1000000) return (Math.round(n / 100000) / 10) + "M";
  if (n >= 1000) return Math.round(n / 1000) + "k";
  return String(n);
}
// An author's surname, for the medal and the badge's name: «Чехов А.П.» → «Чехов».
function badgeSurname(a) {
  return String(a || "").replace(/\s+[А-ЯЁA-Z]\.(\s*[А-ЯЁA-Z]\.)?\s*$/, "").trim() || String(a || "");
}
// The genitive of a surname, for «Читатель Чехова». The common endings are
// regular; anything else is left as it is written.
function badgeGen(s) {
  var w = String(s || "");
  if (/[ая]$/.test(w) && !/(ая|яя)$/.test(w)) return w;          // Драгунский-type stays; Толстая unlikely
  if (/ий$/.test(w)) return w.replace(/ий$/, "ого");
  if (/ой$/.test(w)) return w.replace(/ой$/, "ого");
  if (/ый$/.test(w)) return w.replace(/ый$/, "ого");
  if (/(ов|ев|ёв|ин|ын)$/.test(w)) return w + "а";
  if (/[бвгджзклмнпрстфхцчшщ]$/.test(w)) return w + "а";
  return w;
}

// The books of the Synodal Bible, in its order, with their chapter counts. A
// Bible book is read when every one of its chapters has been read to its end
// (src.bibleRead, keyed by chapter heading — «Бытие 1»).
var BIBLE_BOOKS = [["Бытие", 50], ["Исход", 40], ["Левит", 27], ["Числа", 36], ["Второзаконие", 34], ["Иисуса Навина", 24], ["Судей", 21], ["Руфь", 4], ["1-я Царств", 31], ["2-я Царств", 24], ["3-я Царств", 22], ["4-я Царств", 25], ["1-я Паралипоменон", 29], ["2-я Паралипоменон", 36], ["Молитва Манассии", 1], ["1-я Ездры", 10], ["Неемии", 13], ["2-я Ездры", 9], ["Товит", 14], ["Иудифь", 16], ["Есфирь", 10], ["Иов", 42], ["Псалтирь", 151], ["Притчи", 31], ["Екклесиаст", 12], ["Песнь песней", 8], ["Премудрости Соломона", 19], ["Сирах", 51], ["Исаия", 66], ["Иеремия", 52], ["Плач Иеремии", 5], ["Послание Иеремии", 1], ["Варух", 5], ["Иезекииль", 48], ["Даниил", 14], ["Осия", 14], ["Иоиль", 3], ["Амос", 9], ["Авдий", 1], ["Иона", 4], ["Михей", 7], ["Наум", 3], ["Аввакум", 3], ["Софония", 3], ["Аггей", 2], ["Захария", 14], ["Малахия", 4], ["1-я Маккавейская", 16], ["2-я Маккавейская", 15], ["3-я Маккавейская", 7], ["3-я Ездры", 16], ["Матфея", 28], ["Марка", 16], ["Луки", 24], ["Иоанна", 21], ["Деяния", 28], ["Иакова", 5], ["1-е Петра", 5], ["2-е Петра", 3], ["1-е Иоанна", 5], ["2-е Иоанна", 1], ["3-е Иоанна", 1], ["Иуды", 1], ["Римлянам", 16], ["1-е Коринфянам", 16], ["2-е Коринфянам", 13], ["Галатам", 6], ["Ефесянам", 6], ["Филиппийцам", 4], ["Колоссянам", 4], ["1-е Фессалоникийцам", 5], ["2-е Фессалоникийцам", 3], ["1-е Тимофею", 6], ["2-е Тимофею", 4], ["Титу", 3], ["Филимону", 1], ["Евреям", 13], ["Откровение", 22]];
var BIBLE_NT_FROM = "Матфея";
function bibleMark(name) {
  var m = /^(\d)-[яе]\s+(.)(.)/.exec(name);
  if (m) return m[1] + m[2] + m[3];
  return name.slice(0, 3);
}

function computeBadges(src) {
  var books = src.books || [];
  var byFile = {};
  books.forEach(function(b){ if (b && b.filename) byFile[b.filename] = b; });
  // Finished works, each once: a play marked read with its спектакль is two
  // works of two kinds, but the same title by the same author is counted once.
  var done = [], seen = {};
  Object.keys(src.finished || {}).forEach(function(k) {
    var f = src.finished[k];
    if (!f || f.removed) return;
    var fn = k.split("::")[0];
    var b = byFile[fn] || null;
    var cat = (b && b.category) || f.category || "";
    var author = (b && b.author) || f.author || "";
    var tag = fn + "|" + cat;
    if (seen[tag]) return;
    seen[tag] = 1;
    done.push({ title: (b && b.title) || f.title || "", author: author, cat: cat, at: f.at || 0,
                great: !!(b && b.great) });
  });
  var out = [];
  var add = function(b) { out.push(b); };

  // Kinds of work.
  BADGE_KINDS.forEach(function(k) {
    var mine = done.filter(function(d){ return d.cat === k.cat; });
    var available = books.filter(function(b){ return b && b.category === k.cat; }).length;
    if (!available) return;
    k.tiers.forEach(function(t, i) {
      if (t > available) return;
      var first = i === 0;
      var when = mine.length >= t ? mine.map(function(d){ return d.at; }).sort(function(a,b){ return a-b; })[t - 1] : 0;
      add({
        id: "kind:" + k.cat + ":" + t, group: "kind", tier: i, cat: k.cat,
        mark: first ? k.ru.slice(0, 1) : String(t),
        title: first ? k.first : (k.ru + ": " + t),
        desc: first ? ("Finish your first " + (k.en || k.cat.toLowerCase().replace(/s$/, "")))
                    : ("Finish " + t + " " + (k.enMany || k.cat.toLowerCase())),
        earned: mine.length >= t, n: Math.min(mine.length, t), of: t, at: when,
      });
    });
  });

  // Champions: every work of a kind on the shelf, finished. Recounted from the
  // shelf as it stands, so a new tale or speech puts the badge back in reach.
  BADGE_KINDS.forEach(function(k) {
    var available = books.filter(function(b){ return b && b.category === k.cat; }).length;
    if (available < 2 || !k.champ) return;
    var mine = done.filter(function(d){ return d.cat === k.cat; });
    var ats = mine.map(function(d){ return d.at; }).sort(function(a, b){ return a - b; });
    add({
      id: "champ:" + k.cat, group: "kind", tier: 9, mark: "♛", cat: k.cat,
      title: k.champ, desc: "Finish every one of the " + available + " " + (k.enMany || k.cat.toLowerCase()) + " in the library",
      earned: mine.length >= available, n: Math.min(mine.length, available), of: available,
      at: mine.length >= available ? ats[available - 1] : 0,
    });
  });

  // The great novels: Война и мир, Братья Карамазовы, Тихий Дон and the rest.
  (function() {
    var greatAll = books.filter(function(b){ return b && b.great; }).length;
    if (!greatAll) return;
    var mineG = done.filter(function(d){ return d.great; });
    var ats = mineG.map(function(d){ return d.at; }).sort(function(a, b){ return a - b; });
    BADGE_GREAT_TIERS.forEach(function(t, i) {
      if (t > greatAll) return;
      add({
        id: "great:" + t, group: "kind", tier: i, mark: i === 0 ? "★" : String(t), great: true,
        title: i === 0 ? "Великий роман" : ("Великие романы: " + t),
        desc: i === 0 ? "Finish one of the great Russian novels" : ("Finish " + t + " of the great Russian novels"),
        earned: mineG.length >= t, n: Math.min(mineG.length, t), of: t, at: mineG.length >= t ? ats[t - 1] : 0,
      });
    });
    add({
      id: "champ:great", group: "kind", tier: 9, mark: "♛", great: true,
      title: "Чемпион великих романов", desc: "Finish all " + greatAll + " of the great Russian novels",
      earned: mineG.length >= greatAll, n: Math.min(mineG.length, greatAll), of: greatAll,
      at: mineG.length >= greatAll ? ats[greatAll - 1] : 0,
    });
  })();

  // Authors.
  var authorsAll = {};
  books.forEach(function(b){
    var a = b && b.author;
    if (!a || BADGE_SKIP_AUTHORS[a]) return;
    authorsAll[a] = (authorsAll[a] || 0) + 1;
  });
  var mineBy = {};
  done.forEach(function(d){
    if (!d.author || BADGE_SKIP_AUTHORS[d.author]) return;
    (mineBy[d.author] = mineBy[d.author] || []).push(d);
  });
  Object.keys(authorsAll).sort(function(a, b){
    return (mineBy[b] ? mineBy[b].length : 0) - (mineBy[a] ? mineBy[a].length : 0) || authorsAll[b] - authorsAll[a];
  }).forEach(function(a) {
    var mine = mineBy[a] || [];
    var sur = badgeSurname(a);
    var ats = mine.map(function(d){ return d.at; }).sort(function(x, y){ return x - y; });
    add({
      id: "author:" + a + ":1", group: "author", tier: 0, mark: sur.slice(0, 1),
      title: / и /.test(sur) ? ("Читатель: " + sur) : ("Читатель " + badgeGen(sur)), desc: "Finish a work by " + a,
      earned: mine.length >= 1, n: Math.min(mine.length, 1), of: 1, at: ats[0] || 0, author: a,
    });
    BADGE_AUTHOR_TIERS.forEach(function(t, i) {
      if (t > authorsAll[a]) return;
      add({
        id: "author:" + a + ":" + t, group: "author", tier: i + 1, mark: String(t),
        title: sur + ": " + t + " " + ruPlural(t, "произведение", "произведения", "произведений"),
        desc: "Finish " + t + " works by " + a,
        earned: mine.length >= t, n: Math.min(mine.length, t), of: t, at: ats[t - 1] || 0, author: a,
      });
    });
  });

  // Books of the Bible, and the collections they make up.
  var br = src.bibleRead || {};
  var ntAt = -1;
  BIBLE_BOOKS.forEach(function(b, i){ if (b[0] === BIBLE_NT_FROM) ntAt = i; });
  var bookDone = {}, doneAt = {};
  BIBLE_BOOKS.forEach(function(b) {
    var n = 0, last = 0;
    for (var c = 1; c <= b[1]; c++) {
      var t = br[b[0] + " " + c];
      if (t) { n++; if (t > last) last = t; }
    }
    bookDone[b[0]] = n >= b[1];
    doneAt[b[0]] = n >= b[1] ? last : 0;
    add({
      id: "bible:" + b[0], group: "bible", tier: 0, mark: bibleMark(b[0]),
      title: b[0], desc: "Read every chapter of «" + b[0] + "»",
      earned: n >= b[1], n: n, of: b[1], at: doneAt[b[0]],
    });
  });
  var collection = function(id, title, names, tier) {
    var n = names.filter(function(x){ return bookDone[x]; }).length;
    var at = n === names.length ? Math.max.apply(null, names.map(function(x){ return doneAt[x] || 0; })) : 0;
    add({ id: "bible:" + id, group: "bible", tier: tier, mark: title.slice(0, 1),
          title: title, desc: "Read every book: " + names.length + " in all",
          earned: n === names.length, n: n, of: names.length, at: at });
  };
  var allNames = BIBLE_BOOKS.map(function(b){ return b[0]; });
  collection("pentateuch", "Пятикнижие", allNames.slice(0, 5), 1);
  collection("gospels", "Евангелия", ["Матфея", "Марка", "Луки", "Иоанна"], 1);
  collection("ot", "Ветхий Завет", allNames.slice(0, ntAt), 3);
  collection("nt", "Новый Завет", allNames.slice(ntAt), 3);
  collection("all", "Вся Библия", allNames, 4);

  // Milestones.
  var have = {
    words: src.wordsRead || 0, streak: src.longestStreak || 0, cards: src.cardsReviewed || 0,
    learned: src.learned || 0, saved: src.saved || 0, drills: src.drills || 0, songs: src.songs || 0,
  };
  BADGE_MILESTONES.forEach(function(m) {
    m.tiers.forEach(function(t, i) {
      add({
        id: "m:" + m.id + ":" + t, group: "milestone", tier: i, mark: badgeShort(t),
        title: m.ru + ": " + badgeShort(t), desc: t.toLocaleString() + " " + m.en,
        earned: have[m.id] >= t, n: Math.min(have[m.id], t), of: t, at: 0, kind: m.id,
      });
    });
  });
  return out;
}

export { BADGE_KINDS, BADGE_STEP_TIERS, BADGE_GREAT_TIERS, BADGE_MILESTONES, BADGE_AUTHOR_TIERS, BADGE_SKIP_AUTHORS, badgeShort, badgeSurname, badgeGen, BIBLE_BOOKS, BIBLE_NT_FROM, bibleMark, computeBadges };
