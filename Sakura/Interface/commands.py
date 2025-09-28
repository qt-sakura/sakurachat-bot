import random
import time
import psutil
import datetime
from telegram import Update, BotCommand
from telegram.ext import ContextTypes
from telegram.constants import ParseMode
from Sakura.Core.helpers import fetch_user, log_action, get_mention
from Sakura.Features.tracking import track_user
from Sakura.Interface.reactions import EMOJI_REACT
from Sakura.Interface.effects import animate_reaction, add_reaction, photo_effect
from Sakura.Interface.typing import sticker_action, photo_action
from Sakura.Storage.storage import START_STICKERS, SAKURA_IMAGES
from Sakura.Interface.keyboards import start_menu, help_menu, broadcast_menu
from Sakura.Core.utils import get_error
from Sakura.Core.config import PING_LINK, OWNER_ID
from Sakura.Storage.database import get_users, get_groups, get_purchases
from Sakura.Interface.messages import (
    START_MESSAGES,
    HELP_MESSAGES,
    BROADCAST_MESSAGES,
)
from Sakura.application import user_ids, group_ids, effects_client


COMMANDS = [
    BotCommand("start", "👋 Wake me up"),
    BotCommand("buy", "🌸 Get flowers"),
    BotCommand("buyers", "💝 Flower buyers"),
    BotCommand("help", "💬 A short guide")
]


async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /start command with two-step inline buttons and effects in private chat"""
    try:
        user_info = fetch_user(update.message)
        log_action("INFO", "🌸 /start command received", user_info)

        track_user(update, user_info)

        if EMOJI_REACT:
            try:
                random_emoji = random.choice(EMOJI_REACT)
                if effects_client and update.effective_chat.type == "private":
                    reaction_sent = await animate_reaction(
                        update.effective_chat.id,
                        update.message.message_id,
                        random_emoji
                    )
                    if not reaction_sent:
                        await add_reaction(context, update, random_emoji, user_info)
                else:
                    await add_reaction(context, update, random_emoji, user_info)
            except Exception as e:
                log_action("WARNING", f"⚠️ Failed to add emoji reaction: {e}", user_info)

        if update.effective_chat.type == "private" and START_STICKERS:
            await sticker_action(context, update.effective_chat.id, user_info)
            random_sticker = random.choice(START_STICKERS)
            await context.bot.send_sticker(
                chat_id=update.effective_chat.id,
                sticker=random_sticker
            )
            log_action("INFO", "✅ Start sticker sent successfully", user_info)

        await photo_action(context, update.effective_chat.id, user_info)

        random_image = random.choice(SAKURA_IMAGES)
        keyboard = start_menu()
        user_mention = get_mention(update.effective_user)
        caption = START_MESSAGES["initial_caption"].format(user_mention=user_mention)

        if update.effective_chat.type == "private":
            effect_sent = await photo_effect(
                update.effective_chat.id,
                random_image,
                caption,
                keyboard
            )
            if not effect_sent:
                await context.bot.send_photo(
                    chat_id=update.effective_chat.id,
                    photo=random_image,
                    caption=caption,
                    parse_mode=ParseMode.HTML,
                    reply_markup=keyboard
                )
        else:
            await context.bot.send_photo(
                chat_id=update.effective_chat.id,
                photo=random_image,
                caption=caption,
                parse_mode=ParseMode.HTML,
                reply_markup=keyboard
            )

        log_action("INFO", "✅ Start command completed successfully", user_info)

    except Exception as e:
        user_info = fetch_user(update.message)
        log_action("ERROR", f"❌ Error in start command: {e}", user_info)
        await update.message.reply_text(get_error())


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /help command with random image and effects in private chat"""
    try:
        user_info = fetch_user(update.message)
        log_action("INFO", "ℹ️ /help command received", user_info)

        track_user(update, user_info)

        if EMOJI_REACT:
            try:
                random_emoji = random.choice(EMOJI_REACT)
                if effects_client and update.effective_chat.type == "private":
                    reaction_sent = await animate_reaction(
                        update.effective_chat.id,
                        update.message.message_id,
                        random_emoji
                    )
                    if not reaction_sent:
                        await add_reaction(context, update, random_emoji, user_info)
                else:
                    await add_reaction(context, update, random_emoji, user_info)
            except Exception as e:
                log_action("WARNING", f"⚠️ Failed to add emoji reaction: {e}", user_info)

        await photo_action(context, update.effective_chat.id, user_info)

        keyboard = help_menu(expanded=False)
        user_mention = get_mention(update.effective_user)
        caption = HELP_MESSAGES["minimal"].format(user_mention=user_mention)

        random_image = random.choice(SAKURA_IMAGES)

        if update.effective_chat.type == "private":
            effect_sent = await photo_effect(
                update.effective_chat.id,
                random_image,
                caption,
                keyboard
            )
            if not effect_sent:
                await context.bot.send_photo(
                    chat_id=update.effective_chat.id,
                    photo=random_image,
                    caption=caption,
                    parse_mode=ParseMode.HTML,
                    reply_markup=keyboard
                )
        else:
            await context.bot.send_photo(
                chat_id=update.effective_chat.id,
                photo=random_image,
                caption=caption,
                parse_mode=ParseMode.HTML,
                reply_markup=keyboard
            )

        log_action("INFO", "✅ Help command completed successfully", user_info)

    except Exception as e:
        user_info = fetch_user(update.message)
        log_action("ERROR", f"❌ Error in help command: {e}", user_info)
        await update.message.reply_text(get_error())


