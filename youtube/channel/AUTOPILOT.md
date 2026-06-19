# Autopilot — fully unattended operation

`autopilot` is the hands-off mode: each run picks the next planned idea (from
the calendar if present, otherwise it generates a fresh one), produces the
complete video package, and publishes it — no human in the loop.

```bash
npm run autopilot -- --count 1            # produce + publish one video
npm run autopilot -- --count 2 --short    # two Shorts
npm run autopilot -- --theme "black holes"
```

Run it on a schedule (the included GitHub Action) and the channel runs itself.

---

## Publish modes (`PBM_PUBLISH_MODE`)

| Mode | What happens | Risk |
|---|---|---|
| `scheduled` *(default)* | Upload **private**, auto-publish at the scheduled time. You can still cancel before it goes live. | Low — there's a window to intervene. |
| `review` | Upload **private**; a human publishes. | Lowest — but not truly hands-off. |
| `public` | Publish **public immediately**, no review. | **Highest** — factual errors / policy issues go live unattended. |

The scheduled time is the calendar slot time (interpreted with
`YOUTUBE_PUBLISH_TZ_OFFSET`) if it's in the future, otherwise *now +
`PBM_PUBLISH_DELAY_HOURS`*.

> Recommended: stay on `scheduled`. It's genuinely hands-off yet leaves a
> cancellation window, which is the single best protection against an
> automated channel earning a strike.

---

## Scheduled runs (GitHub Action)

The workflow at `.github/workflows/palebluemind.yml` runs autopilot on a daily
cron (and on-demand via "Run workflow"). To enable it:

1. **Add repo secrets** (Settings → Secrets and variables → Actions):
   - `ANTHROPIC_API_KEY` — required.
   - `TTS_PROVIDER` + `ELEVENLABS_API_KEY`/`ELEVENLABS_VOICE_ID` *or*
     `OPENAI_API_KEY` — for narration (without this, no audio → no rendered mp4).
   - `PEXELS_API_KEY` — for B-roll.
   - `YOUTUBE_CLIENT_ID`, `YOUTUBE_CLIENT_SECRET`, `YOUTUBE_REFRESH_TOKEN` — to
     upload. Without these the run still produces packages (saved as build
     artifacts) but doesn't upload.
   - `YOUTUBE_PUBLISH_TZ_OFFSET` — optional, e.g. `-05:00`.
2. **Adjust the cron** in the workflow to your posting time.
3. Produced packages are attached to each run as a downloadable artifact.

ffmpeg is installed in the workflow, so the runner renders real `.mp4`s.

---

## Getting a YouTube refresh token (one time)

The Data API uses OAuth2. Briefly:

1. Google Cloud Console → enable **YouTube Data API v3**.
2. Create an **OAuth client ID** (type: Desktop app) → note client id + secret.
3. Use the OAuth Playground (or a tiny local script) with scope
   `https://www.googleapis.com/auth/youtube.upload`, authorize with the channel's
   Google account, and exchange the code for a **refresh token**.
4. Put the three values in secrets (CI) or `.env` (local).

The refresh token is long-lived; the app exchanges it for short-lived access
tokens automatically (`googleapis` handles this).

---

## Honest limitations of "fully automated"

- **State doesn't persist on a fresh CI runner.** `out/` is wiped each run, so
  autopilot generates fresh ideas rather than walking a saved calendar, and the
  cross-run idea-dedup log resets. Topic variety from the model is high, but for
  strict de-duplication at scale, persist `out/ideas.json` (commit it back,
  cache it, or use a small datastore). Locally, where `out/` persists, autopilot
  follows the calendar and de-dups normally.
- **Quality still benefits from a human.** Scheduled mode exists precisely so a
  person *can* glance before publish. Truly unattended `public` mode trades that
  safety for convenience — use it knowingly.
- **APIs cost money and have quotas.** Claude, TTS, and the YouTube upload quota
  all meter usage; a daily cron has a real (small) running cost.
- **Policy is on you.** Automated production doesn't exempt the channel from
  YouTube's rules on originality, accuracy, and disclosure. The guardrails in
  `../CONCEPT.md` are what keep an automated channel alive long-term.
