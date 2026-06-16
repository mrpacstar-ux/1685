# Front end — make the new design the live kd1685.com

**The new design IS the live site.** `vps-tracker/index.html` is the new design
exported as a single self-contained file (all CSS/JS/fonts inlined, works offline).
It replaces the old `index.html` in the repo.

Right now it renders from **built-in mock data** (48 seeded governors) so the UI is
fully alive without a backend. Your job: **swap the mock data for live Supabase data**
and **wire the officer/member actions to the real `users`/`invites` tables**. The UI,
layout, routing, and styling do not need to change.

## The ONE data entry point
All governor data is produced by a single method in the page's logic class,
`_build()`, which returns:
```js
return { governors, alliances, byTag, scans, days, enemyKingdoms };
```
and is assigned once: `_data = this._build();`

**Replace the mock `governors` array with rows from Supabase `players`
(+ `player_snapshots` for history).** Keep the returned shape identical so the rest of
the app keeps working untouched.

### Governor shape the UI expects  ← map from the bot's tables
| UI field (per governor) | Source (Supabase) | Notes |
|---|---|---|
| `id` | `players.governor_id` | string |
| `name` | `players.name` | |
| `tag` | alliance tag | from your alliance mapping; default a single tag if unused |
| `power` | `players.power` | current |
| `kpTotal` | `players.kills` | total kill points |
| `deathsTotal` | `players.deads` | |
| `t4`, `t5` | `players.t4_kills`, `players.t5_kills` | `t1..t3` optional — derive or 0 |
| `series` | from `player_snapshots` | array over scans: `{power, kp, deaths}` per snapshot date |
| `hist` | from `player_snapshots` | daily power array for the sparkline; if you lack daily history, repeat current power |
| `reqTarget` | derived | keep the existing formula or your own season target |
| `status`, `lastActive` | derived from `series` | "active/low/inactive/migrated" by recent gains; keep existing logic |
| `linked`, `role` | from `users` table | see auth wiring below |
| `honor`, `prekvk`, `rss`, `assist`, `helps`, `cmds`, etc. | optional | leave mock/0 until you scrape them; UI tolerates absence |

Minimum viable swap: fill `id, name, power, kpTotal, deathsTotal, t4, t5`. Build `series`
from snapshots if you have ≥2 dates; otherwise synthesize a flat series so charts render.

### Sketch
```js
async _build() {
  const sb = supabase.createClient(SUPABASE_URL, SUPABASE_ANON_KEY);
  const { data: players } = await sb.from('players').select('*');
  const { data: snaps }   = await sb.from('player_snapshots')
    .select('*').order('scan_date', { ascending: true });
  const byGov = groupBy(snaps, 'governor_id');

  const governors = players.map(p => {
    const s = (byGov[p.governor_id] || []);
    const series = s.map(r => ({ power: r.power, kp: r.kills, deaths: r.deads }));
    return {
      id: p.governor_id, name: p.name, tag: 'WW85',
      power: p.power, kpTotal: p.kills, deathsTotal: p.deads,
      t4: p.t4_kills || 0, t5: p.t5_kills || 0,
      series: series.length ? series : [{ power:p.power, kp:p.kills, deaths:p.deads }],
      hist: s.length ? s.map(r => r.power) : [p.power],
      // ...derive reqTarget/status/lastActive with the existing helpers...
    };
  });
  // build `scans` from the distinct snapshot dates; keep alliances/enemyKingdoms as-is
  return { governors, alliances, byTag, scans, days, enemyKingdoms };
}
```
`_build()` is currently synchronous and runs at construction. Make data loading async:
render the mock/empty state first, then `await` Supabase in `componentDidMount`, set the
result into state, and have `renderVals()` read from state. Don't block first paint.

## Auth wiring (replace the localStorage prototype)
The Members view + the `/join` screen already work against **localStorage** as a preview.
Repoint these to Supabase (`users`, `invites` — schema in `auth_schema.sql`):
| Prototype method (in logic) | Real backend |
|---|---|
| `issueInvite()` | `insert into invites (...)` (officer only via RLS) |
| `revokeInvite(code)` | `update invites set revoked=true` |
| `redeemInvite()` (join screen) | validate `invites` row, create/link `users` row, mark used |
| `verifyMember(id)` | `update users set status='active'` + audit row |
| `setMemberRole(id, role)` | `update users set role=...` (officer only) |
| login / "Continue with Discord" | `supabase.auth.signInWithOAuth({ provider:'discord' })` |

Gate officer-only UI on the signed-in user's `role` (`r4`/`r5`); RLS enforces it server-side.

## Keys
- `index.html` uses the **anon** key only. RLS (in the schemas) allows public SELECT on
  `players`/`player_snapshots`/`fort_tracking`/`kingdom_stats` and blocks writes.
- The bot uses the **service_role** key on the VPS. Never put it in `index.html`.

## Deploy
Serve `index.html` from the VPS (nginx/caddy static root) or commit it as the repo's
`index.html`. It's fully self-contained — no build step, no external assets.

## Editing the design later
`index.html` is a generated bundle — don't hand-edit it. The editable source is the
design file (`Kingdom 1685.dc.html`); re-export to regenerate `index.html` when the
design changes.
