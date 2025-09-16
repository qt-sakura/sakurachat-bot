from telegram import InlineKeyboardMarkup, InlineKeyboardButton
from ..config.constants import START_MESSAGES, HELP_MESSAGES, BROADCAST_MESSAGES, UPDATE_LINK, SUPPORT_LINK
from ..database.users import user_ids
from ..database.groups import group_ids

def create_initial_start_keyboard() -> InlineKeyboardMarkup:
    """Create initial start keyboard with Info and Hi buttons"""
    keyboard = [
        [
            InlineKeyboardButton(START_MESSAGES["button_texts"]["info"], callback_data="start_info"),
            InlineKeyboardButton(START_MESSAGES["button_texts"]["hi"], callback_data="start_hi")
        ]
    ]
    return InlineKeyboardMarkup(keyboard)


def create_info_start_keyboard(bot_username: str) -> InlineKeyboardMarkup:
    """Create inline keyboard for start info (original start buttons)"""
    keyboard = [
        [
            InlineKeyboardButton(START_MESSAGES["button_texts"]["updates"], url=UPDATE_LINK),
            InlineKeyboardButton(START_MESSAGES["button_texts"]["support"], url=SUPPORT_LINK)
        ],
        [
            InlineKeyboardButton(START_MESSAGES["button_texts"]["add_to_group"],
                               url=f"https://t.me/{bot_username}?startgroup=true")
        ]
    ]
    return InlineKeyboardMarkup(keyboard)


def get_initial_start_caption(user_mention: str) -> str:
    """Get initial caption text for start command with user mention"""
    return START_MESSAGES["initial_caption"].format(user_mention=user_mention)


def get_info_start_caption(user_mention: str) -> str:
    """Get info caption text for start command with user mention"""
    return START_MESSAGES["info_caption"].format(user_mention=user_mention)


def create_help_keyboard(user_id: int, expanded: bool = False) -> InlineKeyboardMarkup:
    """Create help command keyboard"""
    if expanded:
        button_text = HELP_MESSAGES["button_texts"]["minimize"]
    else:
        button_text = HELP_MESSAGES["button_texts"]["expand"]

    keyboard = [[InlineKeyboardButton(button_text, callback_data=f"help_expand_{user_id}")]]
    return InlineKeyboardMarkup(keyboard)


def get_help_text(user_mention: str, expanded: bool = False) -> str:
    """Get help text based on expansion state with user mention"""
    if expanded:
        return HELP_MESSAGES["expanded"].format(user_mention=user_mention)
    else:
        return HELP_MESSAGES["minimal"].format(user_mention=user_mention)


def create_broadcast_keyboard() -> InlineKeyboardMarkup:
    """Create broadcast target selection keyboard"""
    keyboard = [
        [
            InlineKeyboardButton(
                BROADCAST_MESSAGES["button_texts"]["users"].format(count=len(user_ids)),
                callback_data="bc_users"
            ),
            InlineKeyboardButton(
                BROADCAST_MESSAGES["button_texts"]["groups"].format(count=len(group_ids)),
                callback_data="bc_groups"
            )
        ]
    ]
    return InlineKeyboardMarkup(keyboard)


def get_broadcast_text() -> str:
    """Get broadcast command text"""
    return BROADCAST_MESSAGES["select_target"].format(
        users_count=len(user_ids),
        groups_count=len(group_ids)
    )
