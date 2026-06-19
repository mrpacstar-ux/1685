import path from "node:path";
import fs from "node:fs";
import { generateIdeas } from "./ideas.js";
import type { Idea } from "./schemas.js";
import { OUT_DIR } from "./config.js";
import { writeJson, writeText, readJson, slugify, log } from "./utils.js";

export interface CalendarSlot {
  date: string; // YYYY-MM-DD
  time: string; // HH:MM (local)
  format: "short" | "long";
  pillar: string;
  title: string;
  hook: string;
  slug: string;
}

const CALENDAR_FILE = path.join(OUT_DIR, "calendar.json");

const LONG_DAYS = [2, 6]; // Tue, Sat
const SHORT_TIME = "12:00";
const LONG_TIME = "17:00";

function isoDate(d: Date): string {
  return d.toISOString().slice(0, 10);
}

/**
 * Build a posting calendar: one Short per day, two long-form per week
 * (Tue/Sat). Generates exactly enough fresh ideas to fill every slot.
 */
export async function generateCalendar(weeks: number): Promise<CalendarSlot[]> {
  const days = weeks * 7;
  const start = new Date();
  start.setDate(start.getDate() + 1); // start tomorrow

  // Count slots needed.
  let shortsNeeded = 0;
  let longsNeeded = 0;
  for (let i = 0; i < days; i++) {
    const d = new Date(start);
    d.setDate(start.getDate() + i);
    shortsNeeded++;
    if (LONG_DAYS.includes(d.getDay())) longsNeeded++;
  }

  log("run", `Generating ${shortsNeeded} short + ${longsNeeded} long ideas…`);
  const [shorts, longs] = await Promise.all([
    generateIdeas({ count: shortsNeeded, format: "short" }),
    generateIdeas({ count: longsNeeded, format: "long" }),
  ]);

  const shortQ = [...shorts];
  const longQ = [...longs];
  const take = (q: Idea[], format: "short" | "long"): Idea =>
    q.shift() ?? {
      title: `${format === "short" ? "Short" : "Deep dive"} (TBD)`,
      pillar: "Frontier",
      format,
      hook: "",
      premise: "",
      why_it_works: "",
    };

  const slots: CalendarSlot[] = [];
  for (let i = 0; i < days; i++) {
    const d = new Date(start);
    d.setDate(start.getDate() + i);
    const date = isoDate(d);

    if (LONG_DAYS.includes(d.getDay())) {
      const idea = take(longQ, "long");
      slots.push(toSlot(date, LONG_TIME, idea));
    }
    const s = take(shortQ, "short");
    slots.push(toSlot(date, SHORT_TIME, s));
  }

  writeJson(CALENDAR_FILE, slots);
  writeText(path.join(OUT_DIR, "calendar.md"), toMarkdown(slots, weeks));
  log("ok", `Calendar written: ${slots.length} slots over ${weeks} week(s).`);
  return slots;
}

function toSlot(date: string, time: string, idea: Idea): CalendarSlot {
  return {
    date,
    time,
    format: idea.format,
    pillar: idea.pillar,
    title: idea.title,
    hook: idea.hook,
    slug: slugify(idea.title),
  };
}

function toMarkdown(slots: CalendarSlot[], weeks: number): string {
  const lines = [
    `# Pale Blue Mind — ${weeks}-week content calendar`,
    "",
    "| Date | Time | Format | Pillar | Title |",
    "|------|------|--------|--------|-------|",
  ];
  for (const s of slots) {
    lines.push(
      `| ${s.date} | ${s.time} | ${s.format} | ${s.pillar} | ${s.title} |`,
    );
  }
  lines.push("");
  return lines.join("\n");
}

export function loadCalendar(): CalendarSlot[] {
  try {
    return readJson<CalendarSlot[]>(CALENDAR_FILE);
  } catch {
    return [];
  }
}

/** First calendar slot that hasn't been produced yet (no out/<slug>/ dir). */
export function nextUnproducedSlot(): CalendarSlot | null {
  for (const slot of loadCalendar()) {
    if (!fs.existsSync(path.join(OUT_DIR, slot.slug))) return slot;
  }
  return null;
}

/** Convert a calendar slot into a producible Idea. */
export function slotToIdea(slot: CalendarSlot): Idea {
  return {
    title: slot.title,
    pillar: slot.pillar as Idea["pillar"],
    format: slot.format,
    hook: slot.hook,
    premise: "",
    why_it_works: "",
  };
}
