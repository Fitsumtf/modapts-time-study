"""
MODAPTS (Modular Arrangement of Predetermined Time Standards) engine.

MODAPTS expresses every manual work element as a sequence of activity codes.
Each code carries an integer number of MODs, where:

    1 MOD = 0.129 seconds  (at 100% pace / normal effort)

A movement code (M1..M5) is typically paired with a terminal code:
a GET (G0/G1/G3) when acquiring an object, or a PUT (P0/P2/P5) when
placing it. Example:  M4G1 M3P2  ->  (4+1) + (3+2) = 10 MODs = 1.29 s.

The class values used here are the published standard MODAPTS values.
MODAPTS is a trademark of the International MODAPTS Association; formal
certification is recommended for production rate-setting.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

#: Seconds per MOD at normal pace.
SECONDS_PER_MOD: float = 0.129

#: Standard MODAPTS activity classes (code -> (MOD value, description)).
MODAPTS_CODES: dict[str, tuple[int, str]] = {
    # --- Movement classes (body part doing the move) ---
    "M1": (1, "Finger movement"),
    "M2": (2, "Hand movement (wrist)"),
    "M3": (3, "Forearm movement (elbow)"),
    "M4": (4, "Whole-arm movement (shoulder)"),
    "M5": (5, "Extended arm movement (trunk assists)"),
    # --- Terminal activities: GET ---
    "G0": (0, "Touch / contact grasp (no closing of fingers)"),
    "G1": (1, "Simple grasp (close fingers on easy object)"),
    "G3": (3, "Complex grasp (small, slippery, or jumbled object)"),
    # --- Terminal activities: PUT ---
    "P0": (0, "Put with no control (toss aside / drop)"),
    "P2": (2, "Put with some control (approximate location)"),
    "P5": (5, "Put with high control (precise fit / alignment)"),
    # --- Auxiliary / whole-body activities ---
    "L1": (1, "Load factor (add per ~4 kg handled, per move)"),
    "E2": (2, "Eye use (travel or focus)"),
    "R2": (2, "Regrasp / rethink minor"),
    "D3": (3, "Decide (simple decision between alternatives)"),
    "A4": (4, "Apply pressure"),
    "C4": (4, "Crank (one revolution)"),
    "F3": (3, "Foot action"),
    "W5": (5, "Walk (per pace)"),
    "B17": (17, "Bend and arise"),
    "S30": (30, "Sit and stand"),
    "J2": (2, "Juggle / adjust in hand"),
}

_TOKEN_RE = re.compile(r"([A-Z])(\d+)")
_REPEAT_RE = re.compile(r"(\d+)\(([^()]*)\)")


class ModaptsError(ValueError):
    """Raised when a MODAPTS code string cannot be parsed."""


@dataclass
class ParsedCode:
    """A single resolved MODAPTS code occurrence."""
    code: str
    mods: int
    description: str
    repeat: int = 1

    @property
    def total_mods(self) -> int:
        return self.mods * self.repeat


@dataclass
class ElementAnalysis:
    """MODAPTS analysis result for one work element."""
    name: str
    notation: str
    codes: list[ParsedCode] = field(default_factory=list)
    frequency: float = 1.0  # occurrences per cycle

    @property
    def mods(self) -> int:
        return sum(c.total_mods for c in self.codes)

    @property
    def seconds(self) -> float:
        """Normal time for one occurrence, in seconds."""
        return self.mods * SECONDS_PER_MOD

    @property
    def seconds_per_cycle(self) -> float:
        """Normal time contribution per cycle (frequency-weighted)."""
        return self.seconds * self.frequency


def _expand_repeats(notation: str) -> list[str]:
    """Split a notation string into chunks, expanding N(...) repeats.

    Repeat groups may contain spaces, e.g. "4(M3G3 M3P5)". Groups are
    expanded in place before whitespace splitting, so the group's content
    is repeated N times as ordinary tokens.
    """
    def _sub(m: re.Match) -> str:
        n = int(m.group(1))
        inner = m.group(2).strip()
        return " " + " ".join([inner] * n) + " "

    expanded = _REPEAT_RE.sub(_sub, notation.replace(",", " "))
    if "(" in expanded or ")" in expanded:
        raise ModaptsError(
            f"Unbalanced or nested parentheses in {notation!r} "
            "(nested repeat groups are not supported)."
        )
    return expanded.split()


def parse_notation(notation: str) -> list[ParsedCode]:
    """
    Parse a MODAPTS notation string into resolved codes.

    Accepts compound tokens ("M4G1"), single codes ("B17"),
    and repeat groups ("3(M3G1M3P2)"). Whitespace/comma separated.
    """
    if not notation or not notation.strip():
        raise ModaptsError("Empty MODAPTS notation.")
    parsed: list[ParsedCode] = []
    for chunk in _expand_repeats(notation.upper()):
        pos = 0
        for m in _TOKEN_RE.finditer(chunk):
            if m.start() != pos:
                raise ModaptsError(
                    f"Unrecognized text {chunk[pos:m.start()]!r} in {chunk!r}"
                )
            code = f"{m.group(1)}{m.group(2)}"
            if code not in MODAPTS_CODES:
                raise ModaptsError(
                    f"Unknown MODAPTS code {code!r} in {chunk!r}. "
                    f"Known codes: {', '.join(sorted(MODAPTS_CODES))}"
                )
            value, desc = MODAPTS_CODES[code]
            parsed.append(ParsedCode(code=code, mods=value, description=desc))
            pos = m.end()
        if pos != len(chunk):
            raise ModaptsError(f"Unrecognized trailing text in {chunk!r}")
    return parsed


def analyze_element(
    name: str, notation: str, frequency: float = 1.0
) -> ElementAnalysis:
    """Analyze one work element from its MODAPTS notation."""
    return ElementAnalysis(
        name=name,
        notation=notation,
        codes=parse_notation(notation),
        frequency=frequency,
    )


def predicted_standard_time(
    elements: list[ElementAnalysis], allowance_pct: float = 15.0
) -> dict:
    """
    Roll elements up to a predicted standard time per cycle.

    standard = normal * (1 + allowance_pct/100)
    where allowance covers personal, fatigue, and delay (PF&D).
    """
    normal = sum(e.seconds_per_cycle for e in elements)
    standard = normal * (1.0 + allowance_pct / 100.0)
    return {
        "elements": elements,
        "total_mods": sum(e.mods * e.frequency for e in elements),
        "normal_time_s": normal,
        "allowance_pct": allowance_pct,
        "standard_time_s": standard,
    }
