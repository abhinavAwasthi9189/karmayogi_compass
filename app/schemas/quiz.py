from typing import List, Optional
from pydantic import BaseModel, Field


class QuizOption(BaseModel):
    label: str        # "A" | "B" | "C" | "D"
    text: str


class QuizQuestion(BaseModel):
    id: int
    domain: str
    scenario: str
    question: str
    options: List[QuizOption]
    correct_option: Optional[str] = None   # stripped before returning to client
    explanation: Optional[str] = None
    citation: str                          # e.g. "Source PDF, p.4"
    difficulty: str = "medium"


class QuizGenerateResponse(BaseModel):
    assessment_id: int
    user_id: int
    domain_weighting: dict
    questions: List[QuizQuestion]


class QuizSubmitRequest(BaseModel):
    assessment_id: int
    user_id: int
    answers: List[str] = Field(..., description="Selected option label per question, in order")

class QuizReviewItem(BaseModel):
    id: int
    domain: str
    scenario: str
    question: str
    options: List[QuizOption]
    your_answer: Optional[str] = None
    correct_option: str
    is_correct: bool
    explanation: str
    citation: str

class QuizSubmitResponse(BaseModel):
    assessment_id: int
    score: float
    correct_count: int
    total_questions: int
    domain_breakdown: dict
    updated_scores: dict
    overall_readiness_index: float
    review: List[QuizReviewItem]