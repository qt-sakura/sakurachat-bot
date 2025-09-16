import asyncio
import logging
from .db import db_pool

logger = logging.getLogger("SAKURA 🌸")

def save_purchase_to_database_async(user_id: int, username: str = None, first_name: str = None, last_name: str = None, amount: int = 0, charge_id: str = None):
    """Save purchase to database asynchronously (fire and forget)"""
    if not db_pool:
        return

    async def save_purchase():
        try:
            async with db_pool.acquire() as conn:
                await conn.execute("""
                    INSERT INTO purchases (user_id, username, first_name, last_name, amount, telegram_payment_charge_id)
                    VALUES ($1, $2, $3, $4, $5, $6)
                    ON CONFLICT (telegram_payment_charge_id) DO NOTHING
                """, user_id, username, first_name, last_name, amount, charge_id)
            logger.debug(f"💾 Purchase saved to database: user {user_id}, amount {amount}")
        except Exception as e:
            logger.error(f"❌ Failed to save purchase to database: {e}")

    asyncio.create_task(save_purchase())

async def get_all_purchases():
    """Get all purchases from database ordered by amount descending"""
    if not db_pool:
        return []

    try:
        async with db_pool.acquire() as conn:
            rows = await conn.fetch("""
                SELECT user_id, username, first_name, last_name, SUM(amount) as total_amount, COUNT(*) as purchase_count
                FROM purchases
                GROUP BY user_id, username, first_name, last_name
                ORDER BY total_amount DESC
            """)
            return rows
    except Exception as e:
        logger.error(f"❌ Failed to get purchases from database: {e}")
        return []
