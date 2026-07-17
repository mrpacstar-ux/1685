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
# field each commonly returns on Bosch/PSA EDC15C2 ECUs. Read best-effort;
# only the ones the ECU answers are shown. On EDC15C2 the load-bearing one
# is 0x9B (concatenated hardware + software number); 0x9C/0x99 carry the
# reflash "fingerprint" (attempts / date / tester). Byte→field numbering
# above 0x9B is not fully consistent between PSA and generic ISO14230, so
# these labels are best-effort and the raw value is always shown.
IDENTIFIERS = {
    0x80: "ECU identification",
    0x86: "Extended identification",
    0x8C: "VIN",
    0x90: "VIN",
    0x91: "Hardware number",
    0x92: "Supplier hardware number",
    0x94: "Software number",
    0x96: "Homologation code",
    0x97: "System / ECU name",
    0x98: "Supplier",
    0x99: "Programming date",
    0x9B: "ECU ident (hardware + software)",
    0x9C: "Flash status (attempts / date / tester)",
}

# Fields whose presence/value is evidence the ECU was reflashed after the
# factory. The flash-status block is the best live signal; see the honest
# reliability notes in verdict logic and TUNING.md.
_REFLASH_FIELDS = ("Flash status (attempts / date / tester)",
                   "Programming date", "Programming counter",
                   "Repair-shop / tester code", "Tester serial number")

# Verified stock EDC15C2 identity strings for the PSA 2.0 HDi (DW10).
# Any of the three numbers (Bosch part / PSA hardware / Bosch software)
# identifies a genuine factory unit. IMPORTANT: a map-only remap normally
# leaves these numbers untouched, so a match proves the ECU is a recognised
# factory part — NOT that its maps are unmodified. Sources in TUNING.md.
_STOCK_UNITS = (
    # (bosch_pn, psa_hw, bosch_sw, label)
    ("0281010592", "9642014880", "",           "Peugeot 306 2.0 HDi RHY (DW10)"),
    ("0281001976", "9635157580", "1037359058", "Peugeot 306 / Xsara 2.0 HDi 90hp"),
    ("0281010500", "9641606980", "",           "Peugeot 206 2.0 HDi"),
    ("0281010594", "9642013980", "1037364196", "Peugeot 206 2.0 HDi 90hp"),
    ("0281010595", "9642014980", "1037353998", "Citroen Xsara Picasso 2.0 HDi 90hp"),
    ("0281010996", "9646774280", "",           "Citroen Xsara Picasso 2.0 HDi 90hp RHY"),
    ("0281010248", "9635157080", "",           "Peugeot 406 2.0 HDi"),
    ("0281010360", "9641607280", "",           "Peugeot Partner 2.0 HDi"),
    ("0281010361", "9641607680", "",           "Peugeot 406 2.0 HDi"),
    ("0281010366", "9636254980", "",           "Citroen C5 2.0 HDi"),
    ("0281010367", "9636254780", "",           "Citroen C5 / 406 2.0 HDi"),
    ("0281010591", "9643527180", "",           "Peugeot Expert 2.0 HDi"),
    ("0281010627", "9642301880", "",           "Peugeot 406 2.0 HDi"),
    ("0281010775", "9643525380", "",           "Peugeot 406 2.0 HDi"),
    ("0281010934", "9645986780", "",           "Peugeot 2.0 HDi"),
    ("0281011081", "9650221480", "1037364448", "Peugeot 307 2.0 HDi 107hp"),
    ("0281011084", "9647693180", "",           "Citroen Xsara Picasso 2.0 HDi"),
    ("0281011342", "9651175080", "1039F00241", "Peugeot Expert 2.0 HDi"),
    ("0281011521", "9651593480", "",           "Citroen Xsara Picasso 2.0 HDi"),
)

STOCK_NUMBERS: dict[str, str] = {}
for _pn, _hw, _sw, _label in _STOCK_UNITS:
    for _num in (_pn, _hw, _sw):
        if _num:
            STOCK_NUMBERS[re.sub(r"[^0-9A-Z]", "", _num.upper())] = _label

# Substrings that betray a tuner's flash tool or naming in an ID string.
_TUNER_HINTS = ("STAGE", "TUNED", "REMAP", "WINOLS", "KESS", "MPPS",
                "GALLETTO", "KTAG", "TUNE")


def _norm(s: str) -> str:
    return re.sub(r"[^0-9A-Z]", "", s.upper())


