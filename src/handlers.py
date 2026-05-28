"""
Handlers module for Hookah Shift Management Bot

Модуль для обработки команд и callback событий от пользователей.
Использует FSM (Finite State Machine) для управления состояниями диалога.

Основные компоненты:
- Router: маршрутизатор для регистрации обработчиков
- FSM States: состояния для многошагового диалога
- Callback handlers: обработчики inline кнопок

Author: Hookah Bot Team
License: MIT
"""

import logging
from datetime import datetime
from os import getenv

from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.filters import Command

import src.database as db
from src.keyboards import (
    get_main_menu_keyboard,
    get_hookah_type_keyboard,
    get_tables_keyboard,
    get_strength_keyboard,
    get_coldness_keyboard,
    get_hookahs_list_keyboard,
    get_hookah_actions_keyboard,
    get_history_keyboard,
    get_profile_keyboard,
    get_admin_menu_keyboard,
    get_confirm_close_keyboard
)

# Настройка логирования для этого модуля
logger = logging.getLogger(__name__)

# Главный маршрутизатор для регистрации всех обработчиков
router = Router()

BOT_OWNER_ID = int(getenv("ADMIN_USER_ID", "0") or 0)
ROLE_LABELS = {
    'admin': 'Админ',
    'manager': 'Менеджер',
    'hookah_master': 'Кальянный мастер',
    'supervisor': 'Управляющий',
    'member': 'Участник смены'
}
STATUS_LABELS = {
    'new_order': 'Новый заказ',
    'in_packing': 'В работе',
    'ready_for_guest': 'Готов к выдаче'
}


def is_admin(user_id: int) -> bool:
    return BOT_OWNER_ID != 0 and user_id == BOT_OWNER_ID


def get_user_role(shift_id: int, user_id: int) -> str:
    if is_admin(user_id):
        return 'admin'
    return db.get_shift_user_role(shift_id, user_id)


def user_has_access(shift_id: int, user_id: int) -> bool:
    role = get_user_role(shift_id, user_id)
    return role in ('admin', 'manager', 'hookah_master', 'supervisor', 'member')


def can_edit_hookah(role: str) -> bool:
    return role in ('admin', 'manager')


def can_add_hookah(role: str) -> bool:
    return role in ('admin', 'hookah_master')


def can_control_hookah(role: str) -> bool:
    return role in ('admin', 'hookah_master')


def is_manager_or_admin(role: str) -> bool:
    return role in ('admin', 'manager')


def get_work_schedule_text() -> str:
    weekday = datetime.now().weekday()
    if weekday in (4, 5):
        today_text = "Пятница/Суббота"
        expected = "Менеджер + 2 кальянных мастера"
    else:
        today_text = "Воскресенье-Четверг"
        expected = "Менеджер + 1 кальянный мастер"

    return (
        "📅 Расписание работы:\n"
        "Воскресенье — Четверг: Менеджер + 1 кальянный мастер\n"
        "Пятница — Суббота: Менеджер + 2 кальянных мастера\n\n"
        f"Сегодня: {today_text}\n"
        f"Ожидаемая команда: {expected}"
    )


async def notify_new_hookah(bot, hookah_id: int, hookah_type: str, table_name: str, shift_id: int) -> None:
    message = (
        f"📣 Новый кальян #{hookah_id}\n"
        f"🌿 Тип: {hookah_type}\n"
        f"📍 Стол: {table_name}\n"
        "Статус: Новый заказ\n"
        "Пожалуйста, подтвердите или начните работу." 
    )
    for user_id in db.get_users_with_notifications_enabled():
        try:
            await bot.send_message(user_id, message)
        except Exception:
            continue


# ==================== FSM STATES (Состояния диалога) ====================

class AddHookah(StatesGroup):
    """Состояния для добавления нового кальяна"""
    waiting_type = State()   # Ожидание выбора типа кальяна
    waiting_table = State()  # Ожидание выбора стола
    waiting_strength = State()  # Ожидание выбора силы кальяна
    waiting_coldness = State()  # Ожидание выбора холодности кальяна
    waiting_comment = State()  # Ожидание комментария к заказу


class EditHookah(StatesGroup):
    """Состояния для редактирования кальяна"""
    waiting_type = State()   # Ожидание выбора нового типа
    waiting_table = State()  # Ожидание выбора нового стола


# ==================== ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ ====================

def get_current_shift():
    """
    Вспомогательная функция для получения текущей открытой смены.
    
    Returns:
        Optional[Tuple]: Данные текущей смены или None
    """
    return db.get_current_shift()


# ==================== КОМАНДЫ ====================

