"""
Task 2 (ClickUp ID: 123u8tyngjn) — Implement text extraction and OCR fallback

Extracts page-level text from PDF documents (preserving document_id, page_number,
section headers, and character metrics), triggers Baidu Unlimited-OCR
(https://github.com/baidu/Unlimited-OCR) fallback ONLY when normal PDF text extraction
returns insufficient text (< MIN_TEXT_CHARS_FOR_NATIVE_PDF), and normalizes structured
regulatory records (openFDA Enforcement Recalls & openFDA NDC) into traceable document units.
Also regenerates `lakehouse/gold/gold_rag_knowledge_corpus.csv`.
"""

from __future__ import annotations

import base64
import csv
import json
import os
import re
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from rag.extraction.document_inventory import (
    EXTRACTION_DIR,
    REPO_ROOT,
    build_document_inventory,
)

MIN_TEXT_CHARS_FOR_NATIVE_PDF = 25

UNLIMITED_OCR_DEFAULT_MODEL = os.getenv("UNLIMITED_OCR_MODEL", "baidu/Unlimited-OCR")
UNLIMITED_OCR_API_URL = os.getenv("UNLIMITED_OCR_API_URL", "").strip()
UNLIMITED_OCR_BASE_SIZE = int(os.getenv("UNLIMITED_OCR_BASE_SIZE", "1024"))
UNLIMITED_OCR_IMAGE_SIZE = int(os.getenv("UNLIMITED_OCR_IMAGE_SIZE", "640"))
UNLIMITED_OCR_MAX_LENGTH = int(os.getenv("UNLIMITED_OCR_MAX_LENGTH", "32768"))
UNLIMITED_OCR_NO_REPEAT_NGRAM = int(os.getenv("UNLIMITED_OCR_NO_REPEAT_NGRAM", "35"))
UNLIMITED_OCR_NGRAM_WINDOW = int(os.getenv("UNLIMITED_OCR_NGRAM_WINDOW", "128"))


