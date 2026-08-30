"""Fetches iGOT courses targeted at a user's weakest competency domains,
via the IGOTAdapter so the source (mock/live) is fully swappable."""
from typing import List, Dict, Any
from app.adapters.base import IGOTAdapter


async def recommend_courses(adapter: IGOTAdapter, gaps: List[Dict[str, Any]], limit: int = 6) -> List[Dict[str, Any]]:
    priority_domains = [g["domain"] for g in gaps if g["gap"] > 0] or [g["domain"] for g in gaps]
    if not priority_domains:
        return await adapter.get_courses(limit=limit)

    courses: List[Dict[str, Any]] = []
    seen_ids = set()
    # weight allocation: bigger gap -> more course slots, at least 1 each
    per_domain = max(1, limit // max(1, len(priority_domains)))
    for domain in priority_domains:
        for course in await adapter.get_courses(domain=domain, limit=per_domain):
            if course["id"] not in seen_ids:
                courses.append(course)
                seen_ids.add(course["id"])
        if len(courses) >= limit:
            break
    return courses[:limit]
