-- Staging model: constructors dimension
-- Source: cleaned constructors table from pipeline

select
    constructor_id,
    constructor_ref,
    name,
    nationality
from read_csv_auto('{{ var("processed_dir") }}/constructors_clean.csv')
