import path from "node:path";
import { renderDescription } from "./metadata.js";
import type { Metadata } from "./schemas.js";
import { writeText, log } from "./utils.js";

/**
 * A copy-paste-ready publishing sheet for the human reviewer: everything that
 * goes into the YouTube upload form, in one file, in the order they'll need it.
 */
export function writePublishSheet(meta: Metadata, dir: string): string {
  const sheet = [
    "=== PALE BLUE MIND — PUBLISH SHEET ===",
    "Review before publishing. Upload defaults to PRIVATE.",
    "",
    "── TITLE (chosen) ──",
    meta.chosen_title,
    "",
    "── TITLE CANDIDATES (for A/B / Test & Compare) ──",
    ...meta.title_candidates.map((t, i) => `${i + 1}. ${t}`),
    "",
    "── DESCRIPTION ──",
    renderDescription(meta),
    "",
    "── TAGS ──",
    meta.tags.join(", "),
    "",
    "── THUMBNAIL TEXT ──",
    meta.thumbnail_text,
    "  (variants rendered: thumbnail.png [A], thumbnail-b.png [B])",
    "",
    "── PINNED COMMENT ──",
    meta.pinned_comment,
    "",
    "── PRE-PUBLISH CHECKLIST ──",
    "[ ] Facts spot-checked against a reliable source",
    "[ ] Thumbnail matches the video's actual payoff (no bait)",
    "[ ] Captions reviewed (captions.srt)",
    "[ ] Correct playlist assigned (by pillar)",
    "[ ] End screen / pinned comment points to a related video",
    "",
  ].join("\n");

  const file = path.join(dir, "publish.txt");
  writeText(file, sheet);
  log("ok", "Publish sheet written: publish.txt");
  return file;
}
