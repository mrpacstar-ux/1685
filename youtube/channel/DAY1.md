# Day 1 — click-by-click launch checklist

The fastest path from nothing to a live, self-running channel. The only manual
parts are creating the account, pasting in assets I already generated, and
granting API access once. Budget ~45–60 minutes.

> Legend: 🧑 = you (manual) · 🤖 = already automated/generated for you

---

## 1. 🧑 Create the account (~5 min)

1. Sign in to (or create) the Google account you want the channel under —
   `youtube.com` → sign in. Use a dedicated account, not a personal one you
   care about.
2. Click your avatar → **Create a channel**.
3. Choose **Use a custom name** → enter **Pale Blue Mind** → Create.
4. (Recommended) youtube.com → Settings → **Advanced settings** → confirm the
   channel, then verify your account at `youtube.com/verify` (phone code).
   Verification unlocks custom thumbnails and longer uploads.

> Want a different channel name? Change `BRAND` in `youtube/src/config.ts`
> first, then continue — every generated asset will match.

---

## 2. 🤖→🧑 Brand assets (~5 min)

Generate them, then upload:

```bash
cd youtube && npm install && npm run branding
# → out/brand/avatar.png  (1024×1024)
# → out/brand/banner.png  (2560×1440)
```

In **YouTube Studio → Customization → Branding**:
- [ ] **Picture** → upload `out/brand/avatar.png`
- [ ] **Banner image** → upload `out/brand/banner.png`
- [ ] **Video watermark** → upload `out/brand/avatar.png`

---

## 3. 🤖→🧑 Channel info & layout (~5 min)

In **Studio → Customization → Basic info**:
- [ ] **Description** → paste the About text from `channel/about.md`
- [ ] **Channel keywords** → paste the keyword list from `channel/about.md`
- [ ] (Later) add links once you have them

Create the five playlists from `channel/playlists.md` (How big is everything? /
What if… / Deep Time / The Frontier / Pale Blue).

In **Studio → Settings → Upload defaults**:
- [ ] Category: **Science & Technology** · "No, not made for kids"
- [ ] Default visibility: **Private**

---

## 4. 🧑 Get YouTube API access (~10 min, one time)

This lets the pipeline upload for you.

**a. Enable the API**
1. [console.cloud.google.com](https://console.cloud.google.com) → create a
   project (e.g. "pale-blue-mind").
2. **APIs & Services → Library** → search **YouTube Data API v3** → **Enable**.

**b. OAuth consent screen**
3. **APIs & Services → OAuth consent screen** → User type **External** →
   fill name + your email → add yourself under **Test users**.
4. ⚠️ **Publish the app** ("Publishing status → Publish app"). In *Testing*
   mode refresh tokens expire after **7 days**; publishing makes them
   long-lived.

**c. Create credentials**
5. **APIs & Services → Credentials → Create credentials → OAuth client ID** →
   type **Web application**.
6. Under **Authorized redirect URIs** add exactly:
   `https://developers.google.com/oauthplayground`
7. Save the **Client ID** and **Client secret**.

**d. Get a refresh token (no code)**
8. Open [OAuth 2.0 Playground](https://developers.google.com/oauthplayground).
9. Click the ⚙️ (top right) → check **Use your own OAuth credentials** → paste
   Client ID + secret.
10. **Step 1**: in the scope box, enter:
    `https://www.googleapis.com/auth/youtube.upload`
    `https://www.googleapis.com/auth/youtube`
    → **Authorize APIs** → sign in with the **channel's** Google account → Allow.
11. **Step 2**: **Exchange authorization code for tokens** → copy the
    **`refresh_token`** value.

---

## 5. 🧑 Wire the keys (~5 min)

```bash
cp .env.example .env
```

Fill in `.env`:
- [ ] `ANTHROPIC_API_KEY` — **required** (scripts, metadata)
- [ ] `TTS_PROVIDER` + key — `elevenlabs` (`ELEVENLABS_API_KEY` +
      `ELEVENLABS_VOICE_ID`) or `openai` (`OPENAI_API_KEY`), for narration
- [ ] `PEXELS_API_KEY` — free B-roll ([pexels.com/api](https://www.pexels.com/api/))
- [ ] `YOUTUBE_CLIENT_ID` / `YOUTUBE_CLIENT_SECRET` / `YOUTUBE_REFRESH_TOKEN`
- [ ] `YOUTUBE_PUBLISH_TZ_OFFSET` — your timezone offset, e.g. `-05:00`
- [ ] Install `ffmpeg` for local rendering (`ffmpeg -version`)

---

## 6. 🤖 First video (~5 min hands-on)

```bash
npm run produce -- "What would you see falling into a black hole?"
```

Then review the package in `out/<slug>/`:
- [ ] Read `script.md` and **fact-check** it
- [ ] Pick a thumbnail (`thumbnail.png` A vs `thumbnail-b.png` B)
- [ ] Use `publish.txt` as the upload sheet
- [ ] Upload + set the right playlist:

```bash
npm run upload -- out/<slug>     # uploads PRIVATE for your final review
```

Flip it public in Studio when you're happy.

---

## 7. 🤖 Turn on autopilot (optional, ~10 min)

For a channel that runs itself:
1. Push this repo to GitHub (the workflow lives at
   `.github/workflows/palebluemind.yml`).
2. **Repo → Settings → Secrets and variables → Actions** → add the same keys
   from step 5 as secrets.
3. Adjust the cron time in the workflow.
4. Done — it produces and **scheduled-publishes** (private → auto-public)
   daily, never repeating a topic. Full details: `channel/AUTOPILOT.md`.

Check progress any time: `npm run history`.

---

### What I can't do for you
Create the Google/YouTube account (human-only, per Google's rules), and supply
your paid API keys. Everything else above is generated or automated.
