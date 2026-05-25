"""
transformation.py
-----------------
Transformation stage for the F1 Data Pipeline.
Merges clean tables and engineers features into three analytical data marts:

    1. driver_performance_mart   — per-driver career metrics (2000-2024)
    2. team_performance_mart     — per-constructor season metrics
    3. season_trends_mart        — year-over-year competitive landscape

All marts are ready for direct BI / analysis consumption.
"""

import logging
import pandas as pd
import numpy as np
from pathlib import Path

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Helper utilities
# ---------------------------------------------------------------------------

def _safe_div(numerator: pd.Series, denominator: pd.Series) -> pd.Series:
    """Element-wise division that returns NaN instead of inf/ZeroDivisionError."""
    return numerator.where(denominator != 0, other=np.nan) / denominator.replace(0, np.nan)


def _pct(numerator: pd.Series, denominator: pd.Series, decimals: int = 4) -> pd.Series:
    """Return a percentage (0–100) rounded to `decimals` places."""
    return (_safe_div(numerator, denominator) * 100).round(decimals)


# ---------------------------------------------------------------------------
# Mart 1: Driver Performance
# ---------------------------------------------------------------------------

def build_driver_performance_mart(
    results:    pd.DataFrame,
    drivers:    pd.DataFrame,
    races:      pd.DataFrame,
    qualifying: pd.DataFrame,
    pit_stops:  pd.DataFrame,
) -> pd.DataFrame:
    """
    Build the driver performance mart.

    Metrics per driver (career over the filtered era):
    - races_entered, wins, podiums, points_total
    - win_rate_pct, podium_rate_pct, points_per_race
    - dnf_count, dnf_rate_pct
    - avg_grid_position, avg_finish_position
    - avg_qualifying_ms (best Q session available)
    - avg_pit_stop_duration
    - best_season_points (peak single-season WDC points)
    - seasons_active
    """
    logger.info("Building driver_performance_mart…")

    # --- Merge results with race year info ----------------------------------
    race_years = races[["race_id","year"]].copy()
    res = results.merge(race_years, on="race_id", how="left")

    # Core aggregations
    agg = (
        res.groupby("driver_id")
        .agg(
            races_entered    = ("race_id",         "nunique"),
            wins             = ("position_numeric", lambda x: (x == 1).sum()),
            podiums          = ("position_numeric", lambda x: (x <= 3).sum()),
            points_total     = ("points",           "sum"),
            dnf_count        = ("finished",         lambda x: (x == 0).sum()),
            avg_grid         = ("grid",             "mean"),
            avg_finish       = ("position_numeric", "mean"),
            seasons_active   = ("year",             "nunique"),
            first_season     = ("year",             "min"),
            last_season      = ("year",             "max"),
        )
        .reset_index()
    )

    # Derived rates
    agg["win_rate_pct"]    = _pct(agg["wins"],    agg["races_entered"])
    agg["podium_rate_pct"] = _pct(agg["podiums"], agg["races_entered"])
    agg["dnf_rate_pct"]    = _pct(agg["dnf_count"], agg["races_entered"])
    agg["points_per_race"] = (_safe_div(agg["points_total"], agg["races_entered"])).round(3)

    # Best single-season points (for peak-performance context)
    season_pts = (
        res.groupby(["driver_id","year"])["points"]
        .sum()
        .reset_index()
        .groupby("driver_id")["points"]
        .max()
        .rename("best_season_points")
    )
    agg = agg.merge(season_pts, on="driver_id", how="left")

    # --- Qualifying: best time across Q1/Q2/Q3 per session -----------------
    q = qualifying[["race_id","driver_id","q1_ms","q2_ms","q3_ms"]].copy()
    q["best_q_ms"] = q[["q1_ms","q2_ms","q3_ms"]].min(axis=1)
    avg_q = (
        q.groupby("driver_id")["best_q_ms"]
        .mean()
        .round(1)
        .rename("avg_qualifying_ms")
        .reset_index()
    )
    agg = agg.merge(avg_q, on="driver_id", how="left")

    # --- Pit stops: average normal stop duration ----------------------------
    normal_stops = pit_stops[pit_stops["is_long_stop"] == 0]
    avg_pit = (
        normal_stops.groupby("driver_id")["duration"]
        .mean()
        .round(3)
        .rename("avg_pit_stop_s")
        .reset_index()
    )
    agg = agg.merge(avg_pit, on="driver_id", how="left")

    # --- Attach driver metadata ---------------------------------------------
    driver_meta = drivers[["driver_id","full_name","code","nationality","dob"]].copy()
    agg = agg.merge(driver_meta, on="driver_id", how="left")

    # Round float columns
    float_cols = ["avg_grid","avg_finish","best_season_points"]
    for col in float_cols:
        agg[col] = agg[col].round(2)

    # Filter to drivers with at least 5 race entries (remove one-off appearances)
    agg = agg[agg["races_entered"] >= 5].copy()

    # Column order
    col_order = [
        "driver_id","full_name","code","nationality","dob",
        "first_season","last_season","seasons_active",
        "races_entered","wins","podiums","dnf_count",
        "points_total","best_season_points","points_per_race",
        "win_rate_pct","podium_rate_pct","dnf_rate_pct",
        "avg_grid","avg_finish","avg_qualifying_ms","avg_pit_stop_s",
    ]
    col_order = [c for c in col_order if c in agg.columns]
    agg = agg[col_order].sort_values("points_total", ascending=False).reset_index(drop=True)

    logger.info(f"driver_performance_mart → {len(agg):,} drivers.")
    return agg


