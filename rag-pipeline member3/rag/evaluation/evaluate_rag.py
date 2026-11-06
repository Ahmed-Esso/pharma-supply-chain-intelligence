"""
Task 5 (ClickUp ID: 123u8tyngk5) — Evaluate RAG relevance and citation support

Runs a 12-question evaluation benchmark covering:
1. WHO Essential Medicines List 2023 (PDF page-level retrieval & citations)
2. openFDA Drug Enforcement Recall Reports (reason for recall, firm, lot codes)
3. openFDA NDC Drug Catalog (active ingredients, dosage forms, packaging)
4. Out-of-scope / unverified market data queries (verifying strict `no_answer` behavior)
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List

from rag.extraction.document_inventory import REPO_ROOT
from rag.retrieval.rag_pipeline import RAGPipeline

EVALUATION_DIR = Path(__file__).resolve().parent


def get_benchmark_questions() -> List[Dict[str, Any]]:
    """Return the curated test question bank with expected ground-truth citations."""
    return [
        {
            "question_id": "Q01",
            "category": "WHO_EML_PDF",
            "question": "How does the WHO Essential Medicines List classify antibiotics under the AWaRe stewardship framework?",
            "expected_status": "answered",
            "expected_document_id": "DOC-WHO-EML-2023",
            "expected_pages": [11],
            "expected_keywords": ["Access", "Watch", "Reserve"],
        },
        {
            "question_id": "Q02",
            "category": "WHO_EML_PDF",
            "question": "What are the recommended dosage forms and first-choice indications for amoxicillin in the WHO Essential Medicines List?",
            "expected_status": "answered",
            "expected_document_id": "DOC-WHO-EML-2023",
            "expected_pages": [12, 20],
            "expected_keywords": ["amoxicillin", "pneumonia"],
        },
        {
            "question_id": "Q03",
            "category": "WHO_EML_PDF",
            "question": "Why does WHO warn against having both 120 mg/5 mL and 125 mg/5 mL paracetamol oral liquid strengths on the same market?",
            "expected_status": "answered",
            "expected_document_id": "DOC-WHO-EML-2023",
            "expected_pages": [5],
            "expected_keywords": ["paracetamol", "confusion"],
        },
        {
            "question_id": "Q04",
            "category": "WHO_EML_PDF",
            "question": "What warning is given for valproic acid (sodium valproate) regarding pregnancy in the WHO Essential Medicines List?",
            "expected_status": "answered",
            "expected_document_id": "DOC-WHO-EML-2023",
            "expected_pages": [8, 9, 52],
            "expected_keywords": ["valproic", "pregnancy", "birth defects"],
        },
        {
            "question_id": "Q05",
            "category": "FDA_ENFORCEMENT_RECALL",
            "question": "What caused the recall of Progesterone 100 mg/mL in Corn Oil Injection under recall number D-321-2016?",
            "expected_status": "answered",
            "expected_document_id": "DOC-FDA-ENF-20261102",
            "expected_pages": [1],
            "expected_keywords": ["Sterility", "Progesterone", "Kalman"],
        },
        {
            "question_id": "Q06",
            "category": "FDA_ENFORCEMENT_RECALL",
            "question": "Why was Assured Instant Hand Sanitizer Aloe & Moisturizers recalled in Recall D-0080-2021 by Albek De Mexico?",
            "expected_status": "answered",
            "expected_document_id": "DOC-FDA-ENF-20261102",
            "expected_pages": [2],
            "expected_keywords": ["methanol", "ethanol", "CGMP"],
        },
        {
            "question_id": "Q07",
            "category": "FDA_NDC_CATALOG",
            "question": "What are the active ingredients and labeler for Vaporizing Chest Rub (NDC 76176-135)?",
            "expected_status": "answered",
            "expected_document_id": "DOC-FDA-NDC-20261102",
            "expected_pages": [2],
            "expected_keywords": ["CAMPHOR", "MENTHOL", "EUCALYPTUS"],
        },
        {
            "question_id": "Q08",
            "category": "FDA_NDC_CATALOG",
            "question": "Who is the manufacturer/labeler of Koate Antihemophilic Factor (Human) with NDC 76125-667?",
            "expected_status": "answered",
            "expected_document_id": "DOC-FDA-NDC-20261102",
            "expected_pages": [1],
            "expected_keywords": ["KEDRION", "Koate", "76125-667"],
        },
        {
            "question_id": "Q09",
            "category": "UNSUPPORTED_GUARDRAIL",
            "question": "What is the current live stock inventory and retail price in EGP of Panadol Extra in Cairo pharmacies today?",
            "expected_status": "no_answer",
            "expected_document_id": None,
            "expected_pages": [],
            "expected_keywords": [],
        },
        {
            "question_id": "Q10",
            "category": "UNSUPPORTED_GUARDRAIL",
            "question": "How much does amoxicillin cost in Egyptian pounds in the local Egyptian pharmacy market right now?",
            "expected_status": "no_answer",
            "expected_document_id": None,
            "expected_pages": [],
            "expected_keywords": [],
        },
        {
            "question_id": "Q11",
            "category": "UNSUPPORTED_GUARDRAIL",
            "question": "What is the current Bitcoin cryptocurrency exchange rate and stock market index today?",
            "expected_status": "no_answer",
            "expected_document_id": None,
            "expected_pages": [],
            "expected_keywords": [],
        },
        {
            "question_id": "Q12",
            "category": "WHO_EML_PDF",
            "question": "Which antidotes are listed in section 4.2 of the WHO Essential Medicines List for poisonings?",
            "expected_status": "answered",
            "expected_document_id": "DOC-WHO-EML-2023",
            "expected_pages": [7],
            "expected_keywords": ["acetylcysteine", "naloxone", "atropine"],
        },
    ]


def run_rag_evaluation() -> Dict[str, Any]:
    """Run all benchmark questions against RAGPipeline and compute evaluation metrics."""
    pipeline = RAGPipeline()
    questions = get_benchmark_questions()

    EVALUATION_DIR.mkdir(parents=True, exist_ok=True)
    bank_path = EVALUATION_DIR / "test_questions_bank.json"
    with open(bank_path, "w", encoding="utf-8") as f:
        json.dump(questions, f, ensure_ascii=False, indent=2)

    eval_results: List[Dict[str, Any]] = []
    status_correct_count = 0
    doc_hit_at_1_count = 0
    doc_hit_at_3_count = 0
    page_citation_hit_count = 0
    keyword_support_count = 0
    answerable_total = 0
    unanswerable_total = 0
    unanswerable_rejected_count = 0

    for q in questions:
        response = pipeline.answer_question(q["question"], top_k=3)
        actual_status = response["status"]
        expected_status = q["expected_status"]
        status_match = actual_status == expected_status
        if status_match:
            status_correct_count += 1

        sources = response.get("sources", [])
        top_doc_ids = [s["document_id"] for s in sources]
        top_pages = [s["page"] for s in sources]

        if expected_status == "answered":
            answerable_total += 1
            exp_doc = q["expected_document_id"]
            hit_1 = bool(top_doc_ids and top_doc_ids[0] == exp_doc)
            hit_3 = exp_doc in top_doc_ids
            page_hit = any(
                s["document_id"] == exp_doc and s["page"] in q["expected_pages"]
                for s in sources
            )
            combined_text = (
                response.get("answer", "")
                + " "
                + " ".join(s.get("excerpt", "") for s in sources)
            ).lower()
            kw_hit = all(kw.lower() in combined_text for kw in q["expected_keywords"])

            if hit_1:
                doc_hit_at_1_count += 1
            if hit_3:
                doc_hit_at_3_count += 1
            if page_hit:
                page_citation_hit_count += 1
            if kw_hit:
                keyword_support_count += 1

            eval_results.append(
                {
                    "question_id": q["question_id"],
                    "category": q["category"],
                    "question": q["question"],
                    "expected_status": expected_status,
                    "actual_status": actual_status,
                    "status_match": status_match,
                    "doc_hit_at_1": hit_1,
                    "doc_hit_at_3": hit_3,
                    "exact_page_or_record_cited": page_hit,
                    "keyword_evidence_verified": kw_hit,
                    "confidence_score": response.get("confidence_score", 0.0),
                    "cited_sources": [
                        {
                            "document_id": s["document_id"],
                            "page": s["page"],
                            "score": s["score"],
                        }
                        for s in sources
                    ],
                    "answer_preview": response.get("answer", "")[:300],
                }
            )
        else:
            unanswerable_total += 1
            rejected = actual_status == "no_answer" and len(sources) == 0
            if rejected:
                unanswerable_rejected_count += 1

            eval_results.append(
                {
                    "question_id": q["question_id"],
                    "category": q["category"],
                    "question": q["question"],
                    "expected_status": expected_status,
                    "actual_status": actual_status,
                    "status_match": status_match,
                    "hallucination_prevented": rejected,
                    "confidence_score": response.get("confidence_score", 0.0),
                    "cited_sources": [],
                    "answer_preview": response.get("answer", "")[:300],
                }
            )

    summary = {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "owner": "Mayar Hany (Member 3 — Document Processing & RAG)",
        "clickup_task_id": "123u8tyngk5",
        "total_questions": len(questions),
        "answerable_questions": answerable_total,
        "unanswerable_guardrail_questions": unanswerable_total,
        "metrics": {
            "overall_status_accuracy": round(status_correct_count / len(questions), 4),
            "document_hit_rate_at_1": round(doc_hit_at_1_count / max(answerable_total, 1), 4),
            "document_hit_rate_at_3": round(doc_hit_at_3_count / max(answerable_total, 1), 4),
            "exact_page_citation_accuracy": round(
                page_citation_hit_count / max(answerable_total, 1), 4
            ),
            "evidence_keyword_support_rate": round(
                keyword_support_count / max(answerable_total, 1), 4
            ),
            "unsupported_query_rejection_rate": round(
                unanswerable_rejected_count / max(unanswerable_total, 1), 4
            ),
        },
        "results": eval_results,
    }

    report_json_path = EVALUATION_DIR / "rag_evaluation_report.json"
    with open(report_json_path, "w", encoding="utf-8") as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)

    # Also write human-readable Markdown report
    md_lines = [
        "# RAG Pipeline Evaluation & Citation Verification Report",
        "",
        f"- **Owner:** Mayar Hany (Member 3 — Document Processing & RAG)",
        f"- **ClickUp Task:** `123u8tyngk5` (Evaluate RAG relevance and citation support)",
        f"- **Generated (UTC):** `{summary['generated_at_utc']}`",
        "",
        "## Summary Metrics",
        "",
        "| Metric | Score |",
        "|---|---:|",
        f"| Overall Status Accuracy (`answered` vs `no_answer`) | **{summary['metrics']['overall_status_accuracy'] * 100:.1f}%** ({status_correct_count}/{len(questions)}) |",
        f"| Document Retrieval Hit@1 | **{summary['metrics']['document_hit_rate_at_1'] * 100:.1f}%** ({doc_hit_at_1_count}/{answerable_total}) |",
        f"| Document Retrieval Hit@3 | **{summary['metrics']['document_hit_rate_at_3'] * 100:.1f}%** ({doc_hit_at_3_count}/{answerable_total}) |",
        f"| Exact Page/Record Citation Accuracy | **{summary['metrics']['exact_page_citation_accuracy'] * 100:.1f}%** ({page_citation_hit_count}/{answerable_total}) |",
        f"| Evidence Keyword Support Rate | **{summary['metrics']['evidence_keyword_support_rate'] * 100:.1f}%** ({keyword_support_count}/{answerable_total}) |",
        f"| Unsupported Query Rejection Rate (No-Guessing Guardrail) | **{summary['metrics']['unsupported_query_rejection_rate'] * 100:.1f}%** ({unanswerable_rejected_count}/{unanswerable_total}) |",
        "",
        "## Question-by-Question Results",
        "",
        "| ID | Category | Expected | Actual | Citation Verified | Top Cited Source(s) |",
        "|---|---|---|---|---|---|",
    ]

    for r in eval_results:
        cited_str = ", ".join(
            f"`{c['document_id']}` (p.{c['page']}, {c['score']:.2f})"
            for c in r.get("cited_sources", [])
        ) or "None (`no_answer`)"
        verified_badge = (
            "PASS"
            if r.get("exact_page_or_record_cited") or r.get("hallucination_prevented")
            else "REVIEW"
        )
        md_lines.append(
            f"| `{r['question_id']}` | {r['category']} | `{r['expected_status']}` | `{r['actual_status']}` | **{verified_badge}** | {cited_str} |"
        )

    md_path = EVALUATION_DIR / "RAG_EVALUATION_SUMMARY.md"
    with open(md_path, "w", encoding="utf-8") as f:
        f.write("\n".join(md_lines) + "\n")

    return summary


if __name__ == "__main__":
    rep = run_rag_evaluation()
    print(json.dumps(rep["metrics"], indent=2))
