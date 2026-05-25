"""
cleaning.py
-----------
Data cleaning stage for the F1 Data Pipeline.
Handles null values, type casting, column standardisation, and deduplication
across all ingested tables. Every function is idempotent and returns a new
DataFrame — originals are never mutated.
"""

import logging
import pandas as pd
import numpy as np
from pathlib import Path

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Generic helpers
# ---------------------------------------------------------------------------

def drop_metadata_cols(df: pd.DataFrame) -> pd.DataFrame:
    """Remove pipeline metadata columns before processing."""
    meta_cols = [c for c in ["_source", "_ingested_at"] if c in df.columns]
    return df.drop(columns=meta_cols)


def standardise_column_names(df: pd.DataFrame) -> pd.DataFrame:
    """
    Convert camelCase column names to snake_case for consistency.
    Example: raceId → race_id, driverId → driver_id.
    """
    import re
    def to_snake(name: str) -> str:
        s1 = re.sub(r"(.)([A-Z][a-z]+)", r"\1_\2", name)
        return re.sub(r"([a-z0-9])([A-Z])", r"\1_\2", s1).lower()

    df = df.copy()
    df.columns = [to_snake(c) for c in df.columns]
    return df


def remove_duplicates(df: pd.DataFrame, subset: list[str] | None = None, label: str = "") -> pd.DataFrame:
    """Drop duplicate rows and log the count removed."""
    before = len(df)
    df = df.drop_duplicates(subset=subset).copy()
    removed = before - len(df)
    if removed:
        logger.warning(f"[{label}] Removed {removed:,} duplicate rows.")
    return df


# ---------------------------------------------------------------------------
# Table-specific cleaning functions
# ---------------------------------------------------------------------------

def clean_results(df: pd.DataFrame) -> pd.DataFrame:
    """
    Clean the race results table.
    - Cast numeric columns
    - Standardise position (DNF/DSQ → NaN in numeric position)
    - Keep positionText for status tracking
    """
    df = drop_metadata_cols(df)
    df = standardise_column_names(df)
    df = remove_duplicates(df, subset=["result_id"], label="results")

    # Numeric position: non-finishing entries have text like 'R', 'D', 'W', 'N', 'F', 'E'
    df["position_numeric"] = pd.to_numeric(df["position"], errors="coerce")

    # Cast columns
    int_cols   = ["result_id","race_id","driver_id","constructor_id","grid",
                   "position_order","laps","status_id"]
    float_cols = ["points","milliseconds","fastest_lap","rank"]

    for col in int_cols:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce").astype("Int64")

    for col in float_cols:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")

    # Derived flag: did the driver finish?
    df["finished"] = df["position_numeric"].notna().astype(int)

    logger.info(f"[results] Cleaned → {len(df):,} rows, {df['finished'].sum():,} finishes.")
    return df


def clean_drivers(df: pd.DataFrame) -> pd.DataFrame:
    """
    Clean the drivers dimension table.
    - Parse dob as date
    - Fill missing permanent numbers
    - Drop redundant URL column
    """
    df = drop_metadata_cols(df)
    df = standardise_column_names(df)
    df = remove_duplicates(df, subset=["driver_id"], label="drivers")

    df["dob"] = pd.to_datetime(df["dob"], errors="coerce")

    # number column has \N for older drivers without permanent numbers
    df["number"] = pd.to_numeric(df["number"], errors="coerce").astype("Int64")

    # Full name convenience column
    df["full_name"] = df["forename"].str.strip() + " " + df["surname"].str.strip()

    df = df.drop(columns=["url"], errors="ignore")

    logger.info(f"[drivers] Cleaned → {len(df):,} drivers.")
    return df


def clean_constructors(df: pd.DataFrame) -> pd.DataFrame:
    """Clean the constructors dimension table."""
    df = drop_metadata_cols(df)
    df = standardise_column_names(df)
    df = remove_duplicates(df, subset=["constructor_id"], label="constructors")
    df = df.drop(columns=["url"], errors="ignore")
    logger.info(f"[constructors] Cleaned → {len(df):,} constructors.")
    return df


