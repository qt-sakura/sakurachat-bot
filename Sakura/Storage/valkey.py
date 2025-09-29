from valkey.asyncio import Valkey as AsyncValkey
from datetime import datetime, timezone
from Sakura.Core.config import VALKEY_URL
from Sakura.Core.logging import logger
from Sakura import state

async def connect_cache():
    """Initialize Valkey connection"""
    try:
        state.valkey_client = AsyncValkey.from_url(
            VALKEY_URL,
            decode_responses=True,
            socket_connect_timeout=5,
            socket_timeout=5,
            retry_on_timeout=True,
            health_check_interval=30
        )
        await state.valkey_client.ping()
        logger.info("✅ Valkey client initialized and connected successfully")
        return True
    except Exception as e:
        logger.error(f"❌ Failed to initialize Valkey client: {e}")
        state.valkey_client = None
        return False

async def update_last_seen(chat_id: int, user_id: int, seen_at: datetime):
    """Update last seen timestamp for a user in Valkey."""
    if not state.valkey_client:
        return
    try:
        key = f"last_seen:{chat_id}:{user_id}"
        await state.valkey_client.set(key, seen_at.isoformat())
        logger.debug(f"👁️ Last seen updated for user {user_id} in chat {chat_id}")
    except Exception as e:
        logger.error(f"❌ Error updating last seen for user {user_id}: {e}")

async def get_all_last_seen():
    """Get all last seen records from Valkey."""
    if not state.valkey_client:
        return []
    try:
        records = []
        async for key in state.valkey_client.scan_iter("last_seen:*"):
            value = await state.valkey_client.get(key)
            if value:
                try:
                    _, chat_id, user_id = key.split(":")
                    records.append({
                        "chat_id": int(chat_id),
                        "user_id": int(user_id),
                        "seen_at": datetime.fromisoformat(value).replace(tzinfo=timezone.utc)
                    })
                except (ValueError, TypeError) as e:
                    logger.warning(f"⚠️ Could not parse last_seen record for key {key}: {e}")

        logger.debug(f"📊 Retrieved {len(records)} last seen records from Valkey")
        return records
    except Exception as e:
        logger.error(f"❌ Error getting all last seen records from Valkey: {e}")
        return []

async def close_cache():
    """Close Valkey connection"""
    if state.valkey_client:
        try:
            await state.valkey_client.aclose()
            logger.info("✅ Valkey connection closed")
        except Exception as e:
            logger.error(f"❌ Error closing Valkey connection: {e}")