@router.message(Command("start"))
async def cmd_start(message: Message):
    """
    Обработчик команды /start
    
    Отправляет приветственное сообщение и показывает главное меню.
    Проверяет, открыта ли текущая смена и выводит соответствующие кнопки.
    
    Args:
        message (Message): Объект сообщения от пользователя
    """
    shift = get_current_shift()
    is_open = shift is not None
    
    user_id = message.from_user.id
    await message.answer(
        "🍃 Добро пожаловать в бот учета кальянов!\n\n"
        "Это приложение поможет вам вести учет всех кальянов за смену.\n\n"
        "Выберите действие:",
        reply_markup=get_main_menu_keyboard(is_open, is_admin(user_id))
    )


# ==================== УПРАВЛЕНИЕ СМЕНАМИ ====================

@router.callback_query(F.data == "open_shift")
async def cmd_open_shift(callback: CallbackQuery):
    """
    Обработчик открытия новой смены.
    
    Создает новую смену в БД с текущей датой/временем.
    Если смена уже открыта, сообщает об этом пользователю.
    
    Args:
        callback (CallbackQuery): Callback от нажатия кнопки
    """
    shift = get_current_shift()
    
    # Проверка: если смена уже открыта, не открываем новую
    if shift:
        await callback.message.edit_text(
            "⚠️ Смена уже открыта!\n"
            "Сначала закройте текущую смену, чтобы открыть новую."
        )
        await callback.answer()
        return
    
    # Открываем новую смену
    shift_id = db.open_shift()
    
    await callback.message.edit_text(
        f"✅ Смена успешно открыта!\n\n"
        f"🆔 ID смены: {shift_id}\n"
        f"⏰ Время: {datetime.now().strftime('%H:%M:%S')}\n\n"
        "Выберите действие:",
        reply_markup=get_main_menu_keyboard(True, is_admin(callback.from_user.id))
    )
    await callback.answer()
    logger.info(f"Смена #{shift_id} открыта")


@router.callback_query(F.data == "close_shift")
async def cmd_close_shift(callback: CallbackQuery):
    """
    Обработчик начала процесса закрытия смены.
    
    Выводит подтверждение с информацией о количестве кальянов за смену.
    
    Args:
        callback (CallbackQuery): Callback от нажатия кнопки
    """
    shift = get_current_shift()
    
    # Проверка: нет ли открытой смены
    if not shift:
        await callback.message.edit_text(
            "⚠️ Нет открытой смены.\n"
            "Откройте смену перед тем как закрывать."
        )
        await callback.answer()
        return
    
    # Получаем кальяны за текущую смену и подсчитываем
    hookahs = db.get_hookahs_by_shift(shift[0])
    total = len(hookahs)
    
    await callback.message.edit_text(
        f"⚠️ Вы уверены, что хотите закрыть смену?\n\n"
        f"📊 Всего кальянов за смену: {total}\n\n"
        "Эту операцию невозможно отменить!",
        reply_markup=get_confirm_close_keyboard()
    )
    await callback.answer()


@router.callback_query(F.data == "confirm_close")
async def cmd_confirm_close(callback: CallbackQuery):
    """
    Обработчик подтверждения закрытия смены.
    
    Окончательно закрывает смену и выводит итоговую информацию.
    
    Args:
        callback (CallbackQuery): Callback от нажатия кнопки подтверждения
    """
    shift = get_current_shift()
    
    # Проверка: смена должна быть открыта
    if not shift:
        await callback.message.edit_text("⚠️ Смена не найдена.")
        await callback.answer()
        return
    
    # Закрываем смену и подсчитываем кальяны
    db.close_shift(shift[0])
    hookahs = db.get_hookahs_by_shift(shift[0])
    total = len(hookahs)
    
    await callback.message.edit_text(
        f"✅ Смена успешно закрыта!\n\n"
        f"📊 Всего кальянов за смену: {total}\n"
        f"🕐 Время закрытия: {datetime.now().strftime('%H:%M:%S')}\n\n"
        "Выберите действие:",
        reply_markup=get_main_menu_keyboard(False, is_admin(callback.from_user.id))
    )
    await callback.answer()
    logger.info(f"Смена #{shift[0]} закрыта с {total} кальянами")


# ==================== ДОБАВЛЕНИЕ КАЛЬЯНА ====================

@router.callback_query(F.data == "add_hookah")
async def cmd_add_hookah(callback: CallbackQuery, state: FSMContext):
    """
    Обработчик начала процесса добавления кальяна.
    
    Запускает FSM диалог, запрашивая выбор типа кальяна.
    Проверяет, открыта ли смена перед добавлением.
    
    Args:
        callback (CallbackQuery): Callback от нажатия кнопки
        state (FSMContext): Контекст для управления состоянием FSM
    """
    shift = get_current_shift()
    
    # Проверка: смена должна быть открыта
    if not shift:
        await callback.message.edit_text(
            "⚠️ Откройте смену сначала!\n\n"
            "Вы не можете добавлять кальяны если смена не открыта."
        )
        await callback.answer()
        return

    role = get_user_role(shift[0], callback.from_user.id)
    if not can_add_hookah(role):
        await callback.message.edit_text(
            "⛔ У вас нет прав добавлять кальяны. Только кальянный мастер или админ может это делать."
        )
        await callback.answer()
        return
    
    # Начинаем диалог добавления кальяна
    await callback.message.edit_text(
        "🌿 Выберите тип кальяна:",
        reply_markup=get_hookah_type_keyboard()
    )
    await state.set_state(AddHookah.waiting_type)
    await callback.answer()


