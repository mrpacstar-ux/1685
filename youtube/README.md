# Pale Blue Mind — concept + automation

> A faceless, AI-assisted YouTube channel about space, deep time, and the
> biggest questions in science — engineered from day one to be cheap to
> produce, impossible to run out of ideas for, and built for the algorithm.

This repo contains two things:

1. **The concept** — brand bible ([`CONCEPT.md`](./CONCEPT.md)) and growth
   playbook ([`GROWTH.md`](./GROWTH.md)).
2. **The automation** — an end-to-end TypeScript pipeline that turns a single
   topic into a finished, upload-ready video package (script → metadata/SEO →
   voiceover → B-roll → thumbnail → assembled `.mp4`), with Claude as the
   writing and ideation brain.

Nothing here is tied to any other project in this repository — it's a clean,
standalone build.

---

## Why this concept (the short version)

A channel "as popular as you can make it" has to win on four axes at once.
Pale Blue Mind is deliberately placed where all four overlap:

| Axis | Why space / big-questions science wins |
|---|---|
| **Broad appeal** | Awe is universal — "how big is the universe?" needs no prior interest. The addressable audience is ~everyone, which is what the recommendation engine rewards. |
| **Evergreen** | The content never expires. A video about black holes is as valid in 3 years as today, so the back catalogue keeps earning views and the channel compounds. |
| **Infinite supply** | Science + history + "what if" is a bottomless topic well. The pipeline can generate a year of distinct ideas in one command. |
| **Faceless & automatable** | No on-camera talent, no set. Narration + stock/AI visuals means every step can be scripted, scheduled, and scaled. |

Full reasoning, brand voice, formats, and monetization are in
[`CONCEPT.md`](./CONCEPT.md). The day-by-day growth strategy (the part that
actually drives subscribers) is in [`GROWTH.md`](./GROWTH.md).

---

## What the automation does

```
                 topic / idea
                      │
        ┌─────────────▼─────────────┐
        │   Claude (opus-4-8)       │   ideas.ts · script.ts · metadata.ts
        │   ideas → script → SEO    │
        └─────────────┬─────────────┘
                      │  script + metadata + storyboard
        ┌─────────────▼─────────────┐
        │   voiceover.ts (TTS)      │   ElevenLabs / OpenAI / dry-run
        │   visuals.ts  (B-roll)    │   Pexels / storyboard
        │   thumbnail.ts (1280×720) │   sharp / SVG
        └─────────────┬─────────────┘
                      │  audio + clips + thumbnail
        ┌─────────────▼─────────────┐
        │   assemble.ts (ffmpeg)    │   → out/<slug>/video.mp4
        └─────────────┬─────────────┘
                      │
        ┌─────────────▼─────────────┐
        │   youtube.ts (Data API)   │   scheduled / private upload
        └───────────────────────────┘
```

**Graceful degradation is the design principle.** With only an Anthropic API
key, the pipeline produces a complete, real deliverable: a polished script,
optimized title/description/tags, a thumbnail PNG, and a shot-by-shot
storyboard. Add the optional keys (TTS, Pexels, YouTube OAuth) and the same
command produces narrated audio, downloaded B-roll, a rendered `.mp4`, and an
uploaded video. Missing a key never crashes a run — that step just emits a
plan instead of an artifact and the pipeline continues.

---

## Quick start

```bash
cd youtube
npm install
cp .env.example .env        # add at least ANTHROPIC_API_KEY

# 0. Render the channel brand assets (avatar + banner). No API key needed.
npm run branding            # → out/brand/avatar.png + out/brand/banner.png

# 1. Brainstorm a batch of ideas (writes ideas to out/ideas.json)
npm run ideas -- --count 15

# 2. Generate a 4-week posting calendar from fresh ideas
npm run calendar -- --weeks 4

# 3. Produce one full video package from a topic
npm run produce -- "What would you see falling into a black hole?"

# 4. Produce the next scheduled item straight from the calendar
npm run produce -- --from-calendar

# 5. Upload a produced package (private by default)
npm run upload -- out/what-would-you-see-falling-into-a-black-hole
```

Run `npm run run -- "<topic>"` to do produce **and** upload in one shot.

### Fully hands-off (autopilot)

```bash
npm run autopilot -- --count 1     # produce + publish one video, no human in the loop
```

