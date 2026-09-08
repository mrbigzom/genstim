from sqlalchemy.ext.asyncio import AsyncSession

from app.models.generation import Generation
from app.repositories.generation import GenerationRepository


class GenerationService:
    def __init__(self, session: AsyncSession) -> None:
        self.repository = GenerationRepository(session)

    async def completed_history(self, user_id: int, *, limit: int = 10) -> list[Generation]:
        return await self.repository.list_completed(user_id, limit=limit)
