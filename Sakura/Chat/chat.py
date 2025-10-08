import base64
from typing import Optional, Dict

from google import genai

from Sakura.Core.config import GEMINI_API_KEY, AI_MODEL
from Sakura.Core.logging import logger
from Sakura.Core.helpers import log_action, get_fallback, get_error
from Sakura.Database.conversation import get_history, update_history
from Sakura.Chat.prompts import SAKURA_PROMPT
from Sakura import state

def init_client():
    """Initialize Google Gemini client for chat."""
    if not GEMINI_API_KEY:
        logger.warning("⚠️ No Gemini API key found, chat functionality will be disabled.")
        return

    logger.info("🫡 Initializing Google GenAI API key.")
    try:
        state.gemini_client = genai.Client(api_key=GEMINI_API_KEY)
        logger.info("✅ Chat client (Gemini) initialized successfully")
    except Exception as e:
        logger.error(f"❌ Failed to initialize chat client: {e}")

async def get_response(
    user_message: str,
    user_id: int,
    user_info: Dict[str, any],
    image_bytes: Optional[bytes] = None
) -> str:
    """Get response from Gemini API."""
    user_name = user_info.get("first_name", "User")
    log_action("DEBUG", f"🤖 Getting AI response for '{user_message[:50]}...'", user_info)

    if not state.gemini_client:
        log_action("WARNING", "❌ Chat client not available, using fallback response", user_info)
        return get_fallback()

    try:
        history = await get_history(user_id)
        context = ""
        if history:
            history_text = [f"{'User' if msg['role'] == 'user' else 'Sakura'}: {msg['content']}" for msg in history]
            context = f"\n\nPrevious conversation:\n" + "\n".join(history_text)

        final_contents = []
        if image_bytes:
            prompt = f"{SAKURA_PROMPT}\n\nUser name: {user_name}{context}\n\nUser sent an image. Caption: '{user_message or 'No caption'}'\n\nDescribe what you see:\n\nSakura's response:"
            image_data = base64.b64encode(image_bytes).decode('utf-8')
            final_contents.extend([prompt, {"inline_data": {"mime_type": "image/jpeg", "data": image_data}}])
        else:
            prompt = f"{SAKURA_PROMPT}\n\nUser name: {user_name}{context}\nCurrent message: {user_message}\n\nSakura's response:"
            final_contents.append(prompt)

        response = await state.gemini_client.aio.models.generate_content(
            model=AI_MODEL,
            contents=final_contents
        )

        ai_response = response.text.strip() if response.text else get_fallback()

        await update_history(user_id, user_message, ai_response)

        log_action("INFO", f"✅ AI response generated: '{ai_response[:50]}...'", user_info)
        return ai_response

    except Exception as e:
        error_message = f"❌ AI API error: {e}"
        log_action("ERROR", error_message, user_info)
        return get_error()