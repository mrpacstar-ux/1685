import { z } from "zod";
import { BRAND } from "./config.js";

/**
 * For each generated structure we keep a zod schema (runtime validation +
 * inferred TS types) alongside a hand-written JSON Schema (sent to the API via
 * output_config.format). JSON Schema here stays within structured-output
 * limits: every object sets additionalProperties:false and lists required;
 * no min/max/length constraints (those are enforced via prompt + zod).
 */

const pillarValues = BRAND.pillars as readonly string[];

// ── Ideas ──────────────────────────────────────────────────────────────────
export const IdeaSchema = z.object({
  title: z.string(),
  pillar: z.enum(BRAND.pillars),
  format: z.enum(["short", "long"]),
  hook: z.string(),
  premise: z.string(),
  why_it_works: z.string(),
});
export type Idea = z.infer<typeof IdeaSchema>;

export const IdeaListSchema = z.object({ ideas: z.array(IdeaSchema) });
export type IdeaList = z.infer<typeof IdeaListSchema>;

export const ideaListJsonSchema: Record<string, unknown> = {
  type: "object",
  additionalProperties: false,
  required: ["ideas"],
  properties: {
    ideas: {
      type: "array",
      items: {
        type: "object",
        additionalProperties: false,
        required: ["title", "pillar", "format", "hook", "premise", "why_it_works"],
        properties: {
          title: { type: "string" },
          pillar: { type: "string", enum: pillarValues },
          format: { type: "string", enum: ["short", "long"] },
          hook: { type: "string" },
          premise: { type: "string" },
          why_it_works: { type: "string" },
        },
      },
    },
  },
};

// ── Script ─────────────────────────────────────────────────────────────────
export const SegmentSchema = z.object({
  heading: z.string(),
  narration: z.string(),
  broll_query: z.string(),
  on_screen_text: z.string(),
});

export const ScriptSchema = z.object({
  title: z.string(),
  format: z.enum(["short", "long"]),
  hook: z.string(),
  segments: z.array(SegmentSchema),
  payoff: z.string(),
  cta: z.string(),
});
export type Script = z.infer<typeof ScriptSchema>;

const segmentJson = {
  type: "object",
  additionalProperties: false,
  required: ["heading", "narration", "broll_query", "on_screen_text"],
  properties: {
    heading: { type: "string" },
    narration: { type: "string" },
    broll_query: { type: "string" },
    on_screen_text: { type: "string" },
  },
};

export const scriptJsonSchema: Record<string, unknown> = {
  type: "object",
  additionalProperties: false,
  required: ["title", "format", "hook", "segments", "payoff", "cta"],
  properties: {
    title: { type: "string" },
    format: { type: "string", enum: ["short", "long"] },
    hook: { type: "string" },
    segments: { type: "array", items: segmentJson },
    payoff: { type: "string" },
    cta: { type: "string" },
  },
};

// ── Metadata ────────────────────────────────────────────────────────────────
export const ChapterSchema = z.object({
  timestamp: z.string(),
  label: z.string(),
});

export const MetadataSchema = z.object({
  title_candidates: z.array(z.string()),
  chosen_title: z.string(),
  description: z.string(),
  tags: z.array(z.string()),
  thumbnail_text: z.string(),
  pinned_comment: z.string(),
  chapters: z.array(ChapterSchema),
});
export type Metadata = z.infer<typeof MetadataSchema>;

export const metadataJsonSchema: Record<string, unknown> = {
  type: "object",
  additionalProperties: false,
  required: [
    "title_candidates",
    "chosen_title",
    "description",
    "tags",
    "thumbnail_text",
    "pinned_comment",
    "chapters",
  ],
  properties: {
    title_candidates: { type: "array", items: { type: "string" } },
    chosen_title: { type: "string" },
    description: { type: "string" },
    tags: { type: "array", items: { type: "string" } },
    thumbnail_text: { type: "string" },
    pinned_comment: { type: "string" },
    chapters: {
      type: "array",
      items: {
        type: "object",
        additionalProperties: false,
        required: ["timestamp", "label"],
        properties: {
          timestamp: { type: "string" },
          label: { type: "string" },
        },
      },
    },
  },
};
