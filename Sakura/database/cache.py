import json
import time
import logging
from valkey.asyncio import Valkey as AsyncValkey

from ..config.settings import VALKEY_URL, SESSION_TTL, CACHE_TTL, MESSAGE_LIMIT, RATE_LIMIT_COUNT, RATE_LIMIT_TTL

logger = logging.getLogger("SAKURA 🌸")
valkey_client: AsyncValkey = None
rate_limited_users = {}
user_message_counts = {}

async def init_valkey():
    """Initialize Valkey connection"""
    global valkey_client
    try:
        valkey_client = AsyncValkey.from_url(
            VALKEY_URL,
            decode_responses=True,
            socket_connect_timeout=5,
            socket_timeout=5,
            retry_on_timeout=True,
            health_check_interval=30
        )
        await valkey_client.ping()
        logger.info("✅ Valkey client initialized and connected successfully")
        return True
    except Exception as e:
        logger.error(f"❌ Failed to initialize Valkey client: {e}")
        valkey_client = None
        return False

async def close_valkey():
    """Close Valkey connection"""
    if valkey_client:
        try:
            await valkey_client.aclose()
            logger.info("✅ Valkey connection closed")
        except Exception as e:
            logger.error(f"❌ Error closing Valkey connection: {e}")

async def save_user_session(user_id: int, session_data: dict):
    """Save user session data to Valkey"""
    if not valkey_client:
        return False
    try:
        key = f"session:{user_id}"
        await valkey_client.setex(key, SESSION_TTL, json.dumps(session_data))
        logger.debug(f"💾 Session saved for user {user_id}")
        return True
    except Exception as e:
        logger.error(f"❌ Failed to save session for user {user_id}: {e}")
        return False

async def get_user_session(user_id: int) -> dict:
    """Get user session data from Valkey"""
    if not valkey_client:
        return {}
    try:
        key = f"session:{user_id}"
        data = await valkey_client.get(key)
        if data:
            return json.loads(data)
        return {}
    except Exception as e:
        logger.error(f"❌ Failed to get session for user {user_id}: {e}")
        return {}

async def delete_user_session(user_id: int):
    """Delete user session from Valkey"""
    if not valkey_client:
        return False
    try:
        key = f"session:{user_id}"
        await valkey_client.delete(key)
        logger.debug(f"🗑️ Session deleted for user {user_id}")
        return True
    except Exception as e:
        logger.error(f"❌ Failed to delete session for user {user_id}: {e}")
        return False

async def cache_set(key: str, value, ttl: int = CACHE_TTL):
    """Set cache value in Valkey"""
    if not valkey_client:
        return False
    try:
        if isinstance(value, (dict, list)):
            value = json.dumps(value)
        await valkey_client.setex(f"cache:{key}", ttl, value)
        logger.debug(f"📦 Cache set for key: {key}")
        return True
    except Exception as e:
        logger.error(f"❌ Failed to set cache for key {key}: {e}")
        return False

async def cache_get(key: str):
    """Get cache value from Valkey"""
    if not valkey_client:
        return None
    try:
        value = await valkey_client.get(f"cache:{key}")
        if value:
            try:
                return json.loads(value)
            except (json.JSONDecodeError, TypeError):
                return value
        return None
    except Exception as e:
        logger.error(f"❌ Failed to get cache for key {key}: {e}")
        return None

async def cache_delete(key: str):
    """Delete cache value from Valkey"""
    if not valkey_client:
        return False
    try:
        await valkey_client.delete(f"cache:{key}")
        logger.debug(f"🗑️ Cache deleted for key: {key}")
        return True
    except Exception as e:
        logger.error(f"❌ Failed to delete cache for key {key}: {e}")
        return False

async def save_user_state(user_id: int, state_data: dict):
    """Save user state (help_expanded, broadcast_mode, etc.) to Valkey"""
    if not valkey_client:
        return False
    try:
        key = f"user_state:{user_id}"
        await valkey_client.setex(key, SESSION_TTL, json.dumps(state_data))
        logger.debug(f"💾 User state saved for user {user_id}")
        return True
    except Exception as e:
        logger.error(f"❌ Failed to save user state for user {user_id}: {e}")
        return False

async def get_user_state(user_id: int) -> dict:
    """Get user state from Valkey"""
    if not valkey_client:
        return {}
    try:
        key = f"user_state:{user_id}"
        data = await valkey_client.get(key)
        if data:
            return json.loads(data)
        return {}
    except Exception as e:
        logger.error(f"❌ Failed to get user state for user {user_id}: {e}")
        return {}

async def update_help_expanded_state(user_id: int, expanded: bool):
    """Update help expanded state in both memory and Valkey"""
    state = await get_user_state(user_id)
    state['help_expanded'] = expanded
    await save_user_state(user_id, state)

async def get_help_expanded_state(user_id: int) -> bool:
    """Get help expanded state from Valkey with memory fallback"""
    state = await get_user_state(user_id)
    return state.get('help_expanded', False)

async def is_rate_limited(user_id: int, chat_id: int) -> bool:
    """Checks if a user is rate-limited based on a per-user, per-chat basis."""
    if valkey_client:
        try:
            hard_limit_key = f"hard_rate_limit:{user_id}:{chat_id}"
            if await valkey_client.exists(hard_limit_key):
                return True

            message_count_key = f"message_count:{user_id}:{chat_id}"
            pipe = valkey_client.pipeline()
            pipe.incr(message_count_key)
            pipe.ttl(message_count_key)
            results = await pipe.execute()

            count = results[0]
            ttl = results[1]

            if ttl == -1:
                await valkey_client.expire(message_count_key, int(MESSAGE_LIMIT))

            if count > RATE_LIMIT_COUNT:
                await valkey_client.setex(hard_limit_key, RATE_LIMIT_TTL, "1")
                return True

            if count > 1:
                return True
            return False
        except Exception as e:
            logger.error(f"❌ Valkey rate limit check failed for user {user_id}:{chat_id}: {e}. Falling back to memory.")

    key = f"{user_id}:{chat_id}"
    current_time = time.time()

    if key in rate_limited_users and current_time < rate_limited_users[key]:
        return True
    elif key in rate_limited_users:
        del rate_limited_users[key]

    timestamps = user_message_counts.get(key, [])
    timestamps = [ts for ts in timestamps if current_time - ts < MESSAGE_LIMIT]
    timestamps.append(current_time)
    user_message_counts[key] = timestamps

    if len(timestamps) > RATE_LIMIT_COUNT:
        rate_limited_users[key] = current_time + RATE_LIMIT_TTL
        return True

    if len(timestamps) > 1:
        return True
    return False

async def update_user_response_time_valkey(user_id: int) -> None:
    """Update the last response time for user in Valkey"""
    if valkey_client:
        try:
            key = f"last_response:{user_id}"
            await valkey_client.setex(key, SESSION_TTL, int(time.time()))
            logger.debug(f"⏰ Updated response time in Valkey for user {user_id}")
        except Exception as e:
            logger.error(f"❌ Failed to update response time in Valkey for user {user_id}: {e}")
