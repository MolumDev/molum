import os
import json
import logging
from typing import Callable, Dict, Any, Awaitable
from aiogram import BaseMiddleware
from aiogram.types import TelegramObject, User
import database

logger = logging.getLogger("MolumBot.I18n")

class LocalizationManager:
    def __init__(self):
        self.translations = {}
        self.load_translations()

    def load_translations(self):
        for lang in ["en", "ru"]:
            path = f"locales/{lang}.json"
            if os.path.exists(path):
                try:
                    with open(path, "r", encoding="utf-8") as f:
                        self.translations[lang] = json.load(f)
                    logger.info(f"Loaded translations for '{lang}'.")
                except Exception as e:
                    logger.error(f"Failed to load translation file '{path}': {e}")
                    self.translations[lang] = {}
            else:
                logger.warning(f"Translation file '{path}' not found!")
                self.translations[lang] = {}

    def get(self, key: str, lang: str = "en", **kwargs) -> str:
        # Fallback to English if language is not supported
        lang_dict = self.translations.get(lang, self.translations.get("en", {}))
        text = lang_dict.get(key, self.translations.get("en", {}).get(key, key))
        if kwargs:
            try:
                return text.format(**kwargs)
            except Exception as e:
                logger.warning(f"Formatting failed for key '{key}' in lang '{lang}': {e}")
                return text
        return text

i18n_manager = LocalizationManager()

class I18nMiddleware(BaseMiddleware):
    def __init__(self):
        super().__init__()
        self.i18n_manager = i18n_manager

    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any]
    ) -> Any:
        # Retrieve the user from event
        user: User = data.get("event_from_user")
        
        lang = "en"
        if user:
            # Query DB for user language
            profile = await database.get_profile(user.id)
            if profile:
                lang = profile.get("language_code", "en")
            else:
                # Fallback to user's Telegram language
                tg_lang = user.language_code
                lang = "ru" if tg_lang == "ru" else "en"
        
        # Define translator function
        def translate(key: str, **kwargs) -> str:
            return self.i18n_manager.get(key, lang, **kwargs)
        
        # Inject translator and language code into handler context
        data["_"] = translate
        data["user_lang"] = lang
        
        return await handler(event, data)
