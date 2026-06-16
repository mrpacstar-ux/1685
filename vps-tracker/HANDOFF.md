# KD1685 — "Personal Statsmaster" build & bot handoff (for Claude Code)

**Goal:** kd1685.com should be Kingdom 1685's own private Statsmaster — a per-player
stats board (power, kills/KP, deads, T4/T5) with history/trends, fed automatically
from Statsmaster and stored in Supabase. You have **git access to
`mrpacstar-ux/1685`** and **SSH to the VPS** that hosts the site.

There are two halves:
- **The bot** (`vps-tracker/sync.js`) — scrapes Statsmaster → writes Supabase. (This package.)
- **The front end** (`index.html` in the repo) — reads Supabase → renders the board.

---

## 1. Why the old bot "couldn't collect names/data"
The original `sync.js` scraped **rendered page text** with regexes (`X: Y:` for forts,
`123B Power` for KvK). That only ever captured **two kingdom-level numbers** and no
real per-player rows, and it broke whenever Statsmaster's layout shifted — silently,
because it caught all errors, exited green, and fell back to a **hardcoded service_role
key** baked into the file.

## 2. What the new bot does differently (`vps-tracker/sync.js` v2)
- **Reads structured JSON, not text.** It attaches a network listener and captures
  every JSON response the dashboard fetches, then heuristically finds the array of
  player objects and maps fields (name/power/kills/deads/T4/T5) regardless of exact
  key names. This is the fix for per-player names + numbers.
- **DOM-table fallback.** If no usable JSON is seen, it reads the largest HTML table
  and maps columns by header text.
- **Writes a real roster + history.** Upserts `players` (current, keyed on
  `governor_id`) and `player_snapshots` (one row per governor per day → trends).
  No more delete-all wipe of player data.
- **Destructive-write guard.** If a scrape returns fewer than `MIN_KEEP_RATIO`
  (default 50%) of the previous row count, it refuses to write, dumps debug, exits 1.
- **Loud failure.** Secrets are env-only, every Supabase `.error` is checked, and
  any failure → `process.exit(1)` so the systemd timer / monitoring sees red.
- **Self-diagnosing.** On empty/low yield it writes `debug/<tag>.png`,
  `debug/<tag>.html`, and `debug/<tag>.endpoints.json` (the JSON endpoints + their
  top-level keys) so you can fix field mapping in minutes.

## 3. Files in this package (`vps-tracker/`)
| File | Purpose |
|---|---|
| `sync.js` | The v2 bot (JSON-first scraper, guarded writes, snapshots, debug dumps). |
| `schema.sql` | Creates `players`, `player_snapshots`, `fort_tracking`, `kingdom_stats` + read-only RLS. |
| `auth_schema.sql` | Creates `users`, `invites`, `user_audit` + officer RLS for accounts. |
| `AUTH.md` | Full accounts spec: Discord OAuth + officer-issued passcodes, role model, how R4/R5 give accounts. |
| `FRONTEND.md` | How to make the new design the live site: swap mock data → Supabase, wire auth. |
| `index.html` | The new design, self-contained — the new live front end (replaces old repo index.html). |
| `discord-role-sync/index.ts` | Supabase Edge Function: maps Discord R4/R5 roles → site roles. |
| `package.json` | Deps: `@supabase/supabase-js`, `playwright`, `axios`, `cheerio`. |
| `.env.example` | `SUPABASE_URL`, `SUPABASE_SERVICE_KEY`, page links, `MIN_KEEP_RATIO`. |
| `kd1685-sync.service` / `.timer` | systemd one-shot + 30-min timer (runs on the VPS, not GitHub). |
| `setup.sh` | Installer: Node 20, user, npm deps, Playwright Chromium + OS libs, enables timer. |
| `.gitignore` | keeps `.env`, `node_modules/`, `debug/` out of git. |

---