class BaiduUnlimitedOCREngine:
    """
    Lazy-loaded wrapper for `baidu/Unlimited-OCR` (Reference Sliding Window Attention VLM).
    Reference: https://github.com/baidu/Unlimited-OCR

    Supports two execution modes when a scanned/low-text PDF page triggers OCR fallback:
    1. vLLM OpenAI-compatible Server (`UNLIMITED_OCR_API_URL` configured in environment)
    2. Local HuggingFace `AutoModel` + `AutoTokenizer` with `trust_remote_code=True` on CUDA GPU
    3. Graceful CPU/Offline fallback if neither vLLM nor CUDA GPU is available on the host.
    """

    _tokenizer: Any = None
    _model: Any = None
    _loaded_model_name: Optional[str] = None

    @classmethod
    def render_pdf_page_to_png_bytes(cls, pdf_path: Path, page_number: int, dpi: int = 200) -> Optional[bytes]:
        """Render a 1-indexed PDF page to PNG bytes using PyMuPDF (fitz) or pypdfium2."""
        try:
            import fitz  # PyMuPDF

            doc = fitz.open(str(pdf_path))
            page = doc[page_number - 1]
            pix = page.get_pixmap(dpi=dpi)
            png_bytes = pix.tobytes("png")
            doc.close()
            return png_bytes
        except ImportError:
            return None
        except Exception:
            return None

    @classmethod
    def infer_via_vllm_endpoint(
        cls,
        png_bytes: bytes,
        api_url: str,
        model_name: str = UNLIMITED_OCR_DEFAULT_MODEL,
    ) -> Tuple[str, str]:
        """
        Query a running `vLLM serve baidu/Unlimited-OCR` endpoint using Reference Sliding
        Window Attention parameters (`no_repeat_ngram_size=35`, `ngram_window=128`).
        """
        import requests

        b64_img = base64.b64encode(png_bytes).decode("ascii")
        endpoint = api_url.rstrip("/")
        if not endpoint.endswith("/chat/completions"):
            endpoint = f"{endpoint}/chat/completions"

        payload = {
            "model": model_name,
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "image_url",
                            "image_url": {"url": f"data:image/png;base64,{b64_img}"},
                        },
                        {
                            "type": "text",
                            "text": "<image>document parsing.",
                        },
                    ],
                }
            ],
            "max_tokens": min(UNLIMITED_OCR_MAX_LENGTH, 8192),
            "no_repeat_ngram_size": UNLIMITED_OCR_NO_REPEAT_NGRAM,
            "ngram_window": UNLIMITED_OCR_NGRAM_WINDOW,
        }
        resp = requests.post(endpoint, json=payload, timeout=60)
        resp.raise_for_status()
        data = resp.json()
        text = (
            data.get("choices", [{}])[0]
            .get("message", {})
            .get("content", "")
            .strip()
        )
        if text:
            return text, f"BAIDU_UNLIMITED_OCR_VLLM_SUCCESS({model_name})"
        return "", f"BAIDU_UNLIMITED_OCR_VLLM_EMPTY({model_name})"

    @classmethod
    def infer_via_transformers_cuda(
        cls,
        png_bytes: bytes,
        model_name: str = UNLIMITED_OCR_DEFAULT_MODEL,
    ) -> Tuple[str, str]:
        """
        Run local HuggingFace `AutoModel.from_pretrained("baidu/Unlimited-OCR", trust_remote_code=True)`
        with Reference Sliding Window Attention (`ngram_window=128`, `no_repeat_ngram_size=35`).
        """
        try:
            import torch
            from transformers import AutoModel, AutoTokenizer
        except ImportError:
            return "", "BAIDU_UNLIMITED_OCR_TRANSFORMERS_NOT_INSTALLED"

        if not torch.cuda.is_available():
            return "", "BAIDU_UNLIMITED_OCR_SKIPPED_NO_CUDA_GPU"

        if cls._model is None or cls._loaded_model_name != model_name:
            cls._tokenizer = AutoTokenizer.from_pretrained(
                model_name, trust_remote_code=True
            )
            cls._model = (
                AutoModel.from_pretrained(
                    model_name,
                    trust_remote_code=True,
                    use_safetensors=True,
                    torch_dtype=torch.bfloat16,
                )
                .eval()
                .cuda()
            )
            cls._loaded_model_name = model_name

        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_img_path = Path(tmp_dir) / "page.png"
            tmp_img_path.write_bytes(png_bytes)
            out_dir = Path(tmp_dir) / "ocr_output"
            out_dir.mkdir(parents=True, exist_ok=True)

            output_text = cls._model.infer(
                cls._tokenizer,
                prompt="<image>document parsing.",
                image_file=str(tmp_img_path),
                output_path=str(out_dir),
                base_size=UNLIMITED_OCR_BASE_SIZE,
                image_size=UNLIMITED_OCR_IMAGE_SIZE,
                crop_mode=True,
                max_length=UNLIMITED_OCR_MAX_LENGTH,
                no_repeat_ngram_size=UNLIMITED_OCR_NO_REPEAT_NGRAM,
                ngram_window=UNLIMITED_OCR_NGRAM_WINDOW,
                save_results=False,
            )

        parsed = (output_text or "").strip()
        if parsed:
            return parsed, f"BAIDU_UNLIMITED_OCR_CUDA_SUCCESS({model_name})"
        return "", f"BAIDU_UNLIMITED_OCR_CUDA_EMPTY({model_name})"


