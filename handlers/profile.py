import logging
from typing import Callable
from aiogram import Router, F, Bot
from aiogram.filters import Command
from aiogram.types import Message
import database
import keyboards

logger = logging.getLogger("MolumBot.ProfileHandler")

router = Router()

@router.message(Command("balance"))
@router.message(F.text.in_(["📊 Мой профиль", "📊 My Profile"]))
async def cmd_balance(message: Message, _: Callable[..., str]):
    user_id = message.from_user.id
    username = message.from_user.username
    
    # Fetch or create profile if not exists (failsafe)
    profile = await database.get_profile(user_id)
    if not profile:
        profile = await database.create_profile(
            telegram_id=user_id,
            username=username
        )
        
    lang = profile.get("language_code", "en")
    referred_count = await database.get_referral_count(user_id)
    
    wallet_display = profile.get("wallet_address") or _("no_wallet")
    
    # Build text
    text = _(
        "profile_text",
        telegram_id=user_id,
        username=username or f"id{user_id}",
        total_points=profile.get("total_points", 0),
        referred_count=referred_count,
        wallet_address=wallet_display
    )
    
    kb = keyboards.get_profile_keyboard(_, lang=lang)
    await message.answer(text, reply_markup=kb, parse_mode="Markdown")


@router.message(Command("referral"))
@router.message(F.text.in_(["👥 Пригласить друга", "👥 Invite Friend"]))
async def cmd_referral(message: Message, _: Callable[..., str], bot: Bot):
    user_id = message.from_user.id
    username = message.from_user.username
    
    profile = await database.get_profile(user_id)
    if not profile:
        profile = await database.create_profile(telegram_id=user_id, username=username)
        
    lang = profile.get("language_code", "en")
    
    # Retrieve bot username to construct direct referral link
    bot_info = await bot.get_me()
    bot_username = bot_info.username
    
    referral_link = f"https://t.me/{bot_username}?start=ref_{user_id}"
    
    text = _(
        "referral_text",
        referral_link=referral_link
    )
    
    kb = keyboards.get_referral_keyboard(_, user_id=user_id, bot_username=bot_username, lang=lang)
    await message.answer(text, reply_markup=kb, parse_mode="Markdown")


@router.message(Command("leaderboard"))
@router.message(F.text.in_(["📈 Таблица лидеров", "📈 Leaderboard"]))
async def cmd_leaderboard(message: Message, _: Callable[..., str]):
    user_id = message.from_user.id
    username = message.from_user.username
    
    profile = await database.get_profile(user_id)
    if not profile:
        profile = await database.create_profile(telegram_id=user_id, username=username)
        
    lang = profile.get("language_code", "en")
    
    text = _("leaderboard_text")
    kb = keyboards.get_leaderboard_keyboard(_, user_id=user_id, lang=lang)
    await message.answer(text, reply_markup=kb, parse_mode="Markdown")


@router.message(Command("wallet"))
@router.message(F.text.in_(["💼 Кошелёк", "💼 Wallet"]))
async def cmd_wallet(message: Message, _: Callable[..., str]):
    user_id = message.from_user.id
    username = message.from_user.username
    
    profile = await database.get_profile(user_id)
    if not profile:
        profile = await database.create_profile(telegram_id=user_id, username=username)
        
    lang = profile.get("language_code", "en")
    wallet_address = profile.get("wallet_address") or _("no_wallet")
    
    text = _("wallet_title", wallet_address=wallet_address)
    kb = keyboards.get_wallet_keyboard(_, user_id=user_id, lang=lang)
    await message.answer(text, reply_markup=kb, parse_mode="Markdown")
