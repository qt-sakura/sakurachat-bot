import asyncio
import logging
from .db import db_pool

logger = logging.getLogger("SAKURA 🌸")
from ..core.state import group_ids

def save_group_to_database_async(group_id: int, title: str = None, username: str = None, chat_type: str = None):
    """Save group to database asynchronously (fire and forget)"""
    if not db_pool:
        return

    async def save_group():
        try:
            async with db_pool.acquire() as conn:
                await conn.execute("""
                    INSERT INTO groups (group_id, title, username, type, updated_at)
                    VALUES ($1, $2, $3, $4, CURRENT_TIMESTAMP)
                    ON CONFLICT (group_id)
                    DO UPDATE SET
                        title = EXCLUDED.title,
                        username = EXCLUDED.username,
                        type = EXCLUDED.type,
                        updated_at = CURRENT_TIMESTAMP
                """, group_id, title, username, chat_type)
            logger.debug(f"💾 Group {group_id} saved to database")
        except Exception as e:
            logger.error(f"❌ Failed to save group {group_id} to database: {e}")

    asyncio.create_task(save_group())

async def get_groups_from_database():
    """Get all group IDs from database"""
    if not db_pool:
        return list(group_ids)

    try:
        async with db_pool.acquire() as conn:
            rows = await conn.fetch("SELECT group_id FROM groups")
            return [row['group_id'] for row in rows]
    except Exception as e:
        logger.error(f"❌ Failed to get groups from database: {e}")
        return list(group_ids)

async def remove_group_from_database(group_id: int):
    """Remove a group from the database and memory."""
    if group_id in group_ids:
        group_ids.remove(group_id)

    if not db_pool:
        logger.warning(f"⚠️ DB pool not available. Cannot remove group {group_id}.")
        return

    try:
        async with db_pool.acquire() as conn:
            await conn.execute("DELETE FROM groups WHERE group_id = $1", group_id)
        logger.info(f"✅ Group {group_id} removed from database.")
    except Exception as e:
        logger.error(f"❌ Failed to remove group {group_id} from database: {e}")
