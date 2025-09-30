from typing import Optional, Dict

from Sakura.AI.gemini import analyze_image, gemini_response
from Sakura.AI.openrouter import openrouter_response
from Sakura.Core.config import OWNER_ID
from Sakura.Core.helpers import log_action, get_error
from Sakura.Storage.conversation import add_history
from Sakura import state


async def get_response(user_message: str, user_name: str = "", user_info: Dict[str, any] = None, user_id: int = None, image_bytes: Optional[bytes] = None) -> str:
    """Gets a response from the AI based on the user type."""
    response = None

    # Route to OpenRouter for the owner
    if user_id == OWNER_ID and state.openrouter_client:
        log_action("INFO", "🤖 Routing owner to OpenRouter API...", user_info)
        try:
            response = await openrouter_response(user_message, user_name, user_info, user_id, image_bytes)
            if response:
                log_action("INFO", f"✅ OpenRouter response generated: '{response[:50]}...'", user_info)
        except Exception as e:
            log_action("ERROR", f"❌ OpenRouter API error for owner: {e}", user_info)
    # Route to Gemini for everyone else
    else:
        log_action("INFO", "🤖 Routing user to Gemini API", user_info)
        try:
            if image_bytes:
                response = await analyze_image(image_bytes, user_message, user_name, user_info, user_id)
            else:
                response = await gemini_response(user_message, user_name, user_info, user_id)
            if response:
                log_action("INFO", f"✅ Gemini response generated: '{response[:50]}...'", user_info)
        except Exception as e:
            log_action("ERROR", f"❌ Gemini API error for user: {e}", user_info)

    if response and user_id:
        history_user_message = user_message
        if image_bytes:
            history_user_message = f"[Image: {user_message}]" if user_message else "[Image sent]"

        await add_history(user_id, history_user_message, is_user=True)
        await add_history(user_id, response, is_user=False)

    return response if response else get_error()