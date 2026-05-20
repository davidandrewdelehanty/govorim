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
//   AZURE_SPEECH_REGION  — e.g. "eastus", "westeurope" (the region you provisioned in)
//
// Cost: ~$4 per 1M characters for neural voices on Azure's Pay-As-You-Go tier.
// Average chat response = ~200 chars = $0.0008. Free tier: 500k chars/month.

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

  const key = process.env.AZURE_SPEECH_KEY;
  const region = process.env.AZURE_SPEECH_REGION;
  if (!key || !region) {
    return res.status(500).json({
      error: "Azure Speech is not configured. Set AZURE_SPEECH_KEY and AZURE_SPEECH_REGION in Vercel env vars.",
    });
  }

  const body = req.body || {};
  const text = typeof body.text === "string" ? body.text : "";
  const voice = typeof body.voice === "string" && ALLOWED_VOICES[body.voice]
    ? body.voice
    : "ru-RU-DariyaNeural";
  const ratePct = typeof body.rate === "number" ? Math.max(-50, Math.min(50, body.rate)) : -8;
  // -8% = slightly slower than native pace, better for language learners.

  if (!text.trim()) {
    return res.status(400).json({ error: "text is required" });
  }
  if (text.length > 5000) {
    return res.status(400).json({ error: "text too long (max 5000 chars per request)" });
  }

  // Build SSML — wrap text with the selected voice + prosody rate.
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
        // 24kHz mono MP3 — good quality, ~5KB/sec, works on all browsers.
        "X-Microsoft-OutputFormat": "audio-24khz-48kbitrate-mono-mp3",
        "User-Agent": "Govorim/1.0 (Russian language practice app)",
      },
      body: ssml,
    });

    if (!azureResp.ok) {
      const errText = await azureResp.text().catch(() => "");
      console.error("Azure TTS error:", azureResp.status, errText.slice(0, 500));
      return res.status(azureResp.status >= 400 && azureResp.status < 500 ? 502 : 500).json({
        error: "Azure TTS request failed",
        azureStatus: azureResp.status,
        detail: errText.slice(0, 300),
      });
    }

    const audioBuffer = Buffer.from(await azureResp.arrayBuffer());
    if (!audioBuffer.length) {
      return res.status(502).json({ error: "Azure returned empty audio" });
    }

    res.setHeader("Content-Type", "audio/mpeg");
    res.setHeader("Content-Length", audioBuffer.length);
    // Cache same text+voice in CDN for 1 hour to avoid re-paying Azure for identical phrases.
    res.setHeader("Cache-Control", "public, max-age=3600, s-maxage=3600");
    res.status(200).send(audioBuffer);
  } catch (e) {
    console.error("TTS handler exception:", e);
    return res.status(500).json({ error: e && e.message ? e.message : "TTS failed" });
  }
}
