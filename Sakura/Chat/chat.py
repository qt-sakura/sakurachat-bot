import asyncio
import base64
from typing import Optional, Dict

from sambanova import SambaNova

from Sakura.Core.config import OWNER_ID, AI_MODEL, SAMBANOVA_API_KEY
from Sakura.Core.logging import logger
from Sakura.Core.helpers import log_action, get_fallback, get_error
from Sakura.Database.conversation import get_history
from Sakura.Chat.prompts import SAKURA_PROMPT
from Sakura import state

def init_client():
    """Initialize SambaNova client for chat."""
    if not SAMBANOVA_API_KEY:
        logger.warning("⚠️ No SambaNova API key found, chat functionality will be disabled.")
        return

    logger.info("🫡 Initializing SambaNova API key.")
    try:
        state.sambanova_client = SambaNova(
            api_key=SAMBANOVA_API_KEY,
            base_url="https://api.sambanova.ai/v1",
        )
        logger.info("✅ Chat client (SambaNova) initialized successfully")
    except Exception as e:
        logger.error(f"❌ Failed to initialize chat client: {e}")

async def get_response(
    user_message: str,
    user_id: int,
    user_info: Dict[str, any] = None,
    image_bytes: Optional[bytes] = None
) -> str:
    """Get response from SambaNova API."""
    if user_info:
        log_action("DEBUG", f"🤖 Getting AI response for message: '{user_message[:50]}...'", user_info)

    if not state.sambanova_client:
        if user_info:
            log_action("WARNING", "❌ Chat client not available, using fallback response", user_info)
        return get_fallback()

    try:
        model_to_use = AI_MODEL
        prompt_to_use = SAKURA_PROMPT

        if user_info:
            log_action("INFO", f"🧠 Using model: {model_to_use}", user_info)

        history = await get_history(user_id)
        messages = [{"role": "system", "content": prompt_to_use}]
        messages.extend(history)

        if image_bytes:
            # Multimodal message
            content = []
            if user_message:
                content.append({"type": "text", "text": user_message})

            image_data = base64.b64encode(image_bytes).decode('utf-8')
            content.append({
                "type": "image_url",
                "image_url": {
                    "url": f"data:image/jpeg;base64,{image_data}"
                }
            })
        else:
            # Text-only message
            content = user_message

        if not content:
            if user_info:
                log_action("WARNING", "🤷‍♀️ No message content to send to AI.", user_info)
            return get_fallback()

        messages.append({"role": "user", "content": content})

        logger.debug("Sending request to SambaNova API.")
        completion = await asyncio.to_thread(
            state.sambanova_client.chat.completions.create,
            model=model_to_use,
            messages=messages,
            temperature=0.1,
            top_p=0.1
        )
        logger.debug("Received response from SambaNova API.")

        ai_response = completion.choices[0].message.content.strip() if completion.choices[0].message.content else get_fallback()

        if user_info:
            log_action("INFO", f"✅ AI response generated: '{ai_response[:50]}...'", user_info)

        return ai_response

    except Exception as e:
        error_message = f"❌ AI API error: {e}"
        if user_info:
            log_action("ERROR", error_message, user_info)
        else:
            logger.error(error_message)
        return get_error()
