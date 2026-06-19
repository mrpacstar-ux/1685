# Run Pale Blue Mind on your VPS

A VPS is the best home for the autopilot: state lives on disk, so the calendar
and never-repeat history persist for free (no CI commit-back needed). One script
installs everything; a systemd timer runs it on a schedule.

**Prereqs:** an Ubuntu/Debian VPS with a sudo user, and `ffmpeg`-able resources
(any small VPS is fine). You run these commands — I can't SSH in for you.

---

## 1. Get the code onto the VPS

Either clone it (private repo → use a token or your SSH key):

```bash
ssh you@your-vps
git clone https://github.com/mrpacstar-ux/1685.git
cd 1685/youtube/deploy
```

…or copy just the `youtube/` folder from your PC:

```bash
# from your PC, in the repo root
rsync -a --exclude node_modules --exclude out youtube/ you@your-vps:~/palebluemind-src/
ssh you@your-vps
cd ~/palebluemind-src/deploy
```

## 2. Install (one command)

```bash
./setup.sh
```

This installs Node 20 + ffmpeg, creates a `palebluemind` service user, copies the
app to `/opt/palebluemind`, runs `npm ci`, and installs the systemd timer.

## 3. Add your keys

```bash
sudo nano /opt/palebluemind/.env
```

Fill in (see `.env.example` for the full list):
- `ANTHROPIC_API_KEY` — required
- `TTS_PROVIDER` + the matching TTS key — for narration (no key → no audio → no render)
- `PEXELS_API_KEY` — for B-roll
- `YOUTUBE_CLIENT_ID` / `YOUTUBE_CLIENT_SECRET` / `YOUTUBE_REFRESH_TOKEN` — to upload
- `YOUTUBE_PUBLISH_TZ_OFFSET` — e.g. `-05:00`
- Keep `PBM_PUBLISH_MODE=scheduled` (upload private → auto-publish, cancellable)

## 4. Test one run, then start the schedule

```bash
# produce + publish a single video now, watching the logs
sudo systemctl start palebluemind-autopilot.service
journalctl -u palebluemind-autopilot -f

# happy with it? start the daily timer
sudo systemctl start palebluemind-autopilot.timer
systemctl list-timers palebluemind-autopilot.timer
```

That's it — it now produces and scheduled-publishes one video per day, never
repeating a topic.

---

## Tuning

- **Schedule / cadence:** edit `OnCalendar=` in
  `/etc/systemd/system/palebluemind-autopilot.timer`, then
  `sudo systemctl daemon-reload`. For more than one video per run, change
  `--count 1` in the `.service` ExecStart.
- **Plan topics ahead** (optional): run the calendar once as the service user so
  autopilot follows it instead of generating fresh each day:
  ```bash
  cd /opt/palebluemind && sudo -u palebluemind HOME=/opt/palebluemind npm run calendar -- --weeks 4
  ```
- **What's been produced:**
  ```bash
  cd /opt/palebluemind && sudo -u palebluemind HOME=/opt/palebluemind npm run history
  ```
- **Update to the latest code:** re-run `./setup.sh` from a fresh checkout — it
  preserves `.env` and `state/history.json`.
- **Outputs** (scripts, thumbnails, rendered mp4s) land in
  `/opt/palebluemind/out/<slug>/`.

## Safety

`scheduled` mode uploads each video **private** and auto-publishes it at the
scheduled time, so there's always a window to cancel from YouTube Studio before
it goes live. Switch to `review` (never auto-publishes) or `public` (instant) in
`.env` if you prefer.
