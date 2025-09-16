import random
from telegram import Update, ChatMember
from telegram.ext import ContextTypes

from ..utils.messages import log_with_user_info, extract_user_info
from ..utils.actions import send_sticker_action, send_typing_action
from ..utils.helpers import (
    should_respond_in_group,
    get_error_response,
    track_user_and_chat,
)
from ..database.cache import is_rate_limited, update_user_response_time_valkey
from ..core.ai import get_gemini_response, analyze_image_with_gemini, analyze_poll_with_gemini, analyze_referenced_image, analyze_referenced_poll
from ..core.broadcast import execute_broadcast_direct
from ..database.users import remove_user_from_database
from ..database.groups import remove_group_from_database
from ..core.state import broadcast_mode
from ..config.settings import OWNER_ID
from ..config.constants import SAKURA_STICKERS
from ..commands.basic import ping_command


async def handle_sticker_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle sticker messages"""
    user_info = extract_user_info(update.message)
    log_with_user_info("INFO", "🎭 Sticker message received", user_info)

    await send_sticker_action(context, update.effective_chat.id, user_info)

    random_sticker = random.choice(SAKURA_STICKERS)
    chat_type = update.effective_chat.type

    log_with_user_info("DEBUG", f"📤 Sending random sticker: {random_sticker}", user_info)

    # In groups, reply to the user's sticker when they replied to bot
    if (chat_type in ['group', 'supergroup'] and
        update.message.reply_to_message and
        update.message.reply_to_message.from_user.id == context.bot.id):
        await update.message.reply_sticker(sticker=random_sticker)
        log_with_user_info("INFO", "✅ Replied to user's sticker in group", user_info)
    else:
        # In private chats or regular stickers, send normally
        await context.bot.send_sticker(
            chat_id=update.effective_chat.id,
            sticker=random_sticker
        )
        log_with_user_info("INFO", "✅ Sent sticker response", user_info)


async def handle_text_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle text and media messages with AI response and effects in private chat"""
    user_info = extract_user_info(update.message)
    user_message = update.message.text or update.message.caption or "Media message"

    log_with_user_info("INFO", f"💬 Text/media message received: '{user_message[:100]}...'", user_info)

    # Check if user is asking to analyze a previously sent image
    if await analyze_referenced_image(update, context, user_message, user_info):
        return

    # Check if user is asking to analyze a previously sent poll
    if await analyze_referenced_poll(update, context, user_message, user_info):
        return

    await send_typing_action(context, update.effective_chat.id, user_info)

    user_name = update.effective_user.first_name or ""

    # Get response from Gemini
    response = await get_gemini_response(user_message, user_name, user_info, update.effective_user.id)

    log_with_user_info("DEBUG", f"📤 Sending response: '{response[:50]}...'", user_info)

    # Send response (no effects for Gemini responses)
    await update.message.reply_text(response)

    log_with_user_info("INFO", "✅ Text message response sent successfully", user_info)


async def handle_image_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle image messages with AI analysis using Gemini 2.5 Flash"""
    user_info = extract_user_info(update.message)
    log_with_user_info("INFO", "📷 Image message received", user_info)

    await send_typing_action(context, update.effective_chat.id, user_info)

    try:
        # Get the largest photo
        photo = update.message.photo[-1]

        # Get file info
        file = await context.bot.get_file(photo.file_id)

        # Download the image
        image_bytes = await file.download_as_bytearray()

        log_with_user_info("DEBUG", f"📥 Image downloaded: {len(image_bytes)} bytes", user_info)

        # Analyze image with Gemini 2.5 Flash
        user_name = update.effective_user.first_name or ""
        caption = update.message.caption or ""

        response = await analyze_image_with_gemini(image_bytes, caption, user_name, user_info, update.effective_user.id)

        log_with_user_info("DEBUG", f"📤 Sending image analysis: '{response[:50]}...'", user_info)

        # Send response (no effects for Gemini responses)
        await update.message.reply_text(response)

        log_with_user_info("INFO", "✅ Image analysis response sent successfully", user_info)

    except Exception as e:
        log_with_user_info("ERROR", f"❌ Error analyzing image: {e}", user_info)
        await update.message.reply_text(get_error_response())


async def handle_poll_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle poll messages with AI analysis using Gemini 2.5 Flash"""
    user_info = extract_user_info(update.message)
    log_with_user_info("INFO", "📊 Poll message received", user_info)

    await send_typing_action(context, update.effective_chat.id, user_info)

    try:
        poll = update.message.poll
        poll_question = poll.question
        poll_options = [option.text for option in poll.options]

        log_with_user_info("DEBUG", f"📊 Poll question: '{poll_question}' with {len(poll_options)} options", user_info)

        # Analyze poll with Gemini 2.5 Flash
        user_name = update.effective_user.first_name or ""

        response = await analyze_poll_with_gemini(poll_question, poll_options, user_name, user_info, update.effective_user.id)

        log_with_user_info("DEBUG", f"📤 Sending poll analysis: '{response[:50]}...'", user_info)

        # Send response (no effects for Gemini responses)
        await update.message.reply_text(response)

        log_with_user_info("INFO", "✅ Poll analysis response sent successfully", user_info)

    except Exception as e:
        log_with_user_info("ERROR", f"❌ Error analyzing poll: {e}", user_info)
        await update.message.reply_text(get_error_response())


