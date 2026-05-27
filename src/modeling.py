"""
modeling.py
-----------
Dimensional modeling layer for the F1 Data Pipeline.

Loads cleaned tables from the pipeline's processed directory and builds
a star schema inside a DuckDB database file:

    fact_race_results   — grain: one row per driver per race
    dim_drivers         — driver attributes (SCD Type 1)
    dim_constructors    — team attributes
    dim_circuits        — track attributes
    dim_races           — race calendar metadata
    dim_date            — date dimension generated from race dates

Usage:
    python src/modeling.py
"""

import logging
import sys
from pathlib import Path

import duckdb
import pandas as pd

# ---------------------------------------------------------------------------
# Project root — allows running from any working directory
# ---------------------------------------------------------------------------
PROJECT_ROOT = Path(__file__).resolve().parent.parent

if str(PROJECT_ROOT / "src") not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT / "src"))

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
PROCESSED_DIR = PROJECT_ROOT / "data" / "processed"
DB_PATH = PROJECT_ROOT / "outputs" / "f1_warehouse.duckdb"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _read_clean(name: str) -> pd.DataFrame:
    """Read a cleaned CSV from the processed directory."""
    path = PROCESSED_DIR / f"{name}_clean.csv"
    if not path.exists():
        raise FileNotFoundError(f"Cleaned table not found: {path}")
    return pd.read_csv(path)


# ---------------------------------------------------------------------------
# Dimension builders
# ---------------------------------------------------------------------------

def build_dim_drivers(drivers: pd.DataFrame) -> pd.DataFrame:
    """Build the driver dimension table."""
    cols = [c for c in [
        "driver_id", "driver_ref", "number", "code",
        "forename", "surname", "full_name", "dob", "nationality",
    ] if c in drivers.columns]
    dim = drivers[cols].copy()
    dim = dim.drop_duplicates(subset=["driver_id"]).reset_index(drop=True)
    logger.info(f"dim_drivers: {len(dim)} rows")
    return dim


def build_dim_constructors(constructors: pd.DataFrame) -> pd.DataFrame:
    """Build the constructor dimension table."""
    cols = [c for c in [
        "constructor_id", "constructor_ref", "name", "nationality",
    ] if c in constructors.columns]
    dim = constructors[cols].copy()
    dim = dim.drop_duplicates(subset=["constructor_id"]).reset_index(drop=True)
    logger.info(f"dim_constructors: {len(dim)} rows")
    return dim


def build_dim_circuits(circuits: pd.DataFrame) -> pd.DataFrame:
    """Build the circuit dimension table."""
    cols = [c for c in [
        "circuit_id", "circuit_ref", "name", "location", "country", "lat", "lng", "alt",
    ] if c in circuits.columns]
    dim = circuits[cols].copy()
    dim = dim.drop_duplicates(subset=["circuit_id"]).reset_index(drop=True)
    logger.info(f"dim_circuits: {len(dim)} rows")
    return dim


def build_dim_races(races: pd.DataFrame) -> pd.DataFrame:
    """Build the race dimension table."""
    cols = [c for c in [
        "race_id", "year", "round", "circuit_id", "name", "date", "season_round",
    ] if c in races.columns]
    dim = races[cols].copy()
    dim = dim.drop_duplicates(subset=["race_id"]).reset_index(drop=True)
    logger.info(f"dim_races: {len(dim)} rows")
    return dim


def build_dim_date(races: pd.DataFrame) -> pd.DataFrame:
    """Generate a date dimension from unique race dates."""
    dates = pd.to_datetime(races["date"], errors="coerce").dropna().unique()
    dates = pd.Series(sorted(dates))

    dim = pd.DataFrame({
        "date": dates,
        "year": dates.dt.year,
        "month": dates.dt.month,
        "day": dates.dt.day,
        "day_of_week": dates.dt.day_name(),
        "quarter": dates.dt.quarter,
        "week_of_year": dates.dt.isocalendar().week.values.astype(int),
        "is_weekend": dates.dt.dayofweek.isin([5, 6]).astype(int),
    })
    dim = dim.drop_duplicates(subset=["date"]).reset_index(drop=True)
    logger.info(f"dim_date: {len(dim)} rows")
    return dim


