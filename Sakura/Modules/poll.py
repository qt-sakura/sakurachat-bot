import random
from pyrogram import Client
from pyrogram.types import Message
from Sakura.Core.helpers import fetch_user, log_action, get_error
from Sakura.Modules.reactions import CONTEXTUAL_REACTIONS
from Sakura.Modules.effects import animate_reaction
from Sakura.Modules.typing import send_typing
from Sakura.Chat.polls import analyze_poll

async def handle_poll(client: Client, message: Message) -> None:
    """Handle poll messages with AI analysis"""
    user_info = fetch_user(message)
    log_action("INFO", "📊 Poll message received", user_info)

    try:
        emoji_to_react = random.choice(CONTEXTUAL_REACTIONS["confused"])
        await animate_reaction(
            client,
            chat_id=message.chat.id,
            message_id=message.id,
            emoji=emoji_to_react
        )
        log_action("INFO", f"🤔 Sent analysis reaction '{emoji_to_react}' for poll", user_info)
    except Exception as e:
        log_action("WARNING", f"⚠️ Could not send analysis reaction for poll: {e}", user_info)

    await send_typing(client, message.chat.id, user_info)

    try:
        poll = message.poll
        poll_question = poll.question
        poll_options = [option.text for option in poll.options]
        log_action("DEBUG", f"📊 Poll question: '{poll_question}' with {len(poll_options)} options", user_info)

        response = await analyze_poll(poll_question, poll_options, user_info, message.from_user.id)

        log_action("DEBUG", f"📤 Sending poll analysis: '{response[:50]}...'", user_info)
        await message.reply_text(response)
        log_action("INFO", "✅ Poll analysis response sent successfully", user_info)

    except Exception as e:
        log_action("ERROR", f"❌ Error analyzing poll: {e}", user_info)
        await message.reply_text(get_error())