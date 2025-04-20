import logging
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import datetime
import uuid

from config import GOOGLE_CREDENTIALS_FILE, GOOGLE_SHEET_NAME, SERVICE_COMMISSION_PERCENT

# Настроим логирование для gspread, чтобы видеть возможные проблемы
logging.getLogger('gspread').setLevel(logging.INFO)
logging.getLogger('oauth2client').setLevel(logging.WARNING)

# --- Google Sheets Setup ---
scope = ["https://spreadsheets.google.com/feeds", 'https://www.googleapis.com/auth/spreadsheets',
         "https://www.googleapis.com/auth/drive.file", "https://www.googleapis.com/auth/drive"]

creds = None
client = None
sheet = None

def init_gspread():
    """Инициализирует подключение к Google Sheets."""
    global creds, client, sheet
    worksheet_name = "Заказы" # Имя конкретного листа внутри таблицы
    try:
        creds = ServiceAccountCredentials.from_json_keyfile_name(GOOGLE_CREDENTIALS_FILE, scope)
        client = gspread.authorize(creds)

        # --- Изменения здесь: Открываем по имени ---
        print(f"Попытка открыть таблицу с именем: '{GOOGLE_SHEET_NAME}'...")
        spreadsheet = client.open(GOOGLE_SHEET_NAME) # Открываем всю книгу по имени
        print(f"Таблица '{GOOGLE_SHEET_NAME}' успешно открыта.")

        print(f"Попытка получить лист с именем: '{worksheet_name}'...")
        sheet = spreadsheet.worksheet(worksheet_name) # Получаем конкретный лист по его имени
        print(f"Лист '{worksheet_name}' успешно получен.")
        # --- Конец изменений ---

        print("Успешное подключение к Google Sheets.")
        # Проверка наличия заголовков (остается без изменений)
        header = sheet.row_values(1)
        expected_header = [
            'Request ID', 'Timestamp Created', 'Client ID', 'Client Username',
            'Service Type', 'Description', 'Photo File ID', 'Quantity',
            'Estimated Cost', 'Desired Date', 'Desired Time', 'Address',
            'Status', 'Master ID', 'Master Username', 'Timestamp Assigned',
            'Timestamp Completed', 'Amount Received', 'Service Commission', 'Master Feedback'
        ]
        if header != expected_header:
            print("Внимание: Заголовки в Google Sheet не соответствуют ожидаемым.")
            print("Ожидаемые:", expected_header)
            print("Текущие:  ", header)
        #     # Опционально: можно автоматически установить заголовки, если лист пуст
        # if not sheet.get_all_values():
        #     sheet.append_row(expected_header)
        #     print("Заголовки добавлены.")

    except FileNotFoundError:
        print(f"Ошибка: Файл учетных данных '{GOOGLE_CREDENTIALS_FILE}' не найден.")
        raise
    except gspread.exceptions.SpreadsheetNotFound:
        print(f"Ошибка: Таблица с именем '{GOOGLE_SHEET_NAME}' не найдена.")
        print("Убедитесь, что имя в .env файле указано ВЕРНО (с учетом регистра и пробелов) и у сервисного аккаунта есть ДОСТУП к этой таблице.")
        raise
    except gspread.exceptions.WorksheetNotFound:
         print(f"Ошибка: Лист с именем '{worksheet_name}' не найден в таблице '{GOOGLE_SHEET_NAME}'.")
         print(f"Убедитесь, что в вашей таблице существует лист с точным именем '{worksheet_name}'.")
         raise
    except gspread.exceptions.APIError as e:
        print(f"Ошибка API Google Sheets: {e}")
        print("Возможные причины: проблемы с разрешениями сервисного аккаунта, превышены квоты API, неверные учетные данные.")
        raise
    except Exception as e:
        print(f"Не удалось подключиться к Google Sheets: {e}")
        raise


def generate_request_id():
    """Генерирует уникальный ID для заявки."""
    return str(uuid.uuid4())[:8] # Короткий UUID

async def add_new_request(data):
    """Добавляет новую заявку в таблицу."""
    if not sheet:
        print("Ошибка: Google Sheet не инициализирован.")
        return None, "Ошибка сервера: Не удалось подключиться к таблице."
    try:
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        request_id = generate_request_id()
        row_data = [
            request_id,
            timestamp,
            data.get('client_id'),
            data.get('client_username', ''),
            data.get('service_type', ''),
            data.get('description', ''),
            data.get('photo_id', ''),
            data.get('quantity', ''),
            data.get('estimated_cost', ''),
            data.get('date', ''),
            data.get('time', ''),
            data.get('address', ''),
            'New', # Status
            '', # Master ID
            '', # Master Username
            '', # Timestamp Assigned
            '', # Timestamp Completed
            '', # Amount Received
            '', # Service Commission
            ''  # Master Feedback
        ]
        sheet.append_row(row_data)
        print(f"Добавлена новая заявка: ID {request_id}")
        return request_id, None # Возвращаем ID и отсутствие ошибки
    except Exception as e:
        print(f"Ошибка при добавлении заявки в Google Sheets: {e}")
        return None, f"Ошибка сервера: Не удалось сохранить заявку ({e})."

