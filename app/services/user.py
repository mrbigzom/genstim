import secrets

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User
from app.repositories.user import UserRepository

SUPPORTED_LANGUAGES = {"en", "ru"}
DEFAULT_CREDITS = 3
MAX_ADMIN_CREDIT_TOP_UP = 10_000


def detect_language(language_code: str | None) -> str:
    if language_code and language_code.lower().startswith("ru"):
        return "ru"
    return "en"


class UserService:
    def __init__(self, session: AsyncSession) -> None:
        self.repository = UserRepository(session)

    async def get_or_create(
        self,
        *,
        telegram_id: int,
        username: str | None,
        first_name: str | None,
        telegram_language: str | None,
        referral_code: str | None = None,
    ) -> tuple[User, bool]:
        user = await self.repository.get_by_telegram_id(telegram_id)
        if user is not None:
            user.username = username
            user.first_name = first_name
            user.is_active = True
            return user, False

        referred_by = await self._resolve_referrer(referral_code, telegram_id)
        user = User(
            telegram_id=telegram_id,
            username=username,
            first_name=first_name,
            language=detect_language(telegram_language),
            credits=DEFAULT_CREDITS,
            referral_code=await self._new_referral_code(),
            referred_by=referred_by,
        )
        return await self.repository.create(user), True

    async def set_language(self, user: User, language: str) -> User:
        if language not in SUPPORTED_LANGUAGES:
            raise ValueError(f"Unsupported language: {language}")
        user.language = language
        await self.repository.session.flush()
        return user

    async def add_credits(self, *, telegram_id: int, amount: int) -> User | None:
        if amount <= 0 or amount > MAX_ADMIN_CREDIT_TOP_UP:
            raise ValueError("Credit amount is outside the allowed range")
        user = await self.repository.get_by_telegram_id_for_update(telegram_id)
        if user is None:
            return None
        user.credits += amount
        await self.repository.session.flush()
        return user

    async def _resolve_referrer(
        self,
        referral_code: str | None,
        telegram_id: int,
    ) -> int | None:
        if not referral_code:
            return None
        referrer = await self.repository.get_by_referral_code(referral_code)
        if referrer is None or referrer.telegram_id == telegram_id:
            return None
        return referrer.telegram_id

    async def _new_referral_code(self) -> str:
        for _ in range(10):
            code = secrets.token_urlsafe(8).rstrip("=")
            if await self.repository.get_by_referral_code(code) is None:
                return code
        raise RuntimeError("Could not generate a unique referral code")
