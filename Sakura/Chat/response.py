from typing import Optional, Dict

from Sakura.Chat.chat import chat_response
from Sakura.Core.helpers import get_error, log_action
from Sakura.Storage.conversation import add_history


async def get_response(
    user_message: str,
    user_name: str,
    user_info: Dict[str, any],
    user_id: int,
    image_bytes: Optional[bytes] = None
) -> str:
    """Gets a response from the AI."""
    try:
        response = await chat_response(user_message, user_id, user_info, image_bytes)

        if response:
            history_user_message = user_message
            if image_bytes:
                history_user_message = f"[Image: {user_message}]" if user_message else "[Image sent]"

            await add_history(user_id, history_user_message, is_user=True)
            await add_history(user_id, response, is_user=False)
            return response
        else:
            return get_error()

    except Exception as e:
        log_action("ERROR", f"❌ Error getting AI response: {e}", user_info)
        return get_error()