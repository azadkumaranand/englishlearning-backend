from fastapi import APIRouter

from app.api.routes.ai_chat import router as ai_chat_router
from app.api.routes.auth import router as auth_router
from app.api.routes.conversation import router as conversation_router
from app.api.routes.corrections import router as corrections_router
from app.api.routes.daily_plan import router as daily_plan_router
from app.api.routes.health import router as health_router
from app.api.routes.learning_profile import router as learning_profile_router
from app.api.routes.mistakes import router as mistakes_router
from app.api.routes.meta import router as meta_router
from app.api.routes.onboarding import router as onboarding_router
from app.api.routes.personalization import router as personalization_router
from app.api.routes.practice_sessions import router as practice_sessions_router
from app.api.routes.progress import router as progress_router
from app.api.routes.topics import router as topics_router
from app.api.routes.users import router as users_router

api_router = APIRouter()
api_router.include_router(auth_router)
api_router.include_router(meta_router)
api_router.include_router(onboarding_router)
api_router.include_router(daily_plan_router)
api_router.include_router(learning_profile_router)
api_router.include_router(progress_router)
api_router.include_router(conversation_router)
api_router.include_router(mistakes_router)
api_router.include_router(personalization_router)
api_router.include_router(topics_router)
api_router.include_router(practice_sessions_router)
api_router.include_router(ai_chat_router)
api_router.include_router(corrections_router)
api_router.include_router(users_router)
api_router.include_router(health_router)
