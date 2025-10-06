import random
import time
from pyrogram import Client, filters
from pyrogram.types import Message, BotCommand
from pyrogram.enums import ParseMode
from Sakura.Core.helpers import fetch_user, log_action, get_mention, get_error
from Sakura.Services.tracking import track_user
from Sakura.Modules.reactions import EMOJI_REACT
from Sakura.Modules.effects import animate_reaction, add_reaction, photo_effect
from Sakura.Modules.typing import sticker_action, photo_action
from Sakura.Database.constants import START_STICKERS, SAKURA_IMAGES
from Sakura.Modules.keyboards import start_menu, help_menu
from Sakura.Core.config import PING_LINK, OWNER_ID
from Sakura.Database.database import get_users, get_groups
from Sakura.Modules.messages import (
    START_MESSAGES,
    HELP_MESSAGES,
)
from Sakura import state

COMMANDS = [
    BotCommand("start", "👋 Wake me up"),
    BotCommand("meow", "🌸 Get flowers"),
    BotCommand("fams", "🎀 Pookie homies"),
    BotCommand("help", "💬 A short guide")
]

@Client.on_message(filters.command("start"))
async def start_command_handler(client: Client, message: Message) -> None:
    """Handle /start command"""
    try:
        user_info = fetch_user(message)
        log_action("INFO", "🌸 /start command received", user_info)
        await track_user(message, user_info)

        if EMOJI_REACT:
            try:
                random_emoji = random.choice(EMOJI_REACT)
                if message.chat.type == "private":
                    await animate_reaction(client, message.chat.id, message.id, random_emoji)
                else:
                    await add_reaction(client, message, random_emoji, user_info)
            except Exception as e:
                log_action("WARNING", f"⚠️ Failed to add emoji reaction: {e}", user_info)

        if message.chat.type == "private" and START_STICKERS:
            await sticker_action(client, message.chat.id, user_info)
            random_sticker = random.choice(START_STICKERS)
            await client.send_sticker(chat_id=message.chat.id, sticker=random_sticker)
            log_action("INFO", "✅ Start sticker sent successfully", user_info)

        await photo_action(client, message.chat.id, user_info)
        random_image = random.choice(SAKURA_IMAGES)
        keyboard = start_menu()
        user_mention = get_mention(message.from_user)
        caption = START_MESSAGES["initial_caption"].format(user_mention=user_mention)

        if message.chat.type == "private":
            await photo_effect(client, message.chat.id, random_image, caption, keyboard)
        else:
            await client.send_photo(
                chat_id=message.chat.id,
                photo=random_image,
                caption=caption,
                parse_mode=ParseMode.HTML,
                reply_markup=keyboard
            )
        log_action("INFO", "✅ Start command completed successfully", user_info)

    except Exception as e:
        user_info = fetch_user(message)
        log_action("ERROR", f"❌ Error in start command: {e}", user_info)
        await message.reply_text(get_error())

@Client.on_message(filters.command("help"))
async def help_command_handler(client: Client, message: Message) -> None:
    """Handle /help command"""
    try:
        user_info = fetch_user(message)
        log_action("INFO", "ℹ️ /help command received", user_info)
        await track_user(message, user_info)

        if EMOJI_REACT:
            try:
                random_emoji = random.choice(EMOJI_REACT)
                if message.chat.type == "private":
                    await animate_reaction(client, message.chat.id, message.id, random_emoji)
                else:
                    await add_reaction(client, message, random_emoji, user_info)
            except Exception as e:
                log_action("WARNING", f"⚠️ Failed to add emoji reaction: {e}", user_info)

        await photo_action(client, message.chat.id, user_info)
        keyboard = help_menu(expanded=False)
        user_mention = get_mention(message.from_user)
        caption = HELP_MESSAGES["minimal"].format(user_mention=user_mention)
        random_image = random.choice(SAKURA_IMAGES)

        if message.chat.type == "private":
            await photo_effect(client, message.chat.id, random_image, caption, keyboard)
        else:
            await client.send_photo(
                chat_id=message.chat.id,
                photo=random_image,
                caption=caption,
                parse_mode=ParseMode.HTML,
                reply_markup=keyboard
            )
        log_action("INFO", "✅ Help command completed successfully", user_info)

    except Exception as e:
        user_info = fetch_user(message)
        log_action("ERROR", f"❌ Error in help command: {e}", user_info)
        await message.reply_text(get_error())

@Client.on_message(filters.command("broadcast") & filters.user(OWNER_ID))
async def broadcast_command_handler(client: Client, message: Message) -> None:
    """Handle broadcast command (owner only)"""
    user_info = fetch_user(message)
    log_action("INFO", "📢 Broadcast command received from owner", user_info)
    state.user_ids.update(await get_users())
    state.group_ids.update(await get_groups())

    from Sakura.Modules.keyboards import broadcast_menu
    from Sakura.Modules.messages import BROADCAST_MESSAGES

    keyboard = broadcast_menu()
    text = BROADCAST_MESSAGES["select_target"].format(
        users_count=len(state.user_ids),
        groups_count=len(state.group_ids)
    )
    await message.reply_text(text, reply_markup=keyboard, parse_mode=ParseMode.HTML)
    log_action("INFO", "✅ Broadcast selection menu sent", user_info)

@Client.on_message(filters.command("ping"))
async def ping_command_handler(client: Client, message: Message) -> None:
    """Handle ping command"""
    user_info = fetch_user(message)
    log_action("INFO", "🏓 Ping command received", user_info)
    start_time = time.time()
    msg = await message.reply_text("🛰️ Pinging...")
    response_time = round((time.time() - start_time) * 1000, 2)
    await msg.edit_text(
        f"🏓 <a href='{PING_LINK}'>Pong!</a> {response_time}ms",
        parse_mode=ParseMode.HTML,
        disable_web_page_preview=True
    )
    log_action("INFO", "✅ Ping completed", user_info)

@Client.on_message(filters.command("stats") & filters.user(OWNER_ID))
async def stats_command_handler(client: Client, message: Message) -> None:
    """Hidden owner command to show bot statistics"""
    try:
        user_info = fetch_user(message)
        log_action("INFO", "📊 /stats command received from owner", user_info)
        from Sakura.Services.stats import send_stats
        await send_stats(message.chat.id, client, is_refresh=False)
        log_action("INFO", "✅ Bot statistics sent to owner", user_info)
    except Exception as e:
        user_info = fetch_user(message)
        log_action("ERROR", f"❌ Error in /stats command: {e}", user_info)
        await message.reply_text("❌ Something went wrong getting bot statistics!")