from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton, WebAppInfo
from aiogram.utils.keyboard import ReplyKeyboardBuilder, InlineKeyboardBuilder
from config import CHANNEL_USERNAME, MINI_APP_URL

def get_main_menu_keyboard(_, lang: str = "en") -> ReplyKeyboardMarkup:
    """Generates localized Reply Keyboard for Main Menu."""
    builder = ReplyKeyboardBuilder()
    
    # Retrieve translations
    btn_profile = _("btn_profile")
    btn_invite = _("btn_invite")
    btn_leaderboard = _("btn_leaderboard")
    btn_tasks = _("btn_tasks")
    btn_wallet = _("btn_wallet")
    btn_token = _("btn_token")
    btn_language = _("btn_language")
    
    # Grid: 2 columns, Language on its own row
    builder.button(text=btn_profile)
    builder.button(text=btn_invite)
    builder.button(text=btn_leaderboard)
    builder.button(text=btn_tasks)
    builder.button(text=btn_wallet)
    builder.button(text=btn_token)
    builder.adjust(2, 2, 2)
    
    # Language row
    builder.row(KeyboardButton(text=btn_language))
    
    return builder.as_markup(resize_keyboard=True)

def get_delete_button(_, lang: str = "en") -> InlineKeyboardButton:
    """Generates standard localized delete button."""
    return InlineKeyboardButton(text=_("btn_delete"), callback_data="delete_msg")

def get_subscription_keyboard(_, lang: str = "en") -> InlineKeyboardMarkup:
    """Keyboard shown when subscription check is needed."""
    builder = InlineKeyboardBuilder()
    
    # Channel subscribe link (standardizing to handle '@' in handle)
    username_clean = CHANNEL_USERNAME.replace("@", "")
    channel_url = f"https://t.me/{username_clean}"
    
    builder.button(text=_("btn_subscribe"), url=channel_url)
    builder.button(text=_("btn_check_sub"), callback_data="check_subscription")
    builder.button(text=_("btn_delete"), callback_data="delete_msg")
    
    builder.adjust(1, 1, 1)
    return builder.as_markup()

def get_profile_keyboard(_, lang: str = "en") -> InlineKeyboardMarkup:
    """Profile actions keyboard."""
    builder = InlineKeyboardBuilder()
    builder.button(text=get_delete_button(_, lang).text, callback_data=get_delete_button(_, lang).callback_data)
    return builder.as_markup()

def get_referral_keyboard(_, user_id: int, bot_username: str, lang: str = "en") -> InlineKeyboardMarkup:
    """Referral keyboard with Share option."""
    builder = InlineKeyboardBuilder()
    
    ref_link = f"https://t.me/{bot_username}?start=ref_{user_id}"
    share_text = f"Join%20Molum%20and%20claim%20your%20100%20points%20starter%20bonus!%20🚀%20"
    share_url = f"https://t.me/share/url?url={ref_link}&text={share_text}"
    
    builder.button(text="📢 Share Link" if lang == "en" else "📢 Поделиться ссылкой", url=share_url)
    builder.button(text=get_delete_button(_, lang).text, callback_data=get_delete_button(_, lang).callback_data)
    builder.adjust(1, 1)
    return builder.as_markup()

def get_leaderboard_keyboard(_, user_id: int, lang: str = "en") -> InlineKeyboardMarkup:
    """Leaderboard keyboard opening Mini App."""
    builder = InlineKeyboardBuilder()
    
    # Mini App link
    mini_app_url = f"{MINI_APP_URL}/?page=leaderboard&tg_id={user_id}&lang={lang}"
    builder.button(text=_("btn_open_miniapp"), web_app=WebAppInfo(url=mini_app_url))
    builder.button(text=get_delete_button(_, lang).text, callback_data=get_delete_button(_, lang).callback_data)
    builder.adjust(1, 1)
    return builder.as_markup()

def get_wallet_keyboard(_, user_id: int, lang: str = "en") -> InlineKeyboardMarkup:
    """Wallet keyboard with Connect Wallet option opening Mini App."""
    builder = InlineKeyboardBuilder()
    
    # Mini App wallet link
    mini_app_url = f"{MINI_APP_URL}/wallet?tg_id={user_id}&lang={lang}"
    builder.button(text=_("btn_connect_wallet"), web_app=WebAppInfo(url=mini_app_url))
    builder.button(text=get_delete_button(_, lang).text, callback_data=get_delete_button(_, lang).callback_data)
    builder.adjust(1, 1)
    return builder.as_markup()

