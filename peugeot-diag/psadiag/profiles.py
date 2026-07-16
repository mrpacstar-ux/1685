"""Connection profiles: the ladder of init strategies tried against the car.

Generic scan tools stop after the standard OBD-II auto-search; PSA ECUs of
the 306/206 era usually need a manufacturer-specific KWP2000 init with a
specific target address instead. Each profile describes one strategy as
plain data so new ECU quirks can be added without touching the logic.

Byte values collected from PSA reverse-engineering projects and forum
captures of Lexia/PP2000 traffic; see README for sources.
"""

from __future__ import annotations

from dataclasses import dataclass

# Physical target addresses PSA engine ECUs answer on (source addr is the
# tester, 0xF1). 0x10 is the classic PSA engine-ECU diag address; 0x33 is
# the generic-OBD functional address; the others show up on specific
# Bosch/Sagem/Marelli units.
PSA_ENGINE_TARGETS = (0x10, 0x33, 0x01, 0x11, 0x28)

# StartDiagnosticSession sub-function bytes to attempt, in order.
# 0x81 = standard diagnostics; 0xC0 seen in PSA tool traces; 0x85 = ECU
# programming session (never tried here). None = skip session setup, some
# ECUs talk without one.
SESSION_BYTES = (0x81, 0xC0, None)

# DTC read requests to attempt, in order of how widely they work.
READ_REQUESTS = (
    bytes([0x18, 0x00, 0xFF, 0x00]),  # readDTCByStatus: all identified, group FF00
    bytes([0x18, 0x02, 0xFF, 0x00]),  # readDTCByStatus: all supported
    bytes([0x17, 0xFF, 0x00]),        # readStatusOfDTC, group FF00
    bytes([0x13]),                    # readDiagnosticTroubleCodes (older units)
    bytes([0x03]),                    # OBD-II mode 03 (EOBD-capable ECUs)
    bytes([0x07]),                    # OBD-II mode 07 (pending)
)

CLEAR_REQUESTS = (
    bytes([0x14, 0xFF, 0x00]),        # clearDiagnosticInformation, all groups
    bytes([0x04]),                    # OBD-II mode 04
)


@dataclass(frozen=True)
class Profile:
    name: str
    description: str
    setup: tuple[str, ...]            # AT commands, {tgt} formatted with target
    targets: tuple[int | None, ...] = (None,)   # None -> no per-target formatting
    sessions: tuple[int | None, ...] = SESSION_BYTES
    reads: tuple[bytes, ...] = READ_REQUESTS
    clears: tuple[bytes, ...] = CLEAR_REQUESTS
    init_timeout: float = 12.0        # 5-baud init alone takes ~3 s

    def setup_for(self, target: int | None) -> list[str]:
        t = f"{target:02X}" if target is not None else ""
        return [cmd.format(tgt=t) for cmd in self.setup]


# Shared preamble: long messages allowed, generous ECU-response timeout,
# adaptive timing off so slow old ECUs aren't cut short.
_COMMON = ("ATAL", "ATST C8", "ATAT0")

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
        description="KWP2000 fast init, PSA physical addressing (80 tgt F1)",
        setup=_COMMON + (
            "ATSP5",
            "ATSH 80 {tgt} F1",
            "ATWM 81 {tgt} F1 3E",   # keepalive the ELM sends between requests
        ),
        targets=PSA_ENGINE_TARGETS,
    ),
    Profile(
        name="kwp-fast-std",
        description="KWP2000 fast init, ISO functional addressing (C1 33 F1)",
        setup=_COMMON + ("ATSP5",),
    ),
    Profile(
        name="kwp-5baud-psa",
        description="ISO 5-baud slow init at PSA ECU addresses",
        setup=_COMMON + (
            "ATSP4",
            "ATIIA {tgt}",
            "ATSH 80 {tgt} F1",
            "ATWM 81 {tgt} F1 3E",
        ),
        targets=PSA_ENGINE_TARGETS,
        init_timeout=18.0,
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
)


def get_profile(name: str) -> Profile:
    for p in PROFILES:
        if p.name == name:
            return p
    raise KeyError(f"unknown profile {name!r}; known: {', '.join(p.name for p in PROFILES)}")
