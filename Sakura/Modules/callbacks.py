from pyrogram import Client, filters
from pyrogram.types import CallbackQuery
from pyrogram.enums import ParseMode, ChatMemberStatus
from pyrogram.errors import BadRequest, Forbidden
from Sakura.Core.helpers import fetch_user, log_action, get_mention
from Sakura.Modules.keyboards import info_menu, help_menu, broadcast_menu
from Sakura.Modules.messages import START_MESSAGES, HELP_MESSAGES, BROADCAST_MESSAGES
from Sakura.Modules.typing import send_typing
from Sakura.Chat.response import get_response
from Sakura.Modules.effects import send_effect
from Sakura.Services.payments import send_invoice
from Sakura import state
from Sakura.Core.config import OWNER_ID

@Client.on_callback_query(filters.regex(r"^start_"))
async def start_callback_handler(client: Client, callback_query: CallbackQuery) -> None:
    """Handle start command inline button callbacks"""
    if callback_query.message.chat.type in ['group', 'supergroup']:
        try:
            chat_member = await client.get_chat_member(callback_query.message.chat.id, client.me.id)
            if chat_member.status in [ChatMemberStatus.LEFT, ChatMemberStatus.BANNED]:
                await callback_query.answer("Add me first, my soul might be here but my body not! 🌸", show_alert=True)
                return
        except (BadRequest, Forbidden):
            await callback_query.answer("Add me first, my soul might be here but my body not! 🌸", show_alert=True)
            return

    try:
        user_info = fetch_user(callback_query.message)
        log_action("INFO", f"🌸 Start callback received: {callback_query.data}", user_info)
        user_mention = get_mention(callback_query.from_user)

        if callback_query.data == "start_info":
            await callback_query.answer(START_MESSAGES["callback_answers"]["info"], show_alert=False)
            keyboard = info_menu(client.me.username)
            caption = START_MESSAGES["info_caption"].format(user_mention=user_mention)
            await callback_query.edit_message_caption(caption=caption, reply_markup=keyboard, parse_mode=ParseMode.HTML)
            log_action("INFO", "✅ Start info buttons shown", user_info)

        elif callback_query.data == "start_hi":
            await callback_query.answer(START_MESSAGES["callback_answers"]["hi"], show_alert=False)
            await send_typing(client, callback_query.message.chat.id, user_info)
            user_name = callback_query.from_user.first_name or ""
            hi_response = await get_response("Hi sakura", user_name, user_info, callback_query.from_user.id)

            if callback_query.message.chat.type == "private":
                await send_effect(client, callback_query.message.chat.id, hi_response)
            else:
                await client.send_message(chat_id=callback_query.message.chat.id, text=hi_response)
            log_action("INFO", "✅ Hi message sent from Sakura", user_info)

    except Exception as e:
        user_info = fetch_user(callback_query.message) if callback_query.message else {}
        log_action("ERROR", f"❌ Error in start callback: {e}", user_info)
        try:
            await callback_query.answer("Something went wrong 😔", show_alert=True)
        except:
            pass

@Client.on_callback_query(filters.regex(r"^help_"))
async def help_callback_handler(client: Client, callback_query: CallbackQuery) -> None:
    """Handle help expand/minimize callbacks"""
    if callback_query.message.chat.type in ['group', 'supergroup']:
        try:
            chat_member = await client.get_chat_member(callback_query.message.chat.id, client.me.id)
            if chat_member.status in [ChatMemberStatus.LEFT, ChatMemberStatus.BANNED]:
                await callback_query.answer("Add me first, my soul might be here but my body not! 🌸", show_alert=True)
                return
        except (BadRequest, Forbidden):
            await callback_query.answer("Add me first, my soul might be here but my body not! 🌸", show_alert=True)
            return

    try:
        user_info = fetch_user(callback_query.message)
        log_action("INFO", f"🔄 Help callback received: {callback_query.data}", user_info)
        user_mention = get_mention(callback_query.from_user)

        expanded = callback_query.data == "help_expand"
        answer_text = HELP_MESSAGES["callback_answers"]["expand" if expanded else "minimize"]
        await callback_query.answer(answer_text, show_alert=False)

        keyboard = help_menu(expanded=expanded)
        caption = HELP_MESSAGES["expanded" if expanded else "minimal"].format(user_mention=user_mention)

        await callback_query.edit_message_caption(caption=caption, reply_markup=keyboard, parse_mode=ParseMode.HTML)
        log_action("INFO", f"✅ Help message {'expanded' if expanded else 'minimized'}", user_info)

    except Exception as e:
        user_info = fetch_user(callback_query.message) if callback_query.message else {}
        log_action("ERROR", f"❌ Error editing help message: {e}", user_info)
        try:
            await callback_query.answer("Something went wrong 😔", show_alert=True)
        except:
            pass

