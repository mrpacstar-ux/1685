# psa-diag — fault code reader for KWP2000-era Peugeot/Citroën

Reads and clears **engine fault codes** on late-90s / early-2000s PSA cars
(Peugeot 306, 206, Citroën Saxo/Xsara…) through a cheap ELM327-compatible
USB interface.

Built for the classic swap scenario: **a Peugeot 306 running a 206 engine
and ECU**. Generic scanners fail on these cars because the ECU doesn't
speak the standard OBD-II auto-search dialect — it needs a
manufacturer-specific KWP2000 init aimed at the right ECU address. This
tool tries a whole ladder of init strategies, exactly like Peugeot's own
PP2000/Lexia did:

1. `obd-auto` — standard OBD-II/EOBD search (what your scanner already tried)
2. `kwp-fast-psa` — KWP2000 **fast init**, physically addressed (`80 <ecu> F1`),
   walking the known PSA engine-ECU addresses (`10, 33, 01, 11, 28`)
3. `kwp-fast-std` — KWP2000 fast init with generic functional addressing
4. `kwp-5baud-psa` — ISO **5-baud slow init** at the same PSA addresses
5. `iso9141` — plain ISO 9141-2 (early EOBD petrol ECUs)

## Install

Needs Python 3.9+ and one package:

```
pip install pyserial
```

Then run it straight from this folder:

```
python -m psadiag scan
```

(or `pip install .` to get a `psa-diag` command.)

### Windows quickstart (from zero)

1. Install Python from [python.org](https://www.python.org/downloads/) —
   tick **"Add python.exe to PATH"** in the installer.
2. Plug in the USB interface. If Windows doesn't recognise it, install the
   driver for its USB chip (CH340, CP2102 or FTDI — the listing usually
   says which).
3. Find the COM port: Device Manager → **Ports (COM & LPT)** → e.g.
   `USB-SERIAL CH340 (COM3)`.
4. In a Command Prompt inside this folder:

   ```
   pip install pyserial
   python -m psadiag -p COM3 scan
   ```

## Usage

```
python -m psadiag scan               # find adapter, connect, read codes
python -m psadiag clear              # read codes, confirm, clear them
python -m psadiag -v scan            # show raw serial traffic (debugging)
python -m psadiag -p COM3 scan       # explicit serial port (Windows)
python -m psadiag -p /dev/ttyUSB0 scan   # explicit port (Linux)
python -m psadiag --profile kwp-fast-psa scan   # skip straight to one strategy
python -m psadiag terminal           # raw AT/hex terminal for experimenting

# with a dumb KKL/VAG-409.1 cable instead of an ELM327:
python -m psadiag --kkl -p COM3 scan
python -m psadiag --kkl -p /dev/ttyUSB0 clear
```

Do everything with **ignition ON, engine OFF** first. Connection can take
a minute — 5-baud init alone takes several seconds per attempt, and the
ladder tries strategies in sequence.

### Reading

`scan` prints each code with a description and whether the fault is
present *right now* or just stored history, e.g.:

```
2 fault code(s):

  P0135  O2 sensor heater circuit, B1S1  [PRESENT NOW]
  P0505  Idle control system  [stored/historic]
```

A code marked **PRESENT NOW** will come straight back if you clear it —
fix the cause first.

### Clearing

`clear` re-reads first, shows you what it's about to erase, and asks for
confirmation. Freeze-frame data is lost when you clear.

## Hardware

Two supported interface families (full buying guide, with the why and the
clone traps, in **[HARDWARE.md](HARDWARE.md)**):

- **VAG KKL 409.1 cable (FTDI chip), ~£12** — recommended. A dumb raw
  K-line cable; use `--kkl` mode, where this tool performs the 5-baud
  init itself, bit-perfect, at every PSA ECU address. No ELM firmware
  lottery involved.
- **ELM327-compatible USB** — the default mode. Genuine ELM327s are no
  longer made; the reliable modern equivalent is an **OBDLink SX**
  (~£30). Cheap "v1.5" clones often corrupt exactly the K-line protocols
  this car uses — if `psa-diag terminal` answers `ATIIA 10` with `?`,
  the clone is the problem, not the car.

If you want Peugeot's own dealer software instead (actuator tests,
injector coding, every ECU in the car), the modern answer to "where do I
get PP2000" is a **Lexia 3 "full chip 921815C" clone with Diagbox**
(~£40–70) — Diagbox contains PP2000 for old cars. Details and caveats in
HARDWARE.md.

## The engine-swap caveat

On a 306 with a 206 engine loom, the ECU's diagnostic K-line only reaches
the diagnostic socket if someone wired it there. If **no strategy in the
ladder** gets a peep out of the ECU (`-v` shows only `BUS INIT: ERROR` /
`UNABLE TO CONNECT` everywhere), suspect the K-line wire before suspecting
software: the ECU's K-line pin must run to **pin 7** of the 16-pin OBD
socket (with pin 16 = 12 V battery, pins 4/5 = ground). That is a
one-wire fix.

## What this tool is not

It reads and clears engine DTCs. It does **not** do injector coding,
immobiliser key programming, BSI work, or actuator tests — for those you
want a Lexia/Diagbox clone. Nothing here writes to the ECU beyond the
standard "clear diagnostic information" service, so it can't brick
anything.

## Development

```
python -m unittest discover -s tests
```

The test suite runs against a simulated 206 ECU that only answers PSA
fast-init at address 0x10 — no hardware needed. Protocol constants live in
`psadiag/profiles.py`; adding a new ECU quirk is a data change, not a code
change.