def _try_ocr_fallback(pdf_path: Path, page_number: int) -> Tuple[str, str]:
    """
    Attempt OCR fallback on a single 1-indexed PDF page using `baidu/Unlimited-OCR`
    when native PDF text extraction yields insufficient text (< MIN_TEXT_CHARS_FOR_NATIVE_PDF).
    Follows project architectural rule: OCR is fallback ONLY when normal extraction fails.
    """
    model_name = os.getenv("UNLIMITED_OCR_MODEL", UNLIMITED_OCR_DEFAULT_MODEL)
    api_url = os.getenv("UNLIMITED_OCR_API_URL", UNLIMITED_OCR_API_URL).strip()

    png_bytes = BaiduUnlimitedOCREngine.render_pdf_page_to_png_bytes(pdf_path, page_number)

    # 1. Try vLLM Unlimited-OCR Server if configured
    if api_url and png_bytes:
        try:
            return BaiduUnlimitedOCREngine.infer_via_vllm_endpoint(
                png_bytes=png_bytes, api_url=api_url, model_name=model_name
            )
        except Exception as exc:
            return "", f"BAIDU_UNLIMITED_OCR_VLLM_ERROR:{type(exc).__name__}"

    # 2. Try Local HuggingFace `baidu/Unlimited-OCR` on CUDA GPU
    if png_bytes:
        try:
            text, status = BaiduUnlimitedOCREngine.infer_via_transformers_cuda(
                png_bytes=png_bytes, model_name=model_name
            )
            if text:
                return text, status
            return "", status
        except Exception as exc:
            return "", f"BAIDU_UNLIMITED_OCR_CUDA_ERROR:{type(exc).__name__}"

    return "", f"BAIDU_UNLIMITED_OCR_FALLBACK_READY_NO_GPU_OR_RENDERER({model_name})"


def extract_pdf_pages_with_ocr_fallback(
    pdf_path: Path,
    document_id: str,
    title: str,
    source_url: str,
    publisher: str,
) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
    """
    Extract text page-by-page from a PDF file using PyMuPDF (fitz), pypdf, or pdfplumber,
    falling back to verified Bronze page extraction if native PDF libraries are not installed
    in the current Python environment, and triggering `baidu/Unlimited-OCR` fallback on low-text pages.
    """
    raw_pages: List[str] = []
    engine_used = "NONE"

    # 1. Try PyMuPDF (fitz)
    try:
        import fitz

        doc = fitz.open(str(pdf_path))
        raw_pages = [page.get_text("text") or "" for page in doc]
        doc.close()
        engine_used = "PyMuPDF (fitz)"
    except ImportError:
        pass

    # 2. Try pypdf
    if not raw_pages:
        try:
            from pypdf import PdfReader

            reader = PdfReader(str(pdf_path))
            raw_pages = [page.extract_text() or "" for page in reader.pages]
            engine_used = "pypdf"
        except ImportError:
            pass

    # 3. Try pdfplumber
    if not raw_pages:
        try:
            import pdfplumber

            with pdfplumber.open(str(pdf_path)) as pdf:
                raw_pages = [page.extract_text() or "" for page in pdf.pages]
            engine_used = "pdfplumber"
        except ImportError:
            pass

    # 4. Fallback to verified Bronze extraction cache (generated by pypdf from the exact PDF)
    if not raw_pages:
        cached_pages_path = pdf_path.parent / f"{pdf_path.stem}_pages.json"
        if cached_pages_path.exists():
            with open(cached_pages_path, "r", encoding="utf-8") as f:
                cached = json.load(f)
            raw_pages = cached.get("pages", [])
            engine_used = "pypdf (verified_bronze_page_cache)"

    extracted_records: List[Dict[str, Any]] = []
    native_ok_count = 0
    ocr_triggered_count = 0
    empty_after_fallback_count = 0

    for page_idx, raw_text in enumerate(raw_pages, start=1):
        cleaned = re.sub(r"[ \t]+", " ", raw_text).strip()
        extraction_method = "NATIVE_PDF_TEXT"
        ocr_status = "NOT_NEEDED"

        if len(cleaned) < MIN_TEXT_CHARS_FOR_NATIVE_PDF:
            ocr_triggered_count += 1
            ocr_text, ocr_status = _try_ocr_fallback(pdf_path, page_idx)
            if len(ocr_text) >= MIN_TEXT_CHARS_FOR_NATIVE_PDF:
                cleaned = ocr_text
                extraction_method = "OCR_FALLBACK_BAIDU_UNLIMITED_OCR"
            else:
                empty_after_fallback_count += 1
                extraction_method = "LOW_TEXT_OR_BLANK_PAGE"
        else:
            native_ok_count += 1

        # Detect section title if present on the page
        lines = [ln.strip() for ln in cleaned.splitlines() if ln.strip()]
        section_hint = ""
        for ln in lines[:6]:
            if re.match(r"^\d+(\.\d+)*\s+[A-Z]", ln) or "Explanatory notes" in ln:
                section_hint = ln
                break

        extracted_records.append(
            {
                "unit_id": f"{document_id}-P{page_idx:03d}",
                "document_id": document_id,
                "title": title,
                "publisher": publisher,
                "source_url": source_url,
                "document_type": "PDF_REGULATORY_GUIDELINE",
                "page_number": page_idx,
                "section_hint": section_hint,
                "char_count": len(cleaned),
                "word_count": len(cleaned.split()),
                "extraction_engine": engine_used,
                "ocr_fallback_engine": UNLIMITED_OCR_DEFAULT_MODEL,
                "extraction_method": extraction_method,
                "ocr_fallback_status": ocr_status,
                "is_usable": len(cleaned) >= MIN_TEXT_CHARS_FOR_NATIVE_PDF,
                "text": cleaned,
            }
        )

    stats = {
        "document_id": document_id,
        "total_pages": len(raw_pages),
        "native_text_pages": native_ok_count,
        "ocr_fallback_triggered_pages": ocr_triggered_count,
        "ocr_fallback_engine": UNLIMITED_OCR_DEFAULT_MODEL,
        "ocr_fallback_architecture": "Reference Sliding Window Attention (R-SWA)",
        "empty_or_cover_pages": empty_after_fallback_count,
        "usable_pages": sum(1 for r in extracted_records if r["is_usable"]),
        "total_extracted_chars": sum(r["char_count"] for r in extracted_records),
        "extraction_engine": engine_used,
    }
    return extracted_records, stats


