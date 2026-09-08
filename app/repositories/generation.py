from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.generation import Generation


class GenerationRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create(self, generation: Generation) -> Generation:
        self.session.add(generation)
        await self.session.flush()
        return generation

    async def list_completed(self, user_id: int, *, limit: int = 10) -> list[Generation]:
        result = await self.session.scalars(
            select(Generation)
            .where(
                Generation.user_id == user_id,
                Generation.status == "completed",
            )
            .order_by(Generation.completed_at.desc(), Generation.id.desc())
            .limit(limit)
        )
        return list(result)
