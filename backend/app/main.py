from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from app.schemas import SearchRequest, NotesRequest
from app.services import retrieval

app = FastAPI(
    title="LibraLink API",
    version="0.1.0",
)


# --------------------------------------------------
# HEALTH CHECK
# --------------------------------------------------

@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/api/health")
def api_health():
    return {"status": "ok"}


# --------------------------------------------------
# BOOK CATALOGUE
# --------------------------------------------------

@app.get("/api/books")
def get_books():
    try:
        books, _ = retrieval.ingestion.load_corpus()

        return {
            "books": [
                {
                    "book_id": book.get("book_id"),
                    "title": book.get("title", "Untitled"),
                    "author": book.get("author"),
                    "edition": book.get("edition"),
                    "access_status": book.get("access_status"),
                }
                for book in books
            ]
        }

    except Exception as exc:
        return {
            "books": [],
            "message": f"Catalogue unavailable: {exc}",
        }


# --------------------------------------------------
# SEARCH
# --------------------------------------------------

def search_passages(query: str, top_k: int):
    """Retrieve matching source passages using BM25."""
    return retrieval.search(query, top_k)


@app.post("/api/search")
def search(request: SearchRequest):
    results = search_passages(request.query, request.top_k)

    if not results:
        return {
            "query": request.query,
            "answerable": False,
            "message": "Insufficient evidence in the available collection.",
            "results": [],
        }

    return {
        "query": request.query,
        "answerable": True,
        "results": results,
    }


# --------------------------------------------------
# EXTRACTIVE NOTES
# --------------------------------------------------

@app.post("/api/notes")
def generate_notes(request: NotesRequest):
    """
    Return notes based on retrieved source passages.
    This is extractive retrieval, not LLM generation.
    """

    results = search_passages(request.query, request.top_k)

    if not results:
        return {
            "answerable": False,
            "query": request.query,
            "mode": "extractive",
            "generated_by": None,
            "sections": [],
            "sources": [],
            "message": "Insufficient evidence in the available collection.",
        }

    sections = []
    sources = []

    for item in results:
        excerpt = item.get("excerpt", "")

        if excerpt:
            sections.append({
                "heading": item.get("title", "Retrieved evidence"),
                "content": excerpt,
            })

        sources.append({
            "chunk_id": item["chunk_id"],
            "book_id": item["book_id"],
            "title": item.get("title", "Untitled"),
            "page_index": item.get("pdf_page_index", 0),
            "access_status": item.get("access_status", "unknown"),
        })

    return {
        "answerable": bool(sections),
        "query": request.query,
        "mode": "extractive",
        "generated_by": None,
        "sections": sections,
        "sources": sources,
        "message": "Notes extracted from retrieved source passages.",
    }


# --------------------------------------------------
# VALIDATION ERROR HANDLER
# --------------------------------------------------

@app.exception_handler(RequestValidationError)
async def validation_error_handler(
    request: Request,
    exc: RequestValidationError,
):
    return JSONResponse(
        status_code=422,
        content={
            "error": {
                "code": "validation_error",
                "message": "The request contains invalid fields.",
            }
        },
    )