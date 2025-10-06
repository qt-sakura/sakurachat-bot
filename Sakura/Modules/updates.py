from pyrogram import Client, filters
from pyrogram.types import ChatMemberUpdated
from pyrogram.enums import ChatMemberStatus, ChatType
from Sakura.Core.logging import logger
from Sakura.Database.database import remove_user, remove_group

@Client.on_chat_member_updated(filters.my_chat_member)
async def my_chat_member_handler(client: Client, update: ChatMemberUpdated):
    """Handle when the bot's chat member status changes."""
    new_status = update.new_chat_member.status
    chat = update.chat

    if new_status in [ChatMemberStatus.BANNED, ChatMemberStatus.LEFT]:
        if chat.type == ChatType.PRIVATE:
            logger.info(f"User {chat.id} blocked the bot. Removing from database.")
            await remove_user(chat.id)
        elif chat.type in [ChatType.GROUP, ChatType.SUPERGROUP]:
            logger.info(f"Bot was removed from group {chat.id}. Removing from database.")
            await remove_group(chat.id)