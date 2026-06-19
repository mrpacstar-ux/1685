import { CONFIG } from "./config.js";
import { generateIdeas } from "./ideas.js";
import {
  nextUnproducedSlot,
  slotToIdea,
  type CalendarSlot,
} from "./calendar.js";
import { produceFromIdea } from "./pipeline.js";
import { uploadPackage } from "./youtube.js";
import type { Idea } from "./schemas.js";
import { log } from "./utils.js";

export interface AutopilotOptions {
  count?: number;
  theme?: string;
  format?: "short" | "long";
}

/**
 * Hands-off run: for each item, pick the next planned idea (from the calendar
 * if one is present and unproduced, otherwise generate a fresh idea), produce
 * the full package, and publish it according to the configured publish mode.
 *
 * Stateless-friendly: with no persisted calendar (e.g. a fresh CI runner) it
 * generates fresh ideas, so a daily cron just works.
 */
export async function runAutopilot(opts: AutopilotOptions = {}): Promise<void> {
  const count = Math.max(1, opts.count ?? 1);
  const format = opts.format ?? "long";
  log("run", `Autopilot: ${count} item(s), publish mode "${CONFIG.youtube.publishMode}".`);

  for (let i = 0; i < count; i++) {
    const slot = nextUnproducedSlot();
    let idea: Idea;
    if (slot) {
      log("info", `[${i + 1}/${count}] from calendar: "${slot.title}"`);
      idea = slotToIdea(slot);
    } else {
      log("info", `[${i + 1}/${count}] generating a fresh idea…`);
      const ideas = await generateIdeas({ count: 1, theme: opts.theme, format });
      if (!ideas.length) {
        log("warn", "No idea generated; stopping.");
        break;
      }
      idea = ideas[0];
    }

    const result = await produceFromIdea(idea);
    await publishForMode(result.dir, slot ?? undefined);
  }

  log("ok", "Autopilot run complete.");
}

async function publishForMode(dir: string, slot?: CalendarSlot): Promise<void> {
  switch (CONFIG.youtube.publishMode) {
    case "public":
      await uploadPackage(dir, { privacy: "public" });
      return;
    case "review":
      await uploadPackage(dir); // private; a human publishes
      return;
    case "scheduled":
    default:
      await uploadPackage(dir, { publishAt: scheduledPublishAt(slot) });
      return;
  }
}

/**
 * Compute the auto-publish time: a future calendar slot time if available,
 * otherwise now + the configured lead time. Always returns a future RFC3339
 * timestamp so scheduling never fails on a past time.
 */
function scheduledPublishAt(slot?: CalendarSlot): string {
  if (slot) {
    const iso = `${slot.date}T${slot.time}:00${CONFIG.youtube.tzOffset}`;
    const t = new Date(iso).getTime();
    if (!Number.isNaN(t) && t > Date.now() + 60_000) {
      return new Date(t).toISOString();
    }
  }
  const lead = CONFIG.youtube.publishDelayHours * 3_600_000;
  return new Date(Date.now() + lead).toISOString();
}
