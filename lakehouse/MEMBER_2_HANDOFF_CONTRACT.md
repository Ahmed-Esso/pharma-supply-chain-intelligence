# Member 2 → Member 4 Integration Contract (Databricks Lakehouse & DuckDB Analytics)

- **Owner (Member 2):** Ahmed Essam — Lakehouse & Data Quality
- **Consumer (Member 4):** Rawan Husseiny — API (`api/`) & Streamlit UI (`app/`)
- **Databricks Notebooks:**
  - `lakehouse/bronze/01_bronze_ingestion.ipynb`
  - `lakehouse/silver/02_silver_cleaning_and_quarantine.ipynb`
  - `lakehouse/gold/03_gold_analytics_and_duckdb_kpis.ipynb`

---

## 1. Ready-to-Use Gold & Silver Datasets

| Layer | Table Name | Parquet Path | CSV Path | Description |
|---|---|---|---|---|
| **GOLD** | `gold_pharma_catalog_analytics` | `lakehouse/gold/gold_pharma_catalog_analytics.parquet` | `lakehouse/gold/gold_pharma_catalog_analytics.csv` | Active ingredient supply-chain diversity, single-supplier risk, dosage forms, and WHO Essential Medicines cross-match. |
| **GOLD** | `gold_recall_supply_risk_kpis` | `lakehouse/gold/gold_recall_supply_risk_kpis.parquet` | `lakehouse/gold/gold_recall_supply_risk_kpis.csv` | FDA recall hazard classes (`Class I/II/III`), root-cause categories (`CGMP`, `Sterility`, `Contamination`), and country distribution. |
| **GOLD** | `gold_executive_kpis.json` | — | `lakehouse/gold/gold_executive_kpis.json` | Pre-computed KPI summary cards for executive dashboard top banners. |
| **SILVER** | `silver_openfda_ndc` | `lakehouse/silver/silver_openfda_ndc.parquet` | `lakehouse/silver/silver_openfda_ndc.csv` | Cleaned, standardized, deduplicated FDA NDC drug catalog. |
| **SILVER** | `silver_openfda_enforcement` | `lakehouse/silver/silver_openfda_enforcement.parquet` | `lakehouse/silver/silver_openfda_enforcement.csv` | Cleaned, standardized FDA drug recall reports with ISO dates and root-cause tags. |
| **QUARANTINE** | `silver_quarantine_records` | `lakehouse/silver/silver_quarantine_records.parquet` | `lakehouse/silver/silver_quarantine_records.csv` | Quarantined records failing mandatory quality rules with explicit reason codes (`zero_silent_drop_policy_verified = True`). |

---

## 2. Querying Gold & Silver Parquet Tables via DuckDB & PyArrow in Python (FastAPI / Streamlit)

```python
import duckdb
import pyarrow.parquet as pq

con = duckdb.connect(database=":memory:")
con.register("gold_catalog", pq.read_table("lakehouse/gold/gold_pharma_catalog_analytics.parquet"))
con.register("gold_recalls", pq.read_table("lakehouse/gold/gold_recall_supply_risk_kpis.parquet"))

# Example 1: Top active ingredients with multiple manufacturers
top_ingredients = con.execute("""
    SELECT active_ingredient, total_products, distinct_labelers_count, is_who_essential
    FROM gold_catalog
    ORDER BY total_products DESC
    LIMIT 10
""").df()

# Example 2: Recalls breakdown by root cause and hazard classification
recall_summary = con.execute("""
    SELECT classification, recall_reason_category, SUM(total_recalls) AS recalls
    FROM gold_recalls
    GROUP BY classification, recall_reason_category
    ORDER BY recalls DESC
""").df()
```
