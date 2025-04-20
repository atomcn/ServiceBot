import os
from dotenv import load_dotenv
import logging

load_dotenv()

# --- Загрузка токена ---
BOT_TOKEN = os.getenv("BOT_TOKEN")
if not BOT_TOKEN:
    # Используем logging.critical вместо print и raise, чтобы лог был единообразным
    logging.critical("Не найден BOT_TOKEN в .env файле! Бот не может быть запущен.")
    raise ValueError("Не найден BOT_TOKEN в .env файле!")

# --- Загрузка ADMIN_ID (Обязательный, один ID) ---
admin_id_str = os.getenv("ADMIN_ID")
if not admin_id_str:
    logging.critical("Не найден обязательный ADMIN_ID в .env файле!")
    raise ValueError("Не найден обязательный ADMIN_ID в .env файле.")
try:
    ADMIN_ID = int(admin_id_str)
    logging.info(f"ADMIN_ID загружен: {ADMIN_ID}")
except ValueError:
    logging.critical(f"Неверный формат ADMIN_ID в .env файле: '{admin_id_str}'. Ожидается одно целое число.")
    raise ValueError("Неверный формат ADMIN_ID в .env файле. Ожидается одно целое число.")


# --- Функция для парсинга списка ID (для MASTER_IDS) ---
# Она остается, так как мастера могут быть множественными или отсутствовать
def parse_ids(env_var_name):
    ids_str = os.getenv(env_var_name)
    parsed_ids = []
    if ids_str:
        try:
            # Убираем лишние пробелы и пустые строки после разделения
            raw_ids = [id_part.strip() for id_part in ids_str.split(',') if id_part.strip()]
            parsed_ids = [int(id_str) for id_str in raw_ids]
        except ValueError:
            # Используем logging.warning для некритичных проблем
            logging.warning(f"Неверный формат ID в переменной окружения {env_var_name}='{ids_str}'. "
                            f"Ожидаются числа через запятую. Список будет пустым.")
            # Возвращаем пустой список, не прерывая работу
            return []
    # Если переменная не задана или пуста, возвращаем пустой список
    return parsed_ids

# --- Загрузка MASTER_IDS (Необязательные, список ID) ---
MASTER_IDS = parse_ids("MASTER_IDS")
if MASTER_IDS:
    logging.info(f"MASTER_IDS загружены: {MASTER_IDS}")
else:
    # Просто информируем, что мастера не заданы, это не ошибка
    logging.info("MASTER_IDS не найдены или не заданы в .env файле. Список мастеров пуст.")


# --- Google Sheets ---
GOOGLE_SHEET_NAME = os.getenv("GOOGLE_SHEET_NAME")
if not GOOGLE_SHEET_NAME:
    logging.critical("Не найден GOOGLE_SHEET_NAME в .env файле. Укажите имя таблицы.")
    raise ValueError("Не найден GOOGLE_SHEET_NAME в .env файле. Укажите имя таблицы.")
else:
    logging.info(f"Имя Google таблицы: '{GOOGLE_SHEET_NAME}'")

GOOGLE_CREDENTIALS_FILE = os.getenv("GOOGLE_CREDENTIALS_FILE", "credentials.json")
logging.info(f"Файл учетных данных Google: '{GOOGLE_CREDENTIALS_FILE}'")


# --- Процент комиссии ---
try:
    service_commission_str = os.getenv("SERVICE_COMMISSION_PERCENT", "15")
    SERVICE_COMMISSION_PERCENT = int(service_commission_str)
    if not (0 <= SERVICE_COMMISSION_PERCENT <= 100):
        logging.warning(f"SERVICE_COMMISSION_PERCENT ({SERVICE_COMMISSION_PERCENT}%) вне допустимого диапазона (0-100). Используется значение по умолчанию 15.")
        SERVICE_COMMISSION_PERCENT = 15
    else:
         logging.info(f"Процент комиссии сервиса: {SERVICE_COMMISSION_PERCENT}%")

except ValueError:
    logging.warning(f"Неверный формат SERVICE_COMMISSION_PERCENT ('{service_commission_str}'). Используется значение по умолчанию 15.")
    SERVICE_COMMISSION_PERCENT = 15

# --- Типы услуг ---
AVAILABLE_SERVICES = {
    "sanitizer": "Сантехник Plumbing",
    "electrician": "Электрик Electrician",
    "handyman": "Мастер на час Handyman",
    "other": "Другое Other"
}
logging.info(f"Доступные услуги: {list(AVAILABLE_SERVICES.values())}")