"""Gemini client for LibraLink study-note generation."""

import json
import os
from typing import Any

from dotenv import load_dotenv
from google import genai
from google.genai import types

load_dotenv()


class LLMUnavailableError(RuntimeError):
    """Raised when Gemini cannot generate a response."""


def generate_structured_notes(
    query: str,
    passages: list[dict[str, Any]],
) -> dict[str, Any]:
    """Generate draft study-note sections grounded in retrieved passages."""

    provider = os.getenv("LLM_PROVIDER", "").strip().lower()
    api_key = os.getenv("LLM_API_KEY", "").strip()
    model = os.getenv("LLM_MODEL", "").strip()
    timeout_seconds = int(os.getenv("LLM_TIMEOUT_SECONDS", "30"))

    if provider != "gemini":
        raise LLMUnavailableError(
            "LLM_PROVIDER must be set to 'gemini'."
        )

    if not api_key:
        raise LLMUnavailableError("Gemini API key is not configured.")

    if not model:
        raise LLMUnavailableError("LLM_MODEL is not configured.")

    usable_passages = []

    for passage in passages:
        if not isinstance(passage, dict):
            continue

        chunk_id = passage.get("chunk_id")
        excerpt = passage.get("excerpt")

        if (
            isinstance(chunk_id, str)
            and chunk_id.strip()
            and isinstance(excerpt, str)
            and excerpt.strip()
        ):
            usable_passages.append(
                {
                    "chunk_id": chunk_id,
                    "title": passage.get("title"),
                    "author": passage.get("author"),
                    "excerpt": excerpt,
                }
            )

    if not usable_passages:
        raise LLMUnavailableError(
            "No usable retrieved passages were provided."
        )

    prompt = f"""
You are the study-note assistant for LibraLink.

Answer the student's question using ONLY the retrieved passages below.
Do not use outside knowledge to fill gaps.
If the passages do not support an answer, return an empty sections array.

Return valid JSON with this exact structure:
{{
  "title": "A concise title",
  "sections": [
    {{
      "heading": "Section heading",
      "content": "Study notes supported by the passages",
      "citations": ["chunk-id-from-the-input"]
    }}
  ]
}}

Rules:
- Cite only chunk IDs included in the retrieved passages.
- Never invent book titles, authors, page numbers, or chunk IDs.
- Do not claim that a passage says something it does not say.
- If sources disagree, describe the disagreement and cite both sources.
- Keep the notes clear and useful for a student.
- If evidence is insufficient, return {{"title": "Insufficient evidence",
  "sections": []}}.

Student question:
{query}

Retrieved passages:
{json.dumps(usable_passages, ensure_ascii=False)}
"""

    try:
        client = genai.Client(
            api_key=api_key,
            http_options=types.HttpOptions(
                timeout=timeout_seconds * 1000
            ),
        )

        response = client.models.generate_content(
            model=model,
            contents=prompt,
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                temperature=0.2,
            ),
        )

        response_text = response.text

        if not response_text:
            raise LLMUnavailableError(
                "Gemini returned an empty response."
            )

        result = json.loads(response_text)

        if not isinstance(result, dict):
            raise LLMUnavailableError(
                "Gemini returned an invalid response structure."
            )

        sections = result.get("sections")

        if not isinstance(sections, list):
            raise LLMUnavailableError(
                "Gemini response did not contain a sections list."
            )

        return {
            "title": str(result.get("title", "Study Notes")),
            "sections": sections,
        }

    except LLMUnavailableError:
        raise
    except Exception as exc:
        # Print the provider error for local debugging.
        # Never print the API key.
        safe_message = str(exc).replace(api_key, "[REDACTED]")
        print(f"Gemini debug error: {type(exc).__name__}: {safe_message}")

        raise LLMUnavailableError(
            "Gemini could not generate study notes. "
            "See the local debug message for details."
        ) from exc
