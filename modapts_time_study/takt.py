"""
Takt time and line-loading calculations.

    takt = available production time / customer demand

Cycle time is what the process does; takt is what the customer needs.
A station is healthy when standard cycle time <= ~85-90% of takt
(planned utilization leaves room for variation and minor stops).
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class TaktInput:
    shift_minutes: float            # gross shift length, minutes
    planned_downtime_minutes: float  # breaks, meetings, planned maintenance
    shifts_per_day: int
    demand_per_day: float           # units the customer needs per day


def takt_time_s(inp: TaktInput) -> float:
    available_min = (inp.shift_minutes - inp.planned_downtime_minutes) * inp.shifts_per_day
    if inp.demand_per_day <= 0:
        raise ValueError("Demand must be positive.")
    return available_min * 60.0 / inp.demand_per_day


def station_loading(cycle_time_s: float, takt_s: float) -> dict:
    """Loading (%) of a station against takt, with a simple verdict."""
    if takt_s <= 0:
        raise ValueError("Takt must be positive.")
    loading_pct = cycle_time_s / takt_s * 100.0
    if loading_pct > 100.0:
        verdict = "OVERLOADED - cannot meet demand; rebalance or improve"
    elif loading_pct > 90.0:
        verdict = "AT RISK - no buffer for variation; watch closely"
    elif loading_pct >= 60.0:
        verdict = "HEALTHY - meets demand with margin"
    else:
        verdict = "UNDERLOADED - candidate to absorb more work content"
    return {"loading_pct": loading_pct, "verdict": verdict}


def operators_required(total_work_content_s: float, takt_s: float) -> dict:
    """Theoretical minimum operators = total work content / takt."""
    theoretical = total_work_content_s / takt_s
    import math
    return {"theoretical": theoretical, "practical_min": math.ceil(theoretical)}