# ---------------------------------------------------------------------------
# Mart 2: Team (Constructor) Performance
# ---------------------------------------------------------------------------

def build_team_performance_mart(
    results:               pd.DataFrame,
    constructor_standings: pd.DataFrame,
    constructors:          pd.DataFrame,
    races:                 pd.DataFrame,
) -> pd.DataFrame:
    """
    Build the team performance mart — one row per constructor per season.

    Metrics per constructor × season:
    - races, wins, podiums, poles (inferred from grid==1)
    - points_total, final_championship_position
    - win_rate_pct, podium_rate_pct
    - reliability_rate_pct (% of entries that finished)
    - avg_points_per_race
    - drivers_used (count of unique drivers that season)
    """
    logger.info("Building team_performance_mart…")

    race_years = races[["race_id","year"]].copy()
    res = results.merge(race_years, on="race_id", how="left")

    # Aggregate per constructor × season
    agg = (
        res.groupby(["constructor_id","year"])
        .agg(
            races          = ("race_id",         "nunique"),
            wins           = ("position_numeric", lambda x: (x == 1).sum()),
            podiums        = ("position_numeric", lambda x: (x <= 3).sum()),
            poles          = ("grid",             lambda x: (x == 1).sum()),
            points_total   = ("points",           "sum"),
            dnf_count      = ("finished",         lambda x: (x == 0).sum()),
            entries        = ("result_id",        "count"),
            drivers_used   = ("driver_id",        "nunique"),
        )
        .reset_index()
    )

    agg["win_rate_pct"]     = _pct(agg["wins"],    agg["entries"])
    agg["podium_rate_pct"]  = _pct(agg["podiums"], agg["entries"])
    agg["reliability_pct"]  = _pct(agg["entries"] - agg["dnf_count"], agg["entries"])
    agg["points_per_race"]  = (_safe_div(agg["points_total"], agg["races"])).round(3)

    # Final WCC position: take the max-raceId standing row for each constructor-season
    # (last round of the season = final championship position)
    last_race = (
        races.groupby("year")["race_id"]
        .max()
        .reset_index()
        .rename(columns={"race_id": "last_race_id"})
    )
    cs = constructor_standings.merge(
        last_race,
        left_on="race_id", right_on="last_race_id",
        how="inner"
    )[["constructor_id","year","position"]].rename(columns={"position": "wcc_position"})

    agg = agg.merge(cs, on=["constructor_id","year"], how="left")

    # Attach constructor names
    c_meta = constructors[["constructor_id","name","nationality"]].copy()
    agg = agg.merge(c_meta, on="constructor_id", how="left")

    # Round floats
    for col in ["win_rate_pct","podium_rate_pct","reliability_pct","points_per_race"]:
        agg[col] = agg[col].round(2)

    col_order = [
        "constructor_id","name","nationality","year",
        "races","entries","wins","podiums","poles","dnf_count","drivers_used",
        "points_total","points_per_race","wcc_position",
        "win_rate_pct","podium_rate_pct","reliability_pct",
    ]
    col_order = [c for c in col_order if c in agg.columns]
    agg = agg[col_order].sort_values(["year","wcc_position"]).reset_index(drop=True)

    logger.info(f"team_performance_mart → {len(agg):,} constructor-season rows.")
    return agg


# ---------------------------------------------------------------------------
# Mart 3: Season Trends
# ---------------------------------------------------------------------------

