"""
Automated Unit & Integration Tests for Workstream 3 (Document Processing & RAG).
Covers ClickUp Tasks:
- 123u8tyngjm (Source Document Inventory)
- 123u8tyngjn (Text Extraction & OCR Fallback)
- 123u8tyngjp (Chunking & Vector Embeddings)
- 123u8tyngk4 (Retrieval, Grounded Answers & Citations)
- 123u8tyngk5 (RAG Relevance & Citation Evaluation)
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from rag.chunking.chunker import CHUNKING_DIR, run_chunking_pipeline
from rag.chunking.embeddings import build_embeddings_index
from rag.evaluation.evaluate_rag import run_rag_evaluation
from rag.extraction.document_inventory import EXTRACTION_DIR, build_document_inventory
from rag.extraction.extractor import run_extraction_pipeline
from rag.retrieval import ask_question, retrieve_chunks


def test_task1_document_inventory() -> None:
    inv = build_document_inventory()
    assert inv["total_registered_sources"] == 3
    assert inv["verified_sources_count"] == 3
    assert (EXTRACTION_DIR / "document_register.csv").exists()
    assert (EXTRACTION_DIR / "document_register.json").exists()
    for doc in inv["documents"]:
        assert doc["file_exists"] is True
        assert doc["file_size_bytes"] > 0
        assert len(doc["sha256"]) == 64
        assert doc["is_synthetic"] is False


def test_task2_extraction_and_ocr_fallback() -> None:
    rep = run_extraction_pipeline()
    assert rep["total_extracted_units"] == 271  # 71 WHO pages + 100 FDA Recalls + 100 FDA NDC
    assert rep["usable_units"] == 269  # 2 blank pages in WHO PDF trigger OCR fallback
    assert rep["ocr_fallback_engine"] == "baidu/Unlimited-OCR"
    assert (EXTRACTION_DIR / "extracted_documents.json").exists()
    assert (REPO_ROOT / "lakehouse" / "gold" / "gold_rag_knowledge_corpus.csv").exists()

    who_stats = next(s for s in rep["source_breakdown"] if s["document_id"] == "DOC-WHO-EML-2023")
    assert who_stats["total_pages"] == 71
    assert who_stats["ocr_fallback_triggered_pages"] == 2
    assert who_stats["ocr_fallback_engine"] == "baidu/Unlimited-OCR"


def test_task3_chunking_and_embeddings() -> None:
    chk = run_chunking_pipeline()
    assert chk["total_chunks_generated"] >= 269
    assert (CHUNKING_DIR / "chunks.json").exists()

    emb = build_embeddings_index()
    assert emb["num_vectors"] == chk["total_chunks_generated"]
    assert emb["embedding_dimension"] > 0

    mat = np.load(CHUNKING_DIR / "embeddings_matrix.npy")
    assert mat.shape == (emb["num_vectors"], emb["embedding_dimension"])
    # Verify unit-norm normalization
    norms = np.linalg.norm(mat, axis=1)
    assert np.allclose(norms[norms > 0], 1.0, atol=1e-4)


def test_task4_grounded_retrieval_and_citations() -> None:
    # 1. Recall query
    res_recall = ask_question(
        "What caused the recall of Progesterone 100 mg/mL in Corn Oil Injection (D-321-2016)?"
    )
    assert res_recall["status"] == "answered"
    assert len(res_recall["sources"]) >= 1
    assert res_recall["sources"][0]["document_id"] == "DOC-FDA-ENF-20261102"
    assert res_recall["sources"][0]["page"] == 1
    assert "Sterility" in res_recall["answer"]

    # 2. WHO EML PDF query
    res_who = ask_question(
        "How does the WHO Essential Medicines List classify antibiotics under the AWaRe framework?"
    )
    assert res_who["status"] == "answered"
    assert any(
        s["document_id"] == "DOC-WHO-EML-2023" and s["page"] == 11
        for s in res_who["sources"]
    )

    # 3. Unsupported Egyptian live stock/price query -> must return no_answer
    res_no = ask_question(
        "What is the current live stock inventory and retail price in EGP of Panadol in Cairo pharmacies?"
    )
    assert res_no["status"] == "no_answer"
    assert res_no["sources"] == []


def test_task5_evaluation_benchmark() -> None:
    ev = run_rag_evaluation()
    metrics = ev["metrics"]
    assert metrics["overall_status_accuracy"] >= 0.90
    assert metrics["document_hit_rate_at_3"] >= 0.90
    assert metrics["unsupported_query_rejection_rate"] == 1.0
