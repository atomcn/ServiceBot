import logging
import asyncio

from aiogram import Bot, Dispatcher, types
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.utils import executor

from config import BOT_TOKEN
from utils.google_sheets import init_gspread # Импортируем функцию инициализации
from handlers.common import register_handlers_common
from handlers.client import register_handlers_client
from handlers.master import register_handlers_master
from handlers.admin import register_handlers_admin

# Настройка логирования
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

async def on_startup(dp: Dispatcher):
    """Выполняется при старте бота"""
    logging.info("Запуск бота...")
    try:
        # Инициализируем Google Sheets один раз при старте
        init_gspread()
        logging.info("Google Sheets инициализирован.")
    except Exception as e:
        logging.critical(f"Не удалось инициализировать Google Sheets при старте: {e}")
        # Здесь можно решить, останавливать ли бота, если таблицы недоступны
        # raise

    # Регистрация хэндлеров
    register_handlers_common(dp)
    register_handlers_client(dp)
    register_handlers_master(dp)
    register_handlers_admin(dp)
    logging.info("Хэндлеры зарегистрированы.")
    # Установка команд меню (опционально)
    await set_commands(dp.bot)
    logging.info("Команды установлены.")


async def set_commands(bot: Bot):
    """Установка команд в меню Telegram"""
    commands = [
        types.BotCommand(command="/start", description="🚀 Запустить/Перезапустить бота"),
        types.BotCommand(command="/help", description="❓ Помощь"),
        # Можно добавить специфичные команды для ролей, но они будут видны всем
        # types.BotCommand(command="/new_request", description="📝 Создать заявку (Клиент)"),
        # types.BotCommand(command="/requests", description="📋 Просмотр заявок (Админ)"),
        # types.BotCommand(command="/stats", description="📊 Статистика (Админ)"),
    ]
    try:
        await bot.set_my_commands(commands)
    except Exception as e:
        logging.error(f"Ошибка установки команд: {e}")


def main():
    # Проверка наличия токена перед созданием бота
    if not BOT_TOKEN:
        logging.critical("Токен бота не найден. Убедитесь, что он указан в .env файле.")
        return # Не запускаем бота без токена

    # Инициализация бота и диспетчера
    bot = Bot(token=BOT_TOKEN)
    storage = MemoryStorage() # Хранилище состояний в памяти (для продакшена лучше RedisStorage)
    dp = Dispatcher(bot, storage=storage)

    # Запуск бота
    executor.start_polling(dp, skip_updates=True, on_startup=on_startup)

if __name__ == '__main__':
    main()