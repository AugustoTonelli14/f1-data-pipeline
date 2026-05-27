-- Mart: circuit statistics — one row per circuit with aggregate race metrics

with results as (
    select r.*, rc.year, rc.circuit_id
    from {{ ref('stg_results') }} r
    join {{ ref('stg_races') }} rc on r.race_id = rc.race_id
)

select
    c.circuit_id,
    c.name as circuit_name,
    c.country,
    c.location,
    count(distinct res.race_id) as races_held,
    min(res.year) as first_race_year,
    max(res.year) as last_race_year,
    round(avg(res.points), 2) as avg_points_per_entry,
    sum(case when res.finished = 0 then 1 else 0 end) as total_dnfs,
    round(
        sum(case when res.finished = 0 then 1 else 0 end) * 100.0
        / nullif(count(*), 0), 2
    ) as dnf_rate_pct,
    round(avg(res.position_numeric), 2) as avg_finishing_position
from results res
join {{ ref('stg_circuits') }} c on res.circuit_id = c.circuit_id
group by c.circuit_id, c.name, c.country, c.location
order by races_held desc
