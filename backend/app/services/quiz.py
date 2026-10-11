
"""Generate source-grounded MCQs and score quiz submissions."""

import json
import os
import re
import time
from typing import Any
from uuid import uuid4

from dotenv import load_dotenv
from google import genai
from google.genai import types

from app.services import retrieval

PROJECT_ROOT = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "..", "..")
)
load_dotenv(os.path.join(PROJECT_ROOT, ".env"))

# Demo storage. Quiz answer keys are kept on the server.
# They are cleared when the backend restarts.
_QUIZ_STORE: dict[str, dict[str, Any]] = {}
GEMINI_TRANSIENT_MAX_RETRIES = 2
GEMINI_TRANSIENT_STATUS_CODES = {503, 504}


def _gemini_http_status(error: Exception) -> int | None:
    for value in (
        getattr(error, "code", None),
        getattr(error, "status_code", None),
    ):
        try:
            status_code = int(value)
        except (TypeError, ValueError):
            continue
        if status_code in GEMINI_TRANSIENT_STATUS_CODES or status_code in {
            401, 403, 404, 429
        }:
            return status_code

    match = re.search(r"\b(401|403|404|429|503|504)\b", str(error))
    return int(match.group(1)) if match else None


def generate_quiz(
    topic: str,
    question_count: int = 5,
) -> dict[str, Any]:
    """Generate MCQs grounded in retrieved textbook passages."""

    topic = topic.strip() if isinstance(topic, str) else ""

    try:
        question_count = max(1, min(int(question_count), 10))
    except (TypeError, ValueError):
        question_count = 5

    if not topic:
        return {
            "topic": topic,
            "answerable": False,
            "questions": [],
            "sources": [],
            "message": "Please provide a topic.",
            "generated_by": None,
        }

    try:
        results = retrieval.search(topic, top_k=10) or []
    except Exception as exc:
        print(f"Quiz retrieval error: {type(exc).__name__}")
        return {
            "topic": topic,
            "answerable": False,
            "questions": [],
            "sources": [],
            "message": "Textbook retrieval failed.",
            "generated_by": None,
        }

    passages = []
    source_map = {}

    for result in results:
        excerpt = (result.get("excerpt") or "").strip()
        chunk_id = result.get("chunk_id")

        if not excerpt or not chunk_id:
            continue

        source_map[chunk_id] = {
            "chunk_id": chunk_id,
            "book_id": result.get("book_id"),
            "title": result.get("title"),
            "page_number": result.get("page_number"),
            "pdf_page_index": result.get("pdf_page_index"),
            "extraction_method": result.get("extraction_method"),
        }

        passages.append({
            "chunk_id": chunk_id,
            "title": result.get("title"),
            "page_number": result.get("page_number"),
            "excerpt": excerpt[:3000],
        })

    if not passages:
        return {
            "topic": topic,
            "answerable": False,
            "questions": [],
            "sources": [],
            "message": "No supporting textbook passages were found.",
            "generated_by": None,
        }

    provider = os.getenv("LLM_PROVIDER", "").strip().lower()
    api_key = os.getenv("LLM_API_KEY", "").strip()
    model = os.getenv("LLM_MODEL", "").strip()

    try:
        timeout = max(
            1, min(int(os.getenv("LLM_TIMEOUT_SECONDS", "30")), 120)
        )
    except ValueError:
        timeout = 30

    if provider != "gemini" or not api_key or not model:
        return {
            "topic": topic,
            "answerable": False,
            "questions": [],
            "sources": list(source_map.values()),
            "message": "Gemini configuration is incomplete.",
            "generated_by": None,
        }

    prompt = f"""
You are LibraLink, a careful textbook-based MCQ generator.

Create up to {question_count} multiple-choice questions about:
{topic}

Use ONLY the retrieved passages. Do not invent facts.
Return fewer questions if the evidence is insufficient.

Return JSON in this format:
{{
  "questions": [
    {{
      "question": "A clear conceptual question",
      "options": ["Option A", "Option B", "Option C", "Option D"],
      "correct_answer": "Exact text of the correct option",
      "explanation": "Evidence-based explanation",
      "source_chunk_id": "Exact supplied chunk ID"
    }}
  ]
}}

Rules:
- Exactly four distinct options and one correct answer.
- The correct answer must exactly match an option.
- Use only supplied chunk IDs.
- Avoid questions relying on corrupted OCR.
- Return an empty questions array if evidence is insufficient.
- Return JSON only, without Markdown fences.

Retrieved passages:
{json.dumps(passages, ensure_ascii=False)}
"""

    try:
        client = genai.Client(
            api_key=api_key,
            http_options=types.HttpOptions(timeout=timeout * 1000),
        )

        for attempt in range(GEMINI_TRANSIENT_MAX_RETRIES + 1):
            try:
                response = client.models.generate_content(
                    model=model,
                    contents=prompt,
                    config=types.GenerateContentConfig(
                        response_mime_type="application/json",
                        temperature=0.1,
                    ),
                )
                break
            except Exception as exc:
                status_code = _gemini_http_status(exc)
                if (
                    status_code not in GEMINI_TRANSIENT_STATUS_CODES
                    or attempt == GEMINI_TRANSIENT_MAX_RETRIES
                ):
                    raise

                delay_seconds = min(0.5 * (2 ** attempt), 2.0)
                print(
                    f"Gemini quiz request returned HTTP {status_code}; "
                    f"retrying in {delay_seconds:g}s "
                    f"({attempt + 1}/{GEMINI_TRANSIENT_MAX_RETRIES})."
                )
                time.sleep(delay_seconds)

        if not response.text:
            raise ValueError("Gemini returned an empty response.")

        generated = json.loads(response.text)

        if not isinstance(generated, dict):
            raise ValueError("Invalid Gemini response.")

        raw_questions = generated.get("questions", [])

        if not isinstance(raw_questions, list):
            raise ValueError("Invalid questions list.")

        questions = []
        used_questions = set()

        for item in raw_questions:
            if not isinstance(item, dict):
                continue

            question = item.get("question")
            options = item.get("options")
            answer = item.get("correct_answer")
            explanation = item.get("explanation")
            chunk_id = item.get("source_chunk_id")

            if not all(
                isinstance(value, str) and value.strip()
                for value in [question, answer, explanation, chunk_id]
            ):
                continue

            if chunk_id not in source_map:
                continue

            if (
                not isinstance(options, list)
                or len(options) != 4
                or not all(
                    isinstance(option, str) and option.strip()
                    for option in options
                )
                or len({
                    option.strip().casefold() for option in options
                }) != 4
                or answer not in options
            ):
                continue

            question_key = question.strip().casefold()
            if question_key in used_questions:
                continue

            used_questions.add(question_key)
            source = source_map[chunk_id]

            questions.append({
                "question_id": f"q{len(questions) + 1}",
                "question": question.strip(),
                "type": "mcq",
                "options": options,
                "correct_answer": answer,
                "explanation": explanation.strip(),
                "source_chunk_id": chunk_id,
                "source_page": source.get("page_number"),
            })

            if len(questions) >= question_count:
                break

        if not questions:
            return {
                "topic": topic,
                "answerable": False,
                "questions": [],
                "sources": list(source_map.values()),
                "message": "No valid source-linked MCQs were generated.",
                "generated_by": None,
            }

        # Store answer keys privately on the server.
        quiz_id = uuid4().hex
        _QUIZ_STORE[quiz_id] = {
            question["question_id"]: {
                "correct_answer": question["correct_answer"],
                "explanation": question["explanation"],
                "source_page": question["source_page"],
            }
            for question in questions
        }

        # Deduplicate source records.
        unique_sources = list({
            question["source_chunk_id"]: source_map[
                question["source_chunk_id"]
            ]
            for question in questions
        }.values())

        # Never expose the answer key in the quiz-creation response.
        public_questions = [
            {
                key: value
                for key, value in question.items()
                if key != "correct_answer"
            }
            for question in questions
        ]

        return {
            "quiz_id": quiz_id,
            "topic": topic,
            "answerable": True,
            "questions": public_questions,
            "sources": unique_sources,
            "message": (
                "MCQs generated from textbook passages. "
                "OCR-derived content should be reviewed."
            ),
            "generated_by": model,
        }

    except Exception as exc:
        safe_message = str(exc).replace(api_key, "[REDACTED]")
        status_code = _gemini_http_status(exc)
        if status_code == 503:
            message = (
                "Gemini is temporarily unavailable (HTTP 503) after "
                f"{GEMINI_TRANSIENT_MAX_RETRIES + 1} attempts. Retry shortly. "
                "No quiz questions were returned."
            )
        elif status_code == 504:
            message = (
                f"Gemini exceeded its {timeout}-second request deadline "
                "(HTTP 504) after "
                f"{GEMINI_TRANSIENT_MAX_RETRIES + 1} attempts. Retry shortly "
                "or increase LLM_TIMEOUT_SECONDS if this continues. "
                "No quiz questions were returned."
            )
        elif status_code in {401, 403}:
            message = (
                "Gemini rejected the configured credentials. Verify "
                "LLM_API_KEY and the associated project access."
            )
        elif status_code == 404:
            message = (
                "Gemini did not recognize the configured model or endpoint. "
                "Verify LLM_MODEL against the models enabled for this project."
            )
        elif status_code == 429:
            message = (
                "Gemini rate-limited quiz generation. Retry shortly; "
                "no quiz questions were returned."
            )
        else:
            message = (
                "Gemini could not complete quiz generation. Review the "
                "sanitized backend error log; no quiz questions were returned."
            )
        print(
            f"Quiz generation error: {type(exc).__name__}: {safe_message}"
        )
        return {
            "topic": topic,
            "answerable": False,
            "questions": [],
            "sources": list(source_map.values()),
            "message": message,
            "generated_by": None,
        }


