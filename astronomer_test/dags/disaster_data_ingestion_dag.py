import os
from textwrap import dedent
import pendulum

from airflow.decorators import dag, task, task_group
from airflow.providers.postgres.hooks.postgres import PostgresHook
from airflow.providers.postgres.operators.postgres import PostgresOperator
from great_expectations_provider.operators.great_expectations import (
    GreatExpectationsOperator,
)

from scripts.disaster_data.disaster_data_extraction import (
    check_directory_exists,
    get_filenames,
    get_function_name,
    get_weather_data_page,
    main,
    move_file,
    check_already_loaded,
)
from scripts.disaster_data.disaster_data_load import list_dir_contents

from structlog import get_logger

import pandas as pd
from pandas import DataFrame


logger = get_logger()
MAX_ACTIVE_TIS = 2


def remove_invalid_rows(weather_data) -> DataFrame:
    """Remove invalid rows

    Remove repeated header rows that are  scattered randomly in the file.
    """
    weather_data = weather_data[weather_data["BEGIN_YEARMONTH"] != "BEGIN_YEARMONTH"]

    return weather_data


def add_meta_cols(df: DataFrame, meta_col_config: dict) -> DataFrame:
    """
    #### Add meta-data columns
    Adds a few columns that would be useful during ingestion.
    """
    df["__row_hash"] = pd.util.hash_pandas_object(df.loc[:]).apply(str)
    df["__filename"] = meta_col_config["__filename"]
    df.rename(lambda x: x.replace('"', "").lower(), axis="columns", inplace=True)

    return df


def get_postgres_conn():
    postgres_hook = PostgresHook(postgres_conn_id="tutorial_pg_conn")
    conn = postgres_hook.get_sqlalchemy_engine()
    return conn


