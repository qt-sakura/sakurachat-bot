import asyncio
import random
from datetime import datetime, timezone, timedelta
from telegram import Update
from telegram.ext import ContextTypes
from telegram.constants import ParseMode

from Sakura.Core.logging import logger
from Sakura.Core.utils import delete_keyboard, delete_delayed
from Sakura.Core.helpers import fetch_user, log_action
from Sakura.Storage.database import get_afk, set_afk, remove_afk
from Sakura.Storage.valkey import update_last_seen, get_all_last_seen
from Sakura.Storage.storage import BACK_MESSAGES, AFK_NOTICES
from Sakura import state

def format_duration(delta: timedelta) -> str:
    """Format time delta into a human-readable string."""
    seconds = int(delta.total_seconds())
    days, remainder = divmod(seconds, 86400)
    hours, remainder = divmod(remainder, 3600)
    minutes, _ = divmod(remainder, 60)

    parts = []
    if days > 0:
        parts.append(f"{days} day{'s' if days != 1 else ''}")
    if hours > 0:
        parts.append(f"{hours} hour{'s' if hours != 1 else ''}")
    if minutes > 0:
        parts.append(f"{minutes} minute{'s' if minutes != 1 else ''}")

    if not parts:
        return "less than a minute"

    return " ".join(parts)

async def afk_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle all incoming messages for AFK tracking."""
    if not update.message:
        return

    chat_id = update.effective_chat.id
    user = update.effective_user

    if not user or user.is_bot:
        return

    user_info = fetch_user(update.message)
    now = datetime.now(timezone.utc)

    # Update user's last seen time on every message
    await update_last_seen(chat_id, user.id, now)

    # Check if the user was AFK and bring them back
    afk_status = await get_afk(chat_id, user.id)
    if afk_status:
        await remove_afk(chat_id, user.id)
        delta = now - afk_status["since"]

        message_text = random.choice(BACK_MESSAGES).format(
            user=user.mention_html(),
            duration=format_duration(delta)
        )

        sent_message = await update.message.reply_text(
            text=message_text,
            parse_mode=ParseMode.HTML,
            reply_markup=delete_keyboard()
        )
        log_action("INFO", f"🔙 User returned from AFK after {format_duration(delta)}", user_info)
        asyncio.create_task(delete_delayed(sent_message, 60))

    # Check if the message is a reply to an AFK user
    if update.message.reply_to_message and update.message.reply_to_message.from_user:
        replied_user = update.message.reply_to_message.from_user
        if replied_user.id != user.id:
            replied_afk_status = await get_afk(chat_id, replied_user.id)
            if replied_afk_status:
                delta = now - replied_afk_status["since"]

                message_text = random.choice(AFK_NOTICES).format(
                    user=replied_user.mention_html(),
                    duration=format_duration(delta)
                )

                sent_message = await update.message.reply_text(
                    text=message_text,
                    parse_mode=ParseMode.HTML,
                    reply_markup=delete_keyboard()
                )
                log_action("INFO", f"🗣️ Notified user about AFK status of {replied_user.full_name}", user_info)
                asyncio.create_task(delete_delayed(sent_message, 60))


async def check_inactive():
    """Background task to check for inactive users and set them AFK."""
    logger.info("⏰ Starting inactivity checker task...")
    await asyncio.sleep(60)

    while True:
        try:
            now = datetime.now(timezone.utc)
            records = await get_all_last_seen()

            for record in records:
                chat_id = record["chat_id"]
                user_id = record["user_id"]
                last_time = record["seen_at"]

                # Check if user is already AFK
                afk_status = await get_afk(chat_id, user_id)
                if afk_status:
                    continue

                # Mark as AFK if inactive for more than 60 minutes
                if now - last_time > timedelta(minutes=60):
                    await set_afk(chat_id, user_id, last_time)
                    logger.info(f"😴 Auto-set user {user_id} in chat {chat_id} as AFK due to inactivity.")

        except Exception as e:
            logger.error(f"❌ Error in inactivity checker task: {e}")

        await asyncio.sleep(60) # Check every minute