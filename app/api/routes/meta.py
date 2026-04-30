from fastapi import APIRouter

from app.core.config import get_settings

router = APIRouter(tags=["meta"])


@router.get("/")
async def root() -> dict[str, str]:
    settings = get_settings()
    return {"message": settings.app_name}

