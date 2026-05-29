"""
Telegram Bot for Hookah Shift Management (Счетчик Кальянов)

Основной модуль для запуска Telegram бота, предназначенного для учета
кальянов в кальянной во время рабочей смены.

Этот модуль инициализирует:
- Загрузку конфигурации из .env файла
- Настройку логирования
- Инициализацию базы данных SQLite
- Создание и запуск Telegram бота с aiogram 3.x

Usage:
    python bot.py

Requirements:
    - aiogram>=3.20.0
    - python-dotenv>=1.0.0

Author: Hookah Bot Team
License: MIT
"""

import asyncio
import logging
from os import getenv
import sys

from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage
from dotenv import load_dotenv

# Загрузка переменных окружения из .env файла
load_dotenv()

from src.logging_setup import configure_logging

# Настройка логирования (консоль + файл)
configure_logging()

import src.database as db
from src.handlers import router
logger = logging.getLogger(__name__)


async def main():
    """
    Основная асинхронная функция для инициализации и запуска бота.
    
    Этапы:
    1. Проверка наличия и корректности BOT_TOKEN в .env
    2. Инициализация SQLite базы данных
    3. Создание экземпляра Bot и Dispatcher
    4. Регистрация маршрутизаторов обработчиков
    5. Удаление старых webhooks (если были)
    6. Запуск polling для получения обновлений от Telegram
    """
    # Проверка токена бота
    bot_token = getenv("BOT_TOKEN")
    if not bot_token or bot_token == "YOUR_BOT_TOKEN_HERE":
        logger.error("❌ Токен бота не установлен! Отредактируйте файл .env")
        return

    logger.info("✅ Токен бота загружен")

    # Инициализация базы данных SQLite
    # Создаются таблицы shifts и hookahs если их нет
    db.init_db()
    logger.info("✅ База данных инициализирована")

    # Инициализация Telegram бота с полученным токеном
    bot = Bot(token=bot_token)
    
    # Хранилище состояний FSM (Finite State Machine) в памяти
    # Для продакшена рекомендуется использовать Redis или другую БД
    storage = MemoryStorage()
    
    # Создание Dispatcher для управления обновлениями и обработчиками
    dp = Dispatcher(storage=storage)
    
    # Регистрация маршрутизатора с обработчиками команд и callback'ов
    dp.include_router(router)

    # Глобальный обработчик ошибок - логируем все необработанные исключения
    async def errors_handler(update=None, exception=None, *args, **kwargs):
        logger.exception("Unhandled exception while processing update: %s", exception)

    dp.errors.register(errors_handler)
    
    # Удаление старых webhooks и ожидающих обновлений
    # Важно для чистого запуска polling после использования webhooks
    await bot.delete_webhook(drop_pending_updates=True)
    logger.info("✅ Бот запущен и готов к работе 🚀")
    
    # Запуск long polling для получения обновлений от Telegram
    # Бот будет работать в этом цикле до остановки (Ctrl+C)
    try:
        await dp.start_polling(bot)
    finally:
        await bot.session.close()
        logger.info("🛑 Бот остановлен")


if __name__ == "__main__":
    # Запуск основной асинхронной функции
    asyncio.run(main())