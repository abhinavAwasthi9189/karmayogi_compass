"""DB engine/session management for both local SQLite and hosted Postgres (Neon).

Two separate problems are solved here.

**SQLite on a read-only filesystem.** Serverless platforms mount the deployment
bundle read-only and expose only `/tmp` as writable, so a relative SQLite path
fails at the first INSERT with `attempt to write a readonly database`. Rather
than sniffing a platform env var (brittle, differs per platform, not reliably
injected), we ask the filesystem directly whether we can write, and relocate to
a temp directory if not.

**Postgres on serverless.** Neon (and any hosted Postgres) needs a `postgresql://`
scheme, TLS, and -- importantly -- no long-lived connection pool. A serverless
instance gets frozen between invocations, so pooled connections go stale and
come back as `SSL connection has been closed unexpectedly` or
`server closed the connection unexpectedly`. We use NullPool so each request
opens and closes its own connection, and let Neon's PgBouncer endpoint do the
actual pooling.
"""
from __future__ import annotations

import logging
import os
import shutil
import tempfile
import uuid
from pathlib import Path

from sqlalchemy.engine import make_url
from sqlalchemy.pool import NullPool
from sqlmodel import SQLModel, Session, create_engine

from app.config import get_settings

logger = logging.getLogger(__name__)

settings = get_settings()

# Bump this whenever this file changes. Exposed at /api/health/db so you can
# confirm which revision a deployment is actually running, instead of assuming
# a push went live.
DB_RESOLVER_VERSION = "2026-09-17.3-postgres+writable-probe"

# Populated at import time so the health endpoint can explain what happened.
RESOLUTION_INFO: dict = {}

# Env vars the Vercel/Neon integration may inject. Checked in order, and only
# if DATABASE_URL was left at its SQLite default -- an explicit DATABASE_URL
# always wins.
NEON_ENV_FALLBACKS = (
    "DATABASE_URL",
    "POSTGRES_URL",
    "POSTGRES_URL_NON_POOLING",
    "DATABASE_URL_UNPOOLED",
)

SQLITE_DEFAULT = "sqlite:///./karmayogi_compass.db"


# ---------------------------------------------------------------------------
# Filesystem probes (SQLite only)
# ---------------------------------------------------------------------------

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


def _looks_serverless() -> bool:
    """Belt-and-braces signal only -- the writability probe is the real test."""
    return any(
        os.environ.get(k)
        for k in ("VERCEL", "AWS_LAMBDA_FUNCTION_NAME", "LAMBDA_TASK_ROOT", "FUNCTION_TARGET", "K_SERVICE")
    )


def _fallback_dir() -> Path:
    return Path(os.environ.get("TMPDIR") or tempfile.gettempdir()) / "karmayogi-compass"


# ---------------------------------------------------------------------------
# URL resolution
# ---------------------------------------------------------------------------

def _pick_configured_url() -> str:
    """Explicit non-default DATABASE_URL wins. Otherwise fall back to whatever
    Postgres URL the platform injected, so a Neon integration works without
    also editing .env."""
    configured = (settings.DATABASE_URL or "").strip()
    if configured and configured != SQLITE_DEFAULT:
        return configured

    for key in NEON_ENV_FALLBACKS:
        value = (os.environ.get(key) or "").strip()
        if value and value != SQLITE_DEFAULT:
            logger.info("Using database URL from %s", key)
            return value

    return configured or SQLITE_DEFAULT


def _normalise_postgres(url):
    """Neon/Heroku hand out `postgres://`, which SQLAlchemy 2 rejects outright
    (`Can't load plugin: sqlalchemy.dialects:postgres`). Map it to the psycopg2
    dialect and make sure TLS is on -- Neon refuses plaintext connections."""
    if url.drivername in ("postgres", "postgresql"):
        url = url.set(drivername="postgresql+psycopg2")

    query = dict(url.query)
    if "sslmode" not in query:
        query["sslmode"] = "require"
        url = url.set(query=query)
    return url


