from aiogram import Router

from app.bot.handlers.admin import router as admin_router
from app.bot.handlers.background_removal import router as background_removal_router
from app.bot.handlers.common import navigation_router
from app.bot.handlers.common import router as common_router
from app.bot.handlers.local_images import router as local_images_router
from app.bot.handlers.meme import router as meme_router
from app.bot.handlers.payments import router as payments_router
from app.bot.handlers.qr_code import router as qr_code_router

router = Router(name="handlers")
router.include_router(admin_router)
router.include_router(payments_router)
router.include_router(navigation_router)
router.include_router(background_removal_router)
router.include_router(qr_code_router)
router.include_router(meme_router)
router.include_router(local_images_router)
router.include_router(common_router)

__all__ = ["router"]
