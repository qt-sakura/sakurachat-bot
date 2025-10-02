from Sakura import state
from Sakura.Core.logging import logger

async def set_last_message(user_id: int, text: str) -> None:
    """
    Caches the last message sent by the bot to a user.

    Args:
        user_id: The user's ID.
        text: The message text to cache.
    """
    if state.valkey_client:
        try:
            await state.valkey_client.set(f"last_message:{user_id}", text, ex=3600)  # Cache for 1 hour
            logger.info(f"Cached last message for user {user_id}")
        except Exception as e:
            logger.error(f"Failed to cache last message for user {user_id}: {e}")

async def get_last_message(user_id: int) -> str | None:
    """
    Retrieves the last cached message for a user.

    Args:
        user_id: The user's ID.

    Returns:
        The cached message text, or None if not found or on error.
    """
    if state.valkey_client:
        try:
            last_message = await state.valkey_client.get(f"last_message:{user_id}")
            if last_message:
                logger.info(f"Retrieved last message for user {user_id}")
                return last_message.decode('utf-8')
            return None
        except Exception as e:
            logger.error(f"Failed to retrieve last message for user {user_id}: {e}")
            return None
    return None