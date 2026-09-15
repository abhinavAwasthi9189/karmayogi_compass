"""Computes competency gaps: delta = Required_Level - Current_Level per domain."""
from sqlmodel import Session
from app.models import User, CompetencyProfile
from app.adapters.mock_data import REQUIRED_LEVELS_BY_DESIGNATION, DOMAINS, DOMAIN_LABELS


def get_required_levels(designation: str) -> dict:
    return REQUIRED_LEVELS_BY_DESIGNATION.get(designation, REQUIRED_LEVELS_BY_DESIGNATION["DEFAULT"])


def compute_skill_gaps(session: Session, user: User, profile: CompetencyProfile) -> list[dict]:
    required = get_required_levels(user.designation)
    gaps = []
    for domain_field in DOMAINS:
        current = getattr(profile, domain_field)
        req_level = required[domain_field]
        delta = round(req_level - current, 2)
        gaps.append({
            "domain": DOMAIN_LABELS[domain_field],
            "current": current,
            "required": req_level,
            "gap": max(delta, 0.0),
        })
    gaps.sort(key=lambda g: g["gap"], reverse=True)
    return gaps


def persist_gaps(session: Session, profile: CompetencyProfile, gaps: list[dict]) -> None:
    # only positive gaps are "identified gaps" needing remediation
    profile.identified_gaps = [g for g in gaps if g["gap"] > 0]
    session.add(profile)
    session.commit()
    session.refresh(profile)
