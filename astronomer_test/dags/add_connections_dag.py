from tarfile import data_filter
import pendulum
from scripts.add_connections import main

from airflow.decorators import task, dag


@dag(
    start_date=pendulum.datetime(2021, 1, 1, tz="UTC"),
    catchup=False,
    schedule=None,
    tags=["data_engineering"],
)
def add_connections():
    @task(task_id="add_postgres_connection")
    def add_postgres_connection():
        main()

    add_postgres_connection()


add_connections()
