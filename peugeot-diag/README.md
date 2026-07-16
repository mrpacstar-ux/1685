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

## Usage

```
python -m psadiag scan               # find adapter, connect, read codes
python -m psadiag clear              # read codes, confirm, clear them
python -m psadiag -v scan            # show raw serial traffic (debugging)
python -m psadiag -p COM3 scan       # explicit serial port (Windows)
python -m psadiag -p /dev/ttyUSB0 scan   # explicit port (Linux)
python -m psadiag --profile kwp-fast-psa scan   # skip straight to one strategy
python -m psadiag terminal           # raw AT/hex terminal for experimenting
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

You need an interface whose K-line support actually works:

- **Genuine-chip ELM327 v1.4b/1.5 USB** — the cheap route. Must be a real
  PIC-based unit (or a good clone that implements `ATSP4/5`, `ATIIA`,
  `ATSH` correctly). Many £5 clones only do CAN properly and lie about
  everything else; if `psa-diag terminal` rejects `ATIIA 10` with `?`,
  the clone is the problem.
- **Lexia 3 / Diagbox clone interface** — the full-fat route. Runs
  Peugeot's own dealer software (Diagbox replaced PP2000 and still covers
  these cars), does every ECU in the car, coding, actuator tests. Doesn't
  work with this tool (proprietary interface), but it's the definitive
  answer if the ELM route disappoints.

*(Detailed buying guidance, connector/pinout notes for the 306, and the
engine-swap wiring caveat are in [HARDWARE.md](HARDWARE.md).)*

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
