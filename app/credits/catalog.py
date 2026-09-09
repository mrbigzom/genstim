# Cost of one successful function run in internal GenStim credits.
# Add future functions here and change costs in this single catalog.
FEATURE_CREDIT_COSTS: dict[str, int] = {
    "background_removal": 1,
    "qr_designer": 1,
    "meme_generator": 1,
    "pixel_avatar": 1,
    "passport_photo": 1,
    "sticker": 1,
}


def get_feature_credit_cost(feature: str) -> int:
    try:
        cost = FEATURE_CREDIT_COSTS[feature]
    except KeyError as exc:
        raise ValueError(f"Credit cost is not configured for feature: {feature}") from exc
    if cost <= 0:
        raise ValueError(f"Credit cost must be positive for feature: {feature}")
    return cost