@router.callback_query(AddHookah.waiting_type, F.data.startswith("type_"))
async def process_hookah_type(callback: CallbackQuery, state: FSMContext):
    """
    Обработчик выбора типа кальяна (FSM шаг 1).
    
    Сохраняет выбранный тип в состояние и переходит к выбору стола.
    
    Args:
        callback (CallbackQuery): Callback с выбранным типом
        state (FSMContext): Контекст состояния FSM
    """
    # Извлекаем тип из callback_data
    hookah_type = callback.data.replace("type_", "")
    
    # Сохраняем в состояние
    await state.update_data(hookah_type=hookah_type)
    
    # Переходим к выбору стола
    await callback.message.edit_text(
        f"✅ Выбран тип: {hookah_type}\n\n"
        "📍 Теперь выберите стол:",
        reply_markup=get_tables_keyboard()
    )
    await state.set_state(AddHookah.waiting_table)
    await callback.answer()


@router.callback_query(AddHookah.waiting_table, F.data.startswith("table_"))
async def process_table(callback: CallbackQuery, state: FSMContext):
    """
    Обработчик выбора стола и финализации добавления кальяна (FSM шаг 2).
    
    Получает данные из состояния, добавляет кальян в БД и завершает диалог.
    
    Args:
        callback (CallbackQuery): Callback с выбранным столом
        state (FSMContext): Контекст состояния FSM
    """
    # Извлекаем стол из callback_data
    table = callback.data.replace("table_", "")
    
    # Получаем сохраненные данные из состояния
    data = await state.get_data()
    hookah_type = data.get("hookah_type")
    
    # Переходим к выбору силы кальяна
    await state.update_data(table_name=table)
    await callback.message.edit_text(
        f"✅ Выбран стол: {table}\n\n"
        "🔥 Теперь выберите силу кальяна (1-10):",
        reply_markup=get_strength_keyboard()
    )
    await state.set_state(AddHookah.waiting_strength)
    await callback.answer()


@router.callback_query(AddHookah.waiting_strength, F.data.startswith("strength_"))
async def process_hookah_strength(callback: CallbackQuery, state: FSMContext):
    """Обработчик выбора силы кальяна (FSM шаг 3)."""
    strength = int(callback.data.replace("strength_", ""))
    await state.update_data(strength=strength)
    await callback.message.edit_text(
        f"🔥 Сила выбрана: {strength}/10\n\n"
        "❄️ Выберите степень холодности:",
        reply_markup=get_coldness_keyboard()
    )
    await state.set_state(AddHookah.waiting_coldness)
    await callback.answer()


@router.callback_query(AddHookah.waiting_coldness, F.data.startswith("coldness_"))
async def process_hookah_coldness(callback: CallbackQuery, state: FSMContext):
    """Обработчик выбора холодности кальяна (FSM шаг 4)."""
    coldness = callback.data.replace("coldness_", "")
    await state.update_data(coldness=coldness)
    await callback.message.edit_text(
        f"❄️ Холодность выбрана: {coldness}\n\n"
        "💬 Введите комментарий к кальяну или отправьте 'нет' если без комментариев:",
    )
    await state.set_state(AddHookah.waiting_comment)
    await callback.answer()


@router.message(AddHookah.waiting_comment)
async def process_hookah_comment(message: Message, state: FSMContext):
    """Обработчик ввода комментария к кальяну (FSM шаг 5)."""
    data = await state.get_data()
    hookah_type = data.get("hookah_type")
    table_name = data.get("table_name")
    strength = data.get("strength", 5)
    coldness = data.get("coldness", "Средний")
    comment_text = message.text.strip()
    if comment_text.lower() in ("нет", "не", "ничего", "no"):
        comment_text = None

    shift = get_current_shift()
    if not shift:
        await message.answer("⚠️ Смена закрыта или не открыта. Сначала откройте смену.")
        await state.clear()
        return

    user_id = message.from_user.id
    db.add_user_if_not_exists(user_id, message.from_user.username or message.from_user.full_name or "")
    hookah_id = db.add_hookah(
        shift[0],
        hookah_type,
        table_name,
        strength=strength,
        coldness=coldness,
        order_comment=comment_text,
        created_by=user_id
    )
    now = datetime.now().strftime("%H:%M:%S")

    await message.answer(
        f"✅ Кальян успешно добавлен!\n\n"
        f"🌿 Тип: {hookah_type}\n"
        f"📍 Стол: {table_name}\n"
        f"🔥 Сила: {strength}/10\n"
        f"❄️ Холодность: {coldness}\n"
        f"💬 Комментарий: {comment_text or 'Без комментария'}\n"
        f"⏰ Время: {now}",
        reply_markup=get_main_menu_keyboard(True, is_admin(user_id))
    )
    logger.info(f"Кальян добавлен: {hookah_type} на стол {table_name}, сила {strength}, холодность {coldness}")
    await notify_new_hookah(message.bot, hookah_id, hookah_type, table_name, shift[0])
    await state.clear()


