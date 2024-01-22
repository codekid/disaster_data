{{
    config(
        materialized="incremental",
        unique_key="__row_hash",
        on_schema_change="fail"
    )
}}

with latest_records as (
    select *
    from {{ ref("stg_disaster_data") }}
    {% if is_incremental() %}
        where __date_loaded > 
        (select max(__date_loaded) from {{ this }})
    {% endif %}
    
)

select *
from latest_records