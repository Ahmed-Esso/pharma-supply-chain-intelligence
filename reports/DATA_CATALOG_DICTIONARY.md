# Pharma Supply Chain Intelligence — Lakehouse Data Dictionary & Schemas

- **Owner:** Ahmed Essam (Member 2 — Lakehouse & Data Quality)
- **ClickUp Task:** `123u8tync4q` (*Define Bronze/Silver/Gold schemas and data dictionary*)
- **Generated (UTC):** `2026-11-21T05:14:10.969223+00:00`
- **Target Platforms:** Databricks (PySpark + Spark SQL + Delta Lake) & DuckDB + PyArrow (Parquet/CSV Analytics)

---

## Table: `bronze_openfda_ndc` (BRONZE)

- **Source ID:** `SRC-001`
- **Primary Key:** `product_id`
- **Storage Format:** Delta Lake / Parquet / JSONL
- **Description:** Raw openFDA National Drug Code (NDC) product records exploded from API snapshot with full provenance metadata.

| Column Name | Data Type | Nullable | Description |
|---|---|---|---|
| `source_id` | `STRING` | `False` | Source register ID (SRC-001) |
| `source_name` | `STRING` | `False` | Publisher source name |
| `ingestion_timestamp_utc` | `TIMESTAMP` | `False` | UTC timestamp when API snapshot was fetched |
| `run_id` | `STRING` | `False` | Ingestion batch run identifier |
| `product_id` | `STRING` | `True` | Composite FDA product identifier (product_ndc + spl_id) |
| `product_ndc` | `STRING` | `True` | FDA 2-segment National Drug Code |
| `brand_name` | `STRING` | `True` | Proprietary / commercial brand name |
| `generic_name` | `STRING` | `True` | Established generic / nonproprietary drug name |
| `labeler_name` | `STRING` | `True` | Manufacturer or labeler organization name |
| `dosage_form` | `STRING` | `True` | Pharmaceutical dosage form (e.g., TABLET, INJECTION, KIT) |
| `route` | `ARRAY<STRING>` | `True` | Administration route(s) (e.g., ORAL, INTRAVENOUS) |
| `product_type` | `STRING` | `True` | Product category (HUMAN PRESCRIPTION DRUG, HUMAN OTC DRUG, etc.) |
| `marketing_category` | `STRING` | `True` | FDA marketing category (NDA, ANDA, BLA, OTC MONOGRAPH) |
| `marketing_start_date` | `STRING` | `True` | Raw YYYYMMDD marketing start date |
| `listing_expiration_date` | `STRING` | `True` | Raw YYYYMMDD listing expiration date |
| `finished` | `BOOLEAN` | `True` | Whether the product is a finished dosage form |
| `active_ingredients` | `ARRAY<STRUCT<name:STRING,strength:STRING>>` | `True` | Nested list of active ingredients and strengths |
| `packaging` | `ARRAY<STRUCT<package_ndc:STRING,description:STRING>>` | `True` | Nested list of package NDC configurations |
| `raw_record_sha256` | `STRING` | `False` | SHA-256 lineage hash of raw JSON record |

---

## Table: `bronze_openfda_enforcement` (BRONZE)

- **Source ID:** `SRC-002`
- **Primary Key:** `recall_number`
- **Storage Format:** Delta Lake / Parquet / JSONL
- **Description:** Raw openFDA Drug Enforcement recall reports with full provenance metadata.

| Column Name | Data Type | Nullable | Description |
|---|---|---|---|
| `source_id` | `STRING` | `False` | Source register ID (SRC-002) |
| `source_name` | `STRING` | `False` | Publisher source name |
| `ingestion_timestamp_utc` | `TIMESTAMP` | `False` | UTC timestamp of ingestion |
| `run_id` | `STRING` | `False` | Ingestion batch run ID |
| `recall_number` | `STRING` | `True` | FDA assigned recall number (e.g., D-321-2016) |
| `event_id` | `STRING` | `True` | FDA enforcement event identifier |
| `status` | `STRING` | `True` | Recall status (Ongoing, Completed, Terminated) |
| `classification` | `STRING` | `True` | Hazard classification (Class I, Class II, Class III) |
| `recalling_firm` | `STRING` | `True` | Firm initiating the recall |
| `city` | `STRING` | `True` | City of recalling firm |
| `state` | `STRING` | `True` | State of recalling firm |
| `country` | `STRING` | `True` | Country of recalling firm |
| `voluntary_mandated` | `STRING` | `True` | Voluntary vs FDA mandated indicator |
| `distribution_pattern` | `STRING` | `True` | Geographic distribution scope |
| `product_description` | `STRING` | `True` | Full product description and strength |
| `product_quantity` | `STRING` | `True` | Quantity of recalled product |
| `reason_for_recall` | `STRING` | `True` | Regulatory reason for recall (CGMP, Sterility, etc.) |
| `recall_initiation_date` | `STRING` | `True` | Raw YYYYMMDD initiation date |
| `report_date` | `STRING` | `True` | Raw YYYYMMDD report date |
| `code_info` | `STRING` | `True` | Lot numbers and expiration dates |
| `raw_record_sha256` | `STRING` | `False` | SHA-256 lineage hash |

