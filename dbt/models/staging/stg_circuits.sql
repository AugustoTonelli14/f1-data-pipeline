-- Staging model: circuits dimension
-- Source: cleaned circuits table from pipeline

select
    circuit_id,
    circuit_ref,
    name,
    location,
    country,
    lat,
    lng,
    alt
from read_csv_auto('{{ var("processed_dir") }}/circuits_clean.csv')
