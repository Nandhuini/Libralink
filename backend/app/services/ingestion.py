
import hashlib
import json
import re
from pathlib import Path
from typing import Any

import pymupdf


# --------------------------------------------------
# Paths and configuration
# --------------------------------------------------

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
CATALOGUE_PATH = DATA_DIR / "sample_catalogue.json"
DOCS_DIR = DATA_DIR / "sample_docs"
CACHE_PATH = DATA_DIR / "processed_chunks_cache.json"

CHUNK_SIZE = 900
CHUNK_OVERLAP = 120
OCR_LANGUAGE = "eng"
OCR_DPI = 150
CACHE_VERSION = "1"

_BOOKS: list[dict[str, Any]] = []
_CHUNKS: dict[str, dict[str, Any]] = {}


# --------------------------------------------------
# Helpers
# --------------------------------------------------

def _split_text(
    text: str,
    max_chars: int = CHUNK_SIZE,
    overlap: int = CHUNK_OVERLAP,
) -> list[str]:
    """Split page text into overlapping chunks."""

    text = re.sub(r"\s+", " ", text).strip()

    if not text:
        return []

    if max_chars <= 0:
        raise ValueError("max_chars must be greater than zero")

    if overlap < 0 or overlap >= max_chars:
        raise ValueError("overlap must be between 0 and max_chars - 1")

    chunks: list[str] = []
    start = 0
    step = max_chars - overlap

    while start < len(text):
        piece = text[start:start + max_chars].strip()

        if len(piece) > 80:
            chunks.append(piece)

        if start + max_chars >= len(text):
            break

        start += step

    return chunks


def _file_fingerprint(path: Path) -> dict[str, Any]:
    """Create a cache fingerprint for a file."""

    stat = path.stat()

    return {
        "size": stat.st_size,
        "mtime_ns": stat.st_mtime_ns,
    }


def _cache_signature(
    books: list[dict[str, Any]],
) -> dict[str, Any]:
    """Describe the catalogue and files represented by the cache."""

    entries = []

    for book in books:
        if book.get("access_status") != "full_text_available":
            continue

        filename = book.get("filename")
        book_id = book.get("book_id")

        if not filename or not book_id:
            continue

        pdf_path = (DOCS_DIR / filename).resolve()

        if pdf_path.parent != DOCS_DIR.resolve():
            continue

        if not pdf_path.is_file() or pdf_path.suffix.lower() != ".pdf":
            continue

        entries.append({
            "book_id": book_id,
            "filename": filename,
            "fingerprint": _file_fingerprint(pdf_path),
        })

    return {
        "cache_version": CACHE_VERSION,
        "chunk_size": CHUNK_SIZE,
        "chunk_overlap": CHUNK_OVERLAP,
        "ocr_language": OCR_LANGUAGE,
        "ocr_dpi": OCR_DPI,
        "books": entries,
    }


def _load_cache(
    signature: dict[str, Any],
) -> dict[str, dict[str, Any]] | None:
    """Load cached chunks only when the cache matches current files."""

    if not CACHE_PATH.is_file():
        return None

    try:
        with CACHE_PATH.open("r", encoding="utf-8") as file:
            payload = json.load(file)

        if payload.get("signature") != signature:
            print("LibraLink: cache is outdated; rebuilding corpus")
            return None

        raw_chunks = payload.get("chunks")

        if not isinstance(raw_chunks, list):
            return None

        chunks: dict[str, dict[str, Any]] = {}

        for chunk in raw_chunks:
            if not isinstance(chunk, dict):
                return None

            chunk_id = chunk.get("chunk_id")
            if not isinstance(chunk_id, str) or not chunk_id:
                return None

            chunks[chunk_id] = chunk

        print(f"LibraLink: loaded {len(chunks)} chunks from cache")
        return chunks

    except (OSError, json.JSONDecodeError, TypeError, ValueError) as exc:
        print(f"LibraLink: could not read cache: {exc}")
        return None


def _save_cache(
    signature: dict[str, Any],
    chunks: dict[str, dict[str, Any]],
) -> None:
    """Write cache atomically so interrupted writes do not corrupt it."""

    temporary_path = CACHE_PATH.with_suffix(".tmp")

    payload = {
        "signature": signature,
        "chunks": list(chunks.values()),
    }

    try:
        with temporary_path.open("w", encoding="utf-8") as file:
            json.dump(payload, file, ensure_ascii=False)

        temporary_path.replace(CACHE_PATH)
        print(f"LibraLink: saved {len(chunks)} chunks to cache")

    except OSError as exc:
        print(f"Warning: could not save chunk cache: {exc}")

        try:
            temporary_path.unlink(missing_ok=True)
        except OSError:
            pass


# --------------------------------------------------
# PDF extraction with OCR fallback
# --------------------------------------------------

def _extract_page_text(
    page: pymupdf.Page,
) -> tuple[str, str]:
    """Extract selectable text, then fall back to PyMuPDF OCR."""

    text = page.get_text("text", sort=True).strip()

    if text:
        return text, "pymupdf_text"

    try:
        text_page = page.get_textpage_ocr(
            language=OCR_LANGUAGE,
            dpi=OCR_DPI,
            full=True,
        )

        text = page.get_text(
            textpage=text_page,
            sort=True,
        ).strip()

        if text:
            return text, "pymupdf_ocr"

        return "", "no_text_found"

    except Exception as exc:
        print(
            f"Warning: OCR failed on PDF page "
            f"{page.number + 1}: {exc}"
        )
        return "", "ocr_failed"


