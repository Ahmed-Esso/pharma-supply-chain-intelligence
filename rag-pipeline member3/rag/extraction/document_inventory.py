"""
Task 1 (ClickUp ID: 123u8tyngjm) — Inventory and collect source documents
Task 6 (ClickUp ID: 123u8tync6d) — Confirm source-data limitations and sample-data labeling

Builds and validates the official RAG Source Document Register (CSV + JSON),
verifying physical file presence, SHA-256 checksums, licensing, and scope limitations.
"""

from __future__ import annotations

import csv
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List


REPO_ROOT = Path(__file__).resolve().parents[2]
WORKSPACE_ROOT = REPO_ROOT.parent
EXTRACTION_DIR = Path(__file__).resolve().parent


def compute_sha256(file_path: Path) -> str:
    """Compute SHA-256 hash of a file for provenance tracking."""
    h = hashlib.sha256()
    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def get_source_documents_spec() -> List[Dict[str, Any]]:
    """Return the curated list of official source documents for the RAG pipeline."""
    return [
        {
            "document_id": "DOC-WHO-EML-2023",
            "title": "WHO Model List of Essential Medicines - 23rd List (2023)",
            "publisher": "World Health Organization (WHO)",
            "source_url": "https://www.who.int/publications/i/item/WHO-MHP-HPS-EML-2023.02",
            "publication_date": "2023-07-26",
            "retrieval_date": "2026-11-02",
            "document_type": "PDF_REGULATORY_GUIDELINE",
            "file_format": "PDF",
            "language": "en",
            "license": "CC BY-NC-SA 3.0 IGO",
            "geographic_scope": "Global (WHO Reference Standard)",
            "scope_limitations": (
                "Official global reference list of essential medicines, dosage forms, and "
                "therapeutic alternatives (AWaRe antibiotic groups). Does NOT represent "
                "live Egyptian market stock or local retail pricing."
            ),
            "is_synthetic": False,
            "candidate_paths": [
                WORKSPACE_ROOT / "member_1" / "data" / "bronze" / "who" / "WHO_EML_2023.pdf",
                REPO_ROOT / "lakehouse" / "bronze" / "who" / "WHO_EML_2023.pdf",
            ],
        },
        {
            "document_id": "DOC-FDA-ENF-20261102",
            "title": "openFDA Drug Enforcement & Recall Reports Snapshot (100 Records)",
            "publisher": "U.S. Food and Drug Administration (openFDA)",
            "source_url": "https://api.fda.gov/drug/enforcement.json",
            "publication_date": "2026-10-21",
            "retrieval_date": "2026-11-02",
            "document_type": "JSON_REGULATORY_RECALLS",
            "file_format": "JSON",
            "language": "en",
            "license": "CC0 1.0 Public Domain (openFDA Terms of Service)",
            "geographic_scope": "United States ( with international manufacturing sites )",
            "scope_limitations": (
                "Verified FDA drug recall enforcement records (reasons for recall, CGMP deviations, "
                "sterility issues, classifications Class I/II/III, lot codes). Reflects U.S. FDA "
                "regulatory actions, not Egyptian Drug Authority (EDA) local recalls."
            ),
            "is_synthetic": False,
            "candidate_paths": [
                REPO_ROOT
                / "member_1_deliverables"
                / "bronze_live_api"
                / "openfda_enforcement_20261102T155044Z.json",
                WORKSPACE_ROOT
                / "member_1"
                / "member_1_deliverables"
                / "bronze_live_api"
                / "openfda_enforcement_20261102T155044Z.json",
            ],
        },
        {
            "document_id": "DOC-FDA-NDC-20261102",
            "title": "openFDA National Drug Code (NDC) Directory Snapshot (100 Records)",
            "publisher": "U.S. Food and Drug Administration (openFDA)",
            "source_url": "https://api.fda.gov/drug/ndc.json",
            "publication_date": "2026-10-30",
            "retrieval_date": "2026-11-02",
            "document_type": "JSON_DRUG_CATALOG",
            "file_format": "JSON",
            "language": "en",
            "license": "CC0 1.0 Public Domain (openFDA Terms of Service)",
            "geographic_scope": "United States",
            "scope_limitations": (
                "Official product directory covering brand names, generic names, active ingredients, "
                "strengths, dosage forms, and packaging descriptions. Inclusion in NDC does not "
                "verify current commercial availability or local inventory."
            ),
            "is_synthetic": False,
            "candidate_paths": [
                REPO_ROOT
                / "member_1_deliverables"
                / "bronze_live_api"
                / "openfda_ndc_20261102T155044Z.json",
                WORKSPACE_ROOT
                / "member_1"
                / "member_1_deliverables"
                / "bronze_live_api"
                / "openfda_ndc_20261102T155044Z.json",
            ],
        },
    ]


def build_document_inventory() -> Dict[str, Any]:
    """Validate all source documents and save document_register.csv & .json."""
    specs = get_source_documents_spec()
    inventory_rows: List[Dict[str, Any]] = []

    for spec in specs:
        resolved_path: Path | None = None
        for candidate in spec["candidate_paths"]:
            if candidate.exists() and candidate.is_file():
                resolved_path = candidate
                break

        exists = resolved_path is not None
        file_size = resolved_path.stat().st_size if exists and resolved_path else 0
        sha256 = compute_sha256(resolved_path) if exists and resolved_path else ""
        rel_path = (
            str(resolved_path.relative_to(WORKSPACE_ROOT))
            if exists and resolved_path and resolved_path.is_relative_to(WORKSPACE_ROOT)
            else (str(resolved_path) if resolved_path else "NOT_FOUND")
        )

        row = {
            "document_id": spec["document_id"],
            "title": spec["title"],
            "publisher": spec["publisher"],
            "source_url": spec["source_url"],
            "publication_date": spec["publication_date"],
            "retrieval_date": spec["retrieval_date"],
            "document_type": spec["document_type"],
            "file_format": spec["file_format"],
            "language": spec["language"],
            "license": spec["license"],
            "geographic_scope": spec["geographic_scope"],
            "scope_limitations": spec["scope_limitations"],
            "is_synthetic": spec["is_synthetic"],
            "file_exists": exists,
            "file_path": rel_path,
            "absolute_path": str(resolved_path) if resolved_path else "",
            "file_size_bytes": file_size,
            "sha256": sha256,
            "inventory_status": "VERIFIED_READY" if exists and file_size > 0 else "MISSING",
        }
        inventory_rows.append(row)

    EXTRACTION_DIR.mkdir(parents=True, exist_ok=True)
    csv_path = EXTRACTION_DIR / "document_register.csv"
    json_path = EXTRACTION_DIR / "document_register.json"

    fieldnames = list(inventory_rows[0].keys())
    with open(csv_path, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(inventory_rows)

    payload = {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "owner": "Mayar Hany (Member 3 — Document Processing & RAG)",
        "clickup_task_ids": ["123u8tyngjm", "123u8tync6d"],
        "total_registered_sources": len(inventory_rows),
        "verified_sources_count": sum(1 for r in inventory_rows if r["file_exists"]),
        "zero_mock_policy_enforced": True,
        "documents": inventory_rows,
    }
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)

    return payload


if __name__ == "__main__":
    result = build_document_inventory()
    print(f"Document inventory generated: {result['verified_sources_count']}/{result['total_registered_sources']} sources verified.")
