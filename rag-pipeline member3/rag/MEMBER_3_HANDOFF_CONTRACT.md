# Member 3 → Member 4 Integration Contract (RAG Component)

- **Owner (Member 3):** Mayar Hany — Document Processing & RAG
- **Consumer (Member 4):** Rawan Husseiny — API (`api/`) & Streamlit UI (`app/`)
- **Related ClickUp Tasks:** `123u8tyngk4`, `123u8tyngk5`, `123u8tync5t` (Agree component contracts and shared schemas)

---

## 1. Python Import & Usage

```python
from rag.retrieval import ask_question, retrieve_chunks

# 1. End-to-End Grounded Question Answering (for UI Chat / FastAPI `/api/rag/ask`)
response = ask_question(
    query="What caused the recall of Progesterone 100 mg/mL in Corn Oil Injection (D-321-2016)?",
    top_k=3,
    min_score=0.16,
)

# 2. Direct Chunk Search (for Document Explorer / Evidence Search tab)
chunks = retrieve_chunks(
    query="amoxicillin community acquired pneumonia",
    top_k=4,
    document_type_filter=None,  # Optional: "PDF_REGULATORY_GUIDELINE", "JSON_REGULATORY_RECALLS", "JSON_DRUG_CATALOG"
)
```

---

## 2. Response Schema (`ask_question`)

### Case A — Evidence Found (`status == "answered"`)

```json
{
  "query": "What caused the recall of Progesterone 100 mg/mL in Corn Oil Injection (D-321-2016)?",
  "status": "answered",
  "answer": "Based on the verified regulatory documents in the knowledge corpus:\n- **openFDA Drug Enforcement & Recall Reports Snapshot (100 Records) — Recall D-321-2016** (Source `DOC-FDA-ENF-20261102`, Page/Record 1): ...",
  "confidence_score": 0.8912,
  "scope_disclaimer": "Grounded strictly in verified WHO EML 2023 and openFDA regulatory snapshots (not live local pharmacy inventory or retail pricing).",
  "sources": [
    {
      "chunk_id": "DOC-FDA-ENF-20261102-REC-001-CH01",
      "document_id": "DOC-FDA-ENF-20261102",
      "title": "openFDA Drug Enforcement & Recall Reports Snapshot (100 Records) — Recall D-321-2016",
      "publisher": "U.S. Food and Drug Administration (openFDA)",
      "page": 1,
      "url": "https://api.fda.gov/drug/enforcement.json",
      "score": 0.8912,
      "excerpt": "FDA Drug Recall Report — Recall Number: D-321-2016..."
    }
  ]
}
```

### Case B — Insufficient Evidence or Out-of-Scope Query (`status == "no_answer"`)

When a user asks about unverified local market stock, live Egyptian retail drug pricing in EGP, or any topic unsupported by the verified corpus, the pipeline refuses to guess:

```json
{
  "query": "What is the current live stock inventory and retail price in EGP of Panadol Extra in Cairo pharmacies today?",
  "status": "no_answer",
  "answer": "The available verified documents (WHO Essential Medicines List 2023 and U.S. openFDA Enforcement/NDC records) do not contain live Egyptian pharmacy inventory, local retail drug pricing in EGP, or real-time local stock levels. Per project data governance rules (Zero-Mock Policy), the system will not fabricate or guess market figures.",
  "confidence_score": 0.0,
  "scope_disclaimer": "Verified scope: WHO EML 2023 (global) & U.S. openFDA Enforcement/NDC snapshots. Excludes live Egyptian market stock and retail prices.",
  "sources": []
}
```
