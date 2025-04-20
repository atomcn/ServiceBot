import logging
from aiogram import types, Dispatcher
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters import ChatTypeFilter, Text # ChatTypeFilter для ЛС
from aiogram.utils.exceptions import MessageNotModified

from config import MASTER_IDS, ADMIN_ID, SERVICE_COMMISSION_PERCENT
from states.master_states import MasterCompleteForm
from keyboards.inline import request_action_cb, get_master_complete_request_keyboard, get_master_skip_feedback_keyboard
from utils.google_sheets import update_request_status, get_request_details, record_completion_details, get_client_id_for_request
from utils.notify import notify_client_request_accepted, notify_admin_request_accepted, notify_admin_master_report, notify_client_request_completed

# --- Обработчики для Мастера ---

async def process_accept_request(callback_query: types.CallbackQuery, callback_data: dict, state: FSMContext):
    """Обрабатывает нажатие кнопки 'Принять заявку'"""
    request_id = callback_data.get("req_id")
    user_id = callback_query.from_user.id
    user_username = callback_query.from_user.username or f"id{user_id}"

    # Проверяем, является ли пользователь мастером
    if user_id != ADMIN_ID and user_id not in MASTER_IDS:
        await callback_query.answer("Эта кнопка доступна только мастерам и администратору.", show_alert=True)
        return

    # Проверяем статус заявки в Google Sheets перед принятием
    request_details = await get_request_details(request_id)
    if not request_details:
        await callback_query.answer("Ошибка: Заявка не найдена.", show_alert=True)
        return

    current_status = request_details.get('Status')
    if current_status != 'New':
        assigned_master = request_details.get('Master Username', 'другим мастером')
        await callback_query.answer(f"Эта заявка уже '{current_status}' (принята {assigned_master}).", show_alert=True)
        # Можно убрать кнопки у этого сообщения
        try:
            await callback_query.message.edit_reply_markup(reply_markup=None)
        except MessageNotModified:
            pass # Ничего страшного, если клавиатура уже убрана
        return

    # Обновляем статус в Google Sheets
    success, message = await update_request_status(request_id, 'Assigned', user_id, user_username)

    if success:
        action_user_role = "Администратор" if user_id == ADMIN_ID else "Мастер"
        await callback_query.answer(f"✅ Заявка принята ({action_user_role})!", show_alert=False)
        try:
            # --- ИЗМЕНЕНИЕ: Используем user_username ---
            new_text = callback_query.message.md_text + f"\n\n*Заявка принята вами (@{user_username}).*"
            # --- КОНЕЦ ИЗМЕНЕНИЯ ---
            complete_keyboard = get_master_complete_request_keyboard(request_id)
            await callback_query.message.edit_text(
                new_text + "\n\n*Используйте кнопку ниже, когда работа будет завершена.*",
                reply_markup=complete_keyboard,
                parse_mode='Markdown')
        except MessageNotModified:
             pass # Если сообщение не изменилось (например, из-за частого нажатия)
        except Exception as e:
             logging.error(f"Ошибка редактирования сообщения пользователю {user_id} после принятия заявки {request_id}: {e}")
             # Отправим простое сообщение в крайнем случае
             await callback_query.message.answer(f"Вы приняли заявку `{request_id}`. Нажмите кнопку ниже, когда закончите.",
                                                 reply_markup=get_master_complete_request_keyboard(request_id), parse_mode='Markdown')


        client_id = await get_client_id_for_request(request_id)
        if client_id:
            await notify_client_request_accepted(callback_query.bot, int(client_id), request_id, user_username)

        # Уведомляем админа ТОЛЬКО если заявку принял МАСТЕР (админ и так знает, если принял сам)
        if user_id != ADMIN_ID:
            await notify_admin_request_accepted(callback_query.bot, request_id, user_username, user_id)
        # Если принял админ, можно добавить лог или просто пропустить уведомление админу
        else:
            logging.info(f"Администратор ({user_id}) сам принял заявку {request_id}.")


    else:
        await callback_query.answer(f"❌ Ошибка при принятии заявки: {message}", show_alert=True)


