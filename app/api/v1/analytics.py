from typing import Union
from fastapi import APIRouter, Depends
from sqlmodel import Session, select

from app.database import get_session
from app.models import User, CompetencyProfile, CompetencyPassport, Assessment
from app.schemas.analytics import UserAnalytics, AdminAnalytics
from app.api.deps import get_current_user
from app.adapters.mock_data import DOMAINS, DOMAIN_LABELS

router = APIRouter(prefix="/analytics", tags=["Analytics"])


def _user_dashboard(session: Session, user: User) -> UserAnalytics:
    profile = session.exec(select(CompetencyProfile).where(CompetencyProfile.user_id == user.id)).first()
    passport = session.exec(select(CompetencyPassport).where(CompetencyPassport.user_id == user.id)).first()
    assessments = session.exec(select(Assessment).where(Assessment.user_id == user.id)).all()
    scored = [a.score for a in assessments if a.score is not None]

    return UserAnalytics(
        user_id=user.id,
        name=user.name,
        overall_readiness_index=passport.overall_readiness_index if passport else 0.0,
        scores={f: getattr(profile, f) for f in DOMAINS} if profile else {},
        gaps=profile.identified_gaps if profile else [],
        assessments_taken=len(assessments),
        average_quiz_score=round(sum(scored) / len(scored), 2) if scored else 0.0,
    )


def _admin_dashboard(session: Session) -> AdminAnalytics:
    users = session.exec(select(User)).all()
    profiles = session.exec(select(CompetencyProfile)).all()
    passports = session.exec(select(CompetencyPassport)).all()
    assessments = session.exec(select(Assessment)).all()

    avg_readiness = round(sum(p.overall_readiness_index for p in passports) / len(passports), 2) if passports else 0.0

    heatmap = {}
    for field in DOMAINS:
        label = DOMAIN_LABELS[field]
        values = [max(0.0, 100 - getattr(p, field)) for p in profiles]  # gap proxy vs. ceiling
        heatmap[label] = round(sum(values) / len(values), 2) if values else 0.0
    top_gap_domain = max(heatmap, key=heatmap.get) if heatmap else "n/a"

    return AdminAnalytics(
        total_users=len(users),
        average_readiness_index=avg_readiness,
        domain_gap_heatmap=heatmap,
        top_gap_domain=top_gap_domain,
        total_assessments=len(assessments),
    )


@router.get("/dashboard", response_model=Union[UserAnalytics, AdminAnalytics])
def get_dashboard(user: User = Depends(get_current_user), session: Session = Depends(get_session)):
    if user.role == "admin":
        return _admin_dashboard(session)
    return _user_dashboard(session, user)
