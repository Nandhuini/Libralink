
import os
from typing import Any

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, Response

from app.schemas import (
    SearchRequest,
    NotesRequest,
    NotesResponse,
    QuizRequest,
    QuizResponse,
    QuizSubmitRequest,
    QuizSubmitResponse,
)
from app.services import retrieval

# Load environment variables if .env exists.
load_dotenv()

app = FastAPI(
    title="LibraLink API",
    version="0.1.0",
    description="Library-focused AI study assistant prototype",
)

# Allow local development and configured frontend origins.
cors_origins = list(dict.fromkeys([
    "http://localhost:5173",
    "http://127.0.0.1:5173",
    "http://localhost:5174",
    "http://127.0.0.1:5174",
    *[
        origin.strip()
        for origin in os.getenv("CORS_ORIGINS", "").split(",")
        if origin.strip()
    ],
]))

app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


def error_response(
    status_code: int,
    code: str,
    message: str,
) -> JSONResponse:
    """Return errors in the agreed API envelope."""
    return JSONResponse(
        status_code=status_code,
        content={
            "error": {
                "code": code,
                "message": message,
            }
        },
    )


@app.exception_handler(RequestValidationError)
async def validation_error_handler(
    request: Request,
    exc: RequestValidationError,
):
    return error_response(
        422,
        "validation_error",
        "Invalid request. Check the request fields and try again.",
    )


@app.exception_handler(Exception)
async def unexpected_error_handler(
    request: Request,
    exc: Exception,
):
    return error_response(
        500,
        "internal_error",
        "An unexpected server error occurred.",
    )


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/api/health")
def api_health():
    return {"status": "ok"}


@app.get("/api/books")
def get_books():
    """Return catalogue records from the ingestion service."""
    try:
        from app.services import ingestion

        books = ingestion.get_books()
        return {"books": books}
    except Exception:
        return {"books": []}


@app.post("/api/search")
def search(request: SearchRequest):
    """Search the indexed collection and report insufficient evidence."""
    results = retrieval.search(request.query, request.top_k)

    if not results:
        return {
            "query": request.query,
            "results": [],
            "insufficient_evidence": True,
            "message": (
                "No sufficiently relevant passages were found "
                "in the indexed collection."
            ),
        }

    return {
        "query": request.query,
        "results": results,
        "insufficient_evidence": False,
        "message": None,
    }


@app.post("/api/notes", response_model=NotesResponse)
def generate_notes(request: NotesRequest):
    """Generate extractive notes from retrieved passages."""
    results = retrieval.search(request.query, request.top_k)

    if not results:
        return {
            "query": request.query,
            "answerable": False,
            "message": (
                "Insufficient evidence in the indexed collection."
            ),
            "title": f"Study notes: {request.query}",
            "sections": [],
            "sources": [],
            "limitations": [
                "No sufficiently relevant passages were retrieved."
            ],
            "disclaimer": (
                "Study aid based on retrieved text. Verify important "
                "claims in the cited source."
            ),
            "generated_by": None,
        }

    sections = []
    sources = []
    seen_source_ids = set()

    for result in results:
        chunk_id = result.get("chunk_id")
        excerpt = (result.get("excerpt") or "").strip()

        if not chunk_id or not excerpt:
            continue

        sections.append({
            "heading": result.get("section_heading") or "Explanation",
            "type": "explanation",
            "content": excerpt,
            "citations": [chunk_id],
        })

        if chunk_id not in seen_source_ids:
            sources.append({
                "chunk_id": chunk_id,
                "book_id": result.get("book_id"),
                "source_file_id": result.get("source_file_id"),
                "title": result.get("title"),
                "author": result.get("author"),
                "edition": result.get("edition"),
                "pdf_page_index": result.get("pdf_page_index"),
                "page_number": result.get("page_number"),
                "pdf_page_base": result.get("pdf_page_base", 0),
                "printed_page_label": result.get("printed_page_label"),
                "printed_page_verified": result.get(
                    "printed_page_verified", False
                ),
                "section_heading": result.get("section_heading"),
                "excerpt": excerpt[:600],
                "score": result.get("score"),
                "access_status": result.get("access_status"),
                "extraction_method": result.get("extraction_method"),
                "corpus_version": result.get("corpus_version"),
            })
            seen_source_ids.add(chunk_id)

    if not sections:
        return {
            "query": request.query,
            "answerable": False,
            "message": "Retrieved passages contained no usable text.",
            "title": f"Study notes: {request.query}",
            "sections": [],
            "sources": [],
            "limitations": [
                "Retrieved passages did not contain usable excerpts."
            ],
            "disclaimer": (
                "Study aid based on retrieved text. Verify important "
                "claims in the cited source."
            ),
            "generated_by": None,
        }

    return {
        "query": request.query,
        "answerable": True,
        "message": None,
        "title": f"Study notes: {request.query}",
        "sections": sections,
        "sources": sources,
        "limitations": [
            "These are extractive notes based only on retrieved passages.",
            "Printed page labels are not guaranteed to be verified.",
        ],
        "disclaimer": (
            "Study aid based on retrieved text. Verify important "
            "claims in the cited source."
        ),
        "generated_by": None,
    }


