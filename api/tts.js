// Azure Speech Service Text-to-Speech endpoint.
//
// Used to provide high-quality Russian neural voices (Dariya, Dmitry, Svetlana)
// to any browser, including iOS Safari where the WebSpeech API only exposes
// the robotic compact Milena voice. The frontend POSTs text + voice name and
// gets back an MP3 audio stream that it plays via <audio> — bypassing the
// browser's built-in TTS entirely.
//
// Required environment variables on Vercel:
//   AZURE_SPEECH_KEY     — the Cognitive Services subscription key
//   AZURE_SPEECH_REGION  — e.g. "eastus", "westeurope" (region your resource was provisioned in)
//
// Cost: ~$16 per 1M characters for neural voices on Azure's Pay-As-You-Go tier.
// Free tier: 500k characters/month neural.

const ALLOWED_VOICES = {
  "ru-RU-DariyaNeural": true,
  "ru-RU-DmitryNeural": true,
  "ru-RU-SvetlanaNeural": true,
};

function escapeXml(s) {
  return String(s)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&apos;");
}

// Russian typography customarily drops the ё diacritic, writing the letter as
// plain "е" — but the pronunciation still requires "yo". Restore ё to the TTS
// payload only (book text on screen stays unchanged). Two passes:
//
//   1. Static word list: words where ё is virtually always correct regardless
//      of context (е.g. "еще" → "ещё", "идет" → "идёт", "черный" → "чёрный").
//      Extend the YO_RESTORATION table below as you find missing words.
//
//   2. Grammar-aware pattern: "Все/все" + neuter past-tense verb (ending in
//      -ло or -лось within a few words) implies neuter singular "Всё/всё"
//      rather than plural "Все". Example: "Все смешалось" → "Всё смешалось"
//      because "смешалось" is neuter past; if the verb were "смешались"
//      (plural), no substitution would happen.
//
// Run BEFORE yoFix() so any restored ё's get phonetic-spelled too.

