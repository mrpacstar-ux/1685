import { requireAnthropicKey, OUT_DIR } from "./config.js";
import path from "node:path";
import { generateAndStoreIdeas } from "./ideas.js";
import { generateCalendar, nextUnproducedSlot } from "./calendar.js";
import { produceFromTopic, produceFromIdea } from "./pipeline.js";
import { makeBrandAssets } from "./branding.js";
import { uploadPackage } from "./youtube.js";
import type { Idea } from "./schemas.js";
import { log } from "./utils.js";

interface Parsed {
  positionals: string[];
  flags: Record<string, string | boolean>;
}

function parse(argv: string[]): Parsed {
  const positionals: string[] = [];
  const flags: Record<string, string | boolean> = {};
  for (let i = 0; i < argv.length; i++) {
    const a = argv[i];
    if (a.startsWith("--")) {
      const key = a.slice(2);
      const next = argv[i + 1];
      if (next && !next.startsWith("--")) {
        flags[key] = next;
        i++;
      } else {
        flags[key] = true;
      }
    } else {
      positionals.push(a);
    }
  }
  return { positionals, flags };
}

const USAGE = `Pale Blue Mind — channel automation

Usage:
  npm run ideas    -- [--count N] [--theme "..."] [--format short|long|mixed]
  npm run calendar -- [--weeks N]
  npm run branding                                   (render avatar + banner)
  npm run produce  -- "<topic>"  | --from-calendar  [--short]
  npm run upload   -- out/<slug>
  npm run run      -- "<topic>" [--short]            (produce + upload)
`;

async function main(): Promise<void> {
  const [command, ...rest] = process.argv.slice(2);
  const { positionals, flags } = parse(rest);

  switch (command) {
    case "ideas": {
      requireAnthropicKey();
      const count = Number(flags.count ?? 12);
      const format = (flags.format as Idea["format"] | "mixed") ?? "mixed";
      await generateAndStoreIdeas({
        count,
        theme: typeof flags.theme === "string" ? flags.theme : undefined,
        format,
      });
      break;
    }

    case "calendar": {
      requireAnthropicKey();
      await generateCalendar(Number(flags.weeks ?? 4));
      break;
    }

    case "branding": {
      // No API key needed — assets are rendered locally from SVG.
      await makeBrandAssets(path.join(OUT_DIR, "brand"));
      break;
    }

    case "produce": {
      requireAnthropicKey();
      const format: "short" | "long" = flags.short ? "short" : "long";
      if (flags["from-calendar"]) {
        const slot = nextUnproducedSlot();
        if (!slot) {
          log("warn", "No unproduced slots in the calendar. Run `calendar` first.");
          break;
        }
        const idea: Idea = {
          title: slot.title,
          pillar: slot.pillar as Idea["pillar"],
          format: slot.format,
          hook: slot.hook,
          premise: "",
          why_it_works: "",
        };
        await produceFromIdea(idea);
      } else {
        const topic = positionals[0];
        if (!topic) {
          log("warn", 'Provide a topic, e.g. produce -- "What is dark matter?"');
          break;
        }
        await produceFromTopic(topic, format);
      }
      break;
    }

    case "upload": {
      const dir = positionals[0];
      if (!dir) {
        log("warn", "Provide a package directory, e.g. upload -- out/<slug>");
        break;
      }
      await uploadPackage(dir);
      break;
    }

    case "run": {
      requireAnthropicKey();
      const topic = positionals[0];
      if (!topic) {
        log("warn", 'Provide a topic, e.g. run -- "What is dark matter?"');
        break;
      }
      const format: "short" | "long" = flags.short ? "short" : "long";
      const result = await produceFromTopic(topic, format);
      await uploadPackage(result.dir);
      break;
    }

    default:
      console.log(USAGE);
  }
}

main().catch((err) => {
  console.error(`\n✗ ${(err as Error).message}`);
  process.exit(1);
});
