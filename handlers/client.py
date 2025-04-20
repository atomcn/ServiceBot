import logging
from aiogram import types, Dispatcher
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters import Text # Для обработки кнопок "пропустить"

from states.client_states import ClientForm
from keyboards.inline import get_service_keyboard, get_photo_choice_keyboard, service_cb, photo_action_cb
from utils.google_sheets import add_new_request
from utils.notify import notify_masters, notify_admin_new_request
from config import AVAILABLE_SERVICES # Импортируем словарь услуг

# --- Обработчики состояний клиента ---

async def process_service_choice(callback_query: types.CallbackQuery, callback_data: dict, state: FSMContext):
    """Ловит выбор услуги"""
    service_id = callback_data.get("id")
    service_name = callback_data.get("name")

    await state.update_data(service_id=service_id)
    await state.update_data(service_type_name=service_name) # Сохраняем и читаемое имя

    await callback_query.message.edit_text(f"Вы выбрали: *{service_name}*\n\n"
                                           f"Теперь, пожалуйста, опишите вашу проблему или задачу как можно подробнее.",
                                           parse_mode='Markdown')
    await ClientForm.entering_description.set()
    await callback_query.answer() # Убираем часики

async def process_description(message: types.Message, state: FSMContext):
    """Ловит описание проблемы"""
    if not message.text or len(message.text.strip()) < 5:
         await message.reply("Пожалуйста, введите более подробное описание (минимум 5 символов).")
         return

    await state.update_data(description=message.text.strip())
    await message.answer("Отлично! Теперь вы можете прикрепить фотографию проблемы (если нужно) или пропустить этот шаг.",
                         reply_markup=get_photo_choice_keyboard())
    await ClientForm.uploading_photo.set() # Переходим в состояние ожидания фото или нажатия кнопки

async def process_photo(message: types.Message, state: FSMContext):
    """Ловит отправленное фото"""
    if not message.photo:
        await message.reply("Пожалуйста, отправьте фото или нажмите 'Пропустить фото'.")
        return

    # Сохраняем file_id самого большого фото
    photo_id = message.photo[-1].file_id
    await state.update_data(photo_id=photo_id)
    await message.answer("Фото получено!")
    # Переходим к следующему шагу (например, количество, если нужно)
    # await ClientForm.entering_quantity.set()
    # await message.answer("Укажите количество (например, кранов, розеток), если применимо, или введите '1', если не важно:")
    # ---- ЕСЛИ ВОПРОС О КОЛИЧЕСТВЕ НЕ НУЖЕН, ПЕРЕХОДИМ СРАЗУ К ДАТЕ: ----
    await ClientForm.entering_date.set()
    await message.answer("Когда вам удобно, чтобы мастер приехал? (Напишите дату, например, 'Завтра', '25.12', 'В ближайшее время')")


async def process_skip_photo(callback_query: types.CallbackQuery, state: FSMContext):
    """Ловит нажатие кнопки 'Пропустить фото'"""
    await state.update_data(photo_id="") # Явно указываем, что фото нет
    await callback_query.message.edit_text("Фото пропущено.")
    await callback_query.answer()
    # Переходим к следующему шагу (например, количество)
    # await ClientForm.entering_quantity.set()
    # await callback_query.message.answer("Укажите количество (например, кранов, розеток), если применимо, или введите '1', если не важно:")
    # ---- ЕСЛИ ВОПРОС О КОЛИЧЕСТВЕ НЕ НУЖЕН, ПЕРЕХОДИМ СРАЗУ К ДАТЕ: ----
    await ClientForm.entering_date.set()
    await callback_query.message.answer("Когда вам удобно, чтобы мастер приехал? (Напишите дату, например, 'Завтра', '25.12', 'В ближайшее время')")


# --- Пример обработчика доп. вопроса (количество) ---
# async def process_quantity(message: types.Message, state: FSMContext):
#     """Ловит ввод количества"""
#     # Здесь можно добавить валидацию, если нужно (например, что это число)
#     await state.update_data(quantity=message.text.strip())
#     await ClientForm.entering_date.set()
#     await message.answer("Когда вам удобно, чтобы мастер приехал? (Напишите дату, например, 'Завтра', '25.12', 'В ближайшее время')")


async def process_date(message: types.Message, state: FSMContext):
    """Ловит ввод даты"""
    await state.update_data(date=message.text.strip())
    await ClientForm.entering_time.set()
    await message.answer("Укажите удобное время (например, '14:00', 'Утро', 'В течение дня')")

async def process_time(message: types.Message, state: FSMContext):
    """Ловит ввод времени"""
    await state.update_data(time=message.text.strip())
    await ClientForm.entering_address.set()
    await message.answer("Напишите ваш адрес (улица, дом, квартира).")

