// Machine-translation tier — the last thing tried, after Yandex, both
// Wiktionaries and the жаргон glossary have all declined a word.
//
// Everything that reaches here is rare, archaic or slang: precisely the
// vocabulary where a translation engine is least reliable and most confident.
// So this tier is built to be honest about itself rather than accurate:
//   - Azure's DICTIONARY LOOKUP endpoint is tried first. It is a real bilingual
//     dictionary — part of speech, confidence scores, back-translations — and
//     is a different quality of answer from raw MT.
//   - Only if that has no entry does it fall back to translating the word,
//     which is a guess and is labelled as one.
// Both live in the same free allowance.
//
// Two providers, chosen by whichever key is configured:
//
//   DeepL API Free — 500,000 chars/month, no card. The best ru→en of the free
//     options by a clear margin, which matters most here: everything reaching
//     this tier is literary, archaic or slang. Translation only — DeepL has no
//     bilingual-dictionary endpoint.
//   Azure Translator F0 — 2,000,000 chars/month, no card. Weaker prose, but its
//     dictionary-lookup endpoint returns real entries with part of speech,
//     confidence and back-translations, which is a better kind of answer.
//
// A Russian word is ~8 characters, so even DeepL's smaller allowance is around
// 60,000 lookups a month on a tier that only fires when four dictionaries have
// already declined the word.
//
//   MyMemory — no account, no key, no card. 5,000 chars/day anonymous, 50,000
//     if an email is supplied. Weakest of the three and translation-only, but
//     it needs no signup at all, so it is the default when nothing is
//     configured: the tier works out of the box and can be upgraded later by
//     setting one env var.
//
// Env vars on Vercel — set the pair for whichever provider you use, or none:
//   DEEPL_API_KEY             — from deepl.com/your-account/keys (free keys end ":fx")
//   AZURE_TRANSLATOR_KEY      — from the Translator resource's Keys and Endpoint
//   AZURE_TRANSLATOR_REGION   — e.g. "eastus"; omit for a global resource
//   MYMEMORY_EMAIL            — raises MyMemory's cap from 5k to 50k chars/day
// Optional:
//   MT_PROVIDER=deepl|azure|mymemory — force one; otherwise the best configured
//                                      provider is used, falling back to MyMemory
//   MT_FALLBACK=0             — switch this tier off entirely

const AZURE_HOST = "https://api.cognitive.microsofttranslator.com";

function chosenProvider() {
  const forced = (process.env.MT_PROVIDER || "").trim().toLowerCase();
  if (forced) return forced;
  if (process.env.DEEPL_API_KEY) return "deepl";
  if (process.env.AZURE_TRANSLATOR_KEY) return "azure";
  return "mymemory";                 // needs no key, so the tier always works
}

function azureConfigured() {
  return !!process.env.AZURE_TRANSLATOR_KEY;
}

function azureHeaders() {
  const h = {
    "Ocp-Apim-Subscription-Key": process.env.AZURE_TRANSLATOR_KEY,
    "Content-Type": "application/json",
  };
  // Required for a regional resource; harmless for a global one.
  const region = process.env.AZURE_TRANSLATOR_REGION;
  if (region && region !== "global") h["Ocp-Apim-Subscription-Region"] = region;
  return h;
}

async function azurePost(pathAndQuery, body, signal) {
  const resp = await fetch(AZURE_HOST + pathAndQuery, {
    method: "POST",
    signal,
    headers: azureHeaders(),
    body: JSON.stringify(body),
  });
  if (!resp.ok) {
    let detail = "";
    try {
      const j = await resp.json();
      detail = (j && j.error && j.error.message) ? " — " + j.error.message : "";
    } catch (_) { /* body may not be JSON */ }
    const err = new Error("Azure Translator HTTP " + resp.status + detail);
    err.azureStatus = resp.status;
    throw err;
  }
  return resp.json();
}

