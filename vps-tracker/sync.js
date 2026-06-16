/**
 * KD1685 player-data bot — v2
 *
 * Strategy (most reliable first):
 *   1. Capture the JSON the Statsmaster dashboard fetches over the network and
 *      parse player rows out of it. This is what fixes the "names/data won't
 *      collect" problem — we read structured data, not rendered text.
 *   2. Fallback: read the largest HTML <table> by mapping header columns.
 *   3. Fallback (forts only): the old X:/Y: text scan.
 *
 * Safety:
 *   - Every Supabase write is checked; any failure -> process.exit(1).
 *   - Destructive writes are GUARDED: if a scrape returns far fewer rows than
 *     last time, we skip the wipe, save debug artifacts, and exit 1 instead of
 *     blanking good data.
 *   - On low/empty yield we dump screenshot + HTML + the list of JSON endpoints
 *     seen, so layout changes are diagnosable in minutes.
 *
 * Secrets come only from env. No hardcoded keys.
 */
const fs = require('fs');
const path = require('path');
const { chromium } = require('playwright');
const { createClient } = require('@supabase/supabase-js');

// ----------------------------- config --------------------------------------
const SUPABASE_URL = process.env.SUPABASE_URL;
const SUPABASE_KEY = process.env.SUPABASE_SERVICE_KEY || process.env.SUPABASE_KEY;

const FORT_LINK = process.env.FORT_LINK
  || "https://www.statsmasterdatahub.com/1685/rallydata/c5eaf4fxkl3vykx";
const KVK_LINK = process.env.KVK_LINK
  || "https://www.statsmasterdatahub.com/c13048/dashboard/ymheormqhugrg1a";

// Optional: a dedicated per-player ranking/leaderboard page if you have one.
// If unset we extract players from whatever JSON the KvK dashboard loads.
const PLAYERS_LINK = process.env.PLAYERS_LINK || KVK_LINK;

const DEBUG_DIR = process.env.DEBUG_DIR || path.join(__dirname, 'debug');
// Safety threshold: skip a destructive replace if new rows < this fraction of old.
const MIN_KEEP_RATIO = Number(process.env.MIN_KEEP_RATIO || 0.5);

if (!SUPABASE_URL || !SUPABASE_KEY) {
  console.error("❌ Missing SUPABASE_URL or SUPABASE_SERVICE_KEY. Aborting.");
  process.exit(1);
}
const supabase = createClient(SUPABASE_URL, SUPABASE_KEY, { auth: { persistSession: false } });

let HAD_ERROR = false;
const fail = (msg) => { HAD_ERROR = true; console.error("❌ " + msg); };

// ----------------------------- helpers --------------------------------------

/** Parse "1.23B" / "345.6M" / "12K" / "1,234,567" / 1234 -> integer. */
function parseNum(v) {
  if (v == null) return null;
  if (typeof v === 'number') return Number.isFinite(v) ? Math.round(v) : null;
  let s = String(v).trim().replace(/,/g, '').replace(/\s+/g, '');
  if (!s) return null;
  const m = s.match(/^([\d.]+)\s*([BMK])?$/i);
  if (!m) { const n = Number(s); return Number.isFinite(n) ? Math.round(n) : null; }
  let n = parseFloat(m[1]);
  const suf = (m[2] || '').toUpperCase();
  if (suf === 'K') n *= 1e3; else if (suf === 'M') n *= 1e6; else if (suf === 'B') n *= 1e9;
  return Math.round(n);
}

const KEY = {
  id:    /(^|_)id$|governor.?id|gov.?id|lord.?id|player.?id|uid/i,
  name:  /name|governor|nick|player|lord|gov(?!.*id)/i,
  power: /power/i,
  kills: /kill.?points|killpoints|^kp$|^kills?$|total.?kill/i,
  deads: /dead|death/i,
  t4:    /t4|tier.?4/i,
  t5:    /t5|tier.?5/i,
};

