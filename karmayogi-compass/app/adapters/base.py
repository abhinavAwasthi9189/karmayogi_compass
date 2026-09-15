"""Adapter contract. Every iGOT adapter (mock or live) must implement this interface,
so services can depend on `IGOTAdapter` without knowing which backend is in play."""
from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional


class IGOTAdapter(ABC):
    @abstractmethod
    async def get_courses(self, domain: Optional[str] = None, limit: int = 10) -> List[Dict[str, Any]]:
        """Return course listings, optionally filtered by competency domain."""
        raise NotImplementedError

    @abstractmethod
    async def get_course_by_id(self, external_id: str) -> Optional[Dict[str, Any]]:
        raise NotImplementedError
