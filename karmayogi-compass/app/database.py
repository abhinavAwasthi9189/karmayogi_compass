"""DB engine/session management."""
from sqlmodel import SQLModel, Session, create_engine
from app.config import get_settings

settings = get_settings()
connect_args = {"check_same_thread": False} if settings.DATABASE_URL.startswith("sqlite") else {}
engine = create_engine(settings.DATABASE_URL, echo=False, connect_args=connect_args)


def init_db() -> None:
    # models must be imported before create_all so SQLModel.metadata knows about them
    import app.models  # noqa: F401
    SQLModel.metadata.create_all(engine)


def get_session():
    with Session(engine) as session:
        yield session
