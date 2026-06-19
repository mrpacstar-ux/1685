import fs from "node:fs";
import path from "node:path";
import { CONFIG } from "./config.js";
import type { Script } from "./schemas.js";
import { ensureDir, writeText, log } from "./utils.js";

export interface VisualsResult {
  status: "downloaded" | "storyboard";
  clips: string[];
  storyboard: string;
}

interface PexelsVideoFile {
  link: string;
  width: number;
  height: number;
  file_type: string;
}
interface PexelsVideo {
  video_files: PexelsVideoFile[];
}
interface PexelsResponse {
  videos: PexelsVideo[];
}

async function searchPexels(query: string): Promise<string | null> {
  const url =
    "https://api.pexels.com/videos/search?orientation=landscape&size=medium&per_page=1&query=" +
    encodeURIComponent(query);
  const res = await fetch(url, {
    headers: { Authorization: CONFIG.pexelsApiKey },
  });
  if (!res.ok) throw new Error(`Pexels ${res.status}: ${await res.text()}`);
  const data = (await res.json()) as PexelsResponse;
  const video = data.videos[0];
  if (!video) return null;
  // Prefer a ~1080p mp4 file; fall back to the widest available.
  const mp4s = video.video_files
    .filter((f) => f.file_type === "video/mp4")
    .sort((a, b) => b.width - a.width);
  const pick = mp4s.find((f) => f.height <= 1080) ?? mp4s[0];
  return pick?.link ?? null;
}

async function download(url: string, outFile: string): Promise<void> {
  const res = await fetch(url);
  if (!res.ok) throw new Error(`download ${res.status}`);
  fs.writeFileSync(outFile, Buffer.from(await res.arrayBuffer()));
}

function buildStoryboard(script: Script): string {
  const rows = [
    "# Storyboard — " + script.title,
    "",
    "| # | Beat | B-roll search | On-screen text |",
    "|---|------|---------------|----------------|",
    `| 0 | Hook | (cinematic cosmic opener) | — |`,
  ];
  script.segments.forEach((s, i) => {
    rows.push(
      `| ${i + 1} | ${s.heading} | ${s.broll_query} | ${s.on_screen_text || "—"} |`,
    );
  });
  rows.push(`| ${script.segments.length + 1} | Payoff / Pale-blue turn | earth from space | — |`);
  rows.push("");
  return rows.join("\n");
}

/**
 * Acquire B-roll for each segment via Pexels. Without a key, write a
 * storyboard (the shot list a human or another tool can fill).
 */
export async function gatherVisuals(
  script: Script,
  dir: string,
): Promise<VisualsResult> {
  const storyboard = buildStoryboard(script);
  const storyboardPath = path.join(dir, "storyboard.md");
  writeText(storyboardPath, storyboard);

  if (!CONFIG.pexelsApiKey) {
    log("info", "PEXELS_API_KEY not set — storyboard.md written, no clips downloaded.");
    return { status: "storyboard", clips: [], storyboard: storyboardPath };
  }

  const assetsDir = ensureDir(path.join(dir, "assets"));
  const queries = [
    "deep space nebula stars",
    ...script.segments.map((s) => s.broll_query),
    "planet earth from space",
  ];

  const clips: string[] = [];
  for (let i = 0; i < queries.length; i++) {
    try {
      const link = await searchPexels(queries[i]);
      if (!link) {
        log("warn", `No B-roll found for "${queries[i]}"`);
        continue;
      }
      const file = path.join(assetsDir, `clip-${String(i).padStart(2, "0")}.mp4`);
      await download(link, file);
      clips.push(file);
    } catch (err) {
      log("warn", `B-roll fetch failed for "${queries[i]}": ${(err as Error).message}`);
    }
  }

  log("ok", `Downloaded ${clips.length} B-roll clips.`);
  return { status: "downloaded", clips, storyboard: storyboardPath };
}
