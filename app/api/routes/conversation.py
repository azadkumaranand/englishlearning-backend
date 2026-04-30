from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db_session
from app.dependencies.auth import get_current_user
from app.models.user import User
from app.schemas.conversation import (
    ConversationReplyRequest,
    ConversationReplyResponse,
    ConversationStartRequest,
    ConversationStartResponse,
)
from app.services.conversation_roleplay_service import (
    reply_in_conversation_session,
    start_conversation_session,
)

router = APIRouter(prefix="/conversation", tags=["conversation"])


@router.post("/start", response_model=ConversationStartResponse)
async def start_conversation(
    payload: ConversationStartRequest,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
) -> ConversationStartResponse:
    return await start_conversation_session(
        session,
        user=current_user,
        scenario=payload.scenario,
    )


@router.post("/reply", response_model=ConversationReplyResponse)
async def reply_conversation(
    payload: ConversationReplyRequest,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
) -> ConversationReplyResponse:
    return await reply_in_conversation_session(
        session,
        user=current_user,
        payload=payload,
    )
