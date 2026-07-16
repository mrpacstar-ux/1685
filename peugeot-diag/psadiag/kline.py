"""Raw K-line backend for "dumb" cables (VAG KKL 409.1, FTDI-based).

An ELM327 hides the ISO 14230 physical layer; a KKL cable exposes it.
This module does the physical layer itself:

  - 5-baud slow init, bit-banged with serial break conditions (200 ms per
    bit — the UART can't go that slow, but holding/releasing break can)
  - fast init (25 ms low / 25 ms high wakeup, then StartCommunication)
  - KWP2000 framing: fmt/target/source header + checksum, echo removal
    (K-line is a single wire, so everything sent is read back)

Timing is done with time.sleep(); its few-ms jitter is well inside the
ISO tolerances for 5-baud (±10 %) and usually fine for fast init (retry
covers the occasional miss).
"""

from __future__ import annotations

import sys
import time
from dataclasses import dataclass

import serial

from .elm327 import BusError
from .kwp import Dtc, NegativeResponse, parse_dtc_reply, strip_header
from .profiles import (
    CLEAR_REQUESTS,
    PSA_ENGINE_TARGETS,
    READ_REQUESTS,
    SESSION_REQUESTS,
)

TESTER = 0xF1
BAUD = 10400


class KLine:
    """One K-line conversation with one ECU over a dumb serial cable."""

    def __init__(self, port: str, verbose: bool = False):
        self.port = port
        self.verbose = verbose
        self.ser = serial.Serial(port, BAUD, timeout=0.3,
                                 bytesize=serial.EIGHTBITS,
                                 parity=serial.PARITY_NONE,
                                 stopbits=serial.STOPBITS_ONE)
        self.target: int | None = None
        self.keybytes = b""

    def close(self):
        try:
            self.ser.close()
        except serial.SerialException:
            pass

    def _log(self, msg: str):
        if self.verbose:
            print(f"    {msg}", file=sys.stderr)

    # ------------------------------------------------------------------ init

    def _idle(self, seconds: float):
        self.ser.break_condition = False
        time.sleep(seconds)

    def five_baud_init(self, address: int) -> bool:
        """ISO 5-baud slow init: clock the address out at 200 ms/bit."""
        self._log(f"5-baud init, address 0x{address:02X}")
        self._idle(0.3)  # W5: bus must be quiet before init
        self.ser.reset_input_buffer()

        # start bit (low) + 8 data bits LSB-first + stop bit (high);
        # break ON pulls K low, break OFF releases it high
        bits = [0] + [(address >> i) & 1 for i in range(8)] + [1]
        for bit in bits:
            self.ser.break_condition = (bit == 0)
            time.sleep(0.200)
        self.ser.break_condition = False

        # bit-banging feeds garbage into our own receiver — discard it
        time.sleep(0.05)
        self.ser.reset_input_buffer()

        sync = self._read_bytes(1, timeout=1.2)     # W1: sync byte 0x55
        if sync != b"\x55":
            self._log(f"no 0x55 sync (got {sync.hex() or 'nothing'})")
            return False
        kb = self._read_bytes(2, timeout=0.6)       # key bytes
        if len(kb) < 2:
            self._log("key bytes missing")
            return False
        self.keybytes = kb
        self._log(f"key bytes {kb.hex()}")
        time.sleep(0.030)                           # W4
        self._write_raw(bytes([kb[1] ^ 0xFF]))      # invert KB2 back
        ack = self._read_bytes(1, timeout=0.6)      # inverted address ack
        self.target = address
        self._log(f"init ack {ack.hex() or 'none'}")
        return True

    def fast_init(self, target: int) -> bool:
        """ISO 14230 fast init: 25 ms low / 25 ms high, then StartComm."""
        self._log(f"fast init, target 0x{target:02X}")
        self._idle(0.3)
        self.ser.reset_input_buffer()
        self.ser.break_condition = True
        time.sleep(0.025)
        self.ser.break_condition = False
        time.sleep(0.025)
        self.target = target
        try:
            frames = self.request(bytes([0x81]), timeout=1.5)
        except BusError:
            self.target = None
            return False
        for frame in frames:
            try:
                if strip_header(frame, 0x81):
                    self.keybytes = frame[-3:-1]
                    return True
            except NegativeResponse:
                return False
        self.target = None
        return False

    # ------------------------------------------------------------- raw bytes

    def _write_raw(self, data: bytes):
        self.ser.write(data)
        self.ser.flush()
        # single-wire bus: our own bytes echo back — read them off
        echoed = self._read_bytes(len(data), timeout=0.5)
        if echoed != data:
            self._log(f"echo mismatch: sent {data.hex()} got {echoed.hex()}")

    def _read_bytes(self, n: int, timeout: float) -> bytes:
        deadline = time.monotonic() + timeout
        out = b""
        while len(out) < n and time.monotonic() < deadline:
            out += self.ser.read(n - len(out))
        return out

    def _read_frame_bytes(self, first_timeout: float) -> bytes:
        """Everything the ECU says until the bus goes quiet."""
        first = self._read_bytes(1, timeout=first_timeout)
        if not first:
            return b""
        buf = first
        quiet = 0.0
        while quiet < 0.06:                          # P1/P2 inter-byte gap
            chunk = self.ser.read(64)
            if chunk:
                buf += chunk
                quiet = 0.0
            else:
                quiet += self.ser.timeout or 0.3
        return buf

    # --------------------------------------------------------------- framing

    def request(self, payload: bytes, timeout: float = 2.0) -> list[bytes]:
        """Send one KWP request, return raw reply frames (with headers)."""
        if self.target is None:
            raise BusError("K-line not initialised")
        if not 1 <= len(payload) <= 0x3F:
            raise ValueError("payload length out of range for one frame")
        frame = bytes([0x80 | len(payload), self.target, TESTER]) + payload
        frame += bytes([sum(frame) & 0xFF])
        self._log(f">> {frame.hex()}")
        self.ser.reset_input_buffer()
        self._write_raw(frame)

        raw = self._read_frame_bytes(first_timeout=timeout)
        self._log(f"<< {raw.hex() or '(silence)'}")
        if not raw:
            raise BusError(f"no response to {payload.hex()}")
        return self._split_frames(raw)

    @staticmethod
    def _split_frames(raw: bytes) -> list[bytes]:
        """Split a byte run into KWP frames using the length-in-format field.

        Falls back to returning the whole run as one frame when the layout
        doesn't parse — strip_header() copes with lead-in bytes anyway.
        """
        frames, i = [], 0
        while i + 4 <= len(raw):
            fmt = raw[i]
            length = fmt & 0x3F
            if fmt & 0xC0 != 0x80 or length == 0:
                break
            end = i + 3 + length + 1                 # hdr(3) + data + checksum
            if end > len(raw):
                break
            frame = raw[i:end]
            if sum(frame[:-1]) & 0xFF != frame[-1]:
                break
            frames.append(frame)
            i = end
        return frames if frames and i == len(raw) else [raw]

    def tester_present(self):
        try:
            self.request(bytes([0x3E]), timeout=1.0)
        except BusError:
            pass


