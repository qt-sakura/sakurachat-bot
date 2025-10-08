import random
from pyrogram import Client
from pyrogram.types import Message, InlineKeyboardMarkup
from pyrogram.errors import RPCError
from Sakura.Core.logging import logger

EFFECTS = [
    "5104841245755180586",
    "5159385139981059251"
]

async def send_effect(
    client: Client,
    chat_id: int,
    text: str,
    reply_markup: InlineKeyboardMarkup = None
) -> bool:
    """Send message with random effect using the main Pyrogram client."""
    try:
        await client.send_message(
            chat_id=chat_id,
            text=text,
            reply_markup=reply_markup,
            message_effect_id=random.choice(EFFECTS),
            parse_mode='HTML'
        )
        return True
    except RPCError as e:
        logger.error(f"❌ Effect error for {chat_id}: {e}")
        return False
    except Exception as e:
        logger.error(f"❌ Unexpected error in send_effect for {chat_id}: {e}")
        return False

async def animate_reaction(
    client: Client,
    chat_id: int,
    message_id: int,
    emoji: str
) -> bool:
    """Send animated emoji reaction using the main Pyrogram client."""
    try:
        await client.set_message_reaction(
            chat_id=chat_id,
            message_id=message_id,
            reaction=[{'type': 'emoji', 'emoji': emoji}],
            is_big=True
        )
        return True
    except RPCError as e:
        logger.error(f"❌ Animated reaction error for {chat_id}: {e}")
        return False
    except Exception as e:
        logger.error(f"❌ Unexpected error in animate_reaction for {chat_id}: {e}")
        return False

async def add_reaction(message: Message, emoji: str):
    """Fallback reaction without animation."""
    try:
        await message.react(emoji)
    except Exception as e:
        logger.warning(f"⚠️ Reaction fallback failed: {e}")

async def photo_effect(
    client: Client,
    chat_id: int,
    photo_url: str,
    caption: str,
    reply_markup: InlineKeyboardMarkup = None
) -> bool:
    """Send photo message with random effect using the main Pyrogram client."""
    try:
        await client.send_photo(
            chat_id=chat_id,
            photo=photo_url,
            caption=caption,
            reply_markup=reply_markup,
            message_effect_id=random.choice(EFFECTS),
            parse_mode='HTML'
        )
        return True
    except RPCError as e:
        logger.error(f"❌ Photo effect error for {chat_id}: {e}")
        return False
    except Exception as e:
        logger.error(f"❌ Unexpected error in photo_effect for {chat_id}: {e}")
        return False