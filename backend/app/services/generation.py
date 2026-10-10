"""
LibraLink study-note generation utilities.

This module validates retrieved evidence and citations before notes
are returned to the application. It does not call an AI provider yet.
"""

from typing import Any


def insufficient_evidence_response(query: str) -> dict[str, Any]:
    """Return a safe response when usable full-text evidence is unavailable."""
    return {
        "query": query,
        "answerable": False,
        "message": (
            "There is not enough accessible book text to answer this question "
            "reliably. Try a different query or consult the library catalogue."
        ),
        "title": "Insufficient evidence",
        "sections": [],
        "sources": [],
        "limitations": [
            "No sufficient accessible full-text evidence was available."
        ],
        "disclaimer": (
            "This response does not establish what any unread physical book "
            "contains."
        ),
        "generated_by": "evidence_validator",
    }


def _usable_chunk_id(result: dict[str, Any]) -> str | None:
    """Return a non-empty chunk ID, or None if the result lacks one."""
    chunk_id = result.get("chunk_id")

    if not isinstance(chunk_id, str) or not chunk_id.strip():
        return None

    return chunk_id


def _is_usable_evidence(result: dict[str, Any]) -> bool:
    """
    Check whether a search result contains usable passage evidence.

    Catalogue-only records and records without an excerpt are not
    considered evidence for generating study notes.
    """
    excerpt = result.get("excerpt")
    access_status = str(result.get("access_status", "")).strip().lower()

    if not isinstance(excerpt, str) or not excerpt.strip():
        return False

    if access_status in {
        "catalogue_only",
        "catalogue-only",
        "physical_only",
        "physical-only",
    }:
        return False

    if result.get("ai_can_read_full_text") is False:
        return False

    return _usable_chunk_id(result) is not None


