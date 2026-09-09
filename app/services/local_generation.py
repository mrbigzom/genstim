import logging
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from datetime import UTC, datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.credits.catalog import get_feature_credit_cost
from app.models.generation import Generation
from app.providers.local_processing import LocalProcessingError
from app.repositories.generation import GenerationRepository
from app.repositories.user import UserRepository
from app.services.background_removal import InsufficientCreditsError

logger = logging.getLogger(__name__)

class LocalGenerationFailedError(Exception):
    def __init__(self, code: str) -> None:
        super().__init__(code)
        self.code = code


@dataclass(frozen=True, slots=True)
class LocalGenerationResult:
    content: bytes
    generation: Generation
    remaining_credits: int


class LocalGenerationService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.users = UserRepository(session)
        self.generations = GenerationRepository(session)

    async def process(
        self,
        *,
        user_id: int,
        feature: str,
        operation: Callable[[], Awaitable[bytes]],
    ) -> LocalGenerationResult:
        user = await self.users.get_by_id_for_update(user_id)
        if user is None:
            raise LookupError("User does not exist")
        cost = get_feature_credit_cost(feature)
        if user.credits < cost:
            raise InsufficientCreditsError(required=cost, balance=user.credits)

        generation = await self.generations.create(
            Generation(
                user_id=user.id,
                feature=feature,
                credits_spent=0,
                status="processing",
            )
        )
        try:
            content = await operation()
        except LocalProcessingError as exc:
            await self._mark_failed(generation, exc.code)
            raise LocalGenerationFailedError(exc.code) from exc
        except Exception as exc:
            logger.error(
                "Unexpected local processing error generation_id=%s feature=%s error_type=%s",
                generation.id,
                feature,
                type(exc).__name__,
            )
            await self._mark_failed(generation, "processing_error")
            raise LocalGenerationFailedError("processing_error") from exc

        if not content:
            await self._mark_failed(generation, "processing_error")
            raise LocalGenerationFailedError("processing_error")

        user.credits -= cost
        generation.credits_spent = cost
        generation.status = "completed"
        generation.completed_at = datetime.now(UTC)
        await self.session.flush()
        logger.info(
            "Local generation completed generation_id=%s user_id=%s feature=%s",
            generation.id,
            user.id,
            feature,
        )
        return LocalGenerationResult(content, generation, user.credits)

    async def _mark_failed(self, generation: Generation, error_code: str) -> None:
        generation.status = "failed"
        generation.error_code = error_code
        generation.completed_at = datetime.now(UTC)
        await self.session.flush()
        logger.warning(
            "Local generation failed generation_id=%s feature=%s error_code=%s",
            generation.id,
            generation.feature,
            error_code,
        )
