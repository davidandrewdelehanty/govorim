import { useState, useRef, useEffect, useCallback } from "react";
import { SignedIn, SignedOut, SignIn, UserButton, useAuth } from "@clerk/clerk-react";

// localStorage-backed storage shim, matching the previous window.storage Promise API.
// Keeps the rest of the app code unchanged (still uses await storage.get/set/delete).
var storage = {
  get: function(key) {
    return Promise.resolve().then(function() {
      var v = localStorage.getItem(key);
      return v === null ? null : { value: v };
    });
  },
  set: function(key, value) {
    return Promise.resolve().then(function() {
      localStorage.setItem(key, value);
      return { value: value };
    });
  },
  delete: function(key) {
    return Promise.resolve().then(function() {
      localStorage.removeItem(key);
    });
  }
};

const TOPICS = [
  "Get to know each other",
  "The Golden Age of Russian Literature: Russian Authors",
  "Contemporary Russian Music",
  "Russian History", "Russian Culture", "Russian Food",
  "The Book of Genesis: Синодальный Перевод",
  "Synonyms you should know", "Antonyms you should know",
  "False Cognates", "Verb Workout", "Grammar Jamboree",
];

// Generic EPUB cache slots — one book at a time. Loading a new EPUB replaces these.
var EPUB_CACHE = "epub_data_v1";
var EPUB_BM    = "epub_bm_v1";
// Per-chapter question history (so we can ask different questions each visit).
var QHIST_KEY  = "epub_qhist_v1";

// Different angles a session can take, so visiting the same chapter twice
// asks about different aspects of the passage rather than repeating itself.
var QUESTION_FOCI = [
  { tag: "characters", note: "FOCUS THIS SESSION: questions about specific characters — what they did, said, thought, felt." },
  { tag: "setting",    note: "FOCUS THIS SESSION: questions about the physical setting — locations, rooms, objects, time of day, weather." },
  { tag: "actions",    note: "FOCUS THIS SESSION: questions about specific actions and the order in which they happened." },
  { tag: "appearance", note: "FOCUS THIS SESSION: questions about physical descriptions — what people, places, or objects looked like." },
  { tag: "dialogue",   note: "FOCUS THIS SESSION: questions about what was said — who spoke and what they communicated, including direct quotes." },
  { tag: "emotion",    note: "FOCUS THIS SESSION: questions about emotional states explicitly named or shown in the text." },
  { tag: "causes",     note: "FOCUS THIS SESSION: questions about stated causes and reasons — why things happened, why characters chose what they chose." },
  { tag: "quantities", note: "FOCUS THIS SESSION: questions about numbers, amounts, durations, distances, ages mentioned in the text." },
  { tag: "relations",  note: "FOCUS THIS SESSION: questions about relationships between characters or between characters and objects/places." },
];

function sysprompt(topic, vocab, tips) {
  return `You are a warm, curious Russian language tutor. Topic: "${topic}".

For each turn:
1. Share ONE genuinely interesting fact, perspective, or short anecdote about the topic in Russian (1–2 sentences). Make it specific and surprising, not generic.
2. Then ask a probing follow-up question that pulls the student into responding in Russian. The question should require more than да/нет — push them to use cases, verb aspect, or tense to express something concrete.

CONVERSATION CONTINUITY (very important):
- Treat your OWN previous message as content the student should comprehend. Before introducing anything new, your next question should probe whether they understood what you just shared (e.g. "Что тебя удивило в этом?", "Как ты думаешь, почему так случилось?", "Помнишь, в каком году это было?").
- Build threads, don't dump disconnected facts. If you must move to a new aspect of the topic, bridge it explicitly — reference what was just discussed and connect the new content to it ("Кстати, как и X, который мы только что обсудили, Y тоже…").
- If the student's answer reveals confusion or a misunderstanding, re-explain with a different angle before moving on. Don't drop the thread.

Style rules:
- Speak intermediate-level Russian only — do NOT add English translations of your Russian sentences.
- Correct student mistakes inline using [correct form], but only for grammar — never withhold acknowledgement of a correct comprehension answer because of a small grammar slip.
- Bold key vocab the student should learn as **слово (word)** — the parenthetical gloss is fine; that's a single-word lookup, not a translation.
- Occasionally add 📝 TIP: [grammar rule] when something useful comes up.
- Keep messages to 2–4 Russian sentences. Be warm and encouraging.

GENEROUS ACCEPTANCE (very important):
You are a language tutor, NOT a fact-checker. Accept the student's answers liberally — synonyms, paraphrases, partial answers that capture the gist, and answers in different grammatical forms are all CORRECT. The student is intermediate, not native; if they understood the meaning, that's the goal. Affirm clearly first ("Да, точно!", "Молодец!"), THEN optionally enrich with a more specific word or correction. Only treat something as wrong if it's clearly off-topic.
${vocab.length ? "\nWeave these saved vocabulary words naturally into your messages so the student sees them again in context: " + vocab.map(function(v){ return v.ru; }).join(", ") : ""}`;
}

function litprompt(snippet, idx, total, title, author, focus, prevQuestions) {
  var focusBlock = focus ? `\n${focus.note}\n` : "";
  var prevBlock = (prevQuestions && prevQuestions.length)
    ? "\nQUESTIONS YOU ALREADY ASKED IN PREVIOUS SESSIONS — do NOT repeat any of these. Pick different details from the passage:\n"
      + prevQuestions.map(function(q){ return "- " + q; }).join("\n") + "\n"
    : "";
  return `You are a Russian comprehension tutor working with an INTERMEDIATE student (roughly B1 — NOT a native speaker). The student just read this passage from "${title}" by ${author} (chapter ${idx+1}/${total}):

PASSAGE:
"${snippet}"

Your job: ask 2–3 SPECIFIC comprehension questions IN RUSSIAN that the student can answer using info from the passage.
${focusBlock}${prevBlock}
WHAT MAKES A GOOD QUESTION (read carefully):

1. ANSWER VERIFIABILITY CHECK — before writing each question, locate the exact phrase or sentence in the passage that contains the answer. If you cannot point to a specific phrase that explicitly answers it, do NOT ask the question. Drop it and pick a different detail.

2. The answer must NOT require:
   - Inferring meaning from cultural / historical context the student may not have
   - Interpreting metaphor, irony, or subtext
   - Knowledge of 19th-century Russian society, customs, ranks, currencies, etc., unless the passage explains them
   - Reading between the lines — the answer must be on the surface of the text

3. INTERMEDIATE-LEVEL LANGUAGE in the question itself:
   - Use common, modern Russian vocabulary (B1 register).
   - Use clear, simple syntax — no long subordinate clauses.
   - If the passage uses an archaic, dialectal, or unusually literary word that's relevant to the answer, PARAPHRASE it in your question using a modern equivalent — do not quote the archaic form back at the student.
   - Don't use uncommon participles or adverbial participles (деепричастия) in your question.

4. Each question targets a specific concrete detail: color, location, name, time, action, reason, manner, quantity, who-did-what-to-whom.

5. Vary the grammar so the student exercises different cases and forms across the questions:
   • Какого цвета…? (genitive)
   • Где…? Откуда…? (prepositional / genitive)
   • Куда…? (accusative of direction)
   • Кто…? Кого…? Кому…? Чем…? (nom/acc/dat/instr)
   • Когда…? Сколько…? Почему…? Что сделал…?

INTERNAL SELF-CHECK before sending each question (do this silently):
  (a) Where in the passage is the answer? Quote the relevant phrase to yourself.
  (b) Could a B1 learner produce the answer in 1–2 sentences using only the passage and a basic dictionary? If no — rewrite or drop.
  (c) Does my question use any words the student would have to look up just to understand the question? If yes — paraphrase.

Format your response as:
1. ONE short English note (max 1 sentence) about a notable grammar feature in the passage.
2. Then the questions, numbered, in Russian only — do NOT add English translations of your questions:
   ❓1 [Russian question]
   ❓2 [Russian question]
   (etc.)

Do NOT answer the questions yourself — the student will.

CONVERSATION CONTINUITY (very important):
- After the student answers, ALWAYS treat their previous answer (and the question that prompted it) as the anchor for your next message. Before moving to a new question, probe the SAME detail one level deeper: ask why, ask for a contrast, ask them to imagine an alternative. Example: if they answered "дом был белый", follow up with "А почему именно белый, как ты думаешь?" or "Что ещё в этой сцене было светлым?".
- When transitioning to a new question, bridge from their previous answer explicitly — reference what they said and connect the new question to it ("Хорошо, ты сказал что X. А теперь — …").
- If they get a question wrong or only partially right, re-ask in a simpler way using different vocabulary; don't just move on.
- Never abandon a thread mid-air. The student should always feel that each question follows naturally from what was just said.
- Apply the SAME intermediate-level rule to follow-up questions: paraphrase archaic words, keep syntax simple, only ask things answerable from the passage (or from the student's previous answer).

When the student responds:
- Briefly validate or correct mistakes inline with [correct form].
- Bold any teachable vocab as **слово (word)**.
- Then either probe the same detail deeper OR bridge clearly to the next question (per the continuity rules above).
- Stay concise.

GENEROUS ANSWER ACCEPTANCE (very important — read this carefully):

You are a language tutor, NOT a fact-checker. The student is intermediate, not native. ACCEPT answers liberally:

- ✅ Accept SYNONYMS and category equivalents. If the text says "ржавый" (rust-colored) and the student says "brown", "red", "reddish", "rusty", "orange", "коричневый", "красноватый", "оранжевый" — that is CORRECT. Don't demand the exact word from the text. The student understood the color family; that's the comprehension goal.
- ✅ Accept PARTIAL answers that capture the essential meaning. If the text says "old wooden house" and the student says "wooden" or "old", accept it.
- ✅ Accept PARAPHRASES. The student doesn't have to echo the text verbatim.
- ✅ Accept answers in any grammatical form as long as the meaning is right. Wrong case ending while content is right? Acknowledge correct content first, fix grammar inline with [correct form].
- ✅ Accept answers in English if the student is reaching for a Russian word they don't know yet — affirm the comprehension, then supply the Russian equivalent.

Only mark wrong if the answer is CLEARLY off-topic (e.g. "blue" for a rust-colored object, naming the wrong character or place, contradicting the text).

When you accept an answer:
1. AFFIRM clearly first — "Да, точно!", "Совершенно верно!", "Молодец!", "Правильно!".
2. THEN you can enrich: mention the specific Russian word the text used as bonus information, not as a correction. Format: "Точно — в тексте Чехов использует слово **ржавый (rusty)**, что значит коричневато-красноватый цвет, как ты и сказал."
3. Then probe deeper or bridge to the next question.

When the student is genuinely wrong on the comprehension itself: gently re-ask the question using different words and a simpler hint, NOT "no, the answer is X." Give them a second chance.`;
}

function defprompt(w) {
  return `Define the Russian word "${w}" for an English learner. Return JSON ONLY, no markdown.

Required fields:
{
  "word": "${w}",
  "lemma": "<dictionary form: NOMINATIVE singular for nouns, INFINITIVE for verbs, masculine singular for adjectives>",
  "aspectPair": "<verbs ONLY: the aspectual partner infinitive if it is a clear, commonly-paired pair; empty string otherwise>",
  "aspect": "<verbs ONLY: 'imperfective' or 'perfective'; empty string otherwise>",
  "partOfSpeech": "<noun, verb, adjective, adverb, pronoun, preposition, conjunction, particle, etc.>",
  "translation": "<English translation; for verbs use 'to ...'>",
  "grammar": "<brief note: gender for nouns, conjugation/aspect for verbs, etc.>",
  "example": "<short Russian example sentence>",
  "exampleTranslation": "<English translation of the example>"
}

Rules for aspectPair:
- Fill it ONLY when the verb has a CLEAR, commonly-paired aspectual partner (e.g. писать↔написать, говорить↔сказать, делать↔сделать, читать↔прочитать, давать↔дать).
- Leave it empty for: motion verbs with multiple stems (ходить, идти, ездить), biaspectual verbs, defective verbs (быть), verbs whose pair is not standardly listed in dictionaries.
- aspectPair must be the infinitive form, not conjugated.

Rules for lemma:
- Always the canonical dictionary form, even if "${w}" is inflected. So if "${w}" is "столе" (prepositional), lemma is "стол". If "${w}" is "пишу" (1sg present), lemma is "писать".`;
}


function tokenise(text) {
  return (text || "").match(/[а-яёА-ЯЁ]+|[^а-яёА-ЯЁ]+/g) || [];
}

function yoVariants(word) {
  var out = [];
  for (var i = 0; i < word.length; i++) {
    if (word[i] === "е") out.push(word.slice(0,i) + "ё" + word.slice(i+1));
    else if (word[i] === "Е") out.push(word.slice(0,i) + "Ё" + word.slice(i+1));
  }
  return out;
}

// ── EPUB PARSER ──────────────────────────────────────────────────────────────

function readUint32LE(buf, off) {
  return (buf[off] | buf[off+1]<<8 | buf[off+2]<<16 | buf[off+3]<<24) >>> 0;
}
function readUint16LE(buf, off) {
  return (buf[off] | buf[off+1]<<8) >>> 0;
}

