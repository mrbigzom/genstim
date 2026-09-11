from app.lead_finder.catalog import NICHE_KEYWORDS

COMMERCIAL_SIGNALS = (
    "portfolio",
    "services",
    "book now",
    "shop",
    "catalog",
    "заказать",
    "услуги",
    "портфолио",
    "магазин",
    "каталог",
)


def score_public_lead(
    *,
    text: str,
    niche: str,
    contact: str,
    source: str,
) -> tuple[int, str]:
    lowered = text.casefold()
    niche_matches = [
        keyword for keyword in NICHE_KEYWORDS[niche] if keyword in lowered
    ]
    commercial_matches = [
        signal for signal in COMMERCIAL_SIGNALS if signal in lowered
    ]

    score = 20
    score += min(len(niche_matches) * 10, 40)
    score += min(len(commercial_matches) * 5, 20)
    score += 15 if contact else 0
    score += 5 if source in {"website", "public_page", "telegram_channel"} else 0
    score = max(0, min(score, 100))

    reasons = []
    if niche_matches:
        reasons.append(f"niche signals: {', '.join(niche_matches[:3])}")
    if commercial_matches:
        reasons.append(f"business signals: {', '.join(commercial_matches[:3])}")
    if contact:
        reasons.append("public business contact available")
    return score, "; ".join(reasons) or "public profile matches the selected niche"
