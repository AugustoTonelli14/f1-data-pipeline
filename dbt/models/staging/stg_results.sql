-- Staging model: race results
-- Source: cleaned results table from pipeline

select
    result_id,
    race_id,
    driver_id,
    constructor_id,
    grid,
    position_numeric,
    position_order,
    points,
    laps,
    milliseconds,
    status_id,
    finished,
    positions_gained
from read_csv_auto('{{ var("processed_dir") }}/results_clean.csv')