async def process_complete_request(callback_query: types.CallbackQuery, callback_data: dict, state: FSMContext):
    """Обрабатывает нажатие кнопки 'Работа выполнена'"""
    request_id = callback_data.get("req_id")
    user_id = callback_query.from_user.id

    if user_id != ADMIN_ID and user_id not in MASTER_IDS:
        await callback_query.answer("Эта кнопка доступна только мастерам и администратору.", show_alert=True)
        return

    # Проверим, что заявка действительно назначена этому мастеру (опционально, но хорошо бы)
    request_details = await get_request_details(request_id)
    if not request_details:
        await callback_query.answer("Ошибка: Заявка не найдена.", show_alert=True)
        return

    assigned_master_id_str = request_details.get('Master ID')
    assigned_master_id = int(
        assigned_master_id_str) if assigned_master_id_str and assigned_master_id_str.isdigit() else None
    current_status = request_details.get('Status')

    is_admin = (user_id == ADMIN_ID)
    is_assigned_user = (assigned_master_id == user_id)

    # Запретить, если статус уже 'Completed'
    if current_status == 'Completed':
        await callback_query.answer("Эта заявка уже отмечена как выполненная.", show_alert=True)
        return

    # Разрешить завершение, если:
    # 1. Текущий пользователь - админ И заявка назначена (не важно кому) И статус 'Assigned' или 'In Progress'
    # 2. Текущий пользователь - НЕ админ И заявка назначена ИМЕННО ЕМУ И статус 'Assigned' или 'In Progress'
    can_complete = False
    if current_status in ['Assigned', 'In Progress']:  # Допускаем статус 'In Progress' если он будет использоваться
        if is_admin and assigned_master_id is not None:
            can_complete = True
        elif not is_admin and is_assigned_user:
            can_complete = True

    if not can_complete:
        # Определяем причину отказа
        if current_status == 'New':
            error_msg = "Ошибка: Заявка еще не принята в работу."
        elif current_status not in ['Assigned', 'In Progress', 'Completed']:  # На случай других статусов
            error_msg = f"Ошибка: Нельзя завершить заявку в статусе '{current_status}'."
        elif not assigned_master_id:  # Должно быть поймано статусом 'New', но на всякий случай
            error_msg = "Ошибка: Заявка никому не назначена."
        elif not is_admin and not is_assigned_user:
            error_msg = "Ошибка: Эта заявка не назначена вам."
        else:  # Непредвиденный случай
            error_msg = "Ошибка: Нет прав на завершение этой заявки."
        await callback_query.answer(error_msg, show_alert=True)
        return
    # --- КОНЕЦ ИЗМЕНЕНИЯ ---

    # Переводим пользователя (мастера или админа) в состояние ввода суммы
    await state.update_data(request_id_to_complete=request_id)
    await MasterCompleteForm.entering_amount.set()
    await callback_query.message.answer(f"Завершение заявки `{request_id}`.\n"
                                        f"Пожалуйста, введите точную сумму, полученную от клиента (только число, например: 1500 или 2100.50):",
                                        parse_mode='Markdown')
    await callback_query.answer()


async def process_amount_received(message: types.Message, state: FSMContext):
    """Обрабатывает ввод суммы мастером"""
    amount_str = message.text.strip()
    user_id = message.from_user.id
    user_username = message.from_user.username or f"id{user_id}"
    user_data = await state.get_data()
    request_id = user_data.get("request_id_to_complete")

    if not request_id:
        await message.reply("Произошла ошибка, не найден ID заявки. Попробуйте нажать 'Работа выполнена' еще раз.")
        await state.finish()
        return

    # Валидация суммы
    try:
        amount = float(amount_str.replace(',', '.'))
        if amount < 0:
            await message.reply("Сумма не может быть отрицательной. Пожалуйста, введите корректное число.")
            return
    except ValueError:
        await message.reply("Неверный формат суммы. Пожалуйста, введите только число (например, 1500 или 1500.50).")
        return

    commission = round((amount * SERVICE_COMMISSION_PERCENT) / 100, 2)

    await state.update_data(amount_received=amount_str) # Сохраняем как строку для записи
    await state.update_data(calculated_commission=commission)
    await state.update_data(completing_user_id=user_id)
    await state.update_data(completing_user_username=user_username)

    await message.answer(f"Сумма принята: *{amount:.2f}*\n"
                         f"Комиссия сервиса ({SERVICE_COMMISSION_PERCENT}%): *{commission:.2f}*\n\n"
                         f"Теперь вы можете добавить необязательный комментарий или отзыв о работе/клиенте (он будет виден только администратору).",
                         reply_markup=get_master_skip_feedback_keyboard(),
                         parse_mode='Markdown')
    await MasterCompleteForm.adding_feedback.set()


