"""Seeds demo users/profiles/passports on first startup so the API is usable immediately."""
from sqlmodel import Session, select
from app.models import User, CompetencyProfile, CompetencyPassport
from app.adapters.mock_data import SEED_USERS, DOMAINS
from app.services.auth_service import hash_password

DEMO_PASSWORD = "Karmayogi@123"


def seed_demo_data(session: Session) -> None:
    for entry in SEED_USERS:
        already_exists = session.exec(select(User).where(User.email == entry["email"])).first()
        if already_exists:
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
            overall_readiness_index=round(sum(entry["scores"].values()) / len(DOMAINS), 2),
        )
        session.add(passport)
        session.commit()
