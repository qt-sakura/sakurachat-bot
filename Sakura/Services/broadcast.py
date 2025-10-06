import asyncio
from pyrogram import Client
from pyrogram.types import Message
from pyrogram.enums import ParseMode
from pyrogram.errors import UserIsBlocked, PeerIdInvalid, ChatAdminRequired, FloodWait
from Sakura.Core.helpers import log_action
from Sakura.Database.database import get_users, get_groups, remove_user, remove_group
from Sakura.Modules.messages import BROADCAST_MESSAGES
from Sakura.Core.config import BROADCAST_DELAY

async def execute_broadcast(message: Message, client: Client, target_type: str, user_info: dict) -> None:
    """Execute broadcast with the current message"""
    try:
        if target_type == "users":
            target_list = await get_users()
            target_list = [uid for uid in target_list if uid != user_info["user_id"]]
            target_name = "users"
        elif target_type == "groups":
            target_list = await get_groups()
            target_name = "groups"
        else:
            return

        log_action("INFO", f"🚀 Starting broadcast to {len(target_list)} {target_name}", user_info)

        if not target_list:
            await message.reply_text(
                BROADCAST_MESSAGES["no_targets"].format(target_type=target_name)
            )
            log_action("WARNING", f"⚠️ No {target_name} found for broadcast", user_info)
            return

        is_forward = message.forward_from or message.forward_from_chat
        broadcast_method = "forward" if is_forward else "copy"
        log_action("INFO", f"📤 Using {broadcast_method} method for broadcast", user_info)

        status_msg = await message.reply_text(
            BROADCAST_MESSAGES["progress"].format(count=len(target_list), target_type=target_name)
        )

        broadcast_count = 0
        failed_count = 0

        for i, target_id in enumerate(target_list, 1):
            try:
                if is_forward:
                    await client.forward_messages(
                        chat_id=target_id,
                        from_chat_id=message.chat.id,
                        message_ids=message.id
                    )
                else:
                    await message.copy(chat_id=target_id)
                broadcast_count += 1
                if i % 10 == 0:
                    log_action("DEBUG", f"📡 Broadcast progress: {i}/{len(target_list)} using {broadcast_method}", user_info)
                await asyncio.sleep(BROADCAST_DELAY)

            except FloodWait as e:
                log_action("WARNING", f"⏳ Flood wait of {e.value} seconds requested. Pausing broadcast.", user_info)
                await asyncio.sleep(e.value)
                if is_forward:
                    await client.forward_messages(chat_id=target_id, from_chat_id=message.chat.id, message_ids=message.id)
                else:
                    await message.copy(chat_id=target_id)
                broadcast_count += 1
            except (UserIsBlocked, PeerIdInvalid):
                failed_count += 1
                if target_name == "users":
                    await remove_user(target_id)
                elif target_name == "groups":
                    await remove_group(target_id)
            except (ChatAdminRequired, Exception) as e:
                failed_count += 1
                log_action("ERROR", f"❌ Broadcast failed for {target_id}: {e}", user_info)

        await status_msg.edit_text(
            BROADCAST_MESSAGES["completed"].format(
                success_count=broadcast_count,
                total_count=len(target_list),
                target_type=target_name,
                failed_count=failed_count
            ) + f"\n<i>Method used: {broadcast_method}</i>",
            parse_mode=ParseMode.HTML
        )
        log_action("INFO", f"✅ Broadcast completed using {broadcast_method}: {broadcast_count}/{len(target_list)} successful, {failed_count} failed", user_info)

    except Exception as e:
        log_action("ERROR", f"❌ Broadcast error: {e}", user_info)
        await message.reply_text(
            BROADCAST_MESSAGES["failed"].format(error=str(e))
        )