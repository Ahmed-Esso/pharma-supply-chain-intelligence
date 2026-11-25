"""
Task 4 (ClickUp ID: 123u8tyngk4) — Implement retrieval, grounded answers, and citations

Provides:
- `retrieve_chunks(query, top_k, document_type_filter, deduplicate_pages)`: Hybrid dense
  semantic + word/char n-gram cosine similarity search with IDF-weighted entity overlap
  and bilingual Arabic -> English pharmaceutical term expansion.
- `ask_question(query, top_k, min_score)`: Member 4 integration contract returning
  `status` ("answered" | "no_answer"), grounded `answer` with inline citations,
  and traceable `sources` (`document_id`, `title`, `page`, `url`, `excerpt`, `score`).
"""

from __future__ import annotations

import os
import pickle
import re
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

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
    "having", "both", "classify", "framework", "caused", "current", "today",
    "right", "market", "stock", "index", "rate", "exchange",
    "dosage", "form", "forms", "indication", "indications", "first", "second",
    "choice", "active", "ingredient", "ingredients", "manufacturer", "labeler",
    "warning", "warnings", "reason", "reasons", "strength", "strengths",
}

ARABIC_STOPWORDS = {
    "ما", "ماذا", "هو", "هي", "هم", "هل", "كيف", "لماذا", "متى", "اين",
    "من", "في", "على", "عن", "الى", "مع", "او", "كل", "اي", "بين", "تحت",
    "عند", "سبب", "اسباب", "دواء", "ادويه", "عقار", "مستحضر", "قائمه",
    "منظمه", "الصحه", "العالميه", "الاساسيه", "اداره", "الغذاء", "الدواء",
    "والدواء", "الامريكيه", "الموصى", "بها", "تصنف", "تصنيف", "تحذير",
    "تحذيرات", "اذكر", "وضح", "اخبرني", "علاج", "الادويه", "مجموعه",
    "اطار", "وفقا", "ل", "عنها", "التي", "الذي", "هذا", "هذه",
}

# Normalized Arabic (أ/إ/آ -> ا, ة -> ه, ى -> ي) regulatory & pharma glossary
ARABIC_PHARMA_GLOSSARY: Dict[str, str] = {
    "ممارسات التصنيع الجيده": "cgmp",
    "مضادات التسمم": "antidotes poisonings 4.2",
    "مضادات حيويه": "antibacterials aware access watch reserve",
    "معقم اليدين": "hand sanitizer",
    "اسيتيل سيستئين": "acetylcysteine",
    "اسيتيل سيستين": "acetylcysteine",
    "التهاب رئوي": "pneumonia",
    "الالتهاب الرئوي": "pneumonia",
    "بروجسترون": "progesterone",
    "اموكسيسيلين": "amoxicillin",
    "اموكسيسلين": "amoxicillin",
    "باراسيتامول": "paracetamol",
    "اسيتامينوفين": "acetaminophen",
    "فالبرويك": "valproic sodium valproate",
    "فالبروات": "valproate valproic",
    "ايبوبروفين": "ibuprofen",
    "تادالافيل": "tadalafil",
    "باكليتاكسيل": "paclitaxel",
    "اتروبين": "atropine",
    "نالوكسون": "naloxone",
    "كافور": "camphor",
    "منثول": "menthol",
    "ميثانول": "methanol",
    "ايثانول": "ethanol",
    "زنك": "zinc oxide",
    "كوات": "koate antihemophilic",
    "استدعاء": "recall",
    "سحب": "recall",
    "تعقيم": "sterility",
    "عقامه": "sterility",
    "تلوث": "contamination impurity",
    "شوائب": "impurity contamination",
    "ترياق": "antidotes poisonings",
    "تسمم": "poisonings antidotes",
    "حمل": "pregnancy birth defects",
}

UNSUPPORTED_LIVE_MARKET_PATTERNS = [
    r"\begypt(?:ian)?\s+(?:pharmacy|pharmacies|market|retail|stock|inventory|price|prices|pounds)\b",
    r"\b(?:current|live|real[- ]time)\s+(?:stock|inventory|availability)\b",
    r"\b(?:retail|pharmacy|current|live)\s+price(?:s)?\b",
    r"\bprice(?:s)?\s+(?:of|for|in)\b",
    r"\b(?:cost|costs|priced)\s+(?:of|in)\b",
    r"\bhow\s+much\s+(?:does|do|is)\b.*\b(?:cost|price)\b",
    r"\b(?:in|at)\s+[a-z]+\s+pharmacies\b",
    r"\b(?:egp|usd|eur|gbp|sar|aed)\b.*\b(?:price|cost|pharmacy|pharmacies)\b",
    r"(?:سعر|أسعار|اسعار|تكلفة|بكام|بكم)\s+",
    r"رصيد\s+المخزون",
    r"(?:مخزون|متوفر|توافر).*(?:صيدلي|اليوم|الآن|الان)",
    r"في\s+صيدليات",
]


