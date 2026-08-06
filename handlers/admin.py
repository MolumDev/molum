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
    waiting_for_conversion_rate = State()
    waiting_for_contest_title = State()
    waiting_for_contest_description = State()
    waiting_for_contest_reward = State()

# Custom Admin Filter
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

# --- BACK TO MAIN PANEL ---
@router.callback_query(F.data == "admin_panel_back", IsAdmin())
async def cb_admin_back(callback: CallbackQuery, _: Callable[..., str], state: FSMContext):
    await state.clear()
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
            users_str += f"• <code>{u['telegram_id']}</code>: {username} | 💰 <code>{u['total_points']}</code> | 📅 {date_str}\n"
            
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
    
    try:
        await callback.message.edit_text(text, reply_markup=builder.as_markup(), parse_mode="HTML")
    except Exception as e:
        logger.debug(f"Failed to prompt manual points: {e}")
    await callback.answer()

@router.message(AdminStates.waiting_for_manual_points, IsAdmin())
async def process_manual_points(message: Message, state: FSMContext, _: Callable[..., str]):
    text = message.text.strip()
    parts = text.split()
    if len(parts) == 2:
        try:
            target_user_id = int(parts[0])
            points_change = int(parts[1])
            
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
                
                kb = keyboards.get_admin_main_keyboard(_)
                await message.answer(_("admin_panel_title"), reply_markup=kb, parse_mode="HTML")
                return
        except ValueError:
            pass
            
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
    await database.update_setting("token_status", "prelaunch")
    await callback.answer(_("token_status_changed", status="prelaunch"), show_alert=True)
    
    kb = keyboards.get_admin_token_keyboard(_)
    try:
        await callback.message.edit_text("🚀 **Manage Token Settings**\nUpdate token launch status or reschedule the listing countdown date.", reply_markup=kb, parse_mode="HTML")
    except Exception as e:
        logger.debug(f"Failed to update token menu: {e}")

@router.callback_query(F.data == "admin_token_live", IsAdmin())
async def cb_admin_token_live(callback: CallbackQuery, _: Callable[..., str]):
    await database.update_setting("token_status", "live")
    price = await database.get_setting("token_price")
    if not price:
        await database.update_setting("token_price", "0.0042")
        await database.update_setting("token_chart_url", "https://dexscreener.com")
        
    await callback.answer(_("token_status_changed", status="live"), show_alert=True)
    
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
        
    try:
        clean_str = date_text.replace("Z", "+00:00")
        datetime.datetime.fromisoformat(clean_str)
        
        await database.update_setting("listing_date", date_text)
        await message.answer(_("listing_date_updated", date=date_text), parse_mode="HTML")
        await state.clear()
        
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

# ============================================================
# NEW EXPANDED FEATURES: SNAPSHOTS & CONTESTS (Admin Flow)
# ============================================================

# --- SNAPSHOT & RATE FLOW ---
@router.callback_query(F.data == "admin_claim_snapshot_prompt", IsAdmin())
async def cb_claim_snapshot_prompt(callback: CallbackQuery, _: Callable[..., str], state: FSMContext):
    text = "📸 <b>Wallets Snapshot & Conversion Rate</b>\n\nEnter the conversion rate (Points per Token).\n\n<i>Example: If 10, then 10 points = 1 token. A user with 100 points will receive 10 tokens.</i>"
    
    from aiogram.utils.keyboard import InlineKeyboardBuilder
    builder = InlineKeyboardBuilder()
    builder.button(text=_("btn_cancel"), callback_data="admin_panel_back")
    
    await state.set_state(AdminStates.waiting_for_conversion_rate)
    
    try:
        await callback.message.edit_text(text, reply_markup=builder.as_markup(), parse_mode="HTML")
    except Exception as e:
        logger.debug(f"Failed to prompt snapshot rate: {e}")
    await callback.answer()

