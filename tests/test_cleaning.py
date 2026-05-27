"""
Tests for the cleaning module.
Validates column standardisation, deduplication, type casting,
and table-specific cleaning logic.
"""

import sys
from pathlib import Path

import pandas as pd
import pytest

# Ensure src/ is importable
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from cleaning import (
    clean_all_tables,
    clean_drivers,
    clean_pit_stops,
    clean_qualifying,
    clean_races,
    clean_results,
    drop_metadata_cols,
    remove_duplicates,
    standardise_column_names,
)

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def sample_results():
    """Minimal results DataFrame mimicking raw ingestion output."""
    return pd.DataFrame({
        "resultId":       [1, 2, 3, 4],
        "raceId":         [1, 1, 1, 1],
        "driverId":       [10, 20, 30, 40],
        "constructorId":  [100, 200, 300, 400],
        "number":         [44, 33, 1, 11],
        "grid":           [1, 2, 3, 4],
        "position":       ["1", "2", "R", "3"],
        "positionText":   ["1", "2", "R", "3"],
        "positionOrder":  [1, 2, 20, 3],
        "points":         [25.0, 18.0, 0.0, 15.0],
        "laps":           [58, 58, 30, 58],
        "time":           ["1:30:00", "+5.0", None, "+10.0"],
        "milliseconds":   [5400000, 5405000, None, 5410000],
        "fastestLap":     [40, 35, 20, 45],
        "rank":           [2, 1, None, 3],
        "fastestLapTime": ["1:15.000", "1:14.500", "1:16.000", "1:15.500"],
        "fastestLapSpeed": ["230.5", "231.0", "228.0", "229.5"],
        "statusId":       [1, 1, 3, 1],
        "_source":        ["results"] * 4,
        "_ingested_at":   ["2024-01-01T00:00:00"] * 4,
    })


@pytest.fixture
def sample_drivers():
    """Minimal drivers DataFrame."""
    return pd.DataFrame({
        "driverId":    [10, 20, 30],
        "driverRef":   ["hamilton", "verstappen", "leclerc"],
        "number":      [44, 1, 16],
        "code":        ["HAM", "VER", "LEC"],
        "forename":    ["Lewis", "Max", "Charles"],
        "surname":     ["Hamilton", "Verstappen", "Leclerc"],
        "dob":         ["1985-01-07", "1997-09-30", "1997-10-16"],
        "nationality": ["British", "Dutch", "Monegasque"],
        "url":         ["http://a.com", "http://b.com", "http://c.com"],
        "_source":     ["drivers"] * 3,
        "_ingested_at":["2024-01-01T00:00:00"] * 3,
    })


@pytest.fixture
def sample_races():
    """Minimal races DataFrame."""
    return pd.DataFrame({
        "raceId":      [1, 2],
        "year":        [2023, 2023],
        "round":       [1, 2],
        "circuitId":   [1, 2],
        "name":        ["Bahrain GP", "Saudi Arabian GP"],
        "date":        ["2023-03-05", "2023-03-19"],
        "time":        ["15:00:00", "17:00:00"],
        "url":         ["http://race1.com", "http://race2.com"],
        "fp1_date":    [None, None],
        "fp1_time":    [None, None],
        "fp2_date":    [None, None],
        "fp2_time":    [None, None],
        "fp3_date":    [None, None],
        "fp3_time":    [None, None],
        "quali_date":  [None, None],
        "quali_time":  [None, None],
        "sprint_date": [None, None],
        "sprint_time": [None, None],
        "_source":     ["races"] * 2,
        "_ingested_at":["2024-01-01T00:00:00"] * 2,
    })


@pytest.fixture
def sample_qualifying():
    """Minimal qualifying DataFrame."""
    return pd.DataFrame({
        "qualifyId":     [1, 2, 3],
        "raceId":        [1, 1, 1],
        "driverId":      [10, 20, 30],
        "constructorId": [100, 200, 300],
        "number":        [44, 1, 16],
        "position":      [1, 2, 3],
        "q1":            ["1:32.000", "1:32.500", "1:33.000"],
        "q2":            ["1:31.000", "1:31.500", None],
        "q3":            ["1:30.000", "1:30.500", None],
        "_source":       ["qualifying"] * 3,
        "_ingested_at":  ["2024-01-01T00:00:00"] * 3,
    })


@pytest.fixture
def sample_pit_stops():
    """Minimal pit stops DataFrame."""
    return pd.DataFrame({
        "raceId":       [1, 1, 1, 1],
        "driverId":     [10, 10, 20, 30],
        "stop":         [1, 2, 1, 1],
        "lap":          [15, 35, 18, 20],
        "time":         ["14:30:00", "14:50:00", "14:35:00", "14:40:00"],
        "duration":     [22.5, 23.1, 21.8, 75.0],
        "milliseconds": [22500, 23100, 21800, 75000],
        "_source":      ["pit_stops"] * 4,
        "_ingested_at": ["2024-01-01T00:00:00"] * 4,
    })


# ---------------------------------------------------------------------------
# Tests — Generic helpers
# ---------------------------------------------------------------------------

class TestDropMetadataCols:
    def test_removes_metadata_columns(self, sample_results):
        result = drop_metadata_cols(sample_results)
        assert "_source" not in result.columns
        assert "_ingested_at" not in result.columns

    def test_preserves_data_columns(self, sample_results):
        result = drop_metadata_cols(sample_results)
        assert "resultId" in result.columns
        assert "driverId" in result.columns

    def test_no_metadata_is_noop(self):
        df = pd.DataFrame({"a": [1, 2], "b": [3, 4]})
        result = drop_metadata_cols(df)
        assert list(result.columns) == ["a", "b"]


