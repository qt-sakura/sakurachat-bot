import asyncio
import json
import logging
import time

from ..database.cache import valkey_client
from ..config.settings import CHAT_CLEANUP, OLD_CHAT, CHAT_LENGTH, SESSION_TTL

logger = logging.getLogger("SAKURA 🌸")
conversation_history = {}
user_last_response_time = {}

async def add_to_conversation_history(user_id: int, message: str, is_user: bool = True):
    """Add message to user's conversation history (Valkey + memory fallback)"""
    global conversation_history

    role = "user" if is_user else "assistant"
    new_message = {"role": role, "content": message}

    if valkey_client:
        try:
            key = f"conversation:{user_id}"
            existing = await valkey_client.get(key)
            history = json.loads(existing) if existing else []
            history.append(new_message)

            if len(history) > CHAT_LENGTH:
                history = history[-CHAT_LENGTH:]

            await valkey_client.setex(key, SESSION_TTL, json.dumps(history))
            logger.debug(f"💬 Conversation updated in Valkey for user {user_id}")
            return
        except Exception as e:
            logger.error(f"❌ Failed to update conversation in Valkey for user {user_id}: {e}")

    if user_id not in conversation_history:
        conversation_history[user_id] = []

    conversation_history[user_id].append(new_message)

    if len(conversation_history[user_id]) > CHAT_LENGTH:
        conversation_history[user_id] = conversation_history[user_id][-CHAT_LENGTH:]

async def get_conversation_context(user_id: int) -> str:
    """Get formatted conversation context for the user (Valkey + memory fallback)"""
    history = []

    if valkey_client:
        try:
            key = f"conversation:{user_id}"
            existing = await valkey_client.get(key)
            if existing:
                history = json.loads(existing)
        except Exception as e:
            logger.error(f"❌ Failed to get conversation from Valkey for user {user_id}: {e}")

    if not history and user_id in conversation_history:
        history = conversation_history[user_id]

    if not history:
        return ""

    context_lines = []
    for message in history:
        role = message.get("role", "unknown")
        content = message.get("content", "")
        if role == "user":
            context_lines.append(f"User: {content}")
        else:
            context_lines.append(f"Sakura: {content}")

    return "\n".join(context_lines)

async def cleanup_old_conversations():
    """Clean up old conversation histories and response times periodically"""
    global conversation_history, user_last_response_time

    logger.info("🧹 Conversation cleanup task started")

    while True:
        try:
            current_time = time.time()
            conversations_cleaned = 0
            expired_users = [
                user_id for user_id, last_time in user_last_response_time.items()
                if current_time - last_time > OLD_CHAT
            ]

            for user_id in expired_users:
                if user_id in conversation_history:
                    del conversation_history[user_id]
                    conversations_cleaned += 1
                if user_id in user_last_response_time:
                    del user_last_response_time[user_id]

            if conversations_cleaned > 0:
                logger.info(f"🧹 Cleaned {conversations_cleaned} old conversations")

            logger.debug(f"📊 Active conversations: {len(conversation_history)}")

        except asyncio.CancelledError:
            logger.info("🧹 Cleanup task cancelled - shutting down gracefully")
            break
        except Exception as e:
            logger.error(f"❌ Error in conversation cleanup: {e}")

        try:
            await asyncio.sleep(CHAT_CLEANUP)
        except asyncio.CancelledError:
            logger.info("🧹 Cleanup task sleep cancelled - shutting down")
            break