def clean_races(df: pd.DataFrame) -> pd.DataFrame:
    """
    Clean the races table.
    - Parse date column
    - Drop session time columns (mostly null in modern era)
    - Add season_round composite key
    """
    df = drop_metadata_cols(df)
    df = standardise_column_names(df)
    df = remove_duplicates(df, subset=["race_id"], label="races")

    df["date"] = pd.to_datetime(df["date"], errors="coerce")

    # Drop session detail columns — too sparse to be useful in the pipeline
    sparse_cols = [c for c in df.columns if any(
        kw in c for kw in ["fp1","fp2","fp3","quali_date","quali_time",
                            "sprint_date","sprint_time","time","url"]
    )]
    df = df.drop(columns=sparse_cols, errors="ignore")

    # Composite key
    df["season_round"] = df["year"].astype(str) + "_R" + df["round"].astype(str).str.zfill(2)

    logger.info(f"[races] Cleaned → {len(df):,} races across {df['year'].nunique()} seasons.")
    return df


def clean_circuits(df: pd.DataFrame) -> pd.DataFrame:
    """Clean circuits dimension."""
    df = drop_metadata_cols(df)
    df = standardise_column_names(df)
    df = remove_duplicates(df, subset=["circuit_id"], label="circuits")
    df["alt"] = pd.to_numeric(df["alt"], errors="coerce").astype("Int64")
    df = df.drop(columns=["url"], errors="ignore")
    logger.info(f"[circuits] Cleaned → {len(df):,} circuits.")
    return df


def clean_driver_standings(df: pd.DataFrame) -> pd.DataFrame:
    """Clean cumulative driver standings (end-of-round snapshots)."""
    df = drop_metadata_cols(df)
    df = standardise_column_names(df)
    df = remove_duplicates(df, subset=["driver_standings_id"], label="driver_standings")

    df["points"]   = pd.to_numeric(df["points"],   errors="coerce")
    df["position"] = pd.to_numeric(df["position"], errors="coerce").astype("Int64")
    df["wins"]     = pd.to_numeric(df["wins"],     errors="coerce").astype("Int64")

    logger.info(f"[driver_standings] Cleaned → {len(df):,} rows.")
    return df


def clean_constructor_standings(df: pd.DataFrame) -> pd.DataFrame:
    """Clean cumulative constructor standings."""
    df = drop_metadata_cols(df)
    df = standardise_column_names(df)
    df = remove_duplicates(df, subset=["constructor_standings_id"], label="constructor_standings")

    df["points"]   = pd.to_numeric(df["points"],   errors="coerce")
    df["position"] = pd.to_numeric(df["position"], errors="coerce").astype("Int64")
    df["wins"]     = pd.to_numeric(df["wins"],     errors="coerce").astype("Int64")

    logger.info(f"[constructor_standings] Cleaned → {len(df):,} rows.")
    return df


def clean_qualifying(df: pd.DataFrame) -> pd.DataFrame:
    """
    Clean qualifying table.
    - Parse lap time strings to milliseconds for q1/q2/q3
    """
    df = drop_metadata_cols(df)
    df = standardise_column_names(df)
    df = remove_duplicates(df, subset=["qualify_id"], label="qualifying")

    def lap_to_ms(series: pd.Series) -> pd.Series:
        """Convert 'm:ss.mmm' lap time strings to total milliseconds."""
        def _parse(val):
            if pd.isna(val) or str(val).strip() == "":
                return np.nan
            try:
                parts = str(val).split(":")
                if len(parts) == 2:
                    minutes = float(parts[0])
                    seconds = float(parts[1])
                    return int((minutes * 60 + seconds) * 1000)
            except Exception:
                return np.nan
            return np.nan
        return series.apply(_parse)

    for col in ["q1","q2","q3"]:
        if col in df.columns:
            df[f"{col}_ms"] = lap_to_ms(df[col])

    df["position"] = pd.to_numeric(df["position"], errors="coerce").astype("Int64")

    logger.info(f"[qualifying] Cleaned → {len(df):,} rows.")
    return df


