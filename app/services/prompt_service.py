from __future__ import annotations

from collections.abc import Sequence

from app.models.learning_profile import LearningProfile
from app.models.practice_message import PracticeMessage
from app.models.practice_session import PracticeSession
from app.models.user_learning_summary import UserLearningSummary
from app.models.user import User
from app.prompts.conversation_prompt import build_conversation_system_prompt
from app.prompts.correction_prompt import build_correction_system_prompt


def build_conversation_prompt(
    *,
    user: User,
    learning_profile: LearningProfile | None,
    practice_session: PracticeSession,
    history: Sequence[PracticeMessage],
    learning_summary: UserLearningSummary | None = None,
) -> str:
    return build_conversation_system_prompt(
        user=user,
        learning_profile=learning_profile,
        practice_session=practice_session,
        history=history,
        learning_summary=learning_summary,
    )


def build_correction_prompt(
    *,
    user: User,
    learning_profile: LearningProfile | None,
) -> str:
    return build_correction_system_prompt(user=user, learning_profile=learning_profile)
