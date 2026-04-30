from __future__ import annotations

import asyncio

from app.db.session import AsyncSessionLocal, close_engine
from app.services.topic_service import seed_topics
from app.services.redis import close_redis


async def _seed() -> None:
    try:
        async with AsyncSessionLocal() as session:
            seeded_count = await seed_topics(session)
        print(f"Seeded {seeded_count} topics")
    finally:
        await close_redis()
        await close_engine()


def main() -> None:
    asyncio.run(_seed())


if __name__ == "__main__":
    main()
