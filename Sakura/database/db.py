import asyncpg
import logging
from ..config.settings import DATABASE_URL
from ..core.state import user_ids, group_ids

logger = logging.getLogger("SAKURA 🌸")
db_pool = None

async def init_database():
    """Initialize database connection and create tables"""
    global db_pool

    if not DATABASE_URL:
        logger.error("❌ DATABASE_URL not found in environment variables")
        return False

    try:
        db_pool = await asyncpg.create_pool(
            DATABASE_URL,
            min_size=5,
            max_size=20,
            command_timeout=3,
            server_settings={'application_name': 'sakura_bot'}
        )
        logger.info("✅ Database connection pool created successfully")

        async with db_pool.acquire() as conn:
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    user_id BIGINT PRIMARY KEY,
                    username TEXT,
                    first_name TEXT,
                    last_name TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS groups (
                    group_id BIGINT PRIMARY KEY,
                    title TEXT,
                    username TEXT,
                    type TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS purchases (
                    id SERIAL PRIMARY KEY,
                    user_id BIGINT NOT NULL,
                    username TEXT,
                    first_name TEXT,
                    last_name TEXT,
                    amount INTEGER NOT NULL,
                    telegram_payment_charge_id TEXT UNIQUE,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            await conn.execute("CREATE INDEX IF NOT EXISTS idx_users_created_at ON users(created_at)")
            await conn.execute("CREATE INDEX IF NOT EXISTS idx_groups_created_at ON groups(created_at)")
            await conn.execute("CREATE INDEX IF NOT EXISTS idx_purchases_user_id ON purchases(user_id)")
            await conn.execute("CREATE INDEX IF NOT EXISTS idx_purchases_created_at ON purchases(created_at)")

        logger.info("✅ Database tables created/verified successfully")
        await load_data_from_database()
        return True

    except Exception as e:
        logger.error(f"❌ Database initialization failed: {e}")
        return False

async def load_data_from_database():
    """Load user IDs and group IDs from database into memory"""
    if not db_pool:
        logger.warning("⚠️ Database pool not available for loading data")
        return

    try:
        async with db_pool.acquire() as conn:
            user_rows = await conn.fetch("SELECT user_id FROM users")
            user_ids.update(row['user_id'] for row in user_rows)

            group_rows = await conn.fetch("SELECT group_id FROM groups")
            group_ids.update(row['group_id'] for row in group_rows)

        logger.info(f"✅ Loaded {len(user_ids)} users and {len(group_ids)} groups from database")

    except Exception as e:
        logger.error(f"❌ Failed to load data from database: {e}")

async def close_database():
    """Close database connection pool"""
    global db_pool
    if db_pool:
        await db_pool.close()
        logger.info("✅ Database connection pool closed")
