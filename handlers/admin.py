import logging
import datetime
from typing import Callable
from aiogram import Router, F, Bot
from aiogram.filters import Command, Filter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import Message, CallbackQuery, TelegramObject
import database
import keyboards
from config import ADMIN_IDS

logger = logging.getLogger("MolumBot.AdminHandler")

router = Router()

# FSM States
class AdminStates(StatesGroup):
    waiting_for_broadcast_text = State()
    waiting_for_manual_points = State()
    waiting_for_listing_date = State()

# Simple Custom Filter to restrict access to ADMIN_IDS
class IsAdmin(Filter):
    async def __call__(self, event: TelegramObject) -> bool:
        user = getattr(event, "from_user", None)
        return user is not None and user.id in ADMIN_IDS

@router.message(Command("admin"))
async def cmd_admin(message: Message, _: Callable[..., str]):
    user_id = message.from_user.id
    logger.info(f"Admin command /admin triggered by user_id={user_id}. Current registered ADMIN_IDS={ADMIN_IDS}")
    
    if user_id in ADMIN_IDS:
        text = _("admin_panel_title")
        kb = keyboards.get_admin_main_keyboard(_)
        await message.answer(text, reply_markup=kb, parse_mode="HTML")
    else:
        logger.warning(f"Unauthorized /admin access attempt by user_id={user_id}. Permitted ADMIN_IDS={ADMIN_IDS}")
        await message.answer(_("admin_only"))

# --- BACK ACTION ---
@router.callback_query(F.data == "admin_panel_back", IsAdmin())
async def cb_admin_back(callback: CallbackQuery, _: Callable[..., str]):
    text = _("admin_panel_title")
    kb = keyboards.get_admin_main_keyboard(_)
    try:
        await callback.message.edit_text(text, reply_markup=kb, parse_mode="HTML")
    except Exception as e:
        logger.debug(f"Failed to edit admin menu: {e}")
    await callback.answer()

# --- STATISTICS ---
@router.callback_query(F.data == "admin_stats", IsAdmin())
async def cb_admin_stats(callback: CallbackQuery, _: Callable[..., str]):
    stats = await database.get_admin_stats()
    text = _(
        "stats_text",
        total_users=stats.get("total_users", 0),
        total_referrals=stats.get("total_referrals", 0),
        total_points=stats.get("total_points", 0)
    )
    
    # Simple inline keyboard to go back to admin main menu
    from aiogram.utils.keyboard import InlineKeyboardBuilder
    builder = InlineKeyboardBuilder()
    builder.button(text=_("btn_cancel"), callback_data="admin_panel_back")
    
    try:
        await callback.message.edit_text(text, reply_markup=builder.as_markup(), parse_mode="HTML")
    except Exception as e:
        logger.debug(f"Failed to show admin stats: {e}")
    await callback.answer()

# --- RECENT USERS ---
@router.callback_query(F.data == "admin_view_users", IsAdmin())
async def cb_admin_view_users(callback: CallbackQuery, _: Callable[..., str]):
    users = await database.get_recent_users(20)
    
    if not users:
        users_str = "No users found in database."
    else:
        users_str = ""
        for u in users:
            username = f"@{u['username']}" if u.get("username") else "No username"
            created_at = u.get("created_at")
            if isinstance(created_at, datetime.datetime):
                date_str = created_at.strftime("%Y-%m-%d")
            else:
                date_str = str(created_at)[:10] if created_at else "N/A"
            users_str += f"• `{u['telegram_id']}`: {username} | 💰 `{u['total_points']}` | 📅 {date_str}\n"
            
    text = _("admin_users_list", users_str=users_str)
    
    from aiogram.utils.keyboard import InlineKeyboardBuilder
    builder = InlineKeyboardBuilder()
    builder.button(text=_("btn_cancel"), callback_data="admin_panel_back")
    
    try:
        await callback.message.edit_text(text, reply_markup=builder.as_markup(), parse_mode="HTML")
    except Exception as e:
        logger.debug(f"Failed to view users: {e}")
    await callback.answer()

# --- MANUAL POINTS ---
@router.callback_query(F.data == "admin_manual_points", IsAdmin())
async def cb_admin_manual_points(callback: CallbackQuery, _: Callable[..., str], state: FSMContext):
    text = _("manual_points_prompt")
    
    from aiogram.utils.keyboard import InlineKeyboardBuilder
    builder = InlineKeyboardBuilder()
    builder.button(text=_("btn_cancel"), callback_data="admin_panel_back")
    
    await state.set_state(AdminStates.waiting_for_manual_points)
    # Save the original admin prompt message ID so we can clean up
    await state.update_data(prompt_msg_id=callback.message.message_id)
    
    try:
        await callback.message.edit_text(text, reply_markup=builder.as_markup(), parse_mode="HTML")
    except Exception as e:
        logger.debug(f"Failed to prompt manual points: {e}")
    await callback.answer()

