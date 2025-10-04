from Sakura import state
from Sakura.Core.logging import logger

API_KEY_INDEX_KEY = "sakura:api_key_index"

async def get_key() -> int:
    """Get key index."""
    if not state.valkey_client:
        logger.debug("Valkey client not ready, returning default key index 0.")
        return 0
    try:
        index = await state.valkey_client.get(API_KEY_INDEX_KEY)
        key_index = int(index) if index else 0
        logger.debug(f"Retrieved API key index from Valkey: {key_index}")
        return key_index
    except Exception as e:
        logger.error(f"❌ Failed to get API key index from Valkey: {e}")
        return 0

async def set_key(index: int):
    """Set key index."""
    if not state.valkey_client:
        logger.warning("Valkey client not ready, cannot set key index.")
        return
    try:
        logger.debug(f"Setting API key index in Valkey to {index}.")
        await state.valkey_client.set(API_KEY_INDEX_KEY, index)
    except Exception as e:
        logger.error(f"❌ Failed to set API key index in Valkey: {e}")