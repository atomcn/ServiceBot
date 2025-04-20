import logging
from aiogram import Bot
from aiogram.utils.exceptions import BotBlocked, ChatNotFound, UserDeactivated, TelegramAPIError
from config import MASTER_IDS, ADMIN_ID, SERVICE_COMMISSION_PERCENT
from keyboards.inline import get_master_new_request_keyboard, get_admin_master_report_keyboard, get_master_complete_request_keyboard

async def notify_masters(bot: Bot, request_id: str, request_data: dict):
    """Отправляет уведомление о новой заявке всем мастерам."""
    service_name = request_data.get('service_type_name', 'Не указан')
    description = request_data.get('description', 'Нет описания')
    address = request_data.get('address', 'Не указан')
    photo_id = request_data.get('photo_id')

    text = (
        f"🔔 Новая заявка! ID: `{request_id}`\n\n"
        f"Услуга: *{service_name}*\n"
        f"Описание: {description}\n"
        f"Адрес: {address}\n"
        # Можно добавить дату/время, если нужно
    )
    keyboard = get_master_new_request_keyboard(request_id)

    for master_id in MASTER_IDS:
        try:
            if photo_id:
                 await bot.send_photo(master_id, photo_id, caption=text, reply_markup=keyboard, parse_mode='Markdown')
            else:
                 await bot.send_message(master_id, text, reply_markup=keyboard, parse_mode='Markdown')
            logging.info(f"Уведомление о заявке {request_id} отправлено мастеру {master_id}")
        except (BotBlocked, ChatNotFound, UserDeactivated):
            logging.warning(f"Мастер {master_id} заблокировал бота или чат не найден.")
        except TelegramAPIError as e:
            logging.error(f"Ошибка отправки уведомления мастеру {master_id}: {e}")
        except Exception as e:
            logging.error(f"Неизвестная ошибка при отправке мастеру {master_id}: {e}")

async def notify_admin_new_request(bot: Bot, request_id: str, request_data: dict):
    """Уведомляет администратора о новой заявке (с кнопкой 'Принять')"""
    client_username = request_data.get('client_username', 'N/A')
    client_id = request_data.get('client_id', 'N/A')
    service_name = request_data.get('service_type_name', 'Не указан')
    text = (
        f"📝 Создана новая заявка ID: `{request_id}`\n"
        f"Клиент: @{client_username} (ID: {client_id})\n"
        f"Услуга: {service_name}\n"
        f"[Открыть чат с клиентом](tg://user?id={client_id})"
    )

    keyboard = get_master_new_request_keyboard(request_id)

    try:
        await bot.send_message(ADMIN_ID, text, reply_markup=keyboard, parse_mode='Markdown', disable_web_page_preview=True)
        logging.info(f"Уведомление о новой заявке {request_id} отправлено админу {ADMIN_ID}")
    except Exception as e:
        logging.error(f"Ошибка отправки уведомления админу {ADMIN_ID} о новой заявке: {e}")

async def notify_client_request_accepted(bot: Bot, client_id: int, request_id: str, master_username: str):
    """Уведомляет клиента, что его заявка принята."""
    text = (
        f"✅ Ваша заявка ID `{request_id}` принята!\n"
        f"Мастер @{master_username} скоро свяжется с вами или приедет в назначенное время."
    )
    try:
        await bot.send_message(client_id, text, parse_mode='Markdown')
    except Exception as e:
        logging.error(f"Ошибка отправки уведомления клиенту {client_id} о принятии заявки: {e}")

async def notify_admin_request_accepted(bot: Bot, request_id: str, master_username: str, master_id: int):
     """Уведомляет админа, что заявка принята мастером."""
     text = (
         f"📌 Заявка ID `{request_id}` принята мастером @{master_username} (ID: {master_id})."
         # Можно добавить ссылку на чат с мастером: tg://user?id={master_id}
     )

     keyboard = get_master_complete_request_keyboard(request_id)

     try:
         await bot.send_message(ADMIN_ID, text, reply_markup=keyboard, parse_mode='Markdown', disable_web_page_preview=True)
         logging.info(f"Уведомление о принятии заявки {request_id} мастером {master_id} отправлено админу {ADMIN_ID}")
     except Exception as e:
         logging.error(f"Ошибка отправки уведомления админу {ADMIN_ID} о принятии заявки: {e}")


async def notify_admin_master_report(bot: Bot, request_id: str, master_username: str, master_id: int, amount: float, commission: float, feedback: str):
    """Уведомляет админа об отчете мастера."""
    text = (
        f"💰 Отчет по заявке ID `{request_id}` от мастера @{master_username} (ID: {master_id})\n\n"
        f"Получено от клиента: *{amount:.2f}*\n"
        f"Комиссия сервиса ({SERVICE_COMMISSION_PERCENT}%): *{commission:.2f}*\n"
        f"Отзыв мастера: {feedback if feedback else 'Нет отзыва'}"
    )
    keyboard = get_admin_master_report_keyboard(request_id, master_id) # Добавим кнопки для связи
    try:
        await bot.send_message(ADMIN_ID, text, reply_markup=keyboard, parse_mode='Markdown')
        logging.info(f"Отчет по заявке {request_id} от мастера {master_id} отправлен админу {ADMIN_ID}")
    except Exception as e:
        logging.error(f"Ошибка отправки отчета админу {ADMIN_ID}: {e}")

async def notify_client_request_completed(bot: Bot, client_id: int, request_id: str):
    """Уведомляет клиента о завершении работы (опционально)."""
    text = (
        f"🏁 Работа по вашей заявке ID `{request_id}` завершена мастером.\n"
        f"Спасибо, что воспользовались нашим сервисом!"
        # Здесь можно добавить просьбу оставить отзыв боту или ссылку на форму отзыва
    )
    try:
        await bot.send_message(client_id, text, parse_mode='Markdown')
    except Exception as e:
        logging.error(f"Ошибка отправки уведомления клиенту {client_id} о завершении: {e}")