@router.message(AdminStates.waiting_for_conversion_rate, IsAdmin())
async def process_snapshot_rate(message: Message, state: FSMContext, _: Callable[..., str]):
    rate_text = message.text.strip()
    try:
        rate = float(rate_text)
        if rate <= 0:
            await message.answer("❌ Conversion rate must be greater than 0.")
            return
            
        await state.update_data(conversion_rate=rate)
        
        text = f"📸 <b>Snapshot Confirmation</b>\n\nYou are about to take a snapshot of all user balances with the rate:\n<code>{rate} Points = 1 Token</code>\n\nThis will calculate allocated tokens and save them to the <code>claim_snapshots</code> table so users can claim them on their Mini App!\n\nAre you ready?"
        kb = keyboards.get_admin_snapshot_confirm_keyboard()
        await message.answer(text, reply_markup=kb, parse_mode="HTML")
    except ValueError:
        await message.answer("❌ Invalid number! Please enter a numerical conversion rate (e.g. 10 or 2.5).")

@router.callback_query(F.data == "admin_claim_snapshot_run", IsAdmin())
async def cb_claim_snapshot_run(callback: CallbackQuery, _: Callable[..., str], state: FSMContext):
    state_data = await state.get_data()
    rate = state_data.get("conversion_rate")
    
    if not rate:
        await callback.answer("Error! Lost state data.", show_alert=True)
        return
        
    await callback.message.edit_text("📸 Taking database snapshot... Please wait.")
    
    success = await database.create_claim_snapshot(rate)
    await state.clear()
    
    if success:
        await callback.answer("🎉 Snapshot completed successfully! Tokens allocated.", show_alert=True)
        text = f"🎉 <b>Snapshot Completed!</b>\n\nSuccessfully captured all connected wallets and allocated tokens at rate: <code>{rate} pts = 1 Token</code>.\n\nClaim snapshots are now live and visible in the Mini App!"
    else:
        text = "❌ Error taking snapshot. Please check server logs."
        
    from aiogram.utils.keyboard import InlineKeyboardBuilder
    builder = InlineKeyboardBuilder()
    builder.button(text="OK", callback_data="admin_panel_back")
    
    await callback.message.edit_text(text, reply_markup=builder.as_markup(), parse_mode="HTML")

# --- CONTESTS FLOW ---
@router.callback_query(F.data == "admin_contest_create", IsAdmin())
async def cb_contest_create_prompt(callback: CallbackQuery, _: Callable[..., str], state: FSMContext):
    text = "🏆 <b>Create New Community Contest</b>\n\nEnter the title of the contest (e.g. <i>Best meme of the week</i>):"
    
    from aiogram.utils.keyboard import InlineKeyboardBuilder
    builder = InlineKeyboardBuilder()
    builder.button(text=_("btn_cancel"), callback_data="admin_panel_back")
    
    await state.set_state(AdminStates.waiting_for_contest_title)
    
    try:
        await callback.message.edit_text(text, reply_markup=builder.as_markup(), parse_mode="HTML")
    except Exception as e:
        logger.debug(f"Failed to prompt contest title: {e}")
    await callback.answer()

@router.message(AdminStates.waiting_for_contest_title, IsAdmin())
async def process_contest_title(message: Message, state: FSMContext, _: Callable[..., str]):
    title = message.text.strip()
    await state.update_data(contest_title=title)
    
    await state.set_state(AdminStates.waiting_for_contest_description)
    await message.answer("🏆 <b>Contest Description</b>\n\nEnter description/instructions of the contest:")

@router.message(AdminStates.waiting_for_contest_description, IsAdmin())
async def process_contest_desc(message: Message, state: FSMContext, _: Callable[..., str]):
    desc = message.text.strip()
    await state.update_data(contest_desc=desc)
    
    await state.set_state(AdminStates.waiting_for_contest_reward)
    await message.answer("🏆 <b>Contest Reward</b>\n\nEnter the point reward to be awarded to approved entries (e.g., <code>500</code>):")

@router.message(AdminStates.waiting_for_contest_reward, IsAdmin())
async def process_contest_reward(message: Message, state: FSMContext, _: Callable[..., str]):
    reward_text = message.text.strip()
    try:
        reward = int(reward_text)
        if reward <= 0:
            await message.answer("❌ Reward must be greater than 0.")
            return
            
        state_data = await state.get_data()
        title = state_data.get("contest_title")
        description = state_data.get("contest_desc")
        
        # Save contest in DB
        contest_id = await database.create_contest(title, description, reward)
        await state.clear()
        
        text = f"🎉 <b>Contest Created Successfully!</b>\n\n🆔 ID: <code>{contest_id}</code>\n🏆 Title: {title}\n📝 Description: {description}\n💰 Reward: <code>{reward} Points</code>"
        
        from aiogram.utils.keyboard import InlineKeyboardBuilder
        builder = InlineKeyboardBuilder()
        builder.button(text="OK", callback_data="admin_panel_back")
        
        await message.answer(text, reply_markup=builder.as_markup(), parse_mode="HTML")
    except ValueError:
        await message.answer("❌ Invalid number! Please enter a numerical reward (e.g., 500).")

