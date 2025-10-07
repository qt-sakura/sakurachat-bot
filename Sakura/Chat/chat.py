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
        # The API key is typically set as an environment variable (GOOGLE_API_KEY)
        # which google-genai reads automatically.
        # We are setting it here from our config for explicit configuration.
        state.genai_client = genai.Client(api_key=GEMINI_API_KEY)
        logger.info("✅ Chat client (Google GenAI) initialized successfully")
    except Exception as e:
        logger.error(f"❌ Failed to initialize chat client: {e}")

async def get_response(
    user_message: str,
    user_id: int,
    user_info: Dict[str, any] = None,
    image_bytes: Optional[bytes] = None
) -> str:
    """Get response from Google GenAI API."""
    if user_info:
        log_action("DEBUG", f"🤖 Getting AI response for message: '{user_message[:50]}...'", user_info)

    if not state.genai_client:
        if user_info:
            log_action("WARNING", "❌ Chat client not available, using fallback response", user_info)
        return get_fallback()

    try:
        model_to_use = AI_MODEL
        prompt_to_use = SAKURA_PROMPT

        if user_info:
            log_action("INFO", f"🧠 Using model: {model_to_use}", user_info)

        history = await get_history(user_id)

        # The google-genai library doesn't have the same concept of chat history as openai or others.
        # We will build a single prompt including the history.
        full_prompt = [prompt_to_use]
        for message in history:
            full_prompt.append(f"{message['role']}: {message['content']}")

        content = [user_message] if user_message else []
        if image_bytes:
            try:
                img = Image.open(io.BytesIO(image_bytes))
                content.append(img)
            except Exception as e:
                logger.error(f"Failed to process image: {e}")
                return get_error()

        if not content:
            if user_info:
                log_action("WARNING", "🤷‍♀️ No message content to send to AI.", user_info)
            return get_fallback()

        full_prompt.append(f"user: {' '.join(str(c) for c in content if isinstance(c, str))}")

        # Add images to content for the API
        final_content = []
        if user_message:
            final_content.append(user_message)
        if image_bytes:
            img = Image.open(io.BytesIO(image_bytes))
            final_content.append(img)


        logger.debug("Sending request to Google GenAI API.")

        completion = await asyncio.to_thread(
            state.genai_client.models.generate_content,
            model=model_to_use,
            contents=final_content
        )
        logger.debug("Received response from Google GenAI API.")

        ai_response = completion.text.strip() if completion.text else get_fallback()

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