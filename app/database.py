"""DB engine/session management.

Serverless platforms (Vercel, Lambda, Cloud Run gen1, etc.) mount the
deployment bundle **read-only** and expose exactly one writable directory:
`/tmp`. A SQLite URL pointing at a relative path inside the bundle therefore
blows up at the first INSERT with:

    sqlite3.OperationalError: attempt to write a readonly database

Rather than sniffing a platform env var (`VERCEL`, `AWS_LAMBDA_*`, ...) -- which
is brittle, differs per platform, and isn't reliably injected into every runtime
-- we simply *ask the filesystem* whether we can write where the DB wants to
live. If we can't, we relocate to a writable temp directory. This is
platform-agnostic and a no-op during local development.

Caveat: `/tmp` on serverless is ephemeral and per-instance. Data written there
survives warm invocations but is lost on cold start, and is NOT shared between
concurrent instances. That's fine for a demo/seeded app; for real persistence
set DATABASE_URL to a hosted Postgres (Neon, Supabase, Vercel Postgres).
"""
from __future__ import annotations

import logging
import os
import shutil
import tempfile
import uuid
from pathlib import Path

from sqlalchemy.engine import make_url
from sqlmodel import SQLModel, Session, create_engine

from app.config import get_settings

logger = logging.getLogger(__name__)

settings = get_settings()


def _dir_is_writable(directory: Path) -> bool:
    """Actually try to create (and remove) a file. `os.access(W_OK)` lies on
    some overlay/read-only mounts, so we probe for real."""
    try:
        directory.mkdir(parents=True, exist_ok=True)
        probe = directory / f".write-probe-{uuid.uuid4().hex}"
        with open(probe, "w") as fh:
            fh.write("ok")
        probe.unlink()
        return True
    except OSError:
        return False


def _file_is_writable(path: Path) -> bool:
    """An existing DB file must itself be writable -- SQLite also needs to
    create `-journal` / `-wal` siblings, hence the directory check too."""
    if not path.exists():
        return True
    try:
        with open(path, "r+b"):
            return True
    except OSError:
        return False


def _fallback_dir() -> Path:
    """Writable scratch space. Honours TMPDIR, falls back to /tmp."""
    return Path(os.environ.get("TMPDIR") or tempfile.gettempdir()) / "karmayogi-compass"


def _resolve_database_url(url_str: str) -> str:
    """Returns a DATABASE_URL guaranteed to point somewhere writable.

    Non-SQLite URLs and in-memory SQLite are returned untouched.
    """
    url = make_url(url_str)

    if not url.drivername.startswith("sqlite"):
        return url_str

    db_path_str = url.database
    # `sqlite://` / `sqlite:///:memory:` -- nothing on disk to worry about.
    if not db_path_str or db_path_str == ":memory:":
        return url_str

    db_path = Path(db_path_str).expanduser()
    if not db_path.is_absolute():
        db_path = (Path.cwd() / db_path).resolve()

    if _dir_is_writable(db_path.parent) and _file_is_writable(db_path):
        logger.info("SQLite database is writable at %s", db_path)
        return str(url.set(database=str(db_path)))

    # --- Read-only location: relocate to temp ---------------------------------
    fallback_dir = _fallback_dir()
    if not _dir_is_writable(fallback_dir):
        raise RuntimeError(
            f"Neither {db_path.parent} nor {fallback_dir} is writable. "
            "Set DATABASE_URL to a hosted database (e.g. Postgres)."
        )

    fallback_path = fallback_dir / db_path.name

    # If a pre-seeded .db shipped inside the read-only bundle, copy it across
    # once so we keep its data instead of starting from an empty schema.
    if db_path.exists() and not fallback_path.exists():
        try:
            shutil.copy2(db_path, fallback_path)
            logger.info("Copied bundled read-only database to %s", fallback_path)
        except OSError:
            logger.warning("Could not copy bundled database; starting fresh at %s", fallback_path)

    logger.warning(
        "%s is not writable (read-only filesystem?). Using %s instead. "
        "This storage is ephemeral -- set DATABASE_URL to a hosted database for real persistence.",
        db_path,
        fallback_path,
    )
    return str(url.set(database=str(fallback_path)))


DATABASE_URL = _resolve_database_url(settings.DATABASE_URL)

connect_args = {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}
engine = create_engine(DATABASE_URL, echo=False, connect_args=connect_args)


def init_db() -> None:
    # models must be imported before create_all so SQLModel.metadata knows about them
    import app.models  # noqa: F401
    SQLModel.metadata.create_all(engine)


def get_session():
    with Session(engine) as session:
        yield session