def _normalize_arabic(text: str) -> str:
    cleaned = re.sub(r"[\u064B-\u065F\u0670]", "", text)
    cleaned = re.sub(r"[أإآ]", "ا", cleaned)
    cleaned = cleaned.replace("ة", "ه").replace("ى", "ي")
    return cleaned


def _strip_arabic_al(word: str) -> str:
    if word.startswith("وال") and len(word) > 4:
        return word[3:]
    if word.startswith("بال") and len(word) > 4:
        return word[3:]
    if word.startswith("لال") and len(word) > 4:
        return word[3:]
    if word.startswith("ال") and len(word) > 3:
        return word[2:]
    return word


def _expand_bilingual_query(query: str) -> Tuple[str, set]:
    """
    If the query contains Arabic text, map known pharmaceutical/regulatory terms
    to English and return (expanded_query, mapped_normalized_arabic_tokens).
    Unmapped non-stopword Arabic words remain intact so unsupported Arabic
    questions still fail retrieval rather than falsely matching.
    """
    if not re.search(r"[\u0600-\u06FF]", query):
        return query, set()

    norm_full = _normalize_arabic(query)
    ar_words = re.findall(r"[\u0621-\u064A]+", norm_full)
    ar_stemmed = [_strip_arabic_al(w) for w in ar_words]
    stemmed_phrase = " ".join(ar_stemmed)

    expansions: List[str] = []
    mapped_tokens: set = set()

    for ar_key, en_val in ARABIC_PHARMA_GLOSSARY.items():
        if " " in ar_key:
            if ar_key in norm_full or ar_key in stemmed_phrase:
                expansions.append(en_val)
                for part in ar_key.split():
                    mapped_tokens.add(part)
        else:
            for orig_w, stem_w in zip(ar_words, ar_stemmed):
                if orig_w == ar_key or stem_w == ar_key:
                    expansions.append(en_val)
                    mapped_tokens.add(orig_w)
                    mapped_tokens.add(stem_w)

    expanded_query = f"{query} {' '.join(expansions)}".strip() if expansions else query
    return expanded_query, mapped_tokens


def _extract_meaningful_tokens(text: str) -> List[str]:
    expanded_text, mapped_ar = _expand_bilingual_query(text)
    t_low = expanded_text.lower()

    # Preserve compound alphanumeric identifiers (e.g., D-321-2016, 76176-135) & section numbers (4.2)
    codes = re.findall(r"\b[a-z0-9]+-[0-9][a-z0-9\-]*\b", t_low)
    sections = re.findall(r"\b\d+\.\d+(?:\.\d+)*\b", t_low)
    stripped = re.sub(r"\b[a-z0-9]+-[0-9][a-z0-9\-]*\b", " ", t_low)
    stripped = re.sub(r"\b\d+\.\d+(?:\.\d+)*\b", " ", stripped)

    # Split remaining hyphenated modifiers (e.g., first-choice -> first, choice)
    latin_words = re.findall(r"[a-z0-9]{2,}", stripped.replace("-", " "))

    # Keep unmapped, non-stopword Arabic words so irrelevant Arabic queries won't match
    unmapped_ar: List[str] = []
    for raw_ar in re.findall(r"[\u0621-\u064A]{2,}", _normalize_arabic(expanded_text)):
        norm_ar = _normalize_arabic(raw_ar)
        stem_ar = _strip_arabic_al(norm_ar)
        if (
            norm_ar in mapped_ar
            or stem_ar in mapped_ar
            or norm_ar in ARABIC_STOPWORDS
            or stem_ar in ARABIC_STOPWORDS
        ):
            continue
        unmapped_ar.append(norm_ar)

    ordered_tokens: List[str] = []
    for tok in codes + sections + latin_words + unmapped_ar:
        if tok in STOPWORDS or tok in ARABIC_STOPWORDS:
            continue
        if tok not in ordered_tokens:
            ordered_tokens.append(tok)
    return ordered_tokens


