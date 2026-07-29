"""
Compare observed (stopwatch) times against MODAPTS-predicted times,
element by element and for the full cycle, and judge both against takt.

Interpretation guide (rules of thumb used on the floor):
  * |variance| <= 10% : observed and predicted agree; method is being
    followed and the rating is sane.
  * observed >> predicted : look for method deviation, waiting, poor
    layout/reach distances, or an optimistic MODAPTS analysis.
  * observed << predicted : operator may be exceeding normal pace
    (rating problem) or the MODAPTS analysis includes motions that
    were engineered out.
"""

from __future__ import annotations

from dataclasses import dataclass

from .modapts import ElementAnalysis
from .timestudy import TimeStudy


@dataclass
class ElementComparison:
    name: str
    observed_normal_s: float
    predicted_normal_s: float

    @property
    def delta_s(self) -> float:
        return self.observed_normal_s - self.predicted_normal_s

    @property
    def variance_pct(self) -> float:
        if self.predicted_normal_s == 0:
            return float("inf")
        return self.delta_s / self.predicted_normal_s * 100.0

    @property
    def flag(self) -> str:
        v = self.variance_pct
        if abs(v) <= 10.0:
            return "OK (within +/-10%)"
        if v > 10.0:
            return "OBSERVED SLOWER - check method/layout/waiting"
        return "OBSERVED FASTER - check rating or motion content"


def compare_elements(
    studies: list[TimeStudy], analyses: list[ElementAnalysis]
) -> list[ElementComparison]:
    """Pair time studies with MODAPTS analyses by element name."""
    by_name = {a.name: a for a in analyses}
    out: list[ElementComparison] = []
    for ts in studies:
        if ts.name not in by_name:
            raise KeyError(f"No MODAPTS analysis named {ts.name!r}")
        a = by_name[ts.name]
        out.append(
            ElementComparison(
                name=ts.name,
                observed_normal_s=ts.normal_time_s,
                predicted_normal_s=a.seconds_per_cycle,
            )
        )
    return out


def report(
    comparisons: list[ElementComparison],
    takt_s: float | None = None,
    allowance_pct: float = 15.0,
) -> str:
    """Plain-text comparison report."""
    lines = []
    w = max(len(c.name) for c in comparisons) + 2
    lines.append(
        f"{'Element':<{w}}{'Observed(s)':>12}{'MODAPTS(s)':>12}"
        f"{'Delta(s)':>10}{'Var %':>8}  Flag"
    )
    lines.append("-" * (w + 52))
    for c in comparisons:
        lines.append(
            f"{c.name:<{w}}{c.observed_normal_s:>12.2f}"
            f"{c.predicted_normal_s:>12.2f}{c.delta_s:>10.2f}"
            f"{c.variance_pct:>8.1f}  {c.flag}"
        )
    obs = sum(c.observed_normal_s for c in comparisons)
    prd = sum(c.predicted_normal_s for c in comparisons)
    tot_var = (obs - prd) / prd * 100.0 if prd else float("inf")
    lines.append("-" * (w + 52))
    lines.append(
        f"{'TOTAL (normal)':<{w}}{obs:>12.2f}{prd:>12.2f}"
        f"{obs - prd:>10.2f}{tot_var:>8.1f}"
    )
    obs_std = obs * (1 + allowance_pct / 100.0)
    prd_std = prd * (1 + allowance_pct / 100.0)
    lines.append(
        f"{'TOTAL (standard, +' + str(allowance_pct) + '% PF&D)':<{w}}"
        f"{obs_std:>12.2f}{prd_std:>12.2f}"
    )
    if takt_s:
        lines.append("")
        lines.append(f"Takt time: {takt_s:.2f} s")
        for label, val in (("observed", obs_std), ("MODAPTS", prd_std)):
            pct = val / takt_s * 100.0
            state = "MEETS takt" if pct <= 100 else "MISSES takt"
            lines.append(
                f"  Standard cycle vs takt ({label}): {pct:.1f}% loading -> {state}"
            )
    return "\n".join(lines)


def chart(
    comparisons: list[ElementComparison],
    takt_s: float | None = None,
    path: str = "comparison.png",
) -> str:
    """Grouped bar chart: observed vs predicted per element (matplotlib)."""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    names = [c.name for c in comparisons]
    obs = [c.observed_normal_s for c in comparisons]
    prd = [c.predicted_normal_s for c in comparisons]
    x = range(len(names))
    width = 0.38

    fig, ax = plt.subplots(figsize=(9, 4.6))
    ax.bar([i - width / 2 for i in x], obs, width, label="Observed (stopwatch)",
           color="#C0392B")
    ax.bar([i + width / 2 for i in x], prd, width, label="Predicted (MODAPTS)",
           color="#2C3E50")
    if takt_s:
        ax.axhline(takt_s, color="green", linestyle="--", linewidth=1.4,
                   label=f"Takt = {takt_s:.1f}s")
    ax.set_ylabel("Normal time (s)")
    ax.set_title("Observed vs MODAPTS-predicted cycle time by element")
    ax.set_xticks(list(x))
    ax.set_xticklabels(names, rotation=20, ha="right", fontsize=9)
    ax.legend()
    fig.tight_layout()
    fig.savefig(path, dpi=150)
    plt.close(fig)
    return path
