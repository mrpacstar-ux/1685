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

function buildSvg(text: string): string {
  const lines = wrap(text.toUpperCase());
  const fontSize = lines.length >= 3 ? 120 : 150;
  const lineHeight = fontSize * 1.05;
  const blockHeight = lines.length * lineHeight;
  const startY = H / 2 - blockHeight / 2 + fontSize * 0.8;

  const tspans = lines
    .map((line, i) => {
      const y = startY + i * lineHeight;
      return `<text x="80" y="${y}" font-family="Arial, Helvetica, sans-serif" font-size="${fontSize}" font-weight="900" fill="#ffffff" stroke="#000000" stroke-width="6" paint-order="stroke">${escapeXml(line)}</text>`;
    })
    .join("\n    ");

  return `<svg xmlns="http://www.w3.org/2000/svg" width="${W}" height="${H}" viewBox="0 0 ${W} ${H}">
  <defs>
    <radialGradient id="bg" cx="70%" cy="30%" r="90%">
      <stop offset="0%" stop-color="#1b2c5a"/>
      <stop offset="55%" stop-color="${BRAND.baseColor}"/>
      <stop offset="100%" stop-color="#02030a"/>
    </radialGradient>
  </defs>
  <rect width="${W}" height="${H}" fill="url(#bg)"/>
  <circle cx="980" cy="200" r="150" fill="${BRAND.accentColor}" opacity="0.18"/>
  <rect x="80" y="${H / 2 - (wrap(text).length * 80) - 20}" width="14" height="${wrap(text).length * 160}" fill="${BRAND.accentColor}"/>
    ${tspans}
  <text x="80" y="${H - 50}" font-family="Arial, Helvetica, sans-serif" font-size="34" font-weight="700" fill="${BRAND.accentColor}" letter-spacing="2">${escapeXml(BRAND.name.toUpperCase())}</text>
</svg>`;
}

/** Render a 1280×720 thumbnail PNG from the thumbnail phrase. */
export async function makeThumbnail(text: string, dir: string): Promise<string> {
  const file = path.join(dir, "thumbnail.png");
  const svg = buildSvg(text);
  await sharp(Buffer.from(svg)).png().toFile(file);
  log("ok", `Thumbnail rendered: thumbnail.png ("${text}")`);
  return file;
}
