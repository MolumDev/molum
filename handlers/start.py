import logging
from typing import Callable
from aiogram import Router, Bot, F
from aiogram.filters import CommandStart, CommandObject
from aiogram.types import Message, CallbackQuery
import database
import keyboards
from config import CHANNEL_USERNAME
from handlers.tasks import check_chat_membership

logger = logging.getLogger("MolumBot.StartHandler")

router = Router()

@router.message(CommandStart())
async def cmd_start(message: Message, command: CommandObject, _: Callable[..., str], bot: Bot):
    user_id = message.from_user.id
    username = message.from_user.username
    first_name = message.from_user.first_name
    last_name = message.from_user.last_name
    
    # Use first_name or username for personal greeting, fallback to "friend"
    user_display = first_name or username or "friend"
    
    # Fetch existing profile
    profile = await database.get_profile(user_id)
    
    # Process potential referral arguments (start=ref_12345 or start=ref_MOL12345)
    referred_by = None
    if command.args and command.args.startswith("ref_"):
        try:
            ref_payload = command.args.split("_")[1]
            if ref_payload.startswith("MOL"):
                # Referral payload is code: e.g. MOL100001
                # Extrapolate numeric ID from MOL<id> if formatted as MOL<telegram_id>
                referred_by = int(ref_payload.replace("MOL", ""))
            else:
                referred_by = int(ref_payload)
                
            # Self-referral prevention
            if referred_by == user_id:
                referred_by = None
        except (ValueError, IndexError):
            pass

    # Check actual subscription status on the official channel
    is_subscribed = await check_chat_membership(bot, user_id, CHANNEL_USERNAME)
    
    if is_subscribed:
        if not profile:
            # First time user and subscribed -> Create profile, award 100 points
            profile = await database.create_profile(
                telegram_id=user_id,
                username=username,
                first_name=first_name,
                last_name=last_name,
                referred_by=referred_by,
                is_subscribed=True,
                total_points=100,
                language_code="en" # English first as requested!
            )
            # Mark the subscription task as completed
            await database.complete_user_task(user_id, "subscribe")
            
            # Award referrer 50 points and increment referral count
            if referred_by:
                already_referred = await database.has_referred(referred_by, user_id)
                if not already_referred:
                    await database.add_points(referred_by, 50)
                    await database.increment_referral_count(referred_by)
                    
                    # Notify referrer in their language
                    ref_profile = await database.get_profile(referred_by)
                    ref_lang = ref_profile.get("language_code", "en") if ref_profile else "en"
                    
                    from middlewares.i18n import i18n_manager
                    ref_msg = i18n_manager.get(
                        "referral_notification_referrer",
                        lang=ref_lang,
                        referee_username=first_name or username or f"id{user_id}"
                    )
                    try:
                        await bot.send_message(chat_id=referred_by, text=ref_msg, parse_mode="HTML")
                    except Exception as e:
                        logger.warning(f"Failed to notify referrer {referred_by}: {e}")
                        
            lang = "en"
            welcome_text = _("welcome_subscribed", username=user_display)
            sticker_text = _("sticker_pack_message")
            kb = keyboards.get_main_menu_keyboard(_, lang=lang)
            
            await message.answer(welcome_text, parse_mode="HTML")
            await message.answer(sticker_text, reply_markup=kb, parse_mode="HTML")
        else:
            # Already registered, greeting back
            await database.update_profile_subscription(user_id, True)
            await database.complete_user_task(user_id, "subscribe")
            
            lang = profile.get("language_code", "en")
            welcome_back_text = _("welcome_back", username=user_display)
            sticker_text = _("sticker_pack_message")
            kb = keyboards.get_main_menu_keyboard(_, lang=lang)
            
            await message.answer(welcome_back_text, parse_mode="HTML")
            await message.answer(sticker_text, reply_markup=kb, parse_mode="HTML")
    else:
        # Not subscribed yet
        if not profile:
            # Create a profile in non-subscribed, 0 points state. They get points on subscription verification.
            profile = await database.create_profile(
                telegram_id=user_id,
                username=username,
                first_name=first_name,
                last_name=last_name,
                referred_by=referred_by,
                is_subscribed=False,
                total_points=0,
                language_code="en" # English first as requested!
            )
            
        lang = profile.get("language_code", "en")
        text = _("welcome_not_subscribed", username=user_display)
        kb = keyboards.get_subscription_keyboard(_, lang=lang)
        await message.answer(text, reply_markup=kb, parse_mode="HTML")


@router.callback_query(F.data == "check_subscription")
async def cb_check_subscription(callback: CallbackQuery, _: Callable[..., str], bot: Bot):
    user_id = callback.from_user.id
    username = callback.from_user.username
    first_name = callback.from_user.first_name
    
    user_display = first_name or username or "friend"
    
    is_subscribed = await check_chat_membership(bot, user_id, CHANNEL_USERNAME)
    profile = await database.get_profile(user_id)
    lang = profile.get("language_code", "en") if profile else "en"
    
    if is_subscribed:
        first_time_sub = False
        if profile and not profile.get("is_subscribed"):
            first_time_sub = True
            # Update DB subscription status
            await database.update_profile_subscription(user_id, True)
            await database.complete_user_task(user_id, "subscribe")
            
            # Award 100 starter points
            await database.add_points(user_id, 100)
            
            # Process referral
            referred_by = profile.get("referred_by")
            if referred_by:
                already_referred = await database.has_referred(referred_by, user_id)
                if not already_referred:
                    await database.add_points(referred_by, 50)
                    await database.increment_referral_count(referred_by)
                    
                    # Notify referrer
                    ref_profile = await database.get_profile(referred_by)
                    ref_lang = ref_profile.get("language_code", "en") if ref_profile else "en"
                    
                    from middlewares.i18n import i18n_manager
                    ref_msg = i18n_manager.get(
                        "referral_notification_referrer",
                        lang=ref_lang,
                        referee_username=first_name or username or f"id{user_id}"
                    )
                    try:
                        await bot.send_message(chat_id=referred_by, text=ref_msg, parse_mode="HTML")
                    except Exception as e:
                        logger.warning(f"Could not notify referrer {referred_by}: {e}")
                        
        # Delete subscription prompt
        try:
            await callback.message.delete()
        except Exception:
            pass
            
        welcome_text = _("welcome_subscribed", username=user_display) if first_time_sub else _("welcome_back", username=user_display)
        sticker_text = _("sticker_pack_message")
        kb = keyboards.get_main_menu_keyboard(_, lang=lang)
        
        await bot.send_message(chat_id=user_id, text=welcome_text, parse_mode="HTML")
        await bot.send_message(chat_id=user_id, text=sticker_text, reply_markup=kb, parse_mode="HTML")
    else:
        # Failed check
        await callback.answer(_("task_check_failed"), show_alert=True)


@router.callback_query(F.data == "delete_msg")
async def cb_delete_msg(callback: CallbackQuery):
    """Universal handler to delete a message."""
    try:
        await callback.message.delete()
    except Exception as e:
        logger.debug(f"Failed to delete message: {e}")
    await callback.answer()
