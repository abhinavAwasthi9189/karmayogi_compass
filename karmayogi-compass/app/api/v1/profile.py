from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select

from app.database import get_session
from app.models import CompetencyProfile, User
from app.schemas.profile import ProfileResponse
from app.api.deps import get_current_user

router = APIRouter(prefix="/profile", tags=["Profile"])


@router.get("/me", response_model=ProfileResponse)
def get_my_profile(user: User = Depends(get_current_user), session: Session = Depends(get_session)):
    profile = session.exec(select(CompetencyProfile).where(CompetencyProfile.user_id == user.id)).first()
    if not profile:
        raise HTTPException(status_code=404, detail="Competency profile not found")
    return ProfileResponse(
        user_id=user.id, name=user.name, email=user.email, role=user.role,
        department=user.department, designation=user.designation,
        statistical_score=profile.statistical_score, technical_score=profile.technical_score,
        digital_gov_score=profile.digital_gov_score, managerial_score=profile.managerial_score,
    )
