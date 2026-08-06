import logging
from typing import Callable, Any
from aiogram import Router, F, Bot
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery
import database
import keyboards
from handlers.start import check_channel_subscription

logger = logging.getLogger("MolumBot.TasksHandler")

router = Router()

async def render_tasks_message(user_id: int, _, lang: str) -> tuple[str, Any]:
    """Helper to compile the current tasks message and its keyboard."""
    # Get all active tasks
    all_tasks = await database.get_tasks()
    
    # Get completed task ids for this user
    completed_rows = await database.get_user_tasks(user_id)
    completed_task_ids = {row["task_id"] for row in completed_rows if row.get("completed")}
    
    # Compile text message displaying tasks
    text = _("tasks_title") + "\n\n"
    
    for task in all_tasks:
        desc = _(task["description_key"])
        points = task["points_reward"]
        
        if task["task_id"] in completed_task_ids:
            text += _("task_completed", description=desc, points=points) + "\n"
        else:
            text += _("task_incomplete", description=desc, points=points) + "\n"
            
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
        await callback.answer(_("task_check_success", task_name=_(task_id), points=0), show_alert=True)
        return
        
    # 2. Get task rewards
    all_tasks = await database.get_tasks()
    task_details = next((t for t in all_tasks if t["task_id"] == task_id), None)
    if not task_details:
        await callback.answer("Task not found!", show_alert=True)
        return
        
    reward = task_details["points_reward"]
    desc_key = task_details["description_key"]
    task_name = _(desc_key)
    
    # 3. Perform actual verification logic based on task_id
    success = False
    
    if task_id == "subscribe":
        # Check channel subscription
        success = await check_channel_subscription(bot, user_id)
        if success:
            await database.update_profile_subscription(user_id, True)
            
    elif task_id == "invite_3_friends":
        # Check if user has referred at least 3 friends
        ref_count = await database.get_referral_count(user_id)
        if ref_count >= 3:
            success = True
            
    elif task_id == "connect_wallet":
        # Check if Solana wallet address is filled
        if profile and profile.get("wallet_address"):
            success = True
            
    else:
        # Custom future tasks stub
        success = False
        
    if success:
        # Mark as completed and award points
        await database.complete_user_task(user_id, task_id)
        await database.add_points(user_id, reward)
        
        # Display success alert
        toast_text = _("task_check_success", task_name=task_name, points=reward)
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