def extract_fda_enforcement_records(
    json_path: Path,
    document_id: str,
    title: str,
    source_url: str,
    publisher: str,
) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
    """Convert openFDA Enforcement recall records into rich, traceable document units."""
    with open(json_path, "r", encoding="utf-8") as f:
        payload = json.load(f)

    results = payload.get("data", {}).get("results", payload.get("results", []))
    records: List[Dict[str, Any]] = []

    for idx, item in enumerate(results, start=1):
        recall_num = item.get("recall_number") or f"UNNUMBERED-{idx:03d}"
        firm = item.get("recalling_firm") or "Unknown Firm"
        classification = item.get("classification") or "Unclassified"
        status = item.get("status") or "Unknown Status"
        product_desc = item.get("product_description") or ""
        reason = item.get("reason_for_recall") or ""
        init_date = item.get("recall_initiation_date") or "Unknown Date"
        report_date = item.get("report_date") or "Unknown Date"
        dist_pattern = item.get("distribution_pattern") or "N/A"
        code_info = item.get("code_info") or "N/A"
        city = item.get("city") or ""
        state = item.get("state") or ""
        country = item.get("country") or "United States"
        voluntary = item.get("voluntary_mandated") or "N/A"

        structured_text = (
            f"FDA Drug Recall Report — Recall Number: {recall_num}\n"
            f"Classification: {classification} | Status: {status}\n"
            f"Recalling Firm: {firm} ({city}, {state}, {country})\n"
            f"Recall Initiation Date: {init_date} | Report Date: {report_date}\n"
            f"Action Type: {voluntary} | Distribution Pattern: {dist_pattern}\n"
            f"Recalled Product Description: {product_desc}\n"
            f"Reason for Recall: {reason}\n"
            f"Lot / Code Information: {code_info}"
        )

        records.append(
            {
                "unit_id": f"{document_id}-REC-{idx:03d}",
                "document_id": document_id,
                "title": f"{title} — Recall {recall_num}",
                "publisher": publisher,
                "source_url": source_url,
                "document_type": "JSON_REGULATORY_RECALLS",
                "page_number": idx,
                "section_hint": f"Recall {recall_num} ({classification}) - {firm}",
                "char_count": len(structured_text),
                "word_count": len(structured_text.split()),
                "extraction_engine": "openFDA_JSON_Normalizer",
                "ocr_fallback_engine": "NOT_APPLICABLE_JSON",
                "extraction_method": "STRUCTURED_JSON_TO_TEXT",
                "ocr_fallback_status": "NOT_APPLICABLE_JSON",
                "is_usable": bool(reason or product_desc),
                "metadata_extra": {
                    "recall_number": recall_num,
                    "recalling_firm": firm,
                    "classification": classification,
                    "status": status,
                    "recall_initiation_date": init_date,
                    "report_date": report_date,
                    "country": country,
                },
                "text": structured_text,
            }
        )

    stats = {
        "document_id": document_id,
        "total_records": len(results),
        "usable_records": sum(1 for r in records if r["is_usable"]),
        "total_extracted_chars": sum(r["char_count"] for r in records),
        "extraction_engine": "openFDA_JSON_Normalizer",
    }
    return records, stats