def build_season_trends_mart(
    results:         pd.DataFrame,
    driver_standings: pd.DataFrame,
    races:           pd.DataFrame,
    drivers:         pd.DataFrame,
    constructors:    pd.DataFrame,
    constructor_standings: pd.DataFrame,
) -> pd.DataFrame:
    """
    Build the season trends mart — one row per season.

    Metrics:
    - total_races, total_drivers, total_constructors
    - wdc_driver (champion), wdc_points
    - wcc_team (champion), wcc_points
    - avg_grid_size (drivers per race)
    - competitive_balance_index: lower = more dominant, higher = more competitive
      (HHI-style: sum of squared win-share per driver)
    - safety_car_races_pct (approximated via extra-long races — not available directly)
    """
    logger.info("Building season_trends_mart…")

    race_years = races[["race_id","year","round"]].copy()

    # Season-level race counts
    season_races = (
        races.groupby("year")
        .agg(
            total_races        = ("race_id", "nunique"),
            total_drivers      = ("race_id", "nunique"),   # placeholder — overwritten below
        )
        .reset_index()
    )

    # Unique drivers per season (from results)
    res_with_year = results.merge(race_years[["race_id","year"]], on="race_id", how="left")
    drivers_per_season = (
        res_with_year.groupby("year")["driver_id"]
        .nunique()
        .reset_index()
        .rename(columns={"driver_id": "total_drivers"})
    )
    constructors_per_season = (
        res_with_year.groupby("year")["constructor_id"]
        .nunique()
        .reset_index()
        .rename(columns={"constructor_id": "total_constructors"})
    )

    season_agg = (
        season_races[["year","total_races"]]
        .merge(drivers_per_season,     on="year", how="left")
        .merge(constructors_per_season, on="year", how="left")
    )

    # WDC champion — driver with position=1 after last race of season
    last_race_per_season = (
        races.groupby("year")["race_id"].max().reset_index()
        .rename(columns={"race_id": "last_race_id"})
    )

    wdc = (
        driver_standings
        .merge(last_race_per_season, left_on="race_id", right_on="last_race_id", how="inner")
        .query("position == 1")
        [["year","driver_id","points"]]
        .rename(columns={"points": "wdc_points"})
    )
    wdc = wdc.merge(drivers[["driver_id","full_name"]], on="driver_id", how="left")
    wdc = wdc.rename(columns={"full_name": "wdc_driver"})[["year","wdc_driver","wdc_points"]]

    # WCC champion
    wcc = (
        constructor_standings
        .merge(last_race_per_season, left_on="race_id", right_on="last_race_id", how="inner")
        .query("position == 1")
        [["year","constructor_id","points"]]
        .rename(columns={"points": "wcc_points"})
    )
    wcc = wcc.merge(constructors[["constructor_id","name"]], on="constructor_id", how="left")
    wcc = wcc.rename(columns={"name": "wcc_team"})[["year","wcc_team","wcc_points"]]

    # Competitive balance: Herfindahl-Hirschman Index on wins
    # Higher HHI = more dominated by one driver; lower = more competitive
    wins_per_driver_season = (
        res_with_year[res_with_year["position_numeric"] == 1]
        .groupby(["year","driver_id"])
        .size()
        .reset_index(name="wins")
    )
    total_wins_per_season = wins_per_driver_season.groupby("year")["wins"].sum()
    wins_per_driver_season = wins_per_driver_season.merge(
        total_wins_per_season.rename("total_wins"), on="year"
    )
    wins_per_driver_season["win_share"] = (
        wins_per_driver_season["wins"] / wins_per_driver_season["total_wins"]
    )
    hhi = (
        wins_per_driver_season.groupby("year")
        .apply(lambda g: (g["win_share"] ** 2).sum(), include_groups=False)
        .round(4)
        .reset_index(name="dominance_hhi")
    )

    # Avg points gap between P1 and P2 in WDC (margin of victory)
    p1_pts = (
        driver_standings
        .merge(last_race_per_season, left_on="race_id", right_on="last_race_id", how="inner")
        .query("position == 1")[["year","points"]]
        .rename(columns={"points": "p1_pts"})
    )
    p2_pts = (
        driver_standings
        .merge(last_race_per_season, left_on="race_id", right_on="last_race_id", how="inner")
        .query("position == 2")[["year","points"]]
        .rename(columns={"points": "p2_pts"})
    )
    margin = p1_pts.merge(p2_pts, on="year", how="inner")
    margin["wdc_margin_pts"] = (margin["p1_pts"] - margin["p2_pts"]).round(1)
    margin = margin[["year","wdc_margin_pts"]]

    # Merge everything
    trend = (
        season_agg
        .merge(wdc,    on="year", how="left")
        .merge(wcc,    on="year", how="left")
        .merge(hhi,    on="year", how="left")
        .merge(margin, on="year", how="left")
        .sort_values("year")
        .reset_index(drop=True)
    )

    logger.info(f"season_trends_mart → {len(trend):,} seasons.")
    return trend