// Azure's bilingual dictionary. Returns real entries with a part of speech and
// a confidence, plus back-translations that show what each sense would return
// going the other way — a useful sanity signal for a word this deep in the stack.
async function azureDictionary(word, signal) {
  const data = await azurePost(
    "/dictionary/lookup?api-version=3.0&from=ru&to=en",
    [{ Text: word }],
    signal
  );
  const first = Array.isArray(data) ? data[0] : null;
  const translations = (first && Array.isArray(first.translations)) ? first.translations : [];
  if (!translations.length) return null;

  const ranked = translations.slice().sort(function (a, b) {
    return (b.confidence || 0) - (a.confidence || 0);
  });
  const top = ranked.slice(0, 4);

  const backs = [];
  for (const t of ranked.slice(0, 2)) {
    for (const b of (Array.isArray(t.backTranslations) ? t.backTranslations : []).slice(0, 3)) {
      const w = (b.displayText || b.normalizedText || "").trim();
      if (w && w.toLowerCase() !== word.toLowerCase() && backs.indexOf(w) === -1) backs.push(w);
    }
  }

  return {
    kind: "dictionary",
    lemma: first.normalizedSource || word,
    partOfSpeech: (top[0].posTag || "").toLowerCase(),
    translation: top.map(function (t) { return t.displayTarget || t.normalizedTarget; })
                    .filter(Boolean).join(", "),
    confidence: top[0].confidence || 0,
    backTranslations: backs.slice(0, 5),
  };
}

async function azureTranslate(word, signal) {
  const data = await azurePost(
    "/translate?api-version=3.0&from=ru&to=en",
    [{ Text: word }],
    signal
  );
  const first = Array.isArray(data) ? data[0] : null;
  const t = first && Array.isArray(first.translations) ? first.translations[0] : null;
  const text = t && String(t.text || "").trim();
  if (!text) return null;
  // A translator handed a word it doesn't know often echoes it back, or returns
  // a transliteration. That is not an answer worth showing.
  if (text.toLowerCase() === word.toLowerCase()) return null;
  if (!/[a-z]/i.test(text)) return null;
  return { kind: "translation", lemma: word, partOfSpeech: "", translation: text };
}

// ---- DeepL ----------------------------------------------------------------
// Free keys end in ":fx" and MUST go to api-free.deepl.com; a Pro key on that
// host (or a free key on the Pro host) returns 403, which is a confusing way to
// discover you used the wrong subdomain. Detect it from the key instead.

function deeplHost() {
  const key = process.env.DEEPL_API_KEY || "";
  return /:fx$/.test(key.trim()) ? "https://api-free.deepl.com" : "https://api.deepl.com";
}

async function deeplTranslate(word, signal) {
  const resp = await fetch(deeplHost() + "/v2/translate", {
    method: "POST",
    signal,
    headers: {
      "Authorization": "DeepL-Auth-Key " + (process.env.DEEPL_API_KEY || "").trim(),
      "Content-Type": "application/json",
    },
    body: JSON.stringify({ text: [word], source_lang: "RU", target_lang: "EN-US" }),
  });

  if (!resp.ok) {
    let detail = "";
    if (resp.status === 403) detail = " — key rejected (check DEEPL_API_KEY, and that a ':fx' free key is not pointed at the Pro host)";
    else if (resp.status === 456) detail = " — monthly character quota exhausted";
    else if (resp.status === 429) detail = " — too many requests";
    const err = new Error("DeepL HTTP " + resp.status + detail);
    err.deeplStatus = resp.status;
    throw err;
  }

  const data = await resp.json();
  const t = data && Array.isArray(data.translations) ? data.translations[0] : null;
  const text = t && String(t.text || "").trim();
  if (!text) return null;
  // A word the engine doesn't know often comes back unchanged, or as a
  // transliteration. Neither is an answer worth showing.
  if (text.toLowerCase() === word.toLowerCase()) return null;
  if (!/[a-z]/i.test(text)) return null;
  return { kind: "translation", lemma: word, partOfSpeech: "", translation: text };
}

// ---- MyMemory --------------------------------------------------------------
// A translation-memory service with an open endpoint. It answers with the best
// matching segment rather than a fresh translation, so quality varies a lot —
// but this is the sixth tier, reached only when four dictionaries have already
// declined the word, and a rough gloss beats a dead end.
//
// Two failure modes worth handling explicitly: the daily cap is reported as a
// WARNING inside the translated text rather than an HTTP error, and an unknown
// word comes back unchanged.

