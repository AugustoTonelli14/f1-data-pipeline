"""
ingestion.py
------------
Simulates a real-world data ingestion layer for the F1 Data Pipeline.
Loads raw CSV files, applies source metadata tagging, validates schema,
and stores a clean snapshot to data/raw/ ready for the cleaning stage.
"""

import logging
import pandas as pd
from datetime import datetime, timezone
from pathlib import Path

# ---------------------------------------------------------------------------
# Logger setup
# ---------------------------------------------------------------------------
logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Schema definitions — expected columns per source table
# ---------------------------------------------------------------------------
EXPECTED_SCHEMAS: dict[str, list[str]] = {
    "results":               ["resultId","raceId","driverId","constructorId","number","grid",
                               "position","positionText","positionOrder","points","laps",
                               "time","milliseconds","fastestLap","rank","fastestLapTime",
                               "fastestLapSpeed","statusId"],
    "drivers":               ["driverId","driverRef","number","code","forename","surname",
                               "dob","nationality","url"],
    "constructors":          ["constructorId","constructorRef","name","nationality","url"],
    "races":                 ["raceId","year","round","circuitId","name","date","time","url",
                               "fp1_date","fp1_time","fp2_date","fp2_time","fp3_date","fp3_time",
                               "quali_date","quali_time","sprint_date","sprint_time"],
    "circuits":              ["circuitId","circuitRef","name","location","country","lat","lng",
                               "alt","url"],
    "driver_standings":      ["driverStandingsId","raceId","driverId","points","position",
                               "positionText","wins"],
    "constructor_standings": ["constructorStandingsId","raceId","constructorId","points",
                               "position","positionText","wins"],
    "qualifying":            ["qualifyId","raceId","driverId","constructorId","number",
                               "position","q1","q2","q3"],
    "pit_stops":             ["raceId","driverId","stop","lap","time","duration","milliseconds"],
    "lap_times":             ["raceId","driverId","lap","position","time","milliseconds"],
    "status":                ["statusId","status"],
    "constructor_results":   ["constructorResultsId","raceId","constructorId","points","status"],
    "sprint_results":        ["resultId","raceId","driverId","constructorId","number","grid",
                               "position","positionText","positionOrder","points","laps",
                               "time","milliseconds","fastestLap","fastestLapTime","statusId"],
    "seasons":               ["year","url"],
}


# ---------------------------------------------------------------------------
# Core ingestion functions
# ---------------------------------------------------------------------------

def _validate_schema(df: pd.DataFrame, table_name: str) -> None:
    """Raise ValueError if any expected columns are missing from the DataFrame."""
    expected = set(EXPECTED_SCHEMAS.get(table_name, []))
    actual    = set(df.columns)
    missing   = expected - actual
    if missing:
        raise ValueError(
            f"[{table_name}] Schema validation failed. Missing columns: {missing}"
        )
    logger.debug(f"[{table_name}] Schema validation passed ({len(df.columns)} columns).")


def _tag_metadata(df: pd.DataFrame, source_name: str) -> pd.DataFrame:
    """
    Add pipeline metadata columns to simulate a real ingestion layer
    (source system tag + ingestion timestamp).
    """
    df = df.copy()
    df["_source"]           = source_name
    df["_ingested_at"]      = datetime.now(timezone.utc).isoformat()
    return df


def load_raw_table(
    table_name: str,
    raw_dir: str | Path,
    validate: bool = True,
    tag_metadata: bool = True,
) -> pd.DataFrame:
    """
    Load a single CSV table from raw_dir, optionally validate its schema
    and tag it with ingestion metadata.

    Parameters
    ----------
    table_name   : Name of the table (without .csv extension).
    raw_dir      : Path to the directory containing raw CSV files.
    validate     : Whether to run schema validation.
    tag_metadata : Whether to add _source and _ingested_at columns.

    Returns
    -------
    pd.DataFrame with the loaded (and optionally tagged) data.
    """
    path = Path(raw_dir) / f"{table_name}.csv"

    if not path.exists():
        raise FileNotFoundError(f"Raw file not found: {path}")

    # Replace the Ergast-style null sentinel before parsing
    df = pd.read_csv(path, na_values=["\\N", "\\\\N", "NULL", ""])
    logger.info(f"[{table_name}] Loaded {len(df):,} rows × {len(df.columns)} cols from {path.name}")

    if validate:
        _validate_schema(df, table_name)

    if tag_metadata:
        df = _tag_metadata(df, source_name=table_name)

    return df


