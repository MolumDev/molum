import json
import logging
import asyncio
from typing import Callable
from aiogram import Router, F, Bot
from aiogram.types import Message
import database
from handlers.tasks import check_chat_membership
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
            reward = task_details["points"] if task_details else 200
            
            await database.complete_user_task(user_id, "connect_wallet")
            await database.add_points(user_id, reward)
            
            if lang == "ru":
                conf_text = f"🔌 Кошелёк успешно подключен: <code>{address}</code>\n🎉 Начислено <b>+{reward} Баллов</b>!"
            else:
                conf_text = f"🔌 Wallet successfully connected: <code>{address}</code>\n🎉 Earned <b>+{reward} Points</b>!"
        else:
            if lang == "ru":
                conf_text = f"🔌 Адрес кошелька обновлен: <code>{address}</code>"
            else:
                conf_text = f"🔌 Wallet address updated to: <code>{address}</code>"
                
        # Send delayed deleted message
        msg = await message.answer(conf_text, parse_mode="HTML")
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
            # Task already completed
            return
            
        all_tasks = await database.get_tasks()
        task_details = next((t for t in all_tasks if t["task_id"] == task_id), None)
        if not task_details:
            return
            
        reward = task_details["points"]
        task_name = task_details["title_ru"] if lang == "ru" else task_details["title_en"]
        verify_type = task_details.get("verify_type", "bot")
        verify_chat = task_details.get("verify_chat")
        verify_value = task_details.get("verify_value")
        
        success = False
        
        if verify_type == "channel":
            chat_to_check = verify_chat or "@molum_chain_official"
            success = await check_chat_membership(bot, user_id, chat_to_check)
            if success:
                await database.update_profile_subscription(user_id, True)
                
        elif verify_type == "chat":
            chat_to_check = verify_chat or "@molum_chat"
            success = await check_chat_membership(bot, user_id, chat_to_check)
            
        elif verify_type == "referrals":
            ref_count = await database.get_referral_count(user_id)
            req_value = verify_value or 3
            if ref_count >= req_value:
                success = True
                
        elif verify_type == "wallet":
            if profile and profile.get("wallet_address"):
                success = True
                
        elif verify_type == "bot":
            # Direct complete
            success = True
            
        if success:
            await database.complete_user_task(user_id, task_id)
            await database.add_points(user_id, reward)
            
            toast_text = _("task_check_success", task_name=task_name, points=reward)
            msg = await message.answer(toast_text, parse_mode="HTML")
            asyncio.create_task(delete_message_delayed(bot, message.chat.id, msg.message_id, 5.0))
        else:
            msg = await message.answer(_("task_check_failed"), parse_mode="HTML")
            asyncio.create_task(delete_message_delayed(bot, message.chat.id, msg.message_id, 4.0))
            
        # Delete user's incoming webapp service message
        try:
            await message.delete()
        except Exception:
            pass
