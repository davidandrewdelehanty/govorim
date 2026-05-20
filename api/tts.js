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
<prosody rate="${ratePct >= 0 ? "+" : ""}${ratePct}%">${escapeXml(text)}</prosody>
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