const YO_RESTORATION = {
  // — Adverbs / particles ————————————————————————————————
  "еще": "ещё", "Еще": "Ещё", "ЕЩЕ": "ЕЩЁ",
  "ее": "её", "Ее": "Её",  // feminine accusative/genitive pronoun "her" — always ё in speech

  // — Common 3rd-person verb forms (-ёт / -ёшь / -ём / -ёте) ——————————————
  "идет": "идёт", "Идет": "Идёт",
  "идешь": "идёшь",
  "идем": "идём",
  "идете": "идёте",
  "несет": "несёт", "Несет": "Несёт",
  "несешь": "несёшь",
  "несем": "несём",
  "везет": "везёт", "Везет": "Везёт",
  "везешь": "везёшь",
  "ведет": "ведёт", "Ведет": "Ведёт",
  "ведешь": "ведёшь",
  "поведет": "поведёт",
  "найдет": "найдёт", "Найдет": "Найдёт",
  "найдешь": "найдёшь",
  "найдем": "найдём",
  "придет": "придёт", "Придет": "Придёт",
  "придешь": "придёшь",
  "пойдет": "пойдёт", "Пойдет": "Пойдёт",
  "пойдешь": "пойдёшь",
  "уйдет": "уйдёт",
  "войдет": "войдёт",
  "сойдет": "сойдёт",
  "зайдет": "зайдёт",
  "зовет": "зовёт", "Зовет": "Зовёт",
  "зовешь": "зовёшь",
  "лжет": "лжёт",
  "льет": "льёт",
  "бьет": "бьёт",
  "пьет": "пьёт",
  "поет": "поёт", "Поет": "Поёт",
  "поешь": "поёшь",
  "берет": "берёт", "Берет": "Берёт",  // also a hat — collision possible but rare
  "берешь": "берёшь",
  "берем": "берём",
  "плетет": "плетёт",
  "метет": "метёт",
  "сметет": "сметёт",
  "цветет": "цветёт",
  "печет": "печёт",
  "течет": "течёт",
  "стережет": "стережёт",

  // — Past tense masculine (-ёл / -ёс / -ёз / -ёг) ——————————————
  "шел": "шёл", "Шел": "Шёл",
  "пошел": "пошёл", "Пошел": "Пошёл",
  "пришел": "пришёл", "Пришел": "Пришёл",
  "ушел": "ушёл", "Ушел": "Ушёл",
  "нашел": "нашёл", "Нашел": "Нашёл",
  "зашел": "зашёл",
  "вошел": "вошёл",
  "сошел": "сошёл",
  "обошел": "обошёл",
  "перешел": "перешёл",
  "вел": "вёл", "Вел": "Вёл",
  "повел": "повёл",
  "увел": "увёл",
  "привел": "привёл",
  "нес": "нёс", "Нес": "Нёс",
  "понес": "понёс",
  "привез": "привёз",
  "увез": "увёз",
  "приобрел": "приобрёл",

  // — Adjectives (most common stems) ——————————————
  "черный": "чёрный", "Черный": "Чёрный",
  "черная": "чёрная", "Черная": "Чёрная",
  "черное": "чёрное", "Черное": "Чёрное",
  "черные": "чёрные", "Черные": "Чёрные",
  "черного": "чёрного", "черному": "чёрному", "черным": "чёрным",
  "черной": "чёрной", "черных": "чёрных", "черном": "чёрном", "черными": "чёрными",
  "темный": "тёмный", "Темный": "Тёмный",
  "темная": "тёмная", "темное": "тёмное", "темные": "тёмные",
  "темного": "тёмного", "темной": "тёмной", "темном": "тёмном",
  "темнота": "темнота",  // no ё in this form
  "теплый": "тёплый", "Теплый": "Тёплый",
  "теплая": "тёплая", "теплое": "тёплое", "теплые": "тёплые",
  "теплого": "тёплого", "теплой": "тёплой", "теплом": "тёплом",
  "легкий": "лёгкий", "Легкий": "Лёгкий",
  "легкая": "лёгкая", "легкое": "лёгкое", "легкие": "лёгкие",
  "легкого": "лёгкого", "легкой": "лёгкой",
  "тяжелый": "тяжёлый", "Тяжелый": "Тяжёлый",
  "тяжелая": "тяжёлая", "тяжелое": "тяжёлое", "тяжелые": "тяжёлые",
  "тяжелого": "тяжёлого", "тяжелой": "тяжёлой",
  "твердый": "твёрдый", "Твердый": "Твёрдый",
  "твердая": "твёрдая", "твердое": "твёрдое", "твердые": "твёрдые",
  "мертвый": "мёртвый", "Мертвый": "Мёртвый",
  "мертвая": "мёртвая", "мертвое": "мёртвое", "мертвые": "мёртвые",
  "веселый": "весёлый", "Веселый": "Весёлый",
  "веселая": "весёлая", "веселое": "весёлое", "веселые": "весёлые",

  // — Common nouns ——————————————
  "ребенок": "ребёнок", "Ребенок": "Ребёнок",
  "ребенка": "ребёнка",
  "ребенку": "ребёнку",
  "ребенком": "ребёнком",
  "сестры": "сёстры", "Сестры": "Сёстры",
  "сестрам": "сёстрам",
  "сестрами": "сёстрами",
  "сестрах": "сёстрах",
  "тетя": "тётя", "Тетя": "Тётя",
  "тетка": "тётка",
  "ежик": "ёжик", "Ежик": "Ёжик",
  "ежика": "ёжика",
  "елка": "ёлка", "Елка": "Ёлка",
  "елки": "ёлки",
  "клен": "клён",
  "клена": "клёна",
  "лед": "лёд",      // nominative only — oblique cases lose ё via stress shift
  "слезы": "слёзы",  // nominative plural of "слеза"
  "слез": "слёз",    // genitive plural
  "клест": "клёст",
  "костер": "костёр", "Костер": "Костёр",

  // — Common professional/agentive nouns in -ёр ——————————————
  "актер": "актёр", "Актер": "Актёр",
  "актеры": "актёры",
  "актеров": "актёров",
  "режиссер": "режиссёр", "Режиссер": "Режиссёр",
  "режиссеры": "режиссёры",
  "монтер": "монтёр",
  "шофер": "шофёр",

  // — Family of words around "идти/идущий" ——————————————
  "идущий": "идущий",  // no ё — stress is elsewhere
};

