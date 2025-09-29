import asyncio
import random
from datetime import datetime, timezone, timedelta

from telegram import Update
from telegram.constants import ChatType, ParseMode
from telegram.ext import ContextTypes

from Sakura import state
from Sakura.AI.response import get_response
from Sakura.Core.config import AFK_TIME
from Sakura.Core.helpers import fetch_user, log_action
from Sakura.Core.logging import logger
from Sakura.Core.utils import delete_delayed, delete_keyboard
from Sakura.Storage.database import get_afk, remove_afk, set_afk
from Sakura.Storage.storage import AFK_NOTICES, BACK_MESSAGES
from Sakura.Storage.valkey import get_all_last_seen, update_last_seen

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
    chat_type = update.effective_chat.type

    if not user or user.is_bot:
        return

    user_info = fetch_user(update.message)
    now = datetime.now(timezone.utc)

    # --- New Logic: Handle replies to AFK notices and welcome messages ---
    if update.message.reply_to_message:
        replied_msg_id = update.message.reply_to_message.message_id

        # Cancel deletion task if someone replies to an AFK notice in a group
        if replied_msg_id in state.afk_deletion_tasks:
            deletion_task = state.afk_deletion_tasks.pop(replied_msg_id)
            deletion_task.cancel()
            log_action("INFO", f"🗣️ AFK notice deletion cancelled for message {replied_msg_id} due to reply.", user_info)

        # AI response if a user replies to their "welcome back" message
        if replied_msg_id in state.welcome_back_messages:
            if state.welcome_back_messages[replied_msg_id] == user.id:
                original_message = update.message.reply_to_message.text
                user_reply = update.message.text

                prompt = (
                    "You are a friendly and slightly playful assistant. "
                    f"The user was just welcomed back from being AFK with the message: '{original_message}'. "
                    f"They have now replied: '{user_reply}'. "
                    "Generate a short, natural, and context-aware response to their reply."
                )

                ai_response = await get_response(prompt, user.full_name, user_info, user.id)
                if ai_response:
                    await update.message.reply_text(ai_response)

                # Clean up to prevent re-triggering
                del state.welcome_back_messages[replied_msg_id]
                return

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

        # --- Modified Logic: Handle private vs group "welcome back" messages ---
        if chat_type == ChatType.PRIVATE:
            sent_message = await update.message.reply_text(
                text=message_text,
                parse_mode=ParseMode.HTML,
            )
        else:
            sent_message = await update.message.reply_text(
                text=message_text,
                parse_mode=ParseMode.HTML,
                reply_markup=delete_keyboard()
            )
            asyncio.create_task(delete_delayed(sent_message, 60))

        state.welcome_back_messages[sent_message.message_id] = user.id
        log_action("INFO", f"🔙 User returned from AFK after {format_duration(delta)}", user_info)

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

                # --- Modified Logic: Handle private vs group AFK notices ---
                if chat_type == ChatType.PRIVATE:
                    await update.message.reply_text(
                        text=message_text,
                        parse_mode=ParseMode.HTML,
                    )
                else:
                    sent_message = await update.message.reply_text(
                        text=message_text,
                        parse_mode=ParseMode.HTML,
                        reply_markup=delete_keyboard()
                    )
                    deletion_task = asyncio.create_task(delete_delayed(sent_message, 60))
                    state.afk_deletion_tasks[sent_message.message_id] = deletion_task

                log_action("INFO", f"🗣️ Notified user about AFK status of {replied_user.full_name}", user_info)


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

                # Mark as AFK if inactive for more than the configured time
                if now - last_time > timedelta(minutes=AFK_TIME):
                    await set_afk(chat_id, user_id, last_time)
                    logger.info(f"😴 Auto-set user {user_id} in chat {chat_id} as AFK due to inactivity.")

        except Exception as e:
            logger.error(f"❌ Error in inactivity checker task: {e}")

        await asyncio.sleep(60) # Check every minute
