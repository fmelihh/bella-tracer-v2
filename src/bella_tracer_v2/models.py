from pydantic import BaseModel, Field
from typing import Optional, TypedDict, Any


class QueryRequest(BaseModel):
    question: str
    session_id: Optional[str] = "default_session"


class QueryResponse(BaseModel):
    answer: str
    original_question: str
    optimized_question: str
    extracted_dates: dict
    context_sources: list[str]


class GraphState(TypedDict):
    original_question: str
    optimized_question: str
    extracted_filters: dict
    retrieved_docs: list[Any]
    reranked_docs: list[Any]
    final_answer: str


class RankedDocument(BaseModel):
    index: int = Field(
        description="The original index of the document in the provided list"
    )
    relevance_score: float = Field(description="Relevance score between 0.0 and 1.0")
    reasoning: str = Field(description="Short explanation of why this log is relevant")


class RankingOutput(BaseModel):
    ranked_results: list[RankedDocument]
