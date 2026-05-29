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
    get_shift_management_keyboard,
    get_hookah_type_keyboard,
    get_tables_keyboard,
    get_strength_keyboard,
    get_coldness_keyboard,
    get_hookahs_list_keyboard,
    get_hookah_actions_keyboard,
    get_new_hookah_notification_keyboard,
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
REPORT_CHAT_ID = int(getenv("REPORT_CHAT_ID", "0") or 0)
logger.info(f"🔐 Админ ID из переменных окружения: {BOT_OWNER_ID}")
logger.info(f"📣 Отчетовый чат из переменных окружения: {REPORT_CHAT_ID}")

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
    admin_status = BOT_OWNER_ID != 0 and user_id == BOT_OWNER_ID
    logger.debug(f"Проверка админа: user_id={user_id}, BOT_OWNER_ID={BOT_OWNER_ID}, is_admin={admin_status}")
    return admin_status


def get_user_role(shift_id: int, user_id: int) -> str:
    """Получить глобальную роль пользователя. Роль не привязана к смене."""
    if is_admin(user_id):
        return 'admin'
    global_role = db.get_user_global_role(user_id)
    return global_role or 'member'


def user_has_access(shift_id: int, user_id: int) -> bool:
    """Любой зарегистрированный пользователь имеет доступ к просмотру."""
    role = get_user_role(shift_id, user_id)
    return role in ('admin', 'manager', 'hookah_master', 'supervisor', 'member')


def can_edit_hookah(role: str) -> bool:
    """Менеджер и админ могут редактировать кальяны."""
    return role in ('admin', 'manager')


def can_add_hookah(role: str) -> bool:
    """Кальянный мастер, менеджер и админ могут добавлять кальяны."""
    return role in ('admin', 'hookah_master', 'manager')


def can_control_hookah(role: str) -> bool:
    """Кальянный мастер и админ могут принимать/готовить кальяны."""
    return role in ('admin', 'hookah_master')


def is_manager_or_admin(role: str) -> bool:
    """Менеджер или админ — для редактирования и удаления."""
    return role in ('admin', 'manager')


def get_work_schedule_text() -> str:
    weekday = db.get_moscow_datetime().weekday()
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


def format_shift_report(shift: tuple, hookahs: list, members: list) -> str:
    """Форматирование отчета по смене для отправки в общий чат."""
    shift_id, open_time, close_time, is_open, total_hookahs = shift
    status = "Открыта" if is_open else "Закрыта"
    report = [
        f"📊 Отчет по смене #{shift_id}",
        f"Статус: {status}",
        f"Открыта: {open_time}",
        f"Закрыта: {close_time or '—'}",
        f"Всего кальянов: {total_hookahs}",
        "",
        "👥 Участники смены:"
    ]

    if members:
        for user_id, username, role, joined_at in members:
            display_name = db.get_user_display_name(user_id)
            username_text = f"@{username}" if username else ""
            report.append(f"• {display_name} {username_text} — {role} (вступил: {joined_at})")
    else:
        report.append("• Нет участников")

    report.append("")
    report.append("🍃 Кальяны смены:")

    if hookahs:
        for h in hookahs:
            hookah_id = h[0]
            table_name = h[3]
            hookah_type = h[2]
            created_at = h[4]
            status_label = STATUS_LABELS.get(h[5] if len(h) > 5 else 'new_order', 'Новый заказ')
            strength = h[12] if len(h) > 12 else None
            coldness = h[13] if len(h) > 13 else None
            ready_at = h[9] if len(h) > 9 else None
            timing = created_at
            details = []
            if strength is not None:
                details.append(f"{strength}/10")
            if coldness:
                details.append(coldness)
            if ready_at:
                details.append(f"готов: {ready_at}")
            detail_text = f" ({', '.join(details)})" if details else ""
            report.append(f"• #{hookah_id} {table_name} — {hookah_type}, {status_label}{detail_text}, время: {timing}")
    else:
        report.append("• Кальянов нет")

    return "\n".join(report)


async def send_shift_report(bot, shift: tuple) -> None:
    """Отправить отчет по смене в общий чат из переменных окружения."""
    if REPORT_CHAT_ID == 0:
        logger.warning("Отчетный чат не настроен: REPORT_CHAT_ID=0")
        return

    hookahs = db.get_hookahs_by_shift(shift[0])
    members = db.get_shift_users(shift[0])
    report_text = format_shift_report(shift, hookahs, members)

    try:
        await bot.send_message(REPORT_CHAT_ID, report_text)
        logger.info(f"Отчет по смене #{shift[0]} отправлен в чат {REPORT_CHAT_ID}")
    except Exception as exc:
        logger.exception(f"Не удалось отправить отчет по смене #{shift[0]}: {exc}")


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
            await bot.send_message(
                user_id,
                message,
                reply_markup=get_new_hookah_notification_keyboard(hookah_id)
            )
        except Exception:
            continue


