from airflow import settings
from airflow.models import Connection


def add_postgres_conn():
    conn = Connection(
        conn_id="tutorial_pg_conn",
        conn_type="postgres",
        host="postgres",
        login="airflow",
        password="airflow",
        port=5432,
    )  # create a connection object
    session = settings.Session()  # get the session
    session.add(conn)
    session.commit()


def main():
    add_postgres_conn()


if __name__ == "__main__":
    main()
