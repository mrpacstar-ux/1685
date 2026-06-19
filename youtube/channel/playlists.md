# Playlist structure

Playlists chain viewing sessions (lifting watch-time per visit) and give the
channel a clear shape. Create one per content pillar — the pipeline tags every
idea and package with its pillar, so sorting is mechanical.

| Playlist | Pillar | What goes in it |
|---|---|---|
| **How big is everything?** | Scale | Size/scale videos — comparisons, "if X were Y", largest/smallest things. |
| **What if…** | What if | Counterfactual physics — remove the Moon, fall into a black hole, stop the Earth. |
| **Deep Time** | Deep time | The far past and far future — the last star, Earth in 250M years, the heat death. |
| **The Frontier** | Frontier | Genuinely open questions — dark matter, expansion, what's inside a black hole. |
| **Pale Blue** | Pale blue | Perspective pieces that zoom back to Earth and us. The emotional anchor. |

## Conventions

- **One playlist per video**, chosen by its pillar (also stored in
  `manifest.json` of each produced package).
- Order each playlist so a strong "gateway" video sits first — the one most
  likely to hook a new viewer.
- Set the channel's **featured/trailer** to the best-performing "Pale Blue" or
  "What if" video for non-subscribers.
- Add new uploads to their playlist at publish time (it's a step in
  `publish.txt`'s checklist).

## Series potential (later)

Recurring, numbered series compound subscriptions because viewers come back for
the next installment. Candidates once the channel finds its footing:

- **"Scale of Everything"** — a numbered ladder from the Planck length to the
  observable universe.
- **"The Last …"** — the last star, the last black hole, the last proton
  (deep-time series).
