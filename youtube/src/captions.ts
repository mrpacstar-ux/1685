import path from "node:path";
import type { Script } from "./schemas.js";
import { fullNarration } from "./script.js";
import { writeText, log } from "./utils.js";

// Calm, cinematic narration runs slower than conversational speech.
const WORDS_PER_SECOND = 2.3;
const MAX_WORDS_PER_CAPTION = 12;
const MIN_CAPTION_SECONDS = 1.2;

function srtTimestamp(seconds: number): string {
  const ms = Math.round(seconds * 1000);
  const h = Math.floor(ms / 3_600_000);
  const m = Math.floor((ms % 3_600_000) / 60_000);
  const s = Math.floor((ms % 60_000) / 1000);
  const millis = ms % 1000;
  const pad = (n: number, w = 2) => String(n).padStart(w, "0");
  return `${pad(h)}:${pad(m)}:${pad(s)},${pad(millis, 3)}`;
}

/** Split narration into caption-sized chunks: by sentence, then by length. */
function toCaptionChunks(text: string): string[] {
  const sentences = text.replace(/\s+/g, " ").match(/[^.!?]+[.!?]?/g) ?? [text];
  const chunks: string[] = [];
  for (const sentence of sentences) {
    const words = sentence.trim().split(" ").filter(Boolean);
    for (let i = 0; i < words.length; i += MAX_WORDS_PER_CAPTION) {
      chunks.push(words.slice(i, i + MAX_WORDS_PER_CAPTION).join(" "));
    }
  }
  return chunks.filter(Boolean);
}

/** Build a SubRip (.srt) caption track with timings estimated from word count. */
export function buildSrt(script: Script): { srt: string; durationSeconds: number } {
  const chunks = toCaptionChunks(fullNarration(script));
  const lines: string[] = [];
  let t = 0;
  chunks.forEach((chunk, i) => {
    const words = chunk.split(" ").length;
    const dur = Math.max(MIN_CAPTION_SECONDS, words / WORDS_PER_SECOND);
    const start = t;
    const end = t + dur;
    t = end;
    lines.push(String(i + 1), `${srtTimestamp(start)} --> ${srtTimestamp(end)}`, chunk, "");
  });
  return { srt: lines.join("\n"), durationSeconds: t };
}

export function writeCaptions(script: Script, dir: string): string {
  const { srt, durationSeconds } = buildSrt(script);
  const file = path.join(dir, "captions.srt");
  writeText(file, srt);
  log("ok", `Captions written: captions.srt (~${Math.round(durationSeconds)}s of narration).`);
  return file;
}
