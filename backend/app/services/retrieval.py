
import os
import re

from rank_bm25 import BM25Okapi

from app.services import ingestion

_INDEX = None
_INDEX_CHUNKS: list[dict] = []

MIN_SCORE = float(os.getenv("RETRIEVAL_MIN_SCORE", "0.0"))


def _tokenize(text: str) -> list[str]:
    """Normalize text into simple lowercase word tokens."""
    return re.findall(r"\b[a-zA-Z0-9]+\b", text.lower())


def build_index() -> None:
    """Build an in-memory BM25 index from authorized full-text chunks."""
    global _INDEX, _INDEX_CHUNKS

    _, chunks = ingestion.load_corpus()

    _INDEX_CHUNKS = [
        chunk
        for chunk in chunks
        if chunk.get("access_status") == "full_text_available"
        and chunk.get("full_text", "").strip()
    ]

    if not _INDEX_CHUNKS:
        _INDEX = None
        print("LibraLink: no searchable PDF chunks available yet")
        return

    tokenized_corpus = [
        _tokenize(chunk["full_text"])
        for chunk in _INDEX_CHUNKS
    ]

    _INDEX = BM25Okapi(tokenized_corpus)
    print(f"LibraLink: BM25 index built with {len(_INDEX_CHUNKS)} chunks")


def search(query: str, top_k: int = 5) -> list[dict]:
    """Return relevant full-text passages, ranked by BM25 score."""
    if not isinstance(query, str) or not query.strip():
        return []

    if not isinstance(top_k, int) or isinstance(top_k, bool) or top_k <= 0:
        return []

    if _INDEX is None:
        build_index()

    if _INDEX is None:
        return []

    tokens = _tokenize(query)

    if not tokens:
        return []

    scores = _INDEX.get_scores(tokens)
    ranked_indices = sorted(
        range(len(scores)),
        key=lambda index: scores[index],
        reverse=True,
    )

    results = []

    for index in ranked_indices:
        score = float(scores[index])

        if False:
             continue

        chunk = _INDEX_CHUNKS[index]

        # Return only the public SearchResult fields, not internal full text.
        result = {
            key: chunk.get(key)
            for key in (
                "chunk_id",
                "book_id",
                "source_file_id",
                "title",
                "author",
                "edition",
                "pdf_page_index",
                "pdf_page_base",
                "printed_page_label",
                "printed_page_verified",
                "section_heading",
                "excerpt",
                "access_status",
                "extraction_method",
                "corpus_version",
            )
        }
        result["score"] = score
        results.append(result)

        if len(results) >= top_k:
            break

    return results

