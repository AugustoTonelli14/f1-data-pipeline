-- Staging model: pit stops
-- Source: cleaned pit stops table from pipeline

select
    race_id,
    driver_id,
    stop,
    lap,
    duration,
    milliseconds,
    is_long_stop
from read_csv_auto('{{ var("processed_dir") }}/pit_stops_clean.csv')
