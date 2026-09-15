"""Seeds demo users/profiles/passports on first startup so the API is usable immediately.

Also handles two housekeeping jobs so a long-lived local database stays in sync
with SEED_USERS:

* **Migration** - if a seed entry lists `legacy_emails`, an existing account under
  one of those addresses is renamed/re-pointed in place instead of a duplicate
  account being created alongside it.
* **Reset** - `reset_seed_user()` wipes a demo user's accumulated practice data
  (assessments, validated skills, gap analysis) and puts their scores back to the
  baseline in SEED_USERS. Used by `scripts/reset_user.py`.
"""
from typing import Optional

from sqlmodel import Session, select, delete

from app.models import User, CompetencyProfile, CompetencyPassport, Assessment
from app.adapters.mock_data import SEED_USERS, DOMAINS
from app.services.auth_service import hash_password

DEMO_PASSWORD = "Karmayogi@123"


def _baseline_readiness(scores: dict) -> float:
    return round(sum(scores.values()) / len(DOMAINS), 2)


def _find_seed_entry(email: str) -> Optional[dict]:
    """Looks up a SEED_USERS entry by its current or any of its legacy emails."""
    email = email.strip().lower()
    for entry in SEED_USERS:
        if entry["email"].lower() == email:
            return entry
        if email in [e.lower() for e in entry.get("legacy_emails", [])]:
            return entry
    return None


def seed_demo_data(session: Session) -> None:
    for entry in SEED_USERS:
        user = session.exec(select(User).where(User.email == entry["email"])).first()

        # An account may still be sitting under a previous email - migrate it in place.
        if not user:
            for legacy in entry.get("legacy_emails", []):
                user = session.exec(select(User).where(User.email == legacy)).first()
                if user:
                    user.email = entry["email"]
                    user.name = entry["name"]
                    session.add(user)
                    session.commit()
                    break

        if user:
            # Keep display fields aligned with SEED_USERS, but leave earned data alone.
            if user.name != entry["name"]:
                user.name = entry["name"]
                session.add(user)
                session.commit()
            continue

        user = User(
            name=entry["name"], email=entry["email"], hashed_password=hash_password(DEMO_PASSWORD),
            role=entry["role"], department=entry["department"], designation=entry["designation"],
        )
        session.add(user)
        session.commit()
        session.refresh(user)

        profile = CompetencyProfile(user_id=user.id, **entry["scores"])
        session.add(profile)

        passport = CompetencyPassport(
            user_id=user.id,
            overall_readiness_index=_baseline_readiness(entry["scores"]),
        )
        session.add(passport)
        session.commit()


def reset_seed_user(session: Session, email: str) -> str:
    """Clears a demo user's practice history and restores their baseline scores.

    Returns a human-readable summary of what was removed. Raises ValueError if the
    email doesn't belong to a seeded demo user or no such account exists.
    """
    entry = _find_seed_entry(email)
    if not entry:
        raise ValueError(f"{email} is not one of the seeded demo users.")

    user = session.exec(select(User).where(User.email == entry["email"])).first()
    if not user:
        for legacy in entry.get("legacy_emails", []):
            user = session.exec(select(User).where(User.email == legacy)).first()
            if user:
                break
    if not user:
        raise ValueError(f"No account found for {entry['email']} - start the app once to seed it.")

    # Bring identity fields back in line with SEED_USERS (handles the rename too).
    user.name = entry["name"]
    user.email = entry["email"]
    user.role = entry["role"]
    user.department = entry["department"]
    user.designation = entry["designation"]
    session.add(user)

    assessments = session.exec(select(Assessment).where(Assessment.user_id == user.id)).all()
    removed = len(assessments)
    for assessment in assessments:
        session.delete(assessment)

    profile = session.exec(
        select(CompetencyProfile).where(CompetencyProfile.user_id == user.id)
    ).first()
    if profile:
        for domain_field, value in entry["scores"].items():
            setattr(profile, domain_field, value)
        profile.identified_gaps = []
    else:
        profile = CompetencyProfile(user_id=user.id, **entry["scores"])
    session.add(profile)

    passport = session.exec(
        select(CompetencyPassport).where(CompetencyPassport.user_id == user.id)
    ).first()
    if passport:
        passport.validated_skills = []
        passport.overall_readiness_index = _baseline_readiness(entry["scores"])
    else:
        passport = CompetencyPassport(
            user_id=user.id, overall_readiness_index=_baseline_readiness(entry["scores"])
        )
    session.add(passport)

    session.commit()
    return (
        f"Reset {user.name} <{user.email}>: removed {removed} assessment(s), "
        f"cleared validated skills and gap analysis, restored baseline scores "
        f"(readiness {_baseline_readiness(entry['scores'])})."
    )