# ---------------------------------------------------------------------------
# Fact table: fact_race_results (star-schema centre)
# ---------------------------------------------------------------------------

def build_fact_race_results(
    results:      pd.DataFrame,
    races:        pd.DataFrame,
    qualifying:   pd.DataFrame,
) -> pd.DataFrame:
    """
    Build the central fact table linking results, race metadata, and qualifying.
    This forms the star-schema core for any ad-hoc analysis.
    """
    logger.info("Building fact_race_results…")

    race_meta = races[["race_id","year","round","circuit_id","name","date","season_round"]].copy()
    res = results.merge(race_meta, on="race_id", how="left")

    # Attach best qualifying position
    q_pos = qualifying[["race_id","driver_id","position"]].rename(columns={"position": "qualifying_position"})
    res = res.merge(q_pos, on=["race_id","driver_id"], how="left")

    # Positions gained from grid to finish
    res["positions_gained"] = (res["grid"] - res["position_numeric"]).round(0)

    col_order = [
        "result_id","race_id","season_round","year","round","name","date","circuit_id",
        "driver_id","constructor_id",
        "grid","qualifying_position","position_numeric","position_order","position_text",
        "points","laps","milliseconds","fastest_lap_time","fastest_lap_speed",
        "finished","positions_gained","status_id",
    ]
    col_order = [c for c in col_order if c in res.columns]
    fact = res[col_order].reset_index(drop=True)

    logger.info(f"fact_race_results → {len(fact):,} rows.")
    return fact


# ---------------------------------------------------------------------------
# Dispatcher
# ---------------------------------------------------------------------------

def build_all_marts(
    cleaned: dict[str, pd.DataFrame],
) -> dict[str, pd.DataFrame]:
    """
    Orchestrate all transformation steps and return a dict of output DataFrames.

    Parameters
    ----------
    cleaned : Dict of cleaned DataFrames from the cleaning stage.

    Returns
    -------
    Dict with keys:
        'driver_performance_mart'
        'team_performance_mart'
        'season_trends_mart'
        'fact_race_results'
    """
    outputs: dict[str, pd.DataFrame] = {}

    outputs["driver_performance_mart"] = build_driver_performance_mart(
        results    = cleaned["results"],
        drivers    = cleaned["drivers"],
        races      = cleaned["races"],
        qualifying = cleaned["qualifying"],
        pit_stops  = cleaned["pit_stops"],
    )

    outputs["team_performance_mart"] = build_team_performance_mart(
        results               = cleaned["results"],
        constructor_standings = cleaned["constructor_standings"],
        constructors          = cleaned["constructors"],
        races                 = cleaned["races"],
    )

    outputs["season_trends_mart"] = build_season_trends_mart(
        results               = cleaned["results"],
        driver_standings      = cleaned["driver_standings"],
        races                 = cleaned["races"],
        drivers               = cleaned["drivers"],
        constructors          = cleaned["constructors"],
        constructor_standings = cleaned["constructor_standings"],
    )

    outputs["fact_race_results"] = build_fact_race_results(
        results    = cleaned["results"],
        races      = cleaned["races"],
        qualifying = cleaned["qualifying"],
    )

    logger.info(f"Transformation complete — {len(outputs)} marts built.")
    return outputs


def save_marts(
    marts:      dict[str, pd.DataFrame],
    output_dir: str | Path,
    fmt:        str = "csv",
) -> None:
    """
    Save mart DataFrames to output_dir in CSV (default) or Parquet format.

    Parameters
    ----------
    marts      : Dict of DataFrames.
    output_dir : Target directory.
    fmt        : 'csv' or 'parquet'.
    """
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    for name, df in marts.items():
        if fmt == "parquet":
            path = output_dir / f"{name}.parquet"
            df.to_parquet(path, index=False)
        else:
            path = output_dir / f"{name}.csv"
            df.to_csv(path, index=False)
        logger.info(f"[{name}] Saved → {path.name} ({len(df):,} rows)")
