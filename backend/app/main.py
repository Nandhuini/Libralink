from fastapi import FastAPI
from pydantic import BaseModel, Field

from app.services import retrieval, ingestion
from backend.app.services.generation import (
    generate_grounded_notes,
    insufficient_evidence_response,
)

app = FastAPI(title="LibraLink API")


class NotesRequest(BaseModel):
    query: str = Field(min_length=1, max_length=300)
    top_k: int = Field(default=5, ge=1, le=10)


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/api/notes")
def create_notes(request: NotesRequest):
    results = retrieval.search(request.query, top_k=request.top_k)

    if not results:
        return insufficient_evidence_response(request.query)

    passages = []

    for result in results:
        chunk_id = result.get("chunk_id")
        stored_chunk = ingestion.get_chunk(chunk_id) if chunk_id else None

        if not stored_chunk:
            continue

        # Keep the public retrieval metadata and add the full stored text.
        passages.append({
            **result,
            "full_text": stored_chunk.get("full_text", ""),
        })

    if not passages:
        return insufficient_evidence_response(request.query)

    return generate_grounded_notes(request.query, passages)