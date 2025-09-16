import asyncio
from telegram import Update
from telegram.ext import ContextTypes
from telegram.error import Forbidden, BadRequest
from telegram.constants import ParseMode

from ..utils.messages import log_with_user_info
from ..database.users import get_users_from_database, remove_user_from_database
from ..database.groups import get_groups_from_database, remove_group_from_database
from ..config.settings import OWNER_ID
from ..config.constants import BROADCAST_DELAY, BROADCAST_MESSAGES


async def execute_broadcast_direct(update: Update, context: ContextTypes.DEFAULT_TYPE, target_type: str, user_info: dict) -> None:
    """Execute broadcast with the current message - uses forward_message for forwarded messages, copy_message for regular messages
    Compatible with python-telegram-bot==22.3"""
    try:
        if target_type == "users":
            # Get fresh data from database
            target_list = await get_users_from_database()
            target_list = [uid for uid in target_list if uid != OWNER_ID]
            target_name = "users"
        elif target_type == "groups":
            # Get fresh data from database
            target_list = await get_groups_from_database()
            target_name = "groups"
        else:
            return

        log_with_user_info("INFO", f"🚀 Starting broadcast to {len(target_list)} {target_name}", user_info)

        if not target_list:
            await update.message.reply_text(
                BROADCAST_MESSAGES["no_targets"].format(target_type=target_name)
            )
            log_with_user_info("WARNING", f"⚠️ No {target_name} found for broadcast", user_info)
            return

        # Check if the message is forwarded
        is_forwarded = update.message.forward_origin is not None
        broadcast_method = "forward" if is_forwarded else "copy"

        log_with_user_info("INFO", f"📤 Using {broadcast_method} method for broadcast", user_info)

        # Show initial status
        status_msg = await update.message.reply_text(
            BROADCAST_MESSAGES["progress"].format(count=len(target_list), target_type=target_name)
        )

        broadcast_count = 0
        failed_count = 0

        # Broadcast the current message to all targets
        for i, target_id in enumerate(target_list, 1):
            try:
                if is_forwarded:
                    # Use forward_message for forwarded messages to preserve forwarding chain
                    await context.bot.forward_message(
                        chat_id=target_id,
                        from_chat_id=update.effective_chat.id,
                        message_id=update.message.message_id
                    )
                else:
                    # Use copy_message for regular messages
                    await context.bot.copy_message(
                        chat_id=target_id,
                        from_chat_id=update.effective_chat.id,
                        message_id=update.message.message_id
                    )

                broadcast_count += 1

                if i % 10 == 0:  # Log progress every 10 messages
                    log_with_user_info("DEBUG", f"📡 Broadcast progress: {i}/{len(target_list)} using {broadcast_method}", user_info)

                # Small delay to avoid rate limits
                await asyncio.sleep(BROADCAST_DELAY)

            except Forbidden:
                failed_count += 1
                log_with_user_info("WARNING", f"⚠️ User {target_id} blocked the bot. Removing from DB.", user_info)
                await remove_user_from_database(target_id)
            except BadRequest as e:
                failed_count += 1
                if "chat not found" in str(e).lower():
                    log_with_user_info("WARNING", f"⚠️ Chat {target_id} not found. Removing from DB.", user_info)
                    if target_name == "users":
                        await remove_user_from_database(target_id)
                    else:
                        await remove_group_from_database(target_id)
                else:
                    log_with_user_info("ERROR", f"❌ Broadcast failed for {target_id}: {e}", user_info)
            except Exception as e:
                failed_count += 1
                log_with_user_info("ERROR", f"❌ Unhandled broadcast error for {target_id}: {e}", user_info)

        # Final status update
        await status_msg.edit_text(
            BROADCAST_MESSAGES["completed"].format(
                success_count=broadcast_count,
                total_count=len(target_list),
                target_type=target_name,
                failed_count=failed_count
            ) + f"\n<i>Method used: {broadcast_method}</i>",
            parse_mode=ParseMode.HTML
        )

        log_with_user_info("INFO", f"✅ Broadcast completed using {broadcast_method}: {broadcast_count}/{len(target_list)} successful, {failed_count} failed", user_info)

    except Exception as e:
        log_with_user_info("ERROR", f"❌ Broadcast error: {e}", user_info)
        await update.message.reply_text(
            BROADCAST_MESSAGES["failed"].format(error=str(e))
        )
