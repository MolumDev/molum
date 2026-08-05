import json
import logging
import asyncio
from typing import Callable
from aiogram import Router, F, Bot
from aiogram.types import Message
import database
from handlers.start import check_channel_subscription
from middlewares.throttling import delete_message_delayed

logger = logging.getLogger("MolumBot.WebAppData")

router = Router()

@router.message(F.web_app_data)
async def web_app_data_handler(message: Message, _: Callable[..., str], bot: Bot):
    user_id = message.from_user.id
    raw_data = message.web_app_data.data
    logger.info(f"Received WebApp Data from user {user_id}: {raw_data}")
    
    profile = await database.get_profile(user_id)
    lang = profile.get("language_code", "en") if profile else "en"
    
    try:
        data = json.loads(raw_data)
    except json.JSONDecodeError:
        err_msg = await message.answer("⚠️ Error decoding Mini App data.")
        asyncio.create_task(delete_message_delayed(bot, message.chat.id, err_msg.message_id, 3.0))
        return

    data_type = data.get("type")
    
    if data_type == "wallet":
        address = data.get("address")
        if not address:
            err_msg = await message.answer("⚠️ Wallet address cannot be empty.")
            asyncio.create_task(delete_message_delayed(bot, message.chat.id, err_msg.message_id, 3.0))
            return
            
        # Update wallet address in DB
        await database.update_profile_wallet(user_id, address)
        
        # Check and award points for "connect_wallet" task
        task_status = await database.get_user_task_status(user_id, "connect_wallet")
        if not (task_status and task_status.get("completed")):
            all_tasks = await database.get_tasks()
            task_details = next((t for t in all_tasks if t["task_id"] == "connect_wallet"), None)
            reward = task_details["points_reward"] if task_details else 200
            
            await database.complete_user_task(user_id, "connect_wallet")
            await database.add_points(user_id, reward)
            
            if lang == "ru":
                conf_text = f"🔌 Кошелёк успешно подключен: `{address}`\n🎉 Начислено **+{reward} Баллов**!"
            else:
                conf_text = f"🔌 Wallet successfully connected: `{address}`\n🎉 Earned **+{reward} Points**!"
        else:
            if lang == "ru":
                conf_text = f"🔌 Адрес кошелька обновлен: `{address}`"
            else:
                conf_text = f"🔌 Wallet address updated to: `{address}`"
                
        # Send delayed deleted message
        msg = await message.answer(conf_text, parse_mode="Markdown")
        asyncio.create_task(delete_message_delayed(bot, message.chat.id, msg.message_id, 5.0))
        
        # Delete user's incoming webapp service message to keep chat perfectly clean
        try:
            await message.delete()
        except Exception:
            pass

    elif data_type == "task_check":
        task_id = data.get("task_id")
        if not task_id:
            return
            
        task_status = await database.get_user_task_status(user_id, task_id)
        if task_status and task_status.get("completed"):
            return
            
        all_tasks = await database.get_tasks()
        task_details = next((t for t in all_tasks if t["task_id"] == task_id), None)
        if not task_details:
            return
            
        reward = task_details["points_reward"]
        desc_key = task_details["description_key"]
        task_name = _(desc_key)
        
        success = False
        if task_id == "subscribe":
            success = await check_channel_subscription(bot, user_id)
            if success:
                await database.update_profile_subscription(user_id, True)
        elif task_id == "invite_3_friends":
            ref_count = await database.get_referral_count(user_id)
            if ref_count >= 3:
                success = True
        elif task_id == "connect_wallet":
            if profile and profile.get("wallet_address"):
                success = True
                
        if success:
            await database.complete_user_task(user_id, task_id)
            await database.add_points(user_id, reward)
            
            toast_text = _("task_check_success", task_name=task_name, points=reward)
            msg = await message.answer(toast_text, parse_mode="Markdown")
            asyncio.create_task(delete_message_delayed(bot, message.chat.id, msg.message_id, 5.0))
        else:
            msg = await message.answer(_("task_check_failed"), parse_mode="Markdown")
            asyncio.create_task(delete_message_delayed(bot, message.chat.id, msg.message_id, 4.0))
            
        # Delete user's incoming webapp service message
        try:
            await message.delete()
        except Exception:
            pass
