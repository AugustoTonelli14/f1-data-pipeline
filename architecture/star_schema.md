# F1 Data Warehouse — Star Schema

## Entity-Relationship Diagram

```mermaid
erDiagram
    fact_race_results {
        int result_id PK
        int race_id FK
        int driver_id FK
        int constructor_id FK
        int grid
        int qualifying_position
        float position_numeric
        int position_order
        float points
        int laps
        int milliseconds
        int status_id
        int finished
        float positions_gained
    }

    dim_drivers {
        int driver_id PK
        string driver_ref
        int number
        string code
        string forename
        string surname
        string full_name
        date dob
        string nationality
    }

    dim_constructors {
        int constructor_id PK
        string constructor_ref
        string name
        string nationality
    }

    dim_circuits {
        int circuit_id PK
        string circuit_ref
        string name
        string location
        string country
        float lat
        float lng
        int alt
    }

    dim_races {
        int race_id PK
        int year
        int round
        int circuit_id FK
        string name
        date date
        string season_round
    }

    dim_date {
        date date PK
        int year
        int month
        int day
        string day_of_week
        int quarter
        int week_of_year
        int is_weekend
    }

    fact_race_results ||--o{ dim_drivers : driver_id
    fact_race_results ||--o{ dim_constructors : constructor_id
    fact_race_results ||--o{ dim_races : race_id
    dim_races ||--o{ dim_circuits : circuit_id
    dim_races ||--o{ dim_date : date
```

## Design Decisions

- **Grain**: One row per driver per race entry (finest grain available).
- **Dimensions**: Five conformed dimensions covering who (drivers, constructors), where (circuits), when (races, date), and what happened (fact measures).
- **Date dimension**: Generated from race dates rather than a full calendar spine, since F1 events are sparse (~20-24 days per year).
- **SCD strategy**: Type 1 (overwrite) for all dimensions. Driver nationality and constructor name changes are rare enough that historical tracking adds complexity without analytical value.
- **Storage**: DuckDB single-file database for zero-configuration OLAP queries.
