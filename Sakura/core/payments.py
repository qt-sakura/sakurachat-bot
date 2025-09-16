import random
import asyncio
import aiohttp
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes

from ..utils.messages import log_with_user_info, extract_user_info
from ..database.purchases import save_purchase_to_database_async
from ..core.state import payment_storage
from ..config.constants import (
    PAYMENT_STICKERS,
    THANK_YOU_MESSAGES,
    REFUND_MESSAGES,
    EFFECTS,
)
from ..config.settings import BOT_TOKEN


async def precheckout_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Answer the PreCheckoutQuery."""
    query = update.pre_checkout_query
    await context.bot.answer_pre_checkout_query(
        pre_checkout_query_id=query.id,
        ok=True
    )
    user_info = extract_user_info(update.message)
    log_with_user_info("INFO", f"💳 Pre-checkout approved for user {query.from_user.id}", user_info)


async def successful_payment_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle successful payment - refund if 10 stars or less, otherwise process normally."""
    payment = update.message.successful_payment
    user_id = update.message.from_user.id
    amount = payment.total_amount
    user_info = extract_user_info(update.message)

    log_with_user_info("INFO", f"💰 Payment received for {amount} stars", user_info)

    if amount > 10:
        save_purchase_to_database_async(
            user_id=user_id,
            username=user_info.get("username"),
            first_name=user_info.get("first_name"),
            last_name=user_info.get("last_name"),
            amount=amount,
            charge_id=payment.telegram_payment_charge_id
        )

    if amount <= 10:
        log_with_user_info("INFO", f"🔄 Refunding payment of {amount} stars (kindness gesture)", user_info)
        await asyncio.sleep(4)
        payment_storage[payment.telegram_payment_charge_id] = {
            'user_id': user_id,
            'amount': amount,
            'charge_id': payment.telegram_payment_charge_id
        }
        try:
            await context.bot.refund_star_payment(
                user_id=user_id,
                telegram_payment_charge_id=payment.telegram_payment_charge_id
            )
            keyboard = [[InlineKeyboardButton("Buy flowers again 🌸", callback_data="get_flowers_again")]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            refund_msg = random.choice(REFUND_MESSAGES)
            if update.message.chat.type == "private":
                try:
                    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
                    payload = {
                        'chat_id': update.message.chat.id,
                        'text': refund_msg,
                        'message_effect_id': random.choice(EFFECTS),
                        'parse_mode': 'HTML',
                        'reply_markup': reply_markup.to_json()
                    }
                    async with aiohttp.ClientSession() as session:
                        async with session.post(url, json=payload) as response:
                            result = await response.json()
                            if not result.get('ok'):
                                await update.message.reply_text(refund_msg, reply_markup=reply_markup)
                except Exception:
                    await update.message.reply_text(refund_msg, reply_markup=reply_markup)
            else:
                await update.message.reply_text(refund_msg, reply_markup=reply_markup)
            log_with_user_info("INFO", "✅ Refund completed successfully", user_info)
        except Exception as e:
            log_with_user_info("ERROR", f"❌ Error refunding payment: {e}", user_info)
            await update.message.reply_text("❌ Sorry, there was an issue processing your refund. Please contact support.")
    else:
        log_with_user_info("INFO", f"✅ Processing payment of {amount} stars (no refund)", user_info)
        await asyncio.sleep(4)
        sticker_id = random.choice(PAYMENT_STICKERS)
        await context.bot.send_sticker(chat_id=update.message.chat.id, sticker=sticker_id)
        await asyncio.sleep(4)
        keyboard = [[InlineKeyboardButton("Buy flowers again 🌸", callback_data="get_flowers_again")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        success_msg = random.choice(THANK_YOU_MESSAGES)
        if update.message.chat.type == "private":
            try:
                url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
                payload = {
                    'chat_id': update.message.chat.id,
                    'text': success_msg,
                    'message_effect_id': random.choice(EFFECTS),
                    'parse_mode': 'HTML',
                    'reply_markup': reply_markup.to_json()
                }
                async with aiohttp.ClientSession() as session:
                    async with session.post(url, json=payload) as response:
                        result = await response.json()
                        if not result.get('ok'):
                            await update.message.reply_text(success_msg, reply_markup=reply_markup)
            except Exception:
                await update.message.reply_text(success_msg, reply_markup=reply_markup)
        else:
            await update.message.reply_text(success_msg, reply_markup=reply_markup)
        log_with_user_info("INFO", "✅ Payment processed successfully", user_info)
