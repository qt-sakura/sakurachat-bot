from pyrogram import Client
from pyrogram.enums import ChatAction
from Sakura.Core.helpers import log_action

async def send_typing(client: Client, chat_id: int, user_info: dict) -> None:
    """Send typing action to show bot is processing"""
    log_action("DEBUG", "⌨️ Sending typing action", user_info)
    await client.send_chat_action(chat_id=chat_id, action=ChatAction.TYPING)

async def photo_action(client: Client, chat_id: int, user_info: dict) -> None:
    """Send upload photo action"""
    log_action("DEBUG", "📷 Sending photo upload action", user_info)
    await client.send_chat_action(chat_id=chat_id, action=ChatAction.UPLOAD_PHOTO)

async def sticker_action(client: Client, chat_id: int, user_info: dict) -> None:
    """Send choosing sticker action"""
    log_action("DEBUG", "🎭 Sending sticker choosing action", user_info)
    await client.send_chat_action(chat_id=chat_id, action=ChatAction.CHOOSE_STICKER)