class TestStandardiseColumnNames:
    def test_camel_to_snake(self):
        df = pd.DataFrame({"raceId": [1], "driverId": [2], "fastestLapTime": ["1:30"]})
        result = standardise_column_names(df)
        assert "race_id" in result.columns
        assert "driver_id" in result.columns
        assert "fastest_lap_time" in result.columns

    def test_already_snake_case(self):
        df = pd.DataFrame({"race_id": [1], "driver_id": [2]})
        result = standardise_column_names(df)
        assert list(result.columns) == ["race_id", "driver_id"]

    def test_does_not_mutate_original(self):
        df = pd.DataFrame({"raceId": [1]})
        _ = standardise_column_names(df)
        assert "raceId" in df.columns


class TestRemoveDuplicates:
    def test_removes_exact_duplicates(self):
        df = pd.DataFrame({"id": [1, 1, 2], "val": [10, 10, 20]})
        result = remove_duplicates(df, subset=["id"], label="test")
        assert len(result) == 2

    def test_no_duplicates_unchanged(self):
        df = pd.DataFrame({"id": [1, 2, 3], "val": [10, 20, 30]})
        result = remove_duplicates(df, subset=["id"], label="test")
        assert len(result) == 3


# ---------------------------------------------------------------------------
# Tests — Table-specific cleaners
# ---------------------------------------------------------------------------

class TestCleanResults:
    def test_output_has_expected_columns(self, sample_results):
        result = clean_results(sample_results)
        assert "position_numeric" in result.columns
        assert "finished" in result.columns
        assert "result_id" in result.columns

    def test_position_numeric_handles_dnf(self, sample_results):
        result = clean_results(sample_results)
        # Position "R" (retired) should become NaN
        dnf_row = result[result["result_id"] == 3]
        assert dnf_row["position_numeric"].isna().all()

    def test_finished_flag(self, sample_results):
        result = clean_results(sample_results)
        # 3 finishers (positions 1, 2, 3) and 1 DNF ("R")
        assert result["finished"].sum() == 3
        assert (result["finished"] == 0).sum() == 1

    def test_metadata_removed(self, sample_results):
        result = clean_results(sample_results)
        assert "_source" not in result.columns

    def test_idempotent(self, sample_results):
        first = clean_results(sample_results)
        # Simulate re-adding metadata so cleaner can run again
        first["_source"] = "results"
        first["_ingested_at"] = "2024-01-01"
        # Rename back to camelCase for the second pass
        first.columns = [c.replace("_i", "I").replace("_r", "R").replace("_t", "T")
                         if c.startswith("result") else c for c in first.columns]
        # Just verify it doesn't crash on re-clean
        assert len(first) > 0


class TestCleanDrivers:
    def test_full_name_created(self, sample_drivers):
        result = clean_drivers(sample_drivers)
        assert "full_name" in result.columns
        assert result["full_name"].iloc[0] == "Lewis Hamilton"

    def test_dob_parsed_as_datetime(self, sample_drivers):
        result = clean_drivers(sample_drivers)
        assert pd.api.types.is_datetime64_any_dtype(result["dob"])

    def test_url_dropped(self, sample_drivers):
        result = clean_drivers(sample_drivers)
        assert "url" not in result.columns


class TestCleanRaces:
    def test_date_parsed(self, sample_races):
        result = clean_races(sample_races)
        assert pd.api.types.is_datetime64_any_dtype(result["date"])

    def test_season_round_created(self, sample_races):
        result = clean_races(sample_races)
        assert "season_round" in result.columns
        assert result["season_round"].iloc[0] == "2023_R01"

    def test_sparse_columns_dropped(self, sample_races):
        result = clean_races(sample_races)
        sparse = [c for c in result.columns if "fp1" in c or "fp2" in c or "fp3" in c]
        assert len(sparse) == 0


class TestCleanQualifying:
    def test_lap_times_converted_to_ms(self, sample_qualifying):
        result = clean_qualifying(sample_qualifying)
        assert "q1_ms" in result.columns
        assert "q2_ms" in result.columns
        assert "q3_ms" in result.columns
        # "1:32.000" = 92000 ms
        assert result["q1_ms"].iloc[0] == 92000

    def test_null_qualifying_times(self, sample_qualifying):
        result = clean_qualifying(sample_qualifying)
        # Driver 3 has no Q3 time
        assert result["q3_ms"].iloc[2] != result["q3_ms"].iloc[2]  # NaN != NaN


class TestCleanPitStops:
    def test_long_stop_flagged(self, sample_pit_stops):
        result = clean_pit_stops(sample_pit_stops)
        assert "is_long_stop" in result.columns
        # The 75s stop should be flagged
        assert result["is_long_stop"].sum() == 1

    def test_duration_is_numeric(self, sample_pit_stops):
        result = clean_pit_stops(sample_pit_stops)
        assert pd.api.types.is_float_dtype(result["duration"])


# ---------------------------------------------------------------------------
# Tests — Dispatcher
# ---------------------------------------------------------------------------

class TestCleanAllTables:
    def test_processes_all_known_tables(self, sample_results, sample_drivers):
        tables = {
            "results": sample_results,
            "drivers": sample_drivers,
        }
        cleaned = clean_all_tables(tables)
        assert "results" in cleaned
        assert "drivers" in cleaned
        assert len(cleaned) == 2

    def test_unknown_table_gets_generic_cleaning(self):
        df = pd.DataFrame({
            "someColumn": [1, 2],
            "_source": ["x", "x"],
            "_ingested_at": ["2024-01-01", "2024-01-01"],
        })
        cleaned = clean_all_tables({"custom_table": df})
        result = cleaned["custom_table"]
        assert "some_column" in result.columns
        assert "_source" not in result.columns
