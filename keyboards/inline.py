from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.callback_data import CallbackData
from config import AVAILABLE_SERVICES

# --- CallbackData ---
service_cb = CallbackData("service", "id", "name") # Выбор услуги
photo_action_cb = CallbackData("photo_act", "action") # Действия с фото (пропустить/добавить)
request_action_cb = CallbackData("req_act", "action", "req_id") # Действия с заявкой (принять, выполнено)
confirm_cb = CallbackData("confirm", "action", "req_id") # Подтверждение админом/мастером (если нужно)
admin_action_cb = CallbackData("admin_act", "action", "req_id", "user_id") # Действия админа (связаться)

# --- Client Keyboards ---
def get_service_keyboard():
    keyboard = InlineKeyboardMarkup(row_width=2)
    for key, value in AVAILABLE_SERVICES.items():
        keyboard.insert(InlineKeyboardButton(text=value, callback_data=service_cb.new(id=key, name=value)))
    return keyboard

def get_photo_choice_keyboard():
    keyboard = InlineKeyboardMarkup(row_width=2)
    keyboard.add(
        InlineKeyboardButton("Пропустить фото", callback_data=photo_action_cb.new(action="skip")),
        # InlineKeyboardButton("Добавить фото", callback_data=photo_action_cb.new(action="add")) # Кнопка "добавить" обычно не нужна, т.к. юзер просто шлет фото
    )
    return keyboard

# --- Master Keyboards ---
def get_master_new_request_keyboard(request_id: str):
    keyboard = InlineKeyboardMarkup()
    keyboard.add(InlineKeyboardButton("✅ Принять заявку", callback_data=request_action_cb.new(action="accept", req_id=request_id)))
    # Можно добавить кнопку "Отклонить", если нужно
    # keyboard.add(InlineKeyboardButton("❌ Отклонить", callback_data=request_action_cb.new(action="reject", req_id=request_id)))
    return keyboard

def get_master_complete_request_keyboard(request_id: str):
     # Эта кнопка может быть в сообщении мастеру после принятия заявки или как команда /complete <request_id>
    keyboard = InlineKeyboardMarkup()
    keyboard.add(InlineKeyboardButton("🏁 Работа выполнена", callback_data=request_action_cb.new(action="complete", req_id=request_id)))
    return keyboard

def get_master_skip_feedback_keyboard():
    keyboard = InlineKeyboardMarkup()
    keyboard.add(InlineKeyboardButton("Пропустить отзыв", callback_data="skip_feedback"))
    return keyboard


# --- Admin Keyboards ---
def get_admin_master_report_keyboard(request_id: str, master_id: int):
     keyboard = InlineKeyboardMarkup(row_width=2)
     # Добавляем кнопку для связи с мастером
     keyboard.add(InlineKeyboardButton(f"💬 Связаться с мастером", url=f"tg://user?id={master_id}"))
     # Можно добавить кнопку для просмотра деталей заявки в боте или в таблице
     # keyboard.add(InlineKeyboardButton(f"📄 Детали заявки {request_id}", callback_data=admin_action_cb.new(action="view_req", req_id=request_id, user_id="")))
     # keyboard.add(InlineKeyboardButton(f"📊 Открыть таблицу", url=f"https://docs.google.com/spreadsheets/d/{GOOGLE_SHEET_ID}/edit")) # Нужен GOOGLE_SHEET_ID из config
     return keyboard