@dag(
    schedule=None,
    start_date=pendulum.datetime(2021, 1, 1, tz="UTC"),
    catchup=False,
    tags=["data_engineering"],
    doc_md=dedent(
        """\
    #### Ingest Disaster data from the NCDC website.

    The website link can be found [here](https://www1.ncdc.noaa.gov/pub/data/swdi/stormevents/csvfiles/)
    """
    ),
)
def disaster_data_ingestion():
    create_disaster_data_table = PostgresOperator(
        task_id="create_disaster_data_table",
        postgres_conn_id="tutorial_pg_conn",
        sql="sql/disaster_data/disaster_data_schema.sql",
    )

    create_disaster_data_log_table = PostgresOperator(
        task_id="create_disaster_data_log_table",
        postgres_conn_id="tutorial_pg_conn",
        sql="sql/disaster_data/disaster_data_log_schema.sql",
    )
    create_disaster_data_log_table.doc_md = dedent(
        """\
        #### Log table
        This table will be used to keep a log of the files that were loaded
    """
    )

    @task(task_id="collect_filenames_to_load")
    def collect_filenames_to_load() -> list:
        """Collects the file names
        Compares the files that were already loaded with the full list of
        file names found on the website. Only the missing file names are returned.
        """
        base_dir = os.getcwd() + "/raw"
        archive_dir = os.getcwd() + "/archive"

        check_directory_exists(base_dir)
        check_directory_exists(archive_dir)
        files = list_dir_contents(base_dir)
        conn = get_postgres_conn()

        # get list with files that were loaded
        loaded_files = check_already_loaded(files=files, conn=conn)
        print(loaded_files)
        # grab the html page for the weather data
        soup = get_weather_data_page()
        # using the page data, query and pull all the file names
        full_file_list = get_filenames(soup, [])
        missing_files = [f for f in full_file_list if f not in loaded_files]
        print("files to be loaded")
        print(missing_files)
        return missing_files

    @task_group(
        group_id="process_disaster_data",
        tooltip="Responsibe for orchestrating the ETL",
        prefix_group_id=True,
        # parent_group=None,
        # dag=None,
    )
    def process_disaster_data() -> None:
        @task(task_id="extract_disaster_data", max_active_tis_per_dag=MAX_ACTIVE_TIS)
        def extract(missing_file):
            """Extract data

            Extracts the file data from the website.
            """
            logger.info(
                get_function_name(),
                message=f"Attempting to extract the following files: {missing_file}",
            )

            if len(missing_file) > 0:
                main([missing_file])
            else:
                logger.info(get_function_name(), message="No new files to load.")

        @task(task_id="test_source_file_quality", max_active_tis_per_dag=MAX_ACTIVE_TIS)
        def test_source_file_quality(missing_file):
            """Check the data quality of the file."""
            logger.info(
                get_function_name(), message=f"Testing data quality for {missing_file}"
            )
            csv_file = missing_file[:-3]
            base_dir = os.getcwd() + "/raw"
            gx_validate_pg = None

            if csv_file.endswith("csv"):
                file_path = f"{base_dir}/{csv_file}"
                logger.info(get_function_name(), message="made it her")

                gx_validate_pg = GreatExpectationsOperator(
                    data_asset_name="disaster__source",
                    task_id="validate_source_expectations",
                    data_context_root_dir="include/gx",
                    dataframe_to_validate=pd.read_csv(file_path),
                    execution_engine="PandasExecutionEngine",
                    expectation_suite_name="disaster__source__suite",
                    return_json_dict=True,
                )

            # execute the DQ check in this task
            gx_validate_pg.execute(dict())

        @task(task_id="load_disaster_data", max_active_tis_per_dag=MAX_ACTIVE_TIS)
        def load_disaster_data(missing_file) -> None:
            """Load Disaster Data

            Loads data to table. Some prework and column addition is done before load.
            """
            csv_file = missing_file[:-3]
            conn = get_postgres_conn()

            base_dir = os.getcwd() + "/raw"

            logger.info(get_function_name(), message=f"Checking {missing_file}")
            if csv_file.endswith("csv"):
                file_path = f"{base_dir}/{csv_file}"
                logger.info(
                    get_function_name(),
                    message=f"Attempting to load data for {file_path}",
                )
                # reading file
                weather_data = pd.read_csv(file_path, delimiter=",", quotechar='"')

                weather_data = remove_invalid_rows(weather_data=weather_data)
                meta_col_config = {"__filename": missing_file}

                weather_data = add_meta_cols(
                    df=DataFrame(weather_data), meta_col_config=meta_col_config
                )
                # column type change
                weather_data = weather_data.astype({"magnitude": "Float32"})

                # load to table
                weather_data.to_sql(
                    name="disaster_data", con=conn, if_exists="append", index=False
                )
                logger.info(
                    get_function_name(),
                    message=f"{missing_file} inserted successfully.",
                )

        @task(task_id="log_filename", max_active_tis_per_dag=MAX_ACTIVE_TIS)
        def log_filename(missing_files):
            """ """
            conn = get_postgres_conn()

            logger.info(
                get_function_name(), messag=f"Logging {missing_files} to log table."
            )

            # convert filename to data frame for loading
            filename_df = pd.DataFrame(data=missing_files, columns=["__filename"])
            filename_df.to_sql(
                name="disaster_data_log",
                con=conn,
                if_exists="append",
                index=False,
            )

        @task(
            task_id="archive_disaster_data_file", max_active_tis_per_dag=MAX_ACTIVE_TIS
        )
        def archive_disaster_data_file(missing_file) -> None:
            raw_dir = os.getcwd() + "/raw"
            archive_dir = os.getcwd() + "/archive"
            csv_file = missing_file[:-3]

            try:
                move_file(csv_file, raw_dir, archive_dir)
            except pd.errors.EmptyDataError:
                logger.info(
                    f"{csv_file} is in an empty file and will be skipped. Moving empty file to archive."
                )
                move_file(csv_file, raw_dir, archive_dir)
            except Exception as e:
                raise (e)

        missing_files = collect_filenames_to_load()
        (
            extract.expand(missing_file=missing_files)
            >> test_source_file_quality.expand(missing_file=missing_files)
            >> load_disaster_data.expand(missing_file=missing_files)
            >> log_filename(missing_files=missing_files)
            >> archive_disaster_data_file.expand(missing_file=missing_files)
        )

    (
        [
            create_disaster_data_table,
            create_disaster_data_log_table,
        ]
        >> process_disaster_data()
    )


disaster_data_ingestion()
