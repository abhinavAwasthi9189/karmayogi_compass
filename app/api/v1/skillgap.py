from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import Session, select

from app.database import get_session
from app.models import User, CompetencyProfile
from app.schemas.skillgap import SkillGapResponse
from app.api.deps import get_current_user
from app.services.skillgap_service import compute_skill_gaps, persist_gaps

router = APIRouter(prefix="/skillgap", tags=["Skill Gap"])


@router.get("/{user_id}", response_model=SkillGapResponse)
def get_skill_gap(
    user_id: int, current_user: User = Depends(get_current_user), session: Session = Depends(get_session),
):
    if current_user.role != "admin" and current_user.id != user_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Cannot view another user's skill gap")

    user = session.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    profile = session.exec(select(CompetencyProfile).where(CompetencyProfile.user_id == user_id)).first()
    if not profile:
        raise HTTPException(status_code=404, detail="Competency profile not found")

    gaps = compute_skill_gaps(session, user, profile)
    persist_gaps(session, profile, gaps)
    priority = gaps[0]["domain"] if gaps and gaps[0]["gap"] > 0 else None

    return SkillGapResponse(user_id=user_id, designation=user.designation, gaps=gaps, priority_domain=priority)
