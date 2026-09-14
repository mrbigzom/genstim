from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.lead_source import LeadSource


class LeadSourceRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create(self, source: LeadSource) -> LeadSource:
        self.session.add(source)
        await self.session.flush()
        return source

    async def get_by_url_for_update(self, url: str) -> LeadSource | None:
        return await self.session.scalar(
            select(LeadSource).where(LeadSource.url == url).with_for_update()
        )

    async def get_by_id_for_update(self, source_id: int) -> LeadSource | None:
        return await self.session.scalar(
            select(LeadSource).where(LeadSource.id == source_id).with_for_update()
        )

    async def list_all(self) -> list[LeadSource]:
        result = await self.session.scalars(
            select(LeadSource).order_by(LeadSource.id)
        )
        return list(result)