function parseZip(buffer) {
  var bytes = new Uint8Array(buffer);
  var files = {};

  // Find End of Central Directory record (signature: PK\x05\x06)
  var eocd = -1;
  var maxScan = Math.max(0, bytes.length - 65557);
  for (var i = bytes.length - 22; i >= maxScan; i--) {
    if (bytes[i]===0x50 && bytes[i+1]===0x4B && bytes[i+2]===0x05 && bytes[i+3]===0x06) {
      eocd = i; break;
    }
  }
  if (eocd === -1) throw new Error("Invalid ZIP: End of Central Directory not found");

  var cdSize   = readUint32LE(bytes, eocd + 12);
  var cdOffset = readUint32LE(bytes, eocd + 16);

  // Walk central directory entries (signature: PK\x01\x02)
  var pos = cdOffset;
  var end = cdOffset + cdSize;
  while (pos < end - 4) {
    if (bytes[pos]!==0x50 || bytes[pos+1]!==0x4B || bytes[pos+2]!==0x01 || bytes[pos+3]!==0x02) break;

    var comp        = readUint16LE(bytes, pos + 10);
    var csize       = readUint32LE(bytes, pos + 20);
    var fnlen       = readUint16LE(bytes, pos + 28);
    var exlen       = readUint16LE(bytes, pos + 30);
    var cmtlen      = readUint16LE(bytes, pos + 32);
    var localOff    = readUint32LE(bytes, pos + 42);
    var fname       = new TextDecoder().decode(bytes.slice(pos + 46, pos + 46 + fnlen));

    // Jump to the local header to find the actual data start
    // (local header has its own filename and extra-field lengths that may differ)
    if (localOff + 30 < bytes.length) {
      var lfnlen    = readUint16LE(bytes, localOff + 26);
      var lexlen    = readUint16LE(bytes, localOff + 28);
      var dataStart = localOff + 30 + lfnlen + lexlen;
      var data      = bytes.slice(dataStart, dataStart + csize);

      if (comp === 0) {
        files[fname] = new TextDecoder("utf-8").decode(data);
      } else if (comp === 8) {
        try {
          var ds = new DecompressionStream("deflate-raw");
          var writer = ds.writable.getWriter();
          writer.write(data); writer.close();
          files[fname] = { stream: ds.readable, name: fname };
        } catch(ex) {}
      }
    }

    pos += 46 + fnlen + exlen + cmtlen;
  }
  return files;
}

async function decompressEntry(entry) {
  if (typeof entry === "string") return entry;
  if (entry && entry.stream) {
    var reader = entry.stream.getReader();
    var chunks = [];
    while (true) {
      var r = await reader.read();
      if (r.done) break;
      chunks.push(r.value);
    }
    var total = chunks.reduce(function(a,c){ return a+c.length; }, 0);
    var out = new Uint8Array(total); var pos = 0;
    for (var ci = 0; ci < chunks.length; ci++) { out.set(chunks[ci], pos); pos += chunks[ci].length; }
    return new TextDecoder("utf-8").decode(out);
  }
  return "";
}

function htmlToText(html) {
  var parser = new DOMParser();
  var doc = parser.parseFromString(html, "text/html");
  var result = [];
  var blockTags = {"P":1,"DIV":1,"H1":1,"H2":1,"H3":1,"H4":1,"H5":1,"H6":1,"LI":1,"BR":1,"TR":1};
  function walk(node) {
    if (node.nodeType === 3) {
      var t = node.textContent.replace(/\s+/g," ");
      if (t.trim()) result.push(t);
    } else if (node.nodeType === 1) {
      var tag = node.tagName.toUpperCase();
      if (tag === "SCRIPT" || tag === "STYLE") return;
      if (blockTags[tag]) result.push("\n\n");
      for (var ci = 0; ci < node.childNodes.length; ci++) walk(node.childNodes[ci]);
      if (blockTags[tag]) result.push("\n\n");
    }
  }
  walk(doc.body || doc.documentElement);
  return result.join("").replace(/\n{3,}/g,"\n\n").replace(/ {2,}/g," ").trim();
}

function isFrontMatter(heading, text) {
  var h = (heading || "").toLowerCase().trim();
  var t = (text || "").slice(0, 200).toLowerCase().trim();
  // Publisher metadata / non-content sections to skip.
  // Authorial content like prefaces, dedications, epigraphs are kept intentionally.
  var skip = [
    /^аннотация\b/, /^оглавление\b/, /^содержание\b/,
    /^обложка\b/, /^титульн/, /^выходные данные\b/,
    /^cover\b/, /^title page\b/, /^contents\b/, /^table of contents\b/,
    /^copyright\b/, /^annotation\b/, /^colophon\b/, /^about the (author|book)\b/,
    /^acknowledg(e?)ments\b/, /^издательств/
  ];
  return skip.some(function(p) { return p.test(h) || p.test(t); });
}

async function parseEpub(buffer) {
  var zipFiles = parseZip(buffer);

  var containerXml = zipFiles["META-INF/container.xml"];
  if (!containerXml) throw new Error("Not a valid EPUB — no container.xml");
  if (typeof containerXml !== "string") containerXml = await decompressEntry(containerXml);

  var opfMatch = containerXml.match(/full-path="([^"]+\.opf)"/i);
  if (!opfMatch) throw new Error("Could not find OPF file in EPUB");
  var opfPath = opfMatch[1];
  var opfDir  = opfPath.includes("/") ? opfPath.slice(0, opfPath.lastIndexOf("/")+1) : "";

  var opfRaw = zipFiles[opfPath];
  if (!opfRaw) throw new Error("OPF file not found: " + opfPath);
  if (typeof opfRaw !== "string") opfRaw = await decompressEntry(opfRaw);

  var manifestItems = {};
  var itemRe = /<item\b([^>]+)>/gi;
  var mm;
  while ((mm = itemRe.exec(opfRaw)) !== null) {
    var attrs = mm[1];
    var idM   = attrs.match(/\bid\s*=\s*["']([^"']+)["']/i);
    var hrefM = attrs.match(/\bhref\s*=\s*["']([^"']+)["']/i);
    if (idM && hrefM) manifestItems[idM[1]] = hrefM[1];
  }

  var spineIds = [];
  var itemrefRe = /<itemref\b([^>]+)>/gi;
  var sm;
  while ((sm = itemrefRe.exec(opfRaw)) !== null) {
    var idrefM = sm[1].match(/\bidref\s*=\s*["']([^"']+)["']/i);
    if (idrefM) spineIds.push(idrefM[1]);
  }

  if (spineIds.length === 0) throw new Error("No spine items found in EPUB");

  var chapters = [];
  for (var k = 0; k < spineIds.length; k++) {
    var id   = spineIds[k];
    var href = manifestItems[id];
    if (!href) continue;
    var clean = href.split("#")[0];
    try { clean = decodeURIComponent(clean); } catch(e) {}
    var fullPath = opfDir + clean;
    var fileData = zipFiles[fullPath] || zipFiles[clean] || zipFiles[href.split("#")[0]];
    if (!fileData) continue;
    var html = typeof fileData === "string" ? fileData : await decompressEntry(fileData);
    var text = htmlToText(html);
    var cyrCount = (text.match(/[а-яёА-ЯЁ]/g) || []).length;
    if (cyrCount < 20) continue;

    var headMatch = html.match(/<h[1-3][^>]*>([^<]*)<\/h[1-3]>/i);
    var heading = headMatch ? headMatch[1].trim() : ("Глава " + (chapters.length+1));
    if (isFrontMatter(heading, text)) continue;
    chapters.push({ heading: heading, text: text });
  }

  if (chapters.length === 0) {
    // Fallback: scan ALL HTML/XHTML files in the zip, not just spine
    var keys = Object.keys(zipFiles);
    for (var ki = 0; ki < keys.length; ki++) {
      var fname = keys[ki];
      if (!/\.(x?html?)$/i.test(fname)) continue;
      var fd = zipFiles[fname];
      var ht = typeof fd === "string" ? fd : await decompressEntry(fd);
      var tx = htmlToText(ht);
      var cy = (tx.match(/[а-яёА-ЯЁ]/g) || []).length;
      if (cy < 20) continue;
      var hm = ht.match(/<h[1-3][^>]*>([^<]*)<\/h[1-3]>/i);
      var hd = hm ? hm[1].trim() : ("Глава " + (chapters.length+1));
      if (isFrontMatter(hd, tx)) continue;
      chapters.push({ heading: hd, text: tx });
    }
  }

  if (chapters.length === 0) throw new Error("No Russian text found in EPUB. Check it's the right file.");

  // Extract title/author from OPF metadata
  var titleM  = opfRaw.match(/<dc:title[^>]*>([^<]+)<\/dc:title>/i);
  var authorM = opfRaw.match(/<dc:creator[^>]*>([^<]+)<\/dc:creator>/i);
  var title   = titleM  ? titleM[1].trim()  : "Unknown title";
  var author  = authorM ? authorM[1].trim() : "Unknown author";

  return { chapters: chapters, title: title, author: author };
}

function FileBtn({ label, onLoad }) {
  var ref = useRef(null);
  var [busy, setBusy] = useState(false);
  var [err, setErr] = useState("");
  var go = async function(e) {
    var f = e.target.files && e.target.files[0];
    if (!f) return;
    setBusy(true); setErr("");
    try {
      var buf = await f.arrayBuffer();
      if (buf.byteLength < 100) throw new Error("File too small");
      onLoad(buf, f.name);
    } catch(ex) { setErr(ex.message); }
    setBusy(false); e.target.value = "";
  };
  return (
    <div style={{display:"flex",flexDirection:"column",gap:6,width:"100%"}}>
      <input ref={ref} type="file" accept=".epub" style={{display:"none"}} onChange={go}/>
      <button className="btn-p" onClick={function(){ ref.current && ref.current.click(); }} disabled={busy}>
        {busy ? "Loading…" : "📂 " + label}
      </button>
      {err && <p style={{color:"#c87a68",fontSize:13}}>{err}</p>}
    </div>
  );
}

