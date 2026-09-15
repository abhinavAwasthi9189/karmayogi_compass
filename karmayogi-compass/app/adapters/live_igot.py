"""Live iGOT adapter — calls the real iGOT Karmayogi endpoints over HTTP.
Same method signatures/return shape as MockIGOTAdapter, so callers never
need to branch on which adapter is active."""
from typing import List, Dict, Any, Optional
import httpx
from app.adapters.base import IGOTAdapter
from app.config import get_settings

settings = get_settings()


class LiveIGOTAdapter(IGOTAdapter):
    def __init__(self):
        self.base_url = settings.IGOT_BASE_URL.rstrip("/")
        self.headers = {"Authorization": f"Bearer {settings.IGOT_API_KEY}"} if settings.IGOT_API_KEY else {}

    async def get_courses(self, domain: Optional[str] = None, limit: int = 10) -> List[Dict[str, Any]]:
        params = {"limit": limit}
        if domain:
            params["domain"] = domain
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.get(f"{self.base_url}/courses", params=params, headers=self.headers)
            resp.raise_for_status()
            return resp.json().get("courses", [])

    async def get_course_by_id(self, external_id: str) -> Optional[Dict[str, Any]]:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.get(f"{self.base_url}/courses/{external_id}", headers=self.headers)
            if resp.status_code == 404:
                return None
            resp.raise_for_status()
            return resp.json()
