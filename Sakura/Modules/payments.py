import random
import asyncio
from pyrogram import Client, filters
from pyrogram.types import Message, LabeledPrice, InlineKeyboardButton, InlineKeyboardMarkup, PreCheckoutQuery, LinkPreviewOptions
from pyrogram.enums import ParseMode, ChatType
from Sakura.Core.helpers import fetch_user, log_action, get_error
from Sakura.Core.logging import logger
from Sakura.Services.tracking import track_user
from Sakura.Modules.effects import animate_reaction, add_reaction, send_effect
from Sakura.Modules.reactions import EMOJI_REACT
from Sakura.Modules.typing import send_typing
from Sakura.Modules.messages import INVOICE_DESCRIPTIONS, THANK_YOU_MESSAGES, REFUND_MESSAGES
from Sakura.Database.database import save_purchase, get_purchases
from Sakura.Database.constants import PAYMENT_STICKERS
from Sakura import state

@Client.on_message(filters.command("meow"))
async def meow_command_handler(client: Client, message: Message) -> None:
    """Send an invoice for sakura flowers."""
    try:
        user_info = fetch_user(message)
        log_action("INFO", "🌸 /meow command received", user_info)
        await track_user(message, user_info)

        if EMOJI_REACT:
            try:
                random_emoji = random.choice(EMOJI_REACT)
                if message.chat.type == ChatType.PRIVATE:
                    await animate_reaction(message.chat.id, message.id, random_emoji)
                else:
                    await add_reaction(client, message, random_emoji, user_info)
            except Exception as e:
                log_action("WARNING", f"⚠️ Failed to add emoji reaction: {e}", user_info)

        await send_typing(client, message.chat.id, user_info)

        amount = 50
        if len(message.text.split()) > 1 and message.text.split()[1].isdigit():
            amount = int(message.text.split()[1])
            if amount > 100000:
                amount = 100000
            elif amount < 1:
                amount = 1

        await send_invoice(client, message.chat.id, user_info, amount)

    except Exception as e:
        user_info = fetch_user(message)
        log_action("ERROR", f"❌ Error sending invoice: {e}", user_info)
        await message.reply_text("❌ Oops! Something went wrong creating the invoice. Try again later! 🔧")

@Client.on_message(filters.command("fams"))
async def fams_command_handler(client: Client, message: Message) -> None:
    """Show all flower buyers with their donation amounts."""
    try:
        user_info = fetch_user(message)
        log_action("INFO", "💝 /fams command received", user_info)
        await track_user(message, user_info)

        if EMOJI_REACT:
            try:
                random_emoji = random.choice(EMOJI_REACT)
                if message.chat.type == ChatType.PRIVATE:
                    await animate_reaction(message.chat.id, message.id, random_emoji)
                else:
                    await add_reaction(client, message, random_emoji, user_info)
            except Exception as e:
                log_action("WARNING", f"⚠️ Failed to add emoji reaction: {e}", user_info)

        await send_typing(client, message.chat.id, user_info)
        purchases = await get_purchases()

        if not purchases:
            no_buyers_text = (
                "🌸 <b>Flower Buyers</b>\n\n"
                "No one has bought flowers yet! Be the first to support with /meow 💝"
            )
            if message.chat.type == ChatType.PRIVATE:
                await send_effect(message.chat.id, no_buyers_text)
            else:
                await message.reply_text(no_buyers_text, parse_mode=ParseMode.HTML)
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

        if message.chat.type == ChatType.PRIVATE:
            await send_effect(message.chat.id, buyers_text)
        else:
            await message.reply_text(buyers_text, parse_mode=ParseMode.HTML, link_preview_options=LinkPreviewOptions(is_disabled=True))

    except Exception as e:
        user_info = fetch_user(message)
        log_action("ERROR", f"❌ Error in buyers command: {e}", user_info)
        await message.reply_text(get_error())

async def send_invoice(client: Client, chat_id: int, user_info: dict, amount: int):
    """Sends a payment invoice."""
    try:
        await client.send_invoice(
            chat_id=chat_id,
            title="Flowers 🌸",
            description=random.choice(INVOICE_DESCRIPTIONS),
            payload=f"sakura_star_{user_info['user_id']}",
            provider_token="",  # provider_token is not needed for Stars
            currency="XTR",
            prices=[LabeledPrice(label='✨ Sakura Star', amount=amount)]
        )
        log_action("INFO", f"✅ Invoice sent for {amount} stars", user_info)
    except Exception as e:
        log_action("ERROR", f"❌ Error sending invoice: {e}", user_info)
        await client.send_message(chat_id, "❌ Oops! Something went wrong creating the invoice. Try again later! 🔧")

@Client.on_pre_checkout_query()
async def precheckout_query_handler(client: Client, query: PreCheckoutQuery) -> None:
    """Answer the PreCheckoutQuery."""
    await query.answer(ok=True)
    logger.info(f"💳 Pre-checkout approved for user {query.from_user.id}")

@Client.on_message(filters.successful_payment)
async def successful_payment_handler(client: Client, message: Message) -> None:
    """Handle successful payment - refund if 10 stars or less, otherwise process normally."""
    payment = message.successful_payment
    user_id = message.from_user.id
    amount = payment.total_amount
    user_info = fetch_user(message)

    log_action("INFO", f"💰 Payment received for {amount} stars", user_info)

    if amount > 10:
        await save_purchase(
            user_id=user_id,
            username=user_info.get("username"),
            first_name=user_info.get("first_name"),
            last_name=user_info.get("last_name"),
            amount=amount,
            charge_id=payment.telegram_charge_id
        )

    if amount <= 10:
        log_action("INFO", f"🔄 Refunding payment of {amount} stars (kindness gesture)", user_info)
        await asyncio.sleep(4)
        state.payment_storage[payment.telegram_charge_id] = {
            'user_id': user_id,
            'amount': amount,
            'charge_id': payment.telegram_charge_id
        }
        try:
            await client.refund_star_payment(
                user_id=user_id,
                telegram_payment_charge_id=payment.telegram_charge_id
            )
            keyboard = [[InlineKeyboardButton("Buy flowers again 🌸", callback_data="get_flowers_again")]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            refund_msg = random.choice(REFUND_MESSAGES)

            if message.chat.type == ChatType.PRIVATE:
                await send_effect(message.chat.id, refund_msg, reply_markup)
            else:
                await message.reply_text(refund_msg, reply_markup=reply_markup)
            log_action("INFO", "✅ Refund completed successfully", user_info)
        except Exception as e:
            log_action("ERROR", f"❌ Error refunding payment: {e}", user_info)
            await message.reply_text("❌ Sorry, there was an issue processing your refund. Please contact support.")
    else:
        log_action("INFO", f"✅ Processing payment of {amount} stars (no refund)", user_info)
        await asyncio.sleep(4)
        sticker_id = random.choice(PAYMENT_STICKERS)
        await client.send_sticker(chat_id=message.chat.id, sticker=sticker_id)
        await asyncio.sleep(4)
        keyboard = [[InlineKeyboardButton("Buy flowers again 🌸", callback_data="get_flowers_again")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        success_msg = random.choice(THANK_YOU_MESSAGES)

        if message.chat.type == ChatType.PRIVATE:
            await send_effect(message.chat.id, success_msg, reply_markup)
        else:
            await message.reply_text(success_msg, reply_markup=reply_markup)
        log_action("INFO", "✅ Payment processed successfully", user_info)