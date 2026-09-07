import pytest

from app.locales.messages import get_text
from app.services.user import detect_language


@pytest.mark.parametrize(
    ("telegram_language", "expected"),
    [("ru", "ru"), ("ru-RU", "ru"), ("en", "en"), ("de", "en"), (None, "en")],
)
def test_detect_language(telegram_language: str | None, expected: str) -> None:
    assert detect_language(telegram_language) == expected


def test_unknown_localization_falls_back_to_english() -> None:
    assert get_text("de", "feature_pending") == "This feature is being prepared 🚀"
