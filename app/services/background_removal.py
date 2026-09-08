import logging
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.generation import Generation
from app.providers.background_removal import (
    BackgroundRemovalProvider,
    BackgroundRemovalProviderError,
)
from app.repositories.generation import GenerationRepository
from app.repositories.user import UserRepository

logger = logging.getLogger(__name__)

BACKGROUND_REMOVAL_FEATURE = "background_removal"
BACKGROUND_REMOVAL_COST = 1


class InsufficientCreditsError(Exception):
    pass


class BackgroundRemovalFailedError(Exception):
    def __init__(self, code: str) -> None:
        super().__init__(code)
        self.code = code


@dataclass(frozen=True, slots=True)
class BackgroundRemovalResult:
    image: bytes
    generation: Generation
    remaining_credits: int


class BackgroundRemovalService:
    def __init__(
        self,
        session: AsyncSession,
        provider: BackgroundRemovalProvider,
    ) -> None:
        self.session = session
        self.provider = provider
        self.users = UserRepository(session)
        self.generations = GenerationRepository(session)

    async def process(
        self,
        *,
        user_id: int,
        image_path: Path,
        content_type: str,
    ) -> BackgroundRemovalResult:
        user = await self.users.get_by_id_for_update(user_id)
        if user is None:
            raise LookupError("User does not exist")
        if user.credits < BACKGROUND_REMOVAL_COST:
            raise InsufficientCreditsError

        generation = await self.generations.create(
            Generation(
                user_id=user.id,
                feature=BACKGROUND_REMOVAL_FEATURE,
                credits_spent=0,
                status="processing",
            )
        )

        try:
            result = await self.provider.remove_background(image_path, content_type)
        except BackgroundRemovalProviderError as exc:
            await self._mark_failed(generation, exc.code)
            raise BackgroundRemovalFailedError(exc.code) from exc
        except Exception as exc:
            logger.error(
                "Unexpected background removal provider error generation_id=%s error_type=%s",
                generation.id,
                type(exc).__name__,
            )
            await self._mark_failed(generation, "provider_error")
            raise BackgroundRemovalFailedError("provider_error") from exc

        user.credits -= BACKGROUND_REMOVAL_COST
        generation.credits_spent = BACKGROUND_REMOVAL_COST
        generation.status = "completed"
        generation.completed_at = datetime.now(UTC)
        await self.session.flush()
        logger.info(
            "Background removal completed generation_id=%s user_id=%s",
            generation.id,
            user.id,
        )
        return BackgroundRemovalResult(result, generation, user.credits)

    async def _mark_failed(self, generation: Generation, error_code: str) -> None:
        generation.status = "failed"
        generation.error_code = error_code
        generation.completed_at = datetime.now(UTC)
        await self.session.flush()
        logger.warning(
            "Background removal failed generation_id=%s error_code=%s",
            generation.id,
            error_code,
        )
