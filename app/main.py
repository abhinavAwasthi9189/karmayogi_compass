from pathlib import Path

import hashlib
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import RedirectResponse
from sqlmodel import Session

from app.config import get_settings
from app.database import init_db, engine
from app.services.seed_service import seed_demo_data
from app.api.v1 import api_router

settings = get_settings()

BASE_DIR = Path(__file__).resolve().parent
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))


def _compute_asset_version() -> str:
    """Hashes every static file's path + last-modified time into a short
    version string, appended as ?v=... on every CSS/JS tag (see templates).
    This changes automatically whenever a static file is edited, so browsers
    stop serving a stale cached copy of app.js/style.css after a deploy --
    no manual version bump required."""
    static_dir = BASE_DIR / "static"
    parts = []
    for p in sorted(static_dir.rglob("*")):
        if p.is_file():
            parts.append(f"{p}:{p.stat().st_mtime_ns}")
    digest = hashlib.md5("".join(parts).encode()).hexdigest()
    return digest[:10]


ASSET_VERSION = _compute_asset_version()


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    with Session(engine) as session:
        seed_demo_data(session)
    yield


app = FastAPI(
    title=settings.APP_NAME,
    description="AI-powered skill intelligence layer for India's Official Statistical System (MoSPI), built on iGOT Karmayogi.",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router, prefix="/api/v1")
app.mount("/static", StaticFiles(directory=str(BASE_DIR / "static")), name="static")


@app.get("/api/health", tags=["Health"])
def health_check():
    return {"status": "ok", "service": settings.APP_NAME}


# ---------------------------------------------------------------------------
# Frontend page routes.
# These just render the static template shells; all real data is fetched
# client-side (JS in app/static/js/auth.js + dashboard.js) against the
# JSON API above, using the JWT bearer token issued by /api/v1/auth/login.
# ---------------------------------------------------------------------------

PAGES = {
    "login": "login.html",
    "signup": "signup.html",
    "dashboard": "dashboard.html",
    "passport": "passport.html",
    "path": "path.html",
    "course-detail": "course-detail.html",
    "learning": "learning.html",
    "assessment": "assessment.html",
    "results": "results.html",
}


@app.get("/", tags=["Frontend"])
def root():
    return RedirectResponse(url="/login")


def _make_page_route(template_name: str):
    def _route(request: Request):
        return templates.TemplateResponse(request, template_name, {"ASSET_VERSION": ASSET_VERSION})
    return _route


for _slug, _template in PAGES.items():
    app.add_api_route(f"/{_slug}", _make_page_route(_template), methods=["GET"], tags=["Frontend"])
