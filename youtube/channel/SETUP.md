# Pale Blue Mind — channel launch runbook

A concrete, ordered checklist to take the channel from zero to a healthy
operating rhythm. Pair this with `../CONCEPT.md` (identity) and `../GROWTH.md`
(strategy).

---

## Phase 0 — Brand assets (do once, ~30 min)

```bash
cd youtube
npm install
npm run branding            # → out/brand/avatar.png + out/brand/banner.png
```

- [ ] **Avatar** — `out/brand/avatar.png` (1024×1024). Upload as the channel
      picture. It reads at small sizes (the ringed planet mark).
- [ ] **Banner** — `out/brand/banner.png` (2560×1440). The name + tagline sit
      inside YouTube's centered "safe area" so nothing is cropped on mobile/TV.
- [ ] **Watermark** — reuse the avatar as the video watermark (Settings →
      Branding) so a "subscribe" overlay appears on every video.

> The brand mark, palette, and tagline live in `../src/config.ts` (`BRAND`).
> Change them there and re-run `npm run branding` to regenerate everything.

---

## Phase 1 — Account setup (~1 hr)

- [ ] Create the channel (a Brand Account, not a personal profile — easier to
      manage and transfer).
- [ ] Handle: `@paleblueminds` (keep it consistent across platforms).
- [ ] Channel name: **Pale Blue Mind**.
- [ ] About / description + keywords: paste from [`about.md`](./about.md).
- [ ] Upload avatar, banner, watermark.
- [ ] Create the five pillar **playlists** (see [`playlists.md`](./playlists.md)).
- [ ] Settings → Upload defaults: category **Science & Technology**, default
      description footer, "not made for kids", default to **Private**.
- [ ] Verify the account (unlocks custom thumbnails, longer videos, etc.).

---

## Phase 2 — Wire the automation (~30 min)

- [ ] `cp .env.example .env` and add `ANTHROPIC_API_KEY` (required).
- [ ] (Optional) Add a TTS key (`ELEVENLABS_API_KEY` + voice id, or
      `OPENAI_API_KEY`) and set `TTS_PROVIDER`.
- [ ] (Optional) Add `PEXELS_API_KEY` for B-roll.
- [ ] Install `ffmpeg` if you want local rendering (`ffmpeg -version`).
- [ ] (Optional) Set up YouTube Data API OAuth for automated uploads
      (`YOUTUBE_CLIENT_ID` / `_SECRET` / `_REFRESH_TOKEN`). Leave
      `YOUTUBE_PRIVACY=private` so every upload waits for human review.

---

## Phase 3 — Build the launch slate (~1 day, mostly automated)

Ship with a backlog so the channel never goes quiet.

```bash
npm run calendar -- --weeks 4          # schedule: daily Short + 2 long/week
# work through the calendar:
npm run produce -- --from-calendar     # produce the next unproduced slot
# ...repeat to build a buffer of 5-10 finished packages before launch day
```

For each produced package in `out/<slug>/`:

- [ ] Read `script.md` and **fact-check** the claims.
- [ ] Skim `captions.srt`.
- [ ] Pick a thumbnail (`thumbnail.png` A vs `thumbnail-b.png` B).
- [ ] Use `publish.txt` as the copy-paste sheet for the upload form.
- [ ] Assign the correct pillar playlist.

**Launch with 5–10 videos already live** so a new visitor has something to
binge — a one-video channel converts poorly.

---

## Phase 4 — Operating rhythm (ongoing)

Daily / per-cadence loop:

1. `npm run produce -- --from-calendar` (or `produce -- "<topic>"` for a
   one-off).
2. Human review pass (facts, thumbnail, playlist) using `publish.txt`.
3. Schedule the upload at the slot time (Short midday, long-form early evening).
4. Weekly: review analytics against the KPI table in `../GROWTH.md`. Swap
   thumbnails/titles on under-CTR videos; refresh the calendar and lean idea
   batches toward winning topics (`npm run ideas -- --theme "<winning vein>"`).

---

## Guardrails (every video)

- Facts grounded and human-reviewed — the pipeline assists, it never has final
  say on truth.
- Thumbnail matches the actual payoff. No bait.
- Licensed visuals/audio only.
- Publish **private-first**; a human flips it public.
