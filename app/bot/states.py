from aiogram.fsm.state import State, StatesGroup


class BackgroundRemovalStates(StatesGroup):
    waiting_for_image = State()
