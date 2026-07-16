"""Connection profiles: the ladder of init strategies tried against the car.

Generic scan tools stop after the standard OBD-II auto-search; PSA ECUs of
the 306/206 era usually need a manufacturer-specific KWP2000 init with a
specific target address instead. Each profile describes one strategy as
plain data so new ECU quirks can be added without touching the logic.

Sources for the byte values (see README):
  - ddt4all's K-line ELM init code (verified working sequence: ATSH 81
    <addr> F1 / ATSW 96 / ATWM 81 <addr> F1 3E / ATIB10 / ATST FF /
    ATSP4 + ATIIA <addr> + ATSI, falling back to ATSP5 + ATFI, then a
    bare 0x81 StartCommunication to open the session)
  - the arduino-psa-diag reverse-engineering docs (PSA KWP: 10 C0 opens a
    session, 17 FF 00 reads faults, 14 FF 00 clears, 3E keepalive; nota
    bene 10 81 means END of communication on PSA units)
  - obdtester.com's protocol list (pre-2003 206/306 = KWP2000 5-baud slow
    init; post-2003 = fast init)

A setup command prefixed with '?' is optional: failures are ignored, so
clone adapters that reject the fancier AT commands still get a chance.
"""

from __future__ import annotations

from dataclasses import dataclass

# Physical target addresses PSA engine ECUs answer on (tester is 0xF1).
# 0x10 is the conventional KWP engine-ECU address (0x11 sometimes diesel);
# 0x13 comes from a reported working Peugeot ELM init (ATIIA 13 /
# ATSH 81 13 F1); 0x33 is the generic-OBD functional address.
PSA_ENGINE_TARGETS = (0x10, 0x33, 0x13, 0x01, 0x11, 0x28)

# Session-opening requests to attempt, in order:
#   81    bare StartCommunication — what ddt4all sends on PSA K-line ECUs
#   10 C0 PSA's own "open diagnostic session"
#   10 81 generic ISO default session — tried LAST of the three because on
#         PSA units it doubles as "end of communication"
#   None  skip session setup; some ECUs answer DTC reads without one
SESSION_REQUESTS = (bytes([0x81]), bytes([0x10, 0xC0]), bytes([0x10, 0x81]), None)

# DTC read requests to attempt, in order of how widely they work on PSA.
# 17 FF 00 / 14 FF 00 are the requests PSA's own tooling uses on KWP ECUs
# (arduino-psa-diag docs); reply is 57 <count> then hi/lo/status per DTC.
READ_REQUESTS = (
    bytes([0x17, 0xFF, 0x00]),        # readStatusOfDTC, all groups — PSA standard
    bytes([0x18, 0x00, 0xFF, 0x00]),  # readDTCByStatus: all identified, group FF00
    bytes([0x18, 0x02, 0xFF, 0x00]),  # readDTCByStatus: all supported
    bytes([0x13]),                    # readDiagnosticTroubleCodes (older units)
    bytes([0x03]),                    # OBD-II mode 03 (EOBD-capable ECUs)
    bytes([0x07]),                    # OBD-II mode 07 (pending)
)

CLEAR_REQUESTS = (
    bytes([0x14, 0xFF, 0x00]),        # clearDiagnosticInformation — PSA standard
    bytes([0x04]),                    # OBD-II mode 04
)


@dataclass(frozen=True)
class Profile:
    name: str
    description: str
    setup: tuple[str, ...]            # AT commands; {tgt} formatted with target,
                                      # '?' prefix = failure tolerated
    targets: tuple[int | None, ...] = (None,)   # None -> no per-target formatting
    sessions: tuple[bytes | None, ...] = SESSION_REQUESTS
    reads: tuple[bytes, ...] = READ_REQUESTS
    clears: tuple[bytes, ...] = CLEAR_REQUESTS
    init_timeout: float = 12.0        # 5-baud init alone takes ~3 s

    def setup_for(self, target: int | None) -> list[str]:
        t = f"{target:02X}" if target is not None else ""
        return [cmd.format(tgt=t) for cmd in self.setup]


# Shared preamble: long messages allowed, ~1 s ECU-response timeout,
# adaptive timing off so slow old ECUs aren't cut short.
_COMMON = ("ATAL", "ATST FF", "ATAT0")

# The ddt4all-verified PSA K-line addressing block (minus protocol choice):
# physical header to the target, 3 s wakeup period, 3E keepalive message,
# 10400 baud.
_PSA_ADDRESSING = (
    "ATSH 81 {tgt} F1",
    "?ATSW 96",
    "?ATWM 81 {tgt} F1 3E",
    "?ATIB10",
)

PROFILES: tuple[Profile, ...] = (
    Profile(
        name="obd-auto",
        description="Standard OBD-II/EOBD auto-search (what generic scanners do)",
        setup=_COMMON + ("ATSP0",),
        sessions=(None,),
        reads=(bytes([0x03]), bytes([0x07])),
        clears=(bytes([0x04]),),
    ),
    Profile(
        name="kwp-fast-psa",
        description="KWP2000 fast init, PSA physical addressing (81 tgt F1)",
        setup=_COMMON + ("ATSP5",) + _PSA_ADDRESSING + ("?ATFI",),
        targets=PSA_ENGINE_TARGETS,
    ),
    Profile(
        # Pre-2003 206/306 ECUs mostly use KWP2000 with 5-baud slow init
        # (per obdtester.com's PSA protocol list), so this rung matters
        # most on these cars despite being the slowest to attempt.
        name="kwp-5baud-psa",
        description="KWP2000 5-baud slow init at PSA ECU addresses "
                    "(the pre-2003 206/306 norm)",
        setup=_COMMON + ("ATSP4", "ATIIA {tgt}") + _PSA_ADDRESSING + ("?ATSI",),
        targets=PSA_ENGINE_TARGETS,
        init_timeout=18.0,
    ),
    Profile(
        name="kwp-fast-std",
        description="KWP2000 fast init, ISO functional addressing (C1 33 F1)",
        setup=_COMMON + ("ATSP5",),
    ),
    Profile(
        name="iso9141",
        description="ISO 9141-2 slow init (early EOBD petrol ECUs)",
        setup=_COMMON + ("ATSP3",),
        sessions=(None,),
        reads=(bytes([0x03]), bytes([0x07])),
        clears=(bytes([0x04]),),
        init_timeout=18.0,
    ),
    Profile(
        name="kwp-can-psa",
        description="KWP2000-on-CAN at PSA engine ECU IDs 6A8/688 "
                    "(late 206-era ECUs, needs CAN wired to pins 6/14)",
        setup=_COMMON + (
            "ATSP6",         # ISO 15765-4, 11-bit, 500 kbit
            "ATSH 6A8",      # PSA engine ECU request ID
            "ATCRA 688",     # ... and its reply ID
            "?ATFCSH 6A8",   # flow control from the same ID
        ),
        sessions=(bytes([0x10, 0xC0]), bytes([0x81]), None),
    ),
)


def get_profile(name: str) -> Profile:
    for p in PROFILES:
        if p.name == name:
            return p
    raise KeyError(f"unknown profile {name!r}; known: {', '.join(p.name for p in PROFILES)}")
