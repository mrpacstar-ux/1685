import { completeJSON } from "./anthropic.js";
import { BRAND } from "./config.js";
import { fullNarration } from "./script.js";
import {
  MetadataSchema,
  metadataJsonSchema,
  type Metadata,
  type Script,
} from "./schemas.js";

const SYSTEM = `You are a YouTube packaging and SEO specialist for "${BRAND.name}".
You know that title + thumbnail decide click-through, and that titles must
create a curiosity gap the video genuinely closes. No bait, no all-caps spam.`;

export async function makeMetadata(script: Script): Promise<Metadata> {
  const isShort = script.format === "short";
  const prompt = `Create the publishing package for this video.

Title: ${script.title}
Format: ${script.format}
Narration:
"""
${fullNarration(script)}
"""

Produce:
- title_candidates: 4-5 strong titles (curiosity-driven, <= 60 chars,
  hook front-loaded). ${isShort ? "Add #Shorts-friendly phrasing where natural." : ""}
- chosen_title: the single best one.
- description: first two lines must hook (they show in search), then a 2-4
  sentence summary.${isShort ? "" : " Include a one-line affiliate disclosure placeholder and the channel tagline."}
- tags: 8-15 relevant tags (no stuffing).
- thumbnail_text: a punchy 3-5 word phrase for the thumbnail (states the
  question/tension; must match the video's actual payoff).
- pinned_comment: a short comment that invites a specific reply (drives engagement).
- chapters: ${
    isShort
      ? "an empty array (Shorts have no chapters)."
      : "4-7 chapters with mm:ss timestamps starting at 00:00, matching the segments."
  }

Tagline to weave in where appropriate: "${BRAND.tagline}".`;

  return completeJSON(MetadataSchema, metadataJsonSchema, {
    system: SYSTEM,
    prompt,
    effort: "medium",
    maxTokens: 6000,
  });
}

/** Render the description with chapters + standard channel footer appended. */
export function renderDescription(meta: Metadata): string {
  const parts = [meta.description.trim()];
  if (meta.chapters.length) {
    parts.push("", "Chapters:");
    parts.push(...meta.chapters.map((c) => `${c.timestamp} ${c.label}`));
  }
  parts.push(
    "",
    `${BRAND.name} — ${BRAND.tagline}`,
    `Subscribe: youtube.com/${BRAND.handle}`,
    "",
    "Some links may be affiliate links that support the channel at no extra cost to you.",
  );
  return parts.join("\n");
}
