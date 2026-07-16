# Hardware guide — what to buy and why your scanner fails

For a Peugeot 306 with a 206 engine/ECU transplant. Researched July 2026;
prices approximate.

## The zero-cost first step (do this before buying anything)

On an engine-swapped car, the most likely reason *every* scanner fails is
that the ECU's diagnostic wire never reaches the socket. If only the 206
engine + engine loom went in, the K-line is probably unterminated behind
the 306's socket.

With a multimeter:

1. **Pin 16 of the 16-pin socket must have battery +12 V** (pins 4 and 5
   = ground). Every scanner dies silently without it.
2. **Continuity from the 206 ECU connector's K-line pin to socket pin 7.**
   Find the K-line pin for your exact ECU in the 206 wiring diagrams
   (searchable PDF: "Peugeot 206 Electric Wiring Diagrams"). If there's no
   continuity, that's the whole problem — one wire from the ECU connector
   to pin 7 fixes it.

PSA's 16-pin socket usage in this era (pre-CAN): **pin 7 = engine K-line**
(also auto gearbox), pin 15 = L-line (some older ECUs listen for the init
on K *and* L), pin 11 = BSI/body systems, pin 12 = ABS, pin 13 = airbag.
A generic scanner only ever talks on pin 7 — one reason "full system
scans" never see PSA ABS/airbag on these cars.

On the 306 the socket lives in the lower dash on the driver's side, near
the fusebox (Phase 2/3, 1997-on cars). Phase 1 cars (to ~1997) instead
have a round green 2-pin connector in the engine bay for old-school flash
codes, and sometimes a round 30-pin PSA connector.

## Why generic ELM327 scanners fail on this car

- **No EOBD mandate.** EOBD only became compulsory for petrol cars in
  2001 (diesel 2004). A pre-2001 ECU has no obligation to answer the
  standard OBD-II handshake, and mostly doesn't.
- **Wrong init.** Pre-2003 206/306 ECUs speak KWP2000 with the **5-baud
  slow init** — the tester clocks an address byte out at 5 baud (~2
  seconds per byte!), then jumps to 10400 baud within a 60 ms window. It
  only answers when the *right ECU address* is used, and generic apps only
  try the standard broadcast address (0x33).
- **Clone chips.** Elm Electronics closed in 2022 and never made a
  "v1.5" — every cheap v1.5/v2.1 adapter is a clone of pirated v1.0
  firmware. Clones are notorious for corrupting exactly the K-line
  protocols this car uses, and for silently botching the AT commands
  (`ATIIA`, `ATSP4`) that a custom init needs.

## Ranked shopping list

### 1. VAG KKL 409.1 cable, FTDI chip — ~£12 (buy this one)

A "dumb" cable: USB-to-serial chip wired straight onto OBD pin 7 (K-line)
with no protocol firmware to get in the way. This is the ideal substrate
for `psa-diag`'s raw K-line mode (`--kkl`), which does the 5-baud init
itself, bit-perfect, at any ECU address. Also the classic hardware for
other old-PSA freeware (e.g. PSA-COM/DiagKWP).

**Buy only an FTDI-chip version** (FT232RL) — CH340 copies have unreliable
break timing, which ruins the 5-baud init. Listings normally state the
chip.

### 2. Lexia 3 / Diagbox clone, "full chip 921815C" — ~£40–70

The "PP2000" you keep hearing about, in its modern form. PP2000 as a
product is dead — **Diagbox replaced it, but Diagbox literally contains
PP2000** as its back-end for older Peugeots, so a 306/206 is fully
covered (pick model "306R" for a Phase 2/3 car; you may need to tell it
it's a 206 to match your swapped ECU). Does every ECU in the car,
actuator tests, injector coding, key stuff — the lot.

Realities to accept before buying:

- Insist on **"full chip", revision 921815C** in the listing. Cut-down
  clones omit the relays/optocouplers that switch the different K-line
  pins and fail on some ECUs.
- The bundled software is grey-market cracked dealer software. That's the
  only way it exists outside dealerships; the dead download links you've
  been finding are this ecosystem's normal state. Clone cables ship with
  it on a disc/USB or as a pre-built VMware image.
- Old versions run best: community consensus is Diagbox 7.57/7.58 in a
  32-bit Windows XP/7 virtual machine with the cable's USB passed
  through. Newer Diagbox 9.x runs on Windows 10/11 but is fussier about
  clone hardware.

### 3. OBDLink SX USB — ~£25–40

The honest modern ELM327-compatible (STN11xx chip): correct K-line
support, full AT command set, rock-solid from Python. Works with
`psa-diag`'s default ELM mode. Best choice if your swapped ECU turns out
to be a 2001+ EOBD unit (those answer even standard init once pin 7 is
wired). A £5 clone is not worth the debugging hours.

### 4. iCarsoft i970 / CP series — ~£100+

Standalone PSA-specific handheld, claims 1996+ coverage; user reports are
"fine for 90% of DIY". Weakest value here because it picks its init from
the model you select — on a swap car you'd select "206" and hope. Only
worth it if you never want a laptop involved.

**Not recommended:** Delphi/Autocom DS150E clones (weak on PSA, firmware
headaches), Autel (£250+ overkill, thin evidence on pre-2001 PSA).

## If the car turns out to be Phase 1 (pre-1997 ECU still in place)

Those pre-OBD ECUs don't do KWP2000 at all — they give flash codes: ground
the test pin on the green 2-pin connector, count the check-engine-light
blinks. No scanner needed, just a paperclip and the code table.