# ==================== ПРОСМОТР КАЛЬЯНОВ ====================

@router.callback_query(F.data == "current_hookahs")
async def cmd_current_hookahs(callback: CallbackQuery):
    """
    Обработчик просмотра списка текущих кальянов.
    
    Выводит список всех кальянов за текущую смену с информацией.
    Если кальянов нет, выводит соответствующее сообщение.
    
    Args:
        callback (CallbackQuery): Callback от нажатия кнопки
    """
    shift = get_current_shift()
    
    # Проверка: есть ли открытая смена
    if not shift:
        await callback.message.edit_text("⚠️ Нет открытой смены.")
        await callback.answer()
        return
    
    role = get_user_role(shift[0], callback.from_user.id)
    if not role:
        await callback.message.edit_text(
            "⛔ Вы не участвуете в текущей смене. Вступите в смену или попросите администратора назначить роль."
        )
        await callback.answer()
        return

    hookahs = db.get_hookahs_by_shift(shift[0])
    
    # Если кальянов нет
    if not hookahs:
        await callback.message.edit_text(
            "📭 За эту смену кальянов пока нет.\n\n"
            "Используйте 'Добавить кальян' для добавления."
        )
        await callback.answer()
        return
    
    # Форматируем список кальянов
    text = f"📋 Кальяны за текущую смену ({len(hookahs)}):\n\n"
    for h in hookahs:
        time = h[4][11:]
        status = STATUS_LABELS.get(h[5] if len(h) > 5 else 'new_order', 'Новый заказ')
        strength = h[12] if len(h) > 12 else None
        coldness = h[13] if len(h) > 13 else None
        extras = []
        if strength is not None:
            extras.append(f"{strength}/10")
        if coldness:
            extras.append(coldness)
        detail = ", ".join(extras)
        if detail:
            detail = f", {detail}"
        text += f"• {h[3]} - {h[2]} ({status}{detail}, ⏰ {time})\n"
    
    await callback.message.edit_text(
        text,
        reply_markup=get_hookahs_list_keyboard(hookahs, shift[0])
    )
    await callback.answer()



@router.callback_query(F.data == "join_shift")
async def cmd_join_shift(callback: CallbackQuery):
    """Handler для вступления пользователя в текущую смену как member."""
    shift = get_current_shift()
    if not shift:
        await callback.message.edit_text("⚠️ Нет открытой смены.")
        await callback.answer()
        return

    user_id = callback.from_user.id
    username = callback.from_user.username or callback.from_user.full_name or ""
    db.add_user_if_not_exists(user_id, username)
    success, msg = db.assign_user_to_shift(shift[0], user_id, "member")
    if not success:
        await callback.message.edit_text(f"⚠️ {msg}")
        await callback.answer()
        return

    await callback.message.edit_text(
        "✅ Вы успешно вступили в смену! Теперь вы видите все кальяны этой смены.",
        reply_markup=get_main_menu_keyboard(True, is_admin(user_id))
    )
    await callback.answer()
    logger.info(f"User {user_id} joined shift #{shift[0]} as member")


@router.callback_query(F.data == "take_manager")
async def cmd_take_manager(callback: CallbackQuery):
    """Handler для назначения пользователя менеджером текущей смены."""
    if not is_admin(callback.from_user.id):
        await callback.message.edit_text("⛔ Только админ может назначать менеджера.")
        await callback.answer()
        return

    shift = get_current_shift()
    if not shift:
        await callback.message.edit_text("⚠️ Нет открытой смены.")
        await callback.answer()
        return

    user_id = callback.from_user.id
    username = callback.from_user.username or callback.from_user.full_name or ""
    db.add_user_if_not_exists(user_id, username)
    success, msg = db.assign_user_to_shift(shift[0], user_id, "manager")
    if not success:
        await callback.message.edit_text(f"⚠️ {msg}")
        await callback.answer()
        return

    await callback.message.edit_text(
        "✅ Вы стали менеджером смены. Вам доступны все кальяны этой смены.",
        reply_markup=get_main_menu_keyboard(True, is_admin(user_id))
    )
    await callback.answer()
    logger.info(f"User {user_id} assigned as manager for shift #{shift[0]}")