def get_language_keyboard(_, lang: str = "en") -> InlineKeyboardMarkup:
    """Language selection keyboard."""
    builder = InlineKeyboardBuilder()
    builder.button(text="🇬🇧 English", callback_data="set_lang_en")
    builder.button(text="🇷🇺 Русский", callback_data="set_lang_ru")
    builder.button(text=get_delete_button(_, lang).text, callback_data=get_delete_button(_, lang).callback_data)
    builder.adjust(2, 1)
    return builder.as_markup()

def get_token_prelaunch_keyboard(_, lang: str = "en") -> InlineKeyboardMarkup:
    """Token prelaunch keyboard."""
    builder = InlineKeyboardBuilder()
    builder.button(text=_("btn_notify_me"), callback_data="notify_listing")
    builder.button(text=get_delete_button(_, lang).text, callback_data=get_delete_button(_, lang).callback_data)
    builder.adjust(1, 1)
    return builder.as_markup()

def get_token_live_keyboard(_, chart_url: str, lang: str = "en") -> InlineKeyboardMarkup:
    """Token live keyboard."""
    builder = InlineKeyboardBuilder()
    builder.button(text="📈 DexScreener Chart" if lang == "en" else "📈 График DexScreener", url=chart_url)
    builder.button(text=get_delete_button(_, lang).text, callback_data=get_delete_button(_, lang).callback_data)
    builder.adjust(1, 1)
    return builder.as_markup()

def get_tasks_keyboard(_, tasks: list, completed_task_ids: set, lang: str = "en") -> InlineKeyboardMarkup:
    """Generates inline keyboard for active tasks."""
    builder = InlineKeyboardBuilder()
    
    for task in tasks:
        task_id = task["task_id"]
        reward = task["points_reward"]
        desc_key = task["description_key"]
        description = _(desc_key)
        
        if task_id in completed_task_ids:
            # Completed task: show ✅
            text = f"✅ {description} (+{reward})"
            builder.button(text=text, callback_data=f"task_checked_completed_{task_id}")
        else:
            # Incomplete: show checking button
            text = f"🔍 Check: {description} (+{reward})"
            builder.button(text=text, callback_data=f"check_task_{task_id}")
            
    builder.button(text=get_delete_button(_, lang).text, callback_data=get_delete_button(_, lang).callback_data)
    builder.adjust(*([1] * (len(tasks) + 1)))
    return builder.as_markup()

def get_admin_main_keyboard(_) -> InlineKeyboardMarkup:
    """Generates keyboard for admin panel."""
    builder = InlineKeyboardBuilder()
    builder.button(text=_("btn_stats"), callback_data="admin_stats")
    builder.button(text=_("btn_broadcast"), callback_data="admin_broadcast")
    builder.button(text=_("btn_manual_points"), callback_data="admin_manual_points")
    builder.button(text=_("btn_change_token"), callback_data="admin_change_token")
    builder.button(text=_("btn_view_users"), callback_data="admin_view_users")
    builder.button(text=_("btn_clean_db_admin"), callback_data="admin_clean_db_confirm")
    builder.button(text=_("btn_delete"), callback_data="delete_msg")
    builder.adjust(2, 2, 2, 1)
    return builder.as_markup()

def get_admin_clean_confirm_keyboard(_) -> InlineKeyboardMarkup:
    """Clean database confirmation keyboard."""
    builder = InlineKeyboardBuilder()
    builder.button(text=_("btn_confirm_clean"), callback_data="admin_clean_db_yes")
    builder.button(text=_("btn_cancel"), callback_data="admin_panel_back")
    builder.adjust(1, 1)
    return builder.as_markup()

def get_admin_token_keyboard(_) -> InlineKeyboardMarkup:
    """Admin token settings keyboard."""
    builder = InlineKeyboardBuilder()
    builder.button(text=_("btn_set_prelaunch"), callback_data="admin_token_prelaunch")
    builder.button(text=_("btn_set_live"), callback_data="admin_token_live")
    builder.button(text=_("btn_set_listing_date"), callback_data="admin_token_listing_date")
    builder.button(text=_("btn_cancel"), callback_data="admin_panel_back")
    builder.adjust(2, 1, 1)
    return builder.as_markup()
