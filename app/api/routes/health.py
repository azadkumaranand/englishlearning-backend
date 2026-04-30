from fastapi import APIRouter, status
from fastapi.responses import JSONResponse

from app.db.session import check_database_connection

router = APIRouter(tags=["health"])


@router.get("/health")
async def health_check() -> JSONResponse:
    database_ok = await check_database_connection()

    payload = {
        "status": "ok" if database_ok else "degraded",
        "database": "ok" if database_ok else "error",
    }
    status_code = status.HTTP_200_OK if database_ok else status.HTTP_503_SERVICE_UNAVAILABLE
    return JSONResponse(content=payload, status_code=status_code)
