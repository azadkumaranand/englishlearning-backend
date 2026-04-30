from __future__ import annotations

from datetime import date

from app.models.user import User
from app.schemas.daily_plan import DailyPlanResponse, DailyPlanTaskResponse


def _build_translation_task(user: User) -> DailyPlanTaskResponse:
    level = (user.english_level or "beginner").lower()
    goal = (user.learning_goal or "daily_conversation").lower()

    if level == "beginner":
        title = "Practice 3 daily-life sentences"
        description = "Improve sentence formation and confidence with short practical examples."
        minutes = 5
    elif level == "intermediate":
        title = "Translate 4 natural English replies"
        description = "Practice smoother sentence building for real conversations."
        minutes = 6
    else:
        title = "Refine 4 natural responses"
        description = "Practice polished, natural English for more fluent expression."
        minutes = 6

    if goal == "job_interview":
        title = "Practice 3 interview-style answers"
        description = "Build stronger sentence structure for common interview situations."
    elif goal == "business_english":
        title = "Practice 3 workplace sentences"
        description = "Improve clear and professional English for work communication."
    elif goal == "travel_english":
        title = "Practice 3 travel situations"
        description = "Build useful English for directions, hotels, and daily travel needs."
    elif goal == "confidence_building":
        description = "Use short, simple sentences to speak with less hesitation."

    return DailyPlanTaskResponse(
        id="task_1",
        type="translation",
        title=title,
        description=description,
        estimated_minutes=minutes,
        status="pending",
    )


def _build_second_task(user: User) -> DailyPlanTaskResponse:
    preference = (user.practice_preference or "both").lower()
    goal = (user.learning_goal or "daily_conversation").lower()

    if preference == "speaking":
        return DailyPlanTaskResponse(
            id="task_2",
            type="speaking",
            title="Say your answers out loud",
            description="Repeat your best answers aloud to build speaking comfort and rhythm.",
            estimated_minutes=4,
            status="pending",
        )

    if goal == "exam_preparation":
        return DailyPlanTaskResponse(
            id="task_2",
            type="review",
            title="Review your recent mistakes",
            description="Notice repeated grammar issues before your next structured practice set.",
            estimated_minutes=4,
            status="pending",
        )

    if preference == "writing":
        return DailyPlanTaskResponse(
            id="task_2",
            type="review",
            title="Review your recent mistakes",
            description="Fix repeated grammar mistakes and make your written answers cleaner.",
            estimated_minutes=5,
            status="pending",
        )

    return DailyPlanTaskResponse(
        id="task_2",
        type="review",
        title="Review your recent mistakes",
        description="Fix repeated grammar mistakes and keep your next replies more natural.",
        estimated_minutes=5,
        status="pending",
    )


async def build_daily_plan_for_user(user: User) -> DailyPlanResponse:
    tasks = [_build_translation_task(user), _build_second_task(user)]
    return DailyPlanResponse(
        date=date.today(),
        title="Today’s English Practice",
        estimated_minutes=sum(task.estimated_minutes for task in tasks),
        tasks=tasks,
    )
