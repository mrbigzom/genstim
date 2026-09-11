from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.lead import Lead


class LeadRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_by_source_url(self, source: str, url: str) -> Lead | None:
        return await self.session.scalar(
            select(Lead).where(Lead.source == source, Lead.url == url)
        )

    async def create(self, lead: Lead) -> Lead:
        self.session.add(lead)
        await self.session.flush()
        return lead

    async def list_new(self, *, niche: str | None, limit: int) -> list[Lead]:
        query = select(Lead).where(Lead.status == "new")
        if niche is not None:
            query = query.where(Lead.niche == niche)
        result = await self.session.scalars(
            query.order_by(Lead.score.desc(), Lead.created_at.desc(), Lead.id.desc()).limit(limit)
        )
        return list(result)

    async def get_by_id_for_update(self, lead_id: int) -> Lead | None:
        return await self.session.scalar(
            select(Lead).where(Lead.id == lead_id).with_for_update()
        )
