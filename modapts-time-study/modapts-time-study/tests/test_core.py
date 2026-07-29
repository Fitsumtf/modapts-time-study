import math

import pytest

from modapts_time_study import (
    SECONDS_PER_MOD, ModaptsError, TaktInput, TimeStudy, analyze_element,
    compare_elements, parse_notation, predicted_standard_time,
    station_loading, takt_time_s,
)


# ---------------- MODAPTS ----------------

def test_basic_notation():
    codes = parse_notation("M4G1 M3P2")
    assert [c.code for c in codes] == ["M4", "G1", "M3", "P2"]
    assert sum(c.total_mods for c in codes) == 10


def test_mod_to_seconds():
    el = analyze_element("x", "M4G1 M3P2")
    assert math.isclose(el.seconds, 10 * SECONDS_PER_MOD)


def test_repeat_groups():
    el = analyze_element("clips", "4(M3G3 M3P5)")
    # one rep = 3+3+3+5 = 14 MOD; x4 = 56
    assert el.mods == 56


def test_compound_and_single_codes():
    el = analyze_element("bend", "B17")
    assert el.mods == 17
    el2 = analyze_element("walk3", "3(W5)")
    assert el2.mods == 15


def test_unknown_code_raises():
    with pytest.raises(ModaptsError):
        parse_notation("M9G1")


def test_garbage_raises():
    with pytest.raises(ModaptsError):
        parse_notation("hello world")


def test_frequency_weighting():
    el = analyze_element("x", "M2G1", frequency=2.0)
    assert math.isclose(el.seconds_per_cycle, el.seconds * 2)


def test_predicted_standard_time_allowance():
    els = [analyze_element("a", "M4G1"), analyze_element("b", "M4P5")]
    out = predicted_standard_time(els, allowance_pct=15.0)
    assert math.isclose(out["standard_time_s"], out["normal_time_s"] * 1.15)


# ---------------- Time study ----------------

def test_timestudy_stats():
    ts = TimeStudy.from_times("x", [10.0, 10.0, 10.0], performance_rating=110)
    assert math.isclose(ts.mean_s, 10.0)
    assert math.isclose(ts.normal_time_s, 11.0)
    assert math.isclose(ts.standard_time_s, 11.0 * 1.15)


def test_timestudy_rejects_nonpositive():
    with pytest.raises(ValueError):
        TimeStudy.from_times("x", [1.0, -2.0])


def test_required_observations_grows_with_variance():
    tight = TimeStudy.from_times("t", [10.0, 10.1, 9.9, 10.0])
    loose = TimeStudy.from_times("l", [8.0, 12.0, 9.0, 11.0])
    assert loose.required_observations() > tight.required_observations()


# ---------------- Takt ----------------

def test_takt():
    # (480-50)*2 shifts = 860 min = 51600 s / 900 units = 57.33 s
    t = takt_time_s(TaktInput(480, 50, 2, 900))
    assert math.isclose(t, 51600 / 900, rel_tol=1e-9)


def test_station_loading_verdicts():
    assert "OVERLOADED" in station_loading(70, 60)["verdict"]
    assert "HEALTHY" in station_loading(48, 60)["verdict"]


# ---------------- Comparison ----------------

def test_compare_pairs_by_name():
    a = [analyze_element("x", "M4G1 M3P2")]  # 10 MOD = 1.29 s
    s = [TimeStudy.from_times("x", [1.30, 1.28, 1.29])]
    comps = compare_elements(s, a)
    assert len(comps) == 1
    assert abs(comps[0].variance_pct) < 5
    assert "OK" in comps[0].flag


def test_compare_missing_name_raises():
    a = [analyze_element("x", "M4G1")]
    s = [TimeStudy.from_times("y", [1.0])]
    with pytest.raises(KeyError):
        compare_elements(s, a)
