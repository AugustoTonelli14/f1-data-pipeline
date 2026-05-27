.PHONY: help install lint test pipeline warehouse dbt-run dbt-test analysis all clean

PROCESSED_DIR := $(shell pwd)/data/processed

help:  ## Show available targets
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | \
		awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-15s\033[0m %s\n", $$1, $$2}'

install:  ## Install all dependencies
	pip install -r requirements.txt

lint:  ## Run ruff linter
	ruff check src/ tests/

test:  ## Run pytest suite
	pytest tests/ -v --tb=short

pipeline:  ## Run the full ETL pipeline (ingestion -> cleaning -> transformation)
	python src/pipeline.py

warehouse:  ## Build the DuckDB star schema from cleaned tables
	python src/modeling.py

dbt-run:  ## Run dbt models (requires pipeline to have run first)
	cd dbt && dbt run --vars '{"processed_dir": "$(PROCESSED_DIR)"}' --profiles-dir .

dbt-test:  ## Run dbt tests
	cd dbt && dbt test --vars '{"processed_dir": "$(PROCESSED_DIR)"}' --profiles-dir .

analysis:  ## Generate all charts from pipeline outputs
	python src/analysis.py

all: pipeline warehouse dbt-run analysis  ## Run full pipeline + warehouse + dbt + analysis

clean:  ## Remove all generated outputs (keeps raw data)
	rm -rf data/processed/*.csv
	rm -rf outputs/*.csv outputs/*.parquet outputs/fact_race_results/
	rm -rf outputs/f1_warehouse.duckdb outputs/f1_dbt.duckdb
	rm -rf logs/*.log
	cd dbt && rm -rf target dbt_packages