async def find_request_row(request_id):
    """Находит строку по Request ID."""
    if not sheet: return None
    try:
        cell = sheet.find(request_id, in_column=1) # Ищем в первом столбце (Request ID)
        if cell:
            return cell.row
        return None
    except gspread.exceptions.CellNotFound:
        return None
    except Exception as e:
        print(f"Ошибка при поиске строки {request_id}: {e}")
        return None

async def update_request_status(request_id, new_status, master_id=None, master_username=None):
    """Обновляет статус заявки и, опционально, назначает мастера."""
    if not sheet: return False, "Ошибка: Google Sheet не инициализирован."
    try:
        row_index = await find_request_row(request_id)
        if not row_index:
            return False, f"Заявка с ID {request_id} не найдена."

        sheet.update_cell(row_index, 13, new_status) # 13 - столбец Status
        if new_status == 'Assigned' and master_id and master_username:
            timestamp_assigned = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            sheet.update_cell(row_index, 14, str(master_id))       # Master ID
            sheet.update_cell(row_index, 15, master_username) # Master Username
            sheet.update_cell(row_index, 16, timestamp_assigned) # Timestamp Assigned
            print(f"Заявка {request_id} назначена мастеру {master_username} ({master_id})")
        elif new_status == 'Completed':
             timestamp_completed = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
             sheet.update_cell(row_index, 17, timestamp_completed) # Timestamp Completed
             print(f"Заявка {request_id} отмечена как выполненная.")
        else:
            print(f"Статус заявки {request_id} обновлен на {new_status}")

        return True, f"Статус заявки {request_id} обновлен на {new_status}."
    except Exception as e:
        print(f"Ошибка при обновлении статуса заявки {request_id}: {e}")
        return False, f"Ошибка сервера при обновлении статуса: {e}"

async def record_completion_details(request_id, amount_received_str, master_feedback=''):
    """Записывает детали выполнения: сумму, комиссию, отзыв мастера."""
    if not sheet: return False, "Ошибка: Google Sheet не инициализирован."
    try:
        row_index = await find_request_row(request_id)
        if not row_index:
            return False, f"Заявка с ID {request_id} не найдена."

        # Валидация и расчеты
        try:
            amount_received = float(amount_received_str.replace(',', '.')) # Обработка запятой как разделителя
            if amount_received < 0:
                return False, "Сумма не может быть отрицательной."
        except ValueError:
            return False, "Неверный формат суммы. Введите число (например, 1500 или 1500.50)."

        commission = round((amount_received * SERVICE_COMMISSION_PERCENT) / 100, 2)

        # Обновляем ячейки
        sheet.update_cell(row_index, 18, str(amount_received).replace('.', ',')) # Amount Received (записываем с запятой для единообразия в таблице)
        sheet.update_cell(row_index, 19, str(commission).replace('.', ','))     # Service Commission
        sheet.update_cell(row_index, 20, master_feedback)             # Master Feedback
        # Также обновляем статус на Completed, если еще не обновлен
        current_status = sheet.cell(row_index, 13).value
        if current_status != 'Completed':
             await update_request_status(request_id, 'Completed') # Обновит и время выполнения

        print(f"Заявка {request_id}: Записана сумма {amount_received}, комиссия {commission}, отзыв '{master_feedback[:20]}...'")
        return True, f"Данные о выполнении заявки {request_id} успешно записаны."

    except Exception as e:
        print(f"Ошибка при записи деталей выполнения заявки {request_id}: {e}")
        return False, f"Ошибка сервера при записи деталей: {e}"

async def get_request_details(request_id):
     """Получает детали заявки по ID."""
     if not sheet: return None
     try:
        row_index = await find_request_row(request_id)
        if not row_index:
            return None
        # Получаем всю строку
        row_data = sheet.row_values(row_index)
        # Преобразуем в словарь для удобства
        headers = sheet.row_values(1)
        request_info = dict(zip(headers, row_data))
        return request_info
     except Exception as e:
        print(f"Ошибка при получении деталей заявки {request_id}: {e}")
        return None

async def get_all_requests_data():
    """Получает все данные из таблицы для отчетов."""
    if not sheet: return []
    try:
        return sheet.get_all_records() # Возвращает список словарей
    except Exception as e:
        print(f"Ошибка при получении всех заявок: {e}")
        return []

async def get_client_id_for_request(request_id):
    """Получает Client ID для указанной заявки."""
    details = await get_request_details(request_id)
    return details.get('Client ID') if details else None

async def get_master_id_for_request(request_id):
    """Получает Master ID для указанной заявки."""
    details = await get_request_details(request_id)
    master_id_str = details.get('Master ID') if details else None
    try:
        return int(master_id_str) if master_id_str else None
    except (ValueError, TypeError):
        return None

# Инициализация при загрузке модуля
try:
    init_gspread()
except Exception as e:
    print(f"Критическая ошибка инициализации Google Sheets: {e}")
    # В реальном приложении здесь может быть логика остановки бота или повторных попыток