async def notify_hookah_ready(bot, hookah_id: int) -> None:
    hookah = db.get_hookah_by_id(hookah_id)
    if not hookah:
        return

    hookah_type = hookah[2]
    table_name = hookah[3]
    message = (
        f"🎯 Кальян #{hookah_id} готов к выдаче!\n"
        f"🌿 Тип: {hookah_type}\n"
        f"📍 Стол: {table_name}\n"
        "Статус: Готов к выдаче" 
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


class EditShift(StatesGroup):
    """Состояния для редактирования смены"""
    waiting_open_time = State()  # Ожидание ввода нового времени открытия
    waiting_close_time = State()  # Ожидание ввода нового времени закрытия


class EditUser(StatesGroup):
    """Состояния для редактирования пользователя"""
    waiting_display_name = State()  # Ожидание ввода нового отображаемого имени


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
    
    Args:
        message (Message): Объект сообщения от пользователя
    """
    user_id = message.from_user.id
    logger.info(f"Пользователь {user_id} запросил /start; is_admin={is_admin(user_id)}")
    await message.answer(
        "🍃 Добро пожаловать в бот учета кальянов!\n\n"
        "Это приложение поможет вам вести учет всех кальянов за смену.\n\n"
        "Выберите действие:",
        reply_markup=get_main_menu_keyboard(is_admin(user_id))
    )


# ==================== УПРАВЛЕНИЕ СМЕНАМИ ====================

@router.callback_query(F.data == "shift_management")
async def cmd_shift_management(callback: CallbackQuery):
    """
    Обработчик кнопки 'Смена' в главном меню.

    Показывает текущий статус смены (открыта/закрыта), список кальянов и
    опции в зависимости от роли пользователя и участия в смене.
    """
    shift = db.get_current_shift()
    is_open = shift is not None
    user_id = callback.from_user.id
    is_admin_user = is_admin(user_id)

    status_text = "✅ Смена открыта" if is_open else "❌ Смена закрыта"
    if is_open:
        shift_info = f"{status_text}\n\n🕐 Открыта: {shift[1]}\n"
        user_in_shift = db.is_user_in_shift(shift[0], user_id)
        current_role = get_user_role(shift[0], user_id)
        hookahs = db.get_hookahs_by_shift(shift[0])
        shift_info += f"Кальянов в смене: {len(hookahs)}\n\n"

        if current_role in ('admin', 'manager') and hookahs:
            shift_info += "📋 Текущие кальяны:\n"
            for h in hookahs[:8]:
                time = h[4][11:]
                status = STATUS_LABELS.get(h[5] if len(h) > 5 else 'new_order', 'Новый заказ')
                shift_info += f"• {h[3]} - {h[2]} ({status}, ⏰ {time})\n"
            if len(hookahs) > 8:
                shift_info += f"...и еще {len(hookahs) - 8} кальянов\n"
        elif hookahs:
            shift_info += f"📋 Кальянов в смене: {len(hookahs)}\n"
        else:
            shift_info += "📋 Кальянов в смене пока нет.\n"

        shift_info += "\nВыберите действие:"
    else:
        shift_info = f"{status_text}\n\nНет активной смены. Выберите действие:"
        user_in_shift = False
        current_role = 'member'

    await callback.message.edit_text(
        shift_info,
        reply_markup=get_shift_management_keyboard(
            is_shift_open=is_open,
            is_admin=is_admin_user,
            is_user_in_shift=user_in_shift,
            is_manager=current_role == 'manager'
        )
    )
    await callback.answer()


@router.callback_query(F.data == "back_to_main_menu")
async def cmd_back_to_main_menu(callback: CallbackQuery):
    """
    Обработчик для возврата в главное меню.
    """
    user_id = callback.from_user.id
    await callback.message.edit_text(
        "🍃 Добро пожаловать в бот учета кальянов!\n\n"
        "Это приложение поможет вам вести учет всех кальянов за смену.\n\n"
        "Выберите действие:",
        reply_markup=get_main_menu_keyboard(is_admin(user_id))
    )
    await callback.answer()


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
        f"⏰ Время: {db.get_moscow_datetime().strftime('%H:%M:%S')}\n\n"
        "Выберите действие:",
        reply_markup=get_main_menu_keyboard(is_admin(callback.from_user.id))
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
    await send_shift_report(callback.message.bot, shift)
    await callback.message.edit_text(
        f"✅ Смена успешно закрыта!\n\n"
        f"📊 Всего кальянов за смену: {total}\n"
        f"🕐 Время закрытия: {db.get_moscow_datetime().strftime('%H:%M:%S')}\n\n"
        "Выберите действие:",
        reply_markup=get_main_menu_keyboard(is_admin(callback.from_user.id))
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
        "🔥 Теперь выберите крепость (1-10):",
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
        f"🔥 Крепость выбрана: {strength}/10\n\n"
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
    """Обработчик ввода комментария к кальяну (FSM шаг 5) или редактирования."""
    data = await state.get_data()
    hookah_id = data.get("hookah_id")
    
    # Если это редактирование, а не добавление
    if hookah_id:
        comment_text = message.text.strip()
        if comment_text.lower() in ("нет", "не", "ничего", "no", ""):
            comment_text = None
        
        hookah = db.get_hookah_by_id(hookah_id)
        if hookah:
            db.update_hookah_strength_and_coldness(
                hookah_id,
                order_comment=comment_text,
                updated_by=message.from_user.id
            )
            user_id = message.from_user.id
            shift_id = hookah[1]
            await message.answer(
                f"✅ Комментарий кальяна #{hookah_id} обновлен!",
                reply_markup=get_hookah_actions_keyboard(hookah, get_user_role(shift_id, user_id))
            )
            logger.info(f"Кальян #{hookah_id}: комментарий обновлен")
        await state.clear()
        return
    
    # Иначе это добавление нового кальяна
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
    now = db.get_moscow_datetime().strftime("%H:%M:%S")

    await message.answer(
        f"✅ Кальян успешно добавлен!\n\n"
        f"🌿 Тип: {hookah_type}\n"
        f"📍 Стол: {table_name}\n"
        f"🔥 Крепость: {strength}/10\n"
        f"❄️ Холодность: {coldness}\n"
        f"💬 Комментарий: {comment_text or 'Без комментария'}\n"
        f"⏰ Время: {now}",
        reply_markup=get_main_menu_keyboard(is_admin(user_id))
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
    """
    shift = get_current_shift()
    
    # Проверка: есть ли открытая смена
    if not shift:
        await callback.message.edit_text("⚠️ Нет открытой смены.")
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
        reply_markup=get_main_menu_keyboard(is_admin(user_id))
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
        reply_markup=get_main_menu_keyboard(is_admin(user_id))
    )
    await callback.answer()
    logger.info(f"User {user_id} assigned as manager for shift #{shift[0]}")


