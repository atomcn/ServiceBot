from aiogram import types, Dispatcher
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters import CommandStart, CommandHelp

from config import ADMIN_ID, MASTER_IDS
from keyboards.inline import get_service_keyboard # Импортируем клавиатуру выбора услуг
from states.client_states import ClientForm # Импортируем состояние клиента

async def cmd_start(message: types.Message, state: FSMContext):
    """Обработчик команды /start"""
    await state.finish() # Завершаем любое предыдущее состояние
    user_id = message.from_user.id
    full_name = message.from_user.full_name

    if user_id == ADMIN_ID:
        admin_start_text = (
            f"👑 Добро пожаловать, Администратор {full_name}!\n\n"
            "Вам доступны все функции бота:\n\n"
            "🔹 **Команды Администратора:**\n"
            "   /requests - Просмотр последних заявок\n"
            "   /stats - Статистика доходов и комиссии\n"
            "   /masters - Список зарегистрированных мастеров\n\n"
            "🔸 **Действия Мастера (доступны вам):**\n"
            "   Вы можете нажимать кнопки '✅ Принять заявку' и '🏁 Работа выполнена' в уведомлениях о заявках. "
            "При выполнении этих действий будет записан *ваш* ID администратора.\n\n"
            "▪️ **Клиентский Сценарий:**\n"
            "   Команда /start для *обычных пользователей* запускает процесс создания новой заявки (выбор услуги, описание и т.д.).\n\n"
            "▫️ **Общие Команды:**\n"
            "   /start - Перезапустить бота (сброс состояния)\n"
            "   /help - Показать справочное сообщение"
        )
        await message.answer(admin_start_text, parse_mode='Markdown')
    elif user_id in MASTER_IDS:
        await message.answer(f"Добро пожаловать, Мастер {full_name}!\n"
                             f"Вы будете получать уведомления о новых заявках.\n"
                             f"После выполнения работы используйте кнопку в уведомлении или команду /complete ID_заявки (TODO)")
    else: # Обычный клиент
        await message.answer(f"Здравствуйте, {full_name}!\n"
                             f"Я помогу вам найти мастера для решения бытовых задач.\n"
                             f"Выберите тип услуги, чтобы начать:", reply_markup=get_service_keyboard())
        # Переводим клиента в состояние выбора услуги
        await ClientForm.choosing_service.set()
        # Сохраняем ID и username клиента в состоянии для последующего использования
        await state.update_data(client_id=user_id)
        await state.update_data(client_username=message.from_user.username or "N/A")


async def cmd_help(message: types.Message):
    """Обработчик команды /help"""
    user_id = message.from_user.id
    help_text = "Общие команды:\n" \
                "/start - Начать работу с ботом\n" \
                "/help - Показать это сообщение\n\n"

    if user_id == ADMIN_ID:
        help_text += "Команды Администратора:\n" \
                     "/requests - Просмотр заявок\n" \
                     "/stats - Статистика\n\n"
    elif user_id in MASTER_IDS:
        help_text += "Команды Мастера:\n" \
                     "Ожидайте уведомлений о новых заявках.\n" \
                     "Кнопка 'Работа выполнена' появится после принятия заявки (TODO: или команда /complete ID).\n\n" # TODO: Реализовать команду
    else:
        help_text += "Для Клиентов:\n" \
                     "Нажмите /start, чтобы создать новую заявку.\n" \
                     "Следуйте инструкциям бота для оформления."

    await message.answer(help_text)

# --- Регистрация хэндлеров ---
def register_handlers_common(dp: Dispatcher):
    dp.register_message_handler(cmd_start, CommandStart(), state="*")
    dp.register_message_handler(cmd_help, CommandHelp(), state="*")