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


# ==================== ГЛАВНОЕ МЕНЮ ====================

def get_main_menu_keyboard(is_shift_open: bool = False) -> InlineKeyboardMarkup:
    """
    Получить главное меню бота с кнопками управления.
    
    Содержит разные кнопки в зависимости от того, открыта ли смена:
    - Если смена открыта: добавить кальян, просмотр текущих кальянов, закрыть смену
    - Если смена закрыта: открыть смену
    - Всегда: история смен
    
    Args:
        is_shift_open (bool): Статус смены (True - открыта, False - закрыта)
        
    Returns:
        InlineKeyboardMarkup: Объект с кнопками главного меню
    """
    buttons = []
    
    # Кнопки отличаются в зависимости от статуса смены
    if is_shift_open:
        # Смена открыта - показываем кнопки для работы с кальянами
        buttons.append([InlineKeyboardButton(text="➕ Добавить кальян", callback_data="add_hookah")])
        buttons.append([InlineKeyboardButton(text="📋 Текущие кальяны", callback_data="current_hookahs")])
        # Вступить в смену / взять менеджера
        buttons.append([InlineKeyboardButton(text="👥 Вступить в смену", callback_data="join_shift")])
        buttons.append([InlineKeyboardButton(text="👤 Взять менеджера", callback_data="take_manager")])
        buttons.append([InlineKeyboardButton(text="🔒 Закрыть смену", callback_data="close_shift")])
    else:
        # Смена закрыта - показываем кнопку для открытия
        buttons.append([InlineKeyboardButton(text="🔓 Открыть смену", callback_data="open_shift")])
    
    # История смен доступна всегда
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

def get_hookah_actions_keyboard(hookah_id: int) -> InlineKeyboardMarkup:
    """
    Получить клавиатуру с действиями для конкретного кальяна.
    
    Показывает кнопки для редактирования типа, стола, удаления кальяна
    и возврата к списку.
    
    Args:
        hookah_id (int): ID кальяна для редактирования
        
    Returns:
        InlineKeyboardMarkup: Кнопки с доступными действиями
    """
    buttons = [
        [InlineKeyboardButton(
            text="✏️ Изменить тип",
            callback_data=f"edit_type_{hookah_id}"
        )],
        [InlineKeyboardButton(
            text="📍 Изменить стол",
            callback_data=f"edit_table_{hookah_id}"
        )],
        [InlineKeyboardButton(
            text="🗑️ Удалить",
            callback_data=f"delete_{hookah_id}"
        )],
        [InlineKeyboardButton(
            text="⬅️ Назад к списку",
            callback_data="back_to_hookahs"
        )]
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