@router.callback_query(F.data == "profile")
async def cmd_profile(callback: CallbackQuery):
    """Обработчик кнопки 'Профиль'."""
    user_id = callback.from_user.id
    username = callback.from_user.username or callback.from_user.full_name or ""
    db.add_user_if_not_exists(user_id, username)
    
    profile = db.get_user_profile(user_id)
    display_name = profile[2] if profile else username
    global_role = profile[3] if profile else "member"
    
    text = (
        "👤 Ваш профиль:\n\n"
        f"Имя: {display_name or username or 'Не указано'}\n"
        f"Роль: {global_role}\n"
        f"Username: @{username}\n"
    )
    
    await callback.message.edit_text(
        text,
        reply_markup=get_profile_keyboard()
    )
    await callback.answer()


@router.callback_query(F.data == "profile_stats")
async def cmd_profile_stats(callback: CallbackQuery):
    """Обработчик просмотра статистики профиля."""
    user_id = callback.from_user.id
    
    stats = db.get_user_stats_full(user_id)
    
    if not stats:
        await callback.message.edit_text(
            "❌ Профиль не найден.",
            reply_markup=get_profile_keyboard()
        )
        await callback.answer()
        return
    
    text = (
        f"📊 Статистика {stats['display_name'] or stats['username']}:\n\n"
        f"Кальянов добавлено: {stats['total_hookahs']}\n"
    )
    
    if stats['hookah_types']:
        text += "   По типам:\n"
        for hookah_type, count in stats['hookah_types'].items():
            text += f"   - {hookah_type}: {count}\n"
    
    text += (
        f"\nСмен всего: {stats['total_shifts']}\n"
        f"В этом месяце: {stats['month_shifts']}\n"
    )
    
    await callback.message.edit_text(
        text,
        reply_markup=get_profile_keyboard()
    )
    await callback.answer()


@router.callback_query(F.data == "admin_panel")
async def cmd_admin_panel(callback: CallbackQuery):
    """Обработчик админ-панели."""
    user_id = callback.from_user.id
    
    if not is_admin(user_id):
        await callback.message.edit_text(
            "❌ У вас нет доступа к админ-панели.",
            reply_markup=get_main_menu_keyboard(is_admin(user_id))
        )
        await callback.answer()
        return
    
    shift = db.get_current_shift()
    text = "⚙️ Админ панель\n\n"
    
    if shift:
        text += f"Текущая смена: #{shift[0]}\n"
        text += f"Открыта: {shift[1]}\n"
        text += f"Кальянов в смене: {shift[4]}\n\n"
    else:
        text += "Нет открытой смены\n\n"
    
    text += "Выберите действие:"
    
    await callback.message.edit_text(
        text,
        reply_markup=get_admin_menu_keyboard()
    )
    await callback.answer()


@router.callback_query(F.data == "admin_members")
async def cmd_admin_members(callback: CallbackQuery):
    """Обработчик управления участниками смены."""
    user_id = callback.from_user.id
    
    if not is_admin(user_id):
        await callback.message.edit_text(
            "❌ У вас нет доступа.",
            reply_markup=get_main_menu_keyboard(is_admin(user_id))
        )
        await callback.answer()
        return
    
    shift = db.get_current_shift()
    
    if not shift:
        await callback.message.edit_text(
            "❌ Нет открытой смены.",
            reply_markup=get_admin_menu_keyboard()
        )
        await callback.answer()
        return
    
    users = db.get_shift_users(shift[0])
    text = f"👥 Участники смены #{shift[0]}:\n\n"
    
    if not users:
        text += "Нет участников в смене."
    else:
        for user_id_shift, username, role, joined_at in users:
            display_name = db.get_user_display_name(user_id_shift)
            text += f"• {display_name} (@{username})\n"
            text += f"  Роль: {role}\n"
            text += f"  Присоединилась: {joined_at}\n\n"
    
    await callback.message.edit_text(
        text,
        reply_markup=get_admin_menu_keyboard()
    )
    await callback.answer()


