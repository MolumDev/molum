import logging
from typing import Callable, Any
from aiogram import Router, F, Bot
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup
import database
import keyboards

logger = logging.getLogger("MolumBot.TasksHandler")

router = Router()

async def check_chat_membership(bot: Bot, user_id: int, chat_id: str) -> bool:
    """Verifies if the user is in a channel or group chat dynamically."""
    if not chat_id:
        return False
    try:
        member = await bot.get_chat_member(chat_id=chat_id, user_id=user_id)
        return member.status in ["creator", "administrator", "member", "restricted"]
    except Exception as e:
        logger.warning(f"Could not verify membership for user {user_id} on {chat_id}: {e}")
        return False

async def verify_task_scenario(bot: Bot, user_id: int, task_details: dict, profile: dict) -> bool:
    """
    Extremely versatile tasks verification engine.
    Supports 9 distinct scenarios to easily construct viral and growth-hacking tasks.
    """
    verify_type = task_details.get("verify_type", "bot")
    verify_chat = task_details.get("verify_chat")
    verify_value = task_details.get("verify_value")
    
    logger.info(f"Verifying task {task_details.get('task_id')} (Type: {verify_type}) for user {user_id}")

    # SCENARIO 1: Telegram Channel Subscription Check
    if verify_type == "channel":
        chat_id = verify_chat or "@molum_chain_official"
        return await check_chat_membership(bot, user_id, chat_id)

    # SCENARIO 2: Telegram Group Chat Membership Check (Chat/Boost)
    elif verify_type == "chat":
        chat_id = verify_chat or "@molum_chat"
        return await check_chat_membership(bot, user_id, chat_id)

    # SCENARIO 3: Connected Solana Wallet Check
    elif verify_type == "wallet":
        return bool(profile and profile.get("wallet_address") and len(profile["wallet_address"]) > 20)

    # SCENARIO 4: Referral Count Milestone Check
    elif verify_type == "referrals":
        req_val = verify_value or 3
        ref_count = profile.get("referral_count", 0) if profile else 0
        return ref_count >= req_val

    # SCENARIO 5: Real Telegram Channel Boost Check (Advanced!)
    elif verify_type == "boost":
        chat_id = verify_chat or "@molum_chain_official"
        try:
            boosts_info = await bot.get_user_chat_boosts(chat_id=chat_id, user_id=user_id)
            # If the boosts list is not empty, the user has boosted the channel!
            return len(boosts_info.boosts) > 0
        except Exception as e:
            logger.warning(f"Failed to query boosts for user {user_id} on {chat_id}: {e}")
            # If bot doesn't have admin rights, fallback to chat membership check as graceful safety net
            return await check_chat_membership(bot, user_id, chat_id)

    # SCENARIO 6: Brand keyword/suffix in Username or Name (Growth Hacking!)
    # E.g. Users get points for adding "🦊 Molum" to their Telegram first name
    elif verify_type == "name_suffix":
        keyword = verify_chat or "Molum"
        try:
            chat_user = await bot.get_chat(user_id)
            first_name = chat_user.first_name or ""
            last_name = chat_user.last_name or ""
            username = chat_user.username or ""
            
            full_text = f"{first_name} {last_name} {username}"
            return keyword.lower() in full_text.lower()
        except Exception as e:
            logger.warning(f"Failed to fetch profile details for suffix check on user {user_id}: {e}")
            return False

    # SCENARIO 7: Telegram Premium Account Check (Anti-bot / Quality filter)
    elif verify_type == "premium":
        try:
            chat_user = await bot.get_chat(user_id)
            # check is_premium on User object
            return bool(getattr(chat_user, "is_premium", False))
        except Exception as e:
            logger.warning(f"Failed to query premium status for user {user_id}: {e}")
            return False

    # SCENARIO 8: User Avatar Check (Ensures users have profile pictures)
    elif verify_type == "avatar":
        try:
            photos = await bot.get_user_profile_photos(user_id=user_id, limit=1)
            return photos.total_count > 0
        except Exception as e:
            logger.warning(f"Failed to fetch profile photos for user {user_id}: {e}")
            return False

    # SCENARIO 9: Auto-complete / Bot Approval (Twitter / Story social task fallbacks)
    elif verify_type == "bot":
        return True

    return False