def extract_fda_ndc_records(
    json_path: Path,
    document_id: str,
    title: str,
    source_url: str,
    publisher: str,
) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
    """Convert openFDA NDC product listings into searchable reference document units."""
    with open(json_path, "r", encoding="utf-8") as f:
        payload = json.load(f)

    results = payload.get("data", {}).get("results", payload.get("results", []))
    records: List[Dict[str, Any]] = []

    for idx, item in enumerate(results, start=1):
        product_ndc = item.get("product_ndc") or f"NDC-{idx:03d}"
        brand_name = item.get("brand_name") or item.get("brand_name_base") or "N/A"
        generic_name = item.get("generic_name") or "N/A"
        labeler_name = item.get("labeler_name") or "Unknown Labeler"
        dosage_form = item.get("dosage_form") or "N/A"
        product_type = item.get("product_type") or "N/A"
        marketing_cat = item.get("marketing_category") or "N/A"

        ingredients = item.get("active_ingredients") or []
        ing_str = "; ".join(
            f"{ing.get('name', 'Unknown')} ({ing.get('strength', 'N/A')})"
            for ing in ingredients
        ) or "Not specified"

        packaging = item.get("packaging") or []
        pkg_str = "; ".join(
            f"{p.get('package_ndc', '')}: {p.get('description', '')}"
            for p in packaging
        ) or "Not specified"

        structured_text = (
            f"FDA NDC Drug Directory Listing — Product NDC: {product_ndc}\n"
            f"Brand Name: {brand_name} | Generic Name: {generic_name}\n"
            f"Labeler / Manufacturer: {labeler_name}\n"
            f"Active Ingredients & Strengths: {ing_str}\n"
            f"Dosage Form: {dosage_form} | Product Type: {product_type} | Marketing Category: {marketing_cat}\n"
            f"Packaging Configurations: {pkg_str}"
        )

        records.append(
            {
                "unit_id": f"{document_id}-NDC-{idx:03d}",
                "document_id": document_id,
                "title": f"{title} — NDC {product_ndc} ({brand_name})",
                "publisher": publisher,
                "source_url": source_url,
                "document_type": "JSON_DRUG_CATALOG",
                "page_number": idx,
                "section_hint": f"NDC {product_ndc}: {brand_name} ({generic_name})",
                "char_count": len(structured_text),
                "word_count": len(structured_text.split()),
                "extraction_engine": "openFDA_NDC_Normalizer",
                "ocr_fallback_engine": "NOT_APPLICABLE_JSON",
                "extraction_method": "STRUCTURED_JSON_TO_TEXT",
                "ocr_fallback_status": "NOT_APPLICABLE_JSON",
                "is_usable": True,
                "metadata_extra": {
                    "product_ndc": product_ndc,
                    "brand_name": brand_name,
                    "generic_name": generic_name,
                    "labeler_name": labeler_name,
                    "dosage_form": dosage_form,
                },
                "text": structured_text,
            }
        )

    stats = {
        "document_id": document_id,
        "total_records": len(results),
        "usable_records": len(records),
        "total_extracted_chars": sum(r["char_count"] for r in records),
        "extraction_engine": "openFDA_NDC_Normalizer",
    }
    return records, stats


