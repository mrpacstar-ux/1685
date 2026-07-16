"""Low-level driver for ELM327-compatible serial adapters.

Handles port discovery, AT command plumbing, and turning raw hex reply
lines into byte payloads. Everything protocol-specific lives in
profiles.py / kwp.py — this module only knows how to talk to the chip.
"""

from __future__ import annotations

import sys
import time
from dataclasses import dataclass, field

try:
    import serial
    from serial.tools import list_ports
except ImportError:  # pragma: no cover
    sys.exit("pyserial is required:  pip install pyserial")


class AdapterError(Exception):
    """The adapter itself misbehaved (port gone, no prompt, garbage)."""


class BusError(Exception):
    """The adapter is fine but the car did not answer as expected."""


# Replies the ELM emits that mean "no ECU answered" rather than data.
NO_DATA_REPLIES = {
    "NO DATA", "UNABLE TO CONNECT", "BUS INIT: ERROR", "BUS INIT: ...ERROR",
    "BUS ERROR", "CAN ERROR", "DATA ERROR", "FB ERROR", "STOPPED", "ERROR",
}

USB_SERIAL_HINTS = (
    # (VID, name fragment) pairs commonly seen on ELM327 / KKL cables
    "CH340", "CP210", "FTDI", "FT232", "PL2303", "ELM327", "OBD",
)


@dataclass
class Elm327:
    port: str
    baudrate: int = 38400
    timeout: float = 5.0
    verbose: bool = False
    _ser: "serial.Serial" = field(default=None, repr=False)
    identity: str = ""

    # ------------------------------------------------------------------ setup

    @staticmethod
    def candidate_ports() -> list[str]:
        """Serial ports on this machine, most-likely-adapter first."""
        ports = list(list_ports.comports())

        def score(p):
            text = f"{p.description or ''} {p.manufacturer or ''}".upper()
            return -sum(hint in text for hint in USB_SERIAL_HINTS)

        return [p.device for p in sorted(ports, key=score)]

    @classmethod
    def autodetect(cls, baudrates=(38400, 115200, 9600), verbose=False) -> "Elm327":
        """Try every plausible port/baud until an ELM prompt answers."""
        ports = cls.candidate_ports()
        if not ports:
            raise AdapterError(
                "No serial ports found. Is the USB interface plugged in?\n"
                "(On Linux you may need to be in the 'dialout' group.)"
            )
        errors = []
        for port in ports:
            for baud in baudrates:
                elm = cls(port=port, baudrate=baud, verbose=verbose)
                try:
                    elm.open()
                    return elm
                except (AdapterError, serial.SerialException) as exc:
                    errors.append(f"  {port} @ {baud}: {exc}")
                    elm.close()
        raise AdapterError("No ELM327 adapter answered:\n" + "\n".join(errors))

    def open(self) -> None:
        self._ser = serial.Serial(
            self.port, self.baudrate, timeout=0.3,
            bytesize=serial.EIGHTBITS, parity=serial.PARITY_NONE,
            stopbits=serial.STOPBITS_ONE,
        )
        # A reset proves there is really an ELM on the other end.
        reply = self.command("ATZ", timeout=3.0)
        if not any("ELM" in line.upper() or "OBD" in line.upper() for line in reply):
            raise AdapterError(f"no ELM327 prompt on {self.port} (got {reply!r})")
        self.identity = reply[-1] if reply else "unknown"
        self.command("ATE0")   # echo off
        self.command("ATL0")   # no linefeeds
        self.command("ATS1")   # keep spaces — easier hex parsing

    def close(self) -> None:
        if self._ser and self._ser.is_open:
            try:
                self._ser.close()
            except serial.SerialException:
                pass

    # ------------------------------------------------------------- raw plumbing

    def command(self, cmd: str, timeout: float | None = None) -> list[str]:
        """Send one command, collect reply lines until the '>' prompt."""
        if not self._ser:
            raise AdapterError("port not open")
        deadline = time.monotonic() + (timeout or self.timeout)
        if self.verbose:
            print(f"    >> {cmd}", file=sys.stderr)
        self._ser.reset_input_buffer()
        self._ser.write((cmd + "\r").encode("ascii"))

        buf = ""
        while time.monotonic() < deadline:
            chunk = self._ser.read(self._ser.in_waiting or 1)
            if chunk:
                buf += chunk.decode("ascii", errors="replace")
                if ">" in buf:
                    break
        else:
            raise AdapterError(f"timeout waiting for prompt after {cmd!r}")

        lines = []
        for line in buf.replace(">", "").replace("\r", "\n").split("\n"):
            line = line.strip()
            # drop echo, blanks, and the transient SEARCHING banner
            if line and line != cmd and not line.startswith("SEARCHING"):
                lines.append(line)
        if self.verbose:
            for line in lines:
                print(f"    << {line}", file=sys.stderr)
        return lines

    def at(self, cmd: str, timeout: float | None = None) -> list[str]:
        """AT command; raises if the chip rejects it with '?'."""
        reply = self.command(cmd, timeout=timeout)
        if any(line == "?" for line in reply):
            raise AdapterError(f"adapter rejected {cmd!r} (old/clone firmware?)")
        return reply

    # -------------------------------------------------------------- OBD traffic

    def request(self, payload: bytes, timeout: float | None = None) -> list[bytes]:
        """Send a hex request to the car, return each reply line as bytes.

        Bus init (5-baud especially) can take several seconds, so the
        default timeout here is generous.
        """
        cmd = payload.hex().upper()
        reply = self.command(cmd, timeout=timeout or max(self.timeout, 12.0))

        frames: list[bytes] = []
        for line in reply:
            up = line.upper()
            if up in NO_DATA_REPLIES or up.startswith("BUS INIT") and "ERROR" in up:
                continue
            hexstr = line.replace(" ", "")
            if hexstr and all(c in "0123456789ABCDEFabcdef" for c in hexstr) \
                    and len(hexstr) % 2 == 0:
                frames.append(bytes.fromhex(hexstr))
        if not frames:
            raise BusError(f"no response to {cmd} (adapter said: {reply!r})")
        return frames
