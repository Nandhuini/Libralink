# LibraLink API Contract

## 1. Health Check

GET /health

Response:

{
  "status": "ok"
}

## 2. Books

GET /api/books

Returns the available catalogue records.

## 3. Search

POST /api/search

Request:

{
  "query": "binary search trees",
  "top_k": 5
}

Rules:
- Query length: 1–300 characters.
- top_k: 1–10.
- Default top_k: 5.
- Return relevant passages with source metadata.
- Return an insufficient-evidence message when appropriate.

## 4. Study Notes

POST /api/notes

Request:

{
  "query": "binary search trees",
  "top_k": 5
}

Returns structured study notes grounded in retrieved passages.

## 5. Demo Check-in

GET /api/tokens/demo-code

POST /api/tokens/check-in

GET /api/tokens/{student_id}

These endpoints implement the simulated library check-in and demo token balance.

## 6. PDF Export

POST /api/export/notes

Accepts study notes and returns a PDF.
This is a lower-priority feature.

## 7. Error Format

{
  "error": {
    "code": "validation_error",
    "message": "Description of the error"
  }
}

Supported error codes:
- validation_error
- llm_unavailable
- not_found
- rate_limited
- internal_error

## 8. Reliability Requirements

- Citations must reference retrieved chunk IDs.
- Source metadata must be resolved by the application.
- Unsupported topics must return insufficient evidence.
- An LLM failure must never return fabricated notes.