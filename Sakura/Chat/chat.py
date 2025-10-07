import asyncio
import io
from typing import Optional, Dict
from PIL import Image

from google import genai
from Sakura.Core.config import AI_MODEL, GEMINI_API_KEY
from Sakura.Core.logging import logger
from Sakura.Core.helpers import log_action, get_fallback, get_error
from Sakura.Database.conversation import get_history
from Sakura.Chat.prompts import SAKURA_PROMPT
from Sakura import state

def init_client():
    """Initialize Google GenAI client for chat."""
    if not GEMINI_API_KEY:
        logger.warning("⚠️ No Google GenAI API key found, chat functionality will be disabled.")
        return

    logger.info("🫡 Initializing Google GenAI API key.")
    try:
        genai.configure(api_key=GEMINI_API_KEY)
        model_name = AI_MODEL
        # Set up the model with the system prompt
        state.genai_model = genai.GenerativeModel(
            model_name,
            system_instruction=SAKURA_PROMPT
        )
        logger.info(f"✅ Chat client (Google GenAI, model: {model_name}) initialized successfully")
    except Exception as e:
        logger.error(f"❌ Failed to initialize chat client: {e}")


async def get_response(
    user_message: str,
    user_id: int,
    user_info: Dict[str, any] = None,
    image_bytes: Optional[bytes] = None,
) -> str:
    """Get response from Google GenAI API."""
    if user_info:
        log_action(
            "DEBUG", f"🤖 Getting AI response for message: '{user_message[:50]}...'", user_info
        )

    if not hasattr(state, "genai_model"):
        if user_info:
            log_action(
                "WARNING", "❌ Chat client not available, using fallback response", user_info
            )
        return get_fallback()

    try:
        if user_info:
            log_action("INFO", f"🧠 Using model: {AI_MODEL}", user_info)

        history = await get_history(user_id)

        # Build chat history for the API
        chat_history = []
        for message in history:
            # The role 'model' is used for the assistant's responses.
            role = "model" if message["role"] == "assistant" else message["role"]
            chat_history.append({"role": role, "parts": [message["content"]]})

        # Start a chat session with the history
        chat = state.genai_model.start_chat(history=chat_history)

        # Prepare content to send
        content_to_send = []
        if user_message:
            content_to_send.append(user_message)
        if image_bytes:
            try:
                img = Image.open(io.BytesIO(image_bytes))
                content_to_send.append(img)
            except Exception as e:
                logger.error(f"Failed to process image: {e}")
                return get_error()

        if not content_to_send:
            if user_info:
                log_action("WARNING", "🤷‍♀️ No message content to send to AI.", user_info)
            return get_fallback()

        logger.debug("Sending request to Google GenAI API.")

        completion = await chat.send_message_async(content_to_send)

        logger.debug("Received response from Google GenAI API.")

        ai_response = completion.text.strip() if completion.text else get_fallback()

        if user_info:
            log_action(
                "INFO", f"✅ AI response generated: '{ai_response[:50]}...'", user_info
            )

        return ai_response

    except Exception as e:
        error_message = f"❌ AI API error: {e}"
        if user_info:
            log_action("ERROR", error_message, user_info)
        else:
            logger.error(error_message)
        return get_error()