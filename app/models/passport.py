from datetime import datetime
from typing import Optional, List, Dict, Any
from sqlmodel import SQLModel, Field, Column, JSON


class CompetencyPassport(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="user.id", unique=True, index=True)
    validated_skills: List[Dict[str, Any]] = Field(default_factory=list, sa_column=Column(JSON))
    overall_readiness_index: float = 0.0
    last_updated: datetime = Field(default_factory=datetime.utcnow)
