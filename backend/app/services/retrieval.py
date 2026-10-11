
import os
import re
from typing import Any

from rank_bm25 import BM25Okapi
from app.services import ingestion


_INDEX = None
_INDEX_CHUNKS: list[dict] = []

MIN_SCORE = float(os.getenv("RETRIEVAL_MIN_SCORE", "0.0"))

STOP_WORDS = {
    "a", "an", "the", "is", "are", "was", "were",
    "what", "which", "who", "where", "when", "why",
    "how", "explain", "tell", "me", "about", "for",
    "of", "to", "in", "on", "and", "or", "with",
    "do", "does", "can", "could", "please",
}

SYNONYMS = {
    "average": ["mean"],
    "mean": ["average"],
    "spread": ["variance", "standard deviation"],
    "variance": ["spread"],
    "chance": ["probability"],
    "probability": ["chance"],
    "gaussian": ["normal distribution"],
    "normal": ["gaussian"],
}


def _stem(token: str) -> str:
    """Apply lightweight suffix normalization."""
    if len(token) > 5 and token.endswith("ies"):
        return token[:-3] + "y"

    if len(token) > 5 and token.endswith("ing"):
        token = token[:-3]
    elif len(token) > 4 and token.endswith("ed"):
        token = token[:-2]
    elif len(token) > 4 and token.endswith("es"):
        token = token[:-2]
    elif len(token) > 3 and token.endswith("s"):
        token = token[:-1]

    if (
        len(token) > 3
        and token[-1] == token[-2]
        and token[-1] not in "aeiou"
    ):
        token = token[:-1]

    return token


def _tokenize(text: str) -> list[str]:
    """Normalize text into lowercase, lightly stemmed tokens."""
    tokens = re.findall(r"\b[a-zA-Z0-9]+\b", text.lower())
    return [_stem(token) for token in tokens]


def build_index(force_reload: bool = False) -> None:
    """Build the BM25 index from accessible full-text chunks."""
    global _INDEX, _INDEX_CHUNKS

    if _INDEX is not None and not force_reload:
        return

    # Reuse already-loaded chunks where possible. This avoids
    # triggering OCR again in the same Python process.
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

    # BM25 requires a non-empty token list for each document.
    valid_pairs = [
        (chunk, tokens)
        for chunk, tokens in zip(_INDEX_CHUNKS, tokenized_corpus)
        if tokens
    ]

    if not valid_pairs:
        _INDEX = None
        _INDEX_CHUNKS = []
        print("LibraLink: no searchable tokens available")
        return

    _INDEX_CHUNKS = [pair[0] for pair in valid_pairs]
    tokenized_corpus = [pair[1] for pair in valid_pairs]

    _INDEX = BM25Okapi(tokenized_corpus)

    print(
        f"LibraLink: BM25 index built with "
        f"{len(_INDEX_CHUNKS)} chunks"
    )


def full_page_for_chunk(chunk_id: str) -> dict[str, Any] | None:
    """Rejoin the complete source page containing an indexed chunk."""
    if _INDEX is None:
        build_index()

    selected_chunk = next(
        (
            chunk
            for chunk in _INDEX_CHUNKS
            if chunk.get("chunk_id") == chunk_id
        ),
        None,
    )
    if selected_chunk is None:
        return None

    book_id = selected_chunk.get("book_id")
    page_index = selected_chunk.get("pdf_page_index")
    page_chunks = [
        chunk
        for chunk in _INDEX_CHUNKS
        if chunk.get("book_id") == book_id
        and chunk.get("pdf_page_index") == page_index
    ]

    def chunk_number(chunk: dict) -> int:
        match = re.search(r":c(\d+)$", str(chunk.get("chunk_id", "")))
        return int(match.group(1)) if match else -1

    page_chunks.sort(key=chunk_number)
    numbers = [chunk_number(chunk) for chunk in page_chunks]
    if not page_chunks or numbers != list(range(len(numbers))):
        return None

    full_text = ""
    segments = []

    for chunk in page_chunks:
        chunk_text = str(chunk.get("full_text") or "")
        if not chunk_text:
            return None

        overlap = 0
        if full_text:
            maximum_overlap = min(
                ingestion.CHUNK_OVERLAP,
                len(full_text),
                len(chunk_text),
            )
            for size in range(maximum_overlap, 0, -1):
                if full_text.endswith(chunk_text[:size]):
                    overlap = size
                    break

            if overlap < max(40, ingestion.CHUNK_OVERLAP - 5):
                return None

        start = len(full_text) - overlap
        full_text += chunk_text[overlap:]
        segments.append({
            "chunk_id": chunk.get("chunk_id"),
            "start": start,
            "end": start + len(chunk_text),
            "book_id": book_id,
            "title": chunk.get("title"),
            "page_number": chunk.get("page_number"),
            "pdf_page_index": page_index,
            "extraction_method": chunk.get("extraction_method"),
        })

    return {"text": full_text, "segments": segments}


def search(query: str, top_k: int = 5) -> list[dict]:
    """Return relevant full-text passages ranked by BM25."""

    if not isinstance(query, str) or not query.strip():
        return []

    if (
        not isinstance(top_k, int)
        or isinstance(top_k, bool)
        or top_k <= 0
    ):
        return []

    if _INDEX is None:
        build_index()

    if _INDEX is None:
        return []

    tokens = _tokenize(query)
    if not tokens:
        return []

    query_tokens = set(tokens) - {
        _stem(word) for word in STOP_WORDS
    }

    if not query_tokens:
        return []

    expanded_tokens = list(tokens)

    synonym_tokens = set()
    for token in query_tokens:
        for synonym in SYNONYMS.get(token, []):
            synonym_tokens.update(_tokenize(synonym))

    expanded_tokens.extend(synonym_tokens)

    scores = _INDEX.get_scores(expanded_tokens)

    ranked_indices = sorted(
        range(len(scores)),
        key=lambda index: scores[index],
        reverse=True,
    )

    results: list[dict] = []

    for index in ranked_indices:
        score = float(scores[index])

        # Exclude irrelevant zero-score matches.
        if score <= 0 or score < MIN_SCORE:
            continue

        chunk = _INDEX_CHUNKS[index]
        chunk_tokens = set(_tokenize(chunk.get("full_text", "")))

        # Multi-term queries need more than a single coincidental overlap.
        matching_tokens = (
            query_tokens.intersection(chunk_tokens)
            | synonym_tokens.intersection(chunk_tokens)
        )
        minimum_matches = 1 if len(query_tokens) == 1 else 2
        if len(matching_tokens) < minimum_matches:
            continue

        result = {
            key: chunk.get(key)
            for key in (
                "chunk_id",
                "book_id",
                "source_file_id",
                "title",
                "author",
                "edition",
                "filename",
                "pdf_page_index",
                "page_number",
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
