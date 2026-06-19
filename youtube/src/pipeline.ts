import path from "node:path";
import { completeJSON } from "./anthropic.js";
import { BRAND } from "./config.js";
import {
  IdeaListSchema,
  ideaListJsonSchema,
  type Idea,
} from "./schemas.js";
import { writeScript, scriptToMarkdown } from "./script.js";
import { makeMetadata } from "./metadata.js";
import { writeCaptions } from "./captions.js";
import { writePublishSheet } from "./publish.js";
import { synthesizeVoiceover } from "./voiceover.js";
import { gatherVisuals } from "./visuals.js";
import { makeThumbnails } from "./thumbnail.js";
import { assembleVideo } from "./assemble.js";
import { recordProduced } from "./history.js";
import { packageDir, writeJson, writeText, slugify, log } from "./utils.js";

export interface ProduceResult {
  slug: string;
  dir: string;
  title: string;
  voiceover: string;
  visuals: string;
  video: string;
}

/** Turn a raw topic string into a fully-formed Idea (hook, pillar, premise). */
export async function ideaFromTopic(
  topic: string,
  format: "short" | "long",
): Promise<Idea> {
  const { ideas } = await completeJSON(IdeaListSchema, ideaListJsonSchema, {
    system: `You develop one video idea for "${BRAND.name}". Voice: ${BRAND.voice}`,
    prompt: `Develop exactly ONE ${format}-format video idea for this exact topic:
"${topic}"

Stay faithful to the topic — don't swap it for a different one. Choose the best
fitting pillar (${BRAND.pillars.join(", ")}), write the cold-open hook line, a
1-2 sentence premise, and why it works. Return a list with a single idea.`,
    effort: "medium",
    maxTokens: 2000,
  });
  const idea = ideas[0];
  idea.format = format;
  return idea;
}

/** Produce a complete video package from an Idea. */
export async function produceFromIdea(idea: Idea): Promise<ProduceResult> {
  const slug = slugify(idea.title);
  const dir = packageDir(slug);
  log("run", `Producing "${idea.title}" (${idea.format}) → out/${slug}/`);

  // 1. Script (+ captions track)
  const script = await writeScript(idea);
  writeJson(path.join(dir, "script.json"), script);
  writeText(path.join(dir, "script.md"), scriptToMarkdown(script));
  writeCaptions(script, dir);
  log("ok", `Script written (${script.segments.length} segments).`);

  // 2. Metadata / SEO (+ copy-paste publish sheet)
  const metadata = await makeMetadata(script);
  writeJson(path.join(dir, "metadata.json"), metadata);
  writePublishSheet(metadata, dir);
  log("ok", `Metadata written ("${metadata.chosen_title}").`);

  // 3-5. Assets (each degrades gracefully if a key is missing)
  const voice = await synthesizeVoiceover(script, dir);
  const visuals = await gatherVisuals(script, dir);
  await makeThumbnails(metadata.thumbnail_text, dir);

  // 6. Assemble
  const video = assembleVideo(visuals.clips, voice.file, dir);

  // 7. Manifest
  const manifest = {
    slug,
    title: metadata.chosen_title,
    pillar: idea.pillar,
    format: idea.format,
    createdAt: new Date().toISOString(),
    steps: {
      voiceover: voice.status,
      visuals: visuals.status,
      video: video.status,
    },
    reviewBeforePublish: true,
  };
  writeJson(path.join(dir, "manifest.json"), manifest);

  // Durable record so this topic is never produced again.
  recordProduced({ slug, title: metadata.chosen_title, pillar: idea.pillar });

  log("ok", `Package complete: out/${slug}/`);
  return {
    slug,
    dir,
    title: metadata.chosen_title,
    voiceover: voice.status,
    visuals: visuals.status,
    video: video.status,
  };
}

export async function produceFromTopic(
  topic: string,
  format: "short" | "long" = "long",
): Promise<ProduceResult> {
  const idea = await ideaFromTopic(topic, format);
  return produceFromIdea(idea);
}
