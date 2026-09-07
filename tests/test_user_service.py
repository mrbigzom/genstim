from sqlalchemy.ext.asyncio import AsyncSession

from app.services.user import DEFAULT_CREDITS, UserService


async def test_new_user_gets_language_and_free_credits(session: AsyncSession) -> None:
    user, created = await UserService(session).get_or_create(
        telegram_id=1001,
        username="tester",
        first_name="Test",
        telegram_language="ru-RU",
    )

    assert created is True
    assert user.language == "ru"
    assert user.credits == DEFAULT_CREDITS
    assert user.referral_code


async def test_existing_user_is_reused_and_profile_is_refreshed(session: AsyncSession) -> None:
    service = UserService(session)
    original, _ = await service.get_or_create(
        telegram_id=1002,
        username="before",
        first_name="Before",
        telegram_language="en",
    )
    existing, created = await service.get_or_create(
        telegram_id=1002,
        username="after",
        first_name="After",
        telegram_language="ru",
    )

    assert created is False
    assert existing.id == original.id
    assert existing.username == "after"
    assert existing.first_name == "After"
    assert existing.language == "en"


async def test_referral_is_saved_without_rewarding_credits_yet(session: AsyncSession) -> None:
    service = UserService(session)
    referrer, _ = await service.get_or_create(
        telegram_id=2001,
        username="referrer",
        first_name="Referrer",
        telegram_language="en",
    )
    referred, _ = await service.get_or_create(
        telegram_id=2002,
        username="friend",
        first_name="Friend",
        telegram_language="en",
        referral_code=referrer.referral_code,
    )

    assert referred.referred_by == referrer.telegram_id
    assert referrer.credits == DEFAULT_CREDITS


async def test_language_can_be_changed(session: AsyncSession) -> None:
    service = UserService(session)
    user, _ = await service.get_or_create(
        telegram_id=3001,
        username=None,
        first_name="User",
        telegram_language="en",
    )

    await service.set_language(user, "ru")
    assert user.language == "ru"
