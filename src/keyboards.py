"""
Keyboards module for Hookah Shift Management Bot

Модуль для создания inline-клавиатур в Telegram боте.
Содержит функции для генерации кнопок для различных этапов работы бота.

Inline-кнопки - это кнопки, которые появляются прямо под сообщением и отправляют
callback события при нажатии, вместо того чтобы отправлять текстовые команды.

Author: Hookah Bot Team
License: MIT
"""

from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

# ==================== КОНСТАНТЫ ====================

# Список всех доступных столов в кальянной
TABLES = [
    "1", "2", "3", "4", "5", "6", "7",  # Столы 1-7
    "Большой бар",                       # Большая барная стойка
    "Малый бар",                         # Малая барная стойка
    "Стол у танцпола"                    # Стол возле танцпола
]

# Типы кальянов
HOOKAH_TYPES = ["Стандарт", "Сигара"]

# Уровни силы кальяна
STRENGTH_LEVELS = list(range(1, 11))

# Варианты ледяной/тепловой подачи
COLDNESS_OPTIONS = ["Холодный", "Средний", "Теплый"]


# ==================== ГЛАВНОЕ МЕНЮ ====================

def get_main_menu_keyboard(is_shift_open: bool = False, is_admin: bool = False) -> InlineKeyboardMarkup:
    """Получить главное меню бота с кнопками управления."""
    buttons = []
    if is_shift_open:
        buttons.append([InlineKeyboardButton(text="➕ Добавить кальян", callback_data="add_hookah")])
        buttons.append([InlineKeyboardButton(text="📋 Текущие кальяны", callback_data="current_hookahs")])
        buttons.append([InlineKeyboardButton(text="👥 Вступить в смену", callback_data="join_shift")])
        buttons.append([InlineKeyboardButton(text="⚙️ Профиль", callback_data="profile")])
        if is_admin:
            buttons.append([InlineKeyboardButton(text="🛠️ Админка", callback_data="admin_panel")])
        buttons.append([InlineKeyboardButton(text="🔒 Закрыть смену", callback_data="close_shift")])
    else:
        buttons.append([InlineKeyboardButton(text="🔓 Открыть смену", callback_data="open_shift")])
        buttons.append([InlineKeyboardButton(text="⚙️ Профиль", callback_data="profile")])
        if is_admin:
            buttons.append([InlineKeyboardButton(text="🛠️ Админка", callback_data="admin_panel")])
    buttons.append([InlineKeyboardButton(text="📊 История смен", callback_data="history")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


# ==================== ВЫБОР ТИПА И СТОЛА ====================

def get_hookah_type_keyboard() -> InlineKeyboardMarkup:
    """
    Получить клавиатуру для выбора типа кальяна.
    
    Показывает два варианта: Стандарт и Сигара
    Используется при добавлении нового кальяна.
    
    Returns:
        InlineKeyboardMarkup: Кнопки для выбора типа кальяна
    """
    buttons = [
        [InlineKeyboardButton(text="🌿 Стандарт", callback_data="type_Стандарт")],
        [InlineKeyboardButton(text="🚬 Сигара", callback_data="type_Сигара")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def get_tables_keyboard() -> InlineKeyboardMarkup:
    """
    Получить клавиатуру для выбора стола.
    
    Выводит кнопки для всех столов, расположенные в две колонки.
    Используется при добавлении кальяна и редактировании.
    
    Макет:
        [Стол 1]  [Стол 2]
        [Стол 3]  [Стол 4]
        [Стол 5]  [Стол 6]
        [Стол 7]  [Большой бар]
        [Малый бар]  [Стол у танцпола]
    
    Returns:
        InlineKeyboardMarkup: Кнопки для выбора стола
    """
    buttons = []
    
    # Создаем две кнопки в ряду
    for i in range(0, len(TABLES), 2):
        row = []
        
        # Первая кнопка в ряду
        row.append(InlineKeyboardButton(
            text=TABLES[i],
            callback_data=f"table_{TABLES[i]}"
        ))
        
        # Вторая кнопка в ряду (если существует)
        if i + 1 < len(TABLES):
            row.append(InlineKeyboardButton(
                text=TABLES[i + 1],
                callback_data=f"table_{TABLES[i + 1]}"
            ))
        
        buttons.append(row)
    
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def get_strength_keyboard() -> InlineKeyboardMarkup:
    """Получить клавиатуру выбора силы кальяна от 1 до 10."""
    buttons = []
    for i in range(0, len(STRENGTH_LEVELS), 2):
        row = [InlineKeyboardButton(text=str(STRENGTH_LEVELS[i]), callback_data=f"strength_{STRENGTH_LEVELS[i]}")]
        if i + 1 < len(STRENGTH_LEVELS):
            row.append(InlineKeyboardButton(text=str(STRENGTH_LEVELS[i + 1]), callback_data=f"strength_{STRENGTH_LEVELS[i + 1]}"))
        buttons.append(row)
    buttons.append([InlineKeyboardButton(text="⬅️ Назад в меню", callback_data="back_to_menu")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def get_coldness_keyboard() -> InlineKeyboardMarkup:
    """Получить клавиатуру выбора степени холодности кальяна."""
    buttons = [[InlineKeyboardButton(text=option, callback_data=f"coldness_{option}")] for option in COLDNESS_OPTIONS]
    buttons.append([InlineKeyboardButton(text="⬅️ Назад в меню", callback_data="back_to_menu")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


# ==================== ПРОСМОТР КАЛЬЯНОВ ====================

def get_hookahs_list_keyboard(hookahs: list, shift_id: int) -> InlineKeyboardMarkup:
    """
    Получить клавиатуру со списком всех кальянов за смену.
    
    Каждый кальян выводится отдельной кнопкой с информацией:
    [Стол] - [Тип] ([Время])
    
    Args:
        hookahs (list): Список кортежей с данными кальянов
        shift_id (int): ID смены (используется для контекста)
        
    Returns:
        InlineKeyboardMarkup: Кнопки со списком кальянов
        
    Структура каждого кортежа в hookahs:
        (id, shift_id, hookah_type, table_name, created_at)
    """
    buttons = []
    
    # Добавляем кнопку для каждого кальяна
    for hookah in hookahs:
        # Извлекаем время из datetime (формат: YYYY-MM-DD HH:MM:SS)
        # Берем только HH:MM:SS часть
        time = hookah[4][11:] if len(hookah[4]) > 11 else hookah[4]
        
        # Форматируем текст кнопки: [Стол] - [Тип] ([Время])
        btn_text = f"{hookah[3]} - {hookah[2]} ({time})"
        
        # Callback data для просмотра деталей кальяна
        buttons.append([InlineKeyboardButton(
            text=btn_text,
            callback_data=f"view_{hookah[0]}"
        )])
    
    # Кнопка для возврата в главное меню
    buttons.append([InlineKeyboardButton(
        text="⬅️ Назад в меню",
        callback_data="back_to_menu"
    )])
    
    return InlineKeyboardMarkup(inline_keyboard=buttons)


# ==================== ДЕЙСТВИЯ С КАЛЬЯНОМ ====================

def get_hookah_actions_keyboard(hookah: tuple, role: str) -> InlineKeyboardMarkup:
    """Получить клавиатуру с действиями для конкретного кальяна, в зависимости от роли."""
    hookah_id = hookah[0]
    status = hookah[5] if len(hookah) > 5 else 'new_order'
    buttons = []
    if role in ('admin', 'hookah_master'):
        if status == 'new_order':
            buttons.append([InlineKeyboardButton(text="✅ Принять кальян", callback_data=f"accept_{hookah_id}")])
        elif status == 'in_packing':
            buttons.append([InlineKeyboardButton(text="🎯 Пометить готовым", callback_data=f"ready_{hookah_id}")])
    if role in ('admin', 'manager'):
        buttons.append([InlineKeyboardButton(text="✏️ Изменить тип", callback_data=f"edit_type_{hookah_id}")])
        buttons.append([InlineKeyboardButton(text="📍 Изменить стол", callback_data=f"edit_table_{hookah_id}")])
        buttons.append([InlineKeyboardButton(text="🗑️ Удалить", callback_data=f"delete_{hookah_id}")])
    buttons.append([InlineKeyboardButton(text="⬅️ Назад к списку", callback_data="back_to_hookahs")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def get_profile_keyboard(notifications_enabled: bool, is_admin: bool = False) -> InlineKeyboardMarkup:
    """Получить клавиатуру профиля пользователя с уведомлениями."""
    buttons = [
        [InlineKeyboardButton(
            text=f"🔔 Уведомления: {'Вкл' if notifications_enabled else 'Выкл'}",
            callback_data="toggle_notifications"
        )]
    ]
    if is_admin:
        buttons.append([InlineKeyboardButton(text="🛠️ Админка", callback_data="admin_panel")])
    buttons.append([InlineKeyboardButton(text="⬅️ Назад в меню", callback_data="back_to_menu")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def get_admin_menu_keyboard() -> InlineKeyboardMarkup:
    """Получить клавиатуру админской панели."""
    buttons = [
        [InlineKeyboardButton(text="👥 Назначить роль", callback_data="assign_role_help")],
        [InlineKeyboardButton(text="📅 Расписание работы", callback_data="admin_schedule")],
        [InlineKeyboardButton(text="❌ Удалить текущую смену", callback_data="admin_delete_shift")],
        [InlineKeyboardButton(text="⬅️ Назад в меню", callback_data="back_to_menu")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)


# ==================== ИСТОРИЯ СМЕН ====================

def get_history_keyboard(shifts: list) -> InlineKeyboardMarkup:
    """
    Получить клавиатуру с историей всех смен.
    
    Каждая смена выводится отдельной кнопкой с информацией:
    [Дата] - [Количество кальянов]
    
    Args:
        shifts (list): Список кортежей с данными смен
        
    Returns:
        InlineKeyboardMarkup: Кнопки с историей смен
        
    Структура каждого кортежа в shifts:
        (id, open_time, close_time, is_open, total_hookahs)
    """
    buttons = []
    
    # Добавляем кнопку для каждой смены
    for shift in shifts:
        # Извлекаем дату из datetime (первые 10 символов: YYYY-MM-DD)
        date = shift[1][:10] if shift[1] else "?"
        
        # Получаем количество кальянов за смену
        total = shift[4] if shift[4] else 0
        
        # Форматируем текст кнопки: [Дата] - [Количество] кальянов
        btn_text = f"📅 {date} - {total} кальянов"
        
        # Callback data для просмотра деталей смены
        buttons.append([InlineKeyboardButton(
            text=btn_text,
            callback_data=f"shift_{shift[0]}"
        )])
    
    # Кнопка для возврата в главное меню
    buttons.append([InlineKeyboardButton(
        text="⬅️ Назад в меню",
        callback_data="back_to_menu"
    )])
    
    return InlineKeyboardMarkup(inline_keyboard=buttons)


# ==================== ПОДТВЕРЖДЕНИЯ ====================

def get_confirm_close_keyboard() -> InlineKeyboardMarkup:
    """
    Получить клавиатуру подтверждения закрытия смены.
    
    Выводит кнопки для подтверждения или отмены операции закрытия смены.
    Нужна для предотвращения случайного закрытия.
    
    Returns:
        InlineKeyboardMarkup: Кнопки подтверждения
    """
    buttons = [
        [InlineKeyboardButton(
            text="✅ Да, закрыть смену",
            callback_data="confirm_close"
        )],
        [InlineKeyboardButton(
            text="❌ Отмена",
            callback_data="back_to_menu"
        )]
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)