export default function App() {
  // Clerk auth — getToken() returns a JWT we attach to API calls so the
  // backend can verify the user is signed in.
  var auth = useAuth();
  var [msgs, setMsgs]         = useState([]);
  var [input, setInput]       = useState("");
  var [loading, setLoading]   = useState(false);
  var [topic, setTopic]       = useState(TOPICS[0]);
  var [custom, setCustom]     = useState("");
  var [vocab, setVocab]       = useState([]);
  var [tips, setTips]         = useState([]);
  var [tab, setTab]           = useState("chat");
  var [started, setStarted]   = useState(false);
  var [mode, setMode]         = useState("");      // "" until user picks "chat" or "read"
  var [bookMeta, setBookMeta] = useState({title:"", author:""});

  var [showTopic, setShowTopic] = useState(false);
  var [showWord,  setShowWord]  = useState(false);
  var [showTip,   setShowTip]   = useState(false);
  var [nRu, setNRu] = useState("");
  var [nEn, setNEn] = useState("");
  var [nTip, setNTip] = useState("");

  var [popup, setPopup]   = useState(null);
  var [popXY, setPopXY]   = useState({top:100,left:16});
  var popRef = useRef(null);

  // First-visit landing screen: remembered in localStorage so users only see it once per device.
  var [seenLanding, setSeenLanding] = useState(function() {
    try { return localStorage.getItem("landing_seen_v1") === "1"; } catch(e) { return false; }
  });
  var dismissLanding = function() {
    try { localStorage.setItem("landing_seen_v1", "1"); } catch(e) {}
    setSeenLanding(true);
  };

  var [chapters, setChapters]   = useState([]);
  var [cidx, setCidx]           = useState(0);
  var [cbm,  setCbm]            = useState(0);
  var [lview, setLview]         = useState("read");
  var [lsearch, setLsearch]     = useState("");
  var [lres, setLres]           = useState([]);
  var [fErr, setFErr]           = useState("");

  var [voice, setVoice]         = useState(null);
  var [allVoices, setAllVoices] = useState([]);
  var [playing, setPlaying]     = useState(false);
  var [showVP, setShowVP]       = useState(false);
  var [spkIdx, setSpkIdx]       = useState(null);
  var [ttsErr, setTtsErr]       = useState("");
  var [diagLogs, setDiagLogs]   = useState([]);
  var [spokenChar, setSpokenChar] = useState(-1);
  var charPos  = useRef(0);
  var paraText = useRef("");
  var keepAlive = useRef(null);
  var recentFoci = useRef([]);

  var inputRef = useRef(null);
  var msgsRef = useRef(null);

  var act  = custom.trim() || topic;
  var isLit = mode === "read";
  var pct  = chapters.length > 0 ? Math.round((cidx / chapters.length) * 100) : 0;
  var curChapter = chapters[cidx] || { heading: "", text: "" };

  useEffect(function() {
    (async function() {
      try { var v = await storage.get("vocab"); var g = await storage.get("grammar");
        if (v) setVocab(JSON.parse(v.value)); if (g) setTips(JSON.parse(g.value)); } catch(e) {}
    })();
  }, []);
  useEffect(function() { storage && storage.set("vocab", JSON.stringify(vocab)).catch(function(){}); }, [vocab]);
  useEffect(function() { storage && storage.set("grammar", JSON.stringify(tips)).catch(function(){}); }, [tips]);

  useEffect(function() {
    var h = function(e) { if (popRef.current && !popRef.current.contains(e.target)) setPopup(null); };
    document.addEventListener("mousedown", h);
    return function() { document.removeEventListener("mousedown", h); };
  }, []);

  useEffect(function() {
    var find = function() {
      var all = window.speechSynthesis.getVoices();
      if (!all.length) return false;
      setAllVoices(all);
      // Priority order:
      //   1. Local voices (work everywhere, predictable)
      //   2. Microsoft Edge "Online (Natural)" neural voices (high quality, work reliably in Edge)
      //   3. Other network voices as a last resort
      var isMsNatural = function(v) {
        return /microsoft.*online.*natural/i.test(v.name) || /\(natural\)/i.test(v.name);
      };
      var v =
           all.find(function(v) { return /katya|katja/i.test(v.name) && v.localService; })
        || all.find(function(v) { return v.lang === "ru-RU" && v.localService; })
        || all.find(function(v) { return v.lang.startsWith("ru") && v.localService; })
        // Microsoft Edge online neural voices — high quality, reliable in Edge
        || all.find(function(v) { return v.lang === "ru-RU" && isMsNatural(v); })
        || all.find(function(v) { return v.lang.startsWith("ru") && isMsNatural(v); })
        // Other non-Google network voices
        || all.find(function(v) { return v.lang === "ru-RU" && !/google/i.test(v.name); })
        || all.find(function(v) { return /katya|katja/i.test(v.name); })
        || all.find(function(v) { return v.lang === "ru-RU"; })
        || all.find(function(v) { return v.lang.startsWith("ru"); });
      if (v) setVoice(v);
      return true;
    };
    if (!find()) window.speechSynthesis.onvoiceschanged = find;
  }, []);

  // Load any cached EPUB (single-slot) when user enters Read mode for the first time.
  useEffect(function() {
    if (mode !== "read") return;
    (async function() {
      try { var b = await storage.get(EPUB_BM); if (b) setCbm(parseInt(b.value) || 0); } catch(e) {}
      try {
        var c = await storage.get(EPUB_CACHE);
        if (c && c.value) {
          var d = JSON.parse(c.value);
          if (d && d.chapters && d.chapters.length > 0) {
            setChapters(d.chapters);
            setBookMeta({ title: d.title || "Unknown title", author: d.author || "Unknown author" });
          }
        }
      } catch(e) {}
    })();
  }, [mode]);

  // Persist bookmark whenever it changes (only meaningful with a loaded book).
  useEffect(function() {
    if (chapters.length > 0) storage && storage.set(EPUB_BM, String(cbm)).catch(function(){});
  }, [cbm]);

  useEffect(function() {
    if (!lsearch.trim() || !chapters.length) { setLres([]); return; }
    var q = lsearch.toLowerCase();
    var r = [];
    for (var i = 0; i < chapters.length && r.length < 50; i++) {
      if (chapters[i].text.toLowerCase().includes(q) || chapters[i].heading.toLowerCase().includes(q)) r.push(i);
    }
    setLres(r);
  }, [lsearch, chapters]);

  // Auto-scroll the currently-spoken word into view, but only when it's near
  // the edge of the reading pane (avoids jittery scroll on every word).
  useEffect(function() {
    if (spokenChar < 0) return;
    var el = document.querySelector(".rwhl");
    if (!el) return;
    var container = el.closest(".lit-left");
    if (!container) return;
    var er = el.getBoundingClientRect();
    var cr = container.getBoundingClientRect();
    var margin = 80;
    if (er.top < cr.top + margin || er.bottom > cr.bottom - margin) {
      el.scrollIntoView({ behavior: "smooth", block: "center" });
    }
  }, [spokenChar]);

  // Auto-scroll the chat / lit-msgs to bottom when a new message arrives
  // or the typing indicator appears/disappears, so the latest content stays visible.
  useEffect(function() {
    if (msgsRef.current) {
      msgsRef.current.scrollTop = msgsRef.current.scrollHeight;
    }
  }, [msgs.length, loading]);

  var api = async function(messages, sys) {
    var run = async function() {
      var ctrl = new AbortController();
      var tid = setTimeout(function() { ctrl.abort(); }, 30000);
      try {
        // Get a fresh JWT from Clerk to authorize the API call.
        var token = "";
        try { token = await auth.getToken(); } catch(e) { token = ""; }
        var headers = {"Content-Type":"application/json"};
        if (token) headers["Authorization"] = "Bearer " + token;
        var r = await fetch("/api/chat", {
          method:"POST", signal:ctrl.signal,
          headers: headers,
          body:JSON.stringify({
            messages: messages,
            system: sys || sysprompt(act, vocab, tips),
            max_tokens: 2048
          }),
        });
        clearTimeout(tid);
        var d = await r.json().catch(function(){ return {}; });
        if (!r.ok) throw new Error(d.error || ("HTTP " + r.status));
        return d.text || "";
      } catch(e) { clearTimeout(tid); throw (e.name === "AbortError" ? new Error("Timeout") : e); }
    };
    try { return await run(); } catch(e) {
      await new Promise(function(res){ setTimeout(res, 1500); });
      return await run();
    }
  };

  var startKeepalive = function() {
    if (keepAlive.current) clearInterval(keepAlive.current);
    // Chrome cuts off speechSynthesis after ~15 seconds. Pause+resume keeps it alive.
    keepAlive.current = setInterval(function() {
      if (!window.speechSynthesis || !window.speechSynthesis.speaking) {
        if (keepAlive.current) { clearInterval(keepAlive.current); keepAlive.current = null; }
        return;
      }
      window.speechSynthesis.pause();
      window.speechSynthesis.resume();
    }, 10000);
  };

  var stopKeepalive = function() {
    if (keepAlive.current) { clearInterval(keepAlive.current); keepAlive.current = null; }
  };

  var stopTTS = useCallback(function() {
    stopKeepalive();
    if (window.speechSynthesis) window.speechSynthesis.cancel();
    setPlaying(false); setSpkIdx(null); setSpokenChar(-1);
  }, []);

  var checkTTSAvailable = function() {
    if (!window.speechSynthesis) {
      setTtsErr("This browser does not support speechSynthesis.");
      return false;
    }
    var vs = window.speechSynthesis.getVoices();
    if (!vs.length) {
      setTtsErr("No voices available. Try clicking 🎙 Voice — if list is empty, your browser/OS has no installed voices.");
      return false;
    }
    return true;
  };

  var playText = useCallback(function(text, from) {
    if (from === undefined) from = 0;
    setTtsErr("");
    if (!checkTTSAvailable()) return;
    stopKeepalive();
    window.speechSynthesis.cancel();
    paraText.current = text;
    var slice = text.slice(from);
    if (!slice.trim()) return;

    // Chrome quirk: speak() immediately after cancel() often fails silently.
    // A small delay between cancel and speak fixes it.
    setTimeout(function() {
      setPlaying(true); charPos.current = from;
      var u = new SpeechSynthesisUtterance(slice);
      u.lang = "ru-RU"; u.rate = 0.84;
      if (voice) u.voice = voice;
      u.onstart = function() { startKeepalive(); };
      u.onboundary = function(e) {
        if (e.name === "word") {
          var pos = from + e.charIndex;
          charPos.current = pos;
          setSpokenChar(pos);
        }
      };
      u.onend = function() { stopKeepalive(); setPlaying(false); charPos.current = 0; setSpokenChar(-1); };
      u.onerror = function(e) {
        stopKeepalive();
        setSpokenChar(-1);
        var err = (e && e.error) || "unknown";
        if (err !== "interrupted" && err !== "canceled") {
          var hint = "";
          if (voice && /google/i.test(voice.name)) hint = " (Google network voices often fail in iframes — try a local voice via 🎙 Voice)";
          setTtsErr("Speech error: " + err + "." + hint);
          setPlaying(false);
        }
      };
      try { window.speechSynthesis.speak(u); }
      catch(ex) { setTtsErr("speak() threw: " + (ex.message || ex)); setPlaying(false); }
    }, 60);
  }, [voice]);

  var pauseTTS = useCallback(function() {
    stopKeepalive();
    if (window.speechSynthesis) window.speechSynthesis.cancel();
    setPlaying(false);
  }, []);

  var speakMsg = useCallback(function(text, idx) {
    setTtsErr("");
    if (!checkTTSAvailable()) return;
    stopKeepalive();
    window.speechSynthesis.cancel();
    if (spkIdx === idx) { setSpkIdx(null); return; }
    var ru = text.split("\n")
      .filter(function(l) { var t=l.trim(); return t && !/^\*{1,2}[^*]+\*{1,2}$/.test(t) && !/^📝/.test(t); })
      .join(" ")
      .replace(/\*\*[^*]+\*\*/g, function(m){ return m.replace(/\*\*/g,""); })
      .replace(/\[[^\]]+\]/g,"").replace(/\*[^*]+\*/g,"")
      .replace(/[a-zA-Z()/[\]{}|]/g,"").replace(/\s+/g," ").trim();
    if (!ru) return;
    setSpkIdx(idx);
    setTimeout(function() {
      var u = new SpeechSynthesisUtterance(ru);
      u.lang="ru-RU"; u.rate=0.84; if (voice) u.voice=voice;
      u.onstart = function(){ startKeepalive(); };
      u.onend = function(){ stopKeepalive(); setSpkIdx(null); };
      u.onerror = function(e){
        stopKeepalive();
        var err = (e && e.error) || "unknown";
        if (err !== "interrupted" && err !== "canceled") {
          var hint = "";
          if (voice && /google/i.test(voice.name)) hint = " (Google network voices often fail in iframes)";
          setTtsErr("Speech error: " + err + "." + hint);
        }
        setSpkIdx(null);
      };
      try { window.speechSynthesis.speak(u); }
      catch(ex) { setTtsErr("speak() threw: " + (ex.message || ex)); setSpkIdx(null); }
    }, 60);
  }, [voice, spkIdx]);

  var runDiagnostics = function() {
    var logs = [];
    var addLog = function(line) {
      logs.push(line);
      setDiagLogs(logs.slice());
    };

    addLog("=== TTS DIAGNOSTIC ===");
    addLog("UA: " + navigator.userAgent);
    addLog("speechSynthesis available: " + (window.speechSynthesis ? "YES" : "NO"));
    if (!window.speechSynthesis) return;

    var ss = window.speechSynthesis;
    addLog("Voices count: " + ss.getVoices().length);
    addLog("State before tests — speaking:" + ss.speaking + " pending:" + ss.pending + " paused:" + ss.paused);

    // In sandboxed iframes, the browser sometimes silently drops audio output.
    // Three tests narrow down the cause:
    //   T1 = baseline (English, default voice) — does any TTS work at all?
    //   T2 = Russian language without voice override — does ru-RU work generically?
    //   T3 = Russian with the user's chosen voice — does that specific voice work?

    ss.cancel();

    var runTest = function(name, text, lang, useVoice, delay) {
      setTimeout(function() {
        addLog("--- " + name + ": speak('" + text + "', lang=" + lang + (useVoice && voice ? ", voice=" + voice.name : ", default voice") + ") ---");
        var t0 = Date.now();
        var u = new SpeechSynthesisUtterance(text);
        u.lang = lang; u.rate = 1.0;
        if (useVoice && voice) u.voice = voice;

        u.onstart = function() { addLog(name + " onstart @ +" + (Date.now()-t0) + "ms"); };
        u.onend   = function() { addLog(name + " onend   @ +" + (Date.now()-t0) + "ms"); };
        u.onerror = function(e) { addLog(name + " onerror @ +" + (Date.now()-t0) + "ms — error: " + ((e && e.error) || "unknown")); };

        try { ss.speak(u); addLog(name + " speak() returned cleanly"); }
        catch(ex) { addLog(name + " speak() THREW: " + (ex.message || ex)); }

        setTimeout(function() { addLog(name + " +100ms — speaking:" + ss.speaking + " pending:" + ss.pending); }, 100);
        setTimeout(function() { addLog(name + " +500ms — speaking:" + ss.speaking + " pending:" + ss.pending); }, 500);
      }, delay);
    };

    runTest("T1 (English default)", "Hello, this is a test.",  "en-US", false, 200);
    runTest("T2 (Russian default)", "Привет, это тест.",       "ru-RU", false, 4000);
    runTest("T3 (Russian + voice)", "Привет, это тест.",       "ru-RU", true,  8000);

    setTimeout(function() { addLog("=== DIAGNOSTIC COMPLETE === Copy this log and share it."); }, 12000);
  };

  var copyDiagLogs = function() {
    var text = diagLogs.join("\n");
    if (navigator.clipboard) navigator.clipboard.writeText(text).catch(function(){});
  };

  var fetchDef = async function(word) {
    var raw = await api([{role:"user",content:defprompt(word)}],
      "You are a Russian-English dictionary. Return a single JSON object only. No markdown.");
    var c = raw.replace(/```[a-z]*\n?/gi,"").replace(/```/g,"").trim();
    var s = c.indexOf("{"), e2 = c.lastIndexOf("}");
    if (s === -1 || e2 === -1) throw new Error("No JSON");
    return JSON.parse(c.slice(s, e2+1));
  };

  var defWord = async function(word, e) {
    e.stopPropagation();
    var clean = word.replace(/[^а-яёА-ЯЁ]/g,"");
    if (!clean || clean.length < 2) return;
    var rect = e.currentTarget.getBoundingClientRect();
    var pw = Math.min(280, window.innerWidth-32);
    var left = rect.left;
    if (left+pw > window.innerWidth-16) left = window.innerWidth-pw-16;
    if (left < 16) left = 16;
    var top = window.innerHeight-rect.bottom > 220 ? rect.bottom+8 : rect.top-230;
    setPopXY({top:Math.max(8,top),left:left});
    setPopup({word:clean,data:null,loading:true,error:null,yo:null});
    try {
      var data = await fetchDef(clean);
      setPopup(function(p){ return p ? Object.assign({},p,{data:data,loading:false}) : null; });
    } catch(err) {
      var vars = yoVariants(clean);
      if (vars.length) {
        setPopup(function(p){ return p ? Object.assign({},p,{loading:false,yo:{orig:clean,vars:vars}}) : null; });
      } else {
        setPopup(function(p){ return p ? Object.assign({},p,{loading:false,error:'Could not define "'+clean+'"'}) : null; });
      }
    }
  };

  var defWithYo = async function(word) {
    setPopup(function(p){ return p ? Object.assign({},p,{loading:true,yo:null,error:null,word:word}) : null; });
    try {
      var data = await fetchDef(word);
      setPopup(function(p){ return p ? Object.assign({},p,{data:data,loading:false}) : null; });
    } catch(err) {
      setPopup(function(p){ return p ? Object.assign({},p,{loading:false,error:'Could not define "'+word+'"'}) : null; });
    }
  };

  // Pick a focus angle that hasn't been used in the last few sessions.
  var pickFocus = function() {
    var avoid = recentFoci.current;
    var available = QUESTION_FOCI.filter(function(f) { return avoid.indexOf(f.tag) === -1; });
    if (!available.length) { recentFoci.current = []; available = QUESTION_FOCI; }
    var pick = available[Math.floor(Math.random() * available.length)];
    recentFoci.current.push(pick.tag);
    if (recentFoci.current.length > 4) recentFoci.current.shift();
    return pick;
  };

  // Pull "❓1 Question text" lines out of an assistant message — used to remember
  // what we've already asked so we don't repeat next time.
  var extractQuestions = function(text) {
    var re = /❓\d+\s+([^\n]{6,200})/g;
    var qs = [];
    var m;
    while ((m = re.exec(text)) !== null) {
      var q = m[1].trim();
      if (q) qs.push(q);
    }
    return qs;
  };

  var loadQHist = async function() {
    try {
      var c = await storage.get(QHIST_KEY);
      if (c && c.value) return JSON.parse(c.value);
    } catch(e) {}
    return {};
  };

  var saveQHist = async function(hist) {
    try { await storage.set(QHIST_KEY, JSON.stringify(hist)); } catch(e) {}
  };

  var litAnalysis = async function(chs, i, metaOverride) {
    var ch = chs[i] || {};
    var snippet = (ch.text || "").slice(0, 600);
    var m = metaOverride || bookMeta;
    var focus = pickFocus();

    var hist = await loadQHist();
    var chKey = String(i);
    var prevQs = (hist[chKey] || []).slice(-12); // show the model up to 12 prior questions

    try {
      var t = await api([{role:"user",content:"Go."}],
        litprompt(snippet, i, chs.length, m.title || "this book", m.author || "the author", focus, prevQs));
      setMsgs([{role:"assistant",content:t}]);

      // Append newly-asked questions to history, capped so storage doesn't grow forever.
      var newQs = extractQuestions(t);
      if (newQs.length) {
        hist[chKey] = (hist[chKey] || []).concat(newQs).slice(-25);
        saveQHist(hist);
      }
    } catch(err) {
      setMsgs([{role:"assistant",content:"❓ Что вы заметили в этой главе?"}]);
    }
  };

  var startChat = async function() {
    setStarted(true); setMsgs([]); setLoading(true); setPopup(null); stopTTS();
    try { var t = await api([{role:"user",content:"Start please."}]); setMsgs([{role:"assistant",content:t}]); }
    catch(err) { setMsgs([{role:"assistant",content:"*(Error: "+err.message+" — try again.)*"}]); }
    setLoading(false);
  };

  var startLit = async function(idx, chs, metaOverride) {
    var p = chs || chapters; if (!p || !p.length) return;
    var i = idx !== undefined ? idx : cbm;
    setCidx(i); setCbm(i); setStarted(true); setMsgs([]); setLoading(true);
    setPopup(null); stopTTS(); setLview("read");
    charPos.current = 0; paraText.current = "";
    await litAnalysis(p, i, metaOverride); setLoading(false);
  };

  var navLit = async function(idx) {
    stopTTS(); charPos.current = 0; paraText.current = "";
    if (idx < 0 || idx >= chapters.length) return;
    setCidx(idx); setCbm(idx); setMsgs([]); setLoading(true); setLview("read");
    await litAnalysis(chapters, idx); setLoading(false);
  };

  var loadFile = async function(buf, fname) {
    setFErr("");
    try {
      var result = await parseEpub(buf);
      if (!result.chapters || result.chapters.length < 1) throw new Error("No chapters found in EPUB.");
      var meta = { title: result.title, author: result.author };
      setChapters(result.chapters);
      setBookMeta(meta);
      setCbm(0);
      try {
        await storage.set(EPUB_CACHE, JSON.stringify({
          chapters: result.chapters, title: result.title, author: result.author
        }));
        await storage.set(EPUB_BM, "0");
        // New book → wipe question history so chapter indices don't inherit stale questions.
        await storage.delete(QHIST_KEY);
      } catch(e) {}
      startLit(0, result.chapters, meta);
    } catch(err) { setFErr(err.message); }
  };

  var send = async function() {
    if (!input.trim() || loading) return;
    var um = {role:"user",content:input.trim()};
    var next = msgs.concat([um]); setMsgs(next); setInput(""); setLoading(true);
    try {
      var sys = isLit && chapters.length > 0
        ? litprompt(curChapter.text.slice(0,600), cidx, chapters.length, bookMeta.title || "this book", bookMeta.author || "the author")
        : undefined;
      var t = await api(next, sys);
      setMsgs(function(prev){ return prev.concat([{role:"assistant",content:t}]); });
    } catch(err) {
      setMsgs(function(prev){ return prev.concat([{role:"assistant",content:"*("+err.message+")*"}]); });
    }
    setLoading(false);
    if (inputRef.current) inputRef.current.focus();
  };

  var onKey = function(e) { if (e.key==="Enter" && !e.shiftKey){ e.preventDefault(); send(); } };

  var addV = function(ruOrEntry, en) {
    // Accepts either (ruString, enString) for legacy callers OR a full entry object:
    //   {ru, en, pos, aspect, grammar, example, exampleTranslation}
    var entry = (typeof ruOrEntry === "string")
      ? { ru: ruOrEntry, en: en || "" }
      : (ruOrEntry || {});
    var ru = (entry.ru || "").trim();
    if (!ru) return;
    if (vocab.find(function(v){ return v.ru === ru; })) return;
    setVocab(function(p){ return p.concat([Object.assign({}, entry, { ru: ru, id: Date.now() })]); });
  };
  var addT = function(tip) { if (!tips.find(function(t){ return t.tip===tip; })) setTips(function(p){ return p.concat([{tip:tip,id:Date.now()}]); }); };

  // Builds the canonical vocab entry from popup data:
  //   - nouns/adj/etc → lemma in nominative
  //   - verb without clear pair → infinitive
  //   - verb with pair → "imperfective / perfective" (or just "lemma / pair" if aspect unknown)
  var formatVocabEntry = function(data, fallback) {
    var fallbackRu = (fallback || "").trim();
    if (!data) return { ru: fallbackRu, en: "" };
    var lemma = (data.lemma || data.word || fallbackRu || "").trim();
    var pair  = (data.aspectPair || "").trim();
    var aspect = (data.aspect || "").toLowerCase();
    var ru;
    if (pair) {
      // Conventional dictionary order: imperfective / perfective.
      if (/imperf/.test(aspect))      ru = lemma + " / " + pair;
      else if (/^perf/.test(aspect))  ru = pair + " / " + lemma;
      else                            ru = lemma + " / " + pair;
    } else {
      ru = lemma;
    }
    return {
      ru: ru || fallbackRu,
      en: (data.translation || "").trim(),
      pos: (data.partOfSpeech || "").trim(),
      aspect: (data.aspect || "").trim(),
      grammar: (data.grammar || "").trim(),
      example: (data.example || "").trim(),
      exampleTranslation: (data.exampleTranslation || "").trim()
    };
  };

  var xBold = function(text) {
    var r = []; var re = /\*\*([^*\n(]{1,40})\(([^)]{1,60})\)\*\*/g; var m;
    while ((m = re.exec(text)) !== null) if (m[1].trim()) r.push({ru:m[1].trim(),en:m[2].trim()});
    return r;
  };
  var xTips = function(text) {
    var r = []; var re = /📝\s*TIP[:\s]+(.+)/g; var m;
    while ((m = re.exec(text)) !== null) if (m[1].trim()) r.push(m[1].trim());
    return r;
  };

  var renderLit = function(text) {
    var str = typeof text === "string" ? text : ((text && text.text) ? text.text : "");

    // Build tokens with absolute character positions in the original chapter text,
    // so we can match against onboundary events from speechSynthesis.
    var tokens = [];
    var tre = /[а-яёА-ЯЁ]+|[^а-яёА-ЯЁ]+/g;
    var tm;
    while ((tm = tre.exec(str)) !== null) {
      tokens.push({
        text: tm[0],
        start: tm.index,
        end: tm.index + tm[0].length,
        isRu: /[а-яёА-ЯЁ]/.test(tm[0][0])
      });
    }

    // Group tokens into paragraphs at \n{2,} boundaries (within non-Russian tokens).
    var paragraphs = [[]];
    for (var ti = 0; ti < tokens.length; ti++) {
      var tok = tokens[ti];
      if (tok.isRu) {
        paragraphs[paragraphs.length-1].push(tok);
        continue;
      }
      var sub = tok.text, subStart = tok.start, lastIdx = 0;
      var brkRe = /\n{2,}/g, brk;
      while ((brk = brkRe.exec(sub)) !== null) {
        if (brk.index > lastIdx) {
          paragraphs[paragraphs.length-1].push({
            text: sub.slice(lastIdx, brk.index),
            start: subStart + lastIdx,
            end:   subStart + brk.index,
            isRu: false
          });
        }
        paragraphs.push([]);
        lastIdx = brk.index + brk[0].length;
      }
      if (lastIdx < sub.length) {
        paragraphs[paragraphs.length-1].push({
          text: sub.slice(lastIdx),
          start: subStart + lastIdx,
          end:   tok.end,
          isRu: false
        });
      }
    }

    return paragraphs
      .filter(function(p){ return p.some(function(t){ return t.text.trim().length > 0; }); })
      .map(function(para, pi) {
        return (
          <p key={pi} style={{marginBottom:"1.2em"}}>
            {para.map(function(tk, i) {
              var hl = spokenChar >= tk.start && spokenChar < tk.end;
              if (tk.isRu) {
                return (
                  <span key={i}
                    className={"rw" + (hl ? " rwhl" : "")}
                    onClick={function(e){ defWord(tk.text, e); }}
                    title="Click to define">{tk.text}</span>
                );
              }
              return <span key={i}>{tk.text.replace(/\n/g, " ")}</span>;
            })}
          </p>
        );
      });
  };

  var renderBubble = function(text) {
    try {
      return text.split("\n").map(function(line, li) {
        var t = line.trim();
        var trm = t.match(/^\*{1,2}([^*]+)\*{1,2}$/);
        if (trm && !/[а-яёА-ЯЁ]{3,}/.test(trm[1])) return <div key={li} className="tline">{trm[1]}</div>;
        var tip = t.match(/^📝\s*TIP[:\s]+(.+)/);
        if (tip) return <div key={li} className="tipline">📝 {tip[1]}</div>;
        if (t.startsWith("❓")) return <div key={li} className="qline">{t}</div>;
        var toks = []; var rem = line; var ki = 0;
        while (rem.length > 0) {
          var bm = rem.match(/^\*\*([^*\n(]{1,40})\(([^)]{1,60})\)\*\*/);
          if (bm) {
            var bmRu = bm[1].trim();
            toks.push(<strong key={ki++} className="vw rw" onClick={(function(w){ return function(e){ defWord(w, e); }; })(bmRu)}>{bmRu}</strong>);
            rem = rem.slice(bm[0].length);
            continue;
          }
          if (rem.startsWith("**")) { rem=rem.slice(2); continue; }
          var cm = rem.match(/^\[([^\]]{1,60})\]/);
          if (cm) { toks.push(<span key={ki++} className="corr">[{cm[1]}]</span>); rem=rem.slice(cm[0].length); continue; }
          var rw = rem.match(/^[а-яёА-ЯЁ]+/);
          if (rw) {
            var rwWord = rw[0];
            toks.push(<span key={ki++} className="rw" onClick={(function(w){ return function(e){ defWord(w, e); }; })(rwWord)}>{rwWord}</span>);
            rem = rem.slice(rwWord.length);
            continue;
          }
          toks.push(<span key={ki++}>{rem[0]}</span>); rem=rem.slice(1);
        }
        return <div key={li} className="mline">{toks}</div>;
      });
    } catch(err) { return <div>{text}</div>; }
  };

  var renderMsg = function(msg, i) {
    if (msg.role==="user") return <div key={i} className="msg user"><div className="bub ubub">{msg.content}</div></div>;
    var tp=xTips(msg.content);
    return (
      <div key={i} className="msg ai">
        <div className="bub abub">{renderBubble(msg.content)}</div>
        <div className="acts">
          <button className={"spk"+(spkIdx===i?" spkon":"")} onClick={function(){ speakMsg(msg.content,i); }}>{spkIdx===i?"⏹ Stop":"🔊 Listen"}</button>
          {tp.map(function(t,j){
            var savedT = !!tips.find(function(x){ return x.tip === t; });
            return (
              <button key={j} className={"chip tc" + (savedT ? " chipsaved" : "")} disabled={savedT}
                onClick={function(){ if (!savedT) addT(t); }}
                title={savedT ? "Already saved" : "Save this tip"}>
                {savedT ? "✓ saved" : "📝 Save tip"}
              </button>
            );
          })}
        </div>
      </div>
    );
  };

  return (
    <>
      <style>{`
        @import url('https://fonts.googleapis.com/css2?family=Playfair+Display:wght@400;700&family=Crimson+Pro:ital,wght@0,300;0,400;0,600;1,400&display=swap');
        *,*::before,*::after{box-sizing:border-box;margin:0;padding:0}
        html,body{height:100%;background:#1a1611;color:#d2c5af;font-family:'Crimson Pro',serif}
        .app{min-height:100vh;background:#1a1611;display:flex;flex-direction:column;max-width:1000px;margin:0 auto}
        .app::before{content:'';position:fixed;inset:0;pointer-events:none;z-index:0;background:radial-gradient(ellipse at 15% 0%,rgba(150,80,60,.06) 0%,transparent 50%),radial-gradient(ellipse at 85% 100%,rgba(80,90,130,.05) 0%,transparent 50%)}
        .hdr{padding:16px 28px 12px;border-bottom:1px solid rgba(210,197,175,.1);display:flex;align-items:center;justify-content:space-between;gap:16px;position:relative;z-index:10}
        .logo{display:flex;align-items:baseline;gap:10px}
        .lru{font-family:'Playfair Display',serif;font-size:22px;font-weight:700;color:#c8a276}
        .lsub{font-size:11px;color:rgba(210,197,175,.35);letter-spacing:2.5px;text-transform:uppercase}
        .tbadge{background:rgba(200,162,118,.1);border:1px solid rgba(200,162,118,.25);color:#c8a276;padding:6px 14px;border-radius:20px;font-size:13px;cursor:pointer;max-width:280px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
        .tbadge:hover{background:rgba(200,162,118,.18)}
        .tabs{display:flex;border-bottom:1px solid rgba(210,197,175,.1);padding:0 28px;position:relative;z-index:10}
        .tab{padding:11px 20px;background:none;border:none;color:rgba(210,197,175,.4);font-family:'Crimson Pro',serif;font-size:14px;cursor:pointer;border-bottom:2px solid transparent;position:relative;top:1px;transition:color .2s}
        .tab.on{color:#c8a276;border-bottom-color:#c8a276}
        .tab:hover:not(.on){color:rgba(210,197,175,.7)}
        .bdg{background:#9d4630;color:#fff;font-size:10px;border-radius:10px;padding:1px 5px;margin-left:4px;vertical-align:middle}
        .bdg.g{background:#5a8556}
        .main{flex:1;display:flex;flex-direction:column;position:relative;z-index:1;min-height:0}
        .ss{flex:1;display:flex;flex-direction:column;align-items:center;justify-content:center;padding:48px 28px;text-align:center;gap:22px}
        .sico{font-size:54px;line-height:1}
        .sti{font-family:'Playfair Display',serif;font-size:30px;color:#d2c5af;font-weight:400}
        .sde{color:rgba(210,197,175,.5);font-size:16px;max-width:500px;line-height:1.6}
        .tsel{width:100%;max-width:500px;display:flex;flex-direction:column;gap:12px;text-align:left}
        .slbl{font-size:11px;text-transform:uppercase;letter-spacing:2px;color:rgba(210,197,175,.35)}
        select,input[type="text"],textarea{width:100%;background:rgba(210,197,175,.06);border:1px solid rgba(210,197,175,.16);color:#d2c5af;padding:12px 16px;border-radius:10px;font-family:'Crimson Pro',serif;font-size:16px;outline:none;transition:border-color .2s}
        select{appearance:none;cursor:pointer} select option{background:#221e17}
        ::placeholder{color:rgba(210,197,175,.28)}
        input:focus,textarea:focus,select:focus{border-color:rgba(200,162,118,.5)}
        .btn-p{background:linear-gradient(135deg,#9d4630,#82362a);color:#fff;border:none;padding:14px 32px;border-radius:10px;font-family:'Playfair Display',serif;font-size:17px;cursor:pointer;width:100%;box-shadow:0 4px 20px rgba(157,70,48,.3);transition:opacity .2s}
        .btn-p:hover:not(:disabled){opacity:.88} .btn-p:disabled{opacity:.4;cursor:default}
        .btn-g{background:rgba(210,197,175,.07);color:rgba(210,197,175,.6);border:1px solid rgba(210,197,175,.15);padding:12px 24px;border-radius:10px;font-family:'Crimson Pro',serif;font-size:15px;cursor:pointer;width:100%;transition:background .2s}
        .btn-g:hover{background:rgba(210,197,175,.12)}
        .chat-wrap{flex:1;display:flex;flex-direction:column;min-height:0}
        .msgs{flex:1;overflow-y:auto;padding:20px 28px 8px;display:flex;flex-direction:column;gap:12px}
        .msg{display:flex;flex-direction:column;gap:6px}
        .msg.user{align-items:flex-end} .msg.ai{align-items:flex-start}
        .bub{max-width:72%;padding:14px 18px;font-size:16px;line-height:1.7}
        .abub{background:rgba(210,197,175,.065);border:1px solid rgba(210,197,175,.11);border-radius:4px 16px 16px 16px}
        .ubub{background:rgba(157,70,48,.2);border:1px solid rgba(157,70,48,.28);border-radius:16px 4px 16px 16px}
        .mline{display:block;margin-bottom:3px;line-height:1.7}
        .tline{color:rgba(210,197,175,.5);font-size:14px;margin-top:6px;display:block;line-height:1.65;padding-top:5px;border-top:1px solid rgba(210,197,175,.08)}
        .tipline{color:rgba(128,168,128,.85);font-size:13.5px;border-left:2px solid rgba(128,168,128,.35);padding-left:8px;margin-top:7px;display:block;line-height:1.5}
        .qline{color:#c8a276;font-size:15px;margin-top:10px;display:block;line-height:1.6;padding:8px 12px;background:rgba(200,162,118,.07);border-radius:8px;border-left:2px solid rgba(200,162,118,.4)}
        .vw{color:#c8a276} .corr{color:#87a8c4}
        .vw.rw{color:#c8a276;border-bottom:1px dotted rgba(200,162,118,.5)}
        .vw.rw:hover{color:#ece1cb;border-bottom-color:#ece1cb;background:rgba(200,162,118,.18);border-radius:2px}
        .rw{cursor:pointer;border-bottom:1px dotted rgba(210,197,175,.18);transition:color .15s,background .12s}
        .rw:hover{color:#c8a276;border-bottom-color:#c8a276}
        .rwhl{background:rgba(200,162,118,.18);color:#ece1cb;border-bottom-color:#c8a276;border-radius:3px;padding:1px 2px}
        .acts{display:flex;flex-wrap:wrap;gap:6px;margin-top:2px}
        .spk{padding:5px 12px;border-radius:20px;font-size:13px;cursor:pointer;font-family:'Crimson Pro',serif;background:rgba(210,197,175,.07);border:1px solid rgba(210,197,175,.2);color:rgba(210,197,175,.7);transition:all .15s}
        .spk:hover{background:rgba(210,197,175,.14)} .spkon{background:rgba(157,70,48,.18);border-color:rgba(157,70,48,.35);color:#c87a6806a}
        .chip{padding:5px 12px;border-radius:20px;font-size:12px;cursor:pointer;font-family:'Crimson Pro',serif;border:1px solid;transition:background .15s}
        .vc{background:rgba(200,162,118,.09);border-color:rgba(200,162,118,.28);color:#c8a276} .vc:hover:not(:disabled){background:rgba(200,162,118,.18)}
        .tc{background:rgba(128,168,128,.08);border-color:rgba(128,168,128,.25);color:rgba(128,168,128,.9)} .tc:hover:not(:disabled){background:rgba(128,168,128,.15)}
        .chip:disabled,.chipsaved{cursor:default;opacity:.7}
        .chipsaved{background:rgba(128,168,128,.15)!important;border-color:rgba(128,168,128,.4)!important;color:rgba(150,190,150,.95)!important}
        .typing{display:flex;align-items:center;gap:5px;padding:12px 16px;background:rgba(210,197,175,.065);border:1px solid rgba(210,197,175,.11);border-radius:4px 16px 16px 16px;width:fit-content}
        .dot{width:6px;height:6px;background:rgba(210,197,175,.4);border-radius:50%;animation:bounce 1.2s ease-in-out infinite}
        .dot:nth-child(2){animation-delay:.2s} .dot:nth-child(3){animation-delay:.4s}
        @keyframes bounce{0%,80%,100%{transform:translateY(0);opacity:.4}40%{transform:translateY(-5px);opacity:1}}
        .ibar{padding:12px 28px 16px;border-top:1px solid rgba(210,197,175,.09);display:flex;gap:10px;align-items:flex-end;background:#1a1611;z-index:10}
        .ibar textarea{flex:1;resize:none;min-height:44px;max-height:120px;padding:10px 14px;border-radius:22px;font-size:15px;line-height:1.5}
        .isend{background:linear-gradient(135deg,#9d4630,#82362a);color:#fff;border:none;width:44px;height:44px;border-radius:50%;font-size:18px;cursor:pointer;display:flex;align-items:center;justify-content:center;flex-shrink:0;transition:opacity .15s}
        .isend:hover:not(:disabled){opacity:.85} .isend:disabled{opacity:.35;cursor:default}
        .inew{background:rgba(210,197,175,.06);color:rgba(210,197,175,.5);border:1px solid rgba(210,197,175,.15);padding:0 16px;border-radius:22px;font-size:13px;cursor:pointer;font-family:'Crimson Pro',serif;height:44px;white-space:nowrap;transition:all .15s}
        .inew:hover{background:rgba(210,197,175,.12);color:#d2c5af}
        .lit-wrap{flex:1;display:flex;flex-direction:column;min-height:0;overflow:hidden}
        .lit-top{display:flex;align-items:center;gap:8px;padding:8px 28px;border-bottom:1px solid rgba(210,197,175,.1);flex-shrink:0;background:#1a1611}
        .ltab{padding:6px 14px;border-radius:16px;background:none;border:1px solid rgba(210,197,175,.14);color:rgba(210,197,175,.45);font-family:'Crimson Pro',serif;font-size:13px;cursor:pointer;transition:all .15s}
        .ltab.on{background:rgba(200,162,118,.12);border-color:rgba(200,162,118,.3);color:#c8a276}
        .ltab:hover:not(.on){background:rgba(210,197,175,.06)}
        .lprog{margin-left:auto;display:flex;align-items:center;gap:10px}
        .lpct{font-size:12px;color:rgba(210,197,175,.35)}
        .lpbar{width:80px;height:3px;background:rgba(210,197,175,.1);border-radius:2px;overflow:hidden}
        .lpfill{height:100%;background:#c8a276;border-radius:2px;transition:width .3s}
        .ttsbar{display:flex;align-items:center;gap:10px;padding:7px 28px;background:#1e1a14;border-bottom:1px solid rgba(210,197,175,.08);flex-shrink:0}
        .ttsplay{width:32px;height:32px;border-radius:50%;background:linear-gradient(135deg,#9d4630,#82362a);border:none;color:#fff;font-size:14px;cursor:pointer;display:flex;align-items:center;justify-content:center;flex-shrink:0;transition:opacity .15s}
        .ttsplay:hover{opacity:.85}
        .ttspause{width:32px;height:32px;border-radius:50%;background:rgba(157,70,48,.2);border:1px solid rgba(157,70,48,.4);color:#c87a6806a;font-size:14px;cursor:pointer;display:flex;align-items:center;justify-content:center;flex-shrink:0}
        .ttslab{flex:1;font-size:12px;color:rgba(210,197,175,.4);overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
        .ttsbtn{background:none;border:1px solid rgba(210,197,175,.15);color:rgba(210,197,175,.4);height:26px;border-radius:8px;font-size:12px;cursor:pointer;padding:0 10px;transition:all .15s}
        .ttsbtn:hover{background:rgba(210,197,175,.08);color:rgba(210,197,175,.7)}
        .vpanel{background:#1e1a14;border-bottom:1px solid rgba(210,197,175,.08);max-height:180px;display:flex;flex-direction:column;flex-shrink:0}
        .vphdr{padding:7px 28px 4px;border-bottom:1px solid rgba(210,197,175,.06);font-size:12px;color:rgba(210,197,175,.35)}
        .vplist{overflow-y:auto;padding:4px 28px}
        .vprow{width:100%;background:none;border:none;border-bottom:1px solid rgba(210,197,175,.05);padding:7px 0;display:flex;align-items:center;justify-content:space-between;cursor:pointer;gap:10px;transition:background .15s}
        .vprow:hover,.vprow.sel{background:rgba(200,162,118,.06)}
        .vpn{font-size:14px;color:#d2c5af;font-family:'Crimson Pro',serif;text-align:left}
        .vpnru{color:#c8a276} .vpl{font-size:11px;color:rgba(210,197,175,.28)}
        .vpem{font-size:13px;color:rgba(210,197,175,.3);padding:14px 0;text-align:center}
        .lit-body{flex:1;display:flex;min-height:0;overflow:hidden}
        .lit-left{flex:1;overflow-y:auto;padding:24px 28px;border-right:1px solid rgba(210,197,175,.08)}
        .lit-right{width:380px;flex-shrink:0;display:flex;flex-direction:column;min-height:0}
        @media(max-width:900px){
          .lit-body{flex-direction:column}
          .lit-left{
            border-right:none;
            border-bottom:none;
            max-height:none;
            flex:1;
            /* Leave room at the bottom for the floating nav + chat panel. */
            padding-bottom:calc(40vh + 64px);
          }
          .lit-right{
            width:100%;
            max-width:1000px;
            position:fixed;
            bottom:0;
            left:0;
            right:0;
            margin:0 auto;
            height:40vh;
            background:rgba(26,22,17,.96);
            -webkit-backdrop-filter:blur(10px);
            backdrop-filter:blur(10px);
            border-top:1px solid rgba(210,197,175,.12);
            z-index:50;
            padding-bottom:env(safe-area-inset-bottom);
          }
          /* Pin the Previous / 📌 / Next bar directly above the floating chat,
             with rounded top corners so the two together feel like a unified bottom sheet. */
          .lnav{
            position:fixed;
            bottom:40vh;
            left:0;
            right:0;
            max-width:1000px;
            margin:0 auto;
            z-index:51;
            border-top:none;
            background:rgba(26,22,17,.94);
            -webkit-backdrop-filter:blur(10px);
            backdrop-filter:blur(10px);
            border-radius:14px 14px 0 0;
            box-shadow:0 -8px 28px rgba(0,0,0,.45);
          }
        }
        .lhdr{font-size:11px;color:rgba(210,197,175,.3);text-transform:uppercase;letter-spacing:1.5px;margin-bottom:8px}
        .lch-heading{font-family:'Playfair Display',serif;font-size:20px;color:#c8a276;margin-bottom:14px}
        .ltxt{font-size:17.5px;line-height:1.85;color:#d2c5af;font-family:'Crimson Pro',serif;word-wrap:break-word;overflow-wrap:break-word;letter-spacing:.005em}
        .lit-msgs{flex:0 1 auto;max-height:50%;overflow-y:auto;padding:14px 20px 8px;display:flex;flex-direction:column;gap:10px}
        .lit-ibar{position:relative;padding:10px 20px 14px;border-top:1px solid rgba(210,197,175,.08);background:#1a1611;flex:1 1 auto;min-height:0;display:flex;flex-direction:column}
        .lit-ibar textarea{flex:1;width:100%;resize:none;min-height:80px;max-height:none;padding:14px 60px 14px 16px;border-radius:14px;font-size:16px;line-height:1.55}
        .lit-ibar .isend{position:absolute;bottom:22px;right:28px;box-shadow:0 4px 14px rgba(0,0,0,.4)}
        .lnav{display:flex;gap:8px;padding:12px 28px;border-top:1px solid rgba(210,197,175,.08);flex-shrink:0;background:#1a1611}
        .lnb{flex:1;padding:10px;border-radius:10px;border:1px solid rgba(210,197,175,.14);background:rgba(210,197,175,.05);color:rgba(210,197,175,.55);font-family:'Crimson Pro',serif;font-size:14px;cursor:pointer;transition:all .15s;text-align:center}
        .lnb:hover:not(:disabled){background:rgba(210,197,175,.1);color:#d2c5af} .lnb:disabled{opacity:.22;cursor:default}
        .lnb.p{background:linear-gradient(135deg,#9d4630,#82362a);border-color:transparent;color:#fff} .lnb.p:hover{opacity:.9}
        .lbm{padding:10px 14px;border-radius:10px;border:1px solid rgba(200,162,118,.25);background:rgba(200,162,118,.07);color:#c8a276;font-size:15px;cursor:pointer;transition:background .15s}
        .lbm:hover{background:rgba(200,162,118,.15)}
        .navpanel{flex:1;overflow-y:auto;padding:16px 28px;display:flex;flex-direction:column;gap:8px}
        .lcard{padding:12px 14px;border-radius:10px;background:rgba(210,197,175,.04);border:1px solid rgba(210,197,175,.09);cursor:pointer;transition:all .15s}
        .lcard:hover{background:rgba(210,197,175,.08)} .lcard.cur{border-color:rgba(200,162,118,.4);background:rgba(200,162,118,.07)}
        .lcn{font-size:10px;color:rgba(210,197,175,.28);letter-spacing:1px;margin-bottom:4px}
        .lchead{font-size:14px;color:#c8a276;font-family:'Playfair Display',serif;margin-bottom:3px}
        .lcp{font-size:13px;color:rgba(210,197,175,.55);line-height:1.4}
        .lem{text-align:center;color:rgba(210,197,175,.28);padding:32px;font-size:14px}
        .lsbar{padding:12px 28px;border-bottom:1px solid rgba(210,197,175,.08)}
        .pover{position:fixed;inset:0;z-index:200;background:rgba(0,0,0,.15)}
        .pop{position:fixed;z-index:201;background:#23201a;border:1px solid rgba(210,197,175,.2);border-radius:14px;padding:16px 18px 18px;box-shadow:0 12px 40px rgba(0,0,0,.6);animation:pf .15s ease}
        @keyframes pf{from{opacity:0;transform:translateY(-4px)}to{opacity:1;transform:none}}
        .pcl{position:absolute;top:10px;right:12px;background:none;border:none;color:rgba(210,197,175,.35);font-size:18px;cursor:pointer}
        .pcl:hover{color:rgba(210,197,175,.7)}
        .pw{font-family:'Playfair Display',serif;font-size:22px;color:#c8a276;margin-bottom:2px;padding-right:24px}
        .ppos{font-size:11px;color:rgba(210,197,175,.35);text-transform:uppercase;letter-spacing:1.5px;margin-bottom:8px}
        .ptr{font-size:18px;color:#d2c5af;margin-bottom:7px}
        .pgr{font-size:13px;color:rgba(135,168,196,.8);margin-bottom:7px;background:rgba(135,168,196,.08);border-radius:8px;padding:5px 10px}
        .pex{font-size:13px;color:rgba(210,197,175,.5);border-top:1px solid rgba(210,197,175,.08);padding-top:7px;line-height:1.5}
        .pext{font-size:12px;color:rgba(210,197,175,.3);margin-top:3px}
        .pload{color:rgba(210,197,175,.4);font-size:14px;text-align:center;padding:14px 0}
        .perr{color:#c87a68;font-size:13px}
        .psave{margin-top:12px;width:100%;border:1px solid rgba(200,162,118,.28);background:rgba(200,162,118,.09);color:#c8a276;padding:10px;border-radius:10px;font-size:14px;cursor:pointer;font-family:'Crimson Pro',serif;transition:background .15s}
        .psave:hover{background:rgba(200,162,118,.2)}
        .yobtn{width:100%;background:rgba(210,197,175,.06);border:1px solid rgba(210,197,175,.15);color:#d2c5af;padding:9px;border-radius:10px;font-size:15px;cursor:pointer;font-family:'Crimson Pro',serif;transition:background .15s;text-align:left;margin-bottom:4px}
        .yobtn:hover{background:rgba(210,197,175,.12)}
        .panel{flex:1;padding:28px;overflow-y:auto;display:flex;flex-direction:column;gap:14px}
        .phdr{display:flex;align-items:center;justify-content:space-between;margin-bottom:4px}
        .pti{font-family:'Playfair Display',serif;font-size:20px;color:#d2c5af}
        .ab{border:1px solid rgba(200,162,118,.28);background:rgba(200,162,118,.08);color:#c8a276;padding:7px 16px;border-radius:20px;font-size:13px;cursor:pointer;font-family:'Crimson Pro',serif;transition:background .15s}
        .ab:hover{background:rgba(200,162,118,.18)}
        .ab.g{border-color:rgba(128,168,128,.28);background:rgba(128,168,128,.07);color:rgba(128,168,128,.9)} .ab.g:hover{background:rgba(128,168,128,.15)}
        .empty{text-align:center;color:rgba(210,197,175,.3);font-size:15px;padding:48px 0;line-height:1.7}
        .ilist{display:flex;flex-direction:column;gap:8px}
        .icard{background:rgba(210,197,175,.04);border:1px solid rgba(210,197,175,.09);border-radius:12px;padding:13px 16px;display:flex;align-items:flex-start;justify-content:space-between;gap:12px;transition:background .15s}
        .icard:hover{background:rgba(210,197,175,.07)}
        .icont{display:flex;flex-direction:column;gap:3px;flex:1;min-width:0}
        .ipri{font-size:17px;color:#d2c5af;font-family:'Playfair Display',serif}
        .ipos{font-size:11px;color:rgba(200,162,118,.7);text-transform:uppercase;letter-spacing:1.5px;margin-bottom:1px}
        .isec{font-size:14px;color:rgba(210,197,175,.75)}
        .igr{font-size:12px;color:rgba(135,168,196,.7);background:rgba(135,168,196,.06);border-radius:6px;padding:3px 8px;align-self:flex-start;margin-top:3px}
        .iex{font-size:13px;color:rgba(210,197,175,.5);font-style:italic;margin-top:6px;padding-top:6px;border-top:1px solid rgba(210,197,175,.06);line-height:1.5}
        .iext{font-style:normal;font-size:12px;color:rgba(210,197,175,.35);margin-top:2px}
        .rmb{background:rgba(157,70,48,.1);border:1px solid rgba(157,70,48,.25);color:rgba(200,128,112,.75);font-size:18px;cursor:pointer;padding:0;width:30px;height:30px;border-radius:8px;display:flex;align-items:center;justify-content:center;flex-shrink:0;transition:all .15s}
        .rmb:hover{background:rgba(157,70,48,.3);border-color:rgba(157,70,48,.5);color:#fff}
        .mover{position:fixed;inset:0;background:rgba(26,22,17,.85);z-index:100;display:flex;align-items:center;justify-content:center;padding:24px}
        .modal{background:#1f1c16;border:1px solid rgba(210,197,175,.14);border-radius:16px;padding:28px;width:100%;max-width:480px;display:flex;flex-direction:column;gap:16px}
        .mti{font-family:'Playfair Display',serif;font-size:22px;color:#d2c5af}
        .mact{display:flex;gap:10px;justify-content:flex-end;margin-top:4px}
        .mcanc{background:none;border:1px solid rgba(210,197,175,.18);color:rgba(210,197,175,.55);padding:10px 20px;border-radius:10px;font-size:15px;cursor:pointer;font-family:'Crimson Pro',serif;transition:all .15s}
        .mcanc:hover{color:#d2c5af;border-color:rgba(210,197,175,.35)}
        .mconf{background:linear-gradient(135deg,#9d4630,#82362a);color:#fff;border:none;padding:10px 20px;border-radius:10px;font-size:15px;cursor:pointer;font-family:'Crimson Pro',serif;transition:opacity .15s}
        .mconf:hover{opacity:.85} .mconf.g{background:linear-gradient(135deg,#5a8556,#4a6845)}

        /* First-visit landing screen */
        .land{position:fixed;inset:0;z-index:9999;background:#1a1611;display:flex;align-items:center;justify-content:center;padding:32px;overflow-y:auto}
        .land::before{content:'';position:fixed;inset:0;pointer-events:none;background:radial-gradient(ellipse at 20% 10%,rgba(150,80,60,.10) 0%,transparent 55%),radial-gradient(ellipse at 80% 90%,rgba(80,90,130,.08) 0%,transparent 55%)}
        .land-card{position:relative;max-width:580px;width:100%;text-align:center;display:flex;flex-direction:column;gap:28px;align-items:center;padding:24px}
        .land-flag{font-size:56px;margin-bottom:-4px}
        .land-title{font-family:'Playfair Display',serif;font-size:54px;font-weight:700;color:#c8a276;letter-spacing:-1px;line-height:1}
        .land-sub{font-size:12px;letter-spacing:3px;text-transform:uppercase;color:rgba(210,197,175,.45);margin-top:-12px}
        .land-tagline{font-family:'Crimson Pro',serif;font-style:italic;font-size:18px;color:rgba(210,197,175,.75);max-width:440px;line-height:1.5}
        .land-tips{background:rgba(200,162,118,.06);border:1px solid rgba(200,162,118,.18);border-radius:14px;padding:22px 26px;text-align:left;width:100%;max-width:440px;display:flex;flex-direction:column;gap:14px;margin-top:8px}
        .land-tips-title{font-family:'Playfair Display',serif;font-size:14px;color:#c8a276;letter-spacing:2px;text-transform:uppercase;text-align:center;margin-bottom:4px}
        .land-tip{display:flex;gap:12px;align-items:flex-start;font-size:15px;line-height:1.5;color:#d2c5af}
        .land-tip-num{flex-shrink:0;width:24px;height:24px;border-radius:50%;background:rgba(200,162,118,.15);border:1px solid rgba(200,162,118,.3);color:#c8a276;display:flex;align-items:center;justify-content:center;font-size:12px;font-weight:700;margin-top:1px}
        .land-tip strong{color:#c8a276;font-weight:600}
        .land-begin{background:linear-gradient(135deg,#9d4630,#82362a);color:#fff;border:none;padding:16px 48px;border-radius:12px;font-size:18px;font-family:'Crimson Pro',serif;cursor:pointer;transition:opacity .15s,transform .1s;letter-spacing:1px;margin-top:8px;box-shadow:0 6px 20px rgba(0,0,0,.3)}
        .land-begin:hover{opacity:.92;transform:translateY(-1px)}
        .land-begin:active{transform:translateY(0)}
        @media (max-width:520px){
          .land-title{font-size:42px}
          .land-tagline{font-size:16px}
          .land-tips{padding:18px 20px}
          .land-tip{font-size:14px}
        }

        /* Sign-in / sign-out auth UI */
        .auth-page{min-height:100vh;background:#1a1611;display:flex;align-items:center;justify-content:center;padding:32px;position:relative}
        .auth-page::before{content:'';position:fixed;inset:0;pointer-events:none;background:radial-gradient(ellipse at 20% 10%,rgba(150,80,60,.10) 0%,transparent 55%),radial-gradient(ellipse at 80% 90%,rgba(80,90,130,.08) 0%,transparent 55%)}
        .auth-card{position:relative;display:flex;flex-direction:column;align-items:center;gap:20px;max-width:440px;width:100%}
        .auth-brand{text-align:center;margin-bottom:8px}
        .auth-brand-flag{font-size:44px}
        .auth-brand-title{font-family:'Playfair Display',serif;font-size:42px;font-weight:700;color:#c8a276;line-height:1;margin-top:8px}
        .auth-brand-sub{font-size:11px;letter-spacing:3px;text-transform:uppercase;color:rgba(210,197,175,.45);margin-top:6px}
        .userbtn-wrap{display:flex;align-items:center}
      `}</style>

      <SignedOut>
        <div className="auth-page">
          <div className="auth-card">
            <div className="auth-brand">
              <div className="auth-brand-flag">🇷🇺</div>
              <div className="auth-brand-title">Говорим</div>
              <div className="auth-brand-sub">Russian Practice</div>
            </div>
            <SignIn routing="hash" />
          </div>
        </div>
      </SignedOut>

      <SignedIn>
      {!seenLanding && (
        <div className="land">
          <div className="land-card">
            <div className="land-flag">🇷🇺</div>
            <div>
              <div className="land-title">Говорим</div>
              <div className="land-sub">Russian Practice</div>
            </div>
            <div className="land-tagline">
              Read Russian books with a tutor that asks comprehension questions, explains grammar, and remembers what you've learned.
            </div>
            <div className="land-tips">
              <div className="land-tips-title">Before you begin</div>
              <div className="land-tip">
                <span className="land-tip-num">1</span>
                <span>Open this app in <strong>Microsoft Edge</strong> for the best read-aloud experience. (On iPhone, use Safari with Premium Russian voices downloaded.)</span>
              </div>
              <div className="land-tip">
                <span className="land-tip-num">2</span>
                <span>In the voice picker (🔊), select a <strong>natural Russian voice</strong> — look for ones marked <strong>★ neural</strong> or <strong>✓ local</strong>.</span>
              </div>
            </div>
            <button className="land-begin" onClick={dismissLanding}>Begin</button>
          </div>
        </div>
      )}

      <div className="app">
        <header className="hdr">
          <div className="logo"><span className="lru">Говорим</span><span className="lsub">Russian Practice</span></div>
          <div style={{display:"flex",alignItems:"center",gap:12}}>
            {started && <button className="tbadge" onClick={function(){ setShowTopic(true); }}>{isLit ? ("📖 " + (bookMeta.title || "Book")) : ("💬 "+act)}</button>}
            <div className="userbtn-wrap"><UserButton afterSignOutUrl="/" /></div>
          </div>
        </header>

        <div className="tabs">
          {["chat","vocab","grammar"].map(function(t){
            return (
              <button key={t} className={"tab"+(tab===t?" on":"")} onClick={function(){ setTab(t); }}>
                {t==="chat"?"Conversation":t==="vocab"?"Vocabulary":"Grammar"}
                {t==="vocab"&&vocab.length>0&&<span className="bdg">{vocab.length}</span>}
                {t==="grammar"&&tips.length>0&&<span className="bdg g">{tips.length}</span>}
              </button>
            );
          })}
        </div>

        {ttsErr && (
          <div style={{padding:"8px 28px",background:"rgba(157,70,48,.18)",borderBottom:"1px solid rgba(157,70,48,.35)",color:"#c87a68",fontSize:13,display:"flex",alignItems:"center",gap:10}}>
            <span style={{flex:1}}>🔊 {ttsErr}</span>
            <button onClick={function(){ setTtsErr(""); }} style={{background:"none",border:"none",color:"#c87a68",cursor:"pointer",fontSize:18,padding:0}}>×</button>
          </div>
        )}

        {tab==="chat" && (
          <div className="main">
            {!started && !mode && (
              <div className="ss">
                <div className="sico">🇷🇺</div>
                <h1 className="sti">Говорим</h1>
                <p className="sde">Choose how you want to practice today.</p>
                <div style={{width:"100%",maxWidth:500,display:"flex",flexDirection:"column",gap:14}}>
                  <button className="btn-p" onClick={function(){ setMode("chat"); }} style={{textAlign:"left",padding:"18px 22px"}}>
                    <div style={{fontSize:22,marginBottom:4}}>💬 Chat</div>
                    <div style={{fontSize:13,opacity:.85,fontFamily:"'Crimson Pro',serif",fontStyle:"italic"}}>Pick a topic, hear interesting facts, answer probing questions.</div>
                  </button>
                  <button className="btn-p" onClick={function(){ setMode("read"); }} style={{textAlign:"left",padding:"18px 22px"}}>
                    <div style={{fontSize:22,marginBottom:4}}>📖 Read</div>
                    <div style={{fontSize:13,opacity:.85,fontFamily:"'Crimson Pro',serif",fontStyle:"italic"}}>Load any Russian EPUB, then practice with comprehension questions.</div>
                  </button>
                </div>
              </div>
            )}

            {!started && mode === "chat" && (
              <div className="ss">
                <div className="sico">💬</div>
                <h1 className="sti">Давайте поговорим</h1>
                <p className="sde">Choose a topic and start a natural Russian conversation.</p>
                <div className="tsel">
                  <span className="slbl">Topic</span>
                  <select value={topic} onChange={function(e){ setTopic(e.target.value); setCustom(""); }}>
                    {TOPICS.map(function(t){ return <option key={t}>{t}</option>; })}
                  </select>
                  <input type="text" placeholder="Or type a custom topic…" value={custom} onChange={function(e){ setCustom(e.target.value); }}/>
                </div>
                <div style={{width:"100%",maxWidth:500,display:"flex",flexDirection:"column",gap:8}}>
                  <button className="btn-p" onClick={startChat}>Начать разговор →</button>
                  <button className="btn-g" onClick={function(){ setMode(""); }}>← Back</button>
                </div>
              </div>
            )}

            {!started && mode === "read" && (
              <div className="ss">
                <div className="sico">📖</div>
                <h1 className="sti">{chapters.length > 0 ? bookMeta.title : "Open a Russian EPUB"}</h1>
                <p className="sde">{chapters.length > 0 ? bookMeta.author : "Load any .epub file from your computer or phone. Works with EPUBs from Gutenberg, Litres, Flibusta, etc. Cached after first load."}</p>
                <div style={{width:"100%",maxWidth:500,display:"flex",flexDirection:"column",gap:10}}>
                  {chapters.length > 0 ? (
                    <>
                      {cbm > 0 && <button className="btn-p" onClick={function(){ startLit(cbm); }}>📌 Resume at chapter {cbm+1}</button>}
                      <button className={cbm>0?"btn-g":"btn-p"} onClick={function(){ startLit(0); }}>{cbm>0?"Start from beginning":"Начать читать →"}</button>
                      <FileBtn label="Load a different EPUB" onLoad={loadFile}/>
                      <button className="btn-g" style={{fontSize:13,padding:"8px"}} onClick={async function(){
                        setChapters([]); setCidx(0); setCbm(0); setBookMeta({title:"",author:""});
                        try { await storage.delete(EPUB_CACHE); } catch(e) {}
                        try { await storage.delete(EPUB_BM); } catch(e) {}
                        try { await storage.delete(QHIST_KEY); } catch(e) {}
                      }}>🗑 Clear cached book</button>
                    </>
                  ) : (
                    <FileBtn label="Choose .epub file" onLoad={loadFile}/>
                  )}
                  {fErr && <p style={{color:"#c87a68",fontSize:13,lineHeight:1.5}}>{fErr}</p>}
                  <button className="btn-g" onClick={function(){ setMode(""); }}>← Back</button>
                </div>
              </div>
            )}

            {started && isLit && (
              <div className="lit-wrap">
                <div className="lit-top">
                  <button className={"ltab"+(lview==="read"?" on":"")} onClick={function(){ setLview("read"); }}>📖 Read</button>
                  <button className={"ltab"+(lview==="nav"?" on":"")} onClick={function(){ setLview("nav"); }}>🗂 Chapters</button>
                  <button className={"ltab"+(lview==="search"?" on":"")} onClick={function(){ setLview("search"); }}>🔍 Search</button>
                  <div className="lprog">
                    <span className="lpct">Ch. {cidx+1}/{chapters.length} · {pct}%</span>
                    <div className="lpbar"><div className="lpfill" style={{width:pct+"%"}}/></div>
                  </div>
                </div>

                {lview==="read" && (
                  <>
                    <div className="ttsbar">
                      {!playing
                        ? <button className="ttsplay" onClick={function(){ paraText.current=curChapter.text||""; playText(paraText.current,charPos.current); }}>▶</button>
                        : <button className="ttspause" onClick={pauseTTS}>⏸</button>
                      }
                      <span className="ttslab">{playing?"Reading…":charPos.current>0?(voice&&voice.name||"Voice")+" — paused":voice?(voice.name+" — click ▶"):"No Russian voice found"}</span>
                      {charPos.current>0 && <button className="ttsbtn" onClick={function(){ stopTTS(); charPos.current=0; paraText.current=""; }}>⏹</button>}
                      <button className="ttsbtn" onClick={function(){ setShowVP(function(v){ return !v; }); }}>🎙 Voice</button>
                    </div>

                    {showVP && (
                      <div className="vpanel" style={{maxHeight: diagLogs.length > 0 ? 380 : 180}}>
                        <div className="vphdr" style={{display:"flex",alignItems:"center",justifyContent:"space-between",gap:8}}>
                          <span>Choose voice — Russian voices in gold</span>
                          <div style={{display:"flex",gap:6}}>
                            {diagLogs.length > 0 && <button className="ttsbtn" style={{height:22,fontSize:11}} onClick={copyDiagLogs}>📋 Copy log</button>}
                            <button className="ttsbtn" style={{height:22,fontSize:11}} onClick={runDiagnostics}>🩺 Diagnose</button>
                          </div>
                        </div>
                        {diagLogs.length > 0 && (
                          <div style={{maxHeight:180,overflowY:"auto",padding:"6px 28px",fontFamily:"monospace",fontSize:11,color:"rgba(210,197,175,.7)",background:"#0a0908",borderBottom:"1px solid rgba(210,197,175,.06)",lineHeight:1.5}}>
                            {diagLogs.map(function(line,i){
                              var color = line.indexOf("onerror") >= 0 || line.indexOf("THREW") >= 0 ? "#c87a6806a"
                                       : line.indexOf("onstart") >= 0 ? "#82a882"
                                       : line.indexOf("===") >= 0 ? "#c8a276" : "rgba(210,197,175,.7)";
                              return <div key={i} style={{color:color,whiteSpace:"pre-wrap",wordBreak:"break-all"}}>{line}</div>;
                            })}
                          </div>
                        )}
                        <div className="vplist">
                          {allVoices.length===0 && <div className="vpem">No voices found. Install a Russian voice in system settings.</div>}
                          {(function() {
                            var isRu = function(v) { return v.lang.startsWith("ru")||/katya|katja|milena|yuri/i.test(v.name); };
                            var isMsNatural = function(v) {
                              return /microsoft.*online.*natural/i.test(v.name) || /\(natural\)/i.test(v.name);
                            };
                            // Tier each voice: 0 = local, 1 = Microsoft Online Natural, 2 = other network.
                            var tier = function(v) {
                              if (v.localService) return 0;
                              if (isMsNatural(v)) return 1;
                              return 2;
                            };
                            var byQuality = function(a, b) { return tier(a) - tier(b); };
                            var ruVoices    = allVoices.filter(isRu).slice().sort(byQuality);
                            var otherVoices = allVoices.filter(function(v){ return !isRu(v); }).slice().sort(byQuality);
                            return ruVoices.concat(otherVoices);
                          })()
                            .map(function(v,i){
                              var ru = v.lang.startsWith("ru")||/katya|katja|milena|yuri/i.test(v.name);
                              var network = !v.localService;
                              // Microsoft Edge's Online Natural neural voices are network voices but
                              // they work reliably and sound great — flag them positively, not as a warning.
                              var isMsNatural = /microsoft.*online.*natural/i.test(v.name) || /\(natural\)/i.test(v.name);
                              var labelText, labelColor, rowOpacity;
                              if (!network) {
                                labelText = " · local ✓";
                                labelColor = null;
                                rowOpacity = null;
                              } else if (isMsNatural) {
                                labelText = " · neural ★";
                                labelColor = "#c8a276";
                                rowOpacity = null;
                              } else {
                                labelText = " · network ⚠";
                                labelColor = "#c87a68";
                                rowOpacity = 0.55;
                              }
                              return (
                                <button key={i} className={"vprow"+(voice&&voice.name===v.name?" sel":"")}
                                  style={rowOpacity ? {opacity: rowOpacity} : null}
                                  onClick={function(){
                                    setVoice(v); stopTTS(); setTtsErr("");
                                    // Speak a short test phrase so the user immediately knows if the voice works.
                                    setTimeout(function() {
                                      var u = new SpeechSynthesisUtterance("Привет! Я твой голос.");
                                      u.lang = "ru-RU"; u.voice = v; u.rate = 0.9;
                                      u.onerror = function(e) {
                                        var err = (e && e.error) || "unknown";
                                        if (err !== "interrupted" && err !== "canceled") {
                                          var hint = (network && !isMsNatural) ? " — pick a voice marked « local » or « neural ★ » instead" : "";
                                          setTtsErr("Voice « " + v.name + " » failed: " + err + hint);
                                        }
                                      };
                                      try { window.speechSynthesis.speak(u); }
                                      catch(ex) { setTtsErr("speak() threw: " + (ex.message || ex)); }
                                    }, 80);
                                  }}>
                                  <span className={"vpn"+(ru?" vpnru":"")}>{v.name}</span>
                                  <span className="vpl" style={labelColor ? {color:labelColor} : null}>{v.lang}{labelText}</span>
                                </button>
                              );
                          })}
                        </div>
                      </div>
                    )}

                    <div className="lit-body">
                      <div className="lit-left">
                        <div className="lhdr">Chapter {cidx+1} of {chapters.length} · click any word to define</div>
                        <div className="lch-heading">{curChapter.heading}</div>
                        <div className="ltxt">{renderLit(curChapter.text)}</div>
                      </div>
                      <div className="lit-right">
                        <div className="lit-msgs" ref={msgsRef}>
                          {msgs.map(function(m,i){ return renderMsg(m,i); })}
                          {loading && <div className="msg ai"><div className="typing"><div className="dot"/><div className="dot"/><div className="dot"/></div></div>}
                        </div>
                        <div className="lit-ibar">
                          <textarea ref={inputRef} value={input} onChange={function(e){ setInput(e.target.value); }} onKeyDown={onKey} placeholder="Напиши свой ответ…" disabled={loading}/>
                          <button className="isend" onClick={send} disabled={loading||!input.trim()}>↑</button>
                        </div>
                      </div>
                    </div>

                    <div className="lnav">
                      <button className="lnb" onClick={function(){ navLit(cidx-1); }} disabled={cidx<=0||loading}>← Previous</button>
                      <button className="lbm" onClick={function(){ setCbm(cidx); }}>📌</button>
                      <button className="lnb p" onClick={function(){ navLit(cidx+1); }} disabled={cidx>=chapters.length-1||loading}>Next →</button>
                    </div>
                  </>
                )}

                {lview==="nav" && (
                  <div className="navpanel">
                    {chapters.map(function(ch,i){
                      return (
                        <div key={i} className={"lcard"+(i===cidx?" cur":"")} onClick={function(){ setLview("read"); navLit(i); }}>
                          <div className="lcn">{i+1}{i===cbm?" 📌":""}{i===cidx?" ◀":""}</div>
                          <div className="lchead">{ch.heading}</div>
                          <div className="lcp">{ch.text.slice(0,80)}…</div>
                        </div>
                      );
                    })}
                  </div>
                )}

                {lview==="search" && (
                  <>
                    <div className="lsbar">
                      <input type="text" placeholder={"Search " + (bookMeta.title || "book") + "…"} value={lsearch} onChange={function(e){ setLsearch(e.target.value); }}/>
                    </div>
                    <div className="navpanel">
                      {!lsearch && <div className="lem">Type to search the full text.</div>}
                      {lsearch && !lres.length && <div className="lem">No results for «{lsearch}»</div>}
                      {lres.map(function(i){
                        return (
                          <div key={i} className={"lcard"+(i===cidx?" cur":"")} onClick={function(){ setLsearch(""); setLview("read"); navLit(i); }}>
                            <div className="lcn">{i+1}{i===cbm?" 📌":""}</div>
                            <div className="lchead">{chapters[i].heading}</div>
                            <div className="lcp">{chapters[i].text.slice(0,100)}…</div>
                          </div>
                        );
                      })}
                    </div>
                  </>
                )}
              </div>
            )}

            {started && !isLit && (
              <div className="chat-wrap">
                <div className="msgs">
                  {msgs.map(function(m,i){ return renderMsg(m,i); })}
                  {loading && <div className="msg ai"><div className="typing"><div className="dot"/><div className="dot"/><div className="dot"/></div></div>}
                </div>
                <div className="ibar">
                  <button className="inew" onClick={startChat}>↺ New</button>
                  <textarea ref={inputRef} value={input} onChange={function(e){ setInput(e.target.value); }} onKeyDown={onKey} placeholder="Type in Russian or English…" rows={1} disabled={loading}/>
                  <button className="isend" onClick={send} disabled={loading||!input.trim()}>↑</button>
                </div>
              </div>
            )}
          </div>
        )}

        {tab==="vocab" && (
          <div className="panel">
            <div className="phdr"><span className="pti">My Vocabulary</span><button className="ab" onClick={function(){ setNRu(""); setNEn(""); setShowWord(true); }}>+ Add word</button></div>
            {vocab.length===0 ? <p className="empty">No words saved yet.<br/>Click any Russian word to define and save it.</p>
              : <div className="ilist">{vocab.map(function(v){
                var posLine = [v.pos, v.aspect].filter(Boolean).join(" · ");
                return (
                  <div key={v.id} className="icard">
                    <div className="icont">
                      <span className="ipri">{v.ru}</span>
                      {posLine && <span className="ipos">{posLine}</span>}
                      {v.en && <span className="isec">{v.en}</span>}
                      {v.grammar && <span className="igr">{v.grammar}</span>}
                      {v.example && (
                        <div className="iex">
                          «&nbsp;{v.example}&nbsp;»
                          {v.exampleTranslation && <div className="iext">{v.exampleTranslation}</div>}
                        </div>
                      )}
                    </div>
                    <button className="rmb" title="Remove from vocabulary" onClick={function(){ setVocab(function(p){ return p.filter(function(x){ return x.id!==v.id; }); }); }}>×</button>
                  </div>
                );
              })}</div>}
          </div>
        )}

        {tab==="grammar" && (
          <div className="panel">
            <div className="phdr"><span className="pti">Grammar Tips</span><button className="ab g" onClick={function(){ setNTip(""); setShowTip(true); }}>+ Add tip</button></div>
            {tips.length===0 ? <p className="empty">No tips saved yet.<br/>Click 📝 Save tip under any tutor message.</p>
              : <div className="ilist">{tips.map(function(t){
                return (
                  <div key={t.id} className="icard">
                    <div className="icont"><span className="ipri" style={{fontSize:15}}>📝 {t.tip}</span></div>
                    <button className="rmb" onClick={function(){ setTips(function(p){ return p.filter(function(x){ return x.id!==t.id; }); }); }}>×</button>
                  </div>
                );
              })}</div>}
          </div>
        )}

        {showTopic && (
          <div className="mover" onClick={function(){ setShowTopic(false); }}>
            <div className="modal" onClick={function(e){ e.stopPropagation(); }}>
              <span className="mti">{isLit ? ("📖 " + (bookMeta.title || "Reading")) : "💬 Change Topic"}</span>
              {!isLit && (
                <>
                  <select value={topic} onChange={function(e){ setTopic(e.target.value); setCustom(""); }}>
                    {TOPICS.map(function(t){ return <option key={t}>{t}</option>; })}
                  </select>
                  <input type="text" placeholder="Or a custom topic…" value={custom} onChange={function(e){ setCustom(e.target.value); }}/>
                </>
              )}
              <div className="mact">
                <button className="mcanc" onClick={function(){ setShowTopic(false); }}>Cancel</button>
                {!isLit && <button className="mconf" onClick={function(){ setShowTopic(false); setStarted(false); setMsgs([]); stopTTS(); }}>Switch topic</button>}
                <button className="mconf" onClick={function(){ setShowTopic(false); setStarted(false); setMode(""); setMsgs([]); stopTTS(); }}>← Back to start</button>
              </div>
            </div>
          </div>
        )}

        {showWord && (
          <div className="mover" onClick={function(){ setShowWord(false); }}>
            <div className="modal" onClick={function(e){ e.stopPropagation(); }}>
              <span className="mti">Add Word</span>
              <input type="text" placeholder="Russian word" value={nRu} onChange={function(e){ setNRu(e.target.value); }}/>
              <input type="text" placeholder="English translation (optional)" value={nEn} onChange={function(e){ setNEn(e.target.value); }}/>
              <div className="mact">
                <button className="mcanc" onClick={function(){ setShowWord(false); }}>Cancel</button>
                <button className="mconf" onClick={function(){ if(nRu.trim()) addV(nRu.trim(),nEn.trim()); setShowWord(false); }}>Save</button>
              </div>
            </div>
          </div>
        )}

        {showTip && (
          <div className="mover" onClick={function(){ setShowTip(false); }}>
            <div className="modal" onClick={function(e){ e.stopPropagation(); }}>
              <span className="mti">Add Grammar Tip</span>
              <input type="text" placeholder="e.g. Genitive case after negation" value={nTip} onChange={function(e){ setNTip(e.target.value); }}/>
              <div className="mact">
                <button className="mcanc" onClick={function(){ setShowTip(false); }}>Cancel</button>
                <button className="mconf g" onClick={function(){ if(nTip.trim()) addT(nTip.trim()); setShowTip(false); }}>Save</button>
              </div>
            </div>
          </div>
        )}

        {popup && (
          <div className="pover" onClick={function(){ setPopup(null); }}>
            <div className="pop" ref={popRef} style={{top:popXY.top,left:popXY.left,width:Math.min(280,window.innerWidth-32)}} onClick={function(e){ e.stopPropagation(); }}>
              <button className="pcl" onClick={function(){ setPopup(null); }}>×</button>

              {/* Header shows the canonical form once data has loaded.
                   Pre-load (or on error) we show what the user clicked. */}
              {(function() {
                var entry = formatVocabEntry(popup.data, popup.word);
                var headline = entry.ru || popup.word;
                var clicked = (popup.word || "").trim();
                var lemma = popup.data && popup.data.lemma;
                var showClickedHint = !!(lemma && clicked && lemma !== clicked && !(/\s\/\s/.test(headline)));
                return (
                  <>
                    <div className="pw">{headline}</div>
                    {showClickedHint && (
                      <div style={{fontSize:11,color:"rgba(210,197,175,.4)",marginBottom:6,marginTop:-2}}>
                        you clicked: {clicked}
                      </div>
                    )}
                  </>
                );
              })()}

              {popup.loading && <div className="pload">Looking up…</div>}
              {popup.error && <div className="perr">{popup.error}</div>}

              {popup.yo && (
                <div style={{display:"flex",flexDirection:"column",gap:4,marginTop:8}}>
                  <div className="ppos" style={{marginBottom:8}}>е or ё? Tap the right spelling:</div>
                  <button className="yobtn" onClick={function(){ defWithYo(popup.yo.orig); }}>{popup.yo.orig} (keep е)</button>
                  {popup.yo.vars.map(function(v,i){ return <button key={i} className="yobtn" onClick={function(){ defWithYo(v); }}>{v} (with ё)</button>; })}
                </div>
              )}

              {!popup.loading && !popup.error && !popup.yo && popup.data && (
                <>
                  <div className="ppos">{popup.data.partOfSpeech}{popup.data.aspect ? " · " + popup.data.aspect : ""}</div>
                  <div className="ptr">{popup.data.translation}</div>
                  {popup.data.grammar && <div className="pgr">{popup.data.grammar}</div>}
                  {popup.data.example && <div className="pex">{popup.data.example}{popup.data.exampleTranslation&&<div className="pext">{popup.data.exampleTranslation}</div>}</div>}
                </>
              )}

              {/* Save uses the formatted entry: nominative for nouns, infinitive (with aspect pair) for verbs.
                   Also persists pos/grammar/example into the vocab list. */}
              {(function() {
                var entry = formatVocabEntry(popup.data, popup.word);
                return (
                  <button className="psave" onClick={function(){
                    if (entry.ru) addV(entry);
                    setPopup(null);
                  }}>+ Save « {entry.ru || popup.word} » to vocabulary</button>
                );
              })()}
            </div>
          </div>
        )}
      </div>
      </SignedIn>
    </>
  );
}