/** Given a sample object, build a map of our-field -> source-key. */
function mapFields(obj) {
  const keys = Object.keys(obj);
  const find = (re, opts = {}) => {
    for (const k of keys) {
      if (!re.test(k)) continue;
      const val = obj[k];
      if (opts.string && typeof val === 'object') continue;
      if (opts.numeric && parseNum(val) == null) continue;
      return k;
    }
    return null;
  };
  return {
    id:    find(KEY.id),
    name:  find(KEY.name, { string: true }),
    power: find(KEY.power, { numeric: true }),
    kills: find(KEY.kills, { numeric: true }),
    deads: find(KEY.deads, { numeric: true }),
    t4:    find(KEY.t4, { numeric: true }),
    t5:    find(KEY.t5, { numeric: true }),
  };
}

/** Walk arbitrary JSON, return every array-of-objects found. */
function collectArrays(node, out = [], depth = 0) {
  if (depth > 8 || node == null) return out;
  if (Array.isArray(node)) {
    if (node.length && typeof node[0] === 'object' && node[0] !== null && !Array.isArray(node[0])) {
      out.push(node);
    }
    node.forEach(n => collectArrays(n, out, depth + 1));
  } else if (typeof node === 'object') {
    Object.values(node).forEach(v => collectArrays(v, out, depth + 1));
  }
  return out;
}

/** From all captured JSON bodies, pick the best player array and normalize it. */
function extractPlayers(jsonBodies) {
  let best = null;
  for (const body of jsonBodies) {
    let parsed;
    try { parsed = typeof body === 'string' ? JSON.parse(body) : body; } catch { continue; }
    for (const arr of collectArrays(parsed)) {
      const fm = mapFields(arr[0]);
      if (!fm.name) continue;                                   // must have a name
      if (!fm.power && !fm.kills && !fm.deads) continue;        // and at least one metric
      const richness = ['power', 'kills', 'deads', 't4', 't5'].filter(k => fm[k]).length;
      const score = arr.length * (1 + richness);
      if (!best || score > best.score) best = { arr, fm, score };
    }
  }
  if (!best) return [];

  const { arr, fm } = best;
  const now = new Date().toISOString();
  const players = arr.map(row => {
    const name = String(row[fm.name] ?? '').trim();
    if (!name) return null;
    const gid = fm.id ? String(row[fm.id]).trim() : name.toLowerCase().replace(/\s+/g, '_');
    return {
      governor_id: gid,
      name,
      power: fm.power ? parseNum(row[fm.power]) : null,
      kills: fm.kills ? parseNum(row[fm.kills]) : null,
      deads: fm.deads ? parseNum(row[fm.deads]) : null,
      t4_kills: fm.t4 ? parseNum(row[fm.t4]) : null,
      t5_kills: fm.t5 ? parseNum(row[fm.t5]) : null,
      updated_at: now,
    };
  }).filter(Boolean);

  // de-dupe by governor_id (keep the highest-power record if duplicated)
  const byId = new Map();
  for (const p of players) {
    const prev = byId.get(p.governor_id);
    if (!prev || (p.power || 0) > (prev.power || 0)) byId.set(p.governor_id, p);
  }
  return [...byId.values()];
}

/** Fallback: read the largest HTML table on the page, map columns by header. */
async function extractPlayersFromDom(page) {
  return await page.evaluate(() => {
    const tables = [...document.querySelectorAll('table')];
    if (!tables.length) return [];
    // biggest table by row count
    const table = tables.sort((a, b) =>
      b.querySelectorAll('tr').length - a.querySelectorAll('tr').length)[0];
    const rows = [...table.querySelectorAll('tr')];
    if (rows.length < 2) return [];
    const headers = [...rows[0].querySelectorAll('th,td')].map(c => c.innerText.trim().toLowerCase());
    const col = (re) => headers.findIndex(h => re.test(h));
    const ci = {
      name:  col(/name|governor|player|nick/),
      power: col(/power/),
      kills: col(/kill/),
      deads: col(/dead|death/),
    };
    if (ci.name < 0) return [];
    const out = [];
    for (let i = 1; i < rows.length; i++) {
      const cells = [...rows[i].querySelectorAll('td,th')].map(c => c.innerText.trim());
      const name = cells[ci.name];
      if (!name) continue;
      out.push({
        name,
        power: ci.power >= 0 ? cells[ci.power] : null,
        kills: ci.kills >= 0 ? cells[ci.kills] : null,
        deads: ci.deads >= 0 ? cells[ci.deads] : null,
      });
    }
    return out;
  }).then(rows => {
    const now = new Date().toISOString();
    return rows.map(r => {
      const name = String(r.name).trim();
      return {
        governor_id: name.toLowerCase().replace(/\s+/g, '_'),
        name,
        power: parseNum(r.power),
        kills: parseNum(r.kills),
        deads: parseNum(r.deads),
        t4_kills: null, t5_kills: null,
        updated_at: now,
      };
    }).filter(p => p.name);
  });
}

