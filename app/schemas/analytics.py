from typing import List, Dict, Any
from pydantic import BaseModel


class UserAnalytics(BaseModel):
    user_id: int
    name: str
    overall_readiness_index: float
    scores: Dict[str, float]
    gaps: List[Dict[str, Any]]
    assessments_taken: int
    average_quiz_score: float


class AdminAnalytics(BaseModel):
    total_users: int
    average_readiness_index: float
    domain_gap_heatmap: Dict[str, float]
    top_gap_domain: str
    total_assessments: int
