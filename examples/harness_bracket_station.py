"""
Worked example: General Assembly station installing a harness bracket
(4 clips + 2 fasteners) on a moving line.

Flow:
  1. MODAPTS analysis per element  -> predicted normal time
  2. Observed stopwatch times      -> observed normal time (with rating)
  3. Takt from demand              -> can the station meet demand?
  4. Element-by-element comparison -> where does reality deviate from method?

Run:  python examples/harness_bracket_station.py
"""

from modapts_time_study import (
    TaktInput, TimeStudy, analyze_element, chart, compare_elements,
    report, takt_time_s,
)

# ----------------------------------------------------------------------
# 1) MODAPTS predicted times (method as designed)
# ----------------------------------------------------------------------
analyses = [
    # Reach to bin, grasp bracket, move to fixture, place with precision
    analyze_element("Get & place bracket", "M4G1 M4P5 E2"),
    # Four clips: reach, complex grasp (small parts), seat with precision
    analyze_element("Install 4 clips", "4(M3G3 M3P5)"),
    # Two fasteners: get, place, apply pressure with driver
    analyze_element("Run 2 fasteners", "2(M3G1 M3P5 A4)"),
    # Visual check + confirm on HMI
    analyze_element("Verify & confirm", "E2 D3 M2G0 M2P2"),
]

# ----------------------------------------------------------------------
# 2) Observed stopwatch data (10 cycles per element, seconds)
#    Operator judged working at 105% pace on clips, 100% elsewhere.
# ----------------------------------------------------------------------
studies = [
    TimeStudy.from_times("Get & place bracket",
                         [1.60, 1.48, 1.55, 1.71, 1.52, 1.66, 1.49, 1.58, 1.62, 1.54]),
    TimeStudy.from_times("Install 4 clips",
                         [7.9, 8.4, 8.1, 8.8, 7.7, 8.3, 8.6, 8.0, 8.2, 8.5],
                         performance_rating=105.0),
    TimeStudy.from_times("Run 2 fasteners",
                         [4.4, 4.1, 4.6, 4.3, 4.2, 4.8, 4.4, 4.5, 4.3, 4.6]),
    TimeStudy.from_times("Verify & confirm",
                         [1.9, 2.1, 2.0, 2.3, 1.8, 2.0, 2.2, 1.9, 2.1, 2.0]),
]

# ----------------------------------------------------------------------
# 3) Takt: 2 shifts x 480 min, 50 min planned downtime each, demand 900/day
# ----------------------------------------------------------------------
takt = takt_time_s(TaktInput(shift_minutes=480, planned_downtime_minutes=50,
                             shifts_per_day=2, demand_per_day=900))

# ----------------------------------------------------------------------
# 4) Compare and report
# ----------------------------------------------------------------------
comparisons = compare_elements(studies, analyses)
print(report(comparisons, takt_s=takt))

print("\nSample-size check (95% confidence, +/-5% precision):")
for ts in studies:
    need = ts.required_observations()
    ok = "OK" if ts.n >= need else f"NEED {need}"
    print(f"  {ts.name:<22} observed {ts.n:>2}, required {need:>2} -> {ok}")

path = chart(comparisons, takt_s=takt, path="harness_bracket_comparison.png")
print(f"\nChart written to {path}")