@router.callback_query(F.data == "admin_shifts")
async def cmd_admin_shifts(callback: CallbackQuery):
    """Обработчик управления сменами — показывает список смен с кнопками."""
    user_id = callback.from_user.id
    
    if not is_admin(user_id):
        await callback.message.edit_text(
            "❌ У вас нет доступа.",
            reply_markup=get_main_menu_keyboard(is_admin(user_id))
        )
        await callback.answer()
        return
    
    shifts = db.get_all_shifts()[:10]  # Последние 10 смен
    
    if not shifts:
        await callback.message.edit_text(
            "Нет смен в системе.",
            reply_markup=get_admin_menu_keyboard()
        )
        await callback.answer()
        return

    from src.keyboards import get_admin_shifts_keyboard
    await callback.message.edit_text(
        "📋 Управление сменами\nВыберите смену для редактирования:",
        reply_markup=get_admin_shifts_keyboard(shifts)
    )
    await callback.answer()


@router.callback_query(F.data.startswith("admin_shift_"))
async def cmd_admin_shift_detail(callback: CallbackQuery):
    """Обработчик просмотра и управления конкретной сменой из админки."""
    if not is_admin(callback.from_user.id):
        await callback.message.edit_text("⛔ Только админ.")
        await callback.answer()
        return

    shift_id = int(callback.data.replace("admin_shift_", ""))
    shift = db.get_shift_by_id(shift_id)
    if not shift:
        await callback.answer("Смена не найдена")
        return

    hookahs = db.get_hookahs_by_shift(shift_id)
    status = "✅ Открыта" if shift[3] else "🔒 Закрыта"

    text = (
        f"📋 Смена #{shift[0]}\n"
        f"Статус: {status}\n"
        f"Открыта: {shift[1]}\n"
    )
    if shift[2]:
        text += f"Закрыта: {shift[2]}\n"
    text += f"Кальянов: {len(hookahs)}\n"

    from src.keyboards import get_admin_shift_detail_keyboard
    await callback.message.edit_text(
        text,
        reply_markup=get_admin_shift_detail_keyboard(shift, is_admin=True)
    )
    await callback.answer()


@router.callback_query(F.data.startswith("admin_shift_hookahs_"))
async def cmd_admin_shift_hookahs(callback: CallbackQuery):
    """Обработчик просмотра кальянов в админской смене."""
    if not is_admin(callback.from_user.id):
        await callback.message.edit_text("⛔ Только админ.")
        await callback.answer()
        return

    shift_id = int(callback.data.replace("admin_shift_hookahs_", ""))
    shift = db.get_shift_by_id(shift_id)
    if not shift:
        await callback.answer("Смена не найдена")
        return

    hookahs = db.get_hookahs_by_shift(shift_id)
    if not hookahs:
        await callback.message.edit_text(
            f"📋 Смена #{shift_id}: кальянов нет.",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="⬅️ Назад", callback_data=f"admin_shift_{shift_id}")]
            ])
        )
        await callback.answer()
        return

    text = f"📋 Кальяны смены #{shift_id}:\n\n"
    for h in hookahs:
        time = h[4][11:]
        status = STATUS_LABELS.get(h[5] if len(h) > 5 else 'new_order', 'Новый заказ')
        text += f"• {h[3]} - {h[2]} ({status}, ⏰ {time})\n"

    await callback.message.edit_text(
        text,
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="⬅️ Назад", callback_data=f"admin_shift_{shift_id}")]
        ])
    )
    await callback.answer()


@router.callback_query(F.data.startswith("admin_shift_members_"))
async def cmd_admin_shift_members(callback: CallbackQuery):
    """Обработчик просмотра участников конкретной смены."""
    if not is_admin(callback.from_user.id):
        await callback.message.edit_text("⛔ Только админ.")
        await callback.answer()
        return

    shift_id = int(callback.data.replace("admin_shift_members_", ""))
    shift = db.get_shift_by_id(shift_id)
    if not shift:
        await callback.answer("Смена не найдена")
        return

    members = db.get_shift_users(shift_id)
    text = f"👥 Участники смены #{shift_id}:\n\n"
    if not members:
        text += "Нет участников.\n"
    else:
        for user_id_shift, username, role, joined_at in members:
            display_name = db.get_user_display_name(user_id_shift)
            text += f"• {display_name} (@{username}) — {role}\n"
            text += f"  Присоединился: {joined_at}\n\n"

    await callback.message.edit_text(
        text,
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="⬅️ Назад", callback_data=f"admin_shift_{shift_id}")]
        ])
    )
    await callback.answer()


@router.callback_query(F.data.startswith("admin_close_shift_"))
async def cmd_admin_close_specific_shift(callback: CallbackQuery):
    """Админ закрывает конкретную смену."""
    if not is_admin(callback.from_user.id):
        await callback.message.edit_text("⛔ Только админ.")
        await callback.answer()
        return

    shift_id = int(callback.data.replace("admin_close_shift_", ""))
    shift = db.get_shift_by_id(shift_id)
    if not shift or not shift[3]:
        await callback.message.edit_text(
            "⚠️ Смена уже закрыта или не найдена.",
            reply_markup=get_admin_menu_keyboard()
        )
        await callback.answer()
        return

    db.close_shift(shift_id)
    await send_shift_report(callback.message.bot, db.get_shift_by_id(shift_id))
    hookahs = db.get_hookahs_by_shift(shift_id)

    await callback.message.edit_text(
        f"✅ Смена #{shift_id} закрыта.\nКальянов: {len(hookahs)}",
        reply_markup=get_admin_menu_keyboard()
    )
    await callback.answer()
    logger.info(f"Admin closed shift #{shift_id}")


