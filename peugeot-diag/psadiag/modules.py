"""PSA on-board systems (ECUs) and how to reach them.

The key fact about pre-BSI PSA cars (306, early 206/Xsara/Saxo, roughly
1998–2004): there is NO shared K-line where you pick an ECU by address
byte. Each system sits on its own K-line on its own diagnostic-socket pin.
So the *pin* is the selector, not the address:

    engine / auto gearbox ....... pin 7  (+ pin 15 / L on old ECUs)
    ABS / ESP ................... pin 12
    airbag / SRS ................ pin 13
    BSI, cluster, comfort ....... NOT on the OBD socket — they live on the
                                  VAN bus and aren't reachable this way on
                                  a pre-BSI car

A plain KKL/ELM cable is hard-wired to pin 7, so it only reaches the
engine. To read ABS or airbag you need the K-line routed to pin 12 / 13 —
either a cable with a **pin-select switch** (the cheap manual version of
Lexia's multiplexer) or a re-pinned adapter. After the K-line is on the
right pin, you just run a normal scan: whatever ECU is on that wire answers
the standard KWP init.

On later CAN/BSI cars (~2004+, AEE2004) everything instead routes through
the BSI gateway on the CAN pins (6/14), so one connection reaches every
module — that's what the `kwp-can-psa` profile and CAN IDs are for.

Pin assignments here are verified (PSA diagnostic/pinout sources). The
per-system KWP address bytes are NOT publicly verified for K-line PSA and
aren't the selector anyway, so the scan just tries standard init on the
currently-connected pin. Sources in HARDWARE.md.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Module:
    key: str
    name: str
    pin: str                     # OBD-socket pin its K-line uses (pre-BSI)
    addresses: tuple[int, ...]   # init addresses to try once on the right pin
    on_kline: bool               # reachable over K-line via the OBD socket?
    note: str = ""


# Verified pins; addresses are the standard init set tried on whatever pin
# the cable's switch is set to (the ECU on that wire answers, if present).
_ENGINE_ADDRS = (0x10, 0x33, 0x13, 0x01, 0x11)

PSA_MODULES: tuple[Module, ...] = (
    Module("engine", "Engine / injection", "7", _ENGINE_ADDRS, True,
           "Default pin — a normal cable reaches this."),
    Module("gearbox", "Automatic gearbox", "7", _ENGINE_ADDRS, True,
           "Shares the engine K-line on pin 7."),
    Module("abs", "ABS / ESP", "12", _ENGINE_ADDRS, True,
           "Set the cable's pin switch to ABS (pin 12), then scan."),
    Module("airbag", "Airbag / SRS", "13", _ENGINE_ADDRS, True,
           "Set the cable's pin switch to Airbag (pin 13), then scan."),
    Module("bsi", "BSI / body computer", "—", (), False,
           "On a pre-BSI car this is on the VAN bus, not the OBD socket — "
           "needs Lexia/Diagbox. On CAN cars it's the BSI gateway."),
    Module("cluster", "Instrument cluster", "—", (), False,
           "VAN bus on pre-BSI cars — not reachable through the OBD socket."),
)


def kline_modules() -> tuple[Module, ...]:
    return tuple(m for m in PSA_MODULES if m.on_kline)


def get_module(key: str) -> Module:
    for m in PSA_MODULES:
        if m.key == key:
            return m
    raise KeyError(f"unknown module {key!r}; known: "
                   + ", ".join(m.key for m in PSA_MODULES))
