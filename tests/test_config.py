import pytest
from pydantic import ValidationError

from app.core.config import Settings


def test_settings_accept_empty_optional_admin_id() -> None:
    settings = Settings(
        bot_token="123456:test-token",
        database_url="postgresql+asyncpg://user:pass@db/database",
        admin_telegram_id="",  # type: ignore[arg-type]
        _env_file=None,
    )

    assert settings.admin_telegram_id is None
    assert settings.bot_token.get_secret_value() == "123456:test-token"
    assert settings.background_removal_max_pixels == 25_000_000
    assert "test-token" not in repr(settings)


def test_settings_reject_empty_bot_token() -> None:
    with pytest.raises(ValidationError):
        Settings(bot_token="", database_url="sqlite+aiosqlite://", _env_file=None)
