from airflow import DAG
from airflow.operators.python import PythonOperator
from datetime import datetime, timedelta
import subprocess
import sys

# ---- PARAMÈTRES DU DAG ----
default_args = {
    "owner": "airflow",
    "depends_on_past": False,
    "retries": 1,
    "retry_delay": timedelta(minutes=5),
}

with DAG(
    dag_id="pipeline_meteo_maroc",
    default_args=default_args,
    description="Pipeline météo : Bronze → Silver → Gold → Tests",
    schedule="0 6 * * *",  # Tous les jours à 6h du matin
    start_date=datetime(2026, 5, 9),
    catchup=False,
    tags=["meteo", "maroc"],
) as dag:

    def run_ingestion():
        exec(open("/opt/airflow/dags/ingestion.py").read())

    def run_silver():
        exec(open("/opt/airflow/dags/silver.py").read())

    def run_gold():
        exec(open("/opt/airflow/dags/gold.py").read())

    def run_tests():
        exec(open("/opt/airflow/dags/tests.py").read())

    tache_ingestion = PythonOperator(
        task_id="ingestion_bronze",
        python_callable=run_ingestion,
    )

    tache_silver = PythonOperator(
        task_id="transformation_silver",
        python_callable=run_silver,
    )

    tache_gold = PythonOperator(
        task_id="enrichissement_gold",
        python_callable=run_gold,
    )

    tache_tests = PythonOperator(
        task_id="tests_qualite",
        python_callable=run_tests,
    )

    # Ordre d'exécution
    tache_ingestion >> tache_silver >> tache_gold >> tache_tests