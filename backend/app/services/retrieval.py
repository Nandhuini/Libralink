
import os
import re

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


def build_index() -> None:
    """Build BM25 index from authorized full-text chunks."""
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
    """Return relevant full-text passages ranked by BM25."""
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

    query_tokens = set(tokens) - STOP_WORDS
    expanded_tokens = list(tokens)

    for token in query_tokens:
        for synonym in SYNONYMS.get(token, []):
            expanded_tokens.extend(_tokenize(synonym))

    if not query_tokens:
        return []

    scores = _INDEX.get_scores(expanded_tokens)
    ranked_indices = sorted(
        range(len(scores)),
        key=lambda index: scores[index],
        reverse=True,
    )

    results = []

    for index in ranked_indices:
        score = float(scores[index])

        if score <= 0 or score < MIN_SCORE:
            continue

        chunk = _INDEX_CHUNKS[index]
        chunk_tokens = set(_tokenize(chunk.get("full_text", "")))

        if not query_tokens.intersection(chunk_tokens):
            # Also permit matches through configured synonyms.
            synonym_tokens = set()
            for token in query_tokens:
                for synonym in SYNONYMS.get(token, []):
                    synonym_tokens.update(_tokenize(synonym))

            if not synonym_tokens.intersection(chunk_tokens):
                continue

        result = {
            key: chunk.get(key)
            for key in (
                "chunk_id", "book_id", "source_file_id", "title",
                "author", "edition", "pdf_page_index", "pdf_page_base",
                "printed_page_label", "printed_page_verified",
                "section_heading", "excerpt", "access_status",
                "extraction_method", "corpus_version",
            )
        }
        result["score"] = score
        results.append(result)

        if len(results) >= top_k:
            break

    return results