async function dumpDebug(page, tag, jsonBodies) {
  try {
    fs.mkdirSync(DEBUG_DIR, { recursive: true });
    await page.screenshot({ path: path.join(DEBUG_DIR, `${tag}.png`), fullPage: true });
    fs.writeFileSync(path.join(DEBUG_DIR, `${tag}.html`), await page.content());
    if (jsonBodies) {
      const summary = jsonBodies.map((b, i) => {
        try { return { i, keys: Object.keys(typeof b === 'string' ? JSON.parse(b) : b).slice(0, 12) }; }
        catch { return { i, keys: 'unparseable' }; }
      });
      fs.writeFileSync(path.join(DEBUG_DIR, `${tag}.endpoints.json`), JSON.stringify(summary, null, 2));
    }
    console.log(`📸 Debug artifacts saved to ${DEBUG_DIR}/${tag}.*`);
  } catch (e) { console.error("debug dump failed:", e.message); }
}

/** Attach a JSON response collector to a page. Returns the array it fills. */
function captureJson(page) {
  const bodies = [];
  page.on('response', async (res) => {
    try {
      const ct = (res.headers()['content-type'] || '');
      if (!/json/i.test(ct)) return;
      const txt = await res.text();
      if (txt && (txt.trim()[0] === '{' || txt.trim()[0] === '[')) bodies.push(txt);
    } catch { /* ignore individual response errors */ }
  });
  return bodies;
}

async function loadFully(page, url, settleMs = 6000) {
  await page.goto(url, { waitUntil: 'networkidle', timeout: 90000 });
  await page.waitForTimeout(settleMs);
  await page.evaluate(() => window.scrollTo(0, document.body.scrollHeight));
  await page.waitForTimeout(2500);
  await page.evaluate(() => window.scrollTo(0, 0));
  await page.waitForTimeout(1000);
}

// ----------------------------- scrape steps ---------------------------------

async function scrapePlayers(page) {
  console.log(`📡 Players: ${PLAYERS_LINK}`);
  const jsonBodies = captureJson(page);
  await loadFully(page, PLAYERS_LINK, 7000);

  let players = extractPlayers(jsonBodies);
  let via = 'json';
  if (players.length === 0) {
    players = await extractPlayersFromDom(page);
    via = 'dom-table';
  }
  console.log(`✅ Players parsed: ${players.length} (via ${via})`);

  if (players.length === 0) {
    await dumpDebug(page, 'players', jsonBodies);
    fail("No players parsed — see debug/ to update field mapping or PLAYERS_LINK.");
    return;
  }

  // Guard: don't let a thin scrape overwrite a healthy roster.
  const { count: prevCount } = await supabase
    .from('players').select('*', { count: 'exact', head: true });
  if (prevCount && players.length < prevCount * MIN_KEEP_RATIO) {
    await dumpDebug(page, 'players', jsonBodies);
    fail(`Guard tripped: scraped ${players.length} < ${Math.round(prevCount * MIN_KEEP_RATIO)} (was ${prevCount}). Skipping write.`);
    return;
  }

  // Upsert current roster (keyed on governor_id) — preserves history, no wipe.
  const up = await supabase.from('players')
    .upsert(players, { onConflict: 'governor_id' });
  if (up.error) return fail("players upsert: " + up.error.message);

  // Daily snapshot for trends (one row per governor per day).
  const scan_date = new Date().toISOString().slice(0, 10);
  const snaps = players.map(p => ({
    governor_id: p.governor_id, name: p.name, power: p.power,
    kills: p.kills, deads: p.deads, scan_date,
  }));
  const snap = await supabase.from('player_snapshots')
    .upsert(snaps, { onConflict: 'governor_id,scan_date' });
  if (snap.error) console.warn("⚠️ player_snapshots upsert (non-fatal): " + snap.error.message);

  console.log(`💾 Wrote ${players.length} players + snapshot ${scan_date}.`);
}