# --- CONTEST SUBMISSIONS EVALUATION ---
@router.callback_query(F.data == "admin_contest_submissions", IsAdmin())
async def cb_contest_submissions(callback: CallbackQuery, _: Callable[..., str]):
    subs = await database.get_pending_submissions()
    
    if not subs:
        from aiogram.utils.keyboard import InlineKeyboardBuilder
        builder = InlineKeyboardBuilder()
        builder.button(text="Back / Назад", callback_data="admin_panel_back")
        
        await callback.message.edit_text("📥 <b>No pending submissions at the moment!</b>", reply_markup=builder.as_markup(), parse_mode="HTML")
        await callback.answer()
        return
        
    # Show first submission
    sub = subs[0]
    sub_id = sub["id"]
    username = f"@{sub['username']}" if sub.get("username") else f"User ID {sub['telegram_id']}"
    
    text = f"📥 <b>Pending Contest Submission ({len(subs)} left)</b>\n\n🏆 Contest: <b>{sub['title']}</b>\n👤 User: {username}\n💰 Reward: <code>{sub['reward_points']} Points</code>\n\n🔗 <b>Submission Link:</b>\n{sub['submission_link']}\n\nApprove or Reject below:"
    kb = keyboards.get_submission_approve_reject_keyboard(sub_id)
    
    try:
        await callback.message.edit_text(text, reply_markup=kb, parse_mode="HTML", disable_web_page_preview=False)
    except Exception as e:
        logger.debug(f"Failed to display submission: {e}")
    await callback.answer()

@router.callback_query(F.data.startswith("admin_sub_approve_"), IsAdmin())
async def cb_sub_approve(callback: CallbackQuery, _: Callable[..., str], bot: Bot):
    sub_id = int(callback.data.split("admin_sub_approve_")[1])
    
    # Approve and reward in DB
    # Fetch details first for notification
    subs = await database.get_pending_submissions()
    sub_details = next((s for s in subs if s["id"] == sub_id), None)
    
    success = await database.approve_submission(sub_id)
    
    if success:
        await callback.answer("✅ Submission Approved!", show_alert=True)
        if sub_details:
            user_id = sub_details["telegram_id"]
            contest_title = sub_details["title"]
            reward = sub_details["reward_points"]
            
            # Notify user
            try:
                user_msg_en = f"🎉 <b>Meme Contest Update!</b>\n\nYour submission for <b>\"{contest_title}\"</b> has been **APPROVED**! 🏆\n\nYou have been awarded <b>+{reward} Points</b>!"
                await bot.send_message(chat_id=user_id, text=user_msg_en, parse_mode="HTML")
            except Exception:
                pass
    else:
        await callback.answer("❌ Error approving submission.", show_alert=True)
        
    # Reload submissions
    await cb_contest_submissions(callback, _)

@router.callback_query(F.data.startswith("admin_sub_reject_"), IsAdmin())
async def cb_sub_reject(callback: CallbackQuery, _: Callable[..., str], bot: Bot):
    sub_id = int(callback.data.split("admin_sub_reject_")[1])
    
    # Reject submission in DB
    success = await database.reject_submission(sub_id)
    
    if success:
        await callback.answer("❌ Submission Rejected!", show_alert=True)
    else:
        await callback.answer("❌ Error rejecting submission.", show_alert=True)
        
    # Reload submissions
    await cb_contest_submissions(callback, _)

# Global state cancellation
@router.message(Command("cancel"))
@router.message(F.text.casefold() == "cancel")
async def cmd_cancel(message: Message, state: FSMContext, _: Callable[..., str]):
    current_state = await state.get_state()
    if current_state is None:
        return
    await state.clear()
    await message.answer("❌ FSM Action cancelled. / Действие отменено.")
