"""KWP2000 / OBD-II service helpers: building requests, parsing DTC replies.

The ELM327 does the framing (headers + checksum) once configured, so at
this layer a request is just the service ID plus parameters, and a reply
is the positive-response service byte plus data. Replies may still carry
K-line headers if ATH1 is on — strip_header() deals with that.
"""

from __future__ import annotations

from dataclasses import dataclass

# KWP2000 (ISO 14230-3) services
SID_START_DIAG_SESSION = 0x10
SID_READ_DTC_STORED = 0x13        # older PSA/KW82-era "read stored codes"
SID_CLEAR_DIAG_INFO = 0x14
SID_READ_STATUS_OF_DTC = 0x17
SID_READ_DTC_BY_STATUS = 0x18
SID_TESTER_PRESENT = 0x3E
NEGATIVE_RESPONSE = 0x7F

# OBD-II (SAE J1979) modes
MODE_STORED_DTCS = 0x03
MODE_CLEAR_DTCS = 0x04
MODE_PENDING_DTCS = 0x07

NRC_TEXT = {
    0x10: "general reject",
    0x11: "service not supported",
    0x12: "sub-function not supported / invalid format",
    0x21: "busy, repeat request",
    0x22: "conditions not correct (ignition on, engine off?)",
    0x23: "routine not complete",
    0x31: "request out of range",
    0x33: "security access denied",
    0x78: "response pending (ECU is slow, retry)",
}


@dataclass(frozen=True)
class Dtc:
    code: str          # e.g. "P0135"
    status: int | None  # KWP status byte if the ECU supplied one
    raw: bytes

    @property
    def is_active(self) -> bool | None:
        # bit 7 of the ISO 14230 status byte ~ "malfunction currently present"
        return bool(self.status & 0x80) if self.status is not None else None


def decode_dtc_bytes(hi: int, lo: int) -> str:
    """Two raw DTC bytes -> SAE code string per ISO 15031-6."""
    letter = "PCBU"[(hi & 0xC0) >> 6]
    return f"{letter}{(hi & 0x30) >> 4}{hi & 0x0F:X}{lo >> 4:X}{lo & 0x0F:X}"


def strip_header(frame: bytes, expect_sid: int) -> bytes | None:
    """Return payload starting at the positive-response SID, or None.

    Handles frames with no header, with an ISO 3-byte header (fmt tgt src),
    and with a trailing checksum byte. A 0x7F negative response raises.
    """
    resp = expect_sid | 0x40
    for start in range(min(5, len(frame))):
        if frame[start] == resp:
            return frame[start:]
        if frame[start] == NEGATIVE_RESPONSE and start + 2 < len(frame) \
                and frame[start + 1] == expect_sid:
            nrc = frame[start + 2]
            raise NegativeResponse(expect_sid, nrc)
    return None


class NegativeResponse(Exception):
    def __init__(self, sid: int, nrc: int):
        self.sid, self.nrc = sid, nrc
        text = NRC_TEXT.get(nrc, "unknown code")
        super().__init__(f"ECU refused service {sid:02X}: NRC {nrc:02X} ({text})")

    @property
    def pending(self) -> bool:
        return self.nrc == 0x78


def parse_dtc_reply(frames: list[bytes], sid: int) -> list[Dtc]:
    """Parse DTCs out of the reply frames for the given request SID.

    Layouts handled:
      OBD mode 03/07 :  43 [hi lo] x3 padded with 00 00
      KWP 0x13       :  53 [hi lo] repeated              (no status byte)
      KWP 0x17/0x18  :  57/58 count [hi lo status] repeated
    """
    dtcs: list[Dtc] = []
    for frame in frames:
        payload = strip_header(frame, sid)
        if payload is None:
            continue
        body = payload[1:]

        if sid in (MODE_STORED_DTCS, MODE_PENDING_DTCS, SID_READ_DTC_STORED):
            step, has_status = 2, False
        else:
            # first byte is the DTC count
            body = body[1:]
            step, has_status = 3, True

        # a checksum byte can leave a trailing odd byte — ignore remainder
        for i in range(0, len(body) - step + 1, step):
            hi, lo = body[i], body[i + 1]
            if hi == 0 and lo == 0:
                continue  # padding
            status = body[i + 2] if has_status else None
            dtcs.append(Dtc(decode_dtc_bytes(hi, lo), status, bytes(body[i:i + step])))

    # de-duplicate across multiple reply frames, preserve order
    seen, unique = set(), []
    for d in dtcs:
        if d.code not in seen:
            seen.add(d.code)
            unique.append(d)
    return unique
