"""
Interactive Free-Text RAG Tester for Member 3
Type ANY question in your own words — the pipeline dynamically embeds your query,
searches across all 390 chunks in the vector index, and generates a grounded answer
with exact page/record citations on the spot.

Run from terminal:
    python "rag-pipeline member3/rag/interactive_demo.py"
"""

from __future__ import annotations

import sys
import time
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from rag.retrieval import ask_question


def print_formatted_response(res: dict, elapsed_ms: float) -> None:
    print("\n" + "=" * 80)
    print(f"YOUR QUESTION : {res['query']}")
    print(
        f"STATUS        : {res['status'].upper()}  |  "
        f"CONFIDENCE: {res['confidence_score']}  |  "
        f"LATENCY: {elapsed_ms:.1f} ms"
    )
    print("-" * 80)
    print("GROUNDED ANSWER:")
    print(res["answer"])
    print("-" * 80)
    sources = res.get("sources", [])
    if not sources:
        print("CITATIONS: None (No supporting evidence in corpus — refused to guess)")
    else:
        print(f"RETRIEVED CITATIONS ({len(sources)} chunks matched from 390 indexed chunks):")
        for idx, s in enumerate(sources, start=1):
            print(
                f"\n  [{idx}] Document ID : {s['document_id']} (Chunk: {s['chunk_id']})"
                f"\n      Title       : {s['title']}"
                f"\n      Page/Record : {s['page']}  |  Similarity Score: {s['score']}"
                f"\n      Source URL  : {s['url']}"
                f"\n      Raw Excerpt : {s['excerpt'][:260].replace(chr(10), ' ')}..."
            )
    print("=" * 80 + "\n")


def main() -> None:
    if len(sys.argv) > 1:
        user_q = " ".join(sys.argv[1:])
        t0 = time.perf_counter()
        res = ask_question(user_q)
        elapsed_ms = (time.perf_counter() - t0) * 1000
        print_formatted_response(res, elapsed_ms)
        return

    print("=" * 80)
    print("   LIVE RAG ENGINE — ASK ANY QUESTION IN YOUR OWN WORDS (390 CHUNKS INDEXED)")
    print("=" * 80)
    print("Topics covered in the corpus:")
    print("  • WHO Essential Medicines List 2023 (71 pages: antibiotics, antidotes, oncology, etc.)")
    print("  • openFDA Drug Recalls (100 official recall reports: reasons, firms, lots)")
    print("  • openFDA NDC Drug Directory (100 drugs: active ingredients, strengths, labelers)")
    print("Type 'q' or 'exit' to stop.\n")

    while True:
        try:
            query = input("Ask any question > ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nSession ended.")
            break

        if not query:
            continue
        if query.lower() in {"q", "quit", "exit"}:
            print("Session ended.")
            break

        t0 = time.perf_counter()
        res = ask_question(query)
        elapsed_ms = (time.perf_counter() - t0) * 1000
        print_formatted_response(res, elapsed_ms)


if __name__ == "__main__":
    main()
