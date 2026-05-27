-- Staging model: drivers dimension
-- Source: cleaned drivers table from pipeline

select
    driver_id,
    driver_ref,
    number,
    code,
    forename,
    surname,
    full_name,
    dob,
    nationality
from read_csv_auto('{{ var("processed_dir") }}/drivers_clean.csv')
