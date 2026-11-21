"""
Master End-to-End Runner for Workstream 3 — Document Processing & RAG
Assignee: Mayar Hany (Member 3)

Executes all 5 official ClickUp tasks sequentially:
1. 123u8tyngjm — Inventory and collect source documents
2. 123u8tyngjn — Implement text extraction and OCR fallback
3. 123u8tyngjp — Build chunking and embeddings pipeline
4. 123u8tyngk4 — Implement retrieval, grounded answers, and citations
5. 123u8tyngk5 — Evaluate RAG relevance and citation support
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from rag.chunking.chunker import run_chunking_pipeline
from rag.chunking.embeddings import build_embeddings_index
from rag.evaluation.evaluate_rag import run_rag_evaluation
from rag.extraction.document_inventory import build_document_inventory
from rag.extraction.extractor import run_extraction_pipeline
from rag.retrieval.rag_pipeline import ask_question


def run_all() -> dict:
    print("=" * 75)
    print("WORKSTREAM 3: DOCUMENT PROCESSING & RAG PIPELINE (MEMBER 3 — MAYAR HANY)")
    print("=" * 75)

    print("\n[1/5] Task 123u8tyngjm: Building & validating source document inventory...")
    inv = build_document_inventory()
    print(
        f"      Verified sources: {inv['verified_sources_count']}/{inv['total_registered_sources']}"
    )

    print("\n[2/5] Task 123u8tyngjn: Running PDF text extraction + OCR fallback & JSON normalization...")
    ext = run_extraction_pipeline()
    print(
        f"      Extracted units: {ext['usable_units']}/{ext['total_extracted_units']} usable "
        f"({ext['total_characters_extracted']:,} chars)"
    )

    print("\n[3/5] Task 123u8tyngjp (Part A): Splitting documents into overlapping chunks...")
    chk = run_chunking_pipeline()
    print(
        f"      Generated chunks: {chk['total_chunks_generated']} "
        f"(avg {chk['avg_chunk_chars']} chars/chunk)"
    )

    print("\n[3/5] Task 123u8tyngjp (Part B): Computing vector embeddings & hybrid index...")
    emb = build_embeddings_index()
    print(
        f"      Embeddings matrix shape: ({emb['num_vectors']}, {emb['embedding_dimension']}) "
        f"| Model: {emb['embedding_model']}"
    )

    print("\n[4/5] Task 123u8tyngk4: Smoke-testing grounded retrieval & citation contract...")
    sample_res = ask_question(
        "What caused the recall of Progesterone 100 mg/mL in Corn Oil Injection (Recall D-321-2016)?"
    )
    print(
        f"      Sample query status: {sample_res['status']} | "
        f"Top citation: {sample_res['sources'][0]['document_id']} (Page/Record {sample_res['sources'][0]['page']})"
    )

    print("\n[5/5] Task 123u8tyngk5: Running 12-question RAG evaluation & guardrail benchmark...")
    ev = run_rag_evaluation()
    m = ev["metrics"]
    print(f"      Overall Status Accuracy:            {m['overall_status_accuracy'] * 100:.1f}%")
    print(f"      Document Retrieval Hit@1:           {m['document_hit_rate_at_1'] * 100:.1f}%")
    print(f"      Document Retrieval Hit@3:           {m['document_hit_rate_at_3'] * 100:.1f}%")
    print(f"      Exact Page/Record Citation Hit:     {m['exact_page_citation_accuracy'] * 100:.1f}%")
    print(f"      Unsupported Query Rejection Rate:   {m['unsupported_query_rejection_rate'] * 100:.1f}%")
    print("=" * 75)

    return {
        "inventory": inv,
        "extraction": ext,
        "chunking": chk,
        "embeddings": emb,
        "evaluation_metrics": m,
    }


if __name__ == "__main__":
    run_all()
