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
from datetime import datetime
from typing import Optional, List, Tuple

# Путь к файлу базы данных SQLite
DB_PATH = "hookah_bot.db"


def get_connection() -> sqlite3.Connection:
    """
    Получить соединение с базой данных SQLite.
    
    Returns:
        sqlite3.Connection: Объект соединения с БД
    """
    return sqlite3.connect(DB_PATH)


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
    
    conn.commit()
    conn.close()


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
    # Получаем текущее время в формате YYYY-MM-DD HH:MM:SS
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
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
    
    # Получаем текущее время для записи времени закрытия
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
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

def add_hookah(shift_id: int, hookah_type: str, table_name: str) -> int:
    """
    Добавить кальян в текущую смену.
    
    Args:
        shift_id (int): ID смены
        hookah_type (str): Тип кальяна ("Стандарт" или "Сигара")
        table_name (str): Название стола (1-7, "Большой бар", "Малый бар", "Стол у танцпола")
        
    Returns:
        int: ID созданного кальяна
        
    Процесс:
        - Записывается текущее время автоматически
        - Создается новая запись в таблице hookahs
        
    Example:
        hookah_id = add_hookah(1, "Стандарт", "1")
    """
    conn = get_connection()
    cursor = conn.cursor()
    # Автоматически записываем текущее время
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    cursor.execute(
        "INSERT INTO hookahs (shift_id, hookah_type, table_name, created_at) VALUES (?, ?, ?, ?)",
        (shift_id, hookah_type, table_name, now)
    )
    hookah_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return hookah_id


def get_hookah_by_id(hookah_id: int) -> Optional[Tuple]:
    """
    Получить информацию о кальяне по ID.
    
    Args:
        hookah_id (int): ID кальяна
        
    Returns:
        Optional[Tuple]: Кортеж с данными кальяна или None если не найден
        
    Структура кортежа: (id, shift_id, hookah_type, table_name, created_at)
    """
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM hookahs WHERE id = ?", (hookah_id,))
    hookah = cursor.fetchone()
    conn.close()
    return hookah


def get_hookahs_by_shift(shift_id: int) -> List[Tuple]:
    """
    Получить все кальяны за конкретную смену.
    
    Args:
        shift_id (int): ID смены
        
    Returns:
        List[Tuple]: Список кортежей с данными кальянов
        
    Структура каждого кортежа: (id, shift_id, hookah_type, table_name, created_at)
    
    Сортировка:
        По времени добавления (от ранних к поздним)
    """
    conn = get_connection()
    cursor = conn.cursor()
    # Сортируем по времени добавления - ранние кальяны в начале
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
    table_name: Optional[str] = None
) -> None:
    """
    Обновить данные кальяна.
    
    Args:
        hookah_id (int): ID кальяна
        hookah_type (Optional[str]): Новый тип кальяна (если нужно изменить)
        table_name (Optional[str]): Новое название стола (если нужно изменить)
        
    Процесс:
        - Обновляет только переданные параметры
        - Если параметр None, он не обновляется
        
    Example:
        # Изменить только тип
        update_hookah(5, hookah_type="Сигара")
        
        # Изменить только стол
        update_hookah(5, table_name="Большой бар")
        
        # Изменить оба
        update_hookah(5, "Стандарт", "2")
    """
    conn = get_connection()
    cursor = conn.cursor()
    
    # Обновляем тип кальяна если передан
    if hookah_type is not None:
        cursor.execute(
            "UPDATE hookahs SET hookah_type = ? WHERE id = ?",
            (hookah_type, hookah_id)
        )
    
    # Обновляем стол если передан
    if table_name is not None:
        cursor.execute(
            "UPDATE hookahs SET table_name = ? WHERE id = ?",
            (table_name, hookah_id)
        )
    
    conn.commit()
    conn.close()


def delete_hookah(hookah_id: int) -> None:
    """
    Удалить кальян из базы данных.
    
    Args:
        hookah_id (int): ID кальяна для удаления
        
    Процесс:
        - Удаляет запись из таблицы hookahs
        - Внешний ключ гарантирует, что можно удалять только кальяны существующих смен
        
    Example:
        delete_hookah(5)  # Удалить кальян с ID 5
    """
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM hookahs WHERE id = ?", (hookah_id,))
    conn.commit()
    conn.close()


def update_hookah(hookah_id: int, hookah_type: str = None, table_name: str = None):
    """Обновить кальян"""
    conn = get_connection()
    cursor = conn.cursor()
    if hookah_type:
        cursor.execute(
            "UPDATE hookahs SET hookah_type = ? WHERE id = ?",
            (hookah_type, hookah_id)
        )
    if table_name:
        cursor.execute(
            "UPDATE hookahs SET table_name = ? WHERE id = ?",
            (table_name, hookah_id)
        )
    conn.commit()
    conn.close()


def delete_hookah(hookah_id: int):
    """Удалить кальян"""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM hookahs WHERE id = ?", (hookah_id,))
    conn.commit()
    conn.close()