def clean_pit_stops(df: pd.DataFrame) -> pd.DataFrame:
    """
    Clean pit stop data.
    - Cast duration to float (seconds)
    - Flag outlier stops (> 60 s — likely safety car or mechanical issue)
    """
    df = drop_metadata_cols(df)
    df = standardise_column_names(df)
    df = remove_duplicates(df, subset=["race_id","driver_id","stop"], label="pit_stops")

    df["duration"]     = pd.to_numeric(df["duration"],     errors="coerce")
    df["milliseconds"] = pd.to_numeric(df["milliseconds"], errors="coerce").astype("Int64")

    # Flag abnormally long stops
    df["is_long_stop"] = (df["duration"] > 60).astype(int)

    logger.info(
        f"[pit_stops] Cleaned → {len(df):,} stops. "
        f"{df['is_long_stop'].sum():,} flagged as long (>60 s)."
    )
    return df


def clean_lap_times(df: pd.DataFrame) -> pd.DataFrame:
    """
    Clean lap times.
    - Cast milliseconds
    - Convert time string to ms for consistency
    """
    df = drop_metadata_cols(df)
    df = standardise_column_names(df)

    df["milliseconds"] = pd.to_numeric(df["milliseconds"], errors="coerce").astype("Int64")
    df["position"]     = pd.to_numeric(df["position"],     errors="coerce").astype("Int64")

    logger.info(f"[lap_times] Cleaned → {len(df):,} lap records.")
    return df


def clean_status(df: pd.DataFrame) -> pd.DataFrame:
    """Clean status lookup table."""
    df = drop_metadata_cols(df)
    df = standardise_column_names(df)
    df = remove_duplicates(df, subset=["status_id"], label="status")
    logger.info(f"[status] Cleaned → {len(df):,} status codes.")
    return df


# ---------------------------------------------------------------------------
# Dispatcher
# ---------------------------------------------------------------------------

CLEANERS = {
    "results":               clean_results,
    "drivers":               clean_drivers,
    "constructors":          clean_constructors,
    "races":                 clean_races,
    "circuits":              clean_circuits,
    "driver_standings":      clean_driver_standings,
    "constructor_standings": clean_constructor_standings,
    "qualifying":            clean_qualifying,
    "pit_stops":             clean_pit_stops,
    "lap_times":             clean_lap_times,
    "status":                clean_status,
}


def clean_all_tables(
    tables: dict[str, pd.DataFrame],
) -> dict[str, pd.DataFrame]:
    """
    Apply the appropriate cleaner to every table in the input dict.
    Tables without a dedicated cleaner are passed through with metadata removal
    and column name standardisation only.

    Parameters
    ----------
    tables : Dict of raw DataFrames (output of ingestion stage).

    Returns
    -------
    Dict of cleaned DataFrames.
    """
    cleaned: dict[str, pd.DataFrame] = {}

    for name, df in tables.items():
        try:
            if name in CLEANERS:
                cleaned[name] = CLEANERS[name](df)
            else:
                # Generic fallback
                df = drop_metadata_cols(df)
                df = standardise_column_names(df)
                cleaned[name] = df
                logger.debug(f"[{name}] No dedicated cleaner — applied generic standardisation.")
        except Exception as exc:
            logger.error(f"[{name}] Cleaning failed: {exc}")
            raise

    logger.info(f"Cleaning stage complete — {len(cleaned)} tables processed.")
    return cleaned


def save_cleaned_tables(
    tables: dict[str, pd.DataFrame],
    output_dir: str | Path,
) -> None:
    """Save cleaned DataFrames to the processed directory as CSV."""
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    for name, df in tables.items():
        path = output_dir / f"{name}_clean.csv"
        df.to_csv(path, index=False)
        logger.debug(f"[{name}] Saved cleaned → {path.name}")

    logger.info(f"All cleaned tables saved to {output_dir}")
