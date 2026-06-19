import fs from "node:fs";
import path from "node:path";
import { CONFIG } from "./config.js";
import type { Script } from "./schemas.js";
import { fullNarration } from "./script.js";
import { writeText, log } from "./utils.js";

export interface VoiceResult {
  status: "audio" | "skipped";
  file?: string;
  reason?: string;
}

async function elevenLabs(text: string, outFile: string): Promise<void> {
  const { apiKey, voiceId, modelId } = CONFIG.tts.elevenLabs;
  const res = await fetch(
    `https://api.elevenlabs.io/v1/text-to-speech/${voiceId}`,
    {
      method: "POST",
      headers: {
        "xi-api-key": apiKey,
        "content-type": "application/json",
        accept: "audio/mpeg",
      },
      body: JSON.stringify({
        text,
        model_id: modelId,
        voice_settings: { stability: 0.5, similarity_boost: 0.75 },
      }),
    },
  );
  if (!res.ok) throw new Error(`ElevenLabs ${res.status}: ${await res.text()}`);
  fs.writeFileSync(outFile, Buffer.from(await res.arrayBuffer()));
}

async function openaiTts(text: string, outFile: string): Promise<void> {
  const { apiKey, model, voice } = CONFIG.tts.openai;
  const res = await fetch("https://api.openai.com/v1/audio/speech", {
    method: "POST",
    headers: {
      authorization: `Bearer ${apiKey}`,
      "content-type": "application/json",
    },
    body: JSON.stringify({ model, voice, input: text, response_format: "mp3" }),
  });
  if (!res.ok) throw new Error(`OpenAI TTS ${res.status}: ${await res.text()}`);
  fs.writeFileSync(outFile, Buffer.from(await res.arrayBuffer()));
}

/**
 * Synthesize the narration to mp3 using the configured provider. If the
 * provider is "none" or its key is missing, writes the narration text and
 * skips audio (so the run still completes).
 */
export async function synthesizeVoiceover(
  script: Script,
  dir: string,
): Promise<VoiceResult> {
  const narration = fullNarration(script);
  writeText(path.join(dir, "narration.txt"), narration);

  const provider = CONFIG.tts.provider;
  const outFile = path.join(dir, "voiceover.mp3");

  try {
    if (provider === "elevenlabs") {
      if (!CONFIG.tts.elevenLabs.apiKey || !CONFIG.tts.elevenLabs.voiceId) {
        return skip("ELEVENLABS_API_KEY / ELEVENLABS_VOICE_ID not set");
      }
      await elevenLabs(narration, outFile);
    } else if (provider === "openai") {
      if (!CONFIG.tts.openai.apiKey) return skip("OPENAI_API_KEY not set");
      await openaiTts(narration, outFile);
    } else {
      return skip('TTS_PROVIDER is "none"');
    }
  } catch (err) {
    return skip(`TTS error: ${(err as Error).message}`);
  }

  log("ok", `Voiceover written: ${path.basename(outFile)}`);
  return { status: "audio", file: outFile };
}

function skip(reason: string): VoiceResult {
  log("info", `Voiceover skipped (${reason}) — narration.txt written instead.`);
  return { status: "skipped", reason };
}
