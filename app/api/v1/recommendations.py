from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import Session, select

from app.database import get_session
from app.models import User, CompetencyProfile
from app.schemas.course import RecommendationResponse, CourseOut
from app.api.deps import get_current_user
from app.services.skillgap_service import compute_skill_gaps
from app.services.recommendation_service import recommend_courses
from app.adapters.factory import get_igot_adapter

router = APIRouter(prefix="/recommendations", tags=["Recommendations"])


@router.get("/{user_id}", response_model=RecommendationResponse)
async def get_recommendations(
    user_id: int, current_user: User = Depends(get_current_user), session: Session = Depends(get_session),
):
    if current_user.role != "admin" and current_user.id != user_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Cannot view another user's recommendations")

    user = session.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    profile = session.exec(select(CompetencyProfile).where(CompetencyProfile.user_id == user_id)).first()
    if not profile:
        raise HTTPException(status_code=404, detail="Competency profile not found")

    gaps = compute_skill_gaps(session, user, profile)
    adapter = get_igot_adapter()
    courses = await recommend_courses(adapter, gaps)

    return RecommendationResponse(
        user_id=user_id,
        based_on_gaps=[g["domain"] for g in gaps if g["gap"] > 0],
        courses=[CourseOut(**c) for c in courses],
    )
