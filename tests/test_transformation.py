"""
Tests for the transformation module.
Validates helper utilities and mart output structure/metrics.
"""

import sys
from pathlib import Path

import pandas as pd
import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from transformation import _safe_div, _pct, build_driver_performance_mart


# ---------------------------------------------------------------------------
# Tests — Helper utilities
# ---------------------------------------------------------------------------

class TestSafeDiv:
    def test_normal_division(self):
        num = pd.Series([10, 20, 30])
        den = pd.Series([2, 4, 5])
        result = _safe_div(num, den)
        expected = pd.Series([5.0, 5.0, 6.0])
        pd.testing.assert_series_equal(result, expected)

    def test_division_by_zero_returns_nan(self):
        num = pd.Series([10, 20])
        den = pd.Series([0, 5])
        result = _safe_div(num, den)
        assert np.isnan(result.iloc[0])
        assert result.iloc[1] == 4.0

    def test_all_zeros(self):
        num = pd.Series([0, 0])
        den = pd.Series([0, 0])
        result = _safe_div(num, den)
        assert result.isna().all()


class TestPct:
    def test_correct_percentage(self):
        num = pd.Series([1, 3])
        den = pd.Series([4, 4])
        result = _pct(num, den)
        assert result.iloc[0] == 25.0
        assert result.iloc[1] == 75.0

    def test_zero_denominator(self):
        num = pd.Series([5])
        den = pd.Series([0])
        result = _pct(num, den)
        assert result.isna().all()


# ---------------------------------------------------------------------------
# Tests — Driver Performance Mart
# ---------------------------------------------------------------------------

class TestBuildDriverPerformanceMart:
    @pytest.fixture
    def mart_inputs(self):
        """Clean DataFrames for building the driver performance mart.
        6 races so drivers 10/20/30 pass the >=5 races filter."""
        # 6 races × 3 core drivers + 1 extra driver in race 6
        race_ids =   [1,1,1,  2,2,2,  3,3,3,  4,4,4,  5,5,5,  6,6,6,6]
        driver_ids = [10,20,30, 10,20,30, 10,20,30, 10,20,30, 10,20,30, 10,20,30,40]
        results = pd.DataFrame({
            "result_id":        list(range(1, 20)),
            "race_id":          race_ids,
            "driver_id":        driver_ids,
            "constructor_id":   [100,200,300]*6 + [400],
            "grid":             [1,2,3, 2,1,3, 1,3,2, 1,2,3, 2,1,3, 1,3,2,4],
            "position_numeric": [1,2,3, 2,1,np.nan, 1,3,2, 1,2,3, 2,1,3, 1,np.nan,2,np.nan],
            "position_order":   [1,2,3, 2,1,20, 1,3,2, 1,2,3, 2,1,3, 1,20,2,20],
            "points":           [25,18,15, 18,25,0, 25,15,18, 25,18,15, 18,25,15, 25,0,18,0],
            "laps":             [58]*19,
            "status_id":        [1,1,1, 1,1,3, 1,1,1, 1,1,1, 1,1,1, 1,3,1,3],
            "finished":         [1,1,1, 1,1,0, 1,1,1, 1,1,1, 1,1,1, 1,0,1,0],
        })
        races = pd.DataFrame({
            "race_id":  [1, 2, 3, 4, 5, 6],
            "year":     [2023]*6,
            "round":    [1, 2, 3, 4, 5, 6],
        })
        drivers = pd.DataFrame({
            "driver_id": [10, 20, 30, 40],
            "full_name": ["Lewis Hamilton", "Max Verstappen", "Charles Leclerc", "One Race"],
            "code":      ["HAM", "VER", "LEC", "ONE"],
            "nationality": ["British", "Dutch", "Monegasque", "Test"],
            "dob":       ["1985-01-07", "1997-09-30", "1997-10-16", "2000-01-01"],
        })
        qualifying = pd.DataFrame({
            "race_id":   race_ids,
            "driver_id": driver_ids,
            "q1_ms":     [92000]*19,
            "q2_ms":     [91000]*19,
            "q3_ms":     [90000]*19,
        })
        pit_stops = pd.DataFrame({
            "race_id":      [1, 1, 2, 3, 4, 5],
            "driver_id":    [10, 20, 10, 20, 10, 20],
            "stop":         [1, 1, 1, 1, 1, 1],
            "duration":     [22.5, 23.0, 21.0, 22.0, 22.8, 21.5],
            "is_long_stop": [0, 0, 0, 0, 0, 0],
        })
        return {
            "results": results,
            "races": races,
            "drivers": drivers,
            "qualifying": qualifying,
            "pit_stops": pit_stops,
        }

    def test_mart_has_expected_columns(self, mart_inputs):
        mart = build_driver_performance_mart(**mart_inputs)
        expected_cols = [
            "driver_id", "full_name", "races_entered", "wins",
            "podiums", "points_total", "win_rate_pct", "podium_rate_pct",
            "dnf_rate_pct", "points_per_race",
        ]
        for col in expected_cols:
            assert col in mart.columns, f"Missing column: {col}"

    def test_filters_out_low_entry_drivers(self, mart_inputs):
        mart = build_driver_performance_mart(**mart_inputs)
        # Driver 40 only has 1 race entry (< 5 minimum), should be excluded
        assert 40 not in mart["driver_id"].values

    def test_win_count_correct(self, mart_inputs):
        mart = build_driver_performance_mart(**mart_inputs)
        ham = mart[mart["driver_id"] == 10].iloc[0]
        # Driver 10 won races 1, 3, 4, 6 = 4 wins
        assert ham["wins"] == 4

    def test_dnf_counted(self, mart_inputs):
        mart = build_driver_performance_mart(**mart_inputs)
        lec = mart[mart["driver_id"] == 30].iloc[0]
        # Driver 30 has 1 DNF (race 2, position = NaN, finished = 0)
        assert lec["dnf_count"] == 1

    def test_points_total(self, mart_inputs):
        mart = build_driver_performance_mart(**mart_inputs)
        ham = mart[mart["driver_id"] == 10].iloc[0]
        # Driver 10: 25+18+25+25+18+25 = 136
        assert ham["points_total"] == 136

    def test_sorted_by_points_descending(self, mart_inputs):
        mart = build_driver_performance_mart(**mart_inputs)
        points = mart["points_total"].tolist()
        assert points == sorted(points, reverse=True)
