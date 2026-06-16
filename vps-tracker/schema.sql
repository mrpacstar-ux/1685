-- KD1685 personal Statsmaster — database schema
-- Run in Supabase: SQL Editor -> paste -> Run. Safe to re-run (IF NOT EXISTS).

-- ----- current roster (one row per governor, overwritten each scan) ---------
create table if not exists players (
  governor_id text primary key,         -- real governor id when available, else slug of name
  name        text not null,
  power       bigint,
  kills       bigint,                    -- kill points
  deads       bigint,
  t4_kills    bigint,
  t5_kills    bigint,
  updated_at  timestamptz default now()
);

-- ----- history (one row per governor per day, for trends/graphs) ------------
create table if not exists player_snapshots (
  governor_id text not null,
  name        text,
  power       bigint,
  kills       bigint,
  deads       bigint,
  scan_date   date not null,
  created_at  timestamptz default now(),
  primary key (governor_id, scan_date)
);
create index if not exists idx_snapshots_date on player_snapshots (scan_date);
create index if not exists idx_snapshots_gov  on player_snapshots (governor_id);

-- ----- existing tables the front end already reads --------------------------
create table if not exists fort_tracking (
  id         bigserial primary key,
  level      text,
  coords     text,
  player     text,
  updated_at timestamptz default now()
);

create table if not exists kingdom_stats (
  id        int primary key,
  power     text,
  kills     text,
  last_sync timestamptz
);
insert into kingdom_stats (id) values (1) on conflict (id) do nothing;

-- ----- Row Level Security -----------------------------------------------------
-- The BOT uses the service_role key and bypasses RLS entirely.
-- The WEBSITE (index.html) must use the ANON key and only needs READ.
alter table players          enable row level security;
alter table player_snapshots enable row level security;
alter table fort_tracking    enable row level security;
alter table kingdom_stats    enable row level security;

create policy "public read players"   on players          for select using (true);
create policy "public read snapshots" on player_snapshots for select using (true);
create policy "public read forts"     on fort_tracking    for select using (true);
create policy "public read stats"     on kingdom_stats    for select using (true);
-- No insert/update/delete policies => anon key cannot write. Only the bot writes.
