# Pale Blue Mind — growth playbook

Concept gets you started; **distribution discipline** is what actually grows a
channel. This is the operating plan the automation is built to serve.

---

## The growth thesis

On YouTube in the current era, growth is driven by **per-video performance**,
not subscriber count. The algorithm tests every upload on a small audience and
expands reach based on two signals:

1. **Click-through rate (CTR)** — does the title + thumbnail earn the click?
2. **Watch time / retention** — once clicked, do people stay?

Everything below optimizes those two numbers. Subscribers are a *lagging*
result of nailing them repeatedly.

### The Shorts → long-form flywheel

- **Shorts** are the cheapest discovery surface on the platform. We publish
  one daily as the top of funnel — each is a single awe-hook with a payoff.
- Every Short ends by pointing at a related **long-form** video.
- **Long-form** carries watch-time (algorithmic weight) and revenue.
- Long-form viewers subscribe; subscribers get the next Short surfaced; loop.

The pipeline's daily-Short + 2×-weekly-long cadence exists specifically to feed
this flywheel without burning out a human creator — because it's automated.

---

## Cadence (first 90 days)

| | Shorts | Long-form | Perspective |
|---|---|---|---|
| Weeks 1–4 | 1 / day | 2 / week | — |
| Weeks 5–8 | 1 / day | 2 / week | 1 (week 6) |
| Weeks 9–12 | 1–2 / day | 2–3 / week | 1 (week 10) |

Consistency beats volume beats perfection — *in that order*. A predictable slot
(same times daily) trains both the audience and the algorithm. `calendar.ts`
generates the schedule; `produce --from-calendar` works through it.

**Best-time defaults** (tune to your analytics): long-form lands early
evening in your largest-audience timezone; Shorts spread across the day.

---

## The 50% rule: title & thumbnail get half the effort

A great video with a weak title/thumbnail is invisible. The pipeline therefore
treats packaging as a first-class output:

- `metadata.ts` generates **multiple title candidates** per video — pick the
  most curiosity-driving (a question or a tension), keep it under ~60 chars,
  front-load the hook.
- Thumbnails: one subject, 3–5 word phrase, huge contrast, legible at thumbnail
  size. The thumbnail asks; the video answers.
- **A/B mindset:** swap the thumbnail/title on any long-form video that
  underperforms its channel-median CTR after 48h. (YouTube's Test & Compare
  for thumbnails is ideal here.)

---

## Retention craft (baked into the scripts)

`script.ts` is prompted to engineer retention, not just inform:

- **No intros.** The first frame is the hook. Cold open, every time.
- **Open loops.** Pose the question early; don't resolve it until the payoff.
- **Escalating beats.** Each segment tops the last and ends on a micro-payoff
  so the retention graph stair-steps instead of decaying.
- **Pattern interrupts.** A surprising number, a reframe, or a visual shift
  every ~30–40s.
- **Pace to the visuals.** Calm, but never idle — silence is used on purpose.

---

## SEO & discovery

Search is secondary to browse/suggested on this kind of content, but it's free
compounding traffic:

- Title carries the primary phrase naturally (no keyword stuffing).
- Description: a strong first two lines (shown in search), then a fuller
  summary, chapters for long-form, affiliate + related links, and consistent
  channel links. `metadata.ts` writes this.
- Tags are a minor signal — generated, not obsessed over.
- **Playlists** by pillar (Scale / What if / Deep time / Frontier / Pale blue)
  to chain sessions and lift watch-time per visit.

---

## KPIs and decision rules

Track weekly. Let the numbers, not vibes, drive changes.

| Metric | Healthy early signal | Action if below |
|---|---|---|
| Long-form CTR | ≥ 4–6% | New thumbnail + title within 48h |
| Avg. % viewed (long) | ≥ 40% | Tighten hook + first 60s; cut a beat |
| Avg. view duration (Short) | high loop / re-watch | Shorten; stronger payoff |
| Shorts → channel CTR | climbing | Stronger end-screen pointer to long-form |
| Subs per 1k views | climbing | Clearer, more specific CTA |

**Double down on winners.** When a topic over-performs its median, the next
batch of ideas leans into that vein (`ideas.ts` can be seeded with a theme).
The catalogue is an experiment; the pipeline makes iterating cheap.

---

## 90-day milestone path (targets, not promises)

- **Day 30:** ~30 Shorts + ~8 long-form live. A consistent identity. First
  videos beating channel-median CTR identified.
- **Day 60:** Eligible for / approaching monetization. A clear "winning" topic
  vein. Thumbnail/title craft dialed in from real CTR data.
- **Day 90:** A back-catalogue that earns views without new uploads
  (compounding), 1–2 breakout videos driving subscriber spikes, and a repeatable
  weekly operation that runs on the pipeline plus a human review pass.

Growth is non-linear and breakout-driven: most videos are base hits, a few
break out, and the breakouts compound. The strategy is to take *many cheap,
high-quality swings* — which is precisely what automation makes affordable.
