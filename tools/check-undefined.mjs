#!/usr/bin/env node
// Catch a reference to something that does not exist, before Vercel ships it.
//
// This exists because two bugs of exactly this shape reached the live site in
// one afternoon: a helper deleted by an edit that rewrote the block around it
// (`readingsInContext`), and a module-level helper silently shadowed by a
// same-named one inside the component (`playText`). Neither is a syntax error,
// so `node --check` and the build both pass and the failure only appears when a
// reader taps a word.
//
//   node tools/check-undefined.mjs                 # every source file
//   node tools/check-undefined.mjs src/App.jsx     # just one
//
// Exits non-zero if anything is unresolved, so it can go in a pre-push hook.
import fs from "node:fs";
import path from "node:path";
import { parse } from "@babel/parser";
import _traverse from "@babel/traverse";
const traverse = _traverse.default || _traverse;

// Standard JavaScript, which every environment has.
const BUILTINS = new Set([
  "Object","Array","String","Number","Boolean","Symbol","BigInt","Math","JSON","Date",
  "RegExp","Error","TypeError","RangeError","SyntaxError","Map","Set","WeakMap","WeakSet",
  "Promise","Proxy","Reflect","Intl","Function","undefined","NaN","Infinity","globalThis",
  "parseInt","parseFloat","isNaN","isFinite","encodeURIComponent","decodeURIComponent",
  "encodeURI","decodeURI","ArrayBuffer","Uint8Array","Int8Array","Float64Array","DataView",
  "arguments","eval",
]);

const BROWSER = new Set([
  "window","document","navigator","console","fetch","localStorage","sessionStorage",
  "setTimeout","clearTimeout","setInterval","clearInterval","requestAnimationFrame",
  "cancelAnimationFrame","alert","confirm","prompt","location","history","URL",
  "URLSearchParams","FormData","Blob","File","FileReader","Image","Audio","Event",
  "CustomEvent","IntersectionObserver","MutationObserver","ResizeObserver","DOMParser",
  "XMLHttpRequest","AbortController","TextDecoder","TextEncoder","atob","btoa",
  "structuredClone","speechSynthesis","SpeechSynthesisUtterance","crypto","YT",
  "getComputedStyle","matchMedia","scrollTo","indexedDB","performance","caches",
  "DecompressionStream","CompressionStream","ReadableStream","WritableStream","Response",
  "Request","Headers","AbortSignal","MediaSource","Notification","__BUILD_ID__",
  "process","Buffer","globalThis","__SITE_MODE__","module","require","exports","__dirname",
]);

function check(file) {
  const src = fs.readFileSync(file, "utf8");
  let ast;
  try {
    ast = parse(src, { sourceType: "module", plugins: ["jsx"], errorRecovery: false });
  } catch (e) {
    console.log(`${file}: PARSE ERROR ${e.message}`);
    return 1;
  }
  const bad = [];
  traverse(ast, {
    ReferencedIdentifier(p) {
      const name = p.node.name;
      if (BUILTINS.has(name) || BROWSER.has(name)) return;
      if (p.scope.hasBinding(name, true)) return;
      if (/^[A-Z][A-Za-z0-9_]*$/.test(name) && p.scope.hasGlobal(name)) { /* fall through */ }
      bad.push({ name, line: p.node.loc && p.node.loc.start.line });
    },
  });
  // One line per name, with every place it is used.
  const byName = new Map();
  for (const b of bad) {
    if (!byName.has(b.name)) byName.set(b.name, []);
    byName.get(b.name).push(b.line);
  }
  if (!byName.size) { console.log(`${file}: ok`); return 0; }
  for (const [name, lines] of [...byName].sort()) {
    console.log(`${file}:${lines[0]}  ${name} is used but never defined` +
                (lines.length > 1 ? ` (also line${lines.length > 2 ? "s" : ""} ${lines.slice(1).join(", ")})` : ""));
  }
  return byName.size;
}

const args = process.argv.slice(2);
const files = args.length ? args : [
  ...fs.readdirSync("src").filter(f => /\.jsx?$/.test(f) && !f.includes(".bak")).map(f => path.join("src", f)),
  ...fs.readdirSync("lib").filter(f => /\.js$/.test(f) && !f.includes(".bak")).map(f => path.join("lib", f)),
  ...fs.readdirSync("api").filter(f => /\.js$/.test(f) && !f.includes(".bak")).map(f => path.join("api", f)),
];
let bad = 0;
for (const f of files) bad += check(f);
if (bad) { console.log(`\n${bad} unresolved reference${bad === 1 ? "" : "s"}.`); process.exit(1); }
console.log("\nNothing unresolved.");