def submit_quiz(
    quiz_id: str,
    answers: list[dict[str, str]],
) -> dict[str, Any]:
    """Score submitted answers using the server-side answer key."""

    answer_key = _QUIZ_STORE.get(quiz_id)

    if answer_key is None:
        return {
            "success": False,
            "message": "Quiz not found or expired. Generate a new quiz.",
        }

    submitted = {}

    for answer in answers:
        question_id = answer.get("question_id")
        selected = answer.get("selected_answer")

        if not isinstance(question_id, str):
            continue
        if not isinstance(selected, str):
            continue
        if question_id in answer_key and question_id not in submitted:
            submitted[question_id] = selected

    results = []
    correct_count = 0

    for question_id, data in answer_key.items():
        selected = submitted.get(question_id)
        correct_answer = data["correct_answer"]
        is_correct = selected == correct_answer

        if is_correct:
            correct_count += 1

        results.append({
            "question_id": question_id,
            "answered": selected is not None,
            "is_correct": is_correct,
            "correct_answer": correct_answer,
            "explanation": data["explanation"],
            "source_page": data["source_page"],
        })

    total = len(answer_key)

    return {
        "success": True,
        "quiz_id": quiz_id,
        "score": correct_count,
        "total": total,
        "percentage": round(correct_count / total * 100, 2) if total else 0,
        "correct_count": correct_count,
        "wrong_count": total - correct_count,
        "results": results,
    }
