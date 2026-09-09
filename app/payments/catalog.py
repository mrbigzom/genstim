from dataclasses import dataclass

STARS_CURRENCY = "XTR"


@dataclass(frozen=True, slots=True)
class CreditPackage:
    id: str
    stars_amount: int
    credits: int


# Telegram Stars top-up packages. Change package prices and credit amounts here.
CREDIT_PACKAGES: dict[str, CreditPackage] = {
    "credits_10": CreditPackage("credits_10", stars_amount=10, credits=10),
    "credits_30": CreditPackage("credits_30", stars_amount=25, credits=30),
    "credits_65": CreditPackage("credits_65", stars_amount=50, credits=65),
}


def get_credit_package(package_id: str) -> CreditPackage | None:
    return CREDIT_PACKAGES.get(package_id)
