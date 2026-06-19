import path from "node:path";
import sharp from "sharp";
import { BRAND } from "./config.js";
import { ensureDir, log } from "./utils.js";

/**
 * Deterministic channel brand assets (avatar + banner) rendered from SVG so
 * the visual identity is reproducible and version-controlled. No external
 * services — pure sharp.
 */

// Small seeded PRNG so the star field is identical every render.
function mulberry32(seed: number): () => number {
  let a = seed;
  return () => {
    a |= 0;
    a = (a + 0x6d2b79f5) | 0;
    let t = Math.imul(a ^ (a >>> 15), 1 | a);
    t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t;
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}

function starField(w: number, h: number, count: number, seed = 1685): string {
  const rnd = mulberry32(seed);
  const stars: string[] = [];
  for (let i = 0; i < count; i++) {
    const x = Math.round(rnd() * w);
    const y = Math.round(rnd() * h);
    const r = (rnd() * rnd() * 2 + 0.3).toFixed(2);
    const o = (0.3 + rnd() * 0.6).toFixed(2);
    stars.push(`<circle cx="${x}" cy="${y}" r="${r}" fill="#ffffff" opacity="${o}"/>`);
  }
  return stars.join("");
}

/** The brand mark: a ringed crescent-lit planet — readable at any size. */
function planetMark(cx: number, cy: number, r: number): string {
  return `
    <defs>
      <radialGradient id="planet" cx="35%" cy="30%" r="80%">
        <stop offset="0%" stop-color="#3a5aa8"/>
        <stop offset="60%" stop-color="#16224a"/>
        <stop offset="100%" stop-color="#070b1c"/>
      </radialGradient>
    </defs>
    <ellipse cx="${cx}" cy="${cy}" rx="${r * 1.7}" ry="${r * 0.42}"
      fill="none" stroke="${BRAND.accentColor}" stroke-width="${r * 0.07}"
      opacity="0.9" transform="rotate(-22 ${cx} ${cy})"/>
    <circle cx="${cx}" cy="${cy}" r="${r}" fill="url(#planet)"/>
    <circle cx="${cx - r * 0.28}" cy="${cy - r * 0.3}" r="${r * 0.95}"
      fill="#070b1c" opacity="0.45"/>`;
}

function escapeXml(s: string): string {
  return s.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
}

function avatarSvg(): string {
  const S = 1024;
  return `<svg xmlns="http://www.w3.org/2000/svg" width="${S}" height="${S}" viewBox="0 0 ${S} ${S}">
  <rect width="${S}" height="${S}" fill="${BRAND.baseColor}"/>
  <rect width="${S}" height="${S}" fill="#02030a" opacity="0.3"/>
  ${starField(S, S, 90, 7)}
  ${planetMark(S / 2, S / 2, 250)}
</svg>`;
}

function bannerSvg(): string {
  const W = 2560;
  const H = 1440;
  // YouTube "text & logo safe area" is the centered 1546×423 region.
  const cx = W / 2;
  const cy = H / 2;
  return `<svg xmlns="http://www.w3.org/2000/svg" width="${W}" height="${H}" viewBox="0 0 ${W} ${H}">
  <defs>
    <radialGradient id="bg" cx="50%" cy="38%" r="75%">
      <stop offset="0%" stop-color="#1b2c5a"/>
      <stop offset="55%" stop-color="${BRAND.baseColor}"/>
      <stop offset="100%" stop-color="#02030a"/>
    </radialGradient>
  </defs>
  <rect width="${W}" height="${H}" fill="url(#bg)"/>
  ${starField(W, H, 260, 1685)}
  ${planetMark(cx - 520, cy, 120)}
  <text x="${cx}" y="${cy - 10}" text-anchor="middle"
    font-family="Arial, Helvetica, sans-serif" font-size="150" font-weight="900"
    fill="#ffffff" letter-spacing="6">${escapeXml(BRAND.name.toUpperCase())}</text>
  <text x="${cx}" y="${cy + 80}" text-anchor="middle"
    font-family="Georgia, 'Times New Roman', serif" font-size="56" font-style="italic"
    fill="${BRAND.accentColor}" letter-spacing="2">${escapeXml(BRAND.tagline)}</text>
</svg>`;
}

export async function makeBrandAssets(dir: string): Promise<{ avatar: string; banner: string }> {
  ensureDir(dir);
  const avatar = path.join(dir, "avatar.png");
  const banner = path.join(dir, "banner.png");
  await sharp(Buffer.from(avatarSvg())).png().toFile(avatar);
  await sharp(Buffer.from(bannerSvg())).png().toFile(banner);
  log("ok", `Brand assets rendered: avatar.png (1024²), banner.png (2560×1440)`);
  return { avatar, banner };
}
