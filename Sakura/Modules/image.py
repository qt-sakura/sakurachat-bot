import random
from pyrogram import Client
from pyrogram.types import Message
from Sakura.Core.helpers import fetch_user, log_action, get_error
from Sakura.Modules.reactions import CONTEXTUAL_REACTIONS
from Sakura.Modules.effects import animate_reaction
from Sakura.Modules.typing import send_typing
from Sakura.Chat.response import get_response

async def handle_image(client: Client, message: Message) -> None:
    """Handle image messages with AI analysis"""
    user_info = fetch_user(message)
    log_action("INFO", "📷 Image message received", user_info)

    try:
        emoji_to_react = random.choice(CONTEXTUAL_REACTIONS["love"])
        await animate_reaction(
            client,
            chat_id=message.chat.id,
            message_id=message.id,
            emoji=emoji_to_react
        )
        log_action("INFO", f"🤔 Sent analysis reaction '{emoji_to_react}' for image", user_info)
    except Exception as e:
        log_action("WARNING", f"⚠️ Could not send analysis reaction for image: {e}", user_info)

    await send_typing(client, message.chat.id, user_info)

    try:
        log_action("DEBUG", "📥 Downloading image...", user_info)
        image_bytes = await client.download_media(message.photo.file_id, in_memory=True)
        log_action("DEBUG", f"📥 Image downloaded: {len(image_bytes)} bytes", user_info)

        user_name = message.from_user.first_name or ""
        caption = message.caption or ""

        response = await get_response(caption, user_name, user_info, message.from_user.id, image_bytes=bytes(image_bytes))

        log_action("DEBUG", f"📤 Sending image analysis: '{response[:50]}...'", user_info)
        await message.reply_text(response)
        log_action("INFO", "✅ Image analysis response sent successfully", user_info)

    except Exception as e:
        log_action("ERROR", f"❌ Error analyzing image: {e}", user_info)
        await message.reply_text(get_error())