@router.callback_query(F.data == "profile")
async def cmd_profile(callback: CallbackQuery):
    user_id = callback.from_user.id
    username = callback.from_user.username or callback.from_user.full_name or ""
    db.add_user_if_not_exists(user_id, username)
    enabled = db.get_notification_status(user_id)
    await callback.message.edit_text(
        "👤 Профиль пользователя:\n\nВы можете включить или выключить уведомления о новых кальянах.",
        reply_markup=get_profile_keyboard(enabled, is_admin(user_id))
    )
    await callback.answer()


@router.callback_query(F.data == "admin_panel")
async def cmd_admin_panel(callback: CallbackQuery):
    shift = get_current_shift()
    text = "🛠️ Админская панель\n\n"
    if shift:
        users = db.get_shift_users(shift[0])
        counts = {role: 0 for role in ROLE_LABELS}
        for _, _, role, _ in users:
            if role in counts:
                counts[role] += 1
        text += (
            f"Текущая смена: #{shift[0]}\n"
            f"Менеджеров: {counts.get('manager', 0)}\n"
            f"Кальянных мастеров: {counts.get('hookah_master', 0)}\n"
            f"Управляющих: {counts.get('supervisor', 0)}\n"
            f"Участников: {counts.get('member', 0)}\n\n"
        )
    text += get_work_schedule_text()
    await callback.message.edit_text(
        text,
        reply_markup=get_admin_menu_keyboard()
    )
    await callback.answer()


@router.callback_query(F.data == "admin_schedule")
async def cmd_admin_schedule(callback: CallbackQuery):
    await callback.message.edit_text(
        get_work_schedule_text(),
        reply_markup=get_admin_menu_keyboard()
    )
    await callback.answer()


@router.callback_query(F.data == "admin_delete_shift")
async def cmd_admin_delete_shift(callback: CallbackQuery):
    if not is_admin(callback.from_user.id):
        await callback.message.edit_text("⛔ Только админ может удалять смену.")
        await callback.answer()
        return

    shift = get_current_shift()
    if not shift:
        await callback.message.edit_text(
            "⚠️ Нет открытой смены для удаления.",
            reply_markup=get_admin_menu_keyboard()
        )
        await callback.answer()
        return

    await callback.message.edit_text(
        "❗ Вы уверены, что хотите удалить текущую смену? Все кальяны и роли будут удалены.",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="✅ Удалить смену", callback_data="confirm_delete_shift")],
            [InlineKeyboardButton(text="❌ Отмена", callback_data="back_to_menu")]
        ])
    )
    await callback.answer()


@router.callback_query(F.data == "confirm_delete_shift")
async def cmd_confirm_delete_shift(callback: CallbackQuery):
    if not is_admin(callback.from_user.id):
        await callback.message.edit_text("⛔ Только админ может удалять смену.")
        await callback.answer()
        return

    shift = get_current_shift()
    if not shift:
        await callback.message.edit_text(
            "⚠️ Смена уже закрыта или удалена.",
            reply_markup=get_admin_menu_keyboard()
        )
        await callback.answer()
        return

    db.delete_shift(shift[0])
    await callback.message.edit_text(
        "✅ Текущая смена удалена вместе со всеми данными.",
        reply_markup=get_main_menu_keyboard(False, is_admin(callback.from_user.id))
    )
    await callback.answer()


@router.callback_query(F.data == "toggle_notifications")
async def cmd_toggle_notifications(callback: CallbackQuery):
    user_id = callback.from_user.id
    current = db.get_notification_status(user_id)
    db.set_notification_status(user_id, not current)
    await callback.message.edit_text(
        f"🔔 Уведомления {'включены' if not current else 'выключены'}.",
        reply_markup=get_profile_keyboard(not current, is_admin(user_id))
    )
    await callback.answer()


@router.callback_query(F.data == "assign_role_help")
async def cmd_assign_role_help(callback: CallbackQuery):
    await callback.message.edit_text(
        "🧩 Назначить роль может только админ.\n"
        "Используйте команду:\n"
        "/assign_role <user_id> <role>\n\n"
        "Доступные роли: manager, hookah_master, supervisor, member"
    )
    await callback.answer()


