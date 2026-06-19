import path from "node:path";
import { STATE_DIR } from "./config.js";
import { writeJson, readJson, log } from "./utils.js";

/**
 * Durable record of every video the channel has produced. It lives in the
 * tracked `state/` directory (not `out/`), so it persists locally and — once
 * the CI step commits it back — across stateless GitHub Action runs. This is
 * what guarantees autopilot never repeats a topic day to day.
 */

const HISTORY_FILE = path.join(STATE_DIR, "history.json");

export interface HistoryEntry {
  slug: string;
  title: string;
  pillar: string;
  producedAt: string;
}

export function loadHistory(): HistoryEntry[] {
  try {
    return readJson<HistoryEntry[]>(HISTORY_FILE);
  } catch {
    return [];
  }
}

export function isProduced(slug: string): boolean {
  return loadHistory().some((e) => e.slug === slug);
}

/** Append a produced video (idempotent on slug). */
export function recordProduced(entry: Omit<HistoryEntry, "producedAt">): void {
  const history = loadHistory();
  if (history.some((e) => e.slug === entry.slug)) return;
  history.push({ ...entry, producedAt: new Date().toISOString() });
  writeJson(HISTORY_FILE, history);
  log("ok", `History updated — ${history.length} topics produced to date.`);
}

/** Most-recent produced titles, for excluding from new idea generation. */
export function recentTitles(limit = 200): string[] {
  return loadHistory()
    .slice(-limit)
    .map((e) => e.title);
}
