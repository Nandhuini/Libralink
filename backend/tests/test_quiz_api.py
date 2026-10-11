import json
from types import SimpleNamespace

from fastapi.testclient import TestClient

from app.main import app
from app.services import quiz


class TemporaryUnavailable(Exception):
    code = 503

    def __str__(self):
        return "503 UNAVAILABLE"


class TemporaryDeadlineExceeded(Exception):
    code = 504

    def __str__(self):
        return "504 DEADLINE_EXCEEDED"


def source_passage():
    return {
        "chunk_id": "chunk-normal-1",
        "book_id": "book-stats",
        "title": "Statistics Textbook",
        "page_number": 42,
        "pdf_page_index": 41,
        "excerpt": "A normal distribution is symmetric around its mean.",
        "extraction_method": "pymupdf_text",
    }


def configure_quiz(monkeypatch):
    monkeypatch.setenv("LLM_PROVIDER", "gemini")
    monkeypatch.setenv("LLM_API_KEY", "test-key-not-a-secret")
    monkeypatch.setenv("LLM_MODEL", "test-configured-model")
    monkeypatch.setenv("LLM_TIMEOUT_SECONDS", "1")
    monkeypatch.setattr(
        quiz.retrieval,
        "search",
        lambda topic, top_k: [source_passage()],
    )
    monkeypatch.setattr(quiz, "_QUIZ_STORE", {})


def generated_question():
    return {
        "question": "What is the shape of a normal distribution?",
        "options": [
            "Symmetric around its mean",
            "Always increasing",
            "Uniform across all values",
            "Defined only for integers",
        ],
        "correct_answer": "Symmetric around its mean",
        "explanation": "The retrieved passage states that it is symmetric around its mean.",
        "source_chunk_id": "chunk-normal-1",
    }


def test_quiz_api_retries_503_and_hides_answer_key(monkeypatch):
    configure_quiz(monkeypatch)
    monkeypatch.setattr(quiz.time, "sleep", lambda _delay: None)
    calls = []

    class FakeModels:
        def generate_content(self, **kwargs):
            calls.append(kwargs)
            if len(calls) == 1:
                raise TemporaryUnavailable()
            return SimpleNamespace(
                text=json.dumps({"questions": [generated_question()]})
            )

    client = SimpleNamespace(models=FakeModels())
    monkeypatch.setattr(quiz.genai, "Client", lambda **_kwargs: client)

    response = TestClient(app).post(
        "/api/quiz",
        json={"topic": "normal distribution", "question_count": 1},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["answerable"] is True
    assert body["topic"] == "normal distribution"
    assert len(body["questions"]) == 1
    assert body["questions"][0]["options"] == generated_question()["options"]
    assert "correct_answer" not in body["questions"][0]
    assert body["questions"][0]["source_page"] == 42
    assert body["generated_by"] == "test-configured-model"
    assert len(calls) == 2
    assert all(call["model"] == "test-configured-model" for call in calls)


def test_quiz_api_reports_503_after_bounded_retries(monkeypatch):
    configure_quiz(monkeypatch)
    monkeypatch.setattr(quiz.time, "sleep", lambda _delay: None)
    calls = []

    class FakeModels:
        def generate_content(self, **_kwargs):
            calls.append(True)
            raise TemporaryUnavailable()

    client = SimpleNamespace(models=FakeModels())
    monkeypatch.setattr(quiz.genai, "Client", lambda **_kwargs: client)

    response = TestClient(app).post(
        "/api/quiz",
        json={"topic": "normal distribution", "question_count": 1},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["answerable"] is False
    assert body["questions"] == []
    assert "HTTP 503" in body["message"]
    assert "Retry shortly" in body["message"]
    assert "test-key-not-a-secret" not in response.text
    assert len(calls) == quiz.GEMINI_TRANSIENT_MAX_RETRIES + 1


def test_quiz_api_reports_deadline_after_bounded_retries(monkeypatch):
    configure_quiz(monkeypatch)
    monkeypatch.setattr(quiz.time, "sleep", lambda _delay: None)
    calls = []

    class FakeModels:
        def generate_content(self, **_kwargs):
            calls.append(True)
            raise TemporaryDeadlineExceeded()

    client = SimpleNamespace(models=FakeModels())
    monkeypatch.setattr(quiz.genai, "Client", lambda **_kwargs: client)

    response = TestClient(app).post(
        "/api/quiz",
        json={"topic": "normal distribution", "question_count": 1},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["answerable"] is False
    assert body["questions"] == []
    assert "1-second request deadline (HTTP 504)" in body["message"]
    assert "increase LLM_TIMEOUT_SECONDS" in body["message"]
    assert len(calls) == quiz.GEMINI_TRANSIENT_MAX_RETRIES + 1


def test_quiz_submit_api_scores_by_question_id(monkeypatch):
    configure_quiz(monkeypatch)
    quiz._QUIZ_STORE["api-test-quiz"] = {
        "q-second": {
            "correct_answer": "Right second",
            "explanation": "Second explanation.",
            "source_page": 8,
        },
        "q-first": {
            "correct_answer": "Right first",
            "explanation": "First explanation.",
            "source_page": 3,
        },
    }

    response = TestClient(app).post(
        "/api/quiz/submit",
        json={
            "quiz_id": "api-test-quiz",
            "answers": [
                {"question_id": "q-first", "selected_answer": "Right first"},
                {"question_id": "q-second", "selected_answer": "Wrong"},
            ],
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["score"] == 1
    assert body["total"] == 2
    assert body["percentage"] == 50
    assert body["correct_count"] == 1
    assert body["wrong_count"] == 1
    assert [item["question_id"] for item in body["results"]] == [
        "q-second",
        "q-first",
    ]
    assert body["results"][0]["source_page"] == 8


def test_quiz_api_rejects_invalid_generation_request():
    response = TestClient(app).post(
        "/api/quiz",
        json={"topic": "", "question_count": 11},
    )

    assert response.status_code == 422