@router.callback_query(F.data.startswith("admin_delete_shift_"))
async def cmd_admin_delete_specific_shift(callback: CallbackQuery):
    """Админ удаляет конкретную смену."""
    if not is_admin(callback.from_user.id):
        await callback.message.edit_text("⛔ Только админ.")
        await callback.answer()
        return

    shift_id = int(callback.data.replace("admin_delete_shift_", ""))
    shift = db.get_shift_by_id(shift_id)
    if not shift:
        await callback.message.edit_text(
            "⚠️ Смена не найдена.",
            reply_markup=get_admin_menu_keyboard()
        )
        await callback.answer()
        return

    await callback.message.edit_text(
        f"❗ Удалить смену #{shift_id}? Все кальяны и данные будут удалены безвозвратно.",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="✅ Да, удалить", callback_data=f"confirm_admin_delete_shift_{shift_id}")],
            [InlineKeyboardButton(text="❌ Отмена", callback_data="admin_shifts")]
        ])
    )
    await callback.answer()


@router.callback_query(F.data.startswith("confirm_admin_delete_shift_"))
async def cmd_confirm_admin_delete_shift(callback: CallbackQuery):
    """Подтверждение удаления смены из админки."""
    if not is_admin(callback.from_user.id):
        await callback.message.edit_text("⛔ Только админ.")
        await callback.answer()
        return

    shift_id = int(callback.data.replace("confirm_admin_delete_shift_", ""))
    db.delete_shift(shift_id)

    await callback.message.edit_text(
        f"✅ Смена #{shift_id} удалена.",
        reply_markup=get_admin_menu_keyboard()
    )
    await callback.answer()
    logger.info(f"Admin deleted shift #{shift_id}")


@router.callback_query(F.data.startswith("reopen_shift_"))
async def cmd_reopen_shift(callback: CallbackQuery):
    """Переоткрыть закрытую смену."""
    if not is_admin(callback.from_user.id):
        await callback.message.edit_text("⛔ Только админ.")
        await callback.answer()
        return

    shift_id = int(callback.data.replace("reopen_shift_", ""))
    shift = db.get_shift_by_id(shift_id)
    if not shift:
        await callback.message.edit_text("Смена не найдена.", reply_markup=get_admin_menu_keyboard())
        await callback.answer()
        return

    if shift[3]:  # is_open
        await callback.message.edit_text("Эта смена уже открыта.", reply_markup=get_admin_menu_keyboard())
        await callback.answer()
        return

    db.reopen_shift(shift_id)
    await callback.message.edit_text(
        f"✅ Смена #{shift_id} переоткрыта.",
        reply_markup=get_admin_menu_keyboard()
    )
    await callback.answer()
    logger.info(f"Admin reopened shift #{shift_id}")


@router.callback_query(F.data.startswith("edit_shift_") & ~F.data.startswith("edit_shift_open_time_") & ~F.data.startswith("edit_shift_close_time_"))
async def cmd_edit_shift(callback: CallbackQuery):
    """Показать меню редактирования смены."""
    if not is_admin(callback.from_user.id):
        await callback.message.edit_text("⛔ Только админ.")
        await callback.answer()
        return

    shift_id = int(callback.data.replace("edit_shift_", ""))
    shift = db.get_shift_by_id(shift_id)
    if not shift:
        await callback.answer("Смена не найдена")
        return

    from src.keyboards import get_edit_shift_time_keyboard
    await callback.message.edit_text(
        f"📝 Редактирование смены #{shift_id}\n"
        f"Текущее время открытия: {shift[1]}\n"
        f"Текущее время закрытия: {shift[2] or 'не закрыта'}\n\n"
        "Выберите что редактировать:",
        reply_markup=get_edit_shift_time_keyboard(shift_id)
    )
    await callback.answer()


@router.callback_query(F.data.startswith("edit_shift_open_time_"))
async def cmd_edit_shift_open_time(callback: CallbackQuery, state: FSMContext):
    """Начать редактирование времени открытия смены."""
    if not is_admin(callback.from_user.id):
        await callback.message.edit_text("⛔ Только админ.")
        await callback.answer()
        return

    shift_id = int(callback.data.replace("edit_shift_open_time_", ""))
    await state.update_data(shift_id=shift_id)
    await callback.message.edit_text(
        "📝 Введите новое время открытия в формате:\n"
        "YYYY-MM-DD HH:MM:SS\n\n"
        "Пример: 2026-05-29 18:00:00"
    )
    await state.set_state(EditShift.waiting_open_time)
    await callback.answer()


