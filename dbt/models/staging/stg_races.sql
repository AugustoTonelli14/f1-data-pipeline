-- Staging model: races
-- Source: cleaned races table from pipeline

select
    race_id,
    year,
    round,
    circuit_id,
    name,
    date,
    season_round
from read_csv_auto('{{ var("processed_dir") }}/races_clean.csv')
