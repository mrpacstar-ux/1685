"""Connection orchestration: walk the profile ladder until the ECU answers."""

from __future__ import annotations

import sys
import time
from dataclasses import dataclass

from .elm327 import AdapterError, BusError, Elm327
from .kwp import (
    Dtc,
    NegativeResponse,
    SID_START_DIAG_SESSION,
    parse_dtc_reply,
    strip_header,
)
from .profiles import PROFILES, Profile


@dataclass
class Connection:
    elm: Elm327
    profile: Profile
    target: int | None
    session_byte: int | None

    def describe(self) -> str:
        parts = [self.profile.name]
        if self.target is not None:
            parts.append(f"target 0x{self.target:02X}")
        if self.session_byte is not None:
            parts.append(f"session 0x{self.session_byte:02X}")
        return ", ".join(parts)


def _is_pending(frames: list[bytes], sid: int) -> bool:
    """True if every reply is a 7F <sid> 78 'responsePending'."""
    needle = bytes([0x7F, sid, 0x78])
    return all(needle in frame for frame in frames)


def _try_request(elm: Elm327, payload: bytes, timeout: float):
    """One request, retried while the ECU answers NRC 0x78 (responsePending)."""
    frames = elm.request(payload, timeout=timeout)
    for _ in range(3):
        if not _is_pending(frames, payload[0]):
            break
        time.sleep(0.5)
        frames = elm.request(payload, timeout=timeout)
    return frames


def _start_session(elm: Elm327, session_byte: int | None, timeout: float) -> bool:
    if session_byte is None:
        return True
    payload = bytes([SID_START_DIAG_SESSION, session_byte])
    try:
        frames = elm.request(payload, timeout=timeout)
    except BusError:
        return False
    for frame in frames:
        try:
            if strip_header(frame, SID_START_DIAG_SESSION):
                return True
        except NegativeResponse:
            return False
    return False


def connect(elm: Elm327, profiles: list[Profile] | None = None,
            status=lambda msg: print(msg, file=sys.stderr)) -> Connection:
    """Try each profile/target/session combination until DTC reads work.

    Returns the first combination where the ECU gives any positive
    response. Raises BusError if the whole ladder is exhausted.
    """
    attempts = []
    for profile in profiles or PROFILES:
        for target in profile.targets:
            label = profile.name + (f"/0x{target:02X}" if target is not None else "")
            status(f"  trying {label} ({profile.description}) ...")
            try:
                elm.at("ATPC")  # drop any previous bus session
                for cmd in profile.setup_for(target):
                    elm.at(cmd)
            except AdapterError as exc:
                attempts.append(f"{label}: adapter: {exc}")
                continue

            for session_byte in profile.sessions:
                if not _start_session(elm, session_byte, profile.init_timeout):
                    if session_byte is not None:
                        continue
                # Prove the link with an actual DTC read attempt.
                for read in profile.reads:
                    try:
                        elm.request(read, timeout=profile.init_timeout)
                        status(f"  connected: {label}")
                        return Connection(elm, profile, target, session_byte)
                    except NegativeResponse:
                        # ECU spoke to us — the link is up, even if it
                        # dislikes this particular read.
                        status(f"  connected: {label}")
                        return Connection(elm, profile, target, session_byte)
                    except BusError:
                        continue
            attempts.append(f"{label}: no response")

    raise BusError(
        "Could not raise the ECU on any known init strategy.\n"
        "Checklist: ignition ON (engine off is fine), adapter firmly seated,\n"
        "K-line present on socket pin 7 (see README wiring notes for a\n"
        "306 with a 206 engine loom). Attempts:\n  " + "\n  ".join(attempts)
    )


def read_dtcs(conn: Connection, status=lambda msg: None) -> list[Dtc]:
    """Read fault codes, trying each read request the profile knows."""
    collected: list[Dtc] = []
    spoke = False
    for read in conn.profile.reads:
        try:
            frames = _try_request(conn.elm, read, conn.profile.init_timeout)
        except BusError:
            continue
        spoke = True
        try:
            found = parse_dtc_reply(frames, read[0])
        except NegativeResponse as exc:
            status(f"  read {read.hex()}: {exc}")
            continue
        status(f"  read {read.hex().upper()}: {len(found)} code(s)")
        for d in found:
            if all(d.code != c.code for c in collected):
                collected.append(d)
        if found:
            break  # a working read that returned codes is authoritative
    if not spoke:
        raise BusError("ECU stopped responding while reading codes")
    return collected


def clear_dtcs(conn: Connection, status=lambda msg: None) -> bool:
    """Clear fault codes. Returns True on a positive response."""
    for clear in conn.profile.clears:
        try:
            frames = _try_request(conn.elm, clear, conn.profile.init_timeout)
        except BusError:
            continue
        for frame in frames:
            try:
                if strip_header(frame, clear[0]):
                    status(f"  clear {clear.hex().upper()}: OK")
                    return True
            except NegativeResponse as exc:
                status(f"  clear {clear.hex().upper()}: {exc}")
                break
    return False
