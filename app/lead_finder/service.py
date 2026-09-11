from sqlalchemy.ext.asyncio import AsyncSession

from app.lead_finder.catalog import NICHES, localized_niche
from app.lead_finder.types import LeadCandidate
from app.locales.messages import get_text
from app.models.lead import Lead
from app.repositories.lead import LeadRepository

LEAD_STATUSES = ("new", "contacted", "interested", "rejected")
LEAD_SOURCES = ("website", "public_page", "telegram_channel")


class LeadFinderService:
    def __init__(self, session: AsyncSession) -> None:
        self.repository = LeadRepository(session)

    async def save_candidate(self, candidate: LeadCandidate) -> tuple[Lead, bool]:
        self._validate_candidate(candidate)
        existing = await self.repository.get_by_source_url(candidate.source, candidate.url)
        if existing is not None:
            existing.name = candidate.name
            existing.niche = candidate.niche
            existing.contact = candidate.contact
            existing.reason_fit = candidate.reason_fit
            existing.score = candidate.score
            await self.repository.session.flush()
            return existing, False

        lead = Lead(
            name=candidate.name,
            source=candidate.source,
            url=candidate.url,
            niche=candidate.niche,
            contact=candidate.contact,
            reason_fit=candidate.reason_fit,
            score=candidate.score,
            status="new",
        )
        return await self.repository.create(lead), True

    async def best_new(self, *, niche: str | None = None, limit: int = 5) -> list[Lead]:
        if niche is not None and niche not in NICHES:
            raise ValueError(f"Unsupported lead niche: {niche}")
        if limit <= 0 or limit > 20:
            raise ValueError("Lead result limit must be between 1 and 20")
        return await self.repository.list_new(niche=niche, limit=limit)

    async def set_status(self, *, lead_id: int, status: str) -> Lead | None:
        if status not in LEAD_STATUSES:
            raise ValueError(f"Unsupported lead status: {status}")
        lead = await self.repository.get_by_id_for_update(lead_id)
        if lead is None:
            return None
        lead.status = status
        await self.repository.session.flush()
        return lead

    @staticmethod
    def draft_message(lead: Lead, language: str) -> str:
        return get_text(
            language,
            "lead_outreach_template",
            name=lead.name,
            niche=localized_niche(lead.niche, language),
        )

    @staticmethod
    def _validate_candidate(candidate: LeadCandidate) -> None:
        if not candidate.name.strip() or len(candidate.name) > 255:
            raise ValueError("Lead name is invalid")
        if candidate.source not in LEAD_SOURCES:
            raise ValueError("Lead source is invalid")
        if not candidate.url.strip() or len(candidate.url) > 2048:
            raise ValueError("Lead URL is invalid")
        if candidate.niche not in NICHES:
            raise ValueError("Lead niche is invalid")
        if len(candidate.contact) > 255 or len(candidate.reason_fit) > 1000:
            raise ValueError("Lead metadata is too long")
        if candidate.score < 0 or candidate.score > 100:
            raise ValueError("Lead score must be between 0 and 100")
