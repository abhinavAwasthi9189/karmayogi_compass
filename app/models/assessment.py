from datetime import datetime
from typing import Optional, List, Dict, Any
from sqlmodel import SQLModel, Field, Column, JSON


class Assessment(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="user.id", index=True)
    course_id: Optional[int] = Field(default=None, foreign_key="course.id")
    questions: List[Dict[str, Any]] = Field(default_factory=list, sa_column=Column(JSON))
    answers: List[int] = Field(default_factory=list, sa_column=Column(JSON))
    score: Optional[float] = None
    domain_breakdown: Dict[str, Any] = Field(default_factory=dict, sa_column=Column(JSON))
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    source_document: str = ""