@router.message(EditShift.waiting_open_time)
async def process_edit_shift_open_time(message: Message, state: FSMContext):
    """Обработать ввод нового времени открытия."""
    if not is_admin(message.from_user.id):
        await message.answer("⛔ Только админ может редактировать смены.")
        await state.clear()
        return

    new_time = message.text.strip()
    data = await state.get_data()
    shift_id = data.get("shift_id")

    # Проверяем формат времени
    try:
        from datetime import datetime
        datetime.strptime(new_time, "%Y-%m-%d %H:%M:%S")
    except ValueError:
        await message.answer(
            "❌ Неверный формат времени!\n\n"
            "Используйте формат: YYYY-MM-DD HH:MM:SS\n"
            "Пример: 2026-05-29 18:00:00"
        )
        return

    if db.update_shift_open_time(shift_id, new_time):
        await message.answer(
            f"✅ Время открытия смены #{shift_id} обновлено на: {new_time}",
            reply_markup=get_admin_menu_keyboard()
        )
        logger.info(f"Admin updated shift #{shift_id} open_time to {new_time}")
    else:
        await message.answer(
            "❌ Ошибка при обновлении времени.",
            reply_markup=get_admin_menu_keyboard()
        )

    await state.clear()


@router.callback_query(F.data.startswith("edit_shift_close_time_"))
async def cmd_edit_shift_close_time(callback: CallbackQuery, state: FSMContext):
    """Начать редактирование времени закрытия смены."""
    if not is_admin(callback.from_user.id):
        await callback.message.edit_text("⛔ Только админ.")
        await callback.answer()
        return

    shift_id = int(callback.data.replace("edit_shift_close_time_", ""))
    await state.update_data(shift_id=shift_id)
    await callback.message.edit_text(
        "📝 Введите новое время закрытия в формате:\n"
        "YYYY-MM-DD HH:MM:SS\n\n"
        "Пример: 2026-05-29 23:00:00"
    )
    await state.set_state(EditShift.waiting_close_time)
    await callback.answer()


@router.message(EditShift.waiting_close_time)
async def process_edit_shift_close_time(message: Message, state: FSMContext):
    """Обработать ввод нового времени закрытия."""
    if not is_admin(message.from_user.id):
        await message.answer("⛔ Только админ может редактировать смены.")
        await state.clear()
        return

    new_time = message.text.strip()
    data = await state.get_data()
    shift_id = data.get("shift_id")

    # Проверяем формат времени
    try:
        from datetime import datetime
        datetime.strptime(new_time, "%Y-%m-%d %H:%M:%S")
    except ValueError:
        await message.answer(
            "❌ Неверный формат времени!\n\n"
            "Используйте формат: YYYY-MM-DD HH:MM:SS\n"
            "Пример: 2026-05-29 23:00:00"
        )
        return

    if db.update_shift_close_time(shift_id, new_time):
        await message.answer(
            f"✅ Время закрытия смены #{shift_id} обновлено на: {new_time}",
            reply_markup=get_admin_menu_keyboard()
        )
        logger.info(f"Admin updated shift #{shift_id} close_time to {new_time}")
    else:
        await message.answer(
            "❌ Ошибка при обновлении времени.",
            reply_markup=get_admin_menu_keyboard()
        )

    await state.clear()



@router.callback_query(F.data == "admin_users")
async def cmd_admin_users(callback: CallbackQuery):
    """Обработчик просмотра пользователей и их ролей."""
    user_id = callback.from_user.id
    
    if not is_admin(user_id):
        await callback.message.edit_text(
            "❌ У вас нет доступа.",
            reply_markup=get_main_menu_keyboard(is_admin(user_id))
        )
        await callback.answer()
        return
    
    users = db.get_all_users()[:20]  # Последние 20 пользователей
    if not users:
        await callback.message.edit_text(
            "👤 Пользователи системы:\n\nНет пользователей.",
            reply_markup=get_admin_menu_keyboard()
        )
        await callback.answer()
        return

    from src.keyboards import get_admin_users_keyboard
    await callback.message.edit_text(
        "👤 Пользователи системы:\n\nВыберите пользователя для редактирования:",
        reply_markup=get_admin_users_keyboard(users)
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
        reply_markup=get_main_menu_keyboard(is_admin(callback.from_user.id))
    )
    await callback.answer()


@router.callback_query(F.data == "toggle_notifications")
async def cmd_toggle_notifications(callback: CallbackQuery):
    user_id = callback.from_user.id
    current = db.get_notification_status(user_id)
    db.set_notification_status(user_id, not current)
    await callback.message.edit_text(
        f"🔔 Уведомления {'включены' if not current else 'выключены'}.",
        reply_markup=get_profile_keyboard()
    )
    await callback.answer()


@router.callback_query(F.data == "admin_roles")
async def cmd_admin_roles(callback: CallbackQuery):
    """Обработчик управления глобальными ролями пользователей."""
    user_id = callback.from_user.id
    if not is_admin(user_id):
        await callback.message.edit_text("⛔ Только админ может управлять ролями.")
        await callback.answer()
        return

    users = db.get_all_users()
    if not users:
        await callback.message.edit_text(
            "Нет пользователей в системе.",
            reply_markup=get_admin_menu_keyboard()
        )
        await callback.answer()
        return

    from src.keyboards import get_admin_users_keyboard
    await callback.message.edit_text(
        "👥 Выберите пользователя для назначения глобальной роли:",
        reply_markup=get_admin_users_keyboard(users)
    )
    await callback.answer()