async def process_master_feedback(message: types.Message, state: FSMContext):
    """Обрабатывает ввод отзыва мастером"""
    feedback = message.text.strip()
    await state.update_data(master_feedback=feedback)
    await finalize_completion(message, state)

async def process_skip_feedback(callback_query: types.CallbackQuery, state: FSMContext):
    """Обрабатывает пропуск отзыва"""
    await state.update_data(master_feedback="") # Пустой отзыв
    await callback_query.answer("Отзыв пропущен.")
    # Нужно передать объект message для унификации finalize_completion
    await finalize_completion(callback_query.message, state)
    # Убираем кнопки у сообщения с предложением оставить отзыв
    try:
        await callback_query.message.edit_reply_markup(reply_markup=None)
    except MessageNotModified:
        pass


async def finalize_completion(message_or_cq_message: types.Message, state: FSMContext):
    """Общая функция для завершения процесса отчета мастера"""
    user_data = await state.get_data()
    request_id = user_data.get("request_id_to_complete")
    amount_str = user_data.get("amount_received")
    commission = user_data.get("calculated_commission")
    feedback = user_data.get("master_feedback", "")
    completing_user_id = user_data.get("completing_user_id")
    completing_user_username = user_data.get("completing_user_username")

    if not all([request_id, amount_str is not None, commission is not None]):
         # Используем message_or_cq_message.answer для ответа
        await message_or_cq_message.answer("Произошла внутренняя ошибка при сохранении данных. Пожалуйста, сообщите администратору.")
        logging.error(f"Ошибка finalize_completion: не хватает данных в state для мастера {master_id}, заявка {request_id}. State: {user_data}")
        await state.finish()
        return

    # Записываем данные в Google Sheets
    success, msg = await record_completion_details(request_id, amount_str, feedback)

    if success:
        # Уведомляем админа
        # Преобразуем amount_str обратно в float для передачи в уведомление
        try:
             amount_float = float(amount_str.replace(',', '.'))
        except ValueError:
             amount_float = 0.0 # Или другое значение по умолчанию/обработка ошибки
             logging.error(f"Не удалось преобразовать amount_str '{amount_str}' в float для уведомления админа (заявка {request_id})")

        await notify_admin_master_report(message_or_cq_message.bot, request_id, completing_user_username, completing_user_id, amount_float, commission, feedback)

        # Уведомляем клиента (опционально)
        client_id = await get_client_id_for_request(request_id)
        if client_id:
            await notify_client_request_completed(message_or_cq_message.bot, int(client_id), request_id)

        action_user_role = "Администратором" if completing_user_id == ADMIN_ID else "Мастером"
        await message_or_cq_message.answer(f"✅ Отчет по заявке `{request_id}` успешно сохранен ({action_user_role}).",
                                           parse_mode='Markdown')
    else:
        await message_or_cq_message.answer(f"❌ Ошибка при сохранении отчета: {msg}")
        logging.error(f"Ошибка записи completion details для заявки {request_id} пользователем {completing_user_id}: {msg}")

    await state.finish()

# --- Регистрация хэндлеров ---
def register_handlers_master(dp: Dispatcher):
    # Обработка нажатия "Принять заявку" (только от мастеров в ЛС или группах, где есть бот)
    dp.register_callback_query_handler(process_accept_request, request_action_cb.filter(action="accept"), state="*")

    # Обработка нажатия "Работа выполнена"
    dp.register_callback_query_handler(process_complete_request, request_action_cb.filter(action="complete"), state="*")

    # Обработка ввода суммы (только от мастера в ЛС)
    dp.register_message_handler(process_amount_received, ChatTypeFilter(types.ChatType.PRIVATE), state=MasterCompleteForm.entering_amount)

    # Обработка ввода отзыва
    dp.register_message_handler(process_master_feedback, ChatTypeFilter(types.ChatType.PRIVATE), state=MasterCompleteForm.adding_feedback)
    # Обработка пропуска отзыва (callback)
    dp.register_callback_query_handler(process_skip_feedback, Text(equals="skip_feedback"), state=MasterCompleteForm.adding_feedback)