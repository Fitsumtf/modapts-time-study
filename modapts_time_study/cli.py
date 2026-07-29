"""Command-line interface.

Usage:
    python -m modapts_time_study.cli timer  "Element name" --cycles 10
    python -m modapts_time_study.cli modapts "M4G1 M3P2 B17"
    python -m modapts_time_study.cli takt --shift-min 480 --downtime-min 50 \
        --shifts 2 --demand 400
"""

from __future__ import annotations

import argparse

from .modapts import analyze_element
from .takt import TaktInput, takt_time_s
from .timestudy import TimeStudy


def main() -> None:
    ap = argparse.ArgumentParser(prog="modapts-time-study")
    sub = ap.add_subparsers(dest="cmd", required=True)

    t = sub.add_parser("timer", help="Interactive stopwatch time study")
    t.add_argument("name")
    t.add_argument("--cycles", type=int, default=10)
    t.add_argument("--rating", type=float, default=100.0)
    t.add_argument("--allowance", type=float, default=15.0)

    m = sub.add_parser("modapts", help="Evaluate a MODAPTS notation string")
    m.add_argument("notation")
    m.add_argument("--name", default="element")
    m.add_argument("--frequency", type=float, default=1.0)

    k = sub.add_parser("takt", help="Compute takt time")
    k.add_argument("--shift-min", type=float, required=True)
    k.add_argument("--downtime-min", type=float, default=0.0)
    k.add_argument("--shifts", type=int, default=1)
    k.add_argument("--demand", type=float, required=True)

    args = ap.parse_args()

    if args.cmd == "timer":
        ts = TimeStudy(args.name, performance_rating=args.rating,
                       allowance_pct=args.allowance)
        ts.interactive_timer(cycles=args.cycles)
        for key, val in ts.summary().items():
            print(f"{key:>24}: {val:.3f}" if isinstance(val, float) else f"{key:>24}: {val}")

    elif args.cmd == "modapts":
        el = analyze_element(args.name, args.notation, args.frequency)
        print(f"Element : {el.name}")
        print(f"Notation: {el.notation}")
        for c in el.codes:
            print(f"  {c.code:<4} {c.mods:>3} MOD  {c.description}")
        print(f"Total   : {el.mods} MOD = {el.seconds:.3f} s normal "
              f"(x{el.frequency} per cycle = {el.seconds_per_cycle:.3f} s)")

    elif args.cmd == "takt":
        inp = TaktInput(args.shift_min, args.downtime_min, args.shifts, args.demand)
        print(f"Takt time: {takt_time_s(inp):.2f} s/unit")


if __name__ == "__main__":
    main()
