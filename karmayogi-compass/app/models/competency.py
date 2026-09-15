from typing import Optional, List, Dict, Any
from sqlmodel import SQLModel, Field, Column, JSON


class CompetencyProfile(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="user.id", unique=True, index=True)
    statistical_score: float = 0.0
    technical_score: float = 0.0
    digital_gov_score: float = 0.0
    managerial_score: float = 0.0
    # list[{"domain": str, "current": float, "required": float, "gap": float}]
    identified_gaps: List[Dict[str, Any]] = Field(default_factory=list, sa_column=Column(JSON))
