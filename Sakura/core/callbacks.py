import random
from telegram import Update, ChatMember, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from telegram.constants import ParseMode
from telegram.error import BadRequest, Forbidden

from ..utils.messages import log_with_user_info, extract_user_info, get_user_mention
from ..utils.actions import send_typing_action
from ..utils.keyboards import (
    create_info_start_keyboard,
    get_info_start_caption,
    create_help_keyboard,
    get_help_text,
)
from ..database.cache import get_help_expanded_state, update_help_expanded_state
from ..utils.helpers import send_stats_message
from ..core.ai import get_gemini_response
from ..core.effects import send_with_effect
from ..core.state import broadcast_mode, user_ids, group_ids
from ..config.settings import OWNER_ID
from ..config.constants import START_MESSAGES, HELP_MESSAGES, BROADCAST_MESSAGES, INVOICE_DESCRIPTIONS


async def start_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle start command inline button callbacks"""
    query = update.callback_query
    if query.message.chat.type in ['group', 'supergroup']:
        try:
            chat_member = await context.bot.get_chat_member(query.message.chat.id, context.bot.id)
            if chat_member.status in [ChatMember.LEFT, ChatMember.BANNED]:
                await query.answer("Add me first, my soul might be here but my body not! 🌸", show_alert=True)
                return
        except (BadRequest, Forbidden):
            await query.answer("Add me first, my soul might be here but my body not! 🌸", show_alert=True)
            return

    try:
        query = update.callback_query
        user_info = extract_user_info(query.message)
        log_with_user_info("INFO", f"🌸 Start callback received: {query.data}", user_info)

        user_mention = get_user_mention(update.effective_user)

        if query.data == "start_info":
            await query.answer(START_MESSAGES["callback_answers"]["info"], show_alert=False)
            keyboard = create_info_start_keyboard(context.bot.username)
            caption = get_info_start_caption(user_mention)
            await query.edit_message_caption(
                caption=caption,
                parse_mode=ParseMode.HTML,
                reply_markup=keyboard
            )
            log_with_user_info("INFO", "✅ Start info buttons shown", user_info)

        elif query.data == "start_hi":
            await query.answer(START_MESSAGES["callback_answers"]["hi"], show_alert=False)
            await send_typing_action(context, update.effective_chat.id, user_info)
            user_name = update.effective_user.first_name or ""
            hi_response = await get_gemini_response("Hi sakura", user_name, user_info, update.effective_user.id)

            if update.effective_chat.type == "private":
                effect_sent = await send_with_effect(update.effective_chat.id, hi_response)
                if not effect_sent:
                    await context.bot.send_message(chat_id=update.effective_chat.id, text=hi_response)
            else:
                await context.bot.send_message(chat_id=update.effective_chat.id, text=hi_response)

            log_with_user_info("INFO", "✅ Hi message sent from Sakura", user_info)

    except Exception as e:
        user_info = extract_user_info(query.message) if query.message else {}
        log_with_user_info("ERROR", f"❌ Error in start callback: {e}", user_info)
        await query.answer("Something went wrong 😔", show_alert=True)

async def help_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle help expand/minimize callbacks"""
    query = update.callback_query
    if query.message.chat.type in ['group', 'supergroup']:
        try:
            chat_member = await context.bot.get_chat_member(query.message.chat.id, context.bot.id)
            if chat_member.status in [ChatMember.LEFT, ChatMember.BANNED]:
                await query.answer("Add me first, my soul might be here but my body not! 🌸", show_alert=True)
                return
        except (BadRequest, Forbidden):
            await query.answer("Add me first, my soul might be here but my body not! 🌸", show_alert=True)
            return

    try:
        user_info = extract_user_info(query.message)
        log_with_user_info("INFO", "🔄 Help expand/minimize callback received", user_info)

        callback_data = query.data
        user_id = int(callback_data.split('_')[2])

        if update.effective_user.id != user_id:
            await query.answer("This button isn't for you 💔", show_alert=True)
            return

        is_expanded = await get_help_expanded_state(user_id)
        await update_help_expanded_state(user_id, not is_expanded)

        if not is_expanded:
            await query.answer(HELP_MESSAGES["callback_answers"]["expand"], show_alert=False)
        else:
            await query.answer(HELP_MESSAGES["callback_answers"]["minimize"], show_alert=False)

        keyboard = create_help_keyboard(user_id, not is_expanded)
        user_mention = get_user_mention(update.effective_user)
        help_text = get_help_text(user_mention, not is_expanded)

        await query.edit_message_caption(
            caption=help_text,
            parse_mode=ParseMode.HTML,
            reply_markup=keyboard
        )
        log_with_user_info("INFO", f"✅ Help message {'expanded' if not is_expanded else 'minimized'}", user_info)

    except Exception as e:
        user_info = extract_user_info(query.message) if query.message else {}
        log_with_user_info("ERROR", f"❌ Error editing help message: {e}", user_info)
        await query.answer("Something went wrong 😔", show_alert=True)

