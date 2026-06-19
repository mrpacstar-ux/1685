# Launch slate — the first 12 videos

A ready-to-produce opening run: 6 long-form anchors + 6 Shorts across all five
pillars. Each is a strong, evergreen "gateway" topic. Hooks are written in the
channel voice; the pipeline will expand each into a full script — but these give
`produce` a real queue instead of a blank prompt.

> Fact-check each script before publishing (some figures are approximate by
> nature — e.g. cosmic timescales). The hooks below are accurate as written.

---

## Long-form anchors (8–12 min)

**1. What would you actually see falling into a black hole?** · *What if*
> "Fall into a black hole and the universe behind you does something impossible
> — it speeds up, blueshifts, and then blinks out. Here's what the last seconds
> really look like."

**2. How big is the universe, really?** · *Scale*
> "Hold out your thumb at arm's length. You're now covering more than ten
> thousand galaxies — and that's the easy part to comprehend."

**3. The last star: how the universe ends** · *Deep time*
> "Trillions of years from now the final star will flicker out, and the sky will
> go dark — not for a night, but forever. This is how it happens."

**4. What is dark matter — and why can't we find it?** · *Frontier*
> "Every star and galaxy you've ever seen is barely 5% of the universe. The rest
> is invisible, everywhere, and holding the galaxies together — and we have no
> idea what it is."

**5. The most important photo ever taken** · *Pale blue*
> "In 1990, a spacecraft six billion kilometers away turned around and
> photographed home. Earth was less than a single pixel. Here's why that pixel
> changed how we see everything."

**6. What if the Moon disappeared?** · *What if*
> "Lose the Moon and you don't just lose a light in the sky — you lose the
> metronome of life on Earth. The tides, the seasons, even the length of a day."

---

## Shorts (30–60s)

**7. If the Sun were a grain of sand…** · *Scale*
> "Shrink the Sun to a single grain of sand. The next nearest star? Still six
> kilometers away. That's how empty space really is."

**8. The biggest thing in the universe** · *Scale*
> "This one structure is so vast that light — the fastest thing there is — takes
> billions of years just to cross it."

**9. What if you fell into Jupiter?** · *What if*
> "Jupiter has no surface to land on. You'd just keep falling — through clouds,
> then liquid, then a crush no machine could survive."

**10. Earth in 250 million years** · *Deep time*
> "Every continent is slowly drifting toward a single supercontinent. Here's the
> map of a world none of us will ever see."

**11. Why is the universe expanding faster?** · *Frontier*
> "Something is pushing the universe apart — and it's winning. We named it dark
> energy, and that name is just about everything we know."

**12. You are made of dead stars** · *Pale blue*
> "The calcium in your bones and the iron in your blood were forged inside stars
> that exploded long before the Sun existed. You're not on the universe — you're
> made of it."

---

## Pillar coverage

| Pillar | Videos |
|---|---|
| Scale | 2, 7, 8 |
| What if | 1, 6, 9 |
| Deep time | 3, 10 |
| Frontier | 4, 11 |
| Pale blue | 5, 12 |

---

## Suggested 2-week launch sequence

Launch with several videos already live so a new visitor can binge. Front-load
the strongest gateways (#1, #5).

| Day | Long-form (early eve) | Short (midday) |
|---|---|---|
| 1 | **1. Falling into a black hole** | 7. Grain of sand |
| 2 | — | 9. Falling into Jupiter |
| 3 | — | 8. Biggest thing |
| 4 (Tue) | **2. How big is the universe** | 12. Made of dead stars |
| 5 | — | 10. Earth in 250M years |
| 6 | — | 11. Expanding faster |
| 7 (Sat) | **5. Most important photo** | (rest / re-share) |
| 8 | **6. Moon disappeared** | new Short (autopilot) |
| 11 (Tue) | **3. The last star** | new Short |
| 14 (Sat) | **4. What is dark matter** | new Short |

After this slate, let autopilot generate fresh topics — it won't repeat any of
these (they're recorded in `state/history.json` once produced).

---

## Produce the whole slate

Run these (review each `out/<slug>/` before uploading):

```bash
npm run produce -- "What would you actually see falling into a black hole?"
npm run produce -- "How big is the universe, really?"
npm run produce -- "The last star: how the universe ends"
npm run produce -- "What is dark matter and why can't we find it?"
npm run produce -- "The most important photo ever taken (the Pale Blue Dot)"
npm run produce -- "What if the Moon disappeared?"

npm run produce -- --short "If the Sun were a grain of sand, how far is the nearest star?"
npm run produce -- --short "What is the biggest thing in the universe?"
npm run produce -- --short "What if you fell into Jupiter?"
npm run produce -- --short "What will Earth look like in 250 million years?"
npm run produce -- --short "Why is the universe expanding faster?"
npm run produce -- --short "You are made of dead stars"
```
