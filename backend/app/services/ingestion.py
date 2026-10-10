
import json
import re
from pathlib import Path

import pymupdf

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
CATALOGUE_PATH = DATA_DIR / "sample_catalogue.json"
DOCS_DIR = DATA_DIR / "sample_docs"

_BOOKS: list[dict] = []
_CHUNKS: dict[str, dict] = {}


def _split_text(text: str, max_chars: int = 900, overlap: int = 120) -> list[str]:
    """Split page text into overlapping chunks."""
    text = re.sub(r"\s+", " ", text).strip()

    if not text:
        return []

    chunks = []
    start = 0

    while start < len(text):
        piece = text[start:start + max_chars].strip()

        if len(piece) > 80:
            chunks.append(piece)

        if start + max_chars >= len(text):
            break

        start += max_chars - overlap

    return chunks


def load_corpus() -> tuple[list[dict], list[dict]]:
    """Load catalogue and extract text from authorized demo PDFs."""
    global _BOOKS, _CHUNKS

    if not CATALOGUE_PATH.exists():
        raise FileNotFoundError(f"Catalogue not found: {CATALOGUE_PATH}")

    with CATALOGUE_PATH.open(encoding="utf-8") as file:
        catalogue = json.load(file)

    books = catalogue.get("books", [])
    chunks = {}

    for book in books:
        if book.get("access_status") != "full_text_available":
            continue

        filename = book.get("filename")
        book_id = book.get("book_id")

        if not filename or not book_id:
            continue

        pdf_path = (DOCS_DIR / filename).resolve()

        # Keep PDF access inside the sample_docs directory.
        if pdf_path.parent != DOCS_DIR.resolve():
            continue

        if not pdf_path.is_file() or pdf_path.suffix.lower() != ".pdf":
            continue

        with pymupdf.open(pdf_path) as document:
            for page_index, page in enumerate(document):
                page_text = page.get_text("text")

                for chunk_index, text in enumerate(_split_text(page_text)):
                    chunk_id = f"{book_id}:p{page_index}:c{chunk_index}"

                    chunks[chunk_id] = {
                        "chunk_id": chunk_id,
                        "book_id": book_id,
                        "source_file_id": book.get("source_file_id"),
                        "title": book.get("title", "Untitled"),
                        "author": book.get("author"),
                        "edition": book.get("edition"),
                        "pdf_page_index": page_index,
                        "pdf_page_base": 0,
                        "printed_page_label": None,
                        "printed_page_verified": False,
                        "section_heading": None,
                        "excerpt": text[:600],
                        "full_text": text,
                        "access_status": "full_text_available",
                        "extraction_method": "pymupdf_text",
                        "corpus_version": "demo-v1",
                    }

    _BOOKS = books
    _CHUNKS = chunks

    print(f"LibraLink: loaded {len(_BOOKS)} catalogue records")
    print(f"LibraLink: extracted {len(_CHUNKS)} text chunks")

    return _BOOKS, list(_CHUNKS.values())


def get_books() -> list[dict]:
    """Return catalogue records."""
    if not _BOOKS:
        load_corpus()

    return _BOOKS


def get_chunk(chunk_id: str) -> dict | None:
    """Return a chunk by ID."""
    return _CHUNKS.get(chunk_id)
