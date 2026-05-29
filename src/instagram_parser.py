"""
Instagram Parser Module

Модуль для парсинга постов и историй с Instagram аккаунта
и отправки их в Telegram чат.

Author: Hookah Bot Team
License: MIT
"""

import logging
import asyncio
from typing import Optional, List
from datetime import datetime, timedelta
from os import getenv
import io

try:
    from instagrapi import Client
    from instagrapi.types import Media
except ImportError:
    logging.error("instagrapi не установлен. Установите: pip install instagrapi")
    Client = None
    Media = None

from aiogram import Bot
from aiogram.types import InputFile, FSInputFile

logger = logging.getLogger(__name__)


class InstagramParser:
    """Класс для парсинга Instagram аккаунта"""
    
    def __init__(self, username: str, password: str):
        """
        Инициализация парсера Instagram
        
        Args:
            username: имя пользователя Instagram
            password: пароль Instagram
        """
        if Client is None:
            raise ImportError("instagrapi не установлена")
        
        self.client = Client()
        self.username = username
        self.password = password
        self.is_logged_in = False
    
    async def login(self) -> bool:
        """
        Вход в аккаунт Instagram
        
        Returns:
            True если успешно, False если ошибка
        """
        try:
            loop = asyncio.get_event_loop()
            self.client.login(self.username, self.password)
            self.is_logged_in = True
            logger.info(f"✅ Успешный вход в Instagram аккаунт: {self.username}")
            return True
        except Exception as e:
            logger.error(f"❌ Ошибка входа в Instagram: {e}")
            return False
    
    async def get_user_id(self, username: str) -> Optional[int]:
        """
        Получить ID пользователя по имени
        
        Args:
            username: имя пользователя
            
        Returns:
            ID пользователя или None если не найден
        """
        try:
            user = self.client.user_info_by_username(username)
            return user.pk
        except Exception as e:
            logger.error(f"❌ Ошибка получения ID пользователя {username}: {e}")
            return None
    
    async def get_user_posts(self, username: str, count: int = 10) -> List[Media]:
        """
        Получить посты пользователя
        
        Args:
            username: имя пользователя
            count: количество постов для загрузки
            
        Returns:
            Список медиа объектов
        """
        try:
            user_id = await self.get_user_id(username)
            if not user_id:
                return []
            
            medias = self.client.user_medias(user_id, amount=count)
            logger.info(f"✅ Загружено {len(medias)} постов пользователя {username}")
            return medias
        except Exception as e:
            logger.error(f"❌ Ошибка загрузки постов {username}: {e}")
            return []
    
    async def get_user_stories(self, username: str) -> List:
        """
        Получить истории пользователя
        
        Args:
            username: имя пользователя
            
        Returns:
            Список объектов историй
        """
        try:
            user_id = await self.get_user_id(username)
            if not user_id:
                return []
            
            stories = self.client.user_stories(user_id)
            logger.info(f"✅ Загружено {len(stories)} историй пользователя {username}")
            return stories
        except Exception as e:
            logger.error(f"❌ Ошибка загрузки историй {username}: {e}")
            return []
    
    async def download_media(self, media: Media) -> Optional[bytes]:
        """
        Загрузить медиа (фото/видео)
        
        Args:
            media: объект медиа
            
        Returns:
            Байты медиа или None если ошибка
        """
        try:
            if media.media_type == 8:  # Carousel
                # Для карусели берем первое изображение
                photo_url = media.resources[0].thumb_url
            else:
                photo_url = media.thumbnail_url or media.resources[0].thumb_url
            
            import requests
            response = requests.get(photo_url, timeout=10)
            if response.status_code == 200:
                return response.content
        except Exception as e:
            logger.error(f"❌ Ошибка загрузки медиа: {e}")
        
        return None


async def send_posts_to_telegram(
    bot: Bot,
    chat_id: int,
    parser: InstagramParser,
    instagram_account: str,
    count: int = 5
):
    """
    Загрузить и отправить посты в Telegram
    
    Args:
        bot: экземпляр Telegram бота
        chat_id: ID чата для отправки
        parser: экземпляр парсера Instagram
        instagram_account: имя аккаунта для парсинга
        count: количество постов
    """
    try:
        posts = await parser.get_user_posts(instagram_account, count)
        
        for post in posts:
            try:
                caption = f"📸 <b>@{instagram_account}</b>\n\n"
                
                if post.caption:
                    caption += f"{post.caption[:1000]}\n\n"
                
                caption += f"❤️ Лайков: {post.like_count}\n"
                caption += f"💬 Комментариев: {post.comment_count}\n"
                caption += f"🔗 <a href='https://instagram.com/p/{post.code}'>Перейти в Instagram</a>"
                
                if post.media_type in [1, 2]:  # Photo or Video
                    media_data = await parser.download_media(post)
                    if media_data:
                        if post.media_type == 1:  # Photo
                            await bot.send_photo(
                                chat_id=chat_id,
                                photo=InputFile(io.BytesIO(media_data), filename="photo.jpg"),
                                caption=caption,
                                parse_mode="HTML"
                            )
                        else:  # Video
                            await bot.send_document(
                                chat_id=chat_id,
                                document=InputFile(io.BytesIO(media_data), filename="video.mp4"),
                                caption=caption,
                                parse_mode="HTML"
                            )
                    else:
                        await bot.send_message(
                            chat_id=chat_id,
                            text=caption,
                            parse_mode="HTML"
                        )
                else:
                    await bot.send_message(
                        chat_id=chat_id,
                        text=caption,
                        parse_mode="HTML"
                    )
                
                await asyncio.sleep(1)  # Задержка между сообщениями
                
            except Exception as e:
                logger.error(f"❌ Ошибка отправки поста: {e}")
                continue
        
        logger.info(f"✅ Отправлено {len(posts)} постов в чат {chat_id}")
        
    except Exception as e:
        logger.error(f"❌ Ошибка отправки постов: {e}")


async def send_stories_to_telegram(
    bot: Bot,
    chat_id: int,
    parser: InstagramParser,
    instagram_account: str
):
    """
    Загрузить и отправить истории в Telegram
    
    Args:
        bot: экземпляр Telegram бота
        chat_id: ID чата для отправки
        parser: экземпляр парсера Instagram
        instagram_account: имя аккаунта для парсинга
    """
    try:
        stories = await parser.get_user_stories(instagram_account)
        
        for story in stories:
            try:
                caption = f"📱 <b>История @{instagram_account}</b>\n"
                caption += f"🔗 <a href='https://instagram.com/{instagram_account}'>Профиль</a>"
                
                # Попытка загрузить первый ресурс истории
                if hasattr(story, 'resources') and story.resources:
                    media_data = await parser.download_media(story)
                    if media_data:
                        await bot.send_document(
                            chat_id=chat_id,
                            document=InputFile(io.BytesIO(media_data), filename="story.mp4"),
                            caption=caption,
                            parse_mode="HTML"
                        )
                    else:
                        await bot.send_message(
                            chat_id=chat_id,
                            text=caption,
                            parse_mode="HTML"
                        )
                else:
                    await bot.send_message(
                        chat_id=chat_id,
                        text=caption,
                        parse_mode="HTML"
                    )
                
                await asyncio.sleep(1)
                
            except Exception as e:
                logger.error(f"❌ Ошибка отправки истории: {e}")
                continue
        
        logger.info(f"✅ Отправлено {len(stories)} историй в чат {chat_id}")
        
    except Exception as e:
        logger.error(f"❌ Ошибка отправки историй: {e}")
