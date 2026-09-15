"""Single switch point for which iGOT backend is active. Everything else in the
codebase depends only on the IGOTAdapter interface, so flipping IGOT_MODE in
.env (mock <-> live) requires no other code changes."""
from functools import lru_cache
from app.adapters.base import IGOTAdapter
from app.adapters.mock_igot import MockIGOTAdapter
from app.adapters.live_igot import LiveIGOTAdapter
from app.config import get_settings


@lru_cache
def get_igot_adapter() -> IGOTAdapter:
    settings = get_settings()
    if settings.IGOT_MODE.lower() == "live":
        return LiveIGOTAdapter()
    return MockIGOTAdapter()
