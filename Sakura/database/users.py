import asyncio
import logging
from .db import db_pool

logger = logging.getLogger("SAKURA 🌸")
from ..core.state import user_ids

def save_user_to_database_async(user_id: int, username: str = None, first_name: str = None, last_name: str = None):
    """Save user to database asynchronously (fire and forget)"""
    if not db_pool:
        return

    async def save_user():
        try:
            async with db_pool.acquire() as conn:
                await conn.execute("""
                    INSERT INTO users (user_id, username, first_name, last_name, updated_at)
                    VALUES ($1, $2, $3, $4, CURRENT_TIMESTAMP)
                    ON CONFLICT (user_id)
                    DO UPDATE SET
                        username = EXCLUDED.username,
                        first_name = EXCLUDED.first_name,
                        last_name = EXCLUDED.last_name,
                        updated_at = CURRENT_TIMESTAMP
                """, user_id, username, first_name, last_name)
            logger.debug(f"💾 User {user_id} saved to database")
        except Exception as e:
            logger.error(f"❌ Failed to save user {user_id} to database: {e}")

    asyncio.create_task(save_user())

async def get_users_from_database():
    """Get all user IDs from database"""
    if not db_pool:
        return list(user_ids)

    try:
        async with db_pool.acquire() as conn:
            rows = await conn.fetch("SELECT user_id FROM users")
            return [row['user_id'] for row in rows]
    except Exception as e:
        logger.error(f"❌ Failed to get users from database: {e}")
        return list(user_ids)

async def remove_user_from_database(user_id: int):
    """Remove a user from the database and memory."""
    if user_id in user_ids:
        user_ids.remove(user_id)

    if not db_pool:
        logger.warning(f"⚠️ DB pool not available. Cannot remove user {user_id}.")
        return

    try:
        async with db_pool.acquire() as conn:
            await conn.execute("DELETE FROM users WHERE user_id = $1", user_id)
        logger.info(f"✅ User {user_id} removed from database.")
    except Exception as e:
        logger.error(f"❌ Failed to remove user {user_id} from database: {e}")

async def get_user_info_by_identifier(identifier: str) -> tuple:
    """Get user info by user ID or username from database"""
    if not db_pool:
        return None, None

    try:
        async with db_pool.acquire() as conn:
            if identifier.isdigit():
                row = await conn.fetchrow(
                    "SELECT user_id, username, first_name, last_name FROM users WHERE user_id = $1",
                    int(identifier)
                )
            else:
                username = identifier.lstrip('@')
                row = await conn.fetchrow(
                    "SELECT user_id, username, first_name, last_name FROM users WHERE username = $1",
                    username
                )

            if row:
                display_name = row['first_name'] or row['username'] or f"User {row['user_id']}"
                return row['user_id'], display_name

        return None, None
    except Exception as e:
        logger.error(f"❌ Error looking up user {identifier}: {e}")
        return None, None
