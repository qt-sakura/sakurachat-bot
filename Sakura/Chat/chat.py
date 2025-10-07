import asyncio
import base64
from typing import Optional, Dict
from PIL import Image
import io

import google.generativeai as genai

from Sakura.Core.config import OWNER_ID, AI_MODEL, GEMINI_API_KEY
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
        state.gemini_client = genai.GenerativeModel(AI_MODEL)
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

    if not state.gemini_client:
        if user_info:
            log_action("WARNING", "❌ Chat client not available, using fallback response", user_info)
        return get_fallback()

    try:
        model_to_use = AI_MODEL

        if user_info:
            log_action("INFO", f"🧠 Using model: {model_to_use}", user_info)

        history = await get_history(user_id)

        # Start with the system prompt
        messages = [{"role": "system", "content": SAKURA_PROMPT}]

        # Add historical messages
        messages.extend(history)

        # Prepare content for the current user message
        content_parts = []
        if user_message:
            content_parts.append({"text": user_message})

        if image_bytes:
            try:
                img = Image.open(io.BytesIO(image_bytes))
                content_parts.append(img)
            except Exception as e:
                logger.error(f"🖼️ Failed to process image: {e}")
                return "I'm sorry, I had trouble understanding that image. Please try another one."

        if not content_parts:
            if user_info:
                log_action("WARNING", "🤷‍♀️ No message content to send to AI.", user_info)
            return get_fallback()

        messages.append({"role": "user", "parts": content_parts})

        # Convert to the format expected by the Gemini API
        generation_config = genai.types.GenerationConfig(
            temperature=0.1,
            top_p=0.1
        )

        logger.debug("Sending request to Google GenAI API.")

        # Reformat message history for gemini
        gemini_history = []
        for msg in messages:
            role = 'user' if msg['role'] == 'user' else 'model'

            # Handle different content structures
            if 'parts' in msg:
                content = msg['parts']
            elif 'content' in msg:
                content = msg['content']
            else:
                continue # Skip messages with no content

            gemini_history.append({'role': role, 'parts': content if isinstance(content, list) else [content]})


        completion = await state.gemini_client.generate_content_async(
            contents=gemini_history,
            generation_config=generation_config
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