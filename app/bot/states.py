from aiogram.fsm.state import State, StatesGroup


class BackgroundRemovalStates(StatesGroup):
    waiting_for_image = State()


class QrCodeStates(StatesGroup):
    waiting_for_payload = State()


class MemeStates(StatesGroup):
    choosing_template = State()
    waiting_for_top_text = State()
    waiting_for_bottom_text = State()


class PixelAvatarStates(StatesGroup):
    choosing_level = State()
    waiting_for_image = State()


class PassportPhotoStates(StatesGroup):
    choosing_background = State()
    waiting_for_image = State()


class StickerStates(StatesGroup):
    waiting_for_image = State()
