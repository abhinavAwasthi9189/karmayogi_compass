"""Loads the hackathon `mock/` dataset from disk and exposes it in the exact
shapes the rest of the app already expects (CourseOut-like dicts, quiz-bank
question dicts, designation-requirement overrides).

Files expected in `mock/` (project root, alongside `app/` and `data/`):
    rag_learning_corpus_flat.csv     -> course + module content corpus
    practice_assessments.csv         -> pre-authored quiz question bank
    mock_data_statistical_analyst.py -> extra REQUIRED_LEVELS_BY_DESIGNATION entries
    end_to_end_test_cases.csv        -> QA only, never read at runtime

Every loader degrades gracefully to an empty result if its file isn't there
yet, so the app keeps booting and serving its built-in fixtures until the
real dataset is dropped in -- nothing here is allowed to crash startup.
"""
import csv
import importlib.util
import random
from functools import lru_cache
from pathlib import Path
from typing import Any, Dict, List, Optional

BASE_DIR = Path(__file__).resolve().parent.parent.parent  # project root
MOCK_DIR = BASE_DIR / "mock"

RAG_CORPUS_FILE = MOCK_DIR / "rag_learning_corpus_flat.csv"
ASSESSMENTS_FILE = MOCK_DIR / "practice_assessments.csv"
DESIGNATION_FILE = MOCK_DIR / "mock_data_statistical_analyst.py"

VALID_DOMAINS = {"statistical", "technical", "digital_gov", "managerial"}

# Fallback only: used if a row has no populated `domain` column and instead
# carries the broader 11-item `competency` label from the wider content schema.
COMPETENCY_TO_DOMAIN = {
    "statistical analysis": "statistical",
    "sampling & survey methods": "statistical",
    "hypothesis testing": "statistical",
    "regression analysis": "statistical",
    "official statistics & indicator analysis": "statistical",
    "statistical reporting": "statistical",
    "data management": "technical",
    "data analysis & visualization": "technical",
    "sql & data retrieval": "technical",
    "python for data analysis": "technical",
    "data use & governance": "digital_gov",
}

LEVEL_NORMALIZE = {
    "beginner": "L1", "l1": "L1",
    "intermediate": "L2", "l2": "L2",
    "advanced": "L3", "l3": "L3",
}


def _normalize_domain(row: Dict[str, str]) -> Optional[str]:
    domain = (row.get("domain") or "").strip().lower()
    if domain in VALID_DOMAINS:
        return domain
    competency = (row.get("competency") or "").strip().lower()
    return COMPETENCY_TO_DOMAIN.get(competency)


def _normalize_level(raw: str) -> str:
    return LEVEL_NORMALIZE.get((raw or "").strip().lower(), "L1")


def _read_csv(path: Path) -> List[Dict[str, str]]:
    if not path.exists():
        return []
    with open(path, newline="", encoding="utf-8-sig") as f:
        return list(csv.DictReader(f))


@lru_cache
def load_rag_corpus() -> List[Dict[str, Any]]:
    """One dict per module row, normalized to:
    course_id, course_title, domain, level, learning_outcomes,
    module_no, module_title, study_material, module_learning_outcome
    """
    rows = []
    for raw in _read_csv(RAG_CORPUS_FILE):
        domain = _normalize_domain(raw)
        if not domain:
            continue  # can't confidently place this row in a domain -- skip it
        module_no_raw = str(raw.get("module_no", "")).strip()
        rows.append({
            "course_id": (raw.get("course_id") or "").strip(),
            "course_title": (raw.get("course_title") or "").strip(),
            "domain": domain,
            "level": _normalize_level(raw.get("level", "")),
            "learning_outcomes": (raw.get("learning_outcomes") or "").strip(),
            "module_no": int(module_no_raw) if module_no_raw.isdigit() else 0,
            "module_title": (raw.get("module_title") or "").strip(),
            "study_material": (raw.get("study_material") or "").strip(),
            "module_learning_outcome": (raw.get("module_learning_outcome") or "").strip(),
        })
    return rows


@lru_cache
def load_courses_from_corpus() -> List[Dict[str, Any]]:
    """Collapses per-module rows into one record per course_id, shaped like
    the existing MOCK_COURSES fixture / CourseOut schema:
    id, title, domain, source, launch_url, description."""
    courses: Dict[str, Dict[str, Any]] = {}
    for row in load_rag_corpus():
        cid = row["course_id"]
        if not cid or cid in courses:
            continue
        courses[cid] = {
            "id": cid,
            "title": row["course_title"] or cid,
            "domain": row["domain"],
            "source": "Sample Karmayogi Learning Content",
            "launch_url": f"/mock-content/{cid}",
            "description": row["learning_outcomes"] or row["module_learning_outcome"] or "",
        }
    return list(courses.values())


@lru_cache
def load_practice_assessments() -> List[Dict[str, Any]]:
    """One dict per pre-authored quiz question, normalized to:
    assessment_id, course_id, domain, question_type, scenario, question,
    options (dict A-D), correct_option, explanation, difficulty"""
    rows = []
    for raw in _read_csv(ASSESSMENTS_FILE):
        domain = (raw.get("domain") or "").strip().lower()
        if domain not in VALID_DOMAINS:
            continue
        rows.append({
            "assessment_id": (raw.get("assessment_id") or "").strip(),
            "course_id": (raw.get("course_id") or "").strip(),
            "domain": domain,
            "question_type": (raw.get("question_type") or "").strip(),
            "scenario": (raw.get("scenario") or "").strip(),
            "question": (raw.get("question") or "").strip(),
            "options": {
                "A": (raw.get("option_A") or "").strip(),
                "B": (raw.get("option_B") or "").strip(),
                "C": (raw.get("option_C") or "").strip(),
                "D": (raw.get("option_D") or "").strip(),
            },
            "correct_option": (raw.get("correct_option") or "").strip().upper(),
            "explanation": (raw.get("explanation") or "").strip(),
            "difficulty": (raw.get("difficulty") or "medium").strip().lower(),
        })
    return rows


@lru_cache
def load_designation_overrides() -> Dict[str, Dict[str, float]]:
    """Dynamically imports mock/mock_data_statistical_analyst.py (if present)
    and pulls its REQUIRED_LEVELS_BY_DESIGNATION dict, so new designations
    merge into the app's built-in requirements without hand-editing
    adapters/mock_data.py every time the dataset changes."""
    if not DESIGNATION_FILE.exists():
        return {}

    spec = importlib.util.spec_from_file_location("mock_designation_data", DESIGNATION_FILE)
    if spec is None or spec.loader is None:
        return {}
    module = importlib.util.module_from_spec(spec)
    try:
        spec.loader.exec_module(module)
    except Exception:
        # Malformed override file should never take the whole app down.
        return {}

    overrides = getattr(module, "REQUIRED_LEVELS_BY_DESIGNATION", {})
    return overrides if isinstance(overrides, dict) else {}


def course_corpus_available() -> bool:
    return bool(load_rag_corpus())


def practice_bank_available() -> bool:
    return bool(load_practice_assessments())


def pick_bank_questions(domain: str, count: int, exclude_keys: set) -> List[Dict[str, Any]]:
    """Random, non-repeating sample of up-to-`count` bank questions for a
    domain, skipping any (scenario, question) pairs already chosen this quiz."""
    pool = [
        q for q in load_practice_assessments()
        if q["domain"] == domain and (q["scenario"], q["question"]) not in exclude_keys
    ]
    random.shuffle(pool)
    return pool[:count]
