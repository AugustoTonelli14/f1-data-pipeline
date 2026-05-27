-- Mart: team performance — one row per constructor per season

with results as (
    select r.*, rc.year
    from {{ ref('stg_results') }} r
    join {{ ref('stg_races') }} rc on r.race_id = rc.race_id
),

team_agg as (
    select
        constructor_id,
        year,
        count(distinct race_id) as races,
        count(*) as entries,
        sum(case when position_numeric = 1 then 1 else 0 end) as wins,
        sum(case when position_numeric <= 3 then 1 else 0 end) as podiums,
        sum(case when grid = 1 then 1 else 0 end) as poles,
        sum(points) as points_total,
        sum(case when finished = 0 then 1 else 0 end) as dnf_count,
        count(distinct driver_id) as drivers_used
    from results
    group by constructor_id, year
)

select
    t.constructor_id,
    c.name,
    c.nationality,
    t.year,
    t.races,
    t.entries,
    t.wins,
    t.podiums,
    t.poles,
    t.dnf_count,
    t.drivers_used,
    t.points_total,
    round(t.points_total * 1.0 / nullif(t.races, 0), 3) as points_per_race,
    round(t.wins * 100.0 / nullif(t.entries, 0), 2) as win_rate_pct,
    round(t.podiums * 100.0 / nullif(t.entries, 0), 2) as podium_rate_pct,
    round((t.entries - t.dnf_count) * 100.0 / nullif(t.entries, 0), 2) as reliability_pct
from team_agg t
left join {{ ref('stg_constructors') }} c on t.constructor_id = c.constructor_id
order by t.year, t.points_total desc