@Client.on_callback_query(filters.regex(r"^bc_|^get_flowers_again$"))
async def broadcast_callback_handler(client: Client, callback_query: CallbackQuery) -> None:
    """Handle broadcast target selection and get flowers again button"""
    if callback_query.message.chat.type in ['group', 'supergroup']:
        try:
            chat_member = await client.get_chat_member(callback_query.message.chat.id, client.me.id)
            if chat_member.status in [ChatMemberStatus.LEFT, ChatMemberStatus.BANNED]:
                await callback_query.answer("Add me first, my soul might be here but my body not! 🌸", show_alert=True)
                return
        except (BadRequest, Forbidden):
            await callback_query.answer("Add me first, my soul might be here but my body not! 🌸", show_alert=True)
            return

    user_info = fetch_user(callback_query.message)

    if callback_query.data == "get_flowers_again":
        log_action("INFO", "🌸 'Buy flowers again' button clicked", user_info)
        await callback_query.answer("🌸 Getting more flowers for you!", show_alert=False)
        await send_invoice(client, callback_query.message.chat.id, user_info, 50)
        return

    if callback_query.from_user.id != OWNER_ID:
        log_action("WARNING", "⚠️ Non-owner attempted broadcast callback", user_info)
        await callback_query.answer("You're not authorized to use this 🚫", show_alert=True)
        return

    log_action("INFO", f"🎯 Broadcast target selected: {callback_query.data}", user_info)

    if callback_query.data == "bc_users":
        await callback_query.answer(BROADCAST_MESSAGES["callback_answers"]["users"], show_alert=False)
        state.broadcast_mode[OWNER_ID] = "users"
        await callback_query.edit_message_text(
            BROADCAST_MESSAGES["ready_users"].format(count=len(state.user_ids)),
            parse_mode=ParseMode.HTML
        )
        log_action("INFO", f"✅ Ready to broadcast to {len(state.user_ids)} users", user_info)

    elif callback_query.data == "bc_groups":
        await callback_query.answer(BROADCAST_MESSAGES["callback_answers"]["groups"], show_alert=False)
        state.broadcast_mode[OWNER_ID] = "groups"
        await callback_query.edit_message_text(
            BROADCAST_MESSAGES["ready_groups"].format(count=len(state.group_ids)),
            parse_mode=ParseMode.HTML
        )
        log_action("INFO", f"✅ Ready to broadcast to {len(state.group_ids)} groups", user_info)

@Client.on_callback_query(filters.regex(r"^refresh_stats$"))
async def stats_refresh_handler(client: Client, callback_query: CallbackQuery) -> None:
    """Handle stats refresh button callback"""
    if callback_query.message.chat.type in ['group', 'supergroup']:
        try:
            chat_member = await client.get_chat_member(callback_query.message.chat.id, client.me.id)
            if chat_member.status in [ChatMemberStatus.LEFT, ChatMemberStatus.BANNED]:
                await callback_query.answer("Add me first, my soul might be here but my body not! 🌸", show_alert=True)
                return
        except (BadRequest, Forbidden):
            await callback_query.answer("Add me first, my soul might be here but my body not! 🌸", show_alert=True)
            return

    try:
        user_info = fetch_user(callback_query.message)
        if callback_query.from_user.id != OWNER_ID:
            log_action("WARNING", "⚠️ Non-owner attempted stats refresh", user_info)
            await callback_query.answer("You're not authorized to use this 🚫", show_alert=True)
            return

        log_action("INFO", "🔄 Stats refresh callback received from owner", user_info)
        await callback_query.answer("🔄 Refreshing statistics...", show_alert=False)

        from Sakura.Services.stats import send_stats
        stats_message, reply_markup = await send_stats(callback_query.message.chat.id, client, is_refresh=True)

        await callback_query.edit_message_text(
            text=stats_message,
            reply_markup=reply_markup,
            disable_web_page_preview=True,
            parse_mode=ParseMode.HTML
        )
        log_action("INFO", "✅ Stats refreshed successfully", user_info)

    except Exception as e:
        user_info = fetch_user(callback_query.message) if callback_query.message else {}
        log_action("ERROR", f"❌ Error refreshing stats: {e}", user_info)
        try:
            await callback_query.answer("❌ Error refreshing statistics!", show_alert=True)
        except:
            pass