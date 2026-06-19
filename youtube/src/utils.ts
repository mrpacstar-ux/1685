import fs from "node:fs";
import path from "node:path";
import { spawnSync } from "node:child_process";
import { OUT_DIR } from "./config.js";

export function slugify(text: string): string {
  return text
    .toLowerCase()
    .replace(/['’"]/g, "")
    .replace(/[^a-z0-9]+/g, "-")
    .replace(/^-+|-+$/g, "")
    .slice(0, 60)
    .replace(/-+$/g, "");
}

export function ensureDir(dir: string): string {
  fs.mkdirSync(dir, { recursive: true });
  return dir;
}

/** Directory for a single produced video package, e.g. out/<slug>/. */
export function packageDir(slug: string): string {
  return ensureDir(path.join(OUT_DIR, slug));
}

export function writeJson(file: string, data: unknown): void {
  ensureDir(path.dirname(file));
  fs.writeFileSync(file, JSON.stringify(data, null, 2) + "\n");
}

export function readJson<T>(file: string): T {
  return JSON.parse(fs.readFileSync(file, "utf8")) as T;
}

export function writeText(file: string, text: string): void {
  ensureDir(path.dirname(file));
  fs.writeFileSync(file, text.endsWith("\n") ? text : text + "\n");
}

/** Strip ```json fences a model may wrap JSON in, then return the raw payload. */
export function stripCodeFences(text: string): string {
  const fence = text.match(/```(?:json)?\s*([\s\S]*?)```/i);
  return (fence ? fence[1] : text).trim();
}

const ICON = { ok: "✓", info: "•", warn: "!", run: "→" } as const;
export function log(kind: keyof typeof ICON, msg: string): void {
  console.log(`${ICON[kind]} ${msg}`);
}

export function commandExists(cmd: string): boolean {
  const probe = process.platform === "win32" ? "where" : "which";
  return spawnSync(probe, [cmd], { stdio: "ignore" }).status === 0;
}
