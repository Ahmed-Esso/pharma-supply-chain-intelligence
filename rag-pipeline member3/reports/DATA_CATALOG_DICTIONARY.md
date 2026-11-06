# Pharmaceutical Data Lake - Data Catalog

Generated: 2026-11-04 19:11:23 UTC

Architecture: Bronze -> Silver -> Gold

This catalog describes the CSV datasets physically available at generation time.

---

## Silver Layer

### Dataset: `silver_eda_alerts.csv`

- Status: **EMPTY_DATASET**
- Records: 0
- Columns: 2
- File Size: 0.02 KB

| Column | Data Type | Non-Null Count |
|---|---|---:|
| `alert_id` | `object` | 0 |
| `alert_title` | `object` | 0 |

---

### Dataset: `silver_fda_ndc.csv`

- Status: **AVAILABLE**
- Records: 300
- Columns: 8
- File Size: 69.01 KB

| Column | Data Type | Non-Null Count |
|---|---|---:|
| `product_id` | `str` | 300 |
| `product_ndc` | `str` | 300 |
| `brand_name` | `str` | 300 |
| `generic_name` | `str` | 300 |
| `active_ingredients_all` | `str` | 300 |
| `dosage_form` | `str` | 300 |
| `labeler_name` | `str` | 300 |
| `lineage_hash` | `str` | 300 |

---

### Dataset: `silver_fda_shortages.csv`

- Status: **EMPTY_DATASET**
- Records: 0
- Columns: 2
- File Size: 0.02 KB

| Column | Data Type | Non-Null Count |
|---|---|---:|
| `ingredient` | `object` | 0 |
| `status` | `object` | 0 |

---

### Dataset: `silver_integrated_catalog.csv`

- Status: **EMPTY_DATASET**
- Records: 0
- Columns: 0
- File Size: 0.00 KB

_No column metadata available._

---

### Dataset: `silver_kaggle_medicines.csv`

- Status: **AVAILABLE**
- Records: 22,145
- Columns: 16
- File Size: 7194.79 KB

| Column | Data Type | Non-Null Count |
|---|---|---:|
| `Name` | `str` | 10,320 |
| `Price` | `float64` | 10,320 |
| `Prescription Required` | `object` | 10,320 |
| `Company` | `str` | 8,007 |
| `Salt` | `str` | 9,405 |
| `kaggle_source_file` | `str` | 22,145 |
| `lineage_hash` | `str` | 22,145 |
| `Medicine Name` | `str` | 11,825 |
| `Composition` | `str` | 11,825 |
| `Uses` | `str` | 11,825 |
| `Side_effects` | `str` | 11,825 |
| `Image URL` | `str` | 11,825 |
| `Manufacturer` | `str` | 11,825 |
| `Excellent Review %` | `float64` | 11,825 |
| `Average Review %` | `float64` | 11,825 |
| `Poor Review %` | `float64` | 11,825 |

---

### Dataset: `silver_who_catalog.csv`

- Status: **EMPTY_DATASET**
- Records: 0
- Columns: 0
- File Size: 0.00 KB

_No column metadata available._

---

## Gold Layer

### Dataset: `gold_pharma_analytics.csv`

- Status: **AVAILABLE**
- Records: 222
- Columns: 5
- File Size: 16.33 KB

| Column | Data Type | Non-Null Count |
|---|---|---:|
| `active_ingredient` | `str` | 222 |
| `total_commercial_products` | `int64` | 222 |
| `labelers_count` | `int64` | 222 |
| `has_who_essential_match` | `bool` | 222 |
| `last_updated_utc` | `str` | 222 |

---

### Dataset: `gold_rag_knowledge_corpus.csv`

- Status: **AVAILABLE**
- Records: 150
- Columns: 4
- File Size: 60.34 KB

| Column | Data Type | Non-Null Count |
|---|---|---:|
| `doc_id` | `str` | 150 |
| `source_type` | `str` | 150 |
| `content` | `str` | 150 |
| `metadata` | `str` | 150 |

---

## Catalog Summary

- Total datasets: 8
- Available datasets: 4
- Empty datasets: 4
- Read errors: 0

> Dataset availability does not independently verify source authenticity or data correctness.