async function myMemoryTranslate(word, signal) {
  const params = new URLSearchParams({ q: word, langpair: "ru|en" });
  const email = (process.env.MYMEMORY_EMAIL || "").trim();
  if (email) params.set("de", email);       // raises the cap from 5k to 50k chars/day

  const resp = await fetch("https://api.mymemory.translated.net/get?" + params.toString(), {
    signal,
    headers: { accept: "application/json" },
  });
  if (!resp.ok) {
    const err = new Error("MyMemory HTTP " + resp.status);
    err.myMemoryStatus = resp.status;
    throw err;
  }

  const data = await resp.json();
  const rd = data && data.responseData;
  const text = rd && String(rd.translatedText || "").trim();
  if (!text) return null;

  // The quota message arrives as the translation itself, with HTTP 200.
  if (/MYMEMORY WARNING|ALL AVAILABLE FREE TRANSLATIONS/i.test(text)) {
    const err = new Error("MyMemory daily quota exhausted" +
      (email ? "" : " — set MYMEMORY_EMAIL to raise the cap to 50k chars/day"));
    err.myMemoryStatus = 429;
    throw err;
  }
  if (text.toLowerCase() === word.toLowerCase()) return null;
  if (!/[a-z]/i.test(text)) return null;

  // MyMemory shouts a lot of its memory segments.
  const tidy = text === text.toUpperCase() ? text.toLowerCase() : text;
  const match = typeof rd.match === "number" ? rd.match : null;
  return {
    kind: "translation",
    lemma: word,
    partOfSpeech: "",
    translation: tidy,
    matchScore: match,
  };
}

// Try the candidates in order — the clicked form, the ё-folded form, and the
// lemma the search step resolved. The lemma usually wins here: MT handles a
// dictionary form far better than an oblique case of a rare noun.
export async function mtLookup(candidates, clickedWord, signal) {
  if (process.env.MT_FALLBACK === "0") return null;
  const provider = chosenProvider();
  if (provider === "deepl" && !process.env.DEEPL_API_KEY) return null;
  if (provider === "azure" && !azureConfigured()) return null;
  if (!provider) return null;

  const providerName = provider === "deepl" ? "DeepL"
    : provider === "azure" ? "Microsoft Translator"
    : "MyMemory";

  for (const cand of candidates) {
    let hit = null;

    if (provider === "deepl") {
      hit = await deeplTranslate(cand, signal);
    } else if (provider === "mymemory") {
      hit = await myMemoryTranslate(cand, signal);
    } else {
      try {
        hit = await azureDictionary(cand, signal);
      } catch (e) {
        if (e && e.name === "AbortError") throw e;
        // A key or quota problem will fail the translate call too — stop here
        // rather than spending the rest of the request budget on it.
        if (e.azureStatus === 401 || e.azureStatus === 403 || e.azureStatus === 429) throw e;
      }
      if (!hit) hit = await azureTranslate(cand, signal);
    }

    if (!hit) continue;

    const bits = [];
    if (hit.kind === "dictionary") {
      if (hit.confidence) bits.push("confidence " + Math.round(hit.confidence * 100) + "%");
      if (hit.backTranslations && hit.backTranslations.length) {
        bits.push("back-translates as " + hit.backTranslations.join(", "));
      }
    }
    if (typeof hit.matchScore === "number") bits.push("match " + Math.round(hit.matchScore * 100) + "%");
    if (cand !== clickedWord.toLowerCase()) bits.push("looked up as " + cand);

    return {
      word: clickedWord,
      lemma: hit.lemma || cand,
      matchedForm: cand,
      partOfSpeech: hit.partOfSpeech || "",
      aspect: "",
      aspectPair: "",
      translation: hit.translation,
      definitionRu: "",
      grammar: bits.join(" · "),
      example: "",
      exampleTranslation: "",
      definitionSource: "mt",
      mtKind: hit.kind,                       // "dictionary" | "translation"
      mtProvider: providerName,
      sourceUrl: "",
    };
  }
  return null;
}
