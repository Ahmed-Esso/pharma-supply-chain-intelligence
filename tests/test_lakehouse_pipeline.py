"""
Automated Pytest Suite for Workstream 2 (Databricks Lakehouse & DuckDB/PyArrow Outputs).
Validates:
1. Databricks PySpark & Delta Lake Notebooks (.ipynb) across Bronze, Silver, and Gold.
2. Exported Parquet/CSV tables using PyArrow and DuckDB SQL queries.
3. Quarantine enforcement and zero-silent-drop data quality audit report.
"""

from __future__ import annotations

import json
from pathlib import Path

import duckdb
import pyarrow.parquet as pq

REPO_ROOT = Path(__file__).resolve().parents[1]
LAKEHOUSE_DIR = REPO_ROOT / "lakehouse"
BRONZE_DIR = LAKEHOUSE_DIR / "bronze"
SILVER_DIR = LAKEHOUSE_DIR / "silver"
GOLD_DIR = LAKEHOUSE_DIR / "gold"


def test_databricks_notebooks_exist_and_valid_json() -> None:
    notebooks = [
        BRONZE_DIR / "01_bronze_ingestion.ipynb",
        SILVER_DIR / "02_silver_cleaning_and_quarantine.ipynb",
        GOLD_DIR / "03_gold_analytics_and_duckdb_kpis.ipynb",
    ]
    for nb_path in notebooks:
        assert nb_path.exists(), f"Missing Databricks notebook: {nb_path}"
        with open(nb_path, "r", encoding="utf-8") as f:
            nb = json.load(f)
        assert "cells" in nb and len(nb["cells"]) >= 2


def test_bronze_parquet_snapshots() -> None:
    ndc_table = pq.read_table(BRONZE_DIR / "bronze_openfda_ndc.parquet")
    enf_table = pq.read_table(BRONZE_DIR / "bronze_openfda_enforcement.parquet")
    who_table = pq.read_table(BRONZE_DIR / "bronze_who_eml.parquet")

    assert ndc_table.num_rows == 100
    assert enf_table.num_rows == 100
    assert who_table.num_rows == 69
    assert "raw_record_sha256" in ndc_table.column_names


def test_silver_cleaning_quarantine_and_dq_report() -> None:
    with open(SILVER_DIR / "data_quality_report.json", "r", encoding="utf-8") as f:
        dq = json.load(f)

    assert dq["zero_silent_drop_policy_verified"] is True
    assert dq["summary"]["total_bronze_records_evaluated"] == 200
    assert (
        dq["summary"]["total_valid_silver_records"]
        + dq["summary"]["total_quarantined_records"]
        == 200
    )

    df_silver_ndc = pq.read_table(SILVER_DIR / "silver_openfda_ndc.parquet").to_pandas()
    df_quarantine = pq.read_table(SILVER_DIR / "silver_quarantine_records.parquet").to_pandas()

    assert df_silver_ndc["product_id"].is_unique
    assert len(df_quarantine) == 3
    assert (df_quarantine["quarantine_reason_code"].str.len() > 0).all()


def test_gold_analytics_with_duckdb_and_pyarrow() -> None:
    con = duckdb.connect(database=":memory:")
    con.register(
        "gold_catalog",
        pq.read_table(GOLD_DIR / "gold_pharma_catalog_analytics.parquet"),
    )
    con.register(
        "gold_recalls",
        pq.read_table(GOLD_DIR / "gold_recall_supply_risk_kpis.parquet"),
    )

    catalog_stats = con.execute(
        "SELECT COUNT(*) AS cnt, SUM(total_products) AS total_prods FROM gold_catalog"
    ).fetchone()
    recall_stats = con.execute(
        "SELECT SUM(total_recalls) AS total_recalls FROM gold_recalls"
    ).fetchone()
    con.close()

    assert catalog_stats[0] == 88
    assert catalog_stats[1] == 97
    assert recall_stats[0] == 100
