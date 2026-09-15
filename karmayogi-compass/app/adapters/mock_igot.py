"""Mock iGOT adapter — serves structured fixture data with zero network calls.
Used when settings.IGOT_MODE == 'mock', or automatically as a fallback if the
live adapter errors out (e.g. iGOT endpoint unreachable during a demo)."""
from typing import List, Dict, Any, Optional
from app.adapters.base import IGOTAdapter
from app.adapters.mock_data import MOCK_COURSES


class MockIGOTAdapter(IGOTAdapter):
    async def get_courses(self, domain: Optional[str] = None, limit: int = 10) -> List[Dict[str, Any]]:
        courses = MOCK_COURSES
        if domain:
            courses = [c for c in courses if c["domain"] == domain]
        return courses[:limit]

    async def get_course_by_id(self, external_id: str) -> Optional[Dict[str, Any]]:
        return next((c for c in MOCK_COURSES if c["id"] == external_id), None)