async def broadcast_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle broadcast target selection and get flowers again button"""
    query = update.callback_query
    if query.message.chat.type in ['group', 'supergroup']:
        try:
            chat_member = await context.bot.get_chat_member(query.message.chat.id, context.bot.id)
            if chat_member.status in [ChatMember.LEFT, ChatMember.BANNED]:
                await query.answer("Add me first, my soul might be here but my body not! 🌸", show_alert=True)
                return
        except (BadRequest, Forbidden):
            await query.answer("Add me first, my soul might be here but my body not! 🌸", show_alert=True)
            return

    user_info = extract_user_info(query.message)

    if query.data == "get_flowers_again":
        log_with_user_info("INFO", "🌸 'Buy flowers again' button clicked", user_info)
        await query.answer("🌸 Getting more flowers for you!", show_alert=False)
        try:
            from telegram import LabeledPrice
            await context.bot.send_invoice(
                chat_id=query.message.chat.id,
                title="Flowers 🌸",
                description=random.choice(INVOICE_DESCRIPTIONS),
                payload=f"sakura_star_{query.from_user.id}",
                provider_token="",
                currency="XTR",
                prices=[LabeledPrice(label='✨ Sakura Star', amount=50)]
            )
            log_with_user_info("INFO", "✅ New invoice sent from 'Buy flowers again' button", user_info)
        except Exception as e:
            log_with_user_info("ERROR", f"❌ Error sending new invoice from button: {e}", user_info)
            await query.message.reply_text("❌ Oops! Something went wrong. Try using /buy command instead! 🔧")
        return

    if query.from_user.id != OWNER_ID:
        await query.answer("You're not authorized to use this 🚫", show_alert=True)
        return

    log_with_user_info("INFO", f"🎯 Broadcast target selected: {query.data}", user_info)

    if query.data == "bc_users":
        await query.answer(BROADCAST_MESSAGES["callback_answers"]["users"], show_alert=False)
        broadcast_mode[OWNER_ID] = "users"
        await query.edit_message_text(
            BROADCAST_MESSAGES["ready_users"].format(count=len(user_ids)),
            parse_mode=ParseMode.HTML
        )
        log_with_user_info("INFO", f"✅ Ready to broadcast to {len(user_ids)} users", user_info)
    elif query.data == "bc_groups":
        await query.answer(BROADCAST_MESSAGES["callback_answers"]["groups"], show_alert=False)
        broadcast_mode[OWNER_ID] = "groups"
        await query.edit_message_text(
            BROADCAST_MESSAGES["ready_groups"].format(count=len(group_ids)),
            parse_mode=ParseMode.HTML
        )
        log_with_user_info("INFO", f"✅ Ready to broadcast to {len(group_ids)} groups", user_info)

async def stats_refresh_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle stats refresh button callback"""
    query = update.callback_query
    if query.message.chat.type in ['group', 'supergroup']:
        try:
            chat_member = await context.bot.get_chat_member(query.message.chat.id, context.bot.id)
            if chat_member.status in [ChatMember.LEFT, ChatMember.BANNED]:
                await query.answer("Add me first, my soul might be here but my body not! 🌸", show_alert=True)
                return
        except (BadRequest, Forbidden):
            await query.answer("Add me first, my soul might be here but my body not! 🌸", show_alert=True)
            return

    try:
        user_info = extract_user_info(query.message)
        if query.from_user.id != OWNER_ID:
            await query.answer("You're not authorized to use this 🚫", show_alert=True)
            return

        log_with_user_info("INFO", "🔄 Stats refresh callback received from owner", user_info)
        await query.answer("🔄 Refreshing statistics...", show_alert=False)
        stats_message, reply_markup = await send_stats_message(query.message.chat.id, context, is_refresh=True)
        await query.edit_message_text(
            text=stats_message,
            parse_mode=ParseMode.HTML,
            reply_markup=reply_markup,
            disable_web_page_preview=True
        )
        log_with_user_info("INFO", "✅ Stats refreshed successfully", user_info)
    except Exception as e:
        user_info = extract_user_info(query.message) if query.message else {}
        log_with_user_info("ERROR", f"❌ Error refreshing stats: {e}", user_info)
        await query.answer("❌ Error refreshing statistics!", show_alert=True)
