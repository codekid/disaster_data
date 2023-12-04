from curses import meta
import json
import os
import pendulum

from airflow.decorators import dag

from cosmos import DbtTaskGroup, ProjectConfig, ProfileConfig, ExecutionConfig
from cosmos.profiles import PostgresUserPasswordProfileMapping

from structlog import get_logger

import pandas as pd
from pandas import DataFrame

CONNECTION_ID = "tutorial_pg_conn"
SCHEMA_NAME = "public"
DATABASE_NAME = "airflow"
# The path to the dbt project
DBT_PROJECT_PATH = f"{os.environ['AIRFLOW_HOME']}/dags/dbt/analytics_practice"
# The path where Cosmos will find the dbt executable
# in the virtual environment created in the Dockerfile
DBT_EXECUTABLE_PATH = "/home/airflow/.local/bin/dbt"


profile_config = ProfileConfig(
    profile_name="default",
    target_name="dev",
    profile_mapping=PostgresUserPasswordProfileMapping(
        conn_id=CONNECTION_ID,
        profile_args={"schema": SCHEMA_NAME, "database": DATABASE_NAME},
    ),
)

execution_config = ExecutionConfig(
    dbt_executable_path=DBT_EXECUTABLE_PATH,
)


@dag(
    schedule=None,
    start_date=pendulum.datetime(2021, 1, 1, tz="UTC"),
    catchup=False,
    tags=["data_engineering", "analytics_engineering"],
)
def dbt_run_dag():
    dbt_transform_full = DbtTaskGroup(
        group_id="dbt_transform_full",
        project_config=ProjectConfig(DBT_PROJECT_PATH),
        profile_config=profile_config,
        execution_config=execution_config,
        default_args={"retries": 2},
    )

    dbt_transform_full


dbt_run_dag()