// Pre-build a single regex from the keys for efficiency. Sort by length so
// longer matches win when alternates overlap ("придет" before "идет").
const YO_KEYS = Object.keys(YO_RESTORATION).sort(function(a, b){ return b.length - a.length; });
// Russian word-boundary: preceded by start-of-string OR a non-Cyrillic-letter,
// followed by a non-Cyrillic-letter or end-of-string.
const YO_REGEX = new RegExp(
  "(^|[^а-яёА-ЯЁ])(" + YO_KEYS.join("|") + ")(?=[^а-яёА-ЯЁ]|$)",
  "g"
);

function restoreYo(text) {
  if (!text) return text;

  // 1. Static word substitutions
  text = text.replace(YO_REGEX, function(_, prefix, word) {
    return prefix + YO_RESTORATION[word];
  });

  // 2. Grammar-aware: "Все"/"все" + neuter past verb (-ло/-лось within ~3 words) → "Всё"/"всё"
  // Captures the leading context char so we don't accidentally match inside another word.
  text = text.replace(
    /(^|[^а-яёА-ЯЁ])([Вв])се(?=\s+(?:[а-яёА-ЯЁ]+\s+){0,3}[а-яёА-ЯЁ]+(?:лось|ло)(?:[^а-яёА-ЯЁ]|$))/g,
    function(_, prefix, v) {
      return prefix + v + "сё";
    }
  );

  return text;
}

