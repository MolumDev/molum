import logging
import datetime
from typing import Callable
from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery
import database
import keyboards

logger = logging.getLogger("MolumBot.TokenHandler")

router = Router()

def parse_iso_datetime(iso_str: str) -> datetime.datetime:
    """Parses ISO-8601 datetime strings with timezone support."""
    try:
        clean_str = iso_str.replace("Z", "+00:00")
        return datetime.datetime.fromisoformat(clean_str)
    except Exception as e:
        logger.error(f"Failed to parse datetime '{iso_str}': {e}. Defaulting to far future.")
        return datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(days=180)

@router.message(Command("token"))
@router.message(F.text.in_(["🚀 Статус токена", "🚀 Token Status"]))
async def cmd_token(message: Message, _: Callable[..., str]):
    user_id = message.from_user.id
    username = message.from_user.username
    
    profile = await database.get_profile(user_id)
    if not profile:
        profile = await database.create_profile(telegram_id=user_id, username=username)
        
    lang = profile.get("language_code", "en")
    
    # Get current token status from settings
    status = await database.get_setting("token_status") or "pre-launch"
    
    if status == "pre-launch":
        # Get listing date
        listing_date_raw = await database.get_setting("listing_date") or "2026-12-31T23:59:59Z"
        listing_datetime = parse_iso_datetime(listing_date_raw)
        
        now = datetime.datetime.now(datetime.timezone.utc)
        diff = listing_datetime - now
        
        if diff.total_seconds() > 0:
            days = diff.days
            hours, remainder = divmod(diff.seconds, 3600)
            minutes, seconds = divmod(remainder, 60)
        else:
            days = hours = minutes = seconds = 0
            
        # Display countdown
        text = _(
            "token_title_pre",
            days=days,
            hours=hours,
            minutes=minutes,
            seconds=seconds,
            listing_date=listing_datetime.strftime("%Y-%m-%d %H:%M:%S UTC")
        )
        kb = keyboards.get_token_prelaunch_keyboard(_, lang=lang)
        await message.answer(text, reply_markup=kb, parse_mode="HTML")
        
    else:
        # Token is LIVE!
        price = await database.get_setting("token_price") or "0.0042"
        chart_url = await database.get_setting("token_chart_url") or "https://dexscreener.com"
        
        text = _(
            "token_title_live",
            price=price,
            chart_url=chart_url
        )
        kb = keyboards.get_token_live_keyboard(_, chart_url=chart_url, lang=lang)
        await message.answer(text, reply_markup=kb, parse_mode="HTML")


@router.callback_query(F.data == "notify_listing")
async def cb_notify_listing(callback: CallbackQuery, _: Callable[..., str]):
    user_id = callback.from_user.id
    
    already_notified = await database.has_token_notification(user_id)
    
    if already_notified:
        await callback.answer(_("notified_already"), show_alert=True)
    else:
        await database.add_token_notification(user_id)
        await callback.answer(_("notified_success"), show_alert=True)
