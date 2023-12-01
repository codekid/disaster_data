FROM apache/airflow:2.7.3 

# USER root
# RUN apt-get install openssh-client -y
# RUN apt-get install openssh-server -y

ADD requirements.txt .
RUN pip install apache-airflow==2.7.3 -r requirements.txt

COPY dbt_requirements.txt ./

RUN pip install --upgrade pip
# install dbt into a virtual environment
RUN python -m venv dbt_venv
# RUN pip install --upgrade pip && \
RUN source dbt_venv/bin/activate
RUN pip install --no-cache-dir -r dbt_requirements.txt
# RUN source {ARIFLOW_HOME}/dbt_venv/bin/deactivate
