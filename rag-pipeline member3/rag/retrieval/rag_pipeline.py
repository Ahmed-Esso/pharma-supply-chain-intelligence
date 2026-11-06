"""
Task 4 (ClickUp ID: 123u8tyngk4) — Implement retrieval, grounded answers, and citations

Provides:
- `retrieve_chunks(query, top_k, document_type_filter)`: Hybrid dense SVD semantic +
  word/char n-gram cosine similarity search with IDF-weighted entity overlap.
- `ask_question(query, top_k, min_score)`: Member 4 integration contract returning
  `status` ("answered" | "no_answer"), grounded `answer` with inline citations,
  and traceable `sources` (`document_id`, `title`, `page`, `url`, `excerpt`, `score`).
"""

from __future__ import annotations

import os
import pickle
import re
from pathlib import Path
from typing import Any, Dict, List, Optional

import numpy as np
from sklearn.metrics.pairwise import cosine_similarity
from sklearn.preprocessing import normalize

from rag.chunking.chunker import CHUNKING_DIR
from rag.chunking.embeddings import build_embeddings_index

RETRIEVAL_DIR = Path(__file__).resolve().parent
DEFAULT_MIN_SCORE = 0.25

STOPWORDS = {
    "what", "why", "how", "when", "where", "which", "who", "whom", "whose",
    "is", "are", "was", "were", "be", "been", "being", "have", "has", "had",
    "do", "does", "did", "can", "could", "will", "would", "should", "may",
    "might", "must", "the", "a", "an", "in", "on", "at", "to", "for", "of",
    "with", "by", "from", "about", "as", "into", "like", "through", "after",
    "over", "between", "out", "against", "during", "without", "before",
    "under", "around", "among", "and", "or", "but", "if", "because", "this",
    "that", "these", "those", "there", "their", "they", "it", "its", "tell",
    "me", "give", "show", "list", "please", "any", "all", "some", "many",
    "much", "more", "most", "other", "such", "no", "nor", "not", "only",
    "own", "same", "so", "than", "too", "very", "just", "now", "also",
    "drug", "drugs", "medicine", "medicines", "pharmaceutical", "product",
    "products", "information", "details", "report", "documents", "document",
    "essential", "model", "fda", "openfda", "ndc", "recall", "recalled",
    "number", "section", "listed", "recommended", "given", "warn", "against",
    "having", "both", "under", "classify", "framework", "caused", "current",
    "today", "right", "now", "market", "stock", "index", "rate", "exchange",
}

UNSUPPORTED_LIVE_MARKET_PATTERNS = [
    r"\begypt(?:ian)?\s+(?:pharmacy|market|retail|stock|inventory|price|prices|pounds)\b",
    r"\b(?:current|live|real[- ]time)\s+(?:stock|inventory|availability)\s+in\s+(?:cairo|alexandria|egypt)\b",
    r"\bhow\s+much\s+does\b.*\bcost\b",
    r"\bprice\s+in\s+egp\b",
    r"\bcairo\s+pharmacies\b",
    r"\bسعر\b.*\bفي\s+مصر\b",
    r"\bرصيد\s+المخزون\b",
]


def _extract_meaningful_tokens(text: str) -> List[str]:
    tokens = re.findall(r"[a-zA-Z0-9][a-zA-Z0-9\-]{1,}", text.lower())
    return [t for t in tokens if t not in STOPWORDS]