@router.callback_query(F.data.startswith("admin_user_") & ~F.data.startswith("admin_user_role_"))
async def cmd_admin_user_select(callback: CallbackQuery):
    """Обработчик выбора пользователя для просмотра деталей."""
    if not is_admin(callback.from_user.id):
        await callback.message.edit_text("⛔ Только админ может управлять ролями.")
        await callback.answer()
        return

    target_user_id = callback.data.replace("admin_user_", "")
    if not target_user_id.isdigit():
        await callback.answer("Ошибка данных")
        return

    target_user_id = int(target_user_id)
    profile = db.get_user_profile(target_user_id)
    if not profile:
        await callback.answer("Пользователь не найден")
        return

    current_role = profile[3] or "member"
    display_name = profile[2] or profile[1] or f"User {target_user_id}"

    from src.keyboards import get_admin_user_detail_keyboard
    await callback.message.edit_text(
        f"👤 {display_name}\n"
        f"Текущая роль: {ROLE_LABELS.get(current_role, current_role)}\n\n"
        "Выберите действие:",
        reply_markup=get_admin_user_detail_keyboard(target_user_id)
    )
    await callback.answer()


@router.callback_query(F.data.startswith("admin_set_role_"))
async def cmd_admin_set_role(callback: CallbackQuery):
    """Обработчик установки глобальной роли пользователю."""
    if not is_admin(callback.from_user.id):
        await callback.message.edit_text("⛔ Только админ может управлять ролями.")
        await callback.answer()
        return

    # Формат: admin_set_role_{user_id}_{role}
    # Нужно правильно разбить, так как role может содержать underscores (hookah_master)
    valid_roles = ["member", "manager", "hookah_master", "supervisor"]
    data_str = callback.data.replace("admin_set_role_", "")

    new_role = None
    user_id_str = data_str
    
    # Проверяем с конца, какая роль совпадает
    for role in valid_roles:
        if data_str.endswith("_" + role):
            new_role = role
            user_id_str = data_str[: - len("_" + role)]
            break

    if new_role is None or not user_id_str.isdigit():
        await callback.answer("Ошибка данных")
        return

    try:
        target_user_id = int(user_id_str)
    except ValueError:
        await callback.answer("Ошибка при обработке ID пользователя")
        return

    db.set_user_global_role(target_user_id, new_role)
    display_name = db.get_user_display_name(target_user_id)

    await callback.message.edit_text(
        f"✅ Роль пользователя {display_name} изменена на: {ROLE_LABELS.get(new_role, new_role)}",
        reply_markup=get_admin_menu_keyboard()
    )
    await callback.answer()
    logger.info(f"Admin set global role for user {target_user_id} to {new_role}")


@router.callback_query(F.data.startswith("admin_user_role_"))
async def cmd_admin_user_role(callback: CallbackQuery):
    """Обработчик открытия меню выбора роли для пользователя."""
    if not is_admin(callback.from_user.id):
        await callback.message.edit_text("⛔ Только админ может управлять ролями.")
        await callback.answer()
        return

    user_id_str = callback.data.replace("admin_user_role_", "")
    if not user_id_str.isdigit():
        await callback.answer("Ошибка данных")
        return

    target_user_id = int(user_id_str)
    profile = db.get_user_profile(target_user_id)
    if not profile:
        await callback.answer("Пользователь не найден")
        return

    current_role = profile[3] or "member"
    display_name = profile[2] or profile[1] or f"User {target_user_id}"

    from src.keyboards import get_admin_user_role_keyboard
    await callback.message.edit_text(
        f"👤 {display_name}\n"
        f"Текущая роль: {ROLE_LABELS.get(current_role, current_role)}\n\n"
        "Выберите новую глобальную роль:",
        reply_markup=get_admin_user_role_keyboard(target_user_id, current_role)
    )
    await callback.answer()


@router.callback_query(F.data.startswith("admin_edit_user_name_"))
async def cmd_admin_edit_user_name(callback: CallbackQuery, state: FSMContext):
    """Начало редактирования отображаемого имени пользователя."""
    if not is_admin(callback.from_user.id):
        await callback.message.edit_text("⛔ Только админ может редактировать пользователя.")
        await callback.answer()
        return

    user_id = int(callback.data.replace("admin_edit_user_name_", ""))
    await state.update_data(target_user_id=user_id)
    await callback.message.edit_text(
        "📝 Введите новое отображаемое имя для пользователя:" 
    )
    await state.set_state(EditUser.waiting_display_name)
    await callback.answer()


@router.message(EditUser.waiting_display_name)
async def process_admin_edit_user_name(message: Message, state: FSMContext):
    """Обработка нового отображаемого имени пользователя."""
    if not is_admin(message.from_user.id):
        await message.answer("⛔ Только админ может редактировать пользователя.")
        await state.clear()
        return

    data = await state.get_data()
    target_user_id = data.get("target_user_id")
    if not target_user_id:
        await message.answer("❌ Ошибка: пользователь не определен.")
        await state.clear()
        return

    new_name = message.text.strip()
    db.set_user_display_name(target_user_id, new_name)
    display_name = db.get_user_display_name(target_user_id)

    await message.answer(
        f"✅ Имя пользователя обновлено на: {display_name}",
        reply_markup=get_admin_menu_keyboard()
    )
    await state.clear()


