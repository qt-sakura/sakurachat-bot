from telegram import Update
from telegram.ext import ContextTypes
from telegram.constants import ParseMode

from ..utils.messages import log_with_user_info, extract_user_info
from ..utils.keyboards import create_broadcast_keyboard, get_broadcast_text
from ..utils.helpers import send_stats_message
from ..database.groups import get_groups_from_database, group_ids
from ..database.users import get_users_from_database, user_ids
from ..config.settings import OWNER_ID


async def broadcast_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle broadcast command (owner only)"""
    user_info = extract_user_info(update.message)

    if update.effective_user.id != OWNER_ID:
        log_with_user_info("WARNING", "⚠️ Non-owner attempted broadcast command", user_info)
        return

    log_with_user_info("INFO", "📢 Broadcast command received from owner", user_info)

    db_users = await get_users_from_database()
    db_groups = await get_groups_from_database()

    user_ids.update(db_users)
    group_ids.update(db_groups)

    keyboard = create_broadcast_keyboard()
    broadcast_text = get_broadcast_text()

    await update.message.reply_text(
        broadcast_text,
        reply_markup=keyboard,
        parse_mode=ParseMode.HTML
    )

    log_with_user_info("INFO", "✅ Broadcast selection menu sent", user_info)


async def stats_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Hidden owner command to show bot statistics with refresh functionality"""
    try:
        user_info = extract_user_info(update.message)

        if update.effective_user.id != OWNER_ID:
            log_with_user_info("WARNING", "⚠️ Non-owner attempted /stats command", user_info)
            return

        log_with_user_info("INFO", "📊 /stats command received from owner", user_info)
        await send_stats_message(update.message.chat.id, context, is_refresh=False)
        log_with_user_info("INFO", "✅ Bot statistics sent to owner", user_info)

    except Exception as e:
        user_info = extract_user_info(update.message)
        log_with_user_info("ERROR", f"❌ Error in /stats command: {e}", user_info)
        await update.message.reply_text("❌ Something went wrong getting bot statistics!")