def _resolve_sqlite(url, url_str: str) -> str:
    db_path_str = url.database
    # `sqlite://` / `sqlite:///:memory:` -- nothing on disk to worry about.
    if not db_path_str or db_path_str == ":memory:":
        RESOLUTION_INFO.update(backend="sqlite-memory", relocated=False, active_path=db_path_str)
        return url_str

    db_path = Path(db_path_str).expanduser()
    if not db_path.is_absolute():
        db_path = (Path.cwd() / db_path).resolve()

    dir_ok = _dir_is_writable(db_path.parent)
    file_ok = _file_is_writable(db_path)
    serverless = _looks_serverless()

    RESOLUTION_INFO.update(
        cwd=str(Path.cwd()),
        candidate_path=str(db_path),
        dir_writable=dir_ok,
        file_writable=file_ok,
        serverless_markers=serverless,
    )

    if dir_ok and file_ok and not serverless:
        logger.info("SQLite database is writable at %s", db_path)
        RESOLUTION_INFO.update(relocated=False, active_path=str(db_path))
        return str(url.set(database=str(db_path)))

    fallback_dir = _fallback_dir()
    if not _dir_is_writable(fallback_dir):
        raise RuntimeError(
            f"Neither {db_path.parent} nor {fallback_dir} is writable. "
            "Set DATABASE_URL to a hosted database (e.g. Neon Postgres)."
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

    RESOLUTION_INFO.update(relocated=True, active_path=str(fallback_path))
    logger.warning(
        "%s is not usable for writes (read-only filesystem / serverless). Using %s instead. "
        "This storage is ephemeral -- point DATABASE_URL at Neon Postgres for real persistence.",
        db_path,
        fallback_path,
    )
    return str(url.set(database=str(fallback_path)))


def _resolve_database_url() -> str:
    url_str = _pick_configured_url()
    url = make_url(url_str)

    RESOLUTION_INFO.update(
        version=DB_RESOLVER_VERSION,
        configured_scheme=url.drivername,
    )

    if url.drivername.startswith("sqlite"):
        RESOLUTION_INFO.setdefault("backend", "sqlite")
        return _resolve_sqlite(url, url_str)

    if "postgres" in url.drivername:
        url = _normalise_postgres(url)
        RESOLUTION_INFO.update(
            backend="postgres",
            relocated=False,
            resolved_scheme=url.drivername,
            host=url.host,
            database=url.database,
            # Neon's PgBouncer endpoint; strongly preferred on serverless.
            pooled_endpoint=bool(url.host and "-pooler." in url.host),
        )
        if not RESOLUTION_INFO["pooled_endpoint"]:
            logger.warning(
                "Neon host %s is not the pooled (-pooler) endpoint. On serverless, prefer the "
                "pooled connection string to avoid exhausting connection limits.",
                url.host,
            )
        return url.render_as_string(hide_password=False)

    RESOLUTION_INFO.update(backend=url.drivername, relocated=False)
    return url_str


DATABASE_URL = _resolve_database_url()
_IS_SQLITE = DATABASE_URL.startswith("sqlite")

if _IS_SQLITE:
    engine = create_engine(
        DATABASE_URL, echo=False, connect_args={"check_same_thread": False}
    )
else:
    # NullPool: a serverless instance is frozen between invocations, so a pooled
    # connection is usually dead by the time it's reused. Opening per-request and
    # letting Neon's PgBouncer pool is both safer and faster here.
    engine = create_engine(
        DATABASE_URL,
        echo=False,
        poolclass=NullPool,
        pool_pre_ping=True,
        connect_args={"connect_timeout": 10},
    )


def init_db() -> None:
    # models must be imported before create_all so SQLModel.metadata knows about them
    import app.models  # noqa: F401
    SQLModel.metadata.create_all(engine)


def get_session():
    with Session(engine) as session:
        yield session


def write_self_test() -> dict:
    """Opens the live engine and performs a real write inside a rolled-back
    transaction. Surfaced at /api/health/db."""
    from sqlalchemy import text

    info = dict(RESOLUTION_INFO)
    # Never leak credentials in an HTTP response.
    info["database_url"] = make_url(DATABASE_URL).render_as_string(hide_password=True)
    try:
        with engine.connect() as conn:
            # Portable across SQLite and Postgres: an explicit value, no reliance
            # on implicit autoincrement (`INSERT ... DEFAULT VALUES` into an
            # INTEGER PRIMARY KEY autoincrements on SQLite but is a NOT NULL
            # violation on Postgres). Rolled back, so nothing is left behind --
            # both engines have transactional DDL.
            conn.execute(text("CREATE TABLE IF NOT EXISTS _write_probe (token VARCHAR(64))"))
            conn.execute(
                text("INSERT INTO _write_probe (token) VALUES (:token)"),
                {"token": uuid.uuid4().hex},
            )
            conn.rollback()
        info["writable"] = True
    except Exception as exc:  # noqa: BLE001 - diagnostic endpoint, report anything
        info["writable"] = False
        info["error"] = f"{type(exc).__name__}: {exc}"
    return info
