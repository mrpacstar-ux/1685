import Anthropic from "@anthropic-ai/sdk";
import type { z } from "zod";
import { CONFIG } from "./config.js";
import { stripCodeFences } from "./utils.js";

// Reads ANTHROPIC_API_KEY from the environment.
export const client = new Anthropic();

type Effort = "low" | "medium" | "high" | "xhigh" | "max";

interface BaseOpts {
  system?: string;
  prompt: string;
  maxTokens?: number;
  effort?: Effort;
}

function textFrom(message: Anthropic.Message): string {
  return message.content
    .filter((b): b is Anthropic.TextBlock => b.type === "text")
    .map((b) => b.text)
    .join("\n")
    .trim();
}

/**
 * Plain text completion. Streams (so large outputs don't hit HTTP timeouts)
 * and uses adaptive thinking per current Opus guidance.
 */
export async function complete(opts: BaseOpts): Promise<string> {
  // Cast to `any`: `thinking.adaptive` / `output_config` may be newer than the
  // installed SDK's static types, but are valid on the wire for opus-4-8.
  const stream = client.messages.stream({
    model: CONFIG.model,
    max_tokens: opts.maxTokens ?? 8000,
    thinking: { type: "adaptive" },
    output_config: { effort: opts.effort ?? CONFIG.effort },
    system: opts.system,
    messages: [{ role: "user", content: opts.prompt }],
  } as any);
  return textFrom(await stream.finalMessage());
}

/**
 * Structured completion. Constrains the response to `jsonSchema` via
 * output_config.format, then validates the parsed payload with the matching
 * zod schema (belt-and-suspenders against any drift). Returns a typed object.
 */
export async function completeJSON<T>(
  zodSchema: z.ZodType<T>,
  jsonSchema: Record<string, unknown>,
  opts: BaseOpts,
): Promise<T> {
  const stream = client.messages.stream({
    model: CONFIG.model,
    max_tokens: opts.maxTokens ?? 8000,
    thinking: { type: "adaptive" },
    output_config: {
      effort: opts.effort ?? CONFIG.effort,
      format: { type: "json_schema", schema: jsonSchema },
    },
    system: opts.system,
    messages: [{ role: "user", content: opts.prompt }],
  } as any);

  const message = await stream.finalMessage();
  if ((message.stop_reason as string) === "refusal") {
    throw new Error("Request was refused by the model's safety system.");
  }
  const raw = stripCodeFences(textFrom(message));
  let parsed: unknown;
  try {
    parsed = JSON.parse(raw);
  } catch {
    throw new Error(`Model did not return valid JSON:\n${raw.slice(0, 500)}`);
  }
  return zodSchema.parse(parsed);
}
