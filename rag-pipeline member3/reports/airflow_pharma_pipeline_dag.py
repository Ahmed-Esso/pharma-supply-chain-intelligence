
from datetime import datetime, timedelta

from airflow import DAG
from airflow.operators.python import PythonOperator

from pharma_ingestion_runner import run_source

default_args = {
    "owner": "pharma_supply_chain_team",
    "depends_on_past": False,
    "retries": 3,
    "retry_delay": timedelta(minutes=2),
    "retry_exponential_backoff": True,
    "max_retry_delay": timedelta(minutes=15)
}

with DAG(
    dag_id="pharma_supply_chain_ingestion",
    description="Bronze ingestion from openFDA and NIH RxNav APIs",
    default_args=default_args,
    start_date=datetime(2026, 1, 1),
    schedule=None,
    catchup=False,
    max_active_runs=1,
    tags=["pharma", "data-engineering", "bronze", "ingestion"]
) as dag:

    ingest_openfda_ndc = PythonOperator(
        task_id="ingest_openfda_ndc",
        python_callable=run_source,
        op_kwargs={"source_id": "SRC-001"}
    )

    ingest_openfda_enforcement = PythonOperator(
        task_id="ingest_openfda_enforcement",
        python_callable=run_source,
        op_kwargs={"source_id": "SRC-002"}
    )

    ingest_rxnav_version = PythonOperator(
        task_id="ingest_rxnav_version",
        python_callable=run_source,
        op_kwargs={"source_id": "SRC-005"}
    )

    [
        ingest_openfda_ndc,
        ingest_openfda_enforcement,
        ingest_rxnav_version
    ]