@router.message(AdminStates.waiting_for_manual_points, IsAdmin())
async def process_manual_points(message: Message, state: FSMContext, _: Callable[..., str]):
    text = message.text.strip()
    
    # Try parsing format: "123456789 500"
    parts = text.split()
    if len(parts) == 2:
        try:
            target_user_id = int(parts[0])
            points_change = int(parts[1])
            
            # Fetch user to ensure existence and capture old balance
            profile = await database.get_profile(target_user_id)
            if profile:
                old_points = profile.get("total_points", 0)
                new_points = await database.add_points(target_user_id, points_change)
                
                success_text = _(
                    "manual_points_success",
                    user_id=target_user_id,
                    old_points=old_points,
                    new_points=new_points
                )
                await message.answer(success_text, parse_mode="HTML")
                await state.clear()
                
                # Show main admin menu again
                kb = keyboards.get_admin_main_keyboard(_)
                await message.answer(_("admin_panel_title"), reply_markup=kb, parse_mode="HTML")
                return
        except ValueError:
            pass
            
    # If parsing failed
    await message.answer(_("manual_points_failed"))

# --- BROADCAST ---
@router.callback_query(F.data == "admin_broadcast", IsAdmin())
async def cb_admin_broadcast(callback: CallbackQuery, _: Callable[..., str], state: FSMContext):
    text = _("broadcast_prompt")
    
    from aiogram.utils.keyboard import InlineKeyboardBuilder
    builder = InlineKeyboardBuilder()
    builder.button(text=_("btn_cancel"), callback_data="admin_panel_back")
    
    await state.set_state(AdminStates.waiting_for_broadcast_text)
    
    try:
        await callback.message.edit_text(text, reply_markup=builder.as_markup(), parse_mode="HTML")
    except Exception as e:
        logger.debug(f"Failed to prompt broadcast: {e}")
    await callback.answer()

@router.message(AdminStates.waiting_for_broadcast_text, IsAdmin())
async def process_admin_broadcast(message: Message, state: FSMContext, _: Callable[..., str], bot: Bot):
    broadcast_text = message.text
    
    if broadcast_text.strip() == "/cancel":
        await state.clear()
        kb = keyboards.get_admin_main_keyboard(_)
        await message.answer(_("admin_panel_title"), reply_markup=kb, parse_mode="HTML")
        return
        
    await message.answer("📢 Processing broadcast... Please wait.")
    await state.clear()
    
    # Fetch all user telegram_ids
    all_users = await database.get_all_users()
    
    success_count = 0
    failed_count = 0
    
    for uid in all_users:
        try:
            await bot.send_message(chat_id=uid, text=broadcast_text)
            success_count += 1
        except Exception as e:
            logger.warning(f"Could not broadcast message to user {uid}: {e}")
            failed_count += 1
            
    summary = _("broadcast_success", success=success_count, failed=failed_count)
    await message.answer(summary, parse_mode="HTML")
    
    # Return to admin panel
    kb = keyboards.get_admin_main_keyboard(_)
    await message.answer(_("admin_panel_title"), reply_markup=kb, parse_mode="HTML")

# --- TOKEN SETTINGS MENU ---
@router.callback_query(F.data == "admin_change_token", IsAdmin())
async def cb_admin_change_token(callback: CallbackQuery, _: Callable[..., str]):
    text = "🚀 **Manage Token Settings**\nUpdate token launch status or reschedule the listing countdown date."
    kb = keyboards.get_admin_token_keyboard(_)
    try:
        await callback.message.edit_text(text, reply_markup=kb, parse_mode="HTML")
    except Exception as e:
        logger.debug(f"Failed to show token settings: {e}")
    await callback.answer()

@router.callback_query(F.data == "admin_token_prelaunch", IsAdmin())
async def cb_admin_token_prelaunch(callback: CallbackQuery, _: Callable[..., str]):
    await database.update_setting("token_status", "pre-launch")
    await callback.answer(_("token_status_changed", status="pre-launch"), show_alert=True)
    
    # Return to token settings menu
    kb = keyboards.get_admin_token_keyboard(_)
    try:
        await callback.message.edit_text("🚀 **Manage Token Settings**\nUpdate token launch status or reschedule the listing countdown date.", reply_markup=kb, parse_mode="HTML")
    except Exception as e:
        logger.debug(f"Failed to update token menu: {e}")

@router.callback_query(F.data == "admin_token_live", IsAdmin())
async def cb_admin_token_live(callback: CallbackQuery, _: Callable[..., str]):
    await database.update_setting("token_status", "live")
    # Setup some default price & chart if not set
    price = await database.get_setting("token_price")
    if not price:
        await database.update_setting("token_price", "0.0042")
        await database.update_setting("token_chart_url", "https://dexscreener.com")
        
    await callback.answer(_("token_status_changed", status="live"), show_alert=True)
    
    # Return to token settings menu
    kb = keyboards.get_admin_token_keyboard(_)
    try:
        await callback.message.edit_text("🚀 **Manage Token Settings**\nUpdate token launch status or reschedule the listing countdown date.", reply_markup=kb, parse_mode="HTML")
    except Exception as e:
        logger.debug(f"Failed to update token menu: {e}")