async def process_address(message: types.Message, state: FSMContext):
    """Ловит ввод адреса и завершает сбор данных"""
    if not message.text or len(message.text.strip()) < 5:
         await message.reply("Пожалуйста, введите более полный адрес.")
         return

    await state.update_data(address=message.text.strip())
    user_data = await state.get_data()

    # Собираем сообщение для подтверждения (опционально, но полезно)
    # service_name = AVAILABLE_SERVICES.get(user_data.get('service_id'), 'Неизвестная услуга')
    service_name = user_data.get('service_type_name', 'Неизвестная услуга') # Берем сохраненное имя

    # --- Считаем ориентировочную стоимость (ПРИМЕР) ---
    # Логика расчета может быть сложнее, зависеть от услуги, кол-ва и т.д.
    estimated_cost = "от 500 руб." # Пример
    if user_data.get('service_id') == 'electrician':
        estimated_cost = "от 800 руб."
    elif user_data.get('service_id') == 'handyman':
        estimated_cost = "от 600 руб./час"
    await state.update_data(estimated_cost=estimated_cost) # Сохраняем для записи в таблицу
    # --- Конец примера расчета стоимости ---


    confirmation_text = (
        f"✅ Ваша заявка почти готова:\n\n"
        f"Услуга: *{service_name}*\n"
        f"Описание: {user_data.get('description', '-')}\n"
        # f"Количество: {user_data.get('quantity', '-')}\n" # Если используется
        f"Желаемая дата: {user_data.get('date', '-')}\n"
        f"Желаемое время: {user_data.get('time', '-')}\n"
        f"Адрес: {user_data.get('address', '-')}\n"
        f"Фото: {'Прикреплено' if user_data.get('photo_id') else 'Нет'}\n\n"
        f"Ориентировочная стоимость: *{estimated_cost}*\n\n"
        f"Отправляем заявку мастерам?"
    )
    # Можно добавить кнопки Да/Нет для подтверждения перед отправкой
    # await ClientForm.confirming_request.set()
    # await message.answer(confirmation_text, reply_markup=get_confirmation_keyboard(), parse_mode='Markdown')

    # --- Сразу отправляем заявку ---
    await message.answer("⏳ Отправляем вашу заявку мастерам...")

    # Добавляем заявку в Google Sheets
    request_id, error_msg = await add_new_request(user_data)

    if request_id and not error_msg:
        await message.answer(f"👍 Ваша заявка ID `{request_id}` принята! Мастера скоро получат уведомление. "
                             f"Мы сообщим вам, когда мастер возьмет заявку в работу.", parse_mode='Markdown')

        # Уведомляем мастеров и админа
        await notify_masters(message.bot, request_id, user_data)
        await notify_admin_new_request(message.bot, request_id, user_data)

    else:
        await message.answer(f"❌ Произошла ошибка при создании заявки. {error_msg or ''} Попробуйте позже или свяжитесь с поддержкой.")
        logging.error(f"Ошибка создания заявки для {user_data.get('client_id')}: {error_msg}")

    # Завершаем состояние FSM
    await state.finish()


# --- Регистрация хэндлеров ---
def register_handlers_client(dp: Dispatcher):
    # Обработка выбора услуги (callback)
    dp.register_callback_query_handler(process_service_choice, service_cb.filter(), state=ClientForm.choosing_service)

    # Обработка ввода описания
    dp.register_message_handler(process_description, state=ClientForm.entering_description)

    # Обработка фото или пропуска фото
    dp.register_message_handler(process_photo, content_types=types.ContentType.PHOTO, state=ClientForm.uploading_photo)
    dp.register_callback_query_handler(process_skip_photo, photo_action_cb.filter(action="skip"), state=ClientForm.uploading_photo)
    # Защита от неверного ввода на этапе фото
    dp.register_message_handler(lambda message: message.reply("Пожалуйста, отправьте фото или нажмите 'Пропустить фото'."),
                                content_types=types.ContentType.ANY,
                                state=ClientForm.uploading_photo)

    # Обработка ввода количества (если используется)
    # dp.register_message_handler(process_quantity, state=ClientForm.entering_quantity)

    # Обработка ввода даты
    dp.register_message_handler(process_date, state=ClientForm.entering_date)

    # Обработка ввода времени
    dp.register_message_handler(process_time, state=ClientForm.entering_time)

    # Обработка ввода адреса (финальный шаг)
    dp.register_message_handler(process_address, state=ClientForm.entering_address)

    # Обработчик для кнопки "Новая заявка", если пользователь уже не в состоянии FSM
    # dp.register_message_handler(lambda message: asyncio.run(cmd_start(message, FSMContext(dp.storage, message.chat.id, message.from_user.id))), Text(equals="Новая заявка", ignore_case=True), state=None)