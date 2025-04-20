from aiogram.dispatcher.filters.state import State, StatesGroup

class ClientForm(StatesGroup):
    choosing_service = State()
    entering_description = State()
    uploading_photo = State() # Состояние ожидания фото
    entering_quantity = State() # Пример доп. вопроса
    entering_date = State()
    entering_time = State()
    entering_address = State()
    confirming_request = State() # Опциональное состояние подтверждения