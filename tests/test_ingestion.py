"""
Tests for the ingestion module.
Validates schema checking, metadata tagging, and era filtering logic.
"""

import sys
from pathlib import Path

import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from ingestion import EXPECTED_SCHEMAS, _tag_metadata, _validate_schema, filter_modern_era

# ---------------------------------------------------------------------------
# Tests — Schema validation
# ---------------------------------------------------------------------------

class TestValidateSchema:
    def test_valid_schema_passes(self):
        df = pd.DataFrame({col: [1] for col in EXPECTED_SCHEMAS["status"]})
        # Should not raise
        _validate_schema(df, "status")

    def test_missing_column_raises(self):
        df = pd.DataFrame({"statusId": [1]})  # missing "status" column
        with pytest.raises(ValueError, match="Schema validation failed"):
            _validate_schema(df, "status")

    def test_extra_columns_still_pass(self):
        cols = {col: [1] for col in EXPECTED_SCHEMAS["status"]}
        cols["extra_column"] = [99]
        df = pd.DataFrame(cols)
        # Extra columns should be fine
        _validate_schema(df, "status")

    def test_unknown_table_passes(self):
        df = pd.DataFrame({"any_col": [1]})
        # Unknown table has no expected schema, so nothing to validate
        _validate_schema(df, "unknown_table_xyz")


# ---------------------------------------------------------------------------
# Tests — Metadata tagging
# ---------------------------------------------------------------------------

class TestTagMetadata:
    def test_adds_source_column(self):
        df = pd.DataFrame({"a": [1, 2]})
        result = _tag_metadata(df, source_name="test_source")
        assert "_source" in result.columns
        assert (result["_source"] == "test_source").all()

    def test_adds_ingested_at_column(self):
        df = pd.DataFrame({"a": [1, 2]})
        result = _tag_metadata(df, source_name="test")
        assert "_ingested_at" in result.columns
        assert result["_ingested_at"].notna().all()

    def test_does_not_mutate_original(self):
        df = pd.DataFrame({"a": [1, 2]})
        _ = _tag_metadata(df, source_name="test")
        assert "_source" not in df.columns


# ---------------------------------------------------------------------------
# Tests — Era filtering
# ---------------------------------------------------------------------------

class TestFilterModernEra:
    @pytest.fixture
    def era_tables(self):
        """Tables spanning 1990–2025 for era filter testing."""
        races = pd.DataFrame({
            "raceId": [1, 2, 3, 4, 5],
            "year":   [1995, 2000, 2010, 2020, 2025],
            "round":  [1, 1, 1, 1, 1],
        })
        results = pd.DataFrame({
            "raceId":   [1, 2, 3, 4, 5],
            "driverId": [10, 20, 30, 40, 50],
        })
        drivers = pd.DataFrame({
            "driverId": [10, 20, 30, 40, 50],
            "name":     ["A", "B", "C", "D", "E"],
        })
        return {"races": races, "results": results, "drivers": drivers}

    def test_filters_races_to_era(self, era_tables):
        filtered = filter_modern_era(era_tables, start_year=2000, end_year=2024)
        years = filtered["races"]["year"].tolist()
        assert 1995 not in years
        assert 2025 not in years
        assert 2000 in years
        assert 2010 in years
        assert 2020 in years

    def test_propagates_filter_to_results(self, era_tables):
        filtered = filter_modern_era(era_tables, start_year=2000, end_year=2024)
        # Only raceIds 2, 3, 4 should remain in results
        assert len(filtered["results"]) == 3

    def test_dimension_tables_unfiltered(self, era_tables):
        filtered = filter_modern_era(era_tables, start_year=2000, end_year=2024)
        # drivers (dimension) should keep all rows
        assert len(filtered["drivers"]) == 5

    def test_missing_races_raises(self):
        tables = {"results": pd.DataFrame({"raceId": [1]})}
        with pytest.raises(KeyError, match="races"):
            filter_modern_era(tables, start_year=2000, end_year=2024)
