import os
import asyncio
import threading
import uvloop
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    PreCheckoutQueryHandler,
    filters,
    ChatMemberHandler,
)
from telegram import Update
from http.server import BaseHTTPRequestHandler, HTTPServer

from .commands import admin, basic
from .core import callbacks, payments, handlers, effects, memory
from .utils import logging, helpers
from .database import db, cache
from .config.settings import BOT_TOKEN
from .config.constants import COMMANDS

def setup_handlers(application: Application) -> None:
    """Setup all command and message handlers"""
    application.add_handler(CommandHandler("start", basic.start_command))
    application.add_handler(CommandHandler("help", basic.help_command))
    application.add_handler(CommandHandler("ping", basic.ping_command))
    application.add_handler(CommandHandler("buy", basic.buy_command))
    application.add_handler(CommandHandler("buyers", basic.buyers_command))

    application.add_handler(CommandHandler("broadcast", admin.broadcast_command))
    application.add_handler(CommandHandler("stats", admin.stats_command))

    application.add_handler(CallbackQueryHandler(callbacks.start_callback, pattern="^start_"))
    application.add_handler(CallbackQueryHandler(callbacks.help_callback, pattern="^help_expand_"))
    application.add_handler(CallbackQueryHandler(callbacks.broadcast_callback, pattern="^bc_|^get_flowers_again$"))
    application.add_handler(CallbackQueryHandler(callbacks.stats_refresh_callback, pattern="^refresh_stats$"))

    application.add_handler(PreCheckoutQueryHandler(payments.precheckout_callback))
    application.add_handler(MessageHandler(filters.SUCCESSFUL_PAYMENT, payments.successful_payment_callback))

    application.add_handler(MessageHandler(
        filters.TEXT | filters.Sticker.ALL | filters.VOICE | filters.VIDEO_NOTE |
        filters.PHOTO | filters.Document.ALL | filters.POLL & ~filters.COMMAND,
        handlers.handle_all_messages
    ))

    application.add_handler(ChatMemberHandler(handlers.handle_chat_member_update, ChatMemberHandler.MY_CHAT_MEMBER))
    application.add_error_handler(handlers.error_handler)

async def setup_bot_commands(application: Application) -> None:
    """Setup bot commands menu"""
    await application.bot.set_my_commands(COMMANDS)

def run_bot() -> None:
    """Run the bot"""
    logger = logging.setup_colored_logging()
    if not helpers.validate_config():
        return

    logger.info("🚀 Initializing Sakura Bot...")
    application = Application.builder().token(BOT_TOKEN).concurrent_updates(True).build()
    setup_handlers(application)

    async def post_init(app):
        await cache.init_valkey()
        await db.init_database()
        await effects.start_effects_client()
        await setup_bot_commands(app)
        asyncio.create_task(memory.cleanup_old_conversations())
        logger.info("🌸 Sakura Bot initialization completed!")

    async def post_shutdown(app):
        await db.close_database()
        await cache.close_valkey()
        await effects.stop_effects_client()
        logger.info("🌸 Sakura Bot shutdown completed!")

    application.post_init = post_init
    application.post_shutdown = post_shutdown
    logger.info("🌸 Sakura Bot is starting...")
    application.run_polling(allowed_updates=Update.ALL_TYPES, drop_pending_updates=True)

class DummyHandler(BaseHTTPRequestHandler):
    """Simple HTTP handler for keep-alive server"""
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"Sakura bot is alive!")
    def do_HEAD(self):
        self.send_response(200)
        self.end_headers()
    def log_message(self, format, *args):
        pass

def start_dummy_server() -> None:
    """Start dummy HTTP server for deployment platforms"""
    port = int(os.environ.get("PORT", 10000))
    server = HTTPServer(("0.0.0.0", port), DummyHandler)
    # The logger is not available here, so we use print
    print(f"🌐 Dummy server listening on port {port}")
    server.serve_forever()

def main() -> None:
    """Main function"""
    try:
        uvloop.install()
    except ImportError:
        pass  # uvloop not available

    # The logger is not available here, so we use print
    print("🌸 Sakura Bot starting up...")
    threading.Thread(target=start_dummy_server, daemon=True).start()
    run_bot()

if __name__ == "__main__":
    main()