async def broadcast_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle broadcast command (owner only)"""
    user_info = fetch_user(update.message)

    if update.effective_user.id != OWNER_ID:
        log_action("WARNING", "⚠️ Non-owner attempted broadcast command", user_info)
        return

    log_action("INFO", "📢 Broadcast command received from owner", user_info)

    db_users = await get_users()
    db_groups = await get_groups()

    user_ids.update(db_users)
    group_ids.update(db_groups)

    keyboard = broadcast_menu()
    text = BROADCAST_MESSAGES["select_target"].format(
        users_count=len(user_ids),
        groups_count=len(group_ids)
    )

    await update.message.reply_text(
        text,
        reply_markup=keyboard,
        parse_mode=ParseMode.HTML
    )

    log_action("INFO", "✅ Broadcast selection menu sent", user_info)


async def ping_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle ping command for everyone"""
    user_info = fetch_user(update.message)
    log_action("INFO", "🏓 Ping command received", user_info)

    start_time = time.time()
    msg = await update.message.reply_text("🛰️ Pinging...")
    response_time = round((time.time() - start_time) * 1000, 2)

    await msg.edit_text(
        f"🏓 <a href='{PING_LINK}'>Pong!</a> {response_time}ms",
        parse_mode=ParseMode.HTML,
        disable_web_page_preview=True
    )

    log_action("INFO", "✅ Ping completed", user_info)


async def buyers_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Show all flower buyers with their donation amounts."""
    try:
        user_info = fetch_user(update.message)
        log_action("INFO", "💝 /buyers command received", user_info)

        track_user(update, user_info)

        if EMOJI_REACT:
            try:
                random_emoji = random.choice(EMOJI_REACT)
                if effects_client and update.effective_chat.type == "private":
                    reaction_sent = await animate_reaction(
                        update.effective_chat.id,
                        update.message.message_id,
                        random_emoji
                    )
                    if not reaction_sent:
                        await add_reaction(context, update, random_emoji, user_info)
                else:
                    await add_reaction(context, update, random_emoji, user_info)
            except Exception as e:
                log_action("WARNING", f"⚠️ Failed to add emoji reaction: {e}", user_info)

        from Sakura.Interface.typing import send_typing
        await send_typing(context, update.effective_chat.id, user_info)

        purchases = await get_purchases()

        if not purchases:
            no_buyers_text = (
                "🌸 <b>Flower Buyers</b>\n\n"
                "No one has bought flowers yet! Be the first to support with /buy 💝"
            )
            await update.message.reply_text(no_buyers_text, parse_mode=ParseMode.HTML)
            return

        buyers_text = "🌸 <b>Flower Buyers</b>\n\n"
        buyers_text += "💝 <i>Thank you to all our wonderful supporters!</i>\n\n"

        for i, purchase in enumerate(purchases, 1):
            user_mention = f'<a href="tg://user?id={purchase["user_id"]}">{purchase["first_name"] or "Anonymous"}</a>'
            rank_emoji = "🥇" if i == 1 else "🥈" if i == 2 else "🥉" if i == 3 else f"{i}."
            buyers_text += f"{rank_emoji} {user_mention} - {purchase['total_amount']} ⭐"
            if purchase['purchase_count'] > 1:
                buyers_text += f" ({purchase['purchase_count']} purchases)"
            buyers_text += "\n"

        buyers_text += f"\n🌸 <i>Total buyers: {len(purchases)}</i>"

        await update.message.reply_text(
            buyers_text,
            parse_mode=ParseMode.HTML,
            disable_web_page_preview=True
        )

    except Exception as e:
        user_info = fetch_user(update.message)
        log_action("ERROR", f"❌ Error in buyers command: {e}", user_info)
        await update.message.reply_text("❌ Something went wrong getting the buyers list. Try again later! 🔧")


async def stats_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Hidden owner command to show bot statistics with refresh functionality"""
    try:
        user_info = fetch_user(update.message)
        if update.effective_user.id != OWNER_ID:
            log_action("WARNING", "⚠️ Non-owner attempted /stats command", user_info)
            return

        log_action("INFO", "📊 /stats command received from owner", user_info)
        from Sakura.Features.stats import send_stats
        await send_stats(update.message.chat.id, context, is_refresh=False)
        log_action("INFO", "✅ Bot statistics sent to owner", user_info)

    except Exception as e:
        user_info = fetch_user(update.message)
        log_action("ERROR", f"❌ Error in /stats command: {e}", user_info)
        await update.message.reply_text("❌ Something went wrong getting bot statistics!")