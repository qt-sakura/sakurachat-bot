import time
import random
from telegram import (
    Update,
    LabeledPrice,
)
from telegram.ext import (
    ContextTypes,
)
from telegram.constants import ParseMode

from ..utils.messages import log_with_user_info, extract_user_info, get_user_mention
from ..utils.actions import send_sticker_action, send_photo_action, send_typing_action
from ..utils.keyboards import (
    create_initial_start_keyboard,
    create_help_keyboard,
    get_help_text,
    get_initial_start_caption,
)
from ..utils.helpers import get_error_response, track_user_and_chat
from ..core.effects import send_animated_reaction, add_ptb_reaction, send_with_effect_photo, effects_client
from ..database.purchases import get_all_purchases
from ..config.constants import (
    EMOJI_REACT,
    START_STICKERS,
    SAKURA_IMAGES,
    GROUP_LINK,
    INVOICE_DESCRIPTIONS,
)


async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /start command with two-step inline buttons and effects in private chat"""
    try:
        user_info = extract_user_info(update.message)
        log_with_user_info("INFO", "🌸 /start command received", user_info)

        track_user_and_chat(update, user_info)

        if EMOJI_REACT:
            try:
                random_emoji = random.choice(EMOJI_REACT)
                if effects_client and update.effective_chat.type == "private":
                    reaction_sent = await send_animated_reaction(
                        update.effective_chat.id,
                        update.message.message_id,
                        random_emoji
                    )
                    if not reaction_sent:
                        await add_ptb_reaction(context, update, random_emoji)
                else:
                    await add_ptb_reaction(context, update, random_emoji)
            except Exception as e:
                log_with_user_info("WARNING", f"⚠️ Failed to add emoji reaction: {e}", user_info)

        if update.effective_chat.type == "private" and START_STICKERS:
            await send_sticker_action(context, update.effective_chat.id, user_info)
            random_sticker = random.choice(START_STICKERS)
            await context.bot.send_sticker(chat_id=update.effective_chat.id, sticker=random_sticker)
            log_with_user_info("INFO", "✅ Start sticker sent successfully", user_info)

        await send_photo_action(context, update.effective_chat.id, user_info)
        random_image = random.choice(SAKURA_IMAGES)
        keyboard = create_initial_start_keyboard()
        user_mention = get_user_mention(update.effective_user)
        caption = get_initial_start_caption(user_mention)

        if update.effective_chat.type == "private":
            effect_sent = await send_with_effect_photo(
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
        log_with_user_info("INFO", "✅ Start command completed successfully", user_info)

    except Exception as e:
        user_info = extract_user_info(update.message)
        log_with_user_info("ERROR", f"❌ Error in start command: {e}", user_info)
        await update.message.reply_text(get_error_response())


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /help command with random image and effects in private chat"""
    try:
        user_info = extract_user_info(update.message)
        log_with_user_info("INFO", "ℹ️ /help command received", user_info)

        track_user_and_chat(update, user_info)

        if EMOJI_REACT:
            try:
                random_emoji = random.choice(EMOJI_REACT)
                if effects_client and update.effective_chat.type == "private":
                    reaction_sent = await send_animated_reaction(
                        update.effective_chat.id,
                        update.message.message_id,
                        random_emoji
                    )
                    if not reaction_sent:
                        await add_ptb_reaction(context, update, random_emoji)
                else:
                    await add_ptb_reaction(context, update, random_emoji)
            except Exception as e:
                log_with_user_info("WARNING", f"⚠️ Failed to add emoji reaction: {e}", user_info)

        await send_photo_action(context, update.effective_chat.id, user_info)
        user_id = update.effective_user.id
        keyboard = create_help_keyboard(user_id, False)
        user_mention = get_user_mention(update.effective_user)
        help_text = get_help_text(user_mention, False)
        random_image = random.choice(SAKURA_IMAGES)

        if update.effective_chat.type == "private":
            effect_sent = await send_with_effect_photo(
                update.effective_chat.id,
                random_image,
                help_text,
                keyboard
            )
            if not effect_sent:
                await context.bot.send_photo(
                    chat_id=update.effective_chat.id,
                    photo=random_image,
                    caption=help_text,
                    parse_mode=ParseMode.HTML,
                    reply_markup=keyboard
                )
        else:
            await context.bot.send_photo(
                chat_id=update.effective_chat.id,
                photo=random_image,
                caption=help_text,
                parse_mode=ParseMode.HTML,
                reply_markup=keyboard
            )
        log_with_user_info("INFO", "✅ Help command completed successfully", user_info)

    except Exception as e:
        user_info = extract_user_info(update.message)
        log_with_user_info("ERROR", f"❌ Error in help command: {e}", user_info)
        await update.message.reply_text(get_error_response())


