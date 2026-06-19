import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

/**
 * Minimal .env loader (no dependency). Loads youtube/.env into process.env
 * without overwriting variables already present in the real environment.
 */
function loadDotEnv(): void {
  const here = path.dirname(fileURLToPath(import.meta.url));
  const envPath = path.join(here, "..", ".env");
  if (!fs.existsSync(envPath)) return;
  for (const raw of fs.readFileSync(envPath, "utf8").split("\n")) {
    const line = raw.trim();
    if (!line || line.startsWith("#")) continue;
    const eq = line.indexOf("=");
    if (eq === -1) continue;
    const key = line.slice(0, eq).trim();
    let value = line.slice(eq + 1).trim();
    if (
      (value.startsWith('"') && value.endsWith('"')) ||
      (value.startsWith("'") && value.endsWith("'"))
    ) {
      value = value.slice(1, -1);
    }
    if (process.env[key] === undefined) process.env[key] = value;
  }
}

loadDotEnv();

const ROOT = path.dirname(fileURLToPath(import.meta.url));
export const OUT_DIR = path.join(ROOT, "..", "out");
// Tracked (not git-ignored) so the produced-topic history survives across
// runs — including fresh CI runners that wipe out/ each time.
export const STATE_DIR = path.join(ROOT, "..", "state");

/** Brand constants — the single source of truth for identity in code. */
export const BRAND = {
  name: "Pale Blue Mind",
  handle: "@palebluemind",
  tagline: "Big questions, answered with awe.",
  pillars: ["Scale", "What if", "Deep time", "Frontier", "Pale blue"] as const,
  voice:
    "Calm, warm, precise, curious. Short sentences. Never condescending, " +
    "never hype. A thoughtful friend who happens to know the cosmos.",
  accentColor: "#f2b134", // warm amber
  baseColor: "#0a1228", // deep cosmic blue/black
  signature:
    "Always end by zooming back to the human / Earth scale (the 'Pale blue' " +
    "perspective) before a soft, specific call to action.",
} as const;

export type Pillar = (typeof BRAND.pillars)[number];

export const CONFIG = {
  model: process.env.PBM_MODEL ?? "claude-opus-4-8",
  effort: (process.env.PBM_EFFORT ?? "high") as
    | "low"
    | "medium"
    | "high"
    | "xhigh"
    | "max",

  tts: {
    provider: (process.env.TTS_PROVIDER ?? "none") as
      | "none"
      | "elevenlabs"
      | "openai",
    elevenLabs: {
      apiKey: process.env.ELEVENLABS_API_KEY ?? "",
      voiceId: process.env.ELEVENLABS_VOICE_ID ?? "",
      modelId: process.env.ELEVENLABS_MODEL_ID ?? "eleven_multilingual_v2",
    },
    openai: {
      apiKey: process.env.OPENAI_API_KEY ?? "",
      model: process.env.OPENAI_TTS_MODEL ?? "tts-1",
      voice: process.env.OPENAI_TTS_VOICE ?? "onyx",
    },
  },

  pexelsApiKey: process.env.PEXELS_API_KEY ?? "",

  youtube: {
    clientId: process.env.YOUTUBE_CLIENT_ID ?? "",
    clientSecret: process.env.YOUTUBE_CLIENT_SECRET ?? "",
    refreshToken: process.env.YOUTUBE_REFRESH_TOKEN ?? "",
    privacy: (process.env.YOUTUBE_PRIVACY ?? "private") as
      | "private"
      | "unlisted"
      | "public",
    // How the autopilot publishes:
    //   scheduled — upload private + auto-publish at the scheduled time (default)
    //   review    — upload private, a human publishes
    //   public    — publish public immediately (highest risk)
    publishMode: (process.env.PBM_PUBLISH_MODE ?? "scheduled") as
      | "scheduled"
      | "review"
      | "public",
    // UTC offset applied to calendar slot times when computing publish time.
    tzOffset: process.env.YOUTUBE_PUBLISH_TZ_OFFSET ?? "+00:00",
    // Fallback lead time (hours) when there is no future slot time to target.
    publishDelayHours: Number(process.env.PBM_PUBLISH_DELAY_HOURS ?? 3),
  },
} as const;

export function requireAnthropicKey(): void {
  if (!process.env.ANTHROPIC_API_KEY) {
    throw new Error(
      "ANTHROPIC_API_KEY is not set. Copy .env.example to .env and add your key.",
    );
  }
}
