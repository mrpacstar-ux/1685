import path from "node:path";
import sharp from "sharp";
import { BRAND } from "./config.js";
import { log } from "./utils.js";

const W = 1280;
const H = 720;

function escapeXml(s: string): string {
  return s
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&apos;");
}

/** Wrap the thumbnail phrase into balanced lines (max 2 words each). */
function wrap(text: string): string[] {
  const words = text.trim().split(/\s+/);
  const lines: string[] = [];
  for (let i = 0; i < words.length; i += 2) {
    lines.push(words.slice(i, i + 2).join(" "));
  }
  return lines.slice(0, 3);
}

const BG = `
  <defs>
    <radialGradient id="bg" cx="70%" cy="30%" r="90%">
      <stop offset="0%" stop-color="#1b2c5a"/>
      <stop offset="55%" stop-color="${BRAND.baseColor}"/>
      <stop offset="100%" stop-color="#02030a"/>
    </radialGradient>
  </defs>
  <rect width="${W}" height="${H}" fill="url(#bg)"/>`;

/** Variant A — left-aligned text, accent bar, planet upper-right. */
function variantA(text: string): string {
  const lines = wrap(text.toUpperCase());
  const fontSize = lines.length >= 3 ? 116 : 148;
  const lineHeight = fontSize * 1.05;
  const startY = H / 2 - (lines.length * lineHeight) / 2 + fontSize * 0.78;
  const tspans = lines
    .map(
      (line, i) =>
        `<text x="86" y="${startY + i * lineHeight}" font-family="Arial, Helvetica, sans-serif" font-size="${fontSize}" font-weight="900" fill="#ffffff" stroke="#000000" stroke-width="6" paint-order="stroke">${escapeXml(line)}</text>`,
    )
    .join("\n    ");
  return `<svg xmlns="http://www.w3.org/2000/svg" width="${W}" height="${H}" viewBox="0 0 ${W} ${H}">
  ${BG}
  <circle cx="1000" cy="190" r="150" fill="#2a3c70"/>
  <ellipse cx="1000" cy="190" rx="230" ry="60" fill="none" stroke="${BRAND.accentColor}" stroke-width="9" opacity="0.85" transform="rotate(-20 1000 190)"/>
  <rect x="64" y="${H / 2 - lines.length * 80}" width="14" height="${lines.length * 160}" fill="${BRAND.accentColor}"/>
    ${tspans}
  <text x="86" y="${H - 48}" font-family="Arial, Helvetica, sans-serif" font-size="32" font-weight="700" fill="${BRAND.accentColor}" letter-spacing="2">${escapeXml(BRAND.name.toUpperCase())}</text>
</svg>`;
}

/** Variant B — centered text, amber underline, planet lower-left. */
function variantB(text: string): string {
  const lines = wrap(text.toUpperCase());
  const fontSize = lines.length >= 3 ? 108 : 138;
  const lineHeight = fontSize * 1.08;
  const startY = H / 2 - (lines.length * lineHeight) / 2 + fontSize * 0.78 - 20;
  const tspans = lines
    .map(
      (line, i) =>
        `<text x="${W / 2}" y="${startY + i * lineHeight}" text-anchor="middle" font-family="Arial, Helvetica, sans-serif" font-size="${fontSize}" font-weight="900" fill="#ffffff" stroke="#000000" stroke-width="6" paint-order="stroke">${escapeXml(line)}</text>`,
    )
    .join("\n    ");
  const underlineY = startY + lines.length * lineHeight - fontSize * 0.1;
  return `<svg xmlns="http://www.w3.org/2000/svg" width="${W}" height="${H}" viewBox="0 0 ${W} ${H}">
  ${BG}
  <circle cx="190" cy="600" r="180" fill="#2a3c70" opacity="0.7"/>
    ${tspans}
  <rect x="${W / 2 - 170}" y="${underlineY}" width="340" height="12" rx="6" fill="${BRAND.accentColor}"/>
  <text x="${W / 2}" y="${H - 44}" text-anchor="middle" font-family="Arial, Helvetica, sans-serif" font-size="30" font-weight="700" fill="${BRAND.accentColor}" letter-spacing="3">${escapeXml(BRAND.name.toUpperCase())}</text>
</svg>`;
}

async function render(svg: string, file: string): Promise<string> {
  await sharp(Buffer.from(svg)).png().toFile(file);
  return file;
}

/** Render a single thumbnail (variant A). Kept for convenience. */
export async function makeThumbnail(text: string, dir: string): Promise<string> {
  const file = await render(variantA(text), path.join(dir, "thumbnail.png"));
  log("ok", `Thumbnail rendered: thumbnail.png ("${text}")`);
  return file;
}

/** Render both A/B thumbnail variants for the 50%-rule test workflow. */
export async function makeThumbnails(text: string, dir: string): Promise<string[]> {
  const a = await render(variantA(text), path.join(dir, "thumbnail.png"));
  const b = await render(variantB(text), path.join(dir, "thumbnail-b.png"));
  log("ok", `Thumbnails rendered: thumbnail.png [A] + thumbnail-b.png [B] ("${text}")`);
  return [a, b];
}