---

## Table: `bronze_who_eml` (BRONZE)

- **Source ID:** `SRC-007`
- **Primary Key:** `page_number`
- **Storage Format:** Delta Lake / Parquet / JSONL
- **Description:** Raw extracted pages from WHO Model List of Essential Medicines (23rd List, 2023).

| Column Name | Data Type | Nullable | Description |
|---|---|---|---|
| `source_id` | `STRING` | `False` | Source register ID (SRC-007) |
| `source_file` | `STRING` | `False` | PDF filename (WHO_EML_2023.pdf) |
| `ingestion_timestamp_utc` | `TIMESTAMP` | `False` | UTC timestamp |
| `page_number` | `INT` | `False` | 1-based PDF page number |
| `characters` | `INT` | `False` | Character count on page |
| `text_preview` | `STRING` | `False` | Extracted page text |
| `raw_record_sha256` | `STRING` | `False` | SHA-256 lineage hash |

---

## Table: `silver_openfda_ndc` (SILVER)

- **Source ID:** `SRC-001`
- **Primary Key:** `product_id`
- **Storage Format:** Delta Lake / Parquet / CSV
- **Description:** Cleaned, standardized, deduplicated FDA NDC drug catalog with flattened active ingredients, strength, pack count, and parsed ISO dates.

| Column Name | Data Type | Nullable | Description |
|---|---|---|---|
| `product_id` | `STRING` | `False` | Validated unique product ID |
| `product_ndc` | `STRING` | `False` | Standardized product NDC |
| `brand_name` | `STRING` | `False` | Cleaned brand name (UPPERCASE trimmed) |
| `generic_name` | `STRING` | `False` | Cleaned generic name |
| `labeler_name` | `STRING` | `False` | Standardized manufacturer/labeler name |
| `primary_active_ingredient` | `STRING` | `False` | Primary active ingredient name |
| `primary_strength` | `STRING` | `False` | Primary active ingredient strength & unit |
| `active_ingredients_all` | `STRING` | `False` | Semicolon-delimited list of all active ingredients |
| `ingredient_count` | `INT` | `False` | Number of active ingredients |
| `dosage_form` | `STRING` | `False` | Standardized dosage form |
| `route` | `STRING` | `False` | Administration route |
| `product_type` | `STRING` | `False` | Product type |
| `marketing_category` | `STRING` | `False` | Marketing category |
| `package_count` | `INT` | `False` | Number of distinct package NDC configurations |
| `sample_package_description` | `STRING` | `True` | Primary package description |
| `marketing_start_date_iso` | `DATE` | `True` | Validated ISO date YYYY-MM-DD |
| `listing_expiration_date_iso` | `DATE` | `True` | Validated ISO date YYYY-MM-DD |
| `is_who_essential_ingredient` | `BOOLEAN` | `False` | True if primary ingredient appears in WHO EML 2023 |
| `source_id` | `STRING` | `False` | Lineage source ID |
| `raw_record_sha256` | `STRING` | `False` | Lineage hash |

---

## Table: `silver_openfda_enforcement` (SILVER)

- **Source ID:** `SRC-002`
- **Primary Key:** `recall_number`
- **Storage Format:** Delta Lake / Parquet / CSV
- **Description:** Cleaned, standardized, deduplicated FDA Drug Recall enforcement records with categorized root causes and ISO dates.

| Column Name | Data Type | Nullable | Description |
|---|---|---|---|
| `recall_number` | `STRING` | `False` | Unique FDA recall number |
| `event_id` | `STRING` | `True` | FDA event ID |
| `classification` | `STRING` | `False` | Validated classification (Class I, Class II, Class III) |
| `severity_rank` | `INT` | `False` | Numeric severity (1=High/Class I, 2=Moderate/Class II, 3=Low/Class III) |
| `status` | `STRING` | `False` | Standardized recall status |
| `recalling_firm` | `STRING` | `False` | Standardized recalling firm |
| `city` | `STRING` | `True` | Firm city |
| `state` | `STRING` | `True` | Firm state |
| `country` | `STRING` | `False` | Firm country |
| `recall_reason_category` | `STRING` | `False` | Standardized root-cause bucket (CGMP_DEVIATION, STERILITY_FAILURE, CONTAMINATION_IMPURITY, LABELING_PACKAGING, SUBPOTENT_SUPERPOTENT, UNAPPROVED_DRUG, OTHER) |
| `reason_for_recall` | `STRING` | `False` | Full recall reason text |
| `product_description` | `STRING` | `False` | Recalled product description |
| `recall_initiation_date_iso` | `DATE` | `True` | Validated ISO initiation date YYYY-MM-DD |
| `report_date_iso` | `DATE` | `True` | Validated ISO report date YYYY-MM-DD |
| `recall_year` | `INT` | `True` | Year of recall initiation |
| `source_id` | `STRING` | `False` | Lineage source ID |
| `raw_record_sha256` | `STRING` | `False` | Lineage hash |

