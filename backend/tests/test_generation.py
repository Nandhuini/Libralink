from backend.app.services.generation import (
    insufficient_evidence_response,
    prepare_notes_response,
    resolve_sources,
    validate_citations,
)


def sample_result():
    return {
        "chunk_id": "chunk-001",
        "book_id": "book-001",
        "source_file_id": "file-001",
        "title": "Introduction to Data Structures",
        "author": "Demo Author",
        "edition": "First edition",
        "pdf_page_index": 4,
        "pdf_page_base": 0,
        "printed_page_label": "5",
        "printed_page_verified": True,
        "section_heading": "Binary Search Trees",
        "excerpt": "A binary search tree stores keys in an ordered structure.",
        "score": 0.92,
        "access_status": "digital_full_text",
        "extraction_method": "pdf_text",
        "corpus_version": "demo-v1",
        "is_sample_data": True,
    }


def test_valid_citation_is_preserved():
    result = sample_result()
    sections = [
        {
            "heading": "Definition",
            "content": "A binary search tree stores keys in an ordered structure.",
            "citations": ["chunk-001"],
        }
    ]

    validated = validate_citations(sections, [result])

    assert validated[0]["citations"] == ["chunk-001"]


def test_unknown_citation_is_removed():
    result = sample_result()
    sections = [
        {
            "heading": "Definition",
            "content": "Example content.",
            "citations": ["invented-chunk"],
        }
    ]

    validated = validate_citations(sections, [result])

    assert validated[0]["citations"] == []


def test_catalogue_only_record_is_not_evidence():
    result = sample_result()
    result["access_status"] = "catalogue_only"

    response = prepare_notes_response(
        "What is a binary search tree?",
        [
            {
                "heading": "Definition",
                "content": "An unsupported definition.",
                "citations": ["chunk-001"],
            }
        ],
        [result],
    )

    assert response["answerable"] is False
    assert response["sections"] == []
    assert response["sources"] == []


def test_empty_evidence_returns_insufficient_evidence():
    response = insufficient_evidence_response("Explain binary search trees")

    assert response["answerable"] is False
    assert response["sources"] == []
    assert response["sections"] == []


def test_source_metadata_comes_from_retrieved_result():
    result = sample_result()
    sections = [
        {
            "heading": "Definition",
            "content": "A binary search tree stores ordered keys.",
            "citations": ["chunk-001"],
        }
    ]

    sources = resolve_sources(sections, [result])

    assert len(sources) == 1
    assert sources[0]["title"] == "Introduction to Data Structures"
    assert sources[0]["pdf_page_index"] == 4
    assert sources[0]["printed_page_label"] == "5"
    assert sources[0]["is_sample_data"] is True


def test_grounded_notes_abstains_without_evidence():
    from backend.app.services.generation import generate_grounded_notes

    response = generate_grounded_notes(
        "Explain binary search trees",
        [],
    )

    assert response["answerable"] is False
    assert response["sections"] == []
    assert response["sources"] == []

def test_grounded_notes_abstains_without_evidence():
    from backend.app.services.generation import generate_grounded_notes

    response = generate_grounded_notes(
        "Explain binary search trees",
        [],
    )

    assert response["answerable"] is False
    assert response["sections"] == []
    assert response["sources"] == []