## 4. Deploy (over SSH on the VPS)
```bash
# A. Database first — apply schema.sql in Supabase SQL editor (or psql).

# B. Code onto the box
sudo mkdir -p /opt/kd1685-tracker
# copy the vps-tracker/ contents into /opt/kd1685-tracker

# C. Secrets — CURRENT service_role key from Supabase -> Settings -> API
sudo cp .env.example /opt/kd1685-tracker/.env
sudo nano /opt/kd1685-tracker/.env

# D. Install + schedule (run from inside the folder)
cd /opt/kd1685-tracker
bash setup.sh            # or do the manual steps in section 6

# E. Test once and WATCH it
sudo systemctl start kd1685-sync.service
journalctl -u kd1685-sync -f
```
Expected log: `Players parsed: N (via json)` with N in the hundreds, then
`Wrote N players + snapshot YYYY-MM-DD.`

## 5. Verify DATA landed (not just that it ran)
In Supabase SQL editor:
```sql
select count(*) from players;
select name, power, kills, deads from players order by power desc limit 10;
select scan_date, count(*) from player_snapshots group by scan_date order by scan_date desc;
select last_sync from kingdom_stats where id = 1;
```

## 6. Manual install (if not using setup.sh)
```bash
cd /opt/kd1685-tracker
npm install --omit=dev
npx playwright install-deps chromium
npx playwright install chromium
sudo cp kd1685-sync.service kd1685-sync.timer /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now kd1685-sync.timer
systemctl list-timers kd1685-sync.timer
```

## 7. If players come back empty
1. Open `/opt/kd1685-tracker/debug/players.endpoints.json` — this lists the JSON
   responses the page made and their top-level keys. Find the one that holds the
   governor list.
2. If the player array is nested or uses unusual field names, tighten the `KEY`
   regexes / `mapFields()` in `sync.js`, or set `PLAYERS_LINK` in `.env` to a
   dedicated per-player ranking URL on Statsmaster.
3. If Statsmaster renders the table only in HTML (no JSON), the DOM-table fallback
   should catch it — check `debug/players.html` for the table headers and adjust the
   header regexes in `extractPlayersFromDom()`.

## 8. Wire the front end (`index.html`) to the new data
**The new design is the live site.** `index.html` in this package is the new design
exported as a self-contained file — it replaces the old repo `index.html`. It currently
renders from built-in mock data. **See `FRONTEND.md`** for the exact swap: there's a
single data entry point (`_build()`) to repoint at Supabase `players`/`player_snapshots`,
plus the table mapping and the auth-wiring checklist (issue/redeem/verify/role → `users`/
`invites`). The site should read from Supabase with the **anon** key (never the service key):
```js
const sb = supabase.createClient(SUPABASE_URL, SUPABASE_ANON_KEY);
const { data: players } = await sb
  .from('players').select('*').order('power', { ascending: false });
// trends: select from player_snapshots where governor_id = ... order by scan_date
```
RLS in `schema.sql` already allows public SELECT on these tables and blocks writes,
so the anon key is safe to ship in `index.html`.

## 8b. Accounts & auth (how R4/R5 give accounts)
See **`AUTH.md`** + **`auth_schema.sql`**. Summary: built on Supabase Auth, two paths —
- **Discord OAuth** (primary): officers in the 1685 Discord become officers on the site.
- **Officer-issued invite codes** (fallback): R4/R5 generate a code/passcode from the
  Members view; the member redeems it to claim their governor + role.
Roles are `r5`/`r4`/`member`; RLS enforces that only officers can write users/invites.
Bootstrap yourself as R5 once (instructions in `AUTH.md`).

## 9. Cleanup once the VPS run is healthy
- Disable the old GitHub Actions workflow (`.github/workflows/main.yml`) so it isn't
  double-writing.
- **Rotate the Supabase service_role key** — the old one is committed in git history
  (`sync.js`). Generate a new key, put it only in `/opt/kd1685-tracker/.env`.
- Confirm `.env` is gitignored.