---

## Table: `silver_quarantine_records` (SILVER_QUARANTINE)

- **Source ID:** `ALL`
- **Primary Key:** `quarantine_id`
- **Storage Format:** Delta Lake / Parquet / CSV
- **Description:** Quarantined records that failed mandatory Silver data-quality rules (missing required fields, duplicate keys, invalid dates) with explicit failure reasons.

| Column Name | Data Type | Nullable | Description |
|---|---|---|---|
| `quarantine_id` | `STRING` | `False` | Unique quarantine record identifier |
| `source_table` | `STRING` | `False` | Originating Bronze table |
| `record_identifier` | `STRING` | `False` | Primary key or fallback ID of quarantined record |
| `quarantine_reason_code` | `STRING` | `False` | Rule violation code (e.g., MISSING_ACTIVE_INGREDIENT, DUPLICATE_KEY, INVALID_DATE) |
| `quarantine_reason_detail` | `STRING` | `False` | Detailed explanation of data quality violation |
| `severity` | `STRING` | `False` | QUARANTINED_CRITICAL or WARNING_RETAINED |
| `raw_payload_json` | `STRING` | `False` | Preserved original record JSON |
| `quarantined_at_utc` | `TIMESTAMP` | `False` | Timestamp of quarantine action |

---

## Table: `gold_pharma_catalog_analytics` (GOLD)

- **Source ID:** `SRC-001 + SRC-007`
- **Primary Key:** `active_ingredient`
- **Storage Format:** Delta Lake / Parquet / CSV
- **Description:** Analytics-ready Gold table aggregating drug products, manufacturers, dosage forms, and WHO Essential Medicines cross-match by active ingredient.

| Column Name | Data Type | Nullable | Description |
|---|---|---|---|
| `active_ingredient` | `STRING` | `False` | Standardized active ingredient name |
| `total_products` | `INT` | `False` | Total distinct FDA NDC products containing this ingredient |
| `distinct_labelers_count` | `INT` | `False` | Number of distinct manufacturers/labelers (supply chain diversity indicator) |
| `single_supplier_risk` | `BOOLEAN` | `False` | True if only 1 manufacturer produces this ingredient in the snapshot |
| `dosage_forms` | `STRING` | `False` | Available dosage forms |
| `marketing_categories` | `STRING` | `False` | FDA marketing categories (NDA, ANDA, OTC, etc.) |
| `is_who_essential` | `BOOLEAN` | `False` | Whether ingredient is listed in WHO Essential Medicines List 2023 |
| `data_scope_label` | `STRING` | `False` | Explicit governance label: VERIFIED_REGULATORY_SNAPSHOT_NOT_LIVE_STOCK |

---

## Table: `gold_recall_supply_risk_kpis` (GOLD)

- **Source ID:** `SRC-002`
- **Primary Key:** `risk_segment_id`
- **Storage Format:** Delta Lake / Parquet / CSV
- **Description:** Analytics-ready Gold table summarizing FDA drug recalls by hazard classification, root-cause category, country, and status for supply-chain risk dashboards.

| Column Name | Data Type | Nullable | Description |
|---|---|---|---|
| `risk_segment_id` | `STRING` | `False` | Composite key (classification + recall_reason_category + country) |
| `classification` | `STRING` | `False` | FDA hazard class (Class I, Class II, Class III) |
| `severity_rank` | `INT` | `False` | 1 (Highest) to 3 (Lowest) |
| `recall_reason_category` | `STRING` | `False` | Standardized root cause category |
| `country` | `STRING` | `False` | Manufacturing/recalling country |
| `total_recalls` | `INT` | `False` | Count of recall events in this segment |
| `ongoing_recalls` | `INT` | `False` | Count of currently Ongoing recalls |
| `terminated_or_completed_recalls` | `INT` | `False` | Count of closed recalls |
| `affected_firms_count` | `INT` | `False` | Number of distinct recalling firms |
| `data_scope_label` | `STRING` | `False` | Explicit governance label: VERIFIED_US_FDA_ENFORCEMENT_SNAPSHOT |

---