def ingest_all_tables(
    raw_dir: str | Path,
    validate: bool = True,
    tag_metadata: bool = True,
) -> dict[str, pd.DataFrame]:
    """
    Ingest every table defined in EXPECTED_SCHEMAS and return a dict
    keyed by table name.

    Parameters
    ----------
    raw_dir      : Directory containing raw CSV files.
    validate     : Run schema checks on every table.
    tag_metadata : Add pipeline metadata columns.

    Returns
    -------
    dict[str, pd.DataFrame]
    """
    tables: dict[str, pd.DataFrame] = {}
    errors: list[str]               = []

    for table_name in EXPECTED_SCHEMAS:
        try:
            tables[table_name] = load_raw_table(
                table_name,
                raw_dir=raw_dir,
                validate=validate,
                tag_metadata=tag_metadata,
            )
        except FileNotFoundError as exc:
            logger.warning(str(exc))
            errors.append(str(exc))
        except ValueError as exc:
            logger.error(str(exc))
            errors.append(str(exc))

    if errors:
        logger.warning(f"Ingestion completed with {len(errors)} warning(s)/error(s).")
    else:
        logger.info(f"Ingestion complete — {len(tables)} tables loaded successfully.")

    return tables


def filter_modern_era(
    tables: dict[str, pd.DataFrame],
    start_year: int = 2000,
    end_year:   int = 2024,
) -> dict[str, pd.DataFrame]:
    """
    Filter the `races` table to the modern era and propagate the filter
    to all race-linked tables via raceId.

    Parameters
    ----------
    tables     : Dict of DataFrames returned by ingest_all_tables.
    start_year : First season to include (inclusive).
    end_year   : Last  season to include (inclusive).

    Returns
    -------
    Same dict structure with filtered DataFrames.
    """
    if "races" not in tables:
        raise KeyError("'races' table is required for era filtering.")

    # Filter races
    races_filtered = tables["races"][
        tables["races"]["year"].between(start_year, end_year)
    ].copy()

    valid_race_ids = set(races_filtered["raceId"])
    logger.info(
        f"Era filter [{start_year}–{end_year}]: "
        f"{len(races_filtered):,} races kept (from {len(tables['races']):,})."
    )

    # Tables linked by raceId
    race_linked = {
        "results", "driver_standings", "constructor_standings",
        "qualifying", "pit_stops", "lap_times", "constructor_results",
        "sprint_results",
    }

    filtered: dict[str, pd.DataFrame] = {}
    for name, df in tables.items():
        if name == "races":
            filtered[name] = races_filtered
        elif name in race_linked and "raceId" in df.columns:
            before = len(df)
            filtered[name] = df[df["raceId"].isin(valid_race_ids)].copy()
            logger.debug(
                f"[{name}] Filtered {before - len(filtered[name]):,} rows outside era window."
            )
        else:
            # Dimension tables (drivers, constructors, circuits, etc.) — keep all
            filtered[name] = df.copy()

    return filtered


def save_ingested_tables(
    tables: dict[str, pd.DataFrame],
    output_dir: str | Path,
) -> None:
    """
    Persist ingested (and era-filtered) DataFrames back to disk as CSV.
    Simulates a raw landing zone write-back.

    Parameters
    ----------
    tables     : Dict of DataFrames to persist.
    output_dir : Destination directory.
    """
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    for name, df in tables.items():
        out_path = output_dir / f"{name}.csv"
        df.to_csv(out_path, index=False)
        logger.debug(f"[{name}] Saved {len(df):,} rows → {out_path}")

    logger.info(f"All {len(tables)} tables saved to {output_dir}")
