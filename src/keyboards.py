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

# Уровни крепости кальяна
STRENGTH_LEVELS = list(range(1, 11))

# Варианты холодка
COLDNESS_OPTIONS = ["Без холодка", "Чуть-чуть", "Холодный", "Чистая Супернова"]


# ==================== ГЛАВНОЕ МЕНЮ ====================

def get_main_menu_keyboard(is_admin: bool = False) -> InlineKeyboardMarkup:
    """
    Получить главное меню бота с опциями:
    - Смена (управление текущей сменой)
    - Предыдущие смены (история)
    - Профиль (профиль пользователя)
    - Админ панель (только для админов)
    """
    buttons = [
        [InlineKeyboardButton(text="💼 Смена", callback_data="shift_management")],
        [InlineKeyboardButton(text="📋 Предыдущие смены", callback_data="history")],
        [InlineKeyboardButton(text="👤 Профиль", callback_data="profile")]
    ]
    if is_admin:
        buttons.append([InlineKeyboardButton(text="⚙️ Админ панель", callback_data="admin_panel")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


# ==================== УПРАВЛЕНИЕ СМЕНОЙ ====================

def get_shift_management_keyboard(
    is_shift_open: bool = False, 
    is_admin: bool = False,
    is_user_in_shift: bool = False,
    is_manager: bool = False
) -> InlineKeyboardMarkup:
    """
    Получить клавиатуру для управления сменой.
    
    Args:
        is_shift_open: Открыта ли смена
        is_admin: Админ ли пользователь
        is_user_in_shift: Находится ли пользователь в смене
        is_manager: Менеджер ли пользователь
    """
    buttons = []
    if is_shift_open:
        buttons.append([InlineKeyboardButton(text="➕ Добавить кальян", callback_data="add_hookah")])
        if is_manager:
            buttons.append([InlineKeyboardButton(text="📋 Текущие кальяны (редактировать)", callback_data="current_hookahs")])
        if not is_user_in_shift:
            buttons.append([InlineKeyboardButton(text="👥 Вступить в смену", callback_data="join_shift")])
        if is_admin:
            buttons.append([InlineKeyboardButton(text="🔒 Закрыть смену", callback_data="close_shift")])
    else:
        if is_admin:
            buttons.append([InlineKeyboardButton(text="🔓 Открыть смену", callback_data="open_shift")])
    buttons.append([InlineKeyboardButton(text="⬅️ Назад в меню", callback_data="back_to_main_menu")])
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
        buttons.append([InlineKeyboardButton(text="✏️ Изменить крепость", callback_data=f"edit_strength_{hookah_id}")])
        buttons.append([InlineKeyboardButton(text="❄️ Изменить холодность", callback_data=f"edit_coldness_{hookah_id}")])
        buttons.append([InlineKeyboardButton(text="💬 Изменить комментарий", callback_data=f"edit_comment_{hookah_id}")])
        buttons.append([InlineKeyboardButton(text="�🗑️ Удалить", callback_data=f"delete_{hookah_id}")])
    buttons.append([InlineKeyboardButton(text="⬅️ Назад к списку", callback_data="back_to_hookahs")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def get_profile_keyboard() -> InlineKeyboardMarkup:
    """Получить клавиатуру профиля пользователя."""
    buttons = [
        [InlineKeyboardButton(text="📊 Статистика", callback_data="profile_stats")],
        [InlineKeyboardButton(text="⬅️ Назад в меню", callback_data="back_to_main_menu")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def get_admin_menu_keyboard() -> InlineKeyboardMarkup:
    """Получить клавиатуру админской панели."""
    buttons = [
        [InlineKeyboardButton(text="👥 Участники", callback_data="admin_members")],
        [InlineKeyboardButton(text="📋 Смены", callback_data="admin_shifts")],
        [InlineKeyboardButton(text="👤 Пользователи", callback_data="admin_users")],
        [InlineKeyboardButton(text="⬅️ Назад в меню", callback_data="back_to_main_menu")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def get_admin_users_keyboard(users: list) -> InlineKeyboardMarkup:
    """Получить клавиатуру со списком пользователей для назначения роли."""
    buttons = []
    for user_id, username, display_name, global_role in users:
        name = display_name or username or f"User {user_id}"
        buttons.append([InlineKeyboardButton(
            text=f"{name} ({global_role})",
            callback_data=f"admin_user_{user_id}"
        )])
    buttons.append([InlineKeyboardButton(text="⬅️ Назад", callback_data="admin_panel")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def get_admin_user_role_keyboard(user_id: int, current_role: str) -> InlineKeyboardMarkup:
    """Получить клавиатуру для выбора глобальной роли пользователя."""
    roles = ["member", "manager", "hookah_master", "supervisor"]
    buttons = []
    for role in roles:
        label = role.replace("_", " ").title()
        selected = " ✅" if role == current_role else ""
        buttons.append([InlineKeyboardButton(
            text=f"{label}{selected}",
            callback_data=f"admin_set_role_{user_id}_{role}"
        )])
    buttons.append([InlineKeyboardButton(text="⬅️ Назад", callback_data="admin_users")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def get_admin_user_detail_keyboard(user_id: int) -> InlineKeyboardMarkup:
    """Получить клавиатуру для управления конкретным пользователем."""
    buttons = [
        [InlineKeyboardButton(text="✏️ Изменить имя", callback_data=f"admin_edit_user_name_{user_id}")],
        [InlineKeyboardButton(text="🔧 Изменить роль", callback_data=f"admin_user_role_{user_id}")],
        [InlineKeyboardButton(text="⬅️ Назад", callback_data="admin_users")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def get_admin_shifts_keyboard(shifts: list) -> InlineKeyboardMarkup:
    """Получить клавиатуру со списком смен для админ-редактирования."""
    buttons = []
    for shift_id, open_time, close_time, is_open, total_hookahs in shifts:
        status = "Открыта" if is_open else "Закрыта"
        label = open_time[:10] if open_time else "?"
        buttons.append([InlineKeyboardButton(
            text=f"#{shift_id} {label} ({status})",
            callback_data=f"admin_shift_{shift_id}"
        )])
    buttons.append([InlineKeyboardButton(text="⬅️ Назад", callback_data="admin_panel")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def get_admin_shift_detail_keyboard(shift: tuple, is_admin: bool = False) -> InlineKeyboardMarkup:
    """Получить клавиатуру для просмотра и управления сменой."""
    shift_id, open_time, close_time, is_open, total_hookahs = shift
    buttons = []
    buttons.append([InlineKeyboardButton(text="✏️ Редактировать время", callback_data=f"edit_shift_{shift_id}")])
    buttons.append([InlineKeyboardButton(text="🍃 Изменить кальяны", callback_data=f"admin_shift_hookahs_{shift_id}")])
    buttons.append([InlineKeyboardButton(text="👥 Изменить участников", callback_data=f"admin_shift_members_{shift_id}")])
    if is_open:
        buttons.append([InlineKeyboardButton(text="🔒 Закрыть смену", callback_data=f"admin_close_shift_{shift_id}")])
    else:
        buttons.append([InlineKeyboardButton(text="🔓 Переоткрыть смену", callback_data=f"reopen_shift_{shift_id}")])
    buttons.append([InlineKeyboardButton(text="🗑️ Удалить смену", callback_data=f"admin_delete_shift_{shift_id}")])
    buttons.append([InlineKeyboardButton(text="⬅️ Назад", callback_data="admin_shifts")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def get_edit_shift_time_keyboard(shift_id: int) -> InlineKeyboardMarkup:
    """Получить клавиатуру для выбора, что редактировать в смене."""
    buttons = [
        [InlineKeyboardButton(text="🕐 Время открытия", callback_data=f"edit_shift_open_time_{shift_id}")],
        [InlineKeyboardButton(text="🕑 Время закрытия", callback_data=f"edit_shift_close_time_{shift_id}")],
        [InlineKeyboardButton(text="⬅️ Отмена", callback_data=f"admin_shift_{shift_id}")]
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