@dataclass
class KklConnection:
    kline: KLine
    init_kind: str          # "5-baud" or "fast"
    session: bytes | None

    def describe(self) -> str:
        desc = f"kkl {self.init_kind}, target 0x{self.kline.target:02X}"
        if self.session is not None:
            desc += f", session {self.session.hex().upper()}"
        return desc

    def read_dtcs(self, status=lambda m: None) -> list[Dtc]:
        collected, spoke = [], False
        for read in READ_REQUESTS:
            try:
                frames = self.kline.request(read)
            except BusError:
                continue
            spoke = True
            try:
                found = parse_dtc_reply(frames, read[0])
            except NegativeResponse as exc:
                status(f"  read {read.hex().upper()}: {exc}")
                continue
            status(f"  read {read.hex().upper()}: {len(found)} code(s)")
            for d in found:
                if all(d.code != c.code for c in collected):
                    collected.append(d)
            if found:
                break
        if not spoke:
            raise BusError("ECU stopped responding while reading codes")
        return collected

    def clear_dtcs(self, status=lambda m: None) -> bool:
        self.kline.tester_present()   # revive the link after user input
        for clear in CLEAR_REQUESTS:
            try:
                frames = self.kline.request(clear)
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

    def close(self):
        self.kline.close()


def connect_kkl(port: str, verbose: bool = False,
                status=lambda msg: print(msg, file=sys.stderr)) -> KklConnection:
    """Walk the init ladder over a raw KKL cable.

    5-baud first (the pre-2003 PSA norm), then fast init, across the known
    PSA engine ECU addresses.
    """
    kline = KLine(port, verbose=verbose)
    attempts = []
    ladder = [("5-baud", kline.five_baud_init), ("fast", kline.fast_init)]
    try:
        for kind, init in ladder:
            for target in PSA_ENGINE_TARGETS:
                status(f"  trying kkl {kind} init at 0x{target:02X} ...")
                if not init(target):
                    attempts.append(f"{kind} 0x{target:02X}: no answer")
                    continue
                for session in SESSION_REQUESTS:
                    if session == bytes([0x81]) and kind == "fast":
                        session = None   # fast init already sent StartComm
                    if session is not None:
                        try:
                            frames = kline.request(session)
                        except BusError:
                            continue
                        ok = False
                        for frame in frames:
                            try:
                                ok = bool(strip_header(frame, session[0]))
                            except NegativeResponse:
                                ok = False
                            if ok:
                                break
                        if not ok:
                            continue
                    status(f"  connected: kkl {kind} at 0x{target:02X}")
                    return KklConnection(kline, kind, session)
                # init worked but no session variant did — still usable
                status(f"  connected (no session): kkl {kind} at 0x{target:02X}")
                return KklConnection(kline, kind, None)
    except Exception:
        kline.close()
        raise
    kline.close()
    raise BusError(
        "No ECU answered on the raw K-line.\n"
        "Checklist: ignition ON, cable is FTDI-based, K-line reaches socket\n"
        "pin 7 (see HARDWARE.md for the engine-swap wiring check).\n"
        "Attempts:\n  " + "\n  ".join(attempts)
    )
