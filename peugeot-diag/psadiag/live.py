"""Live sensor data and ECU identification.

Works over any transport: functions take a `request(payload) -> frames`
callable (the ELM327 or raw K-line backend). Live values use the standard
OBD mode 01 PIDs, which EOBD-capable PSA ECUs answer even inside a
manufacturer KWP session; pure pre-EOBD ECUs may refuse them, in which
case the GUI says so rather than showing garbage.
"""

from __future__ import annotations

from dataclasses import dataclass

from .elm327 import BusError
from .kwp import NegativeResponse, strip_header


@dataclass(frozen=True)
class Pid:
    pid: int
    name: str
    unit: str
    nbytes: int
    decode: "callable"


PIDS = (
    Pid(0x0C, "Engine speed", "rpm", 2, lambda a, b=0: (a * 256 + b) / 4),
    Pid(0x05, "Coolant temperature", "°C", 1, lambda a, b=0: a - 40),
    Pid(0x0F, "Intake air temperature", "°C", 1, lambda a, b=0: a - 40),
    Pid(0x04, "Engine load", "%", 1, lambda a, b=0: round(a * 100 / 255, 1)),
    Pid(0x11, "Throttle position", "%", 1, lambda a, b=0: round(a * 100 / 255, 1)),
    Pid(0x0B, "Manifold pressure (MAP)", "kPa", 1, lambda a, b=0: a),
    Pid(0x10, "Air flow (MAF)", "g/s", 2, lambda a, b=0: round((a * 256 + b) / 100, 1)),
    Pid(0x0D, "Vehicle speed", "km/h", 1, lambda a, b=0: a),
    Pid(0x0E, "Ignition advance", "° BTDC", 1, lambda a, b=0: a / 2 - 64),
    Pid(0x06, "Short-term fuel trim", "%", 1, lambda a, b=0: round((a - 128) * 100 / 128, 1)),
    Pid(0x07, "Long-term fuel trim", "%", 1, lambda a, b=0: round((a - 128) * 100 / 128, 1)),
    Pid(0x14, "Lambda sensor B1S1", "V", 2, lambda a, b=0: round(a / 200, 3)),
    # diesel / HDi common-rail readings
    Pid(0x23, "Fuel rail pressure", "bar", 2, lambda a, b=0: round((a * 256 + b) * 10 / 1000, 1)),
    Pid(0x22, "Fuel rail pressure (rel.)", "kPa", 2, lambda a, b=0: round((a * 256 + b) * 0.079, 1)),
    Pid(0x2C, "Commanded EGR", "%", 1, lambda a, b=0: round(a * 100 / 255, 1)),
    Pid(0x33, "Barometric pressure", "kPa", 1, lambda a, b=0: a),
    Pid(0x42, "ECU supply voltage", "V", 2, lambda a, b=0: round((a * 256 + b) / 1000, 2)),
)


def supported_pids(request) -> set[int]:
    """Probe mode 01 PID 00 for the supported-PIDs bitmap; empty if refused."""
    try:
        frames = request(bytes([0x01, 0x00]))
    except BusError:
        return set()
    for frame in frames:
        try:
            payload = strip_header(frame, 0x01)
        except NegativeResponse:
            return set()
        if payload and len(payload) >= 6 and payload[1] == 0x00:
            bitmap = int.from_bytes(payload[2:6], "big")
            return {i + 1 for i in range(32) if bitmap & (1 << (31 - i))}
    return set()


def read_pid(request, pid: Pid):
    """One live value, or None if the ECU refuses/ignores the PID."""
    try:
        frames = request(bytes([0x01, pid.pid]))
    except BusError:
        return None
    for frame in frames:
        try:
            payload = strip_header(frame, 0x01)
        except NegativeResponse:
            return None
        if payload and len(payload) >= 2 + pid.nbytes and payload[1] == pid.pid:
            data = payload[2:2 + pid.nbytes]
            return pid.decode(*data)
    return None


def _ascii(data: bytes) -> str:
    return "".join(chr(b) if 32 <= b < 127 else "" for b in data).strip()


def read_ecu_info(request) -> list[tuple[str, str]]:
    """Best-effort identification: OBD mode 09 VIN + KWP readEcuIdentification."""
    info: list[tuple[str, str]] = []

    try:  # OBD mode 09 PID 02: VIN
        frames = request(bytes([0x09, 0x02]))
        text = _ascii(b"".join(frames))
        # VIN is 17 chars; salvage the longest alnum run
        runs = [r for r in "".join(c if c.isalnum() else " " for c in text).split()
                if len(r) >= 11]
        if runs:
            info.append(("VIN (OBD)", max(runs, key=len)))
    except (BusError, NegativeResponse):
        pass

    # KWP 1A readEcuIdentification, common PSA/ISO local identifiers
    for ident, label in ((0x80, "ECU identification"), (0x90, "VIN (KWP)"),
                         (0x91, "Hardware number"), (0x92, "Hardware version"),
                         (0x94, "Software number"), (0x97, "System name"),
                         (0x98, "Supplier")):
        try:
            frames = request(bytes([0x1A, ident]))
        except BusError:
            continue
        for frame in frames:
            try:
                payload = strip_header(frame, 0x1A)
            except NegativeResponse:
                payload = None
            if payload and len(payload) > 2:
                text = _ascii(payload[2:])
                if text:
                    info.append((label, text))
                break
    return info
