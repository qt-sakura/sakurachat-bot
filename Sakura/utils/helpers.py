import random
import logging
import time
import psutil
import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from typing import Dict

from ..database.users import user_ids
from ..database.groups import group_ids
from ..database.db import db_pool
from ..core.memory import conversation_history
from ..config.settings import BOT_TOKEN, GEMINI_API_KEY, OWNER_ID, DATABASE_URL, API_ID, API_HASH
from .messages import log_with_user_info

logger = logging.getLogger("SAKURA 🌸")

def get_fallback_response() -> str:
    """Get a random fallback response when API fails"""
    RESPONSES = [
        "Got a bit confused, try again 😔",
        "Something's off, I can't understand 😕",
        "I'm a little overwhelmed right now, let's talk later 🥺",
        "My brain's all scrambled, hold on 😅",
    ]
    return random.choice(RESPONSES)

def get_error_response() -> str:
    """Get a random error response when something goes wrong"""
    ERROR = [
        "Sorry buddy, something went wrong 😔",
        "Oops, I think I misunderstood 🫢",
        "That was unexpected, try again 😅",
    ]
    return random.choice(ERROR)

def should_respond_in_group(update: Update, bot_id: int) -> bool:
    """Determine if bot should respond in group chat"""
    user_message = update.message.text or update.message.caption or ""
    if "sakura" in user_message.lower():
        return True
    if (update.message.reply_to_message and
        update.message.reply_to_message.from_user.id == bot_id):
        return True
    return False

def track_user_and_chat(update: Update, user_info: Dict[str, any]) -> None:
    """Track user and chat IDs for broadcasting"""
    user_id = user_info["user_id"]
    chat_id = user_info["chat_id"]
    chat_type = user_info["chat_type"]

    if chat_type == "private":
        if user_id not in user_ids:
            user_ids.add(user_id)
            from ..database.users import save_user_to_database_async
            save_user_to_database_async(
                user_id,
                user_info.get("username"),
                user_info.get("first_name"),
                user_info.get("last_name")
            )
            log_with_user_info("INFO", f"👤 New user tracked for broadcasting", user_info)
    elif chat_type in ['group', 'supergroup']:
        if chat_id not in group_ids:
            group_ids.add(chat_id)
            from ..database.groups import save_group_to_database_async
            save_group_to_database_async(
                chat_id,
                user_info.get("chat_title"),
                user_info.get("username"),
                chat_type
            )
            log_with_user_info("INFO", f"📢 New group tracked for broadcasting", user_info)

def validate_config() -> bool:
    """Validate bot configuration"""
    if not BOT_TOKEN:
        logger.error("❌ BOT_TOKEN not found in environment variables")
        return False
    if not GEMINI_API_KEY:
        logger.error("❌ GEMINI_API_KEY not found in environment variables")
        return False
    if not OWNER_ID:
        logger.error("❌ OWNER_ID not found in environment variables")
        return False
    if not DATABASE_URL:
        logger.error("❌ DATABASE_URL not found in environment variables")
        return False
    if not API_ID:
        logger.error("❌ API_ID not found in environment variables")
        return False
    if not API_HASH:
        logger.error("❌ API_HASH not found in environment variables")
        return False
    return True

async def send_stats_message(chat_id: int, context: ContextTypes.DEFAULT_TYPE, is_refresh: bool = False) -> None:
    """Send or update stats message with current data"""
    try:
        ping_start = time.time()
        try:
            await context.bot.get_me()
            ping_ms = round((time.time() - ping_start) * 1000, 2)
        except Exception:
            ping_ms = "Error"

        try:
            process = psutil.Process()
            uptime_seconds = time.time() - process.create_time()
            days = int(uptime_seconds // 86400)
            hours = int((uptime_seconds % 86400) // 3600)
            minutes = int((uptime_seconds % 3600) // 60)
            uptime_str = f"{days}d {hours}h {minutes}m"
        except Exception:
            uptime_str = "Unknown"

        current_time = datetime.datetime.now()
        cpu_percent = psutil.cpu_percent(interval=0.1)
        memory = psutil.virtual_memory()

        db_stats = {
            'users_count': len(user_ids),
            'groups_count': len(group_ids),
            'total_purchases': 0,
            'total_revenue': 0,
            'active_conversations': len(conversation_history)
        }

        if db_pool:
            try:
                async with db_pool.acquire() as conn:
                    purchase_stats = await conn.fetchrow("""
                        SELECT COUNT(*) as total_purchases, COALESCE(SUM(amount), 0) as total_revenue
                        FROM purchases
                    """)
                    if purchase_stats:
                        db_stats['total_purchases'] = purchase_stats['total_purchases']
                        db_stats['total_revenue'] = purchase_stats['total_revenue']

                    recent_users = await conn.fetchval("""
                        SELECT COUNT(*) FROM users
                        WHERE updated_at > NOW() - INTERVAL '24 hours'
                    """)
                    db_stats['recent_users'] = recent_users or 0

                    recent_purchases = await conn.fetchval("""
                        SELECT COUNT(*) FROM purchases
                        WHERE created_at > NOW() - INTERVAL '24 hours'
                    """)
                    db_stats['recent_purchases'] = recent_purchases or 0
            except Exception as e:
                logger.error(f"Error getting database stats: {e}")

        stats_message = f"""📊 <b>Sakura Bot Statistics</b>
<i>Last Updated: {current_time.strftime('%H:%M:%S')}</i>

🏓 <b>Bot Performance</b>
├ Uptime: <b>{uptime_str}</b>
└ Ping: <b>{ping_ms}ms</b>

👥 <b>User Statistics</b>
├ Total Users: <b>{db_stats['users_count']}</b>
├ Total Groups: <b>{db_stats['groups_count']}</b>
├ Recent Users (24h): <b>{db_stats.get('recent_users', 'N/A')}</b>
├ Active Conversations: <b>{db_stats['active_conversations']}</b>
├ Total Purchases: <b>{db_stats['total_purchases']}</b>
├ Total Revenue: <b>{db_stats['total_revenue']} ⭐</b>
└ Recent Purchases (24h): <b>{db_stats.get('recent_purchases', 'N/A')}</b>

🖥️ <b>System Resources</b>
├ CPU Usage: <b>{cpu_percent}%</b>
└ Memory: <b>{memory.percent}%</b> ({memory.used // (1024**3)}GB / {memory.total // (1024**3)}GB)"""

        keyboard = [[InlineKeyboardButton("🔄 Refresh", callback_data="refresh_stats")]]
        reply_markup = InlineKeyboardMarkup(keyboard)

        if is_refresh:
            return stats_message, reply_markup
        else:
            await context.bot.send_message(
                chat_id=chat_id,
                text=stats_message,
                parse_mode="HTML",
                reply_markup=reply_markup,
                disable_web_page_preview=True
            )
    except Exception as e:
        logger.error(f"❌ Error generating stats message: {e}")
        if not is_refresh:
            await context.bot.send_message(chat_id, "❌ Error generating statistics!")
