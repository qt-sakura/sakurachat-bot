import logging
from telegram.ext import ContextTypes
from telegram.constants import ChatAction
from .messages import log_with_user_info

logger = logging.getLogger("SAKURA 🌸")

async def send_typing_action(context: ContextTypes.DEFAULT_TYPE, chat_id: int, user_info: dict) -> None:
    """Send typing action to show bot is processing"""
    log_with_user_info("DEBUG", "⌨️ Sending typing action", user_info)
    await context.bot.send_chat_action(chat_id=chat_id, action=ChatAction.TYPING)


async def send_photo_action(context: ContextTypes.DEFAULT_TYPE, chat_id: int, user_info: dict) -> None:
    """Send upload photo action"""
    log_with_user_info("DEBUG", "📷 Sending photo upload action", user_info)
    await context.bot.send_chat_action(chat_id=chat_id, action=ChatAction.UPLOAD_PHOTO)


async def send_sticker_action(context: ContextTypes.DEFAULT_TYPE, chat_id: int, user_info: dict) -> None:
    """Send choosing sticker action"""
    log_with_user_info("DEBUG", "🎭 Sending sticker choosing action", user_info)
    await context.bot.send_chat_action(chat_id=chat_id, action=ChatAction.CHOOSE_STICKER)