async def render_tasks_message(user_id: int, _, lang: str) -> tuple[str, InlineKeyboardMarkup]:
    """Helper to compile the current tasks message and its keyboard."""
    # Get all active tasks sorted by sort_order
    all_tasks = await database.get_tasks()
    
    # Get completed task ids for this user
    completed_rows = await database.get_user_tasks(user_id)
    completed_task_ids = {row["task_id"] for row in completed_rows if row.get("completed")}
    
    # Compile text message displaying tasks
    text = _("tasks_title") + "\n\n"
    
    for task in all_tasks:
        title = task["title_ru"] if lang == "ru" else task["title_en"]
        points = task["points"]
        
        if task["task_id"] in completed_task_ids:
            text += _("task_completed", description=title, points=points) + "\n"
        else:
            text += _("task_incomplete", description=title, points=points) + "\n"
            
    kb = keyboards.get_tasks_keyboard(_, all_tasks, completed_task_ids, lang=lang)
    return text, kb

@router.message(Command("tasks"))
@router.message(F.text.in_(["🎯 Задания", "🎯 Tasks"]))
async def cmd_tasks(message: Message, _: Callable[..., str]):
    user_id = message.from_user.id
    username = message.from_user.username
    
    profile = await database.get_profile(user_id)
    if not profile:
        profile = await database.create_profile(telegram_id=user_id, username=username, first_name=message.from_user.first_name)
        
    lang = profile.get("language_code", "en")
    
    text, kb = await render_tasks_message(user_id, _, lang)
    await message.answer(text, reply_markup=kb, parse_mode="HTML")


@router.callback_query(F.data.startswith("check_task_"))
async def cb_check_task(callback: CallbackQuery, _: Callable[..., str], bot: Bot):
    user_id = callback.from_user.id
    username = callback.from_user.username
    
    task_id = callback.data.split("check_task_")[1]
    
    profile = await database.get_profile(user_id)
    lang = profile.get("language_code", "en") if profile else "en"
    
    # 1. Check if already completed
    task_status = await database.get_user_task_status(user_id, task_id)
    if task_status and task_status.get("completed"):
        await callback.answer("✅ Task already completed!", show_alert=True)
        return
        
    # 2. Get task details
    all_tasks = await database.get_tasks()
    task_details = next((t for t in all_tasks if t["task_id"] == task_id), None)
    if not task_details:
        await callback.answer("Task not found!", show_alert=True)
        return
        
    reward = task_details["points"]
    title = task_details["title_ru"] if lang == "ru" else task_details["title_en"]
    
    # 3. Perform dynamic verification check using our versatile engine
    success = await verify_task_scenario(bot, user_id, task_details, profile)
        
    if success:
        # Mark as completed and award points
        await database.complete_user_task(user_id, task_id)
        await database.add_points(user_id, reward)
        
        # Display success alert
        toast_text = _("task_check_success", task_name=title, points=reward)
        await callback.answer(toast_text, show_alert=True)
        
        # Update/Re-render the tasks message
        try:
            text, kb = await render_tasks_message(user_id, _, lang)
            await callback.message.edit_text(text, reply_markup=kb, parse_mode="HTML")
        except Exception as e:
            logger.debug(f"Failed to edit tasks message: {e}")
    else:
        # Condition not met
        await callback.answer(_("task_check_failed"), show_alert=True)


@router.callback_query(F.data.startswith("task_checked_completed_"))
async def cb_task_completed_alert(callback: CallbackQuery, _: Callable[..., str]):
    """Simply alert the user that this task is already complete."""
    await callback.answer("✅ Already Completed! / Уже выполнено!", show_alert=False)
