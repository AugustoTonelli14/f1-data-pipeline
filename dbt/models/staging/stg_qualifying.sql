-- Staging model: qualifying results
-- Source: cleaned qualifying table from pipeline

select
    qualify_id,
    race_id,
    driver_id,
    constructor_id,
    position,
    q1_ms,
    q2_ms,
    q3_ms
from read_csv_auto('{{ var("processed_dir") }}/qualifying_clean.csv')