// Azure's Russian neural voices have a known bug where they pronounce "ё" as
// plain "е", losing the "yo" sound. Workaround: substitute "ё" with a
// pronunciation-equivalent spelling before generating SSML. The user's book
// text on screen is untouched — only the audio payload is mangled.
//
// Russian phonetics:
//   - "ё" after a consonant  → consonant softens, vowel is "o".
//                              Phonetic spelling: <consonant>ьо
//                              (e.g. пёс → пьос, лёд → льод, тётя → тьотя)
//   - "ё" at word start or after a vowel / ь / ъ / whitespace
//                            → full "yo" diphthong.
//                              Phonetic spelling: йо
//                              (e.g. ёж → йож, приёмник → прийомник)
function yoFix(text) {
  if (!text) return text;
  return text.replace(/ё/gi, function(match, offset, str) {
    var isUpper = match === "Ё";
    var prev = offset > 0 ? str[offset - 1] : "";
    var afterVowelOrBoundary = !prev || /[аеиоуыэюяьъАЕИОУЫЭЮЯЬЪ\s.,;:!?"'«»()—–\-]/.test(prev);
    if (afterVowelOrBoundary) {
      // Word start, after vowel, after ь/ъ, or after whitespace/punctuation.
      return isUpper ? "Йо" : "йо";
    }
    // After a consonant — soften it with ь and use plain о.
    return isUpper ? "Ьо" : "ьо";
  });
}

export default async function handler(req, res) {
  if (req.method !== "POST") {
    res.setHeader("Allow", "POST");
    return res.status(405).json({ error: "Method not allowed" });
  }

  // Read env vars and validate. Trim in case the user pasted with whitespace.
  const key = (process.env.AZURE_SPEECH_KEY || "").trim();
  const region = (process.env.AZURE_SPEECH_REGION || "").trim().toLowerCase();

  if (!key) {
    return res.status(500).json({
      error: "AZURE_SPEECH_KEY is not set",
      hint: "Add it under Vercel → Settings → Environment Variables, then redeploy.",
    });
  }
  if (!region) {
    return res.status(500).json({
      error: "AZURE_SPEECH_REGION is not set",
      hint: "Add it under Vercel → Settings → Environment Variables, then redeploy. Example values: eastus, westus2, westeurope.",
    });
  }
  // Sanity check region format — must be a single token of letters/digits.
  if (!/^[a-z0-9]+$/i.test(region)) {
    return res.status(500).json({
      error: "AZURE_SPEECH_REGION looks malformed",
      regionGot: region,
      hint: "Expected a single region token like 'eastus' — not a URL or display name.",
    });
  }

  // Defensive body parsing: Vercel usually parses JSON when Content-Type is
  // application/json, but if a client sends raw text, req.body may be a string.
  let body = req.body;
  if (typeof body === "string") {
    try { body = JSON.parse(body); } catch (e) { body = {}; }
  }
  body = body || {};

  const text = typeof body.text === "string" ? body.text : "";
  const voice = typeof body.voice === "string" && ALLOWED_VOICES[body.voice]
    ? body.voice
    : "ru-RU-DariyaNeural";
  const ratePct = typeof body.rate === "number" ? Math.max(-50, Math.min(50, body.rate)) : -8;

  if (!text.trim()) {
    return res.status(400).json({ error: "text is required" });
  }
  if (text.length > 5000) {
    return res.status(400).json({ error: "text too long (max 5000 chars per request)" });
  }

  const ssml = `<speak version="1.0" xml:lang="ru-RU" xmlns="http://www.w3.org/2001/10/synthesis">
<voice name="${voice}">
<prosody rate="${ratePct >= 0 ? "+" : ""}${ratePct}%">${escapeXml(yoFix(restoreYo(text)))}</prosody>
</voice>
</speak>`;

  const endpoint = `https://${region}.tts.speech.microsoft.com/cognitiveservices/v1`;

  try {
    const azureResp = await fetch(endpoint, {
      method: "POST",
      headers: {
        "Ocp-Apim-Subscription-Key": key,
        "Content-Type": "application/ssml+xml",
        "X-Microsoft-OutputFormat": "audio-24khz-48kbitrate-mono-mp3",
        "User-Agent": "Govorim/1.0",
      },
      body: ssml,
    });

    if (!azureResp.ok) {
      let errText = "";
      try { errText = await azureResp.text(); } catch (e) {}
      console.error("[tts] Azure rejected:", azureResp.status, errText.slice(0, 500));

      // Surface common error causes with targeted hints.
      let hint = "";
      if (azureResp.status === 401) {
        hint = "Azure rejected the subscription key (401 Unauthorized). Verify AZURE_SPEECH_KEY is correct — copy KEY 1 (or KEY 2) from the 'Keys and Endpoint' page of your Speech resource. Make sure there's no extra whitespace.";
      } else if (azureResp.status === 403) {
        hint = "Azure rejected with 403 Forbidden. Common causes: (1) the Speech resource is suspended or its free tier quota is exhausted, (2) the key belongs to a different Azure resource type (must be a Speech / Cognitive Services Speech resource, not a generic Cognitive Services key), (3) the resource is in a different region than AZURE_SPEECH_REGION.";
      } else if (azureResp.status === 404) {
        hint = "Azure endpoint not found (404). AZURE_SPEECH_REGION is probably wrong. Check 'Keys and Endpoint' in the Azure portal — the 'Location/Region' field tells you the correct value (e.g., eastus, westeurope).";
      } else if (azureResp.status === 429) {
        hint = "Azure rate limit (429). Wait a moment or upgrade from the free tier.";
      } else if (azureResp.status >= 500) {
        hint = "Azure server error — try again in a moment.";
      }

      return res.status(502).json({
        error: "Azure TTS request failed",
        azureStatus: azureResp.status,
        azureDetail: errText.slice(0, 300),
        region: region,
        hint: hint,
      });
    }

    const audioBuffer = Buffer.from(await azureResp.arrayBuffer());
    if (!audioBuffer.length) {
      return res.status(502).json({ error: "Azure returned empty audio" });
    }

    res.setHeader("Content-Type", "audio/mpeg");
    res.setHeader("Content-Length", audioBuffer.length);
    res.setHeader("Cache-Control", "public, max-age=3600, s-maxage=3600");
    res.status(200).send(audioBuffer);
  } catch (e) {
    console.error("[tts] handler exception:", e);
    return res.status(500).json({
      error: e && e.message ? e.message : "TTS failed",
      stack: process.env.NODE_ENV === "development" ? (e && e.stack) : undefined,
    });
  }
}