class RAGPipeline:
    """End-to-end Retrieval-Augmented Generation pipeline with strict citation grounding."""

    def __init__(self, index_path: Optional[Path] = None) -> None:
        self.index_path = index_path or (CHUNKING_DIR / "vector_index.pkl")
        if not self.index_path.exists():
            build_embeddings_index()
        with open(self.index_path, "rb") as f:
            self.bundle = pickle.load(f)

        self.backend = self.bundle.get("backend", "sklearn-lsa")
        self.word_vectorizer = self.bundle["word_vectorizer"]
        self.char_vectorizer = self.bundle["char_vectorizer"]
        self.svd_model = self.bundle.get("svd_model")
        self.word_tfidf_matrix = self.bundle["word_tfidf_matrix"]
        self.char_tfidf_matrix = self.bundle["char_tfidf_matrix"]
        self.dense_embeddings = self.bundle["dense_embeddings"]
        self.chunks: List[Dict[str, Any]] = self.bundle["chunks"]
        self._st_model = None

        self.vocab = self.word_vectorizer.vocabulary_
        self.idf = self.word_vectorizer.idf_

    def _token_importance(self, token: str) -> float:
        """Return IDF importance weight for a query token; OOV tokens get high weight."""
        if token in self.vocab:
            return float(self.idf[self.vocab[token]])
        return 8.0

    def _encode_dense_query(self, query_text: str, q_word_vec: Any) -> np.ndarray:
        if self.backend == "sentence-transformers" or self.svd_model is None:
            try:
                if self._st_model is None:
                    from sentence_transformers import SentenceTransformer

                    model_id = self.bundle.get("model_name", "sentence-transformers/all-MiniLM-L6-v2")
                    model_id = model_id.replace("sentence-transformers/", "", 1)
                    self._st_model = SentenceTransformer(model_id)
                vec = np.asarray(
                    self._st_model.encode([query_text], normalize_embeddings=True),
                    dtype=np.float32,
                )
                return vec.ravel()
            except ImportError:
                return np.zeros(self.dense_embeddings.shape[1], dtype=np.float32)

        q_lsa = self.svd_model.transform(q_word_vec)
        return normalize(q_lsa, norm="l2").astype(np.float32).ravel()

    def retrieve(
        self,
        query: str,
        top_k: int = 4,
        document_type_filter: Optional[str] = None,
        deduplicate_pages: bool = True,
    ) -> List[Dict[str, Any]]:
        """
        Compute hybrid similarity (Word TF-IDF + Char N-Gram TF-IDF + Dense Cosine
        + IDF-weighted entity/identifier overlap) and return the top_k ranked chunks.
        """
        q_clean = query.strip()
        if not q_clean:
            return []

        expanded_query, _ = _expand_bilingual_query(q_clean)
        q_word_vec = self.word_vectorizer.transform([expanded_query])
        q_char_vec = self.char_vectorizer.transform([expanded_query])
        q_dense = self._encode_dense_query(expanded_query, q_word_vec)

        word_sims = cosine_similarity(q_word_vec, self.word_tfidf_matrix).ravel()
        char_sims = cosine_similarity(q_char_vec, self.char_tfidf_matrix).ravel()
        dense_sims = np.dot(self.dense_embeddings, q_dense)

        hybrid_scores = (
            (0.45 * word_sims)
            + (0.20 * char_sims)
            + (0.15 * np.maximum(0.0, dense_sims))
        )

        q_tokens = _extract_meaningful_tokens(q_clean)
        token_weights = {t: self._token_importance(t) for t in q_tokens}
        total_weight = sum(token_weights.values()) or 1.0

        q_lower = expanded_query.lower()
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
            # Match against actual chunk body + section_hint (not generic document title)
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
        if not deduplicate_pages:
            return results[:top_k]

        deduped: List[Dict[str, Any]] = []
        seen_pages = set()
        for r in results:
            key = (r["document_id"], r["page"])
            if key in seen_pages:
                continue
            seen_pages.add(key)
            deduped.append(r)
            if len(deduped) >= top_k:
                break
        return deduped

    def _is_unsupported_query(self, query: str) -> Optional[str]:
        q_lower = query.lower()
        for pat in UNSUPPORTED_LIVE_MARKET_PATTERNS:
            if re.search(pat, q_lower):
                return (
                    "The available verified documents (WHO Essential Medicines List 2023 and U.S. openFDA "
                    "Enforcement/NDC records) do not contain live local or international pharmacy inventory, "
                    "retail drug pricing (in EGP or any currency), or real-time stock levels. Per project data "
                    "governance rules (Zero-Mock Policy), the system will not fabricate or guess market figures."
                )
        return None

    def _build_focused_snippet(
        self, excerpt: str, matched_terms: List[str]
    ) -> str:
        excerpt_lines = [
            ln.strip()
            for ln in excerpt.splitlines()
            if ln.strip()
            and not ln.strip().startswith("WHO Model List of Essential Medicines")
            and not ln.strip().startswith("[WHO Model List of Essential Medicines")
        ]
        if not excerpt_lines:
            return ""

        if len(excerpt_lines) > 12 and matched_terms:
            first_match_idx: Optional[int] = None
            for i, ln in enumerate(excerpt_lines):
                ln_low = ln.lower()
                if any(term in ln_low for term in matched_terms):
                    first_match_idx = i
                    break

            if first_match_idx is not None and first_match_idx > 1:
                start = max(1, first_match_idx - 1)
                window = [excerpt_lines[0]] + excerpt_lines[start : start + 13]
            else:
                window = excerpt_lines[:12]
        else:
            window = excerpt_lines[:12]

        summary_snippet = " | ".join(window)
        if len(summary_snippet) > 800:
            summary_snippet = summary_snippet[:797] + "..."
        return summary_snippet

    def _try_llm_synthesis(
        self, query: str, supporting: List[Dict[str, Any]]
    ) -> Optional[str]:
        if os.environ.get("RAG_ENABLE_LLM", "").strip().lower() not in {"1", "true", "yes"}:
            return None
        api_key = os.environ.get("OPENAI_API_KEY", "").strip()
        if not api_key or api_key == "your_openai_api_key_here":
            return None

        try:
            from openai import OpenAI

            context_blocks = "\n\n".join(
                f"[{s['document_id']}, p. {s['page']}] ({s['title']}):\n{s['excerpt']}"
                for s in supporting
            )
            client = OpenAI(api_key=api_key)
            resp = client.chat.completions.create(
                model=os.environ.get("LLM_MODEL", "gpt-4o-mini"),
                temperature=0.0,
                messages=[
                    {
                        "role": "system",
                        "content": (
                            "You are a pharmaceutical regulatory assistant. Answer ONLY using the "
                            "provided evidence snippets. Cite every claim inline as [DOCUMENT_ID, p. X]. "
                            "Never invent stock levels, prices, or external facts."
                        ),
                    },
                    {
                        "role": "user",
                        "content": f"Question: {query}\n\nVerified Evidence:\n{context_blocks}",
                    },
                ],
            )
            content = resp.choices[0].message.content
            return content.strip() if content else None
        except Exception:
            return None

    def _synthesize_grounded_answer(
        self, query: str, top_chunks: List[Dict[str, Any]]
    ) -> str:
        """
        Construct a clear, concise, citation-backed answer strictly from the top
        retrieved chunks (using optional OpenAI synthesis if explicitly enabled,
        otherwise deterministic query-focused evidence formatting).
        """
        supporting = top_chunks[:3]

        llm_answer = self._try_llm_synthesis(query, supporting)
        if llm_answer:
            return llm_answer

        lines: List[str] = [
            "Based on the verified regulatory documents in the knowledge corpus:"
        ]

        for src in supporting:
            doc_id = src["document_id"]
            page = src["page"]
            title = src["title"]
            summary_snippet = self._build_focused_snippet(
                src["excerpt"], src.get("matched_terms", [])
            )
            lines.append(
                f"- **{title}** (Source `{doc_id}`, Page/Record {page}): {summary_snippet} "
                f"[{doc_id}, p. {page}]"
            )

        return "\n".join(lines)

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
                    "Excludes live pharmacy market stock and retail prices."
                ),
                "sources": [],
            }

        # 2. Retrieve candidate chunks (deduplicated by document/page)
        candidates = self.retrieve(q_clean, top_k=top_k, deduplicate_pages=True)
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

        qualified_candidates = [
            c
            for c in candidates
            if c["score"] >= min_score and (not q_tokens or len(c["matched_terms"]) > 0)
        ]

        answer_text = self._synthesize_grounded_answer(q_clean, qualified_candidates)

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
            for c in qualified_candidates
        ]

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
    deduplicate_pages: bool = True,
) -> List[Dict[str, Any]]:
    """Public helper for retrieving top-k chunks."""
    return _get_pipeline().retrieve(
        query=query,
        top_k=top_k,
        document_type_filter=document_type_filter,
        deduplicate_pages=deduplicate_pages,
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
