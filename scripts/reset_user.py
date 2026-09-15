"""Reset a seeded demo user's practice data back to their baseline.

Usage (from the project root, with the venv active):

    python scripts/reset_user.py                            # defaults to Ravi Kishan
    python scripts/reset_user.py ravi.kishan@mospi.gov.in
    python scripts/reset_user.py priya.iyer@mospi.gov.in

Deletes the user's assessment attempts, clears their competency passport's
validated skills and their identified gaps, and restores the domain scores
defined in app/adapters/mock_data.py. The account, password and role are left
intact, so you can log straight back in and run the flow from scratch.
"""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlmodel import Session  # noqa: E402

from app.database import engine, init_db  # noqa: E402
from app.services.seed_service import reset_seed_user  # noqa: E402

DEFAULT_EMAIL = "ravi.kishan@mospi.gov.in"


def main() -> int:
    email = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_EMAIL
    init_db()
    with Session(engine) as session:
        try:
            print(reset_seed_user(session, email))
        except ValueError as exc:
            print(f"Nothing reset: {exc}")
            return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
