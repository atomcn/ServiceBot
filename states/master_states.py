from aiogram.dispatcher.filters.state import State, StatesGroup

class MasterCompleteForm(StatesGroup):
    entering_amount = State()
    adding_feedback = State()