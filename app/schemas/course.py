from typing import List
from pydantic import BaseModel


class CourseOut(BaseModel):
    id: str
    title: str
    domain: str
    source: str
    launch_url: str
    description: str = ""


class RecommendationResponse(BaseModel):
    user_id: int
    based_on_gaps: List[str]
    courses: List[CourseOut]
