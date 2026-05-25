"""
pipeline.py
-----------
Main orchestrator for the F1 Data Engineering Pipeline.

Run this file directly to execute the full pipeline end-to-end:

    python src/pipeline.py

The pipeline executes the following stages in order:
    1. Ingestion   — load raw CSVs, validate schema, filter to modern era
    2. Cleaning    — handle nulls, fix types, standardise columns
    3. Transformation — engineer features and build analytical marts
    4. Export      — save marts as CSV (and optionally Parquet)

Configuration is controlled via the CONFIG dict below.
"""

import logging
import sys
import time
from pathlib import Path
from datetime import datetime, timezone

# ---------------------------------------------------------------------------
# Project root — allows running from any working directory
# ---------------------------------------------------------------------------
PROJECT_ROOT = Path(__file__).resolve().parent.parent

if str(PROJECT_ROOT / "src") not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT / "src"))

from ingestion      import ingest_all_tables, filter_modern_era, save_ingested_tables
from cleaning       import clean_all_tables,  save_cleaned_tables
from transformation import build_all_marts,   save_marts

# ---------------------------------------------------------------------------
# Pipeline configuration
# ---------------------------------------------------------------------------
CONFIG = {
    "raw_dir":        PROJECT_ROOT / "data" / "raw",
    "processed_dir":  PROJECT_ROOT / "data" / "processed",
    "output_dir":     PROJECT_ROOT / "outputs",
    "log_dir":        PROJECT_ROOT / "logs",
    "start_year":     2000,
    "end_year":       2024,
    "output_format":  "csv",       # "csv" or "parquet"
    "validate_schema": True,
}


# ---------------------------------------------------------------------------
# Logging setup
# ---------------------------------------------------------------------------

def setup_logging(log_dir: Path) -> logging.Logger:
    """Configure root logger to write to both console and a dated log file."""
    log_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    log_file  = log_dir / f"pipeline_{timestamp}.log"

    fmt = logging.Formatter(
        fmt="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    # File handler
    fh = logging.FileHandler(log_file, encoding="utf-8")
    fh.setLevel(logging.DEBUG)
    fh.setFormatter(fmt)

    # Console handler
    ch = logging.StreamHandler(sys.stdout)
    ch.setLevel(logging.INFO)
    ch.setFormatter(fmt)

    root_logger = logging.getLogger()
    root_logger.setLevel(logging.DEBUG)
    root_logger.addHandler(fh)
    root_logger.addHandler(ch)

    return logging.getLogger("pipeline"), log_file


# ---------------------------------------------------------------------------
# Stage wrappers with timing and error handling
# ---------------------------------------------------------------------------

def run_stage(stage_name: str, stage_fn, logger: logging.Logger, *args, **kwargs):
    """
    Execute a pipeline stage function with timing, structured logging,
    and error handling. Raises on failure so the pipeline halts cleanly.
    """
    logger.info(f"{'='*60}")
    logger.info(f"STAGE START: {stage_name}")
    logger.info(f"{'='*60}")
    t0 = time.perf_counter()
    try:
        result = stage_fn(*args, **kwargs)
        elapsed = time.perf_counter() - t0
        logger.info(f"STAGE DONE:  {stage_name} completed in {elapsed:.2f}s")
        return result
    except Exception as exc:
        elapsed = time.perf_counter() - t0
        logger.error(f"STAGE FAILED: {stage_name} after {elapsed:.2f}s — {type(exc).__name__}: {exc}")
        raise


# ---------------------------------------------------------------------------
# Pipeline stages
# ---------------------------------------------------------------------------

def stage_ingest(cfg: dict, logger: logging.Logger) -> dict:
    """Stage 1: Ingest raw tables, validate, filter to modern era."""
    # Load all tables from raw CSVs
    tables = ingest_all_tables(
        raw_dir=cfg["raw_dir"],
        validate=cfg["validate_schema"],
        tag_metadata=True,
    )

    # Restrict to configured year range
    tables = filter_modern_era(tables, cfg["start_year"], cfg["end_year"])

    # Persist raw-era snapshot (for reproducibility / audit trail)
    save_ingested_tables(tables, cfg["raw_dir"] / "era_snapshot")

    return tables


def stage_clean(tables: dict, cfg: dict, logger: logging.Logger) -> dict:
    """Stage 2: Clean all tables."""
    cleaned = clean_all_tables(tables)
    save_cleaned_tables(cleaned, cfg["processed_dir"])
    return cleaned


def stage_transform(cleaned: dict, cfg: dict, logger: logging.Logger) -> dict:
    """Stage 3: Build analytical marts."""
    marts = build_all_marts(cleaned)
    save_marts(marts, cfg["output_dir"], fmt=cfg["output_format"])
    return marts


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------

def run_pipeline(cfg: dict | None = None) -> dict:
    """
    Execute the full F1 data pipeline.

    Parameters
    ----------
    cfg : Optional config dict. If None, uses the module-level CONFIG.

    Returns
    -------
    Dict of final mart DataFrames.
    """
    if cfg is None:
        cfg = CONFIG

    logger, log_file = setup_logging(cfg["log_dir"])

    logger.info("╔══════════════════════════════════════════════════════════╗")
    logger.info("║         F1 DATA ENGINEERING PIPELINE — START            ║")
    logger.info("╚══════════════════════════════════════════════════════════╝")
    logger.info(f"Era scope  : {cfg['start_year']} – {cfg['end_year']}")
    logger.info(f"Output fmt : {cfg['output_format'].upper()}")
    logger.info(f"Log file   : {log_file}")

    pipeline_start = time.perf_counter()

    # --- Stage 1: Ingestion -------------------------------------------------
    tables = run_stage("INGESTION", stage_ingest, logger, cfg, logger)

    # --- Stage 2: Cleaning --------------------------------------------------
    cleaned = run_stage("CLEANING", stage_clean, logger, tables, cfg, logger)

    # --- Stage 3: Transformation --------------------------------------------
    marts = run_stage("TRANSFORMATION", stage_transform, logger, cleaned, cfg, logger)

    # --- Summary ------------------------------------------------------------
    total_elapsed = time.perf_counter() - pipeline_start
    logger.info("╔══════════════════════════════════════════════════════════╗")
    logger.info("║         F1 DATA ENGINEERING PIPELINE — COMPLETE         ║")
    logger.info("╚══════════════════════════════════════════════════════════╝")
    logger.info(f"Total runtime : {total_elapsed:.2f}s")
    logger.info(f"Outputs saved : {cfg['output_dir']}")
    logger.info("Marts produced:")
    for name, df in marts.items():
        logger.info(f"  └─ {name:<35} {len(df):>7,} rows")

    return marts


if __name__ == "__main__":
    run_pipeline()
