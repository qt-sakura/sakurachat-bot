import random
from pyrogram import Client
from pyrogram.types import Message
from pyrogram.enums import ChatType
from Sakura.Core.helpers import fetch_user, log_action
from Sakura.Modules.typing import sticker_action
from Sakura.Database.constants import SAKURA_STICKERS

async def handle_sticker(client: Client, message: Message) -> None:
    """Handle sticker messages"""
    user_info = fetch_user(message)
    log_action("INFO", "🎭 Sticker message received", user_info)

    await sticker_action(client, message.chat.id, user_info)

    random_sticker = random.choice(SAKURA_STICKERS)
    chat_type = message.chat.type

    log_action("DEBUG", f"📤 Sending random sticker: {random_sticker}", user_info)

    if (chat_type in [ChatType.GROUP, ChatType.SUPERGROUP] and
        message.reply_to_message and
        message.reply_to_message.from_user.id == client.me.id):
        await message.reply_sticker(sticker=random_sticker)
        log_action("INFO", "✅ Replied to user's sticker in group", user_info)
    else:
        await client.send_sticker(
            chat_id=message.chat.id,
            sticker=random_sticker
        )
        log_action("INFO", "✅ Sent sticker response", user_info)