import { completeJSON } from "./anthropic.js";
import { BRAND } from "./config.js";
import { ScriptSchema, scriptJsonSchema, type Idea, type Script } from "./schemas.js";

const SYSTEM = `You are the head writer for "${BRAND.name}", a faceless cinematic science channel.
Voice: ${BRAND.voice}
Signature: ${BRAND.signature}

You write narration scripts engineered for retention, not just information:
- The very first line is the hook. No intro, no channel name, no "hey guys".
- Open a curiosity loop early and don't close it until the payoff.
- Each segment escalates and ends on a micro-payoff so the retention graph
  stair-steps instead of decaying.
- Calm, warm, precise narration. Short sentences. Let visuals breathe.
- The payoff delivers genuine awe — the emotional point of the whole video.
- Facts must be accurate and checkable. Never invent specifics.

For every segment you also specify:
- broll_query: a short, literal stock-footage search phrase (e.g. "black hole
  accretion disk", "earth from space at night") for the visuals under it.
- on_screen_text: at most one short phrase (or "" for none) shown large.`;

function lengthGuidance(format: "short" | "long"): string {
  if (format === "short") {
    return `This is a SHORT (30-60s, ~90-150 words total).
Use 1-2 tight segments. One hook, one escalation, one payoff. Ruthless economy.`;
  }
  return `This is a LONG-FORM video (8-12 min, ~1300-1900 words total).
Use 4-6 segments forming a clear narrative arc: hook -> stakes -> 3-5 escalating
beats -> payoff -> turn. Pace narration to slow, drifting visuals.`;
}

export async function writeScript(idea: Idea): Promise<Script> {
  const prompt = `Write the full narration script for this video.

Title: ${idea.title}
Pillar: ${idea.pillar}
Format: ${idea.format}
Intended hook: ${idea.hook}
Premise: ${idea.premise}

${lengthGuidance(idea.format)}

Return the structured script: the hook line, the ordered segments (each with
narration, broll_query, on_screen_text), the payoff, and a soft CTA that ends
on the "Pale blue" perspective and teases a related next video.`;

  const script = await completeJSON(ScriptSchema, scriptJsonSchema, {
    system: SYSTEM,
    prompt,
    effort: "high",
    maxTokens: 16000,
  });
  // Keep the format aligned to the idea even if the model labels it loosely.
  script.format = idea.format;
  return script;
}

/** Full narration as one block, in reading order — used for TTS. */
export function fullNarration(script: Script): string {
  return [
    script.hook,
    ...script.segments.map((s) => s.narration),
    script.payoff,
    script.cta,
  ]
    .map((s) => s.trim())
    .filter(Boolean)
    .join("\n\n");
}

/** Human-readable markdown script with shot directions. */
export function scriptToMarkdown(script: Script): string {
  const lines: string[] = [];
  lines.push(`# ${script.title}`);
  lines.push("");
  lines.push(`_Format: ${script.format}_`);
  lines.push("");
  lines.push("## Hook (cold open)");
  lines.push("");
  lines.push(`> ${script.hook}`);
  lines.push("");
  script.segments.forEach((s, i) => {
    lines.push(`## ${i + 1}. ${s.heading}`);
    lines.push("");
    lines.push(s.narration);
    lines.push("");
    lines.push(`- **B-roll:** ${s.broll_query}`);
    lines.push(`- **On-screen:** ${s.on_screen_text || "—"}`);
    lines.push("");
  });
  lines.push("## Payoff");
  lines.push("");
  lines.push(script.payoff);
  lines.push("");
  lines.push("## CTA / Turn");
  lines.push("");
  lines.push(script.cta);
  lines.push("");
  return lines.join("\n");
}
