import asyncio
from typing import Optional, Dict, Any
from PIL import Image
import io

from google import genai
from google.genai.types import Part

from Sakura.Core.config import AI_MODEL, GEMINI_API_KEY
from Sakura.Core.logging import logger
from Sakura.Core.helpers import log_action, get_fallback, get_error
from Sakura.Database.conversation import get_history
from Sakura.Chat.prompts import SAKURA_PROMPT
from Sakura import state

def init_client():
    """Initialize Google GenAI client for chat."""
    if not GEMINI_API_KEY:
        logger.warning("⚠️ No Gemini API key found, chat functionality will be disabled.")
        return

    logger.info("🫡 Initializing Google GenAI API key.")
    try:
        genai.configure(api_key=GEMINI_API_KEY)
        # As per the latest docs, we initialize the client instance
        state.gemini_client = genai.Client()
        logger.info("✅ Chat client (Google GenAI) initialized successfully")
    except Exception as e:
        logger.error(f"❌ Failed to initialize chat client: {e}")

async def get_response(
    user_message: str,
    user_id: int,
    user_info: Dict[str, Any] = None,
    image_bytes: Optional[bytes] = None
) -> str:
    """Get response from Google GenAI API."""
    if user_info:
        log_action("DEBUG", f"🤖 Getting AI response for message: '{user_message[:50]}...'", user_info)

    if not state.gemini_client:
        if user_info:
            log_action("WARNING", "❌ Chat client not available, using fallback response", user_info)
        return get_fallback()

    try:
        model_to_use = AI_MODEL
        if user_info:
            log_action("INFO", f"🧠 Using model: {model_to_use}", user_info)

        # Build conversation history
        db_history = await get_history(user_id)

        # Start with the system prompt, then add history
        gemini_history = [{'role': 'user', 'parts': [SAKURA_PROMPT]}, {'role': 'model', 'parts': ["Understood. I will now act as Sakura."]}]
        for msg in db_history:
            role = 'model' if msg['role'] == 'assistant' else 'user'
            gemini_history.append({'role': role, 'parts': [msg['content']]})

        # Prepare current message parts (text and/or image)
        current_message_parts = []
        if user_message:
            current_message_parts.append(user_message)

        if image_bytes:
            try:
                img = Image.open(io.BytesIO(image_bytes))
                current_message_parts.append(img)
            except Exception as e:
                logger.error(f"🖼️ Failed to process image: {e}")
                return "I'm sorry, I had trouble understanding that image. Please try another one."

        if not current_message_parts:
            if user_info:
                log_action("WARNING", "🤷‍♀️ No message content to send to AI.", user_info)
            return get_fallback()

        # Add the current message to the end of the history
        gemini_history.append({'role': 'user', 'parts': current_message_parts})

        logger.debug("Sending request to Google GenAI API.")

        # The SDK's generate_content is synchronous, so we run it in a thread
        # to avoid blocking the asyncio event loop.
        response = await asyncio.to_thread(
            state.gemini_client.models.generate_content,
            model_name=model_to_use,
            contents=gemini_history,
            generation_config={
                "temperature": 0.1,
                "top_p": 0.1
            }
        )
        logger.debug("Received response from Google GenAI API.")

        ai_response = response.text.strip() if response.text else get_fallback()

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