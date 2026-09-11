NICHES = (
    "smm",
    "designers",
    "photographers",
    "bloggers",
    "small_business",
    "online_stores",
)

NICHE_LABELS: dict[str, dict[str, str]] = {
    "smm": {"en": "SMM", "ru": "SMM"},
    "designers": {"en": "Designers", "ru": "Дизайнеры"},
    "photographers": {"en": "Photographers", "ru": "Фотографы"},
    "bloggers": {"en": "Bloggers", "ru": "Блогеры"},
    "small_business": {"en": "Small business", "ru": "Малый бизнес"},
    "online_stores": {"en": "Online stores", "ru": "Интернет-магазины"},
}

NICHE_KEYWORDS: dict[str, tuple[str, ...]] = {
    "smm": (
        "smm",
        "social media",
        "соцсет",
        "контент-план",
        "таргет",
        "продвижение",
    ),
    "designers": (
        "designer",
        "design studio",
        "graphic design",
        "дизайнер",
        "дизайн-студ",
        "брендинг",
    ),
    "photographers": (
        "photographer",
        "photo studio",
        "photoshoot",
        "фотограф",
        "фотостуд",
        "фотосесс",
    ),
    "bloggers": (
        "blogger",
        "creator",
        "influencer",
        "блогер",
        "автор блога",
        "контент-мейкер",
    ),
    "small_business": (
        "small business",
        "local business",
        "our services",
        "малый бизнес",
        "наши услуги",
        "записаться",
    ),
    "online_stores": (
        "online store",
        "shop online",
        "add to cart",
        "интернет-магазин",
        "каталог товаров",
        "корзина",
    ),
}


def localized_niche(niche: str, language: str) -> str:
    selected = language if language in {"en", "ru"} else "en"
    return NICHE_LABELS.get(niche, {}).get(selected, niche)


def infer_niche(text: str) -> str | None:
    lowered = text.casefold()
    matches = {
        niche: sum(keyword in lowered for keyword in keywords)
        for niche, keywords in NICHE_KEYWORDS.items()
    }
    niche, count = max(matches.items(), key=lambda item: item[1])
    return niche if count else None