# --------------------------------------------------
# Corpus ingestion
# --------------------------------------------------

def load_corpus(
    force_reload: bool = False,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """
    Load catalogue records and searchable chunks.

    Existing cache is reused when catalogue PDF files and
    extraction settings have not changed.

    force_reload=True bypasses the cache and reprocesses PDFs.
    """

    global _BOOKS, _CHUNKS

    if not force_reload and _BOOKS and _CHUNKS:
        return _BOOKS, list(_CHUNKS.values())

    if not CATALOGUE_PATH.is_file():
        raise FileNotFoundError(
            f"Catalogue not found: {CATALOGUE_PATH}"
        )

    if not DOCS_DIR.is_dir():
        raise FileNotFoundError(
            f"PDF directory not found: {DOCS_DIR}"
        )

    with CATALOGUE_PATH.open("r", encoding="utf-8-sig") as file:
        catalogue = json.load(file)

    books = catalogue.get("books", [])

    if not isinstance(books, list):
        raise ValueError(
            "Invalid catalogue format: 'books' must be a list"
        )

    _BOOKS = books

    signature = _cache_signature(books)

    if not force_reload:
        cached_chunks = _load_cache(signature)

        if cached_chunks is not None:
            _CHUNKS = cached_chunks
            return _BOOKS, list(_CHUNKS.values())

    chunks: dict[str, dict[str, Any]] = {}
    successful_books = 0

    for book in books:
        if book.get("access_status") != "full_text_available":
            continue

        filename = book.get("filename")
        book_id = book.get("book_id")

        if not filename or not book_id:
            print("Warning: skipping book without book_id or filename")
            continue

        pdf_path = (DOCS_DIR / filename).resolve()

        if pdf_path.parent != DOCS_DIR.resolve():
            print(f"Warning: skipping unsafe PDF path: {filename}")
            continue

        if not pdf_path.is_file() or pdf_path.suffix.lower() != ".pdf":
            print(f"Warning: PDF not found: {pdf_path}")
            continue

        print(f"\nLoading: {book.get('title', filename)}")

        book_chunk_count = 0
        text_pages = 0
        ocr_pages = 0

        try:
            with pymupdf.open(pdf_path) as document:
                total_pages = len(document)

                for page_index, page in enumerate(document):
                    page_text, extraction_method = _extract_page_text(page)

                    if not page_text:
                        continue

                    if extraction_method == "pymupdf_ocr":
                        ocr_pages += 1
                    else:
                        text_pages += 1

                    for chunk_index, text in enumerate(
                        _split_text(page_text)
                    ):
                        chunk_id = (
                            f"{book_id}:p{page_index}:c{chunk_index}"
                        )

                        chunks[chunk_id] = {
                            "chunk_id": chunk_id,
                            "book_id": book_id,
                            "source_file_id": book.get("source_file_id"),
                            "title": book.get("title", "Untitled"),
                            "author": book.get("author"),
                            "edition": book.get("edition"),
                            "filename": filename,
                            "pdf_page_index": page_index,
                            "page_number": page_index + 1,
                            "pdf_page_base": 0,
                            "printed_page_label": None,
                            "printed_page_verified": False,
                            "section_heading": None,
                            "excerpt": text[:600],
                            "full_text": text,
                            "access_status": "full_text_available",
                            "extraction_method": extraction_method,
                            "corpus_version": "demo-v3",
                        }

                        book_chunk_count += 1

                    if (page_index + 1) % 50 == 0:
                        print(
                            f"  Processed {page_index + 1}/"
                            f"{total_pages} pages; "
                            f"{book_chunk_count} chunks"
                        )

            successful_books += 1

            print(
                f"  Finished: {book_chunk_count} chunks, "
                f"{text_pages} text pages, "
                f"{ocr_pages} OCR pages"
            )

        except Exception as exc:
            print(f"Warning: could not process {filename}: {exc}")

    _CHUNKS = chunks

    print("\nLibraLink ingestion complete")
    print(f"Catalogue records: {len(_BOOKS)}")
    print(f"Books processed: {successful_books}")
    print(f"Total chunks: {len(_CHUNKS)}")

    _save_cache(signature, _CHUNKS)

    return _BOOKS, list(_CHUNKS.values())


# --------------------------------------------------
# Public helpers
# --------------------------------------------------

def get_books() -> list[dict[str, Any]]:
    """Return catalogue records."""

    if not _BOOKS:
        load_corpus()

    return _BOOKS


def get_chunk(chunk_id: str) -> dict[str, Any] | None:
    """Return a chunk by its ID."""

    if not _CHUNKS:
        load_corpus()

    return _CHUNKS.get(chunk_id)


def get_chunks() -> list[dict[str, Any]]:
    """Return all currently loaded chunks."""

    if not _CHUNKS:
        load_corpus()

    return list(_CHUNKS.values())
