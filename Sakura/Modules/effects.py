import random
import aiohttp
import orjson
from pyrogram import Client
from pyrogram.types import Message, InlineKeyboardMarkup

from Sakura.Core.config import BOT_TOKEN
from Sakura.Core.logging import logger

EFFECTS = [
    "5104841245755180586",
    "5159385139981059251"
]

def serialize_reply_markup(reply_markup):
    """Serializes a Pyrogram InlineKeyboardMarkup to a JSON-compatible dict."""
    if not reply_markup:
        return None
    if isinstance(reply_markup, InlineKeyboardMarkup):
        keyboard = []
        for row in reply_markup.inline_keyboard:
            new_row = []
            for button in row:
                new_button = {"text": button.text}
                if button.callback_data:
                    new_button["callback_data"] = button.callback_data
                if button.url:
                    new_button["url"] = button.url
                new_row.append(new_button)
            keyboard.append(new_row)
        return {"inline_keyboard": keyboard}
    return None

async def send_effect(chat_id: int, text: str, reply_markup=None) -> bool:
    """Send message with random effect using a direct API call."""
    try:
        url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
        payload = {
            'chat_id': chat_id,
            'text': text,
            'message_effect_id': random.choice(EFFECTS),
            'parse_mode': 'HTML'
        }
        if reply_markup:
            payload['reply_markup'] = serialize_reply_markup(reply_markup)

        async with aiohttp.ClientSession() as session:
            async with session.post(
                url,
                data=orjson.dumps(payload),
                headers={'Content-Type': 'application/json'}
            ) as response:
                result = await response.json(loads=orjson.loads)
                return result.get('ok', False)
    except Exception as e:
        logger.error(f"❌ Effect error for {chat_id}: {e}")
        return False

async def animate_reaction(chat_id: int, message_id: int, emoji: str) -> bool:
    """Send animated emoji reaction using a direct API call."""
    try:
        url = f"https://api.telegram.org/bot{BOT_TOKEN}/setMessageReaction"
        payload = {
            'chat_id': chat_id,
            'message_id': message_id,
            'reaction': [{'type': 'emoji', 'emoji': emoji}],
            'is_big': True
        }
        async with aiohttp.ClientSession() as session:
            async with session.post(
                url,
                data=orjson.dumps(payload),
                headers={'Content-Type': 'application/json'}
            ) as response:
                result = await response.json(loads=orjson.loads)
                return result.get('ok', False)
    except Exception as e:
        logger.error(f"❌ Animated reaction error for {chat_id}: {e}")
        return False

async def add_reaction(client: Client, message: Message, emoji: str, user_info: dict):
    """Fallback reaction without animation."""
    try:
        await message.react(emoji)
    except Exception as e:
        from Sakura.Core.helpers import log_action
        log_action("WARNING", f"⚠️ Reaction fallback failed: {e}", user_info)

async def photo_effect(chat_id: int, photo_url: str, caption: str, reply_markup=None) -> bool:
    """Send photo message with random effect using a direct API call."""
    try:
        url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendPhoto"
        payload = {
            'chat_id': chat_id,
            'photo': photo_url,
            'caption': caption,
            'message_effect_id': random.choice(EFFECTS),
            'parse_mode': 'HTML'
        }
        if reply_markup:
            payload['reply_markup'] = serialize_reply_markup(reply_markup)

        async with aiohttp.ClientSession() as session:
            async with session.post(
                url,
                data=orjson.dumps(payload),
                headers={'Content-Type': 'application/json'}
            ) as response:
                result = await response.json(loads=orjson.loads)
                return result.get('ok', False)
    except Exception as e:
        logger.error(f"❌ Photo effect error for {chat_id}: {e}")
        return False