-- Mart: season overview — one row per season with summary metrics

with results as (
    select r.*, rc.year
    from {{ ref('stg_results') }} r
    join {{ ref('stg_races') }} rc on r.race_id = rc.race_id
)

select
    year,
    count(distinct race_id) as total_races,
    count(distinct driver_id) as total_drivers,
    count(distinct constructor_id) as total_constructors,
    sum(case when position_numeric = 1 then 1 else 0 end) as total_wins,
    round(avg(points), 2) as avg_points_per_entry,
    sum(case when finished = 0 then 1 else 0 end) as total_dnfs,
    round(
        sum(case when finished = 0 then 1 else 0 end) * 100.0
        / nullif(count(*), 0), 2
    ) as dnf_rate_pct
from results
group by year
order by year
