from typing import List
from pydantic import BaseModel


class DomainGap(BaseModel):
    domain: str
    current: float
    required: float
    gap: float


class SkillGapResponse(BaseModel):
    user_id: int
    designation: str
    gaps: List[DomainGap]
    priority_domain: str | None = None