def validate_citations(
    sections: list[dict[str, Any]],
    retrieved_results: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """
    Validate citations against retrieved chunks.

    Each section may contain:
        {
            "heading": "...",
            "content": "...",
            "citations": ["chunk-id-1"]
        }

    Invalid citations are removed. Source metadata is taken from the
    retrieved records, never invented from model-generated text.
    """
    retrieved_by_id: dict[str, dict[str, Any]] = {}

    for result in retrieved_results:
        chunk_id = _usable_chunk_id(result)

        if chunk_id is not None and _is_usable_evidence(result):
            retrieved_by_id[chunk_id] = result

    validated_sections: list[dict[str, Any]] = []

    for section in sections:
        if not isinstance(section, dict):
            continue

        raw_citations = section.get("citations", [])
        if not isinstance(raw_citations, list):
            raw_citations = []

        valid_citations: list[str] = []
        seen: set[str] = set()

        for citation in raw_citations:
            if not isinstance(citation, str):
                continue

            if citation in retrieved_by_id and citation not in seen:
                valid_citations.append(citation)
                seen.add(citation)

        validated_sections.append(
            {
                "heading": str(section.get("heading", "Study notes")),
                "content": str(section.get("content", "")),
                "citations": valid_citations,
            }
        )

    return validated_sections


def resolve_sources(
    sections: list[dict[str, Any]],
    retrieved_results: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """
    Resolve citations to source metadata from retrieved search results.

    Page labels are preserved only when provided by the retrieval layer.
    This function never guesses printed page numbers.
    """
    retrieved_by_id: dict[str, dict[str, Any]] = {}

    for result in retrieved_results:
        chunk_id = _usable_chunk_id(result)

        if chunk_id is not None and _is_usable_evidence(result):
            retrieved_by_id[chunk_id] = result

    cited_ids: list[str] = []

    for section in sections:
        for chunk_id in section.get("citations", []):
            if chunk_id in retrieved_by_id and chunk_id not in cited_ids:
                cited_ids.append(chunk_id)

    sources: list[dict[str, Any]] = []

    for chunk_id in cited_ids:
        result = retrieved_by_id[chunk_id]

        sources.append(
            {
                "chunk_id": chunk_id,
                "book_id": result.get("book_id"),
                "source_file_id": result.get("source_file_id"),
                "title": result.get("title"),
                "author": result.get("author"),
                "edition": result.get("edition"),
                "pdf_page_index": result.get("pdf_page_index"),
                "pdf_page_base": result.get("pdf_page_base"),
                "printed_page_label": result.get("printed_page_label"),
                "printed_page_verified": result.get("printed_page_verified"),
                "section_heading": result.get("section_heading"),
                "excerpt": result.get("excerpt"),
                "access_status": result.get("access_status"),
                "extraction_method": result.get("extraction_method"),
                "corpus_version": result.get("corpus_version"),
                "is_sample_data": result.get("is_sample_data", False),
            }
        )

    return sources


def prepare_notes_response(
    query: str,
    sections: list[dict[str, Any]],
    retrieved_results: list[dict[str, Any]],
) -> dict[str, Any]:
    """
    Validate proposed sections and prepare the NotesResponse structure.

    This is a deterministic validation stage, not an AI generator.
    Connect it to the actual retrieval and LLM layers after their
    interfaces are confirmed.
    """
    usable_results = [
        result
        for result in retrieved_results
        if isinstance(result, dict) and _is_usable_evidence(result)
    ]

    if not query.strip() or not usable_results:
        return insufficient_evidence_response(query)

    validated_sections = validate_citations(sections, usable_results)

    # Do not claim the notes are answerable if every section lacks
    # a valid citation to accessible retrieved evidence.
    supported_sections = [
        section
        for section in validated_sections
        if section["content"].strip() and section["citations"]
    ]

    if not supported_sections:
        return insufficient_evidence_response(query)

    sources = resolve_sources(supported_sections, usable_results)

    if not sources:
        return insufficient_evidence_response(query)

    return {
        "query": query,
        "answerable": True,
        "message": "Study notes prepared from retrieved book passages.",
        "title": "Study Notes",
        "sections": supported_sections,
        "sources": sources,
        "limitations": [
            "Notes are limited to the retrieved passages.",
            "Citation validation confirms that cited chunks were retrieved; "
            "it does not independently prove every claim in the notes."
        ],
        "disclaimer": (
            "Verify important details against the cited source material."
        ),
        "generated_by": "validated_retrieval",
    }

def generate_grounded_notes(
    query: str,
    retrieved_results: list[dict[str, Any]],
) -> dict[str, Any]:
    """
    Generate study notes with Gemini, then validate citations
    against retrieved evidence before returning the response.
    """
    from backend.app.services.llm_client import (
        LLMUnavailableError,
        generate_structured_notes,
    )

    usable_results = [
        result
        for result in retrieved_results
        if isinstance(result, dict) and _is_usable_evidence(result)
    ]

    if not query.strip() or not usable_results:
        return insufficient_evidence_response(query)

    try:
        draft = generate_structured_notes(query, usable_results)
    except LLMUnavailableError:
        return {
            "query": query,
            "answerable": False,
            "message": (
                "The AI service is currently unavailable. "
                "No study notes were generated."
            ),
            "title": "Study notes unavailable",
            "sections": [],
            "sources": [],
            "limitations": [
                "AI generation failed; no notes were returned."
            ],
            "disclaimer": (
                "Please try again later or consult the source material."
            ),
            "generated_by": "gemini",
        }

    sections = draft.get("sections", [])

    if not isinstance(sections, list) or not sections:
        return insufficient_evidence_response(query)

    validated_sections = validate_citations(sections, usable_results)

    supported_sections = [
        section
        for section in validated_sections
        if section["content"].strip() and section["citations"]
    ]

    if not supported_sections:
        return insufficient_evidence_response(query)

    sources = resolve_sources(supported_sections, usable_results)

    if not sources:
        return insufficient_evidence_response(query)

    return {
        "query": query,
        "answerable": True,
        "message": "Study notes generated from retrieved book passages.",
        "title": str(draft.get("title", "Study Notes")),
        "sections": supported_sections,
        "sources": sources,
        "limitations": [
            "Notes are limited to the retrieved passages.",
            "Citation validation confirms that cited chunks were retrieved; "
            "it does not independently verify every factual claim."
        ],
        "disclaimer": (
            "Verify important details against the cited source material."
        ),
        "generated_by": "gemini",
    }