{{
    config(
        materialized="table"
    )
}}


with d as (
	select *
	from {{ ref("clean__disaster_data") }}
),
formatted as (
select
	state,
	substr(begin_yearmonth::varchar,1,4) as event_year,
	damage_property,
	case
		when length(regexp_replace(lower(damage_property), '[[:alpha:]]','')) > 0 then regexp_replace(lower(damage_property), '[[:alpha:]]','')::float
		else null
	end as damage_number,
	case
		when regexp_like(lower(right(damage_property, 1)), '[[:alpha:]]') then lower(right(damage_property, 1))
		else null
	end	as damage_unit
from d
),

damage as (
select *,
case
	when damage_unit ='h' then damage_number * 100
	when damage_unit ='k' then damage_number * 1000
	when damage_unit ='m' then damage_number * 1000000
	when damage_unit ='b' then damage_number * 1000000000
	else coalesce(damage_number, 0)
end as property_damage
from formatted
)

select
	event_year,
	state,
	sum(property_damage) as total_property_damage
from damage
group by 1,2
