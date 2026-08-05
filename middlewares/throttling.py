import time
import asyncio
import logging
from typing import Callable, Dict, Any, Awaitable
from aiogram import BaseMiddleware
from aiogram.types import TelegramObject, Message, CallbackQuery

logger = logging.getLogger("MolumBot.Throttling")

async def delete_message_delayed(bot, chat_id, message_id, delay=2):
    await asyncio.sleep(delay)
    try:
        await bot.delete_message(chat_id=chat_id, message_id=message_id)
    except Exception as e:
        logger.debug(f"Delayed deletion failed for msg {message_id} in chat {chat_id}: {e}")

class ThrottlingMiddleware(BaseMiddleware):
    def __init__(self, limit: float = 1.0):
        super().__init__()
        self.limit = limit
        self.cache = {}
        self.warning_sent_cache = {}

    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any]
    ) -> Any:
        user = data.get("event_from_user")
        if not user:
            return await handler(event, data)
        
        user_id = user.id
        now = time.time()
        
        # Check throttling
        if user_id in self.cache:
            last_time = self.cache[user_id]
            if now - last_time < self.limit:
                # User is executing commands too fast
                # Send warning if not sent in the last 3 seconds (avoid spamming warnings)
                last_warning_time = self.warning_sent_cache.get(user_id, 0)
                if now - last_warning_time > 3.0:
                    self.warning_sent_cache[user_id] = now
                    _ = data.get("_")
                    warning_text = _("spam_warning") if _ else "⚠️ Please do not spam! Wait a moment."
                    
                    if isinstance(event, Message):
                        try:
                            warn_msg = await event.answer(warning_text)
                            asyncio.create_task(delete_message_delayed(event.bot, event.chat.id, warn_msg.message_id, 2.5))
                        except Exception as e:
                            logger.warning(f"Failed to send throttling warning message: {e}")
                    elif isinstance(event, CallbackQuery):
                        try:
                            await event.answer(warning_text, show_alert=True)
                        except Exception as e:
                            logger.warning(f"Failed to answer throttling callback query: {e}")
                return
            
        self.cache[user_id] = now
        return await handler(event, data)
