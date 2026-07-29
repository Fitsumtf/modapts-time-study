"""
Stopwatch time study: capture observed cycle times, then convert
observed -> normal -> standard time.

    normal   = observed_mean * (performance_rating / 100)
    standard = normal * (1 + allowance_pct / 100)

Two capture modes:
  * interactive_timer(): press Enter at each cycle completion (lap timer).
  * from_times(): supply a list of observed times (e.g., from CSV/video).
"""

from __future__ import annotations

import statistics
import time
from dataclasses import dataclass, field


@dataclass
class TimeStudy:
    """Observed time study for one work element or one full cycle."""

    name: str
    observed_s: list[float] = field(default_factory=list)
    performance_rating: float = 100.0  # % pace vs normal operator
    allowance_pct: float = 15.0        # PF&D allowance

    # ---------- capture ----------

    @classmethod
    def from_times(
        cls,
        name: str,
        times_s: list[float],
        performance_rating: float = 100.0,
        allowance_pct: float = 15.0,
    ) -> "TimeStudy":
        ts = cls(name, list(times_s), performance_rating, allowance_pct)
        ts._validate()
        return ts

    def interactive_timer(self, cycles: int = 10) -> None:
        """
        Lap-timer capture. Press Enter to start, then Enter at the end of
        each cycle. Type 'q' + Enter to stop early.
        """
        print(f"\n=== Time study: {self.name} ===")
        print(f"Capturing up to {cycles} cycles. Enter = lap, q = quit.\n")
        input("Press Enter to START the first cycle... ")
        last = time.perf_counter()
        for i in range(1, cycles + 1):
            raw = input(f"Cycle {i}: press Enter at cycle end... ")
            now = time.perf_counter()
            if raw.strip().lower() == "q":
                print("Stopped early.")
                break
            lap = now - last
            last = now
            self.observed_s.append(lap)
            print(f"   -> {lap:6.2f} s")
        self._validate()

    # ---------- statistics ----------

    def _validate(self) -> None:
        if any(t <= 0 for t in self.observed_s):
            raise ValueError("Observed times must be positive.")

    @property
    def n(self) -> int:
        return len(self.observed_s)

    @property
    def mean_s(self) -> float:
        return statistics.fmean(self.observed_s)

    @property
    def stdev_s(self) -> float:
        return statistics.stdev(self.observed_s) if self.n > 1 else 0.0

    @property
    def cv_pct(self) -> float:
        """Coefficient of variation (%): stability of the observed process."""
        return (self.stdev_s / self.mean_s * 100.0) if self.mean_s else 0.0

    @property
    def normal_time_s(self) -> float:
        return self.mean_s * (self.performance_rating / 100.0)

    @property
    def standard_time_s(self) -> float:
        return self.normal_time_s * (1.0 + self.allowance_pct / 100.0)

    def required_observations(
        self, confidence_z: float = 1.96, precision_pct: float = 5.0
    ) -> int:
        """
        Sample-size check: cycles needed so the mean is within
        +/- precision_pct at the given confidence (default 95%, +/-5%).
        n = (z * s / (k * x_bar))^2
        """
        if self.n < 2 or self.mean_s == 0:
            return max(self.n, 2)
        k = precision_pct / 100.0
        n_req = (confidence_z * self.stdev_s / (k * self.mean_s)) ** 2
        return max(int(n_req + 0.9999), 2)

    def summary(self) -> dict:
        return {
            "name": self.name,
            "cycles_observed": self.n,
            "mean_s": self.mean_s,
            "stdev_s": self.stdev_s,
            "cv_pct": self.cv_pct,
            "performance_rating": self.performance_rating,
            "normal_time_s": self.normal_time_s,
            "allowance_pct": self.allowance_pct,
            "standard_time_s": self.standard_time_s,
            "cycles_required_95_5": self.required_observations(),
        }
