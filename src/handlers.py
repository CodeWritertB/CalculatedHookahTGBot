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

from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.filters import Command

import src.database as db
from src.keyboards import (
    get_main_menu_keyboard,
    get_hookah_type_keyboard,
    get_tables_keyboard,
    get_hookahs_list_keyboard,
    get_hookah_actions_keyboard,
    get_history_keyboard,
    get_confirm_close_keyboard
)

# Настройка логирования для этого модуля
logger = logging.getLogger(__name__)

# Главный маршрутизатор для регистрации всех обработчиков
router = Router()


# ==================== FSM STATES (Состояния диалога) ====================

class AddHookah(StatesGroup):
    """Состояния для добавления нового кальяна"""
    waiting_type = State()   # Ожидание выбора типа кальяна
    waiting_table = State()  # Ожидание выбора стола


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
    
    await message.answer(
        "🍃 Добро пожаловать в бот учета кальянов!\n\n"
        "Это приложение поможет вам вести учет всех кальянов за смену.\n\n"
        "Выберите действие:",
        reply_markup=get_main_menu_keyboard(is_open)
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
        reply_markup=get_main_menu_keyboard(True)
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
        reply_markup=get_main_menu_keyboard(False)
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
    
    # Получаем текущую смену и добавляем кальян
    shift = get_current_shift()
    if shift:
        db.add_hookah(shift[0], hookah_type, table)
        now = datetime.now().strftime("%H:%M:%S")
        
        await callback.message.edit_text(
            f"✅ Кальян успешно добавлен!\n\n"
            f"🌿 Тип: {hookah_type}\n"
            f"📍 Стол: {table}\n"
            f"⏰ Время: {now}\n\n"
            "Выберите действие:",
            reply_markup=get_main_menu_keyboard(True)
        )
        logger.info(f"Кальян добавлен: {hookah_type} на стол {table}")
    
    # Очищаем состояние FSM
    await state.clear()
    await callback.answer()


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
    
    # Проверяем принадлежность пользователя к смене (manager или member)
    role = db.get_shift_user_role(shift[0], callback.from_user.id)
    if not role:
        await callback.message.edit_text(
            "⛔ Вы не участвуете в текущей смене. Вступите в смену, чтобы видеть список кальянов."
        )
        await callback.answer()
        return

    # Получаем кальяны за смену
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
        time = h[4][11:]  # Извлекаем время (HH:MM:SS)
        text += f"• {h[3]} - {h[2]} (⏰ {time})\n"
    
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
        reply_markup=get_main_menu_keyboard(True)
    )
    await callback.answer()
    logger.info(f"User {user_id} joined shift #{shift[0]} as member")


@router.callback_query(F.data == "take_manager")
async def cmd_take_manager(callback: CallbackQuery):
    """Handler для назначения пользователя менеджером текущей смены."""
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
        reply_markup=get_main_menu_keyboard(True)
    )
    await callback.answer()
    logger.info(f"User {user_id} assigned as manager for shift #{shift[0]}")


@router.callback_query(F.data.startswith("view_"))
async def cmd_view_hookah(callback: CallbackQuery):
    """
    Обработчик просмотра деталей конкретного кальяна.
    
    Выводит подробную информацию о кальяне и меню для редактирования.
    
    Args:
        callback (CallbackQuery): Callback с ID кальяна
    """
    # Извлекаем ID из callback_data
    hookah_id = int(callback.data.replace("view_", ""))
    
    # Получаем данные кальяна
    hookah = db.get_hookah_by_id(hookah_id)
    
    # Проверка: кальян найден
    if not hookah:
        await callback.answer("❌ Кальян не найден")
        return
    
    # Форматируем информацию
    text = (
        f"🍃 Кальян #{hookah[0]}\n"
        f"🌿 Тип: {hookah[2]}\n"
        f"📍 Стол: {hookah[3]}\n"
        f"⏰ Добавлен: {hookah[4]}"
    )
    
    await callback.message.edit_text(
        text,
        reply_markup=get_hookah_actions_keyboard(hookah_id)
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
    # Извлекаем ID кальяна
    hookah_id = int(callback.data.replace("edit_type_", ""))
    
    # Сохраняем ID в состояние
    await state.update_data(hookah_id=hookah_id)
    
    # Показываем меню выбора типа
    await callback.message.edit_text(
        "🌿 Выберите новый тип кальяна:",
        reply_markup=get_hookah_type_keyboard()
    )
    await state.set_state(EditHookah.waiting_type)
    await callback.answer()


@router.callback_query(EditHookah.waiting_type, F.data.startswith("type_"))
async def process_edit_type(callback: CallbackQuery, state: FSMContext):
    """
    Обработчик сохранения нового типа кальяна (FSM шаг).
    
    Args:
        callback (CallbackQuery): Callback с новым типом
        state (FSMContext): Контекст состояния FSM
    """
    # Извлекаем новый тип
    hookah_type = callback.data.replace("type_", "")
    
    # Получаем ID из состояния
    data = await state.get_data()
    hookah_id = data.get("hookah_id")
    
    # Обновляем в БД
    db.update_hookah(hookah_id, hookah_type=hookah_type)
    
    await callback.message.edit_text(
        f"✅ Тип успешно изменен на: {hookah_type}",
        reply_markup=get_hookah_actions_keyboard(hookah_id)
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
    # Извлекаем ID кальяна
    hookah_id = int(callback.data.replace("edit_table_", ""))
    
    # Сохраняем ID в состояние
    await state.update_data(hookah_id=hookah_id)
    
    # Показываем меню выбора стола
    await callback.message.edit_text(
        "📍 Выберите новый стол:",
        reply_markup=get_tables_keyboard()
    )
    await state.set_state(EditHookah.waiting_table)
    await callback.answer()


@router.callback_query(EditHookah.waiting_table, F.data.startswith("table_"))
async def process_edit_table(callback: CallbackQuery, state: FSMContext):
    """
    Обработчик сохранения нового стола кальяна (FSM шаг).
    
    Args:
        callback (CallbackQuery): Callback с новым столом
        state (FSMContext): Контекст состояния FSM
    """
    # Извлекаем новый стол
    table = callback.data.replace("table_", "")
    
    # Получаем ID из состояния
    data = await state.get_data()
    hookah_id = data.get("hookah_id")
    
    # Обновляем в БД
    db.update_hookah(hookah_id, table_name=table)
    
    await callback.message.edit_text(
        f"✅ Стол успешно изменен на: {table}",
        reply_markup=get_hookah_actions_keyboard(hookah_id)
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
    # Извлекаем ID кальяна
    hookah_id = int(callback.data.replace("delete_", ""))
    
    # Удаляем из БД
    db.delete_hookah(hookah_id)
    
    # Определяем текущий статус смены
    shift = get_current_shift()
    is_shift_open = shift is not None
    
    await callback.message.edit_text(
        f"✅ Кальян #{hookah_id} успешно удален.\n\n"
        "Выберите действие:",
        reply_markup=get_main_menu_keyboard(is_shift_open)
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
        reply_markup=get_main_menu_keyboard(get_current_shift() is not None)
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
        reply_markup=get_main_menu_keyboard(is_open)
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
                reply_markup=get_main_menu_keyboard(True)
            )
    
    await callback.answer()