async def ping_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle ping command for everyone"""
    user_info = extract_user_info(update.message)
    log_with_user_info("INFO", "🏓 Ping command received", user_info)

    start_time = time.time()
    msg = await update.message.reply_text("🛰️ Pinging...")
    response_time = round((time.time() - start_time) * 1000, 2)
    await msg.edit_text(
        f"🏓 <a href='{GROUP_LINK}'>Pong!</a> {response_time}ms",
        parse_mode=ParseMode.HTML,
        disable_web_page_preview=True
    )
    log_with_user_info("INFO", "✅ Ping completed", user_info)


async def buy_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Send an invoice for sakura flowers."""
    try:
        user_info = extract_user_info(update.message)
        log_with_user_info("INFO", "🌸 /buy command received", user_info)

        track_user_and_chat(update, user_info)

        if EMOJI_REACT:
            try:
                random_emoji = random.choice(EMOJI_REACT)
                if effects_client and update.effective_chat.type == "private":
                    reaction_sent = await send_animated_reaction(
                        update.effective_chat.id,
                        update.message.message_id,
                        random_emoji
                    )
                    if not reaction_sent:
                        await add_ptb_reaction(context, update, random_emoji)
                else:
                    await add_ptb_reaction(context, update, random_emoji)
            except Exception as e:
                log_with_user_info("WARNING", f"⚠️ Failed to add emoji reaction: {e}", user_info)

        await send_typing_action(context, update.effective_chat.id, user_info)
        amount = 50
        if len(update.message.text.split()) > 1 and update.message.text.split()[1].isdigit():
            amount = int(update.message.text.split()[1])
            if amount > 100000:
                amount = 100000
            elif amount < 1:
                amount = 1

        await context.bot.send_invoice(
            chat_id=update.message.chat.id,
            title="Flowers 🌸",
            description=random.choice(INVOICE_DESCRIPTIONS),
            payload=f"sakura_star_{update.message.from_user.id}",
            provider_token="",
            currency="XTR",
            prices=[LabeledPrice(label='✨ Sakura Star', amount=amount)]
        )
        log_with_user_info("INFO", f"✅ Invoice sent for {amount} stars", user_info)

    except Exception as e:
        user_info = extract_user_info(update.message)
        log_with_user_info("ERROR", f"❌ Error sending invoice: {e}", user_info)
        await update.message.reply_text("❌ Oops! Something went wrong creating the invoice. Try again later! 🔧")


async def buyers_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Show all flower buyers with their donation amounts."""
    try:
        user_info = extract_user_info(update.message)
        log_with_user_info("INFO", "💝 /buyers command received", user_info)

        track_user_and_chat(update, user_info)

        if EMOJI_REACT:
            try:
                random_emoji = random.choice(EMOJI_REACT)
                if effects_client and update.effective_chat.type == "private":
                    reaction_sent = await send_animated_reaction(
                        update.effective_chat.id,
                        update.message.message_id,
                        random_emoji
                    )
                    if not reaction_sent:
                        await add_ptb_reaction(context, update, random_emoji)
                else:
                    await add_ptb_reaction(context, update, random_emoji)
            except Exception as e:
                log_with_user_info("WARNING", f"⚠️ Failed to add emoji reaction: {e}", user_info)

        await send_typing_action(context, update.effective_chat.id, user_info)
        purchases = await get_all_purchases()

        if not purchases:
            no_buyers_text = (
                "🌸 <b>Flower Buyers</b>\n\n"
                "No one has bought flowers yet! Be the first to support with /buy 💝"
            )
            await update.message.reply_text(no_buyers_text, parse_mode=ParseMode.HTML)
            log_with_user_info("INFO", "✅ No buyers found message sent", user_info)
            return

        buyers_text = "🌸 <b>Flower Buyers</b>\n\n"
        buyers_text += "💝 <i>Thank you to all our wonderful supporters!</i>\n\n"
        for i, purchase in enumerate(purchases, 1):
            user_id = purchase['user_id']
            first_name = purchase['first_name'] or "Anonymous"
            total_amount = purchase['total_amount']
            purchase_count = purchase['purchase_count']
            user_mention = f'<a href="tg://user?id={user_id}">{first_name}</a>'
            rank_emoji = "🥇" if i == 1 else "🥈" if i == 2 else "🥉" if i == 3 else f"{i}."
            buyers_text += f"{rank_emoji} {user_mention} - {total_amount} ⭐"
            if purchase_count > 1:
                buyers_text += f" ({purchase_count} purchases)"
            buyers_text += "\n"
        buyers_text += f"\n🌸 <i>Total buyers: {len(purchases)}</i>"

        await update.message.reply_text(
            buyers_text,
            parse_mode=ParseMode.HTML,
            disable_web_page_preview=True
        )
        log_with_user_info("INFO", f"✅ Buyers list sent with {len(purchases)} buyers", user_info)

    except Exception as e:
        user_info = extract_user_info(update.message)
        log_with_user_info("ERROR", f"❌ Error in buyers command: {e}", user_info)
        await update.message.reply_text("❌ Something went wrong getting the buyers list. Try again later! 🔧")
