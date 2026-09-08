from aiogram import Router

from app.bot.handlers.background_removal import router as background_removal_router
from app.bot.handlers.common import router as common_router
from app.bot.handlers.qr import router as qr_router

router = Router(name="handlers")
router.include_router(background_removal_router)
router.include_router(qr_router)
router.include_router(common_router)

__all__ = ["router"]