async def handle_all_messages(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle all types of messages (text, stickers, voice, photos, etc.)"""
    try:
        user_info = extract_user_info(update.message)
        user_id = update.effective_user.id
        chat_type = update.effective_chat.type

        log_with_user_info("DEBUG", f"📨 Processing message in {chat_type}", user_info)

        # Track user and chat IDs for broadcasting
        track_user_and_chat(update, user_info)

        # Check if user is owner and in broadcast mode
        if user_id == OWNER_ID and OWNER_ID in broadcast_mode:
            log_with_user_info("INFO", f"📢 Executing broadcast to {broadcast_mode[OWNER_ID]}", user_info)
            await execute_broadcast_direct(update, context, broadcast_mode[OWNER_ID], user_info)
            del broadcast_mode[OWNER_ID]
            return

        # Check for ping command with prefixes BEFORE group response logic
        user_message = update.message.text or update.message.caption or ""
        ping_prefixes = ['?ping', '!ping', '*ping', '#ping']
        if any(user_message.lower().startswith(prefix) for prefix in ping_prefixes):
            log_with_user_info("INFO", f"🏓 Ping command detected with prefix: {user_message}", user_info)
            await ping_command(update, context)
            return

        # Determine if bot should respond
        should_respond = True
        if chat_type in ['group', 'supergroup']:
            should_respond = should_respond_in_group(update, context.bot.id)
            if not should_respond:
                log_with_user_info("DEBUG", "🚫 Not responding to group message (no mention/reply)", user_info)
                return
            else:
                log_with_user_info("INFO", "✅ Responding to group message (mentioned/replied)", user_info)

        # Check rate limiting (using Valkey with memory fallback)
        if await is_rate_limited(user_id, user_info["chat_id"]):
            log_with_user_info("WARNING", "⏱️ Rate limited - ignoring message", user_info)
            return

        # Handle different message types
        if update.message.sticker:
            await handle_sticker_message(update, context)
        elif update.message.photo:
            await handle_image_message(update, context)
        elif update.message.poll:
            await handle_poll_message(update, context)
        else:
            await handle_text_message(update, context)

        # Update response time after sending response
        await update_user_response_time_valkey(user_id)
        log_with_user_info("DEBUG", "⏰ Updated user response time in Valkey", user_info)

    except Exception as e:
        user_info = extract_user_info(update.message)
        log_with_user_info("ERROR", f"❌ Error handling message: {e}", user_info)
        if update.message.text:
            await update.message.reply_text(get_error_response())


async def handle_chat_member_update(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle when a user blocks the bot or the bot is removed from a group."""
    result = update.my_chat_member
    if not result:
        return

    chat = result.chat
    new_status = result.new_chat_member.status

    if new_status in [ChatMember.BANNED, ChatMember.LEFT]:
        if chat.type == 'private':
            log_with_user_info("INFO", f"User {chat.id} blocked the bot. Removing from database.", extract_user_info(update.message))
            await remove_user_from_database(chat.id)
        elif chat.type in ['group', 'supergroup']:
            log_with_user_info("INFO", f"Bot was removed from group {chat.id}. Removing from database.", extract_user_info(update.message))
            await remove_group_from_database(chat.id)


async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Log the error and send a message to the user."""
    logger.error("Exception while handling an update:", exc_info=context.error)

    # Try to extract user info for more detailed logging
    user_info = {}
    message = None
    if hasattr(update, 'message') and update.message:
        message = update.message
    elif hasattr(update, 'callback_query') and update.callback_query:
        message = update.callback_query.message

    if message:
        try:
            user_info = extract_user_info(message)
            log_with_user_info("ERROR", f"An exception was raised while handling an update: {context.error}", user_info)
        except Exception as e:
            logger.error(f"Could not extract user info for error logging: {e}")
    else:
        logger.error(f"An exception was raised for an update without a message object: {context.error}")