@router.message(Command("assign_role"))
async def cmd_assign_role(message: Message):
    if not is_admin(message.from_user.id):
        await message.reply("⛔ Только админ может назначать роли.")
        return

    parts = message.text.split()
    if len(parts) < 3:
        await message.reply("Использование: /assign_role <user_id> <role>")
        return

    try:
        target_id = int(parts[1])
    except ValueError:
        await message.reply("Неправильный user_id. Укажите числовой Telegram user_id.")
        return

    role = parts[2]
    shift = get_current_shift()
    if not shift:
        await message.reply("⚠️ Нет открытой смены.")
        return

    db.add_user_if_not_exists(target_id, None)
    success, msg = db.assign_user_to_shift(shift[0], target_id, role)
    if not success:
        await message.reply(f"⚠️ {msg}")
        return

    await message.reply(f"✅ Пользователь {target_id} назначен как {role} в текущую смену.")
@router.callback_query(F.data.startswith("view_"))
async def cmd_view_hookah(callback: CallbackQuery):
    """Обработчик просмотра деталей конкретного кальяна."""
    hookah_id = int(callback.data.replace("view_", ""))
    hookah = db.get_hookah_by_id(hookah_id)
    if not hookah:
        await callback.answer("❌ Кальян не найден")
        return

    shift_id = hookah[1]
    role = get_user_role(shift_id, callback.from_user.id)
    if not role:
        await callback.message.edit_text(
            "⛔ У вас нет доступа к этому кальяну. Вступите в смену или попросите администратора назначить роль."
        )
        await callback.answer()
        return

    status = STATUS_LABELS.get(hookah[5] if len(hookah) > 5 else 'new_order', 'Новый заказ')
    creator = db.get_username(hookah[6]) if len(hookah) > 6 else None
    accepted_by = db.get_username(hookah[7]) if len(hookah) > 7 and hookah[7] else None
    accepted_at = hookah[8] if len(hookah) > 8 else None
    ready_at = hookah[9] if len(hookah) > 9 else None
    last_updated_at = hookah[10] if len(hookah) > 10 else None
    last_updated_by = db.get_username(hookah[11]) if len(hookah) > 11 and hookah[11] else None
    strength = hookah[12] if len(hookah) > 12 else None
    coldness = hookah[13] if len(hookah) > 13 else None
    order_comment = hookah[14] if len(hookah) > 14 else None

    text = f"🍃 Кальян #{hookah[0]}\n"
    text += f"🌿 Тип: {hookah[2]}\n"
    text += f"📍 Стол: {hookah[3]}\n"
    if strength is not None:
        text += f"🔥 Сила: {strength}/10\n"
    if coldness:
        text += f"❄️ Холодность: {coldness}\n"
    if order_comment:
        text += f"💬 Комментарий: {order_comment}\n"
    text += f"⏰ Добавлен: {hookah[4]}\n"
    text += f"📌 Статус: {status}\n"
    if creator:
        text += f"👤 Добавил: {creator}\n"
    if accepted_by and accepted_at:
        text += f"✅ Принят: {accepted_by} ({accepted_at})\n"
    if ready_at:
        text += f"🎯 Готов: {ready_at}\n"
    if last_updated_at and last_updated_by:
        text += f"✍️ Изменил: {last_updated_by} ({last_updated_at})\n"

    await callback.message.edit_text(
        text,
        reply_markup=get_hookah_actions_keyboard(hookah, role)
    )
    await callback.answer()


@router.callback_query(F.data.startswith("accept_"))
async def cmd_accept_hookah(callback: CallbackQuery):
    hookah_id = int(callback.data.replace("accept_", ""))
    hookah = db.get_hookah_by_id(hookah_id)
    if not hookah:
        await callback.answer("❌ Кальян не найден")
        return

    role = get_user_role(hookah[1], callback.from_user.id)
    if not can_control_hookah(role):
        await callback.message.edit_text("⛔ У вас нет прав принимать кальяны.")
        await callback.answer()
        return

    if (hookah[5] if len(hookah) > 5 else 'new_order') != 'new_order':
        await callback.answer("⚠️ Этот кальян уже принят или уже находится в работе.")
        return

    db.set_hookah_status(hookah_id, 'accepted', callback.from_user.id)
    await callback.message.edit_text(
        f"✅ Кальян #{hookah_id} принят в работу.",
        reply_markup=get_hookah_actions_keyboard(db.get_hookah_by_id(hookah_id), role)
    )
    await callback.answer()


@router.callback_query(F.data.startswith("ready_"))
async def cmd_ready_hookah(callback: CallbackQuery):
    hookah_id = int(callback.data.replace("ready_", ""))
    hookah = db.get_hookah_by_id(hookah_id)
    if not hookah:
        await callback.answer("❌ Кальян не найден")
        return

    role = get_user_role(hookah[1], callback.from_user.id)
    if not can_control_hookah(role):
        await callback.message.edit_text("⛔ У вас нет прав отмечать кальян готовым.")
        await callback.answer()
        return

    if (hookah[5] if len(hookah) > 5 else 'new_order') != 'in_packing':
        await callback.answer("⚠️ Этот кальян ещё не принят или уже готов.")
        return

    db.set_hookah_status(hookah_id, 'ready', callback.from_user.id)
    await callback.message.edit_text(
        f"✅ Кальян #{hookah_id} помечен как готовый к выдаче.",
        reply_markup=get_hookah_actions_keyboard(db.get_hookah_by_id(hookah_id), role)
    )
    await callback.answer()


