from typing import List, Optional
from pydantic import BaseModel, Field


class CompassSuggestRequest(BaseModel):
    context: str = Field(..., description="What the user is currently learning, e.g. course/module title")


class CompassSuggestResponse(BaseModel):
    suggestions: List[str]


class CompassAskRequest(BaseModel):
    context: str = Field(..., description="What the user is currently learning, e.g. course/module title")
    question: str
    history: Optional[List[str]] = None


class CompassAskResponse(BaseModel):
    answer: str
