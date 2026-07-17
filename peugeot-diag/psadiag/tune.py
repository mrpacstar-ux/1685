"""Read-only "is this ECU already remapped?" check.

Reads the ECU's identification records over KWP2000 (service 0x1A) and,
where the ECU exposes it, the reflash fingerprint (programming date /
counter / tester code). From those it forms a *best-effort* verdict —
never a certainty, because a careful tuner can preserve the original
calibration number, and the only definitive test is reading the flash and
comparing to a known-stock image.

No writing, no security access, nothing that can change the ECU.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from .elm327 import BusError
from .kwp import NegativeResponse, strip_header

# KWP2000 service 0x1A readEcuIdentification — local identifiers and the
# field each commonly returns on Bosch/PSA ECUs. Read best-effort; only
# the ones the ECU answers are shown.
IDENTIFIERS = {
    0x80: "ECU identification",
    0x86: "DTC-format identifier",
    0x8C: "VIN",
    0x90: "VIN",
    0x91: "Hardware number",
    0x92: "Hardware version",
    0x94: "Software number",
    0x95: "Software version",
    0x96: "Calibration number",
    0x97: "System / ECU name",
    0x98: "Supplier",
    0x99: "Programming date",
    0x9A: "Repair-shop / tester code",
    0x9B: "Tester serial number",
    0x9C: "Programming counter",
}

# Fields whose presence/value is evidence the ECU was reflashed after the
# factory. Populated conservatively; see verdict logic below.
_REFLASH_FIELDS = ("Programming date", "Repair-shop / tester code",
                   "Tester serial number", "Programming counter")

# Known-stock software/hardware numbers, keyed by normalised string.
# Seeded from research (see README); may be partial. A match means
# "consistent with a known factory calibration", NOT proof of stock.
# A non-match means "not in our list" — which could be a remap OR simply a
# factory number we don't have on file.
STOCK_NUMBERS: dict[str, str] = {
    # normalised-number : human label   (filled in from verified sources)
}

# Substrings that betray a tuner's flash tool or naming in an ID string.
_TUNER_HINTS = ("STAGE", "TUNED", "REMAP", "WINOLS", "KESS", "MPPS",
                "GALLETTO", "KTAG", "TUNE")


def _norm(s: str) -> str:
    return re.sub(r"[^0-9A-Z]", "", s.upper())


@dataclass
class TuneReport:
    fields: list[tuple[str, str]] = field(default_factory=list)
    verdict: str = "unknown"          # "stock" | "reflashed" | "unknown"
    headline: str = ""
    reasons: list[str] = field(default_factory=list)

    def add(self, label: str, value: str):
        self.fields.append((label, value))


def _read_identifier(request, ident: int) -> str | None:
    try:
        frames = request(bytes([0x1A, ident]))
    except BusError:
        return None
    for frame in frames:
        try:
            payload = strip_header(frame, 0x1A)
        except NegativeResponse:
            return None
        if payload and len(payload) > 2 and payload[1] == ident:
            data = payload[2:]
            text = "".join(chr(b) if 32 <= b < 127 else "" for b in data).strip()
            # prefer ASCII if it's meaningful, else show hex
            if len(text) >= 3 and any(c.isalnum() for c in text):
                return text
            return data.hex().upper()
    return None


def check_tune(request, status=lambda m: None) -> TuneReport:
    """Read identification + reflash evidence and form a verdict."""
    report = TuneReport()
    seen: dict[str, str] = {}

    for ident, label in IDENTIFIERS.items():
        value = _read_identifier(request, ident)
        if value:
            report.add(label, value)
            seen.setdefault(label, value)
            status(f"  {label}: {value}")

    # ---- collect the numbers we can judge on
    numbers = [seen[k] for k in ("Software number", "Calibration number",
                                 "Hardware number", "ECU identification")
               if k in seen]
    matched_stock = [(n, STOCK_NUMBERS[_norm(n)]) for n in numbers
                     if _norm(n) in STOCK_NUMBERS]

    reflash_evidence = [(k, seen[k]) for k in _REFLASH_FIELDS if k in seen]
    tuner_marks = [(k, v) for k, v in report.fields
                   if any(h in v.upper() for h in _TUNER_HINTS)]

    # ---- verdict, most-confident signal first
    if tuner_marks:
        report.verdict = "reflashed"
        report.headline = "Almost certainly REMAPPED"
        report.reasons.append(
            "An identification string names a tuning tool/stage: "
            + "; ".join(f"{k} = {v}" for k, v in tuner_marks))
    elif matched_stock:
        report.verdict = "stock"
        report.headline = "Looks STOCK (matches a known factory calibration)"
        for n, lbl in matched_stock:
            report.reasons.append(f"{n} matches known stock: {lbl}")
        report.reasons.append(
            "Caveat: a skilled tuner can keep the original number, so this "
            "is strong but not absolute proof.")
    elif reflash_evidence and _looks_reprogrammed(reflash_evidence):
        report.verdict = "reflashed"
        report.headline = "Shows signs of having been REPROGRAMMED"
        report.reasons.append(
            "The ECU records a programming fingerprint (below) that usually "
            "means it was flashed after leaving the factory — often a remap, "
            "but a dealer software update can look the same.")
        report.reasons += [f"{k} = {v}" for k, v in reflash_evidence]
    else:
        report.verdict = "unknown"
        if numbers and STOCK_NUMBERS:
            report.headline = "UNKNOWN — number not in our stock list"
            report.reasons.append(
                "The calibration number isn't one we have on file as stock. "
                "That could mean a remap, or just a factory number we don't "
                "list. Compare it against a stock reference for your exact "
                "engine (a PSA specialist or an HDi forum can confirm).")
        else:
            report.headline = "UNKNOWN — can't judge from the data available"
            report.reasons.append(
                "Note down the numbers above and compare them against a "
                "known-stock reference for your engine. The only definitive "
                "test is reading the flash and comparing to a stock image.")
        if numbers:
            report.reasons.append("Numbers read: " + ", ".join(numbers))

    if not report.fields:
        report.headline = "No identification returned by this ECU"
        report.reasons = [
            "This ECU didn't answer the identification requests. Some early "
            "EDC15 units expose little over K-line, or the session needs to "
            "be open first (connect, then run this check)."]
    return report


def _looks_reprogrammed(evidence: list[tuple[str, str]]) -> bool:
    """True if the fingerprint suggests more than a single factory write."""
    for key, val in evidence:
        norm = _norm(val)
        if key == "Programming counter":
            digits = re.sub(r"\D", "", val)
            if digits and int(digits[-4:] or 0) > 1:   # written more than once
                return True
        elif key in ("Tester serial number", "Repair-shop / tester code"):
            # a non-zero, non-Peugeot-production tester code is a hint
            if norm and set(norm) != {"0"} and not norm.startswith("FFFF"):
                return True
        elif key == "Programming date":
            if norm and set(norm) != {"0"}:
                return True
    return False
