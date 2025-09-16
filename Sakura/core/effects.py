import asyncio
import aiohttp
import random
import logging
from telethon import TelegramClient
from telegram import Update, ReactionTypeEmoji
from telegram.ext import ContextTypes

from ..config.settings import BOT_TOKEN, API_ID, API_HASH
from ..config.constants import EFFECTS
from ..utils.messages import log_with_user_info, extract_user_info

logger = logging.getLogger("SAKURA 🌸")
effects_client = None

async def initialize_effects_client():
    """Initialize the Telethon effects client"""
    global effects_client
    try:
        effects_client = TelegramClient('sakura_effects', API_ID, API_HASH)
        logger.info("✅ Telethon effects client initialized")
    except Exception as e:
        logger.error(f"❌ Failed to initialize Telethon effects client: {e}")

async def start_effects_client():
    """Start the Telethon effects client"""
    if effects_client:
        try:
            await effects_client.start(bot_token=BOT_TOKEN)
            logger.info("✅ Telethon effects client started successfully")
        except Exception as e:
            logger.error(f"❌ Failed to start Telethon effects client: {e}")
            await stop_effects_client()

async def stop_effects_client():
    """Stop the Telethon effects client"""
    global effects_client
    if effects_client and effects_client.is_connected():
        try:
            await effects_client.disconnect()
            logger.info("✅ Telethon effects client stopped")
        except Exception as e:
            logger.error(f"❌ Error stopping Telethon effects client: {e}")
    effects_client = None

async def send_with_effect(chat_id: int, text: str, reply_markup=None) -> bool:
    """Send message with random effect using Telethon"""
    if not effects_client:
        logger.warning("⚠️ Telethon effects client not available")
        return False

    try:
        url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
        payload = {
            'chat_id': chat_id,
            'text': text,
            'message_effect_id': random.choice(EFFECTS),
            'parse_mode': 'HTML'
        }

        if reply_markup:
            payload['reply_markup'] = reply_markup.to_json()

        async with aiohttp.ClientSession() as session:
            async with session.post(url, json=payload) as response:
                result = await response.json()
                if result.get('ok'):
                    logger.info(f"✨ Effect message sent to {chat_id}")
                    return True
                else:
                    logger.error(f"❌ Effect failed for {chat_id}: {result}")
                    return False
    except Exception as e:
        logger.error(f"❌ Effect error for {chat_id}: {e}")
        return False

async def send_animated_reaction(chat_id: int, message_id: int, emoji: str) -> bool:
    """Send animated emoji reaction using direct API call"""
    try:
        url = f"https://api.telegram.org/bot{BOT_TOKEN}/setMessageReaction"
        payload = {
            'chat_id': chat_id,
            'message_id': message_id,
            'reaction': [{'type': 'emoji', 'emoji': emoji}],
            'is_big': True
        }

        async with aiohttp.ClientSession() as session:
            async with session.post(url, json=payload) as response:
                result = await response.json()
                if result.get('ok'):
                    logger.info(f"🎭 Animated reaction {emoji} sent to {chat_id}")
                    return True
                else:
                    logger.error(f"❌ Animated reaction failed for {chat_id}: {result}")
                    return False
    except Exception as e:
        logger.error(f"❌ Animated reaction error for {chat_id}: {e}")
        return False

async def add_ptb_reaction(context: ContextTypes.DEFAULT_TYPE, update: Update, emoji: str):
    """Fallback PTB reaction without animation"""
    user_info = extract_user_info(update.message)
    try:
        reaction = [ReactionTypeEmoji(emoji=emoji)]
        await context.bot.set_message_reaction(
            chat_id=update.effective_chat.id,
            message_id=update.message.message_id,
            reaction=reaction
        )
        log_with_user_info("DEBUG", f"🍓 Added emoji reaction (PTB): {emoji}", user_info)
    except Exception as e:
        log_with_user_info("WARNING", f"⚠️ PTB reaction fallback failed: {e}", user_info)

async def send_with_effect_photo(chat_id: int, photo_url: str, caption: str, reply_markup=None) -> bool:
    """Send photo message with random effect using direct API"""
    if not effects_client:
        logger.warning("⚠️ Telethon effects client not available")
        return False

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
            payload['reply_markup'] = reply_markup.to_json()

        async with aiohttp.ClientSession() as session:
            async with session.post(url, json=payload) as response:
                result = await response.json()
                if result.get('ok'):
                    logger.info(f"✨ Effect photo sent to {chat_id}")
                    return True
                else:
                    logger.error(f"❌ Photo effect failed for {chat_id}: {result}")
                    return False
    except Exception as e:
        logger.error(f"❌ Photo effect error for {chat_id}: {e}")
        return False

# Initialize the client when the module is loaded
asyncio.run(initialize_effects_client())
