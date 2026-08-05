import os
import logging
from dotenv import load_dotenv

# Set up logging configuration
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("MolumBot")

# Load environment variables
load_dotenv()

# Essential Bot Settings
BOT_TOKEN = os.getenv("BOT_TOKEN")
if not BOT_TOKEN:
    logger.warning("BOT_TOKEN is not set in environment! The bot will not start without a valid token.")

# Supabase Settings
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_SERVICE_KEY = os.getenv("SUPABASE_SERVICE_KEY")

if not SUPABASE_URL or not SUPABASE_SERVICE_KEY:
    logger.warning("SUPABASE_URL or SUPABASE_SERVICE_KEY not set. Real DB integration is disabled. Local mock mode (SQLite) is enabled.")

# Project settings
CHANNEL_USERNAME = os.getenv("CHANNEL_USERNAME", "@molum_chain_official")
MINI_APP_URL = os.getenv("MINI_APP_URL", "https://molum-miniapp.vercel.app")

# Webhook deployment settings (for hosting platforms like Render or Heroku)
WEBHOOK_URL = os.getenv("WEBHOOK_URL") # E.g. https://your-app.onrender.com/webhook
PORT = int(os.getenv("PORT", "8080"))

# Admin user IDs - parse from comma separated list
admin_ids_raw = os.getenv("ADMIN_IDS", "")
ADMIN_IDS = []
if admin_ids_raw:
    for aid in admin_ids_raw.split(","):
        try:
            ADMIN_IDS.append(int(aid.strip()))
        except ValueError:
            pass

# Fallback: if ADMIN_IDS is empty, log warning
if not ADMIN_IDS:
    logger.warning("ADMIN_IDS is empty. Admin features will be inaccessible.")

logger.info(f"Loaded config: CHANNEL={CHANNEL_USERNAME}, MINI_APP_URL={MINI_APP_URL}, ADMINS={ADMIN_IDS}, PORT={PORT}, WEBHOOK_URL={WEBHOOK_URL}")
