# KD1685 — Accounts & Auth spec (for Claude Code)

How governors get accounts and how **R4/R5 give / manage** them. Two login paths,
one role model. Built on **Supabase Auth** so you don't run your own password store.

---

## Role model
| Role | In game | Can do on the site |
|---|---|---|
| `r5` | King / leader | Everything: set any role (incl. other R4/R5), issue invites, verify, suspend, edit kingdom settings. |
| `r4` | Officers | Issue invites, verify members, set roles **up to r4**, message. Cannot touch R5. |
| `member` | Everyone else | Read the board, see own profile, link their governor. No admin. |

Role lives in `users.role` (see `auth_schema.sql`). Every admin action is written to
`user_audit` so there's a trail of who promoted/verified whom.

---

## Path 1 — Discord OAuth (primary, recommended)
**Why:** your kingdom already lives in Discord. Whoever is an officer there becomes an
officer here, with zero passwords to distribute.

**Setup**
1. Supabase → Authentication → Providers → **Discord**: enable, paste your Discord app's
   Client ID + Secret (Discord Developer Portal → New Application → OAuth2). Redirect URL
   is shown by Supabase — add it to the Discord app.
2. Front end: `supabase.auth.signInWithOAuth({ provider: 'discord' })` behind the existing
   "Continue with Discord" button.
3. On first login, upsert a `users` row: `auth_uid = session.user.id`,
   `discord_id`, `discord_name` from `session.user.user_metadata`.

**Mapping Discord *server roles* → app roles (optional but ideal)**
Supabase Auth proves *identity*, not server roles. To auto-grant R4/R5 from Discord:
- Add a small server-side step (Supabase Edge Function, or an endpoint on the VPS) that
  uses a **Discord bot token** to call
  `GET /guilds/{guildId}/members/{userId}` and reads their role IDs.
- Map your R5/R4 Discord role IDs → `users.role`, update the row.
- Run it on login (and/or nightly) so promotions in Discord flow through automatically.

If you skip the mapping, Discord still works for login — officers just set roles manually
in the Members view (Path 2's mechanism).

---

## Path 2 — Officer-issued invite codes / passcodes (fallback)
For governors who don't use Discord, or to pre-bind a login to a specific governor.

**R4/R5 issues an account (in the Members view):**
1. Officer clicks **"Issue invite"** (optionally picks the governor row + the role to grant).
2. App inserts an `invites` row: random `code`, `role`, optional `governor_id`,
   `created_by`, `expires_at`, `max_uses`. Show the code/link to copy
   (e.g. `kd1685.com/join?code=ABC123`).
3. Officer sends it to the member.

**Member redeems:**
1. Opens the link / types the code on the login screen (the existing "PASSCODE" field).
2. App validates: not revoked, not expired, `used_count < max_uses`. If valid →
   creates/*links* their `users` row with the invite's `role` and `governor_id`,
   increments `used_count`, writes a `user_audit` row.
3. For a real password login on this path, pair it with Supabase Auth **email OTP / magic
   link** so there's still no password to manage — the code authorizes the role, the magic
   link authorizes the identity.

**Managing:** officers can revoke an invite (`revoked = true`), set `expires_at`, or raise
`max_uses` for a bulk "everyone in alliance X" code.

---

## How "Verify" works (the button already in the Members UI)
The roster's **Verify** button = an officer confirming a member's claimed governor link:
- Member self-links (says "I am governor ID 1685xxxxxx") → their `users.status = 'pending'`.
- Officer reviews and clicks **Verify** → `status = 'active'`, audit row written.
- The green "linked" dot + "Verified" label in the table reflect `status`/`discord_id`.

---

## Permission gating (front end + RLS)
- **RLS** (in `auth_schema.sql`) is the real guard: members can only read their own `users`
  row; only `is_officer()` can insert/update users or touch invites. The anon key + a
  logged-in session is all the site needs.
- **UI**: hide the Issue-invite / Verify / role-dropdown controls unless
  `session.role in ('r4','r5')`. Never rely on UI hiding alone — RLS enforces it.
- Never ship the service_role key to the browser. Site = anon key + user JWT. Bot = service key.

---

## Bootstrap the first King
Chicken-and-egg: someone must be R5 to promote others.
1. You log in once with Discord.
2. In Supabase → Auth → Users, copy your uid.
3. `update users set role='r5' where auth_uid='<your-uid>';`
You can now hand out R4 to your officers from the Members view.

---

## Build order for Claude Code
1. Apply `schema.sql` then `auth_schema.sql` in Supabase.
2. Enable Discord provider in Supabase Auth.
3. Wire "Continue with Discord" → `signInWithOAuth`; upsert `users` on callback.
4. Add `/join?code=` redemption + the officer "Issue invite" action in the Members view.
5. (Optional) Edge Function to sync Discord server roles → `users.role`.
6. Gate officer-only UI on `users.role`; verify RLS blocks a member from writing.
7. Bootstrap yourself as R5.