# ==================== РЕДАКТИРОВАНИЕ КАЛЬЯНА ====================

@router.callback_query(F.data.startswith("edit_type_"))
async def cmd_edit_type(callback: CallbackQuery, state: FSMContext):
    """
    Обработчик начала редактирования типа кальяна.
    
    Запускает FSM диалог для выбора нового типа.
    
    Args:
        callback (CallbackQuery): Callback с ID кальяна
        state (FSMContext): Контекст состояния FSM
    """
    hookah_id = int(callback.data.replace("edit_type_", ""))
    hookah = db.get_hookah_by_id(hookah_id)
    if not hookah:
        await callback.answer("❌ Кальян не найден")
        return

    role = get_user_role(hookah[1], callback.from_user.id)
    if not is_manager_or_admin(role):
        await callback.message.edit_text("⛔ У вас нет прав редактировать кальяны.")
        await callback.answer()
        return

    await state.update_data(hookah_id=hookah_id)
    await callback.message.edit_text(
        "🌿 Выберите новый тип кальяна:",
        reply_markup=get_hookah_type_keyboard()
    )
    await state.set_state(EditHookah.waiting_type)
    await callback.answer()


@router.callback_query(EditHookah.waiting_type, F.data.startswith("type_"))
async def process_edit_type(callback: CallbackQuery, state: FSMContext):
    """Обработчик сохранения нового типа кальяна."""
    hookah_type = callback.data.replace("type_", "")
    data = await state.get_data()
    hookah_id = data.get("hookah_id")
    db.update_hookah(hookah_id, hookah_type=hookah_type, updated_by=callback.from_user.id)
    await callback.message.edit_text(
        f"✅ Тип успешно изменен на: {hookah_type}",
        reply_markup=get_hookah_actions_keyboard(db.get_hookah_by_id(hookah_id), get_user_role(db.get_hookah_by_id(hookah_id)[1], callback.from_user.id))
    )
    await state.clear()
    await callback.answer()
    logger.info(f"Кальян #{hookah_id}: тип изменен на {hookah_type}")


@router.callback_query(F.data.startswith("edit_table_"))
async def cmd_edit_table(callback: CallbackQuery, state: FSMContext):
    """
    Обработчик начала редактирования стола кальяна.
    
    Запускает FSM диалог для выбора нового стола.
    
    Args:
        callback (CallbackQuery): Callback с ID кальяна
        state (FSMContext): Контекст состояния FSM
    """
    hookah_id = int(callback.data.replace("edit_table_", ""))
    hookah = db.get_hookah_by_id(hookah_id)
    if not hookah:
        await callback.answer("❌ Кальян не найден")
        return

    role = get_user_role(hookah[1], callback.from_user.id)
    if not is_manager_or_admin(role):
        await callback.message.edit_text("⛔ У вас нет прав редактировать кальяны.")
        await callback.answer()
        return

    await state.update_data(hookah_id=hookah_id)
    await callback.message.edit_text(
        "📍 Выберите новый стол:",
        reply_markup=get_tables_keyboard()
    )
    await state.set_state(EditHookah.waiting_table)
    await callback.answer()


@router.callback_query(EditHookah.waiting_table, F.data.startswith("table_"))
async def process_edit_table(callback: CallbackQuery, state: FSMContext):
    """Обработчик сохранения нового стола кальяна."""
    table = callback.data.replace("table_", "")
    data = await state.get_data()
    hookah_id = data.get("hookah_id")
    db.update_hookah(hookah_id, table_name=table, updated_by=callback.from_user.id)
    await callback.message.edit_text(
        f"✅ Стол успешно изменен на: {table}",
        reply_markup=get_hookah_actions_keyboard(db.get_hookah_by_id(hookah_id), get_user_role(db.get_hookah_by_id(hookah_id)[1], callback.from_user.id))
    )
    await state.clear()
    await callback.answer()
    logger.info(f"Кальян #{hookah_id}: стол изменен на {table}")


