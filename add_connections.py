from airflow import settings
from airflow.models import Connection

conn = Connection(
    conn_id="tutorials_pg_conn",
    conn_type="postgres",
    host="postgres",
    login="airflow",
    password="airflow",
    port="8080",
)  # create a connection object
session = settings.Session()  # get the session
session.add(conn)
session.commit()