def _norm_numbers(fields: list[tuple[str, str]]) -> list[str]:
    """Distinct number-like tokens (>=7 alnum) across all field values."""
    out: list[str] = []
    for _, value in fields:
        for token in re.findall(r"[0-9A-Za-z]{7,}", value):
            if any(c.isdigit() for c in token) and token not in out:
                out.append(token)
    return out


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

    # ---- match known factory numbers anywhere in the returned strings
    # (0x9B concatenates hardware + software, so scan the whole blob).
    blob = _norm(" ".join(v for _, v in report.fields))
    recognised = sorted({lbl for num, lbl in STOCK_NUMBERS.items()
                         if num in blob})

    reflash_evidence = [(k, seen[k]) for k in _REFLASH_FIELDS if k in seen]
    reprogrammed = reflash_evidence and _looks_reprogrammed(reflash_evidence)
    tuner_marks = [(k, v) for k, v in report.fields
                   if any(h in v.upper() for h in _TUNER_HINTS)]

    # ---- verdict, most-confident signal first.
    # Key honesty point: a recognised factory NUMBER does NOT prove the maps
    # are stock — a map-only remap keeps the number. So the only positive
    # "remapped" signals are a tuner string or a reflash fingerprint; a
    # recognised number with no fingerprint is reported as "no evidence",
    # never as "confirmed stock".
    if tuner_marks:
        report.verdict = "reflashed"
        report.headline = "Almost certainly REMAPPED"
        report.reasons.append(
            "An identification string names a tuning tool/stage: "
            + "; ".join(f"{k} = {v}" for k, v in tuner_marks))
    elif reprogrammed:
        report.verdict = "reflashed"
        report.headline = "Shows signs of having been REPROGRAMMED"
        report.reasons.append(
            "The ECU's flash fingerprint (below) indicates it was written "
            "after leaving the factory — often a remap, though a genuine "
            "dealer software update or recall can look identical.")
        report.reasons += [f"{k} = {v}" for k, v in reflash_evidence]
        if recognised:
            report.reasons.append(
                "Note: it still reports a factory part number ("
                + "; ".join(recognised) + ") — normal, because a remap keeps "
                "the original numbers.")
    elif recognised:
        report.verdict = "clean"
        report.headline = "Genuine factory ECU — no sign of a remap (but not proof)"
        report.reasons.append(
            "Identity matches a known factory unit: " + "; ".join(recognised))
        report.reasons.append(
            "No reflash fingerprint was seen. IMPORTANT: this is NOT proof "
            "the maps are stock — a map-only remap keeps these exact numbers "
            "and a bench flash can leave no fingerprint. The only certain "
            "test is reading the flash and comparing to a stock image.")
    else:
        report.verdict = "unknown"
        report.headline = "UNKNOWN — identity not recognised"
        report.reasons.append(
            "The numbers read don't match a factory unit on file. That could "
            "mean a remapped/replacement ECU, or simply a factory number we "
            "don't list. Compare against a stock reference for your exact "
            "engine (a PSA specialist or an HDi forum can confirm).")
        nums = _norm_numbers(report.fields)
        if nums:
            report.reasons.append("Numbers read: " + ", ".join(nums))

    if not report.fields:
        report.headline = "No identification returned by this ECU"
        report.reasons = [
            "This ECU didn't answer the identification requests. Some early "
            "EDC15 units expose little over K-line, or the session needs to "
            "be open first (connect, then run this check)."]
    return report


def _looks_reprogrammed(evidence: list[tuple[str, str]]) -> bool:
    """True if the fingerprint suggests more than a single factory write.

    Conservative: an all-zero / all-FF fingerprint (never programmed in the
    field) reads as no evidence. Any recorded programming attempt beyond the
    first, or a non-empty date/tester code, is treated as a hint.
    """
    for key, val in evidence:
        norm = _norm(val)
        if not norm or set(norm) <= {"0"} or set(norm) <= {"F"}:
            continue  # blank / never-programmed fingerprint
        if key == "Programming counter":
            digits = re.sub(r"\D", "", val)
            if digits and int(digits[-4:] or 0) > 1:   # written more than once
                return True
        elif key == "Flash status (attempts / date / tester)":
            # e.g. "attempts 03 date 21-06-14 tester 5AA": >1 attempt, or a
            # recorded date/tester, means it has been (re)flashed in service
            m = re.search(r"attempts?\D*(\d+)", val, re.I)
            if m and int(m.group(1)) > 1:
                return True
            if re.search(r"\d\d[-/]\d\d[-/]\d\d", val):   # a programming date
                return True
        elif key in ("Tester serial number", "Repair-shop / tester code",
                     "Programming date"):
            return True   # any recorded value here is a field-programming hint
    return False
