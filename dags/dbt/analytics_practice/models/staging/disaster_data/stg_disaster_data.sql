{{
    config(
        materialized="view"
    )
}}

select DISTINCT *
from {{ source("disaster_data", "disaster_data") }}