FROM quay.io/astronomer/astro-runtime:10.2.0

ADD requirements.txt .
# RUN pip install apache-airflow==2.7.3 -r requirements.txt
RUN pip install -r requirements.txt

COPY dbt_requirements.txt ./

RUN pip install --upgrade pip
# install dbt into a virtual environment
RUN python -m venv dbt_venv
# RUN pip install --upgrade pip && \
RUN source dbt_venv/bin/activate
RUN cd dags/dbt/analytics_practice/ && dbt deps
RUN pip install --no-cache-dir -r dbt_requirements.txt