@router.callback_query(F.data.startswith("delete_"))
async def cmd_delete_hookah(callback: CallbackQuery):
    """
    Обработчик удаления кальяна.
    
    Удаляет кальян из БД и возвращает пользователя в главное меню.
    
    Args:
        callback (CallbackQuery): Callback с ID кальяна для удаления
    """
    hookah_id = int(callback.data.replace("delete_", ""))
    hookah = db.get_hookah_by_id(hookah_id)
    if not hookah:
        await callback.answer("❌ Кальян не найден")
        return

    role = get_user_role(hookah[1], callback.from_user.id)
    if not is_manager_or_admin(role):
        await callback.message.edit_text("⛔ У вас нет прав удалять кальяны.")
        await callback.answer()
        return

    db.delete_hookah(hookah_id, deleted_by=callback.from_user.id)
    shift = get_current_shift()
    is_shift_open = shift is not None

    await callback.message.edit_text(
        f"✅ Кальян #{hookah_id} успешно удален.\n\n"
        "Выберите действие:",
        reply_markup=get_main_menu_keyboard(is_shift_open, is_admin(callback.from_user.id))
    )
    await callback.answer()
    logger.info(f"Кальян #{hookah_id} удален")


# ==================== ИСТОРИЯ СМЕН ====================

@router.callback_query(F.data == "history")
async def cmd_history(callback: CallbackQuery):
    """
    Обработчик просмотра истории смен.
    
    Выводит список всех закрытых смен с датой и количеством кальянов.
    
    Args:
        callback (CallbackQuery): Callback от нажатия кнопки
    """
    # Получаем все смены
    shifts = db.get_all_shifts()
    
    # Если истории нет
    if not shifts:
        await callback.message.edit_text(
            "📭 История смен пуста.\n\n"
            "После закрытия смены она появится здесь."
        )
        await callback.answer()
        return
    
    await callback.message.edit_text(
        "📊 История смен:",
        reply_markup=get_history_keyboard(shifts)
    )
    await callback.answer()


@router.callback_query(F.data.startswith("shift_"))
async def cmd_shift_details(callback: CallbackQuery):
    """
    Обработчик просмотра деталей конкретной смены.
    
    Выводит подробную информацию о смене и все кальяны за нее.
    
    Args:
        callback (CallbackQuery): Callback с ID смены
    """
    # Извлекаем ID смены
    shift_id = int(callback.data.replace("shift_", ""))
    
    # Получаем данные смены
    shift = db.get_shift_by_id(shift_id)
    
    # Проверка: смена найдена
    if not shift:
        await callback.answer("❌ Смена не найдена")
        return
    
    # Получаем кальяны за смену
    hookahs = db.get_hookahs_by_shift(shift_id)
    
    # Форматируем информацию о смене
    text = (
        f"📊 Смена #{shift[0]}\n"
        f"🔓 Открыта: {shift[1]}\n"
    )
    
    if shift[2]:
        text += f"🔒 Закрыта: {shift[2]}\n"
    
    text += f"📈 Всего кальянов: {len(hookahs)}\n\n"
    
    # Добавляем список кальянов
    if hookahs:
        text += "🍃 Кальяны:\n"
        for h in hookahs:
            time = h[4][11:]  # Извлекаем время
            text += f"• {h[3]} - {h[2]} (⏰ {time})\n"
    
    await callback.message.edit_text(
        text,
        reply_markup=get_main_menu_keyboard(get_current_shift() is not None, is_admin(callback.from_user.id))
    )
    await callback.answer()


# ==================== НАВИГАЦИЯ ====================

@router.callback_query(F.data == "back_to_menu")
async def cmd_back_to_menu(callback: CallbackQuery):
    """
    Обработчик возврата в главное меню.
    
    Возвращает пользователя в главное меню из любого места в боте.
    
    Args:
        callback (CallbackQuery): Callback от нажатия кнопки "Назад"
    """
    is_open = get_current_shift() is not None
    
    await callback.message.edit_text(
        "🏠 Главное меню\n\n"
        "Выберите действие:",
        reply_markup=get_main_menu_keyboard(is_open, is_admin(callback.from_user.id))
    )
    await callback.answer()


@router.callback_query(F.data == "back_to_hookahs")
async def cmd_back_to_hookahs(callback: CallbackQuery):
    """
    Обработчик возврата к списку кальянов.
    
    Возвращает пользователя к списку текущих кальянов.
    
    Args:
        callback (CallbackQuery): Callback от нажатия кнопки "Назад"
    """
    shift = get_current_shift()
    
    if shift:
        hookahs = db.get_hookahs_by_shift(shift[0])
        if hookahs:
            # Форматируем список
            text = f"📋 Кальяны за текущую смену ({len(hookahs)}):\n\n"
            for h in hookahs:
                time = h[4][11:]  # Извлекаем время
                text += f"• {h[3]} - {h[2]} (⏰ {time})\n"
            
            await callback.message.edit_text(
                text,
                reply_markup=get_hookahs_list_keyboard(hookahs, shift[0])
            )
        else:
            await callback.message.edit_text(
                "📭 Нет кальянов.",
                reply_markup=get_main_menu_keyboard(True, is_admin(callback.from_user.id))
            )
    
    await callback.answer()