import asyncio
import logging
from aiogram import Bot, Dispatcher
from aiogram.enums import ParseMode
from aiogram.client.default import DefaultBotProperties
from aiogram.webhook.aiohttp_server import SimpleRequestHandler, setup_application
from aiohttp import web

import config
from handlers import main_router
from middlewares.throttling import ThrottlingMiddleware
from middlewares.i18n import I18nMiddleware

logger = logging.getLogger("MolumBot.Main")

async def on_startup(bot: Bot):
    logger.info("Bot is starting up...")
    if config.WEBHOOK_URL:
        webhook_path = "/webhook"
        full_webhook_url = f"{config.WEBHOOK_URL.rstrip('/')}{webhook_path}"
        logger.info(f"Setting webhook URL to: {full_webhook_url}")
        # Setting webhook and dropping pending updates to prevent backlog flood
        await bot.set_webhook(url=full_webhook_url, drop_pending_updates=True)
    else:
        logger.info("No webhook URL configured. Clearing webhook and starting in polling mode.")
        await bot.delete_webhook(drop_pending_updates=True)

async def on_shutdown(bot: Bot):
    logger.info("Bot is shutting down...")
    # Optional: notify admins or perform cleanup

def main():
    if not config.BOT_TOKEN:
        logger.critical("BOT_TOKEN is missing! Please set it in .env file before running the bot.")
        return

    # Initialize bot with default HTML parse mode
    bot = Bot(
        token=config.BOT_TOKEN,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML)
    )
    
    # Initialize dispatcher
    dp = Dispatcher()
    
    # Register Middlewares
    # Throttling/anti-spam limits (1.0s limit per user)
    dp.message.middleware(ThrottlingMiddleware(limit=1.0))
    dp.callback_query.middleware(ThrottlingMiddleware(limit=1.0))
    
    # Multi-language localization middleware
    dp.message.middleware(I18nMiddleware())
    dp.callback_query.middleware(I18nMiddleware())
    
    # Register handlers
    dp.include_router(main_router)
    
    # Register lifecycle callbacks
    dp.startup.register(on_startup)
    dp.shutdown.register(on_shutdown)
    
    if config.WEBHOOK_URL:
        # AIOHTTP webhook setup
        logger.info(f"Starting webhook server on port {config.PORT}...")
        app = web.Application()
        
        SimpleRequestHandler(
            dispatcher=dp,
            bot=bot
        ).register(app, path="/webhook")
        
        setup_application(app, dp, bot=bot)
        
        web.run_app(app, host="0.0.0.0", port=config.PORT)
    else:
        # Long Polling setup
        logger.info("Starting polling...")
        
        # We run the polling loop using asyncio.run
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            loop.run_until_complete(dp.start_polling(bot))
        except KeyboardInterrupt:
            logger.info("Stopped by user.")
        finally:
            loop.close()

if __name__ == "__main__":
    main()
