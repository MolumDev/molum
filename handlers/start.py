import logging
from typing import Callable
from aiogram import Router, Bot, F
from aiogram.filters import CommandStart, CommandObject
from aiogram.types import Message, CallbackQuery
import database
import keyboards
from config import CHANNEL_USERNAME

logger = logging.getLogger("MolumBot.StartHandler")

router = Router()

async def check_channel_subscription(bot: Bot, user_id: int) -> bool:
    """Verifies if the user is subscribed to the official channel."""
    try:
        member = await bot.get_chat_member(chat_id=CHANNEL_USERNAME, user_id=user_id)
        # Allowed statuses: creator, administrator, member, restricted
        return member.status in ["creator", "administrator", "member", "restricted"]
    except Exception as e:
        logger.warning(f"Could not verify subscription for user {user_id} on {CHANNEL_USERNAME}: {e}")
        # Return True for admin testing or if there's an API error so the bot doesn't completely block
        # during development. However, in production it checks properly.
        # Let's default to False but log details.
        return False

@router.message(CommandStart())
async def cmd_start(message: Message, command: CommandObject, _: Callable[..., str], bot: Bot):
    user_id = message.from_user.id
    username = message.from_user.username
    
    # Fetch existing profile
    profile = await database.get_profile(user_id)
    
    # Process potential referral arguments (start=ref_12345)
    referred_by = None
    if command.args and command.args.startswith("ref_"):
        try:
            ref_id_str = command.args.split("_")[1]
            referred_by = int(ref_id_str)
            # Self-referral prevention
            if referred_by == user_id:
                referred_by = None
        except (ValueError, IndexError):
            pass

    # Check actual subscription status
    is_subscribed = await check_channel_subscription(bot, user_id)
    
    if is_subscribed:
        if not profile:
            # First time user and subscribed -> Create profile, award 100 points
            profile = await database.create_profile(
                telegram_id=user_id,
                username=username,
                referred_by=referred_by,
                subscription_status=True,
                total_points=100
            )
            # Mark the subscription task as completed
            await database.complete_user_task(user_id, "subscribe")
            
            # Award referrer 50 points
            if referred_by:
                already_referred = await database.has_referred(referred_by, user_id)
                if not already_referred:
                    await database.add_points(referred_by, 50)
                    await database.add_referral(referred_by, user_id, 50)
                    
                    # Notify referrer in their language
                    ref_profile = await database.get_profile(referred_by)
                    ref_lang = ref_profile.get("language_code", "en") if ref_profile else "en"
                    
                    from middlewares.i18n import i18n_manager
                    ref_msg = i18n_manager.get(
                        "referral_notification_referrer",
                        lang=ref_lang,
                        referee_username=username or f"id{user_id}"
                    )
                    try:
                        await bot.send_message(chat_id=referred_by, text=ref_msg)
                    except Exception as e:
                        logger.warning(f"Failed to notify referrer {referred_by}: {e}")
                        
            text = _("welcome_subscribed")
        else:
            # Already registered, greeting back
            await database.update_profile_subscription(user_id, True)
            await database.complete_user_task(user_id, "subscribe")
            text = _("welcome_back", username=username or f"id{user_id}")
            
        lang = profile.get("language_code", "en")
        kb = keyboards.get_main_menu_keyboard(_, lang=lang)
        await message.answer(text, reply_markup=kb, parse_mode="Markdown")
    else:
        # Not subscribed yet
        if not profile:
            # Create a profile in non-subscribed, 0 points state. They get points on subscription verification.
            profile = await database.create_profile(
                telegram_id=user_id,
                username=username,
                referred_by=referred_by,
                subscription_status=False,
                total_points=0
            )
            
        lang = profile.get("language_code", "en")
        text = _("welcome_not_subscribed")
        kb = keyboards.get_subscription_keyboard(_, lang=lang)
        await message.answer(text, reply_markup=kb, parse_mode="Markdown")


@router.callback_query(F.data == "check_subscription")
async def cb_check_subscription(callback: CallbackQuery, _: Callable[..., str], bot: Bot):
    user_id = callback.from_user.id
    username = callback.from_user.username
    
    is_subscribed = await check_channel_subscription(bot, user_id)
    profile = await database.get_profile(user_id)
    lang = profile.get("language_code", "en") if profile else "en"
    
    if is_subscribed:
        first_time_sub = False
        if profile and not profile.get("subscription_status"):
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
                    await database.add_referral(referred_by, user_id, 50)
                    
                    # Notify referrer
                    ref_profile = await database.get_profile(referred_by)
                    ref_lang = ref_profile.get("language_code", "en") if ref_profile else "en"
                    
                    from middlewares.i18n import i18n_manager
                    ref_msg = i18n_manager.get(
                        "referral_notification_referrer",
                        lang=ref_lang,
                        referee_username=username or f"id{user_id}"
                    )
                    try:
                        await bot.send_message(chat_id=referred_by, text=ref_msg)
                    except Exception as e:
                        logger.warning(f"Could not notify referrer {referred_by}: {e}")
                        
        # Delete subscription prompt
        try:
            await callback.message.delete()
        except Exception:
            pass
            
        text = _("welcome_subscribed") if first_time_sub else _("welcome_back", username=username or f"id{user_id}")
        kb = keyboards.get_main_menu_keyboard(_, lang=lang)
        await bot.send_message(chat_id=user_id, text=text, reply_markup=kb, parse_mode="Markdown")
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