def build_fact_race_results(
    results: pd.DataFrame,
    qualifying: pd.DataFrame,
) -> pd.DataFrame:
    """Build the central fact table for the star schema."""
    fact = results.copy()

    # Attach best qualifying position
    if "position" in qualifying.columns:
        q_pos = qualifying[["race_id", "driver_id", "position"]].rename(
            columns={"position": "qualifying_position"}
        )
        fact = fact.merge(q_pos, on=["race_id", "driver_id"], how="left")

    # Positions gained
    if "grid" in fact.columns and "position_numeric" in fact.columns:
        fact["positions_gained"] = (fact["grid"] - fact["position_numeric"]).round(0)

    # Select fact columns
    keep = [c for c in [
        "result_id", "race_id", "driver_id", "constructor_id",
        "grid", "qualifying_position", "position_numeric", "position_order",
        "points", "laps", "milliseconds", "status_id",
        "finished", "positions_gained",
    ] if c in fact.columns]

    fact = fact[keep].reset_index(drop=True)
    logger.info(f"fact_race_results: {len(fact)} rows")
    return fact


# ---------------------------------------------------------------------------
# DuckDB writer
# ---------------------------------------------------------------------------

def write_star_schema(
    db_path: Path,
    tables: dict[str, pd.DataFrame],
) -> None:
    """Write all dimension and fact tables into a DuckDB database."""
    db_path.parent.mkdir(parents=True, exist_ok=True)

    con = duckdb.connect(str(db_path))
    try:
        for name, df in tables.items():
            con.execute(f"DROP TABLE IF EXISTS {name}")
            con.register("_tmp_df", df)
            con.execute(f"CREATE TABLE {name} AS SELECT * FROM _tmp_df")
            con.unregister("_tmp_df")
            logger.info(f"[DuckDB] {name}: {len(df)} rows written")

        # Verify row counts
        for name in tables:
            count = con.execute(f"SELECT COUNT(*) FROM {name}").fetchone()[0]
            logger.debug(f"[DuckDB] {name} verified: {count} rows")

    finally:
        con.close()

    logger.info(f"Star schema written to {db_path}")


# ---------------------------------------------------------------------------
# Orchestrator
# ---------------------------------------------------------------------------

def build_warehouse(
    processed_dir: Path | None = None,
    db_path: Path | None = None,
) -> dict[str, pd.DataFrame]:
    """
    Build the full star schema from cleaned tables and persist to DuckDB.

    Parameters
    ----------
    processed_dir : Directory containing *_clean.csv files.
    db_path       : Path for the output DuckDB file.

    Returns
    -------
    Dict of all dimension and fact DataFrames.
    """
    processed_dir = processed_dir or PROCESSED_DIR
    db_path = db_path or DB_PATH

    # Load cleaned tables
    results = _read_clean("results")
    drivers = _read_clean("drivers")
    constructors = _read_clean("constructors")
    circuits = _read_clean("circuits")
    races = _read_clean("races")
    qualifying = _read_clean("qualifying")

    # Build dimensions
    star = {
        "dim_drivers": build_dim_drivers(drivers),
        "dim_constructors": build_dim_constructors(constructors),
        "dim_circuits": build_dim_circuits(circuits),
        "dim_races": build_dim_races(races),
        "dim_date": build_dim_date(races),
        "fact_race_results": build_fact_race_results(results, qualifying),
    }

    # Write to DuckDB
    write_star_schema(db_path, star)

    return star


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    logger.info("Building F1 dimensional model (DuckDB star schema)...")
    warehouse = build_warehouse()

    print("\nStar schema summary:")
    for name, df in warehouse.items():
        print(f"  {name:<25} {len(df):>7,} rows x {len(df.columns):>2} cols")
    print(f"\nDatabase: {DB_PATH}")
