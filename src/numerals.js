// Russian numerals 0–100: the words, declined in all six cases, and the form
// of the noun that goes with them. Used by the Grammar tab's two counting
// drills ("Counting objects" and "Numerals in cases").
//
// Cases are "N", "G", "D", "A", "I", "P". A noun is a row of
// public/vocab/count-nouns.json:
//   [nom.sg, gender m|f|n, animate 0|1, gen.sg, dat.sg, acc.sg, ins.sg,
//    prep.sg, gen.pl, dat.pl, ins.pl, prep.pl]   ("a|b" = either is right)

var ONES = ["", "один", "два", "три", "четыре", "пять", "шесть", "семь", "восемь", "девять"];
var TEENS = ["десять", "одиннадцать", "двенадцать", "тринадцать", "четырнадцать", "пятнадцать",
             "шестнадцать", "семнадцать", "восемнадцать", "девятнадцать"];
var TENS = ["", "", "двадцать", "тридцать", "сорок", "пятьдесят", "шестьдесят", "семьдесят", "восемьдесят", "девяносто"];
export var CASES = ["N", "G", "D", "A", "I", "P"];
export var CASE_NAME = { N: "nominative", G: "genitive", D: "dative", A: "accusative", I: "instrumental", P: "prepositional" };

var ONE = {
  m: { N: "один", G: "одного", D: "одному", I: "одним", P: "одном" },
  f: { N: "одна", G: "одной", D: "одной", A: "одну", I: "одной", P: "одной" },
  n: { N: "одно", G: "одного", D: "одному", A: "одно", I: "одним", P: "одном" },
};
var FEW = {
  "два": { G: "двух", D: "двум", I: "двумя", P: "двух" },
  "три": { G: "трёх", D: "трём", I: "тремя", P: "трёх" },
  "четыре": { G: "четырёх", D: "четырём", I: "четырьмя", P: "четырёх" },
};
var ODD = {
  "сорок": { G: "сорока", D: "сорока", I: "сорока", P: "сорока" },
  "девяносто": { G: "девяноста", D: "девяноста", I: "девяноста", P: "девяноста" },
  "сто": { G: "ста", D: "ста", I: "ста", P: "ста" },
  "ноль": { G: "нуля", D: "нулю", I: "нулём", P: "нуле" },
  "восемь": { G: "восьми", D: "восьми", I: "восемью|восьмью", P: "восьми" },
  "пятьдесят": { G: "пятидесяти", D: "пятидесяти", I: "пятьюдесятью", P: "пятидесяти" },
  "шестьдесят": { G: "шестидесяти", D: "шестидесяти", I: "шестьюдесятью", P: "шестидесяти" },
  "семьдесят": { G: "семидесяти", D: "семидесяти", I: "семьюдесятью", P: "семидесяти" },
  "восемьдесят": { G: "восьмидесяти", D: "восьмидесяти", I: "восемьюдесятью|восьмьюдесятью", P: "восьмидесяти" },
};

// The words of n in the nominative, as a list (feminine/neuter for 1 and 2).
export function numWords(n, g) {
  if (n === 0) return ["ноль"];
  if (n === 100) return ["сто"];
  var out = [];
  if (n >= 20) { out.push(TENS[Math.floor(n / 10)]); n = n % 10; if (!n) return out; }
  if (n >= 10) { out.push(TEENS[n - 10]); return out; }
  out.push(n === 1 ? ONE[g || "m"].N : n === 2 && g === "f" ? "две" : ONES[n]);
  return out;
}

function declineWord(w, c, g, anim, alone) {
  if (c === "N") return w;
  if (w === "один" || w === "одна" || w === "одно") {
    if (c === "A") return g === "m" ? (anim ? "одного" : "один") : ONE[g].A;
    return ONE[g][c];
  }
  var base = w === "две" ? "два" : w;
  if (c === "A") {
    // 2–4 standing alone take the genitive with animate nouns; at the end of
    // a compound number they keep the nominative.
    if (FEW[base] && anim && alone) return FEW[base].G;
    return w;
  }
  if (FEW[base]) return FEW[base][c];
  if (ODD[w]) return ODD[w][c];
  if (/ь$/.test(w)) return c === "I" ? w + "ю" : w.slice(0, -1) + "и";   // пять → пяти, пятью
  return w;
}

