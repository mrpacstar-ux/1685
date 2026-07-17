# Tuning / remapping a 2.0 HDi — what this tool does, and the honest limits

You asked for custom mapping with recommended stage 1 / stage 2 settings,
reading what's on the ECU first and then customising it. Here's the honest
split between what belongs in this tool and what genuinely doesn't — not
to be unhelpful, but because getting this wrong melts a piston, and I'd
rather you spend the money once and keep the engine.

## The short version

- **Reading the current state: yes — the tool does this**, and it's
  genuinely useful. See below.
- **Writing stage 1/2 maps from this tool: no** — and it's not a feature
  I'm withholding, it's that a safe diesel flasher can't be a generic
  script. Here's exactly why, and the real path that works.

## What the tool reads (so you know what you've got)

Your 2.0 HDi runs a **Bosch EDC15C2** (DW10 engine). Two read-only things
tell you a lot:

1. **ECU info tab → software / calibration number.** A remap *changes this
   number*. Note it down; compare against the known stock calibration for
   your exact ECU (forums list these). If it doesn't match stock, someone
   has already flashed it — you may already have the power you're after.
   This is the "read what it has" step, and it's the honest first move
   before spending anything.
2. **Live data tab, on a road/load log** — rail pressure (should climb to
   ~1350–1600 bar under load on EDC15C2), boost (MAP), commanded EGR, MAF.
   A stock DW10 vs a mapped one behaves visibly differently here (mapped
   cars hold more boost and inject more under load). This shows you the
   *current tune's behaviour* without touching anything.

That's the safe, real "read then decide" capability, and it's in the app now.

## Why the tool can't safely write the map

Flashing a diesel ECU is not "send a stage-1 command". To change fuelling
you must:

1. **Read the full flash out of the EDC15C2.** On EDC15 this usually means
   a **bench / boot-mode read** (BDM or boot pins on the bench), not a
   plug-in-the-OBD-socket read — the OBD path on EDC15C2 is limited and
   many maps aren't reachable live. That alone needs hardware this K-line
   cable is not (KESS/KTAG/MPPS/Galletto-class tools, or a BDM frame).
2. **Find the maps in *your* firmware** — driver's-wish/torque limiter,
   the smoke limiter (max fuel vs air mass), rail-pressure map, boost
   target/limiter, start-of-injection. Their addresses differ per
   calibration; tuners use WinOLS with a DAMOS/A2L or map-pack to locate
   them.
3. **Modify them sanely** and **correct the ECU checksums** — a wrong
   checksum bricks the ECU; wrong fuelling with no matching air/boost
   melts pistons or lets the turbo overspeed.
4. **Write it back** and validate on a load log.

A generic program can't know your calibration's map layout, and a
one-size preset written blind is exactly how engines die. So a "click
stage 1" button here would be dishonest — it couldn't be safe.

## The path that actually works (and is legitimate)

Remapping a 2.0 HDi is popular precisely because it responds well — a
proper **stage 1 on stock hardware realistically adds ~25–35 hp and a big
chunk of mid-range torque** on the 90/110 DW10. To do it right:

- **Easiest/safest:** a reputable HDi remapper (mobile or bench). Ask them
  to read your file first and tell you if it's already mapped. A good one
  gives you a stage-1 file matched to your exact calibration.
- **DIY, if you want to learn it:** WinOLS + a DW10/EDC15C2 map pack, an
  EDC15 bench/boot read tool, checksum correction, flash back. Budget real
  time to learn it and a spare ECU to practise on. `psa-diag` complements
  this — use it to read codes and watch live rail pressure/boost while you
  validate — but the flashing is a separate toolchain.

### Stage 1 vs stage 2 — your instinct is right

- **Stage 1 = software only, stock hardware.** Correct to do first, and
  the sensible ceiling until you upgrade breathing. On a DW10 it leans on
  more boost + fuel within the stock turbo/intercooler/injector limits.
- **Stage 2 = after hardware** (intake, bigger/better intercooler,
  exhaust/DPF-delete where legal, sometimes a hybrid turbo and uprated
  clutch/DMF, which a torque bump will find fast). Only map to stage 2
  *after* the hardware is on — mapping for airflow you don't have yet is
  the melted-piston route.

Two non-engine cautions worth saying once: a torque increase punishes the
**clutch and dual-mass flywheel** first, and in most places a remap is
**declarable to your insurer** and affects the car's legal
emissions/MOT status. Worth factoring in before the spend.

## If you want, I can help with the parts I responsibly can

- Add a one-click **"tune inspection" report** to the GUI: grab the
  calibration number + a timed live log of rail pressure/boost/MAF/EGR and
  save it to a file you can share with a remapper.
- Help you **interpret a WinOLS project** or a live log once you have one.
- Document the **stock EDC15C2 calibration numbers** for the DW10 so you
  can tell mapped from stock at a glance.

What I won't do is ship a blind map-writer — that's the one shortcut that
isn't safe on a diesel.
