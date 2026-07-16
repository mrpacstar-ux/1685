"""Tests against a simulated PSA ECU — no hardware needed.

The fake models a 206-era engine ECU that ignores standard OBD-II
auto-search and only answers KWP2000 fast init addressed to 0x10, which is
exactly the behaviour that defeats generic scanners.
"""

import unittest

from psadiag.elm327 import Elm327
from psadiag.kwp import decode_dtc_bytes, parse_dtc_reply
from psadiag.session import clear_dtcs, connect, read_dtcs


class FakePsaEcu(Elm327):
    """Elm327 with the serial layer replaced by a scripted ECU."""

    def __init__(self):
        super().__init__(port="fake")
        self.proto = "0"
        self.header = ""
        self.cleared = False

    def open(self):
        self.identity = "ELM327 v1.5 (simulated)"

    def close(self):
        pass

    def command(self, cmd, timeout=None):
        c = cmd.replace(" ", "").upper()
        if c.startswith("AT"):
            if c.startswith("ATSP"):
                self.proto = c[4:]
            elif c.startswith("ATSH"):
                self.header = c[4:]
            elif c == "ATZ":
                return ["ELM327 v1.5 (simulated)"]
            return ["OK"]
        return self._ecu(c)

    def _ecu(self, hexcmd):
        # Only reachable via KWP fast init, physically addressed to 0x10.
        if self.proto != "5" or self.header != "8110F1":
            return ["UNABLE TO CONNECT"]
        if hexcmd == "81":          # StartCommunication (ddt4all-style)
            return ["C1 EF 8F"]
        if hexcmd == "17FF00":
            if self.cleared:
                return ["57 00"]
            # two DTCs: P0135 (active) and P0505 (stored)
            return ["57 02 01 35 E0 05 05 61"]
        if hexcmd == "14FF00":
            self.cleared = True
            return ["54 FF 00"]
        return ["7F " + hexcmd[:2] + " 11"]


class DecodeTests(unittest.TestCase):
    def test_p_code(self):
        self.assertEqual(decode_dtc_bytes(0x01, 0x35), "P0135")

    def test_letter_ranges(self):
        self.assertEqual(decode_dtc_bytes(0x41, 0x00), "C0100")
        self.assertEqual(decode_dtc_bytes(0x81, 0x00), "B0100")
        self.assertEqual(decode_dtc_bytes(0xC1, 0x00), "U0100")

    def test_obd_mode03_reply(self):
        frames = [bytes.fromhex("43013505050000")]
        codes = [d.code for d in parse_dtc_reply(frames, 0x03)]
        self.assertEqual(codes, ["P0135", "P0505"])

    def test_kwp18_reply_with_status_and_header(self):
        frames = [bytes.fromhex("80F110085802 0135E0 050561".replace(" ", ""))]
        dtcs = parse_dtc_reply(frames, 0x18)
        self.assertEqual([d.code for d in dtcs], ["P0135", "P0505"])
        self.assertTrue(dtcs[0].is_active)
        self.assertFalse(dtcs[1].is_active)


class KLineFramingTests(unittest.TestCase):
    """The raw-cable backend's frame splitter (no serial port involved)."""

    @staticmethod
    def _frame(target, source, payload):
        f = bytes([0x80 | len(payload), target, source]) + payload
        return f + bytes([sum(f) & 0xFF])

    def test_split_two_frames(self):
        from psadiag.kline import KLine
        a = self._frame(0xF1, 0x10, bytes.fromhex("7E"))
        b = self._frame(0xF1, 0x10, bytes.fromhex("570201 35E0 050561".replace(" ", "")))
        frames = KLine._split_frames(a + b)
        self.assertEqual(frames, [a, b])
        dtcs = parse_dtc_reply([frames[1]], 0x17)
        self.assertEqual([d.code for d in dtcs], ["P0135", "P0505"])

    def test_garbage_returned_whole(self):
        from psadiag.kline import KLine
        raw = bytes.fromhex("55EF8F")   # sync/key bytes, not a KWP frame
        self.assertEqual(KLine._split_frames(raw), [raw])


class LadderTests(unittest.TestCase):
    def setUp(self):
        self.elm = FakePsaEcu()
        self.elm.open()

    def test_connects_via_psa_fast_init(self):
        conn = connect(self.elm, status=lambda m: None)
        self.assertEqual(conn.profile.name, "kwp-fast-psa")
        self.assertEqual(conn.target, 0x10)
        self.assertEqual(conn.session, bytes([0x81]))

    def test_read_and_clear(self):
        conn = connect(self.elm, status=lambda m: None)
        dtcs = read_dtcs(conn)
        self.assertEqual([d.code for d in dtcs], ["P0135", "P0505"])
        self.assertTrue(clear_dtcs(conn))
        self.assertEqual(read_dtcs(conn), [])


if __name__ == "__main__":
    unittest.main()
