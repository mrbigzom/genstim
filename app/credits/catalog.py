# Cost of one successful function run in internal GenStim credits.
# Add future functions here and change costs in this single catalog.
FEATURE_CREDIT_COSTS: dict[str, int] = {
    "background_removal": 5,
    "qr_designer": 5,
    "meme_generator": 5,
    "pixel_avatar": 10,
    "passport_photo": 10,
    "sticker": 5,
}


def get_feature_credit_cost(feature: str) -> int:
    try:
        cost = FEATURE_CREDIT_COSTS[feature]
    except KeyError as exc:
        raise ValueError(f"Credit cost is not configured for feature: {feature}") from exc
    if cost <= 0:
        raise ValueError(f"Credit cost must be positive for feature: {feature}")
    return cost
