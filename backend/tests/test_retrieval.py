import pytest

from app.services import retrieval


@pytest.fixture(scope="module", autouse=True)
def setup_index():
    retrieval.build_index()


def test_normal_distribution_returns_results():
    results = retrieval.search("normal distribution", top_k=3)

    assert len(results) > 0
    assert len(results) <= 3
    assert all(result["score"] > 0 for result in results)


def test_empty_query_returns_no_results():
    assert retrieval.search("") == []


def test_unsupported_query_returns_no_results():
    assert retrieval.search("quantum mechanics black holes") == []


def test_result_contains_required_fields():
    results = retrieval.search("normal distribution", top_k=1)

    assert results

    required_fields = {
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
        "score",
        "access_status",
        "extraction_method",
        "corpus_version",
    }

    assert required_fields.issubset(results[0].keys())
    assert results[0]["access_status"] == "full_text_available"
    assert results[0]["extraction_method"] == "pymupdf_text"
    assert len(results[0]["excerpt"]) <= 600