// Every accepted spelling of the number n in case c, for a noun of gender g.
export function numInCase(n, c, g, anim) {
  var ws = numWords(n, g);
  var parts = ws.map(function(w){ return declineWord(w, c, g, anim, ws.length === 1).split("|"); });
  var out = [""];
  parts.forEach(function(alts){
    var next = [];
    out.forEach(function(o){ alts.forEach(function(a){ next.push(o ? o + " " + a : a); }); });
    out = next;
  });
  return out;
}

// 1 → "one" (nominative singular); 2–4 → "few"; else "many".
export function countKind(n) {
  var t = n % 100, u = n % 10;
  if (n === 0) return "many";
  if (u === 1 && t !== 11) return "one";
  if (u >= 2 && u <= 4 && !(t >= 12 && t <= 14)) return "few";
  return "many";
}

// The noun's form(s) after the number n in case c.
export function nounForms(noun, n, c) {
  var nom = noun[0], g = noun[1], anim = !!noun[2];
  var S = { G: noun[3], D: noun[4], A: noun[5], I: noun[6], P: noun[7] };
  var Pl = { G: noun[8], D: noun[9], I: noun[10], P: noun[11] };
  var k = countKind(n), alone = numWords(n, g).length === 1;
  var f;
  if (k === "one") f = c === "N" ? nom : S[c];
  else if (c === "N" || c === "A") {
    if (k === "few") f = (c === "A" && anim && alone) ? Pl.G : noun[3];
    else f = Pl.G;
  } else f = Pl[c];
  return String(f).split("|");
}

// Every accepted answer: number in words + noun, all spellings.
export function answers(noun, n, c) {
  var nums = numInCase(n, c, noun[1], !!noun[2]);
  var ns = nounForms(noun, n, c);
  var out = [];
  nums.forEach(function(a){ ns.forEach(function(b){ out.push(a + " " + b); }); });
  return out;
}

// Why this form, in a line.
export function rule(n, c) {
  var k = countKind(n);
  if (c === "N" || c === "A") {
    if (k === "one") return "Ends in 1 (not 11): the noun is singular, in the same case as один.";
    if (k === "few") return "Ends in 2, 3, 4 (not 12–14): the noun is genitive singular" + (c === "A" ? " — but 2–4 on their own with an animate noun take the genitive plural (вижу двух студентов)." : ".");
    return "5–20, and numbers ending in 0 or 5–9: the noun is genitive plural.";
  }
  if (k === "one") return "Ends in 1 (not 11): один and the noun are both " + CASE_NAME[c] + " singular.";
  return "In the " + CASE_NAME[c] + " the number and the noun agree: both " + CASE_NAME[c] + " — the noun plural. Each part of a compound number is declined.";
}

// For the table at the top of the drill.
export var TABLE_NUMS = [[1, "m"], [1, "f"], [1, "n"], [2, "m"], [2, "f"], [3, "m"], [4, "m"], [5, "m"], [8, "m"], [11, "m"], [20, "m"], [40, "m"], [50, "m"], [90, "m"], [100, "m"]];
export function tableCell(n, g, c) {
  if (c === "A") {
    var inan = numInCase(n, "A", g, false)[0], an = numInCase(n, "A", g, true)[0];
    return inan === an ? inan : inan + " / " + an;
  }
  return numInCase(n, c, g, false).join(" / ");
}

// What the reader typed, made comparable: case, ё, punctuation, spaces.
export function normNum(s) {
  return String(s || "").toLowerCase().replace(/ё/g, "е").replace(/[.,!?;:«»"()—–-]+/g, " ").replace(/\s+/g, " ").trim();
}
