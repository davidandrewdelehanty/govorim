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
// Azure Translator F0: 2,000,000 characters/month, no card, and it returns an
// error rather than a bill when exhausted. A Russian word is ~8 characters, so
// that is roughly 250,000 lookups a month.
//
// Env vars on Vercel:
//   AZURE_TRANSLATOR_KEY      — from the Translator resource's Keys and Endpoint
//   AZURE_TRANSLATOR_REGION   — e.g. "westeurope"; "global" works for a global resource
// Optional:
//   MT_FALLBACK=0             — switch this tier off entirely
//
// The shape here is provider-agnostic on purpose: adding DeepL or MyMemory
// later means one more lookup function and a branch in mtLookup, not a rewrite.

const AZURE_HOST = "https://api.cognitive.microsofttranslator.com";

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

// Try the candidates in order — the clicked form, the ё-folded form, and the
// lemma the search step resolved. The lemma usually wins here: MT handles a
// dictionary form far better than an oblique case of a rare noun.
export async function mtLookup(candidates, clickedWord, signal) {
  if (process.env.MT_FALLBACK === "0") return null;
  if (!azureConfigured()) return null;

  for (const cand of candidates) {
    let hit = null;
    try {
      hit = await azureDictionary(cand, signal);
    } catch (e) {
      if (e && e.name === "AbortError") throw e;
      // A key or quota problem will fail the translate call too — stop here
      // rather than spending the rest of the request budget on it.
      if (e.azureStatus === 401 || e.azureStatus === 403 || e.azureStatus === 429) throw e;
    }
    if (!hit) {
      try {
        hit = await azureTranslate(cand, signal);
      } catch (e) {
        if (e && e.name === "AbortError") throw e;
        throw e;
      }
    }
    if (!hit) continue;

    const bits = [];
    if (hit.kind === "dictionary") {
      if (hit.confidence) bits.push("confidence " + Math.round(hit.confidence * 100) + "%");
      if (hit.backTranslations && hit.backTranslations.length) {
        bits.push("back-translates as " + hit.backTranslations.join(", "));
      }
    }
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
      mtProvider: "Microsoft Translator",
      sourceUrl: "",
    };
  }
  return null;
}
