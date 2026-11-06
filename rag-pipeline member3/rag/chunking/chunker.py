"""
Task 3a (ClickUp ID: 123u8tyngjp) — Build chunking pipeline

Splits extracted document pages and structured regulatory records into
overlapping, context-preserving chunks while retaining full provenance metadata
(document_id, title, page_number, source_url, publisher, section_hint).
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List

from rag.extraction.document_inventory import EXTRACTION_DIR, REPO_ROOT

CHUNKING_DIR = Path(__file__).resolve().parent
DEFAULT_CHUNK_SIZE = 1200
DEFAULT_CHUNK_OVERLAP = 250


def split_text_preserving_lines(
    text: str,
    chunk_size: int = DEFAULT_CHUNK_SIZE,
    chunk_overlap: int = DEFAULT_CHUNK_OVERLAP,
) -> List[str]:
    """
    Split text along line/paragraph boundaries so pharmaceutical drug names,
    dosage strengths, and recall reasons stay intact.
    """
    cleaned = text.strip()
    if not cleaned:
        return []
    if len(cleaned) <= chunk_size:
        return [cleaned]

    lines = [ln.strip() for ln in cleaned.splitlines() if ln.strip()]
    chunks: List[str] = []
    current_lines: List[str] = []
    current_len = 0

    for line in lines:
        line_len = len(line) + 1
        if current_len + line_len > chunk_size and current_lines:
            chunk_str = "\n".join(current_lines).strip()
            chunks.append(chunk_str)

            # Build overlap from trailing lines
            overlap_lines: List[str] = []
            overlap_len = 0
            for prev_line in reversed(current_lines):
                if overlap_len + len(prev_line) + 1 <= chunk_overlap:
                    overlap_lines.insert(0, prev_line)
                    overlap_len += len(prev_line) + 1
                else:
                    break
            current_lines = overlap_lines
            current_len = overlap_len

        current_lines.append(line)
        current_len += line_len

    if current_lines:
        last_chunk = "\n".join(current_lines).strip()
        if not chunks or last_chunk != chunks[-1]:
            chunks.append(last_chunk)

    return chunks


def run_chunking_pipeline(
    chunk_size: int = DEFAULT_CHUNK_SIZE,
    chunk_overlap: int = DEFAULT_CHUNK_OVERLAP,
) -> Dict[str, Any]:
    """Load extracted_documents.json, produce chunks.json and chunking_report.json."""
    extracted_path = EXTRACTION_DIR / "extracted_documents.json"
    if not extracted_path.exists():
        from rag.extraction.extractor import run_extraction_pipeline

        run_extraction_pipeline()

    with open(extracted_path, "r", encoding="utf-8") as f:
        units: List[Dict[str, Any]] = json.load(f)

    all_chunks: List[Dict[str, Any]] = []
    by_source: Dict[str, int] = {}

    for unit in units:
        if not unit.get("is_usable", False):
            continue

        raw_text = unit.get("text", "")
        doc_id = unit["document_id"]
        page_num = unit["page_number"]
        section_hint = unit.get("section_hint", "")

        # Prepend header context to PDF pages if not already at top of chunk
        pieces = split_text_preserving_lines(
            raw_text, chunk_size=chunk_size, chunk_overlap=chunk_overlap
        )

        for idx, piece in enumerate(pieces, start=1):
            # Ensure PDF chunks after chunk 1 still carry document + section context
            if unit["document_type"] == "PDF_REGULATORY_GUIDELINE" and idx > 1:
                header_prefix = f"[{unit['title']} | Page {page_num}"
                if section_hint:
                    header_prefix += f" | {section_hint}"
                header_prefix += "]\n"
                enriched_text = header_prefix + piece
            else:
                enriched_text = piece

            chunk_id = f"{unit['unit_id']}-CH{idx:02d}"
            chunk_record = {
                "chunk_id": chunk_id,
                "unit_id": unit["unit_id"],
                "document_id": doc_id,
                "title": unit["title"],
                "publisher": unit["publisher"],
                "source_url": unit["source_url"],
                "document_type": unit["document_type"],
                "page_number": page_num,
                "section_hint": section_hint,
                "chunk_index": idx,
                "total_chunks_in_unit": len(pieces),
                "char_count": len(enriched_text),
                "word_count": len(enriched_text.split()),
                "metadata_extra": unit.get("metadata_extra", {}),
                "text": enriched_text,
            }
            all_chunks.append(chunk_record)
            by_source[doc_id] = by_source.get(doc_id, 0) + 1

    CHUNKING_DIR.mkdir(parents=True, exist_ok=True)
    chunks_path = CHUNKING_DIR / "chunks.json"
    report_path = CHUNKING_DIR / "chunking_report.json"

    with open(chunks_path, "w", encoding="utf-8") as f:
        json.dump(all_chunks, f, ensure_ascii=False, indent=2)

    report = {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "owner": "Mayar Hany (Member 3 — Document Processing & RAG)",
        "clickup_task_id": "123u8tyngjp",
        "chunk_size_chars": chunk_size,
        "chunk_overlap_chars": chunk_overlap,
        "total_input_units": sum(1 for u in units if u.get("is_usable", False)),
        "total_chunks_generated": len(all_chunks),
        "avg_chunk_chars": round(
            sum(c["char_count"] for c in all_chunks) / max(len(all_chunks), 1), 1
        ),
        "chunks_per_document": by_source,
        "chunks_file": str(chunks_path.relative_to(REPO_ROOT)),
    }
    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)

    return report


if __name__ == "__main__":
    rep = run_chunking_pipeline()
    print(json.dumps(rep, indent=2))
