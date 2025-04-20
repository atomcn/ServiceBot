import logging
from aiogram import types, Dispatcher
from aiogram.dispatcher.filters import Command, ChatTypeFilter
from aiogram.utils.exceptions import ChatNotFound, BotBlocked, UserDeactivated

from config import ADMIN_ID, MASTER_IDS
from utils.google_sheets import get_all_requests_data
from decimal import Decimal, InvalidOperation # Используем Decimal для точных расчетов с деньгами

# --- Команды Администратора ---

async def cmd_requests(message: types.Message):
    """Показывает последние N заявок"""
    # --- ИЗМЕНЕНИЕ ЗДЕСЬ ---
    # Фильтр в register_handlers_admin уже должен отсечь не-админов,
    # но эта проверка как дополнительная защита теперь должна быть на НЕРАВЕНСТВО
    if message.from_user.id != ADMIN_ID: # Было: if message.from_user.id not in ADMIN_ID:
        # Эта строка в идеале никогда не должна выполниться из-за фильтра user_id=ADMIN_ID
        logging.warning(f"Попытка доступа к /requests от user {message.from_user.id}, не являющегося админом {ADMIN_ID}")
        return await message.reply("Эта команда доступна только администратору.")
    try:
        all_requests = await get_all_requests_data()
        if not all_requests:
            await message.answer("Заявок пока нет.")
            return

        # Показываем последние 10 заявок для краткости
        num_to_show = 10
        recent_requests = all_requests[-num_to_show:]
        recent_requests.reverse() # Показать самые новые первыми

        response = f"📋 Последние {len(recent_requests)} заявок:\n\n"
        for req in recent_requests:
            # Безопасное получение значений с помощью .get()
            req_id = req.get('Request ID', 'N/A')
            status = req.get('Status', 'N/A')
            service = req.get('Service Type', 'N/A')
            client = req.get('Client Username', f"ID: {req.get('Client ID', 'N/A')}")
            master = req.get('Master Username', '-')
            created_at = req.get('Timestamp Created', 'N/A') # Предполагаем, что дата уже в нужном формате

            response += (
                f"🆔 `{req_id}` | Статус: *{status}*\n"
                f"👤 Клиент: @{client}\n"
                f"🛠 Услуга: {service}\n"
                f"👷 Мастер: @{master}\n"
                f"📅 Создана: {created_at}\n"
                f"--------------------\n"
            )

        if len(response) > 4096: # Ограничение Telegram
             response = response[:4090] + "\n(...)"

        await message.answer(response, parse_mode='Markdown')

    except Exception as e:
        logging.exception("Ошибка при получении списка заявок для админа:")
        await message.answer(f"Произошла ошибка при получении данных: {e}")

async def cmd_stats(message: types.Message):
    """Показывает статистику по доходам и комиссии"""
    if message.from_user.id != ADMIN_ID: # Было: if message.from_user.id not in ADMIN_ID:
        logging.warning(f"Попытка доступа к /stats от user {message.from_user.id}, не являющегося админом {ADMIN_ID}")
        return await message.reply("Эта команда доступна только администратору.")

    try:
        all_requests = await get_all_requests_data()
        if not all_requests:
            await message.answer("Нет данных для статистики.")
            return

        total_revenue = Decimal('0.0')
        total_commission = Decimal('0.0')
        completed_count = 0

        for req in all_requests:
            if req.get('Status') == 'Completed':
                try:
                    # Обрабатываем суммы, записанные с запятой или точкой
                    amount_str = str(req.get('Amount Received', '0')).replace(',', '.')
                    commission_str = str(req.get('Service Commission', '0')).replace(',', '.')

                    amount = Decimal(amount_str) if amount_str else Decimal('0.0')
                    commission = Decimal(commission_str) if commission_str else Decimal('0.0')

                    total_revenue += amount
                    total_commission += commission
                    completed_count += 1
                except InvalidOperation:
                    logging.warning(f"Не удалось обработать сумму/комиссию для заявки {req.get('Request ID')}: "
                                    f"Amount='{req.get('Amount Received', '')}', Commission='{req.get('Service Commission', '')}'")
                except Exception as e:
                     logging.warning(f"Неожиданная ошибка при обработке статистики для заявки {req.get('Request ID')}: {e}")


        response = (
            f"📊 Статистика по выполненным заявкам ({completed_count} шт.):\n\n"
            f"💰 Общая сумма, полученная от клиентов: *{total_revenue:.2f}*\n"
            f"💸 Общая комиссия сервиса: *{total_commission:.2f}*"
        )
        await message.answer(response, parse_mode='Markdown')

    except Exception as e:
        logging.exception("Ошибка при расчете статистики для админа:")
        await message.answer(f"Произошла ошибка при расчете статистики: {e}")


async def cmd_masters(message: types.Message):
    """Показывает список зарегистрированных мастеров."""
    # Проверка на админа (дополнительная, т.к. есть фильтр)
    if message.from_user.id != ADMIN_ID:
        logging.warning(f"Попытка доступа к /masters от user {message.from_user.id}, не являющегося админом {ADMIN_ID}")
        return await message.reply("Эта команда доступна только администратору.")

    if not MASTER_IDS:
        await message.answer("ℹ️ Список мастеров пуст. Добавьте ID мастеров в файл конфигурации (.env) и перезапустите бота.")
        return

    response_lines = ["👷 Список зарегистрированных мастеров:\n"]
    bot = message.bot # Получаем объект бота для запроса информации о пользователе

    for master_id in MASTER_IDS:
        user_info_str = f"ID: `{master_id}`"
        try:
            # Пытаемся получить информацию о пользователе (может не сработать из-за приватности)
            chat = await bot.get_chat(master_id)
            username = f"@{chat.username}" if chat.username else ""
            full_name = chat.full_name
            user_info_str = f"- {full_name} ({username}) [ID: `{master_id}`](tg://user?id={master_id})"

        except (ChatNotFound, BotBlocked, UserDeactivated):
            user_info_str = f"- ID: `{master_id}` (Не удалось получить имя/юзернейм - возможно, неактивен или заблокировал бота)"
        except Exception as e:
            user_info_str = f"- ID: `{master_id}` (Ошибка получения данных: {e})"
            logging.error(f"Ошибка при получении данных для мастера {master_id}: {e}")

        response_lines.append(user_info_str)

    response = "\n".join(response_lines)
    # Отключаем превью для ссылок tg://user?id=...
    await message.answer(response, parse_mode='Markdown', disable_web_page_preview=True)

# --- Регистрация хэндлеров ---
def register_handlers_admin(dp: Dispatcher):
    # Регистрируем команды только для администраторов в личных чатах
    dp.register_message_handler(cmd_requests, Command("requests"), ChatTypeFilter(types.ChatType.PRIVATE), user_id=ADMIN_ID)
    dp.register_message_handler(cmd_stats, Command("stats"), ChatTypeFilter(types.ChatType.PRIVATE), user_id=ADMIN_ID)
    dp.register_message_handler(cmd_masters, Command("masters"), ChatTypeFilter(types.ChatType.PRIVATE), user_id=ADMIN_ID)

    # Можно добавить обработчики для callback'ов от админских клавиатур, если они будут
    # dp.register_callback_query_handler(process_admin_action, admin_action_cb.filter(), user_id=ADMIN_IDS)