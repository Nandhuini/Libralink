from typing import Literal, Optional

from pydantic import BaseModel, Field


class SearchRequest(BaseModel):
    query: str = Field(min_length=1, max_length=300)
    top_k: int = Field(default=5, ge=1, le=10)


class NotesRequest(BaseModel):
    query: str = Field(min_length=1, max_length=300)
    top_k: int = Field(default=5, ge=1, le=10)


class Source(BaseModel):
    chunk_id: str
    book_id: str
    title: str
    page_index: int
    access_status: str


class NotesResponse(BaseModel):
    answerable: bool
    query: str
    mode: Literal["llm", "extractive"] = "extractive"
    generated_by: Optional[dict] = None
    sections: list[dict] = Field(default_factory=list)
    sources: list[Source] = Field(default_factory=list)
    message: Optional[str] = None