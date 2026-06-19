import { CONFIG } from "./config.js";
import { generateIdeas } from "./ideas.js";
import {
  nextUnproducedSlot,
  slotToIdea,
  type CalendarSlot,
} from "./calendar.js";
import { produceFromIdea } from "./pipeline.js";
import { uploadPackage } from "./youtube.js";
import { isProduced, recentTitles } from "./history.js";
import type { Idea } from "./schemas.js";
import { slugify, log } from "./utils.js";

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
    if (slot && !isProduced(slot.slug)) {
      log("info", `[${i + 1}/${count}] from calendar: "${slot.title}"`);
      idea = slotToIdea(slot);
    } else {
      log("info", `[${i + 1}/${count}] generating a fresh idea…`);
      const picked = await pickFreshIdea(opts.theme, format);
      if (!picked) {
        log("warn", "Could not generate a non-duplicate idea; stopping.");
        break;
      }
      idea = picked;
    }

    const result = await produceFromIdea(idea);
    await publishForMode(result.dir, slot ?? undefined);
  }

  log("ok", "Autopilot run complete.");
}

/**
 * Generate a small batch (excluding already-covered topics) and return the
 * first candidate whose slug hasn't been produced — belt-and-suspenders on top
 * of the model-level exclusion.
 */
async function pickFreshIdea(
  theme: string | undefined,
  format: "short" | "long",
): Promise<Idea | null> {
  const ideas = await generateIdeas({
    count: 3,
    theme,
    format,
    avoid: recentTitles(),
  });
  return ideas.find((idea) => !isProduced(slugify(idea.title))) ?? ideas[0] ?? null;
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