@router.callback_query(F.data == "admin_token_listing_date", IsAdmin())
async def cb_admin_token_listing_date(callback: CallbackQuery, _: Callable[..., str], state: FSMContext):
    text = _("prompt_listing_date")
    
    from aiogram.utils.keyboard import InlineKeyboardBuilder
    builder = InlineKeyboardBuilder()
    builder.button(text=_("btn_cancel"), callback_data="admin_change_token")
    
    await state.set_state(AdminStates.waiting_for_listing_date)
    
    try:
        await callback.message.edit_text(text, reply_markup=builder.as_markup(), parse_mode="HTML")
    except Exception as e:
        logger.debug(f"Failed to prompt listing date: {e}")
    await callback.answer()

@router.message(AdminStates.waiting_for_listing_date, IsAdmin())
async def process_listing_date(message: Message, state: FSMContext, _: Callable[..., str]):
    date_text = message.text.strip()
    
    if date_text == "/cancel" or date_text.lower() == "cancel":
        await state.clear()
        kb = keyboards.get_admin_token_keyboard(_)
        await message.answer("🚀 **Manage Token Settings**", reply_markup=kb, parse_mode="HTML")
        return
        
    # Simple validation check: ISO 8601 parsing check
    try:
        # Check parsing
        clean_str = date_text.replace("Z", "+00:00")
        datetime.datetime.fromisoformat(clean_str)
        
        # Save to database settings
        await database.update_setting("listing_date", date_text)
        await message.answer(_("listing_date_updated", date=date_text), parse_mode="HTML")
        await state.clear()
        
        # Return to main admin panel
        kb = keyboards.get_admin_main_keyboard(_)
        await message.answer(_("admin_panel_title"), reply_markup=kb, parse_mode="HTML")
    except ValueError:
        await message.answer(_("invalid_date_format"))

# --- CLEAN DATABASE FLOW ---
@router.callback_query(F.data == "admin_clean_db_confirm", IsAdmin())
async def cb_admin_clean_db_confirm(callback: CallbackQuery, _: Callable[..., str]):
    text = "⚠️ **Database Cleanup Confirmation**\n\nAre you absolutely sure you want to clean the database?\nThis will **TRUNCATE CASCADE** all user profiles, referrals, notifications, and reset balances!\n\nThis action is **PERMANENT** and cannot be undone."
    kb = keyboards.get_admin_clean_confirm_keyboard(_)
    try:
        await callback.message.edit_text(text, reply_markup=kb, parse_mode="HTML")
    except Exception as e:
        logger.debug(f"Failed to prompt clean confirmation: {e}")
    await callback.answer()

@router.callback_query(F.data == "admin_clean_db_yes", IsAdmin())
async def cb_admin_clean_db_yes(callback: CallbackQuery, _: Callable[..., str]):
    success = await database.clean_database()
    
    if success:
        text = _("db_cleaned_success")
    else:
        text = "❌ An error occurred during database cleanup. Please check the logs."
        
    from aiogram.utils.keyboard import InlineKeyboardBuilder
    builder = InlineKeyboardBuilder()
    builder.button(text="OK", callback_data="admin_panel_back")
    
    try:
        await callback.message.edit_text(text, reply_markup=builder.as_markup(), parse_mode="HTML")
    except Exception as e:
        logger.debug(f"Failed to display clean success: {e}")
    await callback.answer()

# Command /clean_db with confirmation
@router.message(Command("clean_db"))
async def cmd_clean_db(message: Message, _: Callable[..., str]):
    user_id = message.from_user.id
    logger.info(f"Clean DB command /clean_db triggered by user_id={user_id}. Registered ADMIN_IDS={ADMIN_IDS}")
    
    if user_id in ADMIN_IDS:
        text = "⚠️ <b>Database Cleanup Confirmation</b>\n\nAre you absolutely sure you want to clean the database?\nThis will <b>TRUNCATE CASCADE</b> all user profiles, referrals, notifications, and reset balances!\n\nThis action is <b>PERMANENT</b>."
        kb = keyboards.get_admin_clean_confirm_keyboard(_)
        await message.answer(text, reply_markup=kb, parse_mode="HTML")
    else:
        logger.warning(f"Unauthorized /clean_db attempt by user_id={user_id}. Permitted ADMIN_IDS={ADMIN_IDS}")
        await message.answer(_("admin_only"))

# Global cancel helper inside States
@router.message(Command("cancel"))
@router.message(F.text.casefold() == "cancel")
async def cmd_cancel(message: Message, state: FSMContext, _: Callable[..., str]):
    current_state = await state.get_state()
    if current_state is None:
        return
    await state.clear()
    await message.answer("❌ FSM Action cancelled. / Действие отменено.")
