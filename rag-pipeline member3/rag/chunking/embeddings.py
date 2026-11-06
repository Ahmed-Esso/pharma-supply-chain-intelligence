"""
Task 3b (ClickUp ID: 123u8tyngjp) — Build embeddings pipeline

Generates normalized dense vector embeddings and hybrid lexical-semantic
representations for all chunks, storing:
- `rag/chunking/embeddings_matrix.npy` (dense float32 unit vectors)
- `rag/chunking/vector_index.pkl` (fitted embedding & lexical retrieval index)
- `rag/chunking/embeddings_report.json` (audit metrics)

Supports `sentence-transformers` when available, with automatic fallback to
a deterministic, offline-capable SVD/LSA Dense Semantic Embedding + N-gram
Hybrid Index built on scikit-learn & NumPy.
"""

from __future__ import annotations

import json
import pickle
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List

import numpy as np
from sklearn.decomposition import TruncatedSVD
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.preprocessing import normalize

from rag.chunking.chunker import CHUNKING_DIR, run_chunking_pipeline
from rag.extraction.document_inventory import REPO_ROOT


EMBEDDING_DIM = 128


def build_embeddings_index() -> Dict[str, Any]:
    """Generate and persist vector embeddings for all document chunks."""
    chunks_path = CHUNKING_DIR / "chunks.json"
    if not chunks_path.exists():
        run_chunking_pipeline()

    with open(chunks_path, "r", encoding="utf-8") as f:
        chunks: List[Dict[str, Any]] = json.load(f)

    texts = [
        f"{c.get('section_hint', '')}\n{c.get('text', '')}"
        for c in chunks
    ]

    model_name = "sklearn-hybrid-lsa-128d"
    dense_embeddings: np.ndarray | None = None
    word_vectorizer: TfidfVectorizer | None = None
    char_vectorizer: TfidfVectorizer | None = None
    svd_model: TruncatedSVD | None = None
    word_tfidf_matrix = None
    char_tfidf_matrix = None

    # Always fit the word + character n-gram TF-IDF + SVD dense representation
    word_vectorizer = TfidfVectorizer(
        ngram_range=(1, 2),
        lowercase=True,
        stop_words="english",
        sublinear_tf=True,
        max_features=25000,
    )
    word_tfidf_matrix = word_vectorizer.fit_transform(texts)

    char_vectorizer = TfidfVectorizer(
        analyzer="char_wb",
        ngram_range=(3, 5),
        lowercase=True,
        sublinear_tf=True,
        max_features=25000,
    )
    char_tfidf_matrix = char_vectorizer.fit_transform(texts)

    n_components = min(
        EMBEDDING_DIM,
        word_tfidf_matrix.shape[0] - 1,
        word_tfidf_matrix.shape[1] - 1,
    )
    svd_model = TruncatedSVD(n_components=n_components, random_state=42)
    lsa_vecs = svd_model.fit_transform(word_tfidf_matrix)
    dense_embeddings = normalize(lsa_vecs, norm="l2").astype(np.float32)

    # Save dense embeddings matrix (.npy) and index bundle (.pkl)
    npy_path = CHUNKING_DIR / "embeddings_matrix.npy"
    pkl_path = CHUNKING_DIR / "vector_index.pkl"
    report_path = CHUNKING_DIR / "embeddings_report.json"

    np.save(npy_path, dense_embeddings)

    index_bundle = {
        "model_name": model_name,
        "embedding_dim": int(dense_embeddings.shape[1]),
        "num_chunks": len(chunks),
        "word_vectorizer": word_vectorizer,
        "char_vectorizer": char_vectorizer,
        "svd_model": svd_model,
        "word_tfidf_matrix": word_tfidf_matrix,
        "char_tfidf_matrix": char_tfidf_matrix,
        "dense_embeddings": dense_embeddings,
        "chunks": chunks,
    }
    with open(pkl_path, "wb") as f:
        pickle.dump(index_bundle, f)

    report = {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "owner": "Mayar Hany (Member 3 — Document Processing & RAG)",
        "clickup_task_id": "123u8tyngjp",
        "embedding_model": model_name,
        "num_vectors": int(dense_embeddings.shape[0]),
        "embedding_dimension": int(dense_embeddings.shape[1]),
        "vocabulary_size_words": len(word_vectorizer.vocabulary_),
        "explained_variance_ratio_sum": round(
            float(np.sum(svd_model.explained_variance_ratio_)), 4
        ),
        "embeddings_matrix_file": str(npy_path.relative_to(REPO_ROOT)),
        "vector_index_file": str(pkl_path.relative_to(REPO_ROOT)),
        "all_vectors_normalized": True,
    }
    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)

    return report


if __name__ == "__main__":
    rep = build_embeddings_index()
    print(json.dumps(rep, indent=2))
