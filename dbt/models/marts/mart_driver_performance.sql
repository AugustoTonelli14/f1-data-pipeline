-- Mart: driver performance — one row per driver (career aggregates)

with results as (
    select r.*, rc.year
    from {{ ref('stg_results') }} r
    join {{ ref('stg_races') }} rc on r.race_id = rc.race_id
),

driver_agg as (
    select
        driver_id,
        count(distinct race_id) as races_entered,
        sum(case when position_numeric = 1 then 1 else 0 end) as wins,
        sum(case when position_numeric <= 3 then 1 else 0 end) as podiums,
        sum(points) as points_total,
        sum(case when finished = 0 then 1 else 0 end) as dnf_count,
        round(avg(grid), 2) as avg_grid,
        round(avg(position_numeric), 2) as avg_finish,
        count(distinct year) as seasons_active,
        min(year) as first_season,
        max(year) as last_season
    from results
    group by driver_id
),

with_rates as (
    select
        *,
        round(wins * 100.0 / nullif(races_entered, 0), 2) as win_rate_pct,
        round(podiums * 100.0 / nullif(races_entered, 0), 2) as podium_rate_pct,
        round(dnf_count * 100.0 / nullif(races_entered, 0), 2) as dnf_rate_pct,
        round(points_total * 1.0 / nullif(races_entered, 0), 3) as points_per_race
    from driver_agg
    where races_entered >= 5
)

select
    w.driver_id,
    d.full_name,
    d.code,
    d.nationality,
    w.first_season,
    w.last_season,
    w.seasons_active,
    w.races_entered,
    w.wins,
    w.podiums,
    w.dnf_count,
    w.points_total,
    w.points_per_race,
    w.win_rate_pct,
    w.podium_rate_pct,
    w.dnf_rate_pct,
    w.avg_grid,
    w.avg_finish
from with_rates w
left join {{ ref('stg_drivers') }} d on w.driver_id = d.driver_id
order by w.points_total desc