class RAGPipeline:
    """End-to-end Retrieval-Augmented Generation pipeline with strict citation grounding."""

    def __init__(self, index_path: Optional[Path] = None) -> None:
        self.index_path = index_path or (CHUNKING_DIR / "vector_index.pkl")
        if not self.index_path.exists():
            build_embeddings_index()
        with open(self.index_path, "rb") as f:
            self.bundle = pickle.load(f)

        self.word_vectorizer = self.bundle["word_vectorizer"]
        self.char_vectorizer = self.bundle["char_vectorizer"]
        self.svd_model = self.bundle["svd_model"]
        self.word_tfidf_matrix = self.bundle["word_tfidf_matrix"]
        self.char_tfidf_matrix = self.bundle["char_tfidf_matrix"]
        self.dense_embeddings = self.bundle["dense_embeddings"]
        self.chunks: List[Dict[str, Any]] = self.bundle["chunks"]

        self.vocab = self.word_vectorizer.vocabulary_
        self.idf = self.word_vectorizer.idf_

    def _token_importance(self, token: str) -> float:
        """Return IDF importance weight for a query token; OOV tokens get high weight."""
        if token in self.vocab:
            return float(self.idf[self.vocab[token]])
        return 8.0

    def retrieve(
        self,
        query: str,
        top_k: int = 4,
        document_type_filter: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """
        Compute hybrid similarity (Word TF-IDF + Char N-Gram TF-IDF + Dense SVD Cosine
        + IDF-weighted entity/identifier overlap) and return the top_k ranked chunks.
        """
        q_clean = query.strip()
        if not q_clean:
            return []

        q_word_vec = self.word_vectorizer.transform([q_clean])
        q_char_vec = self.char_vectorizer.transform([q_clean])
        q_lsa = self.svd_model.transform(q_word_vec)
        q_dense = normalize(q_lsa, norm="l2").astype(np.float32)

        word_sims = cosine_similarity(q_word_vec, self.word_tfidf_matrix).ravel()
        char_sims = cosine_similarity(q_char_vec, self.char_tfidf_matrix).ravel()
        dense_sims = np.dot(self.dense_embeddings, q_dense.ravel())

        hybrid_scores = (
            (0.45 * word_sims)
            + (0.20 * char_sims)
            + (0.15 * np.maximum(0.0, dense_sims))
        )

        q_tokens = _extract_meaningful_tokens(q_clean)
        token_weights = {t: self._token_importance(t) for t in q_tokens}
        total_weight = sum(token_weights.values()) or 1.0

        q_lower = q_clean.lower()
        intent_is_recall = any(
            w in q_lower
            for w in ["recall", "recalled", "enforcement", "sterility", "cgmp", "d-"]
        )
        intent_is_who = any(
            w in q_lower
            for w in [
                "who ", "essential", "aware", "access group", "watch group",
                "reserve group", "first-choice", "first choice", "antidotes",
            ]
        )
        intent_is_ndc = any(
            w in q_lower for w in ["ndc", "labeler", "manufacturer/labeler"]
        )

        results: List[Dict[str, Any]] = []
        for idx, chunk in enumerate(self.chunks):
            if document_type_filter and chunk["document_type"] != document_type_filter:
                continue

            base_score = float(hybrid_scores[idx])
            body_lines = [
                ln for ln in chunk["text"].splitlines()
                if not ln.startswith("[WHO Model List of Essential Medicines")
                and not ln.strip().startswith("WHO Model List of Essential Medicines")
            ]
            body_lower = (chunk.get("section_hint", "") + "\n" + "\n".join(body_lines)).lower()

            matched_tokens = [t for t in q_tokens if t in body_lower]
            matched_weight = sum(token_weights[t] for t in matched_tokens)
            weighted_overlap = matched_weight / total_weight if q_tokens else 0.0

            if q_tokens and len(matched_tokens) == 0:
                score = base_score * 0.15
            else:
                score = base_score + (0.35 * weighted_overlap)

            doc_type = chunk["document_type"]
            if intent_is_recall and doc_type == "JSON_REGULATORY_RECALLS" and matched_tokens:
                score += 0.05
            elif intent_is_who and doc_type == "PDF_REGULATORY_GUIDELINE" and matched_tokens:
                score += 0.05
            elif intent_is_ndc and doc_type == "JSON_DRUG_CATALOG" and matched_tokens:
                score += 0.05

            results.append(
                {
                    "chunk_id": chunk["chunk_id"],
                    "document_id": chunk["document_id"],
                    "title": chunk["title"],
                    "publisher": chunk["publisher"],
                    "page": chunk["page_number"],
                    "url": chunk["source_url"],
                    "document_type": doc_type,
                    "section_hint": chunk.get("section_hint", ""),
                    "score": round(min(score, 1.0), 4),
                    "matched_terms": matched_tokens,
                    "weighted_overlap": round(weighted_overlap, 4),
                    "excerpt": chunk["text"],
                    "metadata_extra": chunk.get("metadata_extra", {}),
                }
            )

        results.sort(key=lambda r: r["score"], reverse=True)
        return results[:top_k]

    def _is_unsupported_query(self, query: str) -> Optional[str]:
        q_lower = query.lower()
        for pat in UNSUPPORTED_LIVE_MARKET_PATTERNS:
            if re.search(pat, q_lower):
                return (
                    "The available verified documents (WHO Essential Medicines List 2023 and U.S. openFDA "
                    "Enforcement/NDC records) do not contain live Egyptian pharmacy inventory, local retail "
                    "drug pricing in EGP, or real-time local stock levels. Per project data governance rules "
                    "(Zero-Mock Policy), the system will not fabricate or guess market figures."
                )
        return None

    def _try_llm_grounded_generation(
        self, query: str, top_chunks: List[Dict[str, Any]]
    ) -> Optional[str]:
        """
        If an LLM API key (OPENAI_API_KEY / GROQ_API_KEY) or local Ollama is configured,
        generate a natural, reasoning-based answer strictly grounded in top_chunks.
        """
        api_key = os.getenv("OPENAI_API_KEY", "").strip()
        if not api_key or api_key == "your_openai_api_key_here":
            return None

        try:
            from openai import OpenAI

            client = OpenAI(api_key=api_key)
            context_blocks = []
            for idx, c in enumerate(top_chunks[:3], start=1):
                context_blocks.append(
                    f"[Source {idx}: {c['document_id']}, Page/Record {c['page']} — {c['title']}]\n{c['excerpt']}"
                )
            context_str = "\n\n".join(context_blocks)
            resp = client.chat.completions.create(
                model=os.getenv("LLM_MODEL", "gpt-4o-mini"),
                temperature=0.0,
                messages=[
                    {
                        "role": "system",
                        "content": (
                            "You are a Pharmaceutical Supply Chain & Regulatory RAG Assistant. "
                            "Answer the user's question directly, accurately, and concisely using ONLY "
                            "the provided retrieved source excerpts. Always include inline citations in "
                            "the format [DOC_ID, p. X]. Never invent facts outside the provided excerpts."
                        ),
                    },
                    {
                        "role": "user",
                        "content": f"Question: {query}\n\nRetrieved Evidence:\n{context_str}",
                    },
                ],
            )
            return (resp.choices[0].message.content or "").strip() or None
        except Exception:
            return None

    def _synthesize_grounded_answer(
        self, query: str, top_chunks: List[Dict[str, Any]]
    ) -> str:
        """
        Synthesize a query-focused, citation-backed answer from the top retrieved chunks.
        Uses live LLM reasoning if configured in `.env`, or performs question-intent
        and token-relevance analysis over the retrieved evidence sentences.
        """
        llm_answer = self._try_llm_grounded_generation(query, top_chunks)
        if llm_answer:
            return llm_answer

        q_lower = query.lower()
        q_tokens = _extract_meaningful_tokens(query)
        primary = top_chunks[0]
        doc_id = primary["document_id"]
        page = primary["page"]

        # 1. Question-Intent Reasoning for Structured FDA Recall Records
        if "FDA Drug Recall Report" in primary["excerpt"]:
            fields: Dict[str, str] = {}
            for ln in primary["excerpt"].splitlines():
                if ":" in ln:
                    parts = [p.strip() for p in ln.split("|")]
                    for part in parts:
                        if ":" in part:
                            k, v = part.split(":", 1)
                            fields[k.strip()] = v.strip()

            recall_no = fields.get("FDA Drug Recall Report — Recall Number", "N/A")
            firm = fields.get("Recalling Firm", "N/A")
            product = fields.get("Recalled Product Description", "N/A")
            reason = fields.get("Reason for Recall", "N/A")
            classification = fields.get("Classification", "N/A")
            status = fields.get("Status", "N/A")
            init_date = fields.get("Recall Initiation Date", "N/A")
            lot_info = fields.get("Lot / Code Information", "N/A")

            if any(w in q_lower for w in ["why", "reason", "cause", "caused"]):
                return (
                    f"**Recall Reason ({recall_no}):** {reason}\n"
                    f"- **Recalled Product:** {product}\n"
                    f"- **Recalling Firm:** {firm} | **Classification:** {classification} ({status})\n"
                    f"- **Lot / Code Info:** {lot_info} [{doc_id}, p. {page}]"
                )
            if any(w in q_lower for w in ["who", "firm", "company", "manufacturer"]):
                return (
                    f"**Recalling Firm:** {firm} initiated Recall **{recall_no}** ({classification}, {status}).\n"
                    f"- **Product:** {product}\n"
                    f"- **Reason:** {reason} [{doc_id}, p. {page}]"
                )
            return (
                f"**FDA Recall {recall_no}** ({classification} — {status}):\n"
                f"- **Product:** {product}\n"
                f"- **Recalling Firm:** {firm} (Initiated: {init_date})\n"
                f"- **Reason for Recall:** {reason}\n"
                f"- **Lot / Code Info:** {lot_info} [{doc_id}, p. {page}]"
            )

        # 2. Question-Intent Reasoning for Structured FDA NDC Drug Catalog Records
        if "FDA NDC Drug Directory Listing" in primary["excerpt"]:
            fields = {}
            for ln in primary["excerpt"].splitlines():
                for part in [p.strip() for p in ln.split("|")]:
                    if ":" in part:
                        k, v = part.split(":", 1)
                        fields[k.strip()] = v.strip()

            ndc_code = fields.get("FDA NDC Drug Directory Listing — Product NDC", "N/A")
            brand = fields.get("Brand Name", "N/A")
            generic = fields.get("Generic Name", "N/A")
            labeler = fields.get("Labeler / Manufacturer", "N/A")
            ingredients = fields.get("Active Ingredients & Strengths", "N/A")
            dosage = fields.get("Dosage Form", "N/A")
            packaging = fields.get("Packaging Configurations", "N/A")

            return (
                f"**{brand}** (Generic: *{generic}*, NDC: `{ndc_code}`):\n"
                f"- **Active Ingredients & Strengths:** {ingredients}\n"
                f"- **Manufacturer / Labeler:** {labeler}\n"
                f"- **Dosage Form:** {dosage}\n"
                f"- **Packaging:** {packaging} [{doc_id}, p. {page}]"
            )

        # 3. Query-Focused Line Selection for WHO Essential Medicines List PDF
        supporting = top_chunks[:2]
        output_blocks: List[str] = []
        for src in supporting:
            s_doc = src["document_id"]
            s_page = src["page"]
            raw_lines = [
                ln.strip()
                for ln in src["excerpt"].splitlines()
                if ln.strip()
                and not ln.strip().startswith("WHO Model List of Essential Medicines")
                and not ln.strip().startswith("[WHO Model List of Essential Medicines")
            ]

            # Find lines matching the query's specific terms and include surrounding context window
            hit_indices = [
                i
                for i, ln in enumerate(raw_lines)
                if any(t in ln.lower() for t in q_tokens)
            ]
            if hit_indices:
                start_i = max(0, min(hit_indices) - 1)
                end_i = min(len(raw_lines), max(hit_indices) + 8)
                selected_lines = raw_lines[start_i:end_i]
            else:
                selected_lines = raw_lines[:10]

            snippet = " | ".join(selected_lines)
            if len(snippet) > 750:
                snippet = snippet[:747] + "..."
            output_blocks.append(
                f"- **{src['title']}** (Page {s_page}): {snippet} [{s_doc}, p. {s_page}]"
            )

        return (
            "Based on the verified WHO Essential Medicines List (2023):\n"
            + "\n".join(output_blocks)
        )

    def answer_question(
        self,
        query: str,
        top_k: int = 3,
        min_score: float = DEFAULT_MIN_SCORE,
    ) -> Dict[str, Any]:
        """
        Execute full RAG flow and return the standardized dictionary agreed with Member 4.
        """
        q_clean = query.strip()
        if not q_clean:
            return {
                "query": query,
                "status": "no_answer",
                "answer": "Please provide a valid question.",
                "confidence_score": 0.0,
                "scope_disclaimer": "Evidence-grounded RAG over WHO EML 2023 & openFDA snapshots.",
                "sources": [],
            }

        # 1. Check explicit out-of-scope / unverified market data guardrails
        unsupported_reason = self._is_unsupported_query(q_clean)
        if unsupported_reason:
            return {
                "query": query,
                "status": "no_answer",
                "answer": unsupported_reason,
                "confidence_score": 0.0,
                "scope_disclaimer": (
                    "Verified scope: WHO EML 2023 (global) & U.S. openFDA Enforcement/NDC snapshots. "
                    "Excludes live Egyptian market stock and retail prices."
                ),
                "sources": [],
            }

        # 2. Retrieve candidate chunks dynamically
        candidates = self.retrieve(q_clean, top_k=top_k)
        q_tokens = _extract_meaningful_tokens(q_clean)

        if (
            not candidates
            or candidates[0]["score"] < min_score
            or (q_tokens and candidates[0].get("weighted_overlap", 0.0) < 0.20)
        ):
            return {
                "query": query,
                "status": "no_answer",
                "answer": (
                    "The available verified documents do not provide sufficient evidence to answer "
                    "this question. No answer was generated to prevent unsupported claims."
                ),
                "confidence_score": round(candidates[0]["score"], 4) if candidates else 0.0,
                "scope_disclaimer": (
                    "Verified scope: WHO EML 2023 (global) & U.S. openFDA Enforcement/NDC snapshots."
                ),
                "sources": [],
            }

        qualified_sources = [
            {
                "chunk_id": c["chunk_id"],
                "document_id": c["document_id"],
                "title": c["title"],
                "publisher": c["publisher"],
                "page": c["page"],
                "url": c["url"],
                "score": c["score"],
                "excerpt": c["excerpt"],
            }
            for c in candidates
            if c["score"] >= min_score and (not q_tokens or len(c["matched_terms"]) > 0)
        ]

        answer_text = self._synthesize_grounded_answer(q_clean, qualified_sources)

        return {
            "query": query,
            "status": "answered",
            "answer": answer_text,
            "confidence_score": qualified_sources[0]["score"],
            "scope_disclaimer": (
                "Grounded strictly in verified WHO EML 2023 and openFDA regulatory snapshots "
                "(not live local pharmacy inventory or retail pricing)."
            ),
            "sources": qualified_sources,
        }


_PIPELINE_INSTANCE: Optional[RAGPipeline] = None


def _get_pipeline() -> RAGPipeline:
    global _PIPELINE_INSTANCE
    if _PIPELINE_INSTANCE is None:
        _PIPELINE_INSTANCE = RAGPipeline()
    return _PIPELINE_INSTANCE


def retrieve_chunks(
    query: str,
    top_k: int = 4,
    document_type_filter: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """Public helper for retrieving top-k chunks."""
    return _get_pipeline().retrieve(
        query=query, top_k=top_k, document_type_filter=document_type_filter
    )


def ask_question(
    query: str,
    top_k: int = 3,
    min_score: float = DEFAULT_MIN_SCORE,
) -> Dict[str, Any]:
    """
    Primary integration entrypoint for Member 4 (API / Streamlit UI).
    Returns a dictionary with `status`, `answer`, `confidence_score`, `scope_disclaimer`, and `sources`.
    """
    return _get_pipeline().answer_question(
        query=query, top_k=top_k, min_score=min_score
    )
