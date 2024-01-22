{{
    config(
        materialized="incremental",
        unique_key="__row_hash",
        on_schema_change="fail"
    )
}}

with distinct_records as (
    select distinct {{ dbt_utils.star(from=ref("stg_disaster_data")) }}
    from {{ ref("stg_disaster_data") }}
    {% if is_incremental() %}
        where __date_loaded > 
        (select max(__date_loaded) from {{ this }})
    {% endif %}
    
),
distinct_rn as (
    select
        {{ dbt_utils.star(from=ref("stg_disaster_data")) }},
        row_number() over (partition by __row_hash order by __date_loaded) as rn
    from distinct_records
)


select {{ dbt_utils.star(from=ref("stg_disaster_data")) }}
from distinct_rn
where rn = 1