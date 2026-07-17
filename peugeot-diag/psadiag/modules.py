"""PSA on-board systems (ECUs) the tool can try to talk to.

Lexia's everyday value is that it reaches *every* ECU, not just the
engine. Each PSA module answers KWP2000 at its own K-line address. This
table drives the multi-system scan (`psa-diag systems`).

IMPORTANT HARDWARE NOTE: on a pre-BSI car (306, early 206/Xsara/Saxo) each
system's K-line is on a *different pin* of the diagnostic socket, and a
plain KKL/ELM cable only reaches pin 7 (engine). Reaching ABS (pin 12) or
airbag (pin 13) needs the cable re-pinned to that pin, or a multiplexing
interface like Lexia's. So a module here can be "reachable" only if the
cable is actually wired to its pin — see HARDWARE.md. On later BSI cars
everything routes through one connection, so all modules are reachable at
once.

Addresses marked (verified) come from PSA diagnostic sources; those marked
(reported) are commonly cited but unconfirmed — the scan tries them but
don't treat a no-answer as proof the module is absent.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Module:
    key: str
    name: str
    addresses: tuple[int, ...]   # K-line target addresses to try, in order
    pin: str                     # OBD-socket pin its K-line uses (pre-BSI)
    verified: bool               # are the addresses confirmed?


# Engine addresses are the verified set used elsewhere in the tool. The
# non-engine addresses are placeholders pending the module-address research
# (see README); they are intentionally conservative and flagged unverified
# so the scan never claims a module is absent on a no-answer.
PSA_MODULES: tuple[Module, ...] = (
    Module("engine", "Engine / injection", (0x10, 0x33, 0x13, 0x01, 0x11), "7", True),
    Module("abs", "ABS / ESP", (0x28, 0x18), "12", False),
    Module("airbag", "Airbag / SRS", (0x18, 0x58), "13", False),
    Module("bsi", "BSI / body computer", (0x36, 0x1A), "1", False),
    Module("cluster", "Instrument cluster", (0x60, 0x20), "1", False),
    Module("gearbox", "Automatic gearbox", (0x11, 0x18), "7", False),
)


def get_module(key: str) -> Module:
    for m in PSA_MODULES:
        if m.key == key:
            return m
    raise KeyError(f"unknown module {key!r}; known: "
                   + ", ".join(m.key for m in PSA_MODULES))