def run_extraction_pipeline() -> Dict[str, Any]:
    """Run full inventory + text extraction + Baidu Unlimited-OCR fallback and save artifacts."""
    inventory = build_document_inventory()
    all_units: List[Dict[str, Any]] = []
    source_summaries: List[Dict[str, Any]] = []

    for doc in inventory["documents"]:
        if not doc["file_exists"]:
            continue

        file_path = Path(doc["absolute_path"])
        doc_id = doc["document_id"]
        title = doc["title"]
        url = doc["source_url"]
        publisher = doc["publisher"]

        if doc["file_format"] == "PDF":
            units, stats = extract_pdf_pages_with_ocr_fallback(
                pdf_path=file_path,
                document_id=doc_id,
                title=title,
                source_url=url,
                publisher=publisher,
            )
            all_units.extend(units)
            source_summaries.append(stats)
        elif doc_id == "DOC-FDA-ENF-20261102":
            units, stats = extract_fda_enforcement_records(
                json_path=file_path,
                document_id=doc_id,
                title=title,
                source_url=url,
                publisher=publisher,
            )
            all_units.extend(units)
            source_summaries.append(stats)
        elif doc_id == "DOC-FDA-NDC-20261102":
            units, stats = extract_fda_ndc_records(
                json_path=file_path,
                document_id=doc_id,
                title=title,
                source_url=url,
                publisher=publisher,
            )
            all_units.extend(units)
            source_summaries.append(stats)

    EXTRACTION_DIR.mkdir(parents=True, exist_ok=True)
    extracted_path = EXTRACTION_DIR / "extracted_documents.json"
    report_path = EXTRACTION_DIR / "extraction_report.json"

    with open(extracted_path, "w", encoding="utf-8") as f:
        json.dump(all_units, f, ensure_ascii=False, indent=2)

    # Also regenerate lakehouse/gold/gold_rag_knowledge_corpus.csv so Gold layer is populated
    gold_dir = REPO_ROOT / "lakehouse" / "gold"
    gold_dir.mkdir(parents=True, exist_ok=True)
    gold_corpus_csv = gold_dir / "gold_rag_knowledge_corpus.csv"

    with open(gold_corpus_csv, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=["doc_id", "source_type", "content", "metadata"],
        )
        writer.writeheader()
        for u in all_units:
            if not u["is_usable"]:
                continue
            meta_obj = {
                "document_id": u["document_id"],
                "title": u["title"],
                "publisher": u["publisher"],
                "source_url": u["source_url"],
                "page_or_record": u["page_number"],
                "section_hint": u["section_hint"],
                "extraction_method": u["extraction_method"],
                "ocr_fallback_engine": u.get("ocr_fallback_engine", ""),
            }
            if "metadata_extra" in u:
                meta_obj.update(u["metadata_extra"])
            writer.writerow(
                {
                    "doc_id": u["unit_id"],
                    "source_type": u["document_type"],
                    "content": u["text"],
                    "metadata": json.dumps(meta_obj, ensure_ascii=False),
                }
            )

    report = {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "owner": "Mayar Hany (Member 3 — Document Processing & RAG)",
        "clickup_task_id": "123u8tyngjn",
        "ocr_fallback_engine": UNLIMITED_OCR_DEFAULT_MODEL,
        "ocr_fallback_repo": "https://github.com/baidu/Unlimited-OCR",
        "total_extracted_units": len(all_units),
        "usable_units": sum(1 for u in all_units if u["is_usable"]),
        "unusable_or_blank_units": sum(1 for u in all_units if not u["is_usable"]),
        "total_characters_extracted": sum(u["char_count"] for u in all_units),
        "gold_corpus_csv_path": str(gold_corpus_csv.relative_to(REPO_ROOT)),
        "source_breakdown": source_summaries,
    }
    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)

    return report


if __name__ == "__main__":
    rep = run_extraction_pipeline()
    print(json.dumps(rep, indent=2))
