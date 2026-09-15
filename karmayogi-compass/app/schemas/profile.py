from pydantic import BaseModel


class ProfileResponse(BaseModel):
    user_id: int
    name: str
    email: str
    role: str
    department: str
    designation: str
    statistical_score: float
    technical_score: float
    digital_gov_score: float
    managerial_score: float
