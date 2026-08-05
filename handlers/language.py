import logging
from typing import Callable
from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery
import database
import keyboards

logger = logging.getLogger("MolumBot.LanguageHandler")

router = Router()

@router.message(Command("language"))
@router.message(F.text.in_(["🌐 Язык", "🌐 Language"]))
async def cmd_language(message: Message, _: Callable[..., str]):
    user_id = message.from_user.id
    username = message.from_user.username
    
    profile = await database.get_profile(user_id)
    if not profile:
        profile = await database.create_profile(telegram_id=user_id, username=username)
        
    lang = profile.get("language_code", "en")
    
    text = _("lang_title")
    kb = keyboards.get_language_keyboard(_, lang=lang)
    await message.answer(text, reply_markup=kb, parse_mode="Markdown")


@router.callback_query(F.data.startswith("set_lang_"))
async def cb_set_lang(callback: CallbackQuery, _: Callable[..., str]):
    user_id = callback.from_user.id
    new_lang = callback.data.split("set_lang_")[1]
    
    # Update language code in database
    await database.update_profile_language(user_id, new_lang)
    
    # Reload localizer with the new language directly for instant UI update!
    from middlewares.i18n import i18n_manager
    def translate_new(key: str, **kwargs) -> str:
        return i18n_manager.get(key, new_lang, **kwargs)
        
    # Re-render messages
    text = translate_new("lang_changed")
    kb = keyboards.get_language_keyboard(translate_new, lang=new_lang)
    
    try:
        await callback.message.edit_text(text, reply_markup=kb, parse_mode="Markdown")
    except Exception as e:
        logger.debug(f"Failed to edit language message: {e}")
        
    # Show toast alert
    await callback.answer(translate_new("lang_changed"), show_alert=True)
    
    # Re-send main menu to update ReplyKeyboard instantly in the correct language!
    main_menu_text = translate_new("main_menu_title")
    menu_kb = keyboards.get_main_menu_keyboard(translate_new, lang=new_lang)
    await callback.bot.send_message(chat_id=user_id, text=main_menu_text, reply_markup=menu_kb, parse_mode="Markdown")
