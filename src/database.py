"""
Database module for Hookah Shift Management Bot

Модуль для работы с SQLite базой данных бота. Содержит функции для
управления сменами и кальянами.

Таблицы:
    - shifts: Информация о рабочих сменах (открыто/закрыто, время, количество)
    - hookahs: Информация о кальянах (тип, стол, время добавления)

Author: Hookah Bot Team
License: MIT
"""

import sqlite3
from datetime import datetime, timedelta, timezone
from typing import Optional, List, Tuple

# Путь к файлу базы данных SQLite
DB_PATH = "hookah_bot.db"

# Временная зона Москвы UTC+3
MOSCOW_TZ = timezone(timedelta(hours=3))


def get_connection() -> sqlite3.Connection:
    """
    Получить соединение с базой данных SQLite.
    
    Returns:
        sqlite3.Connection: Объект соединения с БД
    """
    return sqlite3.connect(DB_PATH)


def get_moscow_datetime() -> datetime:
    """Возвращает текущее московское время."""
    return datetime.now(MOSCOW_TZ)


def get_moscow_now_str(fmt: str = "%Y-%m-%d %H:%M:%S") -> str:
    """Возвращает текущее московское время в формате строки."""
    return get_moscow_datetime().strftime(fmt)


def init_db() -> None:
    """
    Инициализация базы данных.
    
    Создает таблицы shifts и hookahs если их еще нет.
    Безопасно вызывать несколько раз - существующие таблицы не будут перезаписаны.
    
    Таблица shifts:
        - id: Уникальный ID смены
        - open_time: Время открытия смены (YYYY-MM-DD HH:MM:SS)
        - close_time: Время закрытия смены (NULL если открыта)
        - is_open: Статус смены (1 = открыта, 0 = закрыта)
        - total_hookahs: Общее количество кальянов в смене
    
    Таблица hookahs:
        - id: Уникальный ID кальяна
        - shift_id: ID смены (внешний ключ)
        - hookah_type: Тип кальяна ("Стандарт" или "Сигара")
        - table_name: Название стола
        - created_at: Время добавления кальяна (YYYY-MM-DD HH:MM:SS)
        - status: Статус заказа (new_order, in_packing, ready_for_guest)
        - strength: Сила кальяна (1-10)
        - coldness: Холодность кальяна
        - order_comment: Комментарий к заказу
    """
    conn = get_connection()
    cursor = conn.cursor()
    
    # Создание таблицы смен
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS shifts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            open_time TEXT NOT NULL,
            close_time TEXT,
            is_open INTEGER DEFAULT 1,
            total_hookahs INTEGER DEFAULT 0
        )
    ''')
    
    # Создание таблицы кальянов
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS hookahs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            shift_id INTEGER NOT NULL,
            hookah_type TEXT NOT NULL,
            table_name TEXT NOT NULL,
            created_at TEXT NOT NULL,
            FOREIGN KEY (shift_id) REFERENCES shifts(id)
        )
    ''')

    # Таблица пользователей (Telegram user_id, username и т.д.)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            username TEXT,
            created_at TEXT NOT NULL
        )
    ''')

    # Таблица участников смены: кто в смене и какая роль
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS shift_members (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            shift_id INTEGER NOT NULL,
            user_id INTEGER NOT NULL,
            role TEXT NOT NULL,
            joined_at TEXT NOT NULL,
            FOREIGN KEY (shift_id) REFERENCES shifts(id),
            FOREIGN KEY (user_id) REFERENCES users(user_id)
        )
    ''')

    # Таблица журнала событий кальянов
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS hookah_events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            hookah_id INTEGER NOT NULL,
            event_type TEXT NOT NULL,
            user_id INTEGER,
            event_time TEXT NOT NULL,
            comment TEXT,
            FOREIGN KEY (hookah_id) REFERENCES hookahs(id),
            FOREIGN KEY (user_id) REFERENCES users(user_id)
        )
    ''')

    conn.commit()

    # Дополняем таблицу hookahs новыми полями, если они отсутствуют
    add_column_if_not_exists(conn, 'hookahs', 'status TEXT DEFAULT "new_order"')
    add_column_if_not_exists(conn, 'hookahs', 'created_by INTEGER')
    add_column_if_not_exists(conn, 'hookahs', 'accepted_by INTEGER')
    add_column_if_not_exists(conn, 'hookahs', 'accepted_at TEXT')
    add_column_if_not_exists(conn, 'hookahs', 'ready_at TEXT')
    add_column_if_not_exists(conn, 'hookahs', 'last_updated_at TEXT')
    add_column_if_not_exists(conn, 'hookahs', 'last_updated_by INTEGER')
    add_column_if_not_exists(conn, 'hookahs', 'strength INTEGER DEFAULT 5')
    add_column_if_not_exists(conn, 'hookahs', 'coldness TEXT DEFAULT "Средний"')
    add_column_if_not_exists(conn, 'hookahs', 'order_comment TEXT')

    # Дополняем таблицу users полем для уведомлений
    add_column_if_not_exists(conn, 'users', 'notifications_enabled INTEGER DEFAULT 1')
    add_column_if_not_exists(conn, 'users', 'display_name TEXT')
    add_column_if_not_exists(conn, 'users', 'global_role TEXT DEFAULT "member"')

    conn.commit()
    conn.close()


# ==================== ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ ДЛЯ БАЗЫ ДАННЫХ ====================

def add_column_if_not_exists(conn: sqlite3.Connection, table: str, definition: str) -> None:
    cursor = conn.cursor()
    column_name = definition.split()[0]
    cursor.execute(f"PRAGMA table_info({table})")
    columns = [row[1] for row in cursor.fetchall()]
    if column_name not in columns:
        cursor.execute(f"ALTER TABLE {table} ADD COLUMN {definition}")


def log_hookah_event(hookah_id: int, event_type: str, user_id: int = None, comment: str = None) -> None:
    conn = get_connection()
    cursor = conn.cursor()
    now = get_moscow_now_str("%Y-%m-%d %H:%M:%S")
    cursor.execute(
        "INSERT INTO hookah_events (hookah_id, event_type, user_id, event_time, comment) VALUES (?, ?, ?, ?, ?)",
        (hookah_id, event_type, user_id, now, comment)
    )
    conn.commit()
    conn.close()


def get_hookah_events(hookah_id: int) -> List[Tuple]:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT he.event_type, u.username, he.event_time, he.comment"
        " FROM hookah_events he"
        " LEFT JOIN users u ON he.user_id = u.user_id"
        " WHERE he.hookah_id = ?"
        " ORDER BY he.event_time ASC",
        (hookah_id,)
    )
    events = cursor.fetchall()
    conn.close()
    return events


def get_users_with_notifications_enabled() -> List[int]:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT user_id FROM users WHERE notifications_enabled = 1"
    )
    rows = [row[0] for row in cursor.fetchall()]
    conn.close()
    return rows


def get_notification_status(user_id: int) -> bool:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT notifications_enabled FROM users WHERE user_id = ?",
        (user_id,)
    )
    row = cursor.fetchone()
    conn.close()
    return bool(row[0]) if row else True


def set_notification_status(user_id: int, enabled: bool) -> None:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "UPDATE users SET notifications_enabled = ? WHERE user_id = ?",
        (1 if enabled else 0, user_id)
    )
    conn.commit()
    conn.close()


def get_user_hookah_stats(user_id: int) -> Tuple[int, int, int]:
    """Получить статистику кальянов по пользователю."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT COUNT(*) FROM hookahs WHERE created_by = ?",
        (user_id,)
    )
    total = cursor.fetchone()[0] or 0
    cursor.execute(
        "SELECT hookah_type, COUNT(*) FROM hookahs WHERE created_by = ? GROUP BY hookah_type",
        (user_id,)
    )
    counts = {row[0]: row[1] for row in cursor.fetchall()}
    conn.close()
    standard = counts.get('Стандарт', 0)
    cigar = counts.get('Сигара', 0)
    return total, standard, cigar


def get_user_shift_stats(user_id: int) -> Tuple[int, int]:
    """Получить количество смен пользователя всего и за текущий месяц."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT COUNT(DISTINCT shift_id) FROM shift_members WHERE user_id = ?",
        (user_id,)
    )
    total_shifts = cursor.fetchone()[0] or 0
    month_key = get_moscow_datetime().strftime('%Y-%m')
    cursor.execute(
        "SELECT COUNT(DISTINCT sm.shift_id) "
        "FROM shift_members sm "
        "JOIN shifts s ON sm.shift_id = s.id "
        "WHERE sm.user_id = ? AND substr(s.open_time, 1, 7) = ?",
        (user_id, month_key)
    )
    month_shifts = cursor.fetchone()[0] or 0
    conn.close()
    return total_shifts, month_shifts


def get_user_master_hookah_stats(user_id: int) -> Tuple[int, int, int, int]:
    """Получить статистику кальянов для кальянного мастера."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT COUNT(h.id) FROM hookahs h "
        "JOIN shift_members sm ON h.shift_id = sm.shift_id "
        "WHERE sm.user_id = ? AND sm.role = 'hookah_master'",
        (user_id,)
    )
    your_shift_hookahs = cursor.fetchone()[0] or 0
    cursor.execute(
        "SELECT h.hookah_type, COUNT(*) FROM hookahs h "
        "JOIN shift_members sm ON h.shift_id = sm.shift_id "
        "WHERE sm.user_id = ? AND sm.role = 'hookah_master' "
        "GROUP BY h.hookah_type",
        (user_id,)
    )
    counts = {row[0]: row[1] for row in cursor.fetchall()}
    standard = counts.get('Стандарт', 0)
    cigar = counts.get('Сигара', 0)
    cursor.execute("SELECT COUNT(*) FROM hookahs")
    total_hookahs = cursor.fetchone()[0] or 0
    conn.close()
    return your_shift_hookahs, standard, cigar, total_hookahs


# ==================== ФУНКЦИИ ДЛЯ УПРАВЛЕНИЯ СМЕНАМИ ====================

def get_current_shift() -> Optional[Tuple]:
    """
    Получить текущую открытую смену.
    
    Returns:
        Optional[Tuple]: Кортеж с данными смены или None если нет открытой смены
        
    Структура кортежа: (id, open_time, close_time, is_open, total_hookahs)
    """
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM shifts WHERE is_open = 1 LIMIT 1")
    shift = cursor.fetchone()
    conn.close()
    return shift


def open_shift() -> int:
    """
    Открыть новую смену.
    
    Создает новую запись в таблице shifts с текущей датой и временем.
    Обычно вызывается один раз в начале рабочего дня.
    
    Returns:
        int: ID созданной смены
        
    Example:
        shift_id = open_shift()  # Возвращает например 5
    """
    conn = get_connection()
    cursor = conn.cursor()
    # Получаем текущее время в формате YYYY-MM-DD HH:MM:SS (МСК)
    now = get_moscow_now_str("%Y-%m-%d %H:%M:%S")
    
    # Вставляем новую смену со статусом "открыта"
    cursor.execute(
        "INSERT INTO shifts (open_time, is_open) VALUES (?, 1)",
        (now,)
    )
    shift_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return shift_id


def close_shift(shift_id: int) -> None:
    """
    Закрыть смену и подсчитать общее количество кальянов.
    
    Args:
        shift_id (int): ID смены для закрытия
        
    Процесс:
        1. Подсчитывает количество кальянов за смену
        2. Устанавливает время закрытия
        3. Изменяет статус на закрыто (is_open = 0)
        4. Сохраняет общее количество кальянов
    """
    conn = get_connection()
    cursor = conn.cursor()
    
    # Получаем текущее время для записи времени закрытия (МСК)
    now = get_moscow_now_str("%Y-%m-%d %H:%M:%S")
    
    # Подсчитываем количество кальянов за смену
    cursor.execute(
        "SELECT COUNT(*) FROM hookahs WHERE shift_id = ?",
        (shift_id,)
    )
    total = cursor.fetchone()[0]
    
    # Обновляем информацию о смене
    cursor.execute(
        "UPDATE shifts SET close_time = ?, is_open = 0, total_hookahs = ? WHERE id = ?",
        (now, total, shift_id)
    )
    conn.commit()
    conn.close()


def get_shift_by_id(shift_id: int) -> Optional[Tuple]:
    """
    Получить информацию о смене по ID.
    
    Args:
        shift_id (int): ID смены
        
    Returns:
        Optional[Tuple]: Кортеж с данными смены или None если не найдена
        
    Структура кортежа: (id, open_time, close_time, is_open, total_hookahs)
    """
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM shifts WHERE id = ?", (shift_id,))
    shift = cursor.fetchone()
    conn.close()
    return shift


def get_all_shifts() -> List[Tuple]:
    """
    Получить все смены (в обратном хронологическом порядке).
    
    Используется для отображения истории смен. Самые новые смены в начале.
    
    Returns:
        List[Tuple]: Список кортежей с данными всех смен
        
    Структура каждого кортежа: (id, open_time, close_time, is_open, total_hookahs)
    """
    conn = get_connection()
    cursor = conn.cursor()
    # Сортируем по времени открытия в обратном порядке (новые сверху)
    cursor.execute("SELECT * FROM shifts ORDER BY open_time DESC")
    shifts = cursor.fetchall()
    conn.close()
    return shifts


# ==================== ФУНКЦИИ ДЛЯ УПРАВЛЕНИЯ КАЛЬЯНАМИ ====================

def add_hookah(
    shift_id: int,
    hookah_type: str,
    table_name: str,
    strength: int = 5,
    coldness: str = "Средний",
    order_comment: str = None,
    created_by: int = None
) -> int:
    """
    Добавить кальян в текущую смену.
    
    Args:
        shift_id (int): ID смены
        hookah_type (str): Тип кальяна ("Стандарт" или "Сигара")
        table_name (str): Название стола
        strength (int): Сила кальяна от 1 до 10
        coldness (str): Холодность кальяна
        order_comment (str): Комментарий для заказа
        created_by (int): user_id того, кто добавил кальян
        
    Returns:
        int: ID созданного кальяна
    """
    conn = get_connection()
    cursor = conn.cursor()
    now = get_moscow_now_str("%Y-%m-%d %H:%M:%S")
    cursor.execute(
        "INSERT INTO hookahs (shift_id, hookah_type, table_name, created_at, status, created_by, last_updated_at, last_updated_by, strength, coldness, order_comment) VALUES (?, ?, ?, ?, 'new_order', ?, ?, ?, ?, ?, ?)",
        (shift_id, hookah_type, table_name, now, created_by, now, created_by, strength, coldness, order_comment)
    )
    hookah_id = cursor.lastrowid
    conn.commit()
    conn.close()
    comment = f"Сила {strength}, Холодность {coldness}"
    if order_comment:
        comment += f", Комментарий: {order_comment}"
    log_hookah_event(hookah_id, 'created', created_by, f"Добавлен кальян {hookah_type} на стол {table_name}. {comment}")
    return hookah_id


def get_hookah_by_id(hookah_id: int) -> Optional[Tuple]:
    """Получить информацию о кальяне по ID."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM hookahs WHERE id = ?", (hookah_id,))
    hookah = cursor.fetchone()
    conn.close()
    return hookah


def get_hookahs_by_shift(shift_id: int) -> List[Tuple]:
    """Получить все кальяны за конкретную смену."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT * FROM hookahs WHERE shift_id = ? ORDER BY created_at ASC",
        (shift_id,)
    )
    hookahs = cursor.fetchall()
    conn.close()
    return hookahs


def update_hookah(
    hookah_id: int,
    hookah_type: Optional[str] = None,
    table_name: Optional[str] = None,
    updated_by: int = None
) -> None:
    """Обновить данные кальяна и записать событие."""
    conn = get_connection()
    cursor = conn.cursor()
    now = get_moscow_now_str("%Y-%m-%d %H:%M:%S")
    if hookah_type is not None:
        cursor.execute(
            "UPDATE hookahs SET hookah_type = ?, last_updated_at = ?, last_updated_by = ? WHERE id = ?",
            (hookah_type, now, updated_by, hookah_id)
        )
        log_hookah_event(hookah_id, 'updated_type', updated_by, f"Изменен тип на {hookah_type}")
    if table_name is not None:
        cursor.execute(
            "UPDATE hookahs SET table_name = ?, last_updated_at = ?, last_updated_by = ? WHERE id = ?",
            (table_name, now, updated_by, hookah_id)
        )
        log_hookah_event(hookah_id, 'updated_table', updated_by, f"Изменен стол на {table_name}")
    conn.commit()
    conn.close()


def delete_hookah(hookah_id: int, deleted_by: int = None) -> None:
    """Удалить кальян из базы данных."""
    log_hookah_event(hookah_id, 'deleted', deleted_by, 'Кальян удален')
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM hookahs WHERE id = ?", (hookah_id,))
    conn.commit()
    conn.close()


def delete_shift(shift_id: int) -> None:
    """Удалить смену и все связанные данные из базы данных."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM hookah_events WHERE hookah_id IN (SELECT id FROM hookahs WHERE shift_id = ?)", (shift_id,))
    cursor.execute("DELETE FROM hookahs WHERE shift_id = ?", (shift_id,))
    cursor.execute("DELETE FROM shift_members WHERE shift_id = ?", (shift_id,))
    cursor.execute("DELETE FROM shifts WHERE id = ?", (shift_id,))
    conn.commit()
    conn.close()


def set_hookah_status(hookah_id: int, status: str, user_id: int = None) -> None:
    """Установить статус кальяна и записать событие."""
    status_fields = {
        'accepted': ("status = 'in_packing', accepted_by = ?, accepted_at = ?, last_updated_at = ?, last_updated_by = ?", ['accepted_by', 'accepted_at', 'last_updated_at', 'last_updated_by']),
        'ready': ("status = 'ready_for_guest', ready_at = ?, last_updated_at = ?, last_updated_by = ?", ['ready_at', 'last_updated_at', 'last_updated_by']),
    }
    now = get_moscow_now_str("%Y-%m-%d %H:%M:%S")
    conn = get_connection()
    cursor = conn.cursor()
    if status == 'accepted':
        cursor.execute(
            "UPDATE hookahs SET status = 'in_packing', accepted_by = ?, accepted_at = ?, last_updated_at = ?, last_updated_by = ? WHERE id = ?",
            (user_id, now, now, user_id, hookah_id)
        )
        log_hookah_event(hookah_id, 'accepted', user_id, 'Кальян принят мастером')
    elif status == 'ready':
        cursor.execute(
            "UPDATE hookahs SET status = 'ready_for_guest', ready_at = ?, last_updated_at = ?, last_updated_by = ? WHERE id = ?",
            (now, now, user_id, hookah_id)
        )
        log_hookah_event(hookah_id, 'ready', user_id, 'Кальян готов к выдаче')
    conn.commit()
    conn.close()


# ==================== ФУНКЦИИ ДЛЯ УПРАВЛЕНИЯ ПОЛЬЗОВАТЕЛЯМИ И СМЕНАМИ ====================

def add_user_if_not_exists(user_id: int, username: str = None) -> None:
    """Добавить пользователя в таблицу users если его там нет."""
    conn = get_connection()
    cursor = conn.cursor()
    now = get_moscow_now_str("%Y-%m-%d %H:%M:%S")
    cursor.execute(
        "INSERT OR IGNORE INTO users (user_id, username, created_at, notifications_enabled) VALUES (?, ?, ?, 1)",
        (user_id, username, now)
    )
    # Обновляем username если изменился
    if username:
        cursor.execute("UPDATE users SET username = ? WHERE user_id = ?", (username, user_id))
    conn.commit()
    conn.close()


def assign_user_to_shift(shift_id: int, user_id: int, role: str) -> Tuple[bool, str]:
    """Назначить пользователя в смену с указанной ролью.

    Допустимые роли:
        - manager
        - member
        - hookah_master
        - supervisor
    Возвращает (True, msg) при успехе или (False, error_message) при ошибке.
    """
    valid_roles = {'manager', 'member', 'hookah_master', 'supervisor'}
    if role not in valid_roles:
        return False, "Недопустимая роль. Доступны: manager, member, hookah_master, supervisor"

    conn = get_connection()
    cursor = conn.cursor()

    # Проверяем существование смены
    cursor.execute("SELECT id FROM shifts WHERE id = ? AND is_open = 1", (shift_id,))
    if not cursor.fetchone():
        conn.close()
        return False, "Смена не найдена или закрыта"

    # Если роль manager, проверяем что менеджера нет
    if role == "manager":
        cursor.execute(
            "SELECT COUNT(*) FROM shift_members WHERE shift_id = ? AND role = 'manager'",
            (shift_id,)
        )
        if cursor.fetchone()[0] > 0:
            conn.close()
            return False, "У смены уже есть менеджер"

    # Если роль member, проверяем лимит
    if role == "member":
        cursor.execute(
            "SELECT COUNT(*) FROM shift_members WHERE shift_id = ? AND role = 'member'",
            (shift_id,)
        )
        if cursor.fetchone()[0] >= 2:
            conn.close()
            return False, "В смене уже максимум 2 человека"

    # Проверяем что пользователь уже не в смене
    cursor.execute(
        "SELECT COUNT(*) FROM shift_members WHERE shift_id = ? AND user_id = ?",
        (shift_id, user_id)
    )
    if cursor.fetchone()[0] > 0:
        conn.close()
        return False, "Вы уже в этой смене"

    now = get_moscow_now_str("%Y-%m-%d %H:%M:%S")
    cursor.execute(
        "INSERT INTO shift_members (shift_id, user_id, role, joined_at) VALUES (?, ?, ?, ?)",
        (shift_id, user_id, role, now)
    )
    conn.commit()
    conn.close()
    return True, "OK"


def get_shift_users(shift_id: int) -> List[Tuple]:
    """Вернуть список участников смены: (user_id, username, role, joined_at)"""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT sm.user_id, u.username, sm.role, sm.joined_at FROM shift_members sm LEFT JOIN users u ON sm.user_id = u.user_id WHERE sm.shift_id = ?",
        (shift_id,)
    )
    rows = cursor.fetchall()
    conn.close()
    return rows


def get_shift_user_role(shift_id: int, user_id: int) -> Optional[str]:
    """Вернуть роль пользователя в смене или None."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT role FROM shift_members WHERE shift_id = ? AND user_id = ?",
        (shift_id, user_id)
    )
    row = cursor.fetchone()
    conn.close()
    return row[0] if row else None


def remove_user_from_shift(shift_id: int, user_id: int) -> None:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM shift_members WHERE shift_id = ? AND user_id = ?", (shift_id, user_id))
    conn.commit()
    conn.close()


def get_username(user_id: int) -> Optional[str]:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT username FROM users WHERE user_id = ?", (user_id,))
    row = cursor.fetchone()
    conn.close()
    return row[0] if row else None


# ==================== ФУНКЦИИ ДЛЯ УПРАВЛЕНИЯ ПРОФИЛЕМ ПОЛЬЗОВАТЕЛЯ ====================

def get_user_profile(user_id: int) -> Optional[Tuple]:
    """
    Получить профиль пользователя.
    
    Returns:
        Optional[Tuple]: (user_id, username, display_name, global_role) или None
    """
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT user_id, username, display_name, global_role FROM users WHERE user_id = ?",
        (user_id,)
    )
    row = cursor.fetchone()
    conn.close()
    return row


def get_user_display_name(user_id: int) -> str:
    """Получить отображаемое имя пользователя или username."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT display_name, username FROM users WHERE user_id = ?",
        (user_id,)
    )
    row = cursor.fetchone()
    conn.close()
    if row:
        return row[0] or row[1] or f"User {user_id}"
    return f"User {user_id}"


def set_user_display_name(user_id: int, display_name: str) -> None:
    """Установить отображаемое имя пользователя."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "UPDATE users SET display_name = ? WHERE user_id = ?",
        (display_name if display_name else None, user_id)
    )
    conn.commit()
    conn.close()


def get_user_global_role(user_id: int) -> str:
    """Получить глобальную роль пользователя."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT global_role FROM users WHERE user_id = ?",
        (user_id,)
    )
    row = cursor.fetchone()
    conn.close()
    return row[0] if row else "member"


def set_user_global_role(user_id: int, global_role: str) -> None:
    """Установить глобальную роль пользователя."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "UPDATE users SET global_role = ? WHERE user_id = ?",
        (global_role, user_id)
    )
    conn.commit()
    conn.close()


def get_all_users() -> List[Tuple]:
    """Получить всех пользователей с их профилями."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT user_id, username, display_name, global_role FROM users ORDER BY created_at DESC"
    )
    users = cursor.fetchall()
    conn.close()
    return users


def get_user_stats_full(user_id: int) -> dict:
    """Получить полную статистику пользователя."""
    conn = get_connection()
    cursor = conn.cursor()
    
    # Профиль
    cursor.execute(
        "SELECT user_id, username, display_name, global_role FROM users WHERE user_id = ?",
        (user_id,)
    )
    profile = cursor.fetchone()
    
    if not profile:
        conn.close()
        return {}
    
    # Всего кальянов добавлено
    cursor.execute("SELECT COUNT(*) FROM hookahs WHERE created_by = ?", (user_id,))
    total_hookahs = cursor.fetchone()[0] or 0
    
    # По типам
    cursor.execute(
        "SELECT hookah_type, COUNT(*) FROM hookahs WHERE created_by = ? GROUP BY hookah_type",
        (user_id,)
    )
    hookah_types = {row[0]: row[1] for row in cursor.fetchall()}
    
    # Всего смен
    cursor.execute(
        "SELECT COUNT(DISTINCT shift_id) FROM shift_members WHERE user_id = ?",
        (user_id,)
    )
    total_shifts = cursor.fetchone()[0] or 0
    
    # Смены в этом месяце
    month_key = get_moscow_datetime().strftime('%Y-%m')
    cursor.execute(
        "SELECT COUNT(DISTINCT sm.shift_id) "
        "FROM shift_members sm "
        "JOIN shifts s ON sm.shift_id = s.id "
        "WHERE sm.user_id = ? AND substr(s.open_time, 1, 7) = ?",
        (user_id, month_key)
    )
    month_shifts = cursor.fetchone()[0] or 0
    
    conn.close()
    
    return {
        'user_id': profile[0],
        'username': profile[1],
        'display_name': profile[2],
        'global_role': profile[3],
        'total_hookahs': total_hookahs,
        'hookah_types': hookah_types,
        'total_shifts': total_shifts,
        'month_shifts': month_shifts
    }