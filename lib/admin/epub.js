// Minimal EPUB reader (pure Node, no dependencies). Enough to extract the
// book's text as paragraphs so the alignment engine can compare an audiobook
// transcript against an EPUB just like it does against an FB2. Uses the ZIP
// central directory + zlib.inflateRawSync — EPUB entries are STORE (0) or
// DEFLATE (8).

import zlib from "zlib";
import { decodeEntities } from "./talign.js";

// Read all entries of a zip Buffer → { name: Buffer }.
function unzip(buf) {
  const out = {};
  // locate End Of Central Directory (0x06054b50), searching from the end
  let eocd = -1;
  for (let i = buf.length - 22; i >= 0 && i >= buf.length - 22 - 65536; i--) {
    if (buf.readUInt32LE(i) === 0x06054b50) { eocd = i; break; }
  }
  if (eocd < 0) throw new Error("not a zip / EOCD not found");
  const total = buf.readUInt16LE(eocd + 10);
  let p = buf.readUInt32LE(eocd + 16); // central directory offset
  for (let n = 0; n < total; n++) {
    if (buf.readUInt32LE(p) !== 0x02014b50) break;
    const method = buf.readUInt16LE(p + 10);
    const compSize = buf.readUInt32LE(p + 20);
    const nameLen = buf.readUInt16LE(p + 28);
    const extraLen = buf.readUInt16LE(p + 30);
    const commentLen = buf.readUInt16LE(p + 32);
    const localOff = buf.readUInt32LE(p + 42);
    const name = buf.slice(p + 46, p + 46 + nameLen).toString("utf-8");
    // read local header to find where the data actually starts
    const lNameLen = buf.readUInt16LE(localOff + 26);
    const lExtraLen = buf.readUInt16LE(localOff + 28);
    const dataStart = localOff + 30 + lNameLen + lExtraLen;
    const comp = buf.slice(dataStart, dataStart + compSize);
    let data;
    try { data = method === 8 ? zlib.inflateRawSync(comp) : comp; }
    catch (e) { data = Buffer.alloc(0); }
    out[name] = data;
    p += 46 + nameLen + extraLen + commentLen;
  }
  return out;
}

function xmlText(s) { return decodeEntities(String(s).replace(/<[^>]+>/g, " ")).replace(/\s+/g, " ").trim(); }

// Extract paragraphs from one XHTML string.
function xhtmlParas(xhtml) {
  // strip head; work on body if present
  let body = xhtml;
  const bm = xhtml.match(/<body\b[^>]*>([\s\S]*?)<\/body>/i);
  if (bm) body = bm[1];
  const paras = [];
  const re = /<(p|h[1-6]|div|li|blockquote)\b[^>]*>([\s\S]*?)<\/\1>/gi;
  let m;
  while ((m = re.exec(body))) {
    const kind = /^h[1-6]$/i.test(m[1]) ? "title" : "p";
    const t = xmlText(m[2]);
    if (t) paras.push({ text: t, kind: kind });
  }
  // fallback: if no block elements matched, split on <br> / double newlines
  if (!paras.length) {
    const flat = xmlText(body);
    if (flat) flat.split(/\n{2,}/).forEach(function (t) { if (t.trim()) paras.push({ text: t.trim(), kind: "p" }); });
  }
  return paras;
}

// Parse an EPUB Buffer → { paras: [{text, kind}] } (spine reading order).
function parseEpub(buf) {
  const files = unzip(buf);
  // find the OPF via META-INF/container.xml
  const container = files["META-INF/container.xml"];
  let opfPath = null;
  if (container) {
    const cm = container.toString("utf-8").match(/full-path=["']([^"']+)["']/);
    if (cm) opfPath = cm[1];
  }
  if (!opfPath) { // fallback: first .opf
    opfPath = Object.keys(files).find(function (k) { return /\.opf$/i.test(k); });
  }
  if (!opfPath || !files[opfPath]) throw new Error("EPUB: no OPF package found");
  const opf = files[opfPath].toString("utf-8");
  const baseDir = opfPath.indexOf("/") >= 0 ? opfPath.slice(0, opfPath.lastIndexOf("/") + 1) : "";

  // manifest: id -> href
  const manifest = {};
  const mre = /<item\b[^>]*\bid=["']([^"']+)["'][^>]*\bhref=["']([^"']+)["'][^>]*>/gi;
  let mm;
  while ((mm = mre.exec(opf))) manifest[mm[1]] = mm[2];
  // also handle href-before-id ordering
  const mre2 = /<item\b[^>]*\bhref=["']([^"']+)["'][^>]*\bid=["']([^"']+)["'][^>]*>/gi;
  while ((mm = mre2.exec(opf))) { if (!manifest[mm[2]]) manifest[mm[2]] = mm[1]; }

  // spine: ordered idrefs
  const spine = [];
  const sre = /<itemref\b[^>]*\bidref=["']([^"']+)["'][^>]*>/gi;
  let sm;
  while ((sm = sre.exec(opf))) if (manifest[sm[1]]) spine.push(manifest[sm[1]]);

  // fallback: any xhtml/html files in reading-ish order
  let hrefs = spine.length ? spine : Object.keys(files).filter(function (k) { return /\.x?html?$/i.test(k) && !/nav\.x?html?$/i.test(k); }).sort();

  const paras = [];
  hrefs.forEach(function (href) {
    const key = (baseDir + href).replace(/^\.\//, "");
    const f = files[key] || files[href];
    if (!f) return;
    xhtmlParas(f.toString("utf-8")).forEach(function (p) { paras.push(p); });
  });
  return { paras: paras, bodyStart: 0, bodyEnd: 0 };
}

export { parseEpub, unzip };
