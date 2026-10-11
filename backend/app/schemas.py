
from typing import Literal, Optional

from pydantic import BaseModel, Field


# --------------------------------------------------
# Search
# --------------------------------------------------

class SearchRequest(BaseModel):
    query: str = Field(min_length=1, max_length=300)
    top_k: int = Field(default=5, ge=1, le=10)


# --------------------------------------------------
# Study Notes
# --------------------------------------------------

class NotesRequest(BaseModel):
    query: str = Field(min_length=1, max_length=300)
    top_k: int = Field(default=5, ge=1, le=10)


class NotesSection(BaseModel):
    heading: str
    type: Optional[str] = None
    content: str
    citations: list[str] = Field(default_factory=list)


class NotesSource(BaseModel):
    chunk_id: str
    book_id: Optional[str] = None
    source_file_id: Optional[str] = None
    title: Optional[str] = None
    author: Optional[str] = None
    edition: Optional[str] = None
    pdf_page_index: Optional[int] = None
    page_number: Optional[int] = None
    pdf_page_base: Optional[int] = None
    printed_page_label: Optional[str] = None
    printed_page_verified: Optional[bool] = None
    section_heading: Optional[str] = None
    excerpt: Optional[str] = None
    score: Optional[float] = None
    access_status: Optional[str] = None
    extraction_method: Optional[str] = None
    corpus_version: Optional[str] = None
    is_sample_data: Optional[bool] = None


class NotesResponse(BaseModel):
    query: str
    answerable: bool
    message: Optional[str] = None
    title: Optional[str] = None
    sections: list[NotesSection] = Field(default_factory=list)
    sources: list[NotesSource] = Field(default_factory=list)
    limitations: list[str] = Field(default_factory=list)
    disclaimer: Optional[str] = None
    generated_by: Optional[str] = None


# --------------------------------------------------
# Topic-Based Quiz Generation
# --------------------------------------------------

class QuizRequest(BaseModel):
    topic: str = Field(min_length=1, max_length=300)
    question_count: int = Field(default=5, ge=1, le=10)


class QuizQuestion(BaseModel):
    question_id: str
    question: str
    type: str
    options: list[str]
    explanation: Optional[str] = None
    source_chunk_id: Optional[str] = None
    source_page: Optional[int] = None


class QuizSource(BaseModel):
    chunk_id: str
    book_id: Optional[str] = None
    title: Optional[str] = None
    page_number: Optional[int] = None
    pdf_page_index: Optional[int] = None
    extraction_method: Optional[str] = None


class QuizResponse(BaseModel):
    quiz_id: Optional[str] = None
    topic: str
    answerable: bool
    questions: list[QuizQuestion] = Field(default_factory=list)
    sources: list[QuizSource] = Field(default_factory=list)
    message: Optional[str] = None
    generated_by: Optional[str] = None


# --------------------------------------------------
# Quiz Submission
# --------------------------------------------------

class QuizAnswer(BaseModel):
    question_id: str = Field(min_length=1)
    selected_answer: str = Field(min_length=1)


class QuizSubmitRequest(BaseModel):
    quiz_id: str = Field(min_length=1)
    answers: list[QuizAnswer] = Field(max_length=10)


class QuizResult(BaseModel):
    question_id: str
    answered: bool
    is_correct: bool
    correct_answer: str
    explanation: str
    source_page: Optional[int] = None


class QuizSubmitResponse(BaseModel):
    success: bool
    quiz_id: str
    score: int
    total: int
    percentage: float
    correct_count: int
    wrong_count: int
    results: list[QuizResult] = Field(default_factory=list)
