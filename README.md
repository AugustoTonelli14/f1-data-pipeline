# 🏎️ Formula 1 Performance Analysis
### End-to-End Data Engineering + Analysis · Modern Era 2000–2024

> A production-style data engineering and analysis project — 14 raw source tables, a modular Python pipeline, four analytical marts, and a storytelling-driven Jupyter Notebook with 7 charts and 7 data-driven insights.

[![Python](https://img.shields.io/badge/Python-3.12-3776AB?style=flat-square&logo=python&logoColor=white)](https://python.org)
[![pandas](https://img.shields.io/badge/pandas-2.0+-150458?style=flat-square&logo=pandas&logoColor=white)](https://pandas.pydata.org)
[![Jupyter](https://img.shields.io/badge/Jupyter-Notebook-F37626?style=flat-square&logo=jupyter&logoColor=white)](https://jupyter.org)
[![License](https://img.shields.io/badge/License-MIT-green?style=flat-square)](LICENSE)

---

## Overview

This project transforms raw Formula 1 historical data into structured, analysis-ready datasets and uses them to answer seven concrete analytical questions about driver performance, team dominance, championship competitiveness, and engineering reliability across 25 seasons (2000–2024).

It is built as a **complete data engineering workflow** — not a single notebook — with modular source code, schema validation, structured logging, and four cleaned analytical marts as output. The analysis layer is a storytelling-driven Jupyter Notebook with hypothesis-driven sections and business-level conclusions.

---

## Business & Analytical Objective

Raw sports data is abundant. Analytical value is not. This project answers questions that go beyond *"who won the most races?"*:

| Question | Approach |
|---|---|
| Who are the greatest drivers of the modern era? | Career-level aggregated performance metrics |
| What separates elite drivers from very good ones? | Win rate vs podium rate multidimensional analysis |
| Was F1 competition as fierce as it felt? | Herfindahl-Hirschman Index (HHI) applied to win share |
| Which constructors dominated, and when did power shift? | Season-by-season time-series analysis |
| Does finishing races matter as much as going fast? | DNF rate vs points-per-race trade-off analysis |
| How close were the real title fights? | Margin-of-victory decomposition across 25 seasons |
| Which teams built the most reliable cars? | Cross-season reliability heatmap (2015–2024) |

---

## Dataset

**Source:** [Ergast Motor Racing API](http://ergast.com/mrd/) — flat-file historical export.

| Table | Rows | Role |
|---|---|---|
| `results` | 26,759 | Core race outcomes |
| `lap_times` | 589,081 | Per-lap performance |
| `driver_standings` | 34,863 | Cumulative WDC standings |
| `constructor_standings` | 13,391 | Cumulative WCC standings |
| `pit_stops` | 11,371 | Stop timing and duration |
| `qualifying` | 10,494 | Q1/Q2/Q3 lap times |
| `races` | 1,125 | Race metadata |
| `drivers` | 861 | Driver profiles |
| `constructors` | 212 | Team profiles |
| `circuits` | 77 | Track metadata |

**Key data quality challenges handled by the pipeline:** non-standard null encoding (`\N`), mixed-type position column (integers + status codes), lap time strings requiring millisecond parsing, calendar size drift (16 → 24 races/season).

---

## Methodology

```
14 raw CSV files
      │
      ▼
  INGESTION          Schema validation · null replacement · era filter (2000–2024)
      │
      ▼
  CLEANING           Type casting · column standardisation · deduplication
      │
      ▼
  TRANSFORMATION     Feature engineering · HHI computation · mart construction
      │
      ▼
  4 ANALYTICAL MARTS
  ├── driver_performance_mart    117 rows × 22 cols
  ├── team_performance_mart      266 rows × 17 cols
  ├── season_trends_mart          25 rows × 10 cols
  └── fact_race_results       10,079 rows × 23 cols
      │
      ▼
  ANALYSIS NOTEBOOK  7 charts · 7 insights · Executive Summary
```

**Pipeline runtime: ~3.5 seconds on the full dataset.**

---

## Key Insights

1. **Hamilton leads by volume; Verstappen leads by rate.** Hamilton's 4,820 career points and 105 wins are the modern era's greatest. But Verstappen averages 13.9 pts/race vs Hamilton's 13.5, with a near-identical win rate (~30%) achieved in half the career length.

2. **2023 was the most statistically dominant season in modern F1 history.** Verstappen's HHI of 0.76 (21/22 wins, 290-pt margin) exceeds Schumacher's most extreme year (2004, HHI = 0.54) by a wide margin. By economic standards, it was a monopoly.

3. **Real title fights are rare.** Only 8 of 25 seasons were decided by fewer than 20 points. Four were decided by 4 points or fewer (2007: 1pt, 2008: 1pt, 2010: 4pts, 2012: 3pts).

4. **Reliability and speed are not a trade-off — elite teams optimise both simultaneously.** Mercedes averaged 95%+ reliability throughout their 8-title hybrid era. Ferrari's reliability failures in competitive years are a quantifiable opportunity cost in championship points.

5. **The calendar grew 50% since 2003** (16 → 24 races). Raw career totals systematically favour modern-era drivers. Per-race normalisation is analytically mandatory for cross-era comparisons.

6. **2012 was the most competitive season in modern F1** (HHI = 0.165). Seven different winners in seven races; championship decided on the final lap of the final race by 3 points.

---

## Analysis Layer

The notebook (`notebooks/F1_Analysis.ipynb`) contains 41 cells structured as a complete analytical presentation:

- **Section 1:** Introduction and 7 analytical questions
- **Section 2:** Data overview — all four marts examined before any chart is drawn
- **Section 3:** Data preparation — theme, subsets, methodology notes
- **Section 4:** Seven analyses — each with hypothesis, chart, and data-driven insight
- **Section 5:** Conclusions — five strategic findings
- **Section 6:** Executive Summary — stakeholder briefing format

---

## Technologies Used

| Tool | Version | Purpose |
|---|---|---|
| Python | 3.12 | Pipeline and analysis |
| pandas | 2.0+ | Data loading, transformation, aggregation |
| NumPy | 1.24+ | Numerical operations, HHI computation |
| Matplotlib | 3.7+ | All chart generation |
| seaborn | 0.13+ | Statistical visualisations |
| Jupyter | — | Interactive analysis notebook |
| pathlib | stdlib | Cross-platform path handling |
| logging | stdlib | Structured pipeline logging |

---

## How to Run

### 1. Clone and install
```bash
git clone https://github.com/<YOUR_USERNAME>/f1-data-pipeline.git
cd f1-data-pipeline
pip install -r requirements.txt
```

### 2. Add raw data
Download the [Ergast CSV flat files](http://ergast.com/mrd/) and place all 14 CSVs in `data/raw/`.

### 3. Run the pipeline
```bash
python src/pipeline.py
```
Produces four marts in `outputs/` and a timestamped log in `logs/`.

### 4. Open the notebook
```bash
jupyter notebook notebooks/F1_Analysis.ipynb
```
The notebook reads from `outputs/` — run the pipeline first.

### Configuration
Edit `CONFIG` in `src/pipeline.py` to change era scope, output format (`"csv"` or `"parquet"`), or toggle schema validation.

---

## Project Structure

```
f1-data-pipeline/
├── README.md
├── requirements.txt
├── LICENSE
├── .gitignore
├── data/
│   ├── raw/                        # Ergast CSV source files
│   │   └── era_snapshot/           # Era-filtered audit trail
│   └── processed/                  # Cleaned tables (*_clean.csv)
├── notebooks/
│   ├── F1_Analysis.ipynb           # Main analysis notebook
│   └── analysis.py                 # Headless chart generation script
├── src/
│   ├── __init__.py
│   ├── ingestion.py                # Stage 1: load · validate · filter
│   ├── cleaning.py                 # Stage 2: clean · standardise · cast
│   ├── transformation.py           # Stage 3: feature engineering · marts
│   └── pipeline.py                 # Orchestrator
├── outputs/
│   ├── driver_performance_mart.csv
│   ├── team_performance_mart.csv
│   ├── season_trends_mart.csv
│   ├── fact_race_results.csv
│   └── charts/
└── logs/
```

---

## Future Improvements

- **Qualifying delta analysis** — which drivers gained the most positions from grid to finish?
- **Teammate head-to-head** — the cleanest isolation of driver talent: same car, same season
- **Circuit-specific performance** — systematic over/underperformance at specific tracks
- **Pit stop strategy modelling** — separating strategic advantage from pace advantage
- **dbt integration** — replace `transformation.py` with dbt models for SQL-native transformations
- **Airflow orchestration** — schedule the pipeline as a DAG with dependency management

---

## License

MIT License. Data sourced from the [Ergast Motor Racing Developer API](http://ergast.com/mrd/).

---

<p align="center">Data Engineering Portfolio · Python · pandas · matplotlib · Jupyter</p>
