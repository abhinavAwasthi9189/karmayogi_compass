from fastapi import APIRouter, Depends

from app.models import User
from app.api.deps import get_current_user
from app.schemas.compass_ai import (
    CompassSuggestRequest, CompassSuggestResponse, CompassAskRequest, CompassAskResponse,
)
from app.services.compass_ai_service import get_quick_suggestions, answer_question

router = APIRouter(prefix="/compass-ai", tags=["Compass AI"])


@router.post("/suggestions", response_model=CompassSuggestResponse)
def suggest(payload: CompassSuggestRequest, current_user: User = Depends(get_current_user)):
    """Pre-selection quick-reply chips shown above the chat input, generated
    from what the learner is currently studying."""
    return CompassSuggestResponse(suggestions=get_quick_suggestions(payload.context))


@router.post("/ask", response_model=CompassAskResponse)
def ask(payload: CompassAskRequest, current_user: User = Depends(get_current_user)):
    """A short, context-grounded answer to the learner's actual question."""
    return CompassAskResponse(answer=answer_question(payload.context, payload.question, payload.history))