# --------------------------------------------------
# Quiz Generation
# --------------------------------------------------

@app.post("/api/quiz", response_model=QuizResponse)
def create_quiz(request: QuizRequest):
    """Create reading checks grounded in retrieved passages."""
    from app.services.quiz import generate_quiz

    return generate_quiz(
        topic=request.topic,
        question_count=request.question_count,
    )


# --------------------------------------------------
# Quiz Submission and Scoring
# --------------------------------------------------

@app.post("/api/quiz/submit", response_model=QuizSubmitResponse)
def quiz_submit(request: QuizSubmitRequest):
    """Evaluate submitted quiz answers."""
    from app.services.quiz import submit_quiz

    result = submit_quiz(
        quiz_id=request.quiz_id,
        answers=[
            answer.model_dump()
            for answer in request.answers
        ],
    )

    if not result.get("success"):
        raise HTTPException(
            status_code=404,
            detail=result.get(
                "message",
                "Quiz not found or expired.",
            ),
        )

    return result


# --------------------------------------------------
# Token Endpoints
# --------------------------------------------------

try:
    from app.services import tokens

    @app.get("/api/tokens/demo-code")
    def get_demo_code():
        return tokens.current_demo_code()

    @app.post("/api/tokens/check-in")
    def check_in(payload: dict[str, Any]):
        student_id = payload.get("student_id", "")
        code = payload.get("code", "")

        if not isinstance(student_id, str) or not isinstance(code, str):
            return error_response(
                422,
                "validation_error",
                "student_id and code must be strings.",
            )

        if not student_id.startswith("DEMO-"):
            return error_response(
                422,
                "validation_error",
                "Only demo student IDs are accepted.",
            )

        return tokens.check_in(student_id, code)

    @app.get("/api/tokens/{student_id}")
    def get_token_balance(student_id: str):
        return tokens.get_balance(student_id)

except ImportError:
    pass


# --------------------------------------------------
# PDF Export
# --------------------------------------------------

try:
    from app.services import export as export_service

    @app.post("/api/export/notes")
    def export_notes(payload: dict[str, Any]):
        notes = payload.get("notes")

        if not isinstance(notes, dict):
            return error_response(
                422,
                "validation_error",
                "The request must contain a notes object.",
            )

        pdf_bytes = export_service.notes_to_pdf(notes)

        return Response(
            content=pdf_bytes,
            media_type="application/pdf",
            headers={
                "Content-Disposition": (
                    'attachment; filename="libralink-notes.pdf"'
                )
            },
        )

except ImportError:
    pass