@router.callback_query(F.data == "assign_role_help")
async def cmd_assign_role_help(callback: CallbackQuery):
    await callback.message.edit_text(
        "🧩 Назначить роль можно через Админ панель → Роли.\n\n"
        "Глобальные роли определяют права пользователя на все смены:\n"
        "• Менеджер — может редактировать кальяны\n"
        "• Кальянный мастер — может добавлять кальяны\n"
        "• Управляющий — расширенный доступ\n"
        "• Участник — базовый просмотр",
        reply_markup=get_admin_menu_keyboard()
    )
    await callback.answer()
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
        text += f"🔥 Крепость: {strength}/10\n"
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
    await notify_hookah_ready(callback.bot, hookah_id)
    try:
        await callback.message.delete()
    except Exception:
        # Если сообщение не получилось удалить, обновляем текст, чтобы не оставлять кнопку активной.
        await callback.message.edit_text(
            f"✅ Кальян #{hookah_id} помечен как готовый к выдаче."
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


@router.callback_query(F.data.startswith("edit_strength_"))
async def cmd_edit_strength(callback: CallbackQuery, state: FSMContext):
    """Обработчик начала редактирования силы кальяна."""
    hookah_id = int(callback.data.replace("edit_strength_", ""))
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
        "🔥 Выберите силу кальяна (1-10):",
        reply_markup=get_strength_keyboard()
    )
    await state.set_state(EditHookah.waiting_type)  # Переиспользуем waiting_type для простоты
    await callback.answer()


@router.callback_query(F.data.startswith("edit_coldness_"))
async def cmd_edit_coldness(callback: CallbackQuery, state: FSMContext):
    """Обработчик начала редактирования холодности кальяна."""
    hookah_id = int(callback.data.replace("edit_coldness_", ""))
    hookah = db.get_hookah_by_id(hookah_id)
    if not hookah:
        await callback.answer("❌ Кальян не найден")
        return

    role = get_user_role(hookah[1], callback.from_user.id)
    if not is_manager_or_admin(role):
        await callback.message.edit_text("⛔ У вас нет прав редактировать кальяны.")
        await callback.answer()
        return

    await state.update_data(hookah_id=hookah_id, edit_type="coldness")
    await callback.message.edit_text(
        "❄️ Выберите степень холодности:",
        reply_markup=get_coldness_keyboard()
    )
    await state.set_state(EditHookah.waiting_table)  # Переиспользуем waiting_table для простоты
    await callback.answer()


@router.callback_query(F.data.startswith("edit_comment_"))
async def cmd_edit_comment(callback: CallbackQuery, state: FSMContext):
    """Обработчик начала редактирования комментария кальяна."""
    hookah_id = int(callback.data.replace("edit_comment_", ""))
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
        "💬 Введите новый комментарий к кальяну или отправьте 'нет' для удаления комментария:"
    )
    await state.set_state(AddHookah.waiting_comment)  # Переиспользуем для ввода комментария
    await callback.answer()


# Обработчик для изменения силы при редактировании (через FSM)
@router.callback_query(EditHookah.waiting_type, F.data.startswith("strength_"))
async def process_edit_strength(callback: CallbackQuery, state: FSMContext):
    """Обработчик сохранения новой силы кальяна."""
    strength = int(callback.data.replace("strength_", ""))
    data = await state.get_data()
    hookah_id = data.get("hookah_id")
    
    db.update_hookah_strength_and_coldness(
        hookah_id,
        strength=strength,
        updated_by=callback.from_user.id
    )
    
    await callback.message.edit_text(
        f"✅ Крепость кальяна успешно изменена на: {strength}/10",
        reply_markup=get_hookah_actions_keyboard(db.get_hookah_by_id(hookah_id), get_user_role(db.get_hookah_by_id(hookah_id)[1], callback.from_user.id))
    )
    await state.clear()
    await callback.answer()
    logger.info(f"Кальян #{hookah_id}: сила изменена на {strength}")


# Обработчик для изменения холодности при редактировании (через FSM)
@router.callback_query(EditHookah.waiting_table, F.data.startswith("coldness_"))
async def process_edit_coldness(callback: CallbackQuery, state: FSMContext):
    """Обработчик сохранения новой холодности кальяна."""
    coldness = callback.data.replace("coldness_", "")
    data = await state.get_data()
    hookah_id = data.get("hookah_id")
    
    db.update_hookah_strength_and_coldness(
        hookah_id,
        coldness=coldness,
        updated_by=callback.from_user.id
    )
    
    await callback.message.edit_text(
        f"✅ Холодность кальяна успешно изменена на: {coldness}",
        reply_markup=get_hookah_actions_keyboard(db.get_hookah_by_id(hookah_id), get_user_role(db.get_hookah_by_id(hookah_id)[1], callback.from_user.id))
    )
    await state.clear()
    await callback.answer()
    logger.info(f"Кальян #{hookah_id}: холодность изменена на {coldness}")



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
        reply_markup=get_main_menu_keyboard(is_admin(callback.from_user.id))
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
        reply_markup=get_main_menu_keyboard(is_admin(callback.from_user.id))
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
                reply_markup=get_main_menu_keyboard(is_admin(callback.from_user.id))
            )
    
    await callback.answer()