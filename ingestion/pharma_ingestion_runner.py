import json
import os
from pathlib import Path
from datetime import datetime, timezone

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_BRONZE_PATH = (
    Path("/content/data/bronze/live_api")
    if Path("/content").exists()
    else PROJECT_ROOT / "data" / "bronze" / "live_api"
)

BRONZE_PATH = Path(
    os.environ.get("PHARMA_BRONZE_PATH", str(DEFAULT_BRONZE_PATH))
)
BRONZE_PATH.mkdir(parents=True, exist_ok=True)

SOURCES = [
    {
        "source_id": "SRC-001",
        "source_name": "openFDA Drug NDC",
        "endpoint": "https://api.fda.gov/drug/ndc.json",
        "params": {"limit": 100},
        "filename": "openfda_ndc"
    },
    {
        "source_id": "SRC-002",
        "source_name": "openFDA Drug Enforcement",
        "endpoint": "https://api.fda.gov/drug/enforcement.json",
        "params": {"limit": 100},
        "filename": "openfda_enforcement"
    },
    {
        "source_id": "SRC-005",
        "source_name": "NIH RxNav Version",
        "endpoint": "https://rxnav.nlm.nih.gov/REST/version.json",
        "params": {},
        "filename": "rxnav_version"
    }
]


def build_session():
    retry = Retry(
        total=3,
        connect=3,
        read=3,
        status=3,
        backoff_factor=1,
        status_forcelist=[429, 500, 502, 503, 504],
        allowed_methods=["GET"],
        respect_retry_after_header=True,
        raise_on_status=False
    )

    adapter = HTTPAdapter(max_retries=retry)
    session = requests.Session()
    session.mount("https://", adapter)
    session.mount("http://", adapter)
    session.headers.update({
        "User-Agent": "PharmaSupplyChainIntelligence/1.0",
        "Accept": "application/json"
    })
    return session


def ingest_source(source):
    session = build_session()
    started_at = datetime.now(timezone.utc)

    try:
        response = session.get(
            source["endpoint"],
            params=source["params"],
            timeout=(10, 30)
        )
        response.raise_for_status()
        payload = response.json()

        retry_object = getattr(response.raw, "retries", None)
        retry_attempts = (
            len(getattr(retry_object, "history", []))
            if retry_object is not None else 0
        )

        if isinstance(payload, dict):
            records = payload.get("results")
            record_count = (
                len(records) if isinstance(records, list)
                else (1 if payload else 0)
            )
        elif isinstance(payload, list):
            record_count = len(payload)
        else:
            record_count = 0

        run_id = datetime.now(timezone.utc).strftime(
            "%Y%m%dT%H%M%SZ"
        )

        output = {
            "metadata": {
                "source_id": source["source_id"],
                "source_name": source["source_name"],
                "source_endpoint": source["endpoint"],
                "request_params": source["params"],
                "ingestion_timestamp_utc": datetime.now(
                    timezone.utc
                ).isoformat(),
                "started_at_utc": started_at.isoformat(),
                "run_id": run_id,
                "http_status": response.status_code,
                "retry_attempts": retry_attempts,
                "record_count": record_count,
                "ingestion_method": "AIRFLOW_PYTHON_OPERATOR",
                "data_layer": "BRONZE"
            },
            "data": payload
        }

        output_file = (
            BRONZE_PATH /
            f"{source['filename']}_{run_id}.json"
        )

        with open(output_file, "w", encoding="utf-8") as file:
            json.dump(output, file, ensure_ascii=False, indent=2)

        response.close()

        return {
            "source_id": source["source_id"],
            "record_count": record_count,
            "http_status": response.status_code,
            "output_file": str(output_file),
            "retry_attempts": retry_attempts
        }

    finally:
        session.close()


def run_source(source_id):
    source = next(
        (item for item in SOURCES if item["source_id"] == source_id),
        None
    )

    if source is None:
        raise ValueError("Unknown source_id: " + source_id)

    return ingest_source(source)


def run_all_sources():
    results = []
    for src in SOURCES:
        res = ingest_source(src)
        results.append(res)
    return results


if __name__ == "__main__":
    print("=" * 75)
    print("Running Member 1 Standalone Bronze Ingestion Runner (Local Mode)")
    print(f"Target Bronze Directory: {BRONZE_PATH}")
    print("=" * 75)
    summary = run_all_sources()
    for item in summary:
        print(
            f"[PASS] {item['source_id']} | HTTP {item['http_status']} | "
            f"Records: {item['record_count']} | File: {item['output_file']}"
        )
    print("=" * 75)

