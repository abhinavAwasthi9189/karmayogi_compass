from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import Session, select

from app.database import get_session
from app.models import User, CompetencyProfile, CompetencyPassport
from app.schemas.auth import LoginRequest, RegisterRequest, TokenResponse
from app.services.auth_service import verify_password, hash_password, create_access_token

router = APIRouter(prefix="/auth", tags=["Auth"])


@router.post("/login", response_model=TokenResponse)
def login(payload: LoginRequest, session: Session = Depends(get_session)):
    user = session.exec(select(User).where(User.email == payload.email)).first()
    if not user or not verify_password(payload.password, user.hashed_password):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Incorrect email or password")
    token = create_access_token(user.id, user.role)
    return TokenResponse(access_token=token, user_id=user.id, name=user.name, role=user.role)


@router.post("/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
def register(payload: RegisterRequest, session: Session = Depends(get_session)):
    existing = session.exec(select(User).where(User.email == payload.email)).first()
    if existing:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="An account with this email already exists")

    user = User(
        name=payload.name,
        email=payload.email,
        hashed_password=hash_password(payload.password),
        role="official",
        department=payload.department,
        designation=payload.designation,
    )
    session.add(user)
    session.commit()
    session.refresh(user)

    # New accounts start with an empty competency profile/passport; the
    # assessment flow is what actually fills these scores in.
    session.add(CompetencyProfile(user_id=user.id))
    session.add(CompetencyPassport(user_id=user.id))
    session.commit()

    token = create_access_token(user.id, user.role)
    return TokenResponse(access_token=token, user_id=user.id, name=user.name, role=user.role)
