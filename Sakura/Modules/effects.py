import random
from pyrogram import Client
from pyrogram.types import Message
from pyrogram.enums import ParseMode
from Sakura.Core.logging import logger

EFFECTS = [
    "5104841245755180586",
    "5159385139981059251"
]

async def send_effect(client: Client, chat_id: int, text: str, reply_markup=None) -> bool:
    """Send message with random effect using Pyrogram"""
    try:
        await client.send_message(
            chat_id=chat_id,
            text=text,
            reply_markup=reply_markup,
            parse_mode=ParseMode.HTML
        )
        return True
    except Exception as e:
        logger.error(f"❌ Effect error for {chat_id}: {e}")
        return False

async def animate_reaction(client: Client, chat_id: int, message_id: int, emoji: str) -> bool:
    """Send animated emoji reaction using Pyrogram"""
    try:
        await client.send_reaction(
            chat_id=chat_id,
            message_id=message_id,
            emoji=emoji
        )
        return True
    except Exception as e:
        logger.error(f"❌ Animated reaction error for {chat_id}: {e}")
        return False

async def add_reaction(client: Client, message: Message, emoji: str, user_info: dict):
    """Fallback reaction without animation"""
    try:
        await message.react(emoji)
    except Exception as e:
        from Sakura.Core.helpers import log_action
        log_action("WARNING", f"⚠️ Reaction fallback failed: {e}", user_info)

async def photo_effect(client: Client, chat_id: int, photo_url: str, caption: str, reply_markup=None) -> bool:
    """Send photo message with random effect using Pyrogram"""
    try:
        await client.send_photo(
            chat_id=chat_id,
            photo=photo_url,
            caption=caption,
            reply_markup=reply_markup,
            parse_mode=ParseMode.HTML
        )
        return True
    except Exception as e:
        logger.error(f"❌ Photo effect error for {chat_id}: {e}")
        return False