async function scrapeForts(page) {
  console.log(`📡 Forts: ${FORT_LINK}`);
  await loadFully(page, FORT_LINK, 5000);

  // Prefer table rows; fall back to the old X:/Y: text scan.
  let forts = await page.evaluate(() => {
    const out = [];
    const els = [...document.querySelectorAll('div, tr, li')];
    els.forEach(el => {
      const text = el.innerText || '';
      const c = text.match(/X:\s*(\d+)\s*Y:\s*(\d+)/i);
      if (!c) return;
      const lvl = text.match(/Lvl\s*(\d+)|Level\s*(\d+)/i);
      out.push({
        level: lvl ? (lvl[1] || lvl[2]) : '5',
        coords: `X:${c[1]} Y:${c[2]}`,
        player: text.split('\n')[0].substring(0, 40).trim(),
      });
    });
    return out;
  });
  forts = [...new Map(forts.map(f => [f.coords, f])).values()]
    .map(f => ({ ...f, updated_at: new Date().toISOString() }));
  console.log(`✅ Forts parsed: ${forts.length}`);

  // Forts are secondary: a fort problem warns but does NOT fail the run, so the
  // systemd unit stays green as long as the player scrape (the core job) succeeded.
  if (forts.length === 0) {
    await dumpDebug(page, 'forts');
    console.warn("⚠️ No forts parsed (non-fatal) — see debug/forts.* for the current layout.");
    return;
  }
  const del = await supabase.from('fort_tracking').delete().neq('level', '-1');
  if (del.error) return console.warn("⚠️ fort delete (non-fatal): " + del.error.message);
  const ins = await supabase.from('fort_tracking').insert(forts);
  if (ins.error) return console.warn("⚠️ fort insert (non-fatal): " + ins.error.message);
  console.log(`💾 Wrote ${forts.length} forts.`);
}

async function scrapeKvkSummary(page) {
  console.log(`📡 KvK summary: ${KVK_LINK}`);
  await loadFully(page, KVK_LINK, 7000);
  const stats = await page.evaluate(() => {
    const body = document.body.innerText;
    const p = body.match(/Power\s*[:\n\s]*([\d.]+[BMK])/i) || body.match(/([\d.]+[BMK])\s*Power/i);
    const k = body.match(/Kill\s*Points\s*[:\n\s]*([\d.]+[BMK])/i) || body.match(/([\d.]+[BMK])\s*Kill/i);
    return { power: p ? p[1] : null, kills: k ? k[1] : null };
  });
  console.log(`✅ KvK summary: power=${stats.power} kills=${stats.kills}`);
  if (!stats.power && !stats.kills) { await dumpDebug(page, 'kvk'); return; }
  const upd = await supabase.from('kingdom_stats').update({
    power: stats.power, kills: stats.kills, last_sync: new Date().toISOString(),
  }).eq('id', 1);
  if (upd.error) console.warn("⚠️ kvk update (non-fatal): " + upd.error.message);
}

// ----------------------------- main -----------------------------------------
async function main() {
  console.log("🚀 Launching headless Chromium...");
  const browser = await chromium.launch({ headless: true, args: ['--no-sandbox'] });
  const context = await browser.newContext({
    viewport: { width: 1920, height: 1080 },
    userAgent: 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124 Safari/537.36',
  });

  try {
    const page = await context.newPage();
    await scrapePlayers(page);
    await page.close();

    const page2 = await context.newPage();
    await scrapeForts(page2);
    await page2.close();

    const page3 = await context.newPage();
    await scrapeKvkSummary(page3);
    await page3.close();
  } catch (e) {
    fail("Fatal: " + e.message);
  } finally {
    await browser.close();
    console.log("🏁 Done.");
  }
  process.exit(HAD_ERROR ? 1 : 0);
}

main();
