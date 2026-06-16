-- KD1685 — AUTH schema (run after schema.sql)
-- Supports BOTH login paths:
--   1) Discord OAuth (via Supabase Auth -> Discord provider)
--   2) Officer-issued invite codes / passcodes (for non-Discord governors)

-- ----- app users: identity + role + link to in-game governor -----------------
create table if not exists users (
  id            uuid primary key default gen_random_uuid(),
  auth_uid      uuid unique,            -- = auth.users.id when they signed in via Supabase Auth (Discord)
  discord_id    text unique,            -- Discord snowflake, when known
  discord_name  text,
  governor_id   text references players(governor_id),  -- which in-game account they ARE
  role          text not null default 'member'         -- 'r5' | 'r4' | 'member'
                  check (role in ('r5','r4','member')),
  status        text not null default 'active'         -- 'active' | 'pending' | 'suspended'
                  check (status in ('active','pending','suspended')),
  created_at    timestamptz default now(),
  last_login    timestamptz
);
create index if not exists idx_users_role on users (role);

-- ----- invite codes issued by R4/R5 ------------------------------------------
create table if not exists invites (
  code         text primary key,        -- short random code/passcode the officer hands out
  role         text not null default 'member' check (role in ('r5','r4','member')),
  governor_id  text references players(governor_id),  -- optional: pre-bind to a specific governor
  created_by   uuid references users(id),
  created_at   timestamptz default now(),
  expires_at   timestamptz,             -- null = no expiry
  max_uses     int default 1,
  used_count   int default 0,
  revoked      boolean default false
);
create index if not exists idx_invites_open
  on invites (code) where revoked = false;

-- ----- audit log of officer actions (who verified/promoted whom) -------------
create table if not exists user_audit (
  id          bigserial primary key,
  actor_id    uuid references users(id),
  action      text not null,           -- 'invite_created' | 'verified' | 'role_set' | 'suspended' | 'login'
  target_id   uuid references users(id),
  detail      jsonb,
  created_at  timestamptz default now()
);

-- ----- RLS --------------------------------------------------------------------
-- The website uses the ANON key + a logged-in Supabase Auth session (jwt).
-- The bot keeps using the service_role key and bypasses all of this.
alter table users      enable row level security;
alter table invites    enable row level security;
alter table user_audit enable row level security;

-- helper: is the current jwt an officer (r4/r5)?
create or replace function is_officer() returns boolean
language sql stable as $$
  select exists (
    select 1 from users u
    where u.auth_uid = auth.uid() and u.role in ('r4','r5') and u.status = 'active'
  );
$$;

-- a logged-in user can read their own row; officers can read everyone
create policy "users read self"     on users for select
  using (auth_uid = auth.uid() or is_officer());
-- a user can update their own non-privileged fields (handled app-side); officers update anyone
create policy "officers write users" on users for update using (is_officer());
create policy "officers insert users" on users for insert with check (is_officer());

-- invites: only officers see/manage them
create policy "officers manage invites" on invites for all
  using (is_officer()) with check (is_officer());

-- audit: officers read
create policy "officers read audit" on user_audit for select using (is_officer());
create policy "any insert audit"    on user_audit for insert with check (true);

-- ----- seed the first King (R5) so there's someone who can promote others -----
-- After YOU log in once with Discord, find your auth uid in Supabase -> Auth -> Users,
-- then run (replace the uuid + discord id):
--   update users set role='r5' where auth_uid='<your-auth-uid>';
-- or insert directly if no row exists yet.
