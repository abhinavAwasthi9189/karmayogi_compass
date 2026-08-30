from fastapi import APIRouter
from app.api.v1 import auth, profile, skillgap, recommendations, quiz, analytics

api_router = APIRouter()
api_router.include_router(auth.router)
api_router.include_router(profile.router)
api_router.include_router(skillgap.router)
api_router.include_router(recommendations.router)
api_router.include_router(quiz.router)
api_router.include_router(analytics.router)
