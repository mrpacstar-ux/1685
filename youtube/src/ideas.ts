import path from "node:path";
import { completeJSON } from "./anthropic.js";
import { BRAND, OUT_DIR } from "./config.js";
import { IdeaListSchema, ideaListJsonSchema, type Idea } from "./schemas.js";
import { recentTitles } from "./history.js";
import { writeJson, readJson, log } from "./utils.js";

const IDEAS_FILE = path.join(OUT_DIR, "ideas.json");

const SYSTEM = `You are the head writer and channel strategist for "${BRAND.name}", a faceless YouTube channel.
Tagline: "${BRAND.tagline}".
Voice: ${BRAND.voice}
The channel covers space, deep time, and the biggest questions in science.
Every idea must belong to exactly one content pillar: ${BRAND.pillars.join(", ")}.

You optimize ruthlessly for two things: a hook that creates an irresistible
curiosity gap, and a payoff that delivers genuine awe. No clickbait that the
video can't honor. Facts must be real and checkable.`;

export interface IdeaRequest {
  count: number;
  theme?: string;
  format?: "short" | "long" | "mixed";
  /** Titles to exclude — do not duplicate or closely overlap these. */
  avoid?: string[];
}

export async function generateIdeas(req: IdeaRequest): Promise<Idea[]> {
  const formatLine =
    req.format === "short"
      ? "All ideas should be `short` format (30-60s)."
      : req.format === "long"
        ? "All ideas should be `long` format (8-12 min)."
        : "Mix `short` and `long` formats, roughly 2 shorts per long.";

  const themeLine = req.theme
    ? `Lean into this theme / winning vein: "${req.theme}".`
    : "Spread ideas across all five pillars.";

  const avoid = (req.avoid ?? []).slice(-150);
  const avoidLine = avoid.length
    ? `\nALREADY COVERED — do NOT propose any video that duplicates or closely
overlaps these existing titles (pick genuinely new angles instead):\n${avoid
        .map((t) => `- ${t}`)
        .join("\n")}\n`
    : "";

  const prompt = `Brainstorm ${req.count} distinct video ideas for the channel.

${formatLine}
${themeLine}
${avoidLine}
For each idea provide:
- title: the working title (curiosity-driven; a question or a tension)
- pillar: one of ${BRAND.pillars.join(", ")}
- format: "short" or "long"
- hook: the exact cold-open line that would start the video (no intro, no "hey guys")
- premise: 1-2 sentences on what the video actually explains
- why_it_works: why this earns the click and holds retention

Make the ideas genuinely varied — no two should be near-duplicates. Favor
questions a curious person has wondered about but never had answered well.`;

  const { ideas } = await completeJSON(IdeaListSchema, ideaListJsonSchema, {
    system: SYSTEM,
    prompt,
    effort: "medium",
    maxTokens: 8000,
  });
  return ideas;
}

/** Generate ideas, append to the de-duplicated idea log, and persist. */
export async function generateAndStoreIdeas(req: IdeaRequest): Promise<Idea[]> {
  const existing = loadIdeas();
  // Exclude both the in-progress idea log and every already-produced title.
  const avoid = [
    ...(req.avoid ?? []),
    ...existing.map((i) => i.title),
    ...recentTitles(),
  ];
  const fresh = await generateIdeas({ ...req, avoid });
  const seen = new Set([
    ...existing.map((i) => i.title.toLowerCase().trim()),
    ...recentTitles().map((t) => t.toLowerCase().trim()),
  ]);
  const deduped = fresh.filter((i) => !seen.has(i.title.toLowerCase().trim()));
  const all = [...existing, ...deduped];
  writeJson(IDEAS_FILE, all);
  log("ok", `Generated ${fresh.length} ideas (${deduped.length} new). Log: ${all.length} total.`);
  return deduped;
}

export function loadIdeas(): Idea[] {
  try {
    return readJson<Idea[]>(IDEAS_FILE);
  } catch {
    return [];
  }
}
