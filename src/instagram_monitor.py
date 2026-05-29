"""
Instagram Monitor

Фоновая задача, которая периодически проверяет Instagram аккаунт
и отправляет новые посты/истории в указанный Telegram чат.
"""
import asyncio
import json
import logging
from os import getenv, makedirs
from os.path import exists, dirname
from typing import Set

from aiogram import Bot

from .instagram_parser import InstagramParser, send_posts_to_telegram, send_stories_to_telegram

logger = logging.getLogger(__name__)


class InstagramMonitor:
    def __init__(self, bot: Bot, instagram_username: str, instagram_password: str, instagram_account: str, target_chat_id: int, interval: int = 10, state_path: str = "data/instagram_state.json"):
        self.bot = bot
        self.instagram_username = instagram_username
        self.instagram_password = instagram_password
        self.instagram_account = instagram_account
        self.target_chat_id = target_chat_id
        self.interval = max(1, int(interval))
        self.state_path = state_path
        self.parser = InstagramParser(instagram_username, instagram_password)
        self._running = False

        # state
        self.last_post_codes: Set[str] = set()
        self.last_story_ids: Set[str] = set()

        # ensure state dir exists
        state_dir = dirname(self.state_path)
        if state_dir and not exists(state_dir):
            makedirs(state_dir, exist_ok=True)

        self._load_state()

    def _load_state(self):
        try:
            if exists(self.state_path):
                with open(self.state_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    self.last_post_codes = set(data.get("last_post_codes", []))
                    self.last_story_ids = set(data.get("last_story_ids", []))
                    logger.info("✅ Instagram state loaded")
        except Exception as e:
            logger.warning(f"Не удалось загрузить состояние Instagram: {e}")

    def _save_state(self):
        try:
            data = {
                "last_post_codes": list(self.last_post_codes),
                "last_story_ids": list(self.last_story_ids)
            }
            with open(self.state_path, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            logger.info("✅ Instagram state saved")
        except Exception as e:
            logger.warning(f"Не удалось сохранить состояние Instagram: {e}")

    async def start(self):
        self._running = True
        # try login first
        try:
            ok = await self.parser.login()
            if not ok:
                # Попытка автоматически получить код из Gmail
                try:
                    from .gmail_reader import fetch_verification_code
                    gmail_user = getenv('GMAIL_EMAIL')
                    gmail_pass = getenv('GMAIL_APP_PASSWORD')
                    if gmail_user and gmail_pass:
                        code = fetch_verification_code(gmail_user, gmail_pass)
                        if code:
                            logger.info('Попытка автоподтверждения кода из Gmail')
                            try:
                                # Попытка использовать метод two_factor_login у instagrapi клиента
                                if hasattr(self.parser.client, 'two_factor_login'):
                                    self.parser.client.two_factor_login(code)
                                    self.parser.is_logged_in = True
                                    ok = True
                                elif hasattr(self.parser.client, 'challenge_code'):
                                    self.parser.client.challenge_code(code)
                                    self.parser.is_logged_in = True
                                    ok = True
                                else:
                                    logger.warning('Клиент instagrapi не поддерживает автоматический ввод кода')
                            except Exception as ex:
                                logger.exception('Ошибка при отправке кода в Instagram: %s', ex)
                except Exception as e:
                    logger.debug('Gmail auto-code step failed: %s', e)

            if not ok:
                logger.error("Не удалось залогиниться в Instagram монитор, монитор не запущен")
                return
        except Exception as e:
            logger.exception(f"Ошибка при логине в Instagram: {e}")
            return

        logger.info("🔁 Instagram монитор запущен")
        await self.run()

    async def stop(self):
        logger.info("🛑 Останавливаем Instagram монитор")
        self._running = False

    async def run(self):
        """Основной цикл мониторинга."""
        self._running = True

        while self._running:
            try:
                # Проверяем посты
                posts = await self.parser.get_user_posts(self.instagram_account, count=10)
                # posts — список объектов с атрибутом code
                new_posts = [p for p in posts if getattr(p, "code", None) not in self.last_post_codes]

                # Отправляем новые посты в порядке от старых к новым
                if new_posts:
                    for post in reversed(new_posts):
                        try:
                            await send_posts_to_telegram(self.bot, self.target_chat_id, self.parser, self.instagram_account, count=1)
                            # добавляем код поста как просмотренный
                            code = getattr(post, "code", None)
                            if code:
                                self.last_post_codes.add(code)
                        except Exception as e:
                            logger.exception(f"Ошибка отправки поста: {e}")

                # Проверяем истории
                stories = await self.parser.get_user_stories(self.instagram_account)
                new_stories = [s for s in stories if str(getattr(s, "pk", getattr(s, "id", None))) not in self.last_story_ids]
                if new_stories:
                    for story in new_stories:
                        try:
                            await send_stories_to_telegram(self.bot, self.target_chat_id, self.parser, self.instagram_account)
                            sid = str(getattr(story, "pk", getattr(story, "id", None)))
                            if sid:
                                self.last_story_ids.add(sid)
                        except Exception as e:
                            logger.exception(f"Ошибка отправки истории: {e}")

                # Сохраняем состояние
                self._save_state()

            except Exception as e:
                logger.exception(f"Ошибка в цикле мониторинга Instagram: {e}")

            await asyncio.sleep(self.interval)
