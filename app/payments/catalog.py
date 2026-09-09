from dataclasses import dataclass

STARS_CURRENCY = "XTR"


@dataclass(frozen=True, slots=True)
class Product:
    id: str
    feature_callback: str
    name_key: str
    stars_amount: int
    payments_enabled: bool = False

    @property
    def paid_amount(self) -> int | None:
        return self.stars_amount if self.payments_enabled else None


# These are deliberately disabled placeholder prices, not final commercial prices.
# To make one function payable, set its final stars_amount and payments_enabled=True.
PRODUCT_CATALOG: dict[str, Product] = {
    "background_removal": Product(
        "background_removal", "background", "feature_background_removal", 1
    ),
    "qr_designer": Product("qr_designer", "qr", "feature_qr_designer", 1),
    "meme_generator": Product("meme_generator", "memes", "feature_meme_generator", 1),
    "pixel_avatar": Product("pixel_avatar", "pixel", "feature_pixel_avatar", 1),
    "passport_photo": Product(
        "passport_photo", "passport", "feature_passport_photo", 1
    ),
    "sticker": Product("sticker", "stickers", "feature_sticker", 1),
    "ai_avatar": Product("ai_avatar", "avatar", "feature_ai_avatar", 1),
    "pet_ai": Product("pet_ai", "pet", "feature_pet_ai", 1),
    "family_ai": Product("family_ai", "family", "feature_family_ai", 1),
    "baby_ai": Product("baby_ai", "baby", "feature_baby_ai", 1),
    "anime_ai": Product("anime_ai", "anime", "feature_anime_ai", 1),
    "game_character": Product(
        "game_character", "game", "feature_game_character", 1
    ),
    "photo_enhance": Product("photo_enhance", "enhance", "feature_photo_enhance", 1),
    "roast_me": Product("roast_me", "roast", "feature_roast_me", 1),
}


def get_product(product_id: str) -> Product | None:
    return PRODUCT_CATALOG.get(product_id)