Autopilot produces the next planned idea (or a fresh one) and publishes it
according to `PBM_PUBLISH_MODE` — default **`scheduled`** (upload private,
auto-publish at the slot time, cancellable before it goes live). Run it on the
included GitHub Action (`.github/workflows/palebluemind.yml`) for a channel that
operates itself. Full guide + the honest limitations: **[`channel/AUTOPILOT.md`](./channel/AUTOPILOT.md)**.

Check what's been produced (and per-pillar stats) any time:

```bash
npm run history            # totals, breakdown by pillar, most-recent uploads
```

A produced package (`out/<slug>/`) contains:

```
script.md          full narration script with shot directions
script.json        structured script (segments, b-roll queries, on-screen text)
captions.srt       SubRip captions (timings estimated from the narration)
metadata.json      title, description, tags, thumbnail text, pinned comment
publish.txt        copy-paste publishing sheet + pre-publish checklist
storyboard.md      human-readable shot list (always written)
thumbnail.png      1280×720 thumbnail — variant A
thumbnail-b.png    1280×720 thumbnail — variant B (for A/B "Test & Compare")
manifest.json      package summary + per-step status
voiceover.mp3      narration audio            (if a TTS key is set)
assets/            downloaded B-roll clips    (if PEXELS_API_KEY is set)
video.mp4          final render               (if ffmpeg + assets present)
```

---

## Configuration

All config is environment variables — see [`.env.example`](./.env.example).
Only `ANTHROPIC_API_KEY` is required.

| Variable | Purpose | Required |
|---|---|---|
| `ANTHROPIC_API_KEY` | Claude — ideas, scripts, SEO | **Yes** |
| `TTS_PROVIDER` | `elevenlabs` \| `openai` \| `none` | No (default `none`) |
| `ELEVENLABS_API_KEY` / `ELEVENLABS_VOICE_ID` | ElevenLabs TTS | If `elevenlabs` |
| `OPENAI_API_KEY` | OpenAI TTS | If `openai` |
| `PEXELS_API_KEY` | Free stock B-roll | No |
| `YOUTUBE_CLIENT_ID` / `_SECRET` / `_REFRESH_TOKEN` | Upload via Data API v3 | If uploading |

External services are optional and are called over plain HTTP / official SDKs;
Claude is always accessed through the official `@anthropic-ai/sdk`.

---

## Project layout

```
youtube/
├─ CONCEPT.md        brand bible — niche, voice, formats, monetization
├─ GROWTH.md         growth playbook — algorithm strategy, cadence, KPIs
├─ channel/
│  ├─ SETUP.md       launch runbook — account setup → operating rhythm
│  ├─ about.md       paste-ready About copy + discovery keywords
│  └─ playlists.md   pillar playlist structure + series ideas
├─ src/
│  ├─ config.ts      env + brand constants (BRAND = single source of truth)
│  ├─ anthropic.ts   Claude client (text + structured JSON helpers)
│  ├─ schemas.ts     zod + JSON schemas for structured generation
│  ├─ ideas.ts       topic / idea generation
│  ├─ script.ts      script writing (hook → segments → CTA)
│  ├─ captions.ts    .srt caption generation from the script
│  ├─ metadata.ts    titles, descriptions, tags, thumbnail copy
│  ├─ publish.ts     copy-paste publishing sheet
│  ├─ voiceover.ts   TTS (pluggable provider)
│  ├─ visuals.ts     B-roll fetch + storyboard
│  ├─ thumbnail.ts   1280×720 thumbnail renderer (A/B variants)
│  ├─ branding.ts    channel avatar + banner renderer
│  ├─ assemble.ts    ffmpeg video assembly
│  ├─ youtube.ts     YouTube Data API upload
│  ├─ calendar.ts    content calendar generator
│  ├─ history.ts     durable produced-topic log (cross-run de-dup)
│  ├─ autopilot.ts   hands-off produce + publish
│  ├─ pipeline.ts    orchestrator
│  └─ cli.ts         command-line entry
├─ state/            tracked: history.json (never-repeat-a-topic log)
└─ out/              generated packages + brand assets (git-ignored)
```

New to the channel? Start with [`channel/SETUP.md`](./channel/SETUP.md) — it's
the ordered runbook from account creation to a steady operating rhythm.

---

## A note on responsible automation

This system automates **production and publishing logistics**, not deception.
Practices that get faceless channels banned or throttled — fabricated facts,
reused/duplicated content, misleading thumbnails, undisclosed AI in sensitive
contexts — are explicitly designed against here: scripts are fact-grounded and
flagged for human review before publish, thumbnails must match content, and
the upload step defaults to **private** so a human approves every video before
it goes live. Popularity is pursued through quality and consistency, not
manipulation.
