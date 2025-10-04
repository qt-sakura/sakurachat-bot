import base64
from typing import Optional, Dict

from openai import AsyncOpenAI

from Sakura.Core.config import OWNER_ID, MODEL, OPENROUTER_API_KEYS
from Sakura.Core.logging import logger
from Sakura.Core.helpers import log_action, get_fallback, get_error
from Sakura.Database.conversation import get_history
from Sakura.Chat.prompts import SAKURA_PROMPT
from Sakura import state

def initialize_chat_client():
    """Initialize OpenRouter clients for chat."""
    if not OPENROUTER_API_KEYS:
        logger.warning("⚠️ No OpenRouter API keys found, chat functionality will be disabled.")
        return

    for api_key in OPENROUTER_API_KEYS:
        try:
            client = AsyncOpenAI(
                base_url="https://openrouter.ai/api/v1",
                api_key=api_key,
            )
            state.openrouter_clients.append(client)
        except Exception as e:
            logger.error(f"❌ Failed to initialize chat client for a key: {e}")

    if state.openrouter_clients:
        logger.info(f"✅ {len(state.openrouter_clients)} chat client(s) (OpenRouter) initialized successfully")
    else:
        logger.error("❌ No chat clients could be initialized.")

async def chat_response(
    user_message: str,
    user_id: int,
    user_info: Dict[str, any] = None,
    image_bytes: Optional[bytes] = None
) -> str:
    """Get response from OpenRouter API."""
    if user_info:
        log_action("DEBUG", f"🤖 Getting AI response for message: '{user_message[:50]}...'", user_info)

    if not state.openrouter_clients:
        if user_info:
            log_action("WARNING", "❌ Chat clients not available, using fallback response", user_info)
        return get_fallback()

    try:
        # Round-robin key selection
        client_to_use = state.openrouter_clients[state.current_key_index]
        state.current_key_index = (state.current_key_index + 1) % len(state.openrouter_clients)

        is_owner = (user_id == OWNER_ID)
        model_to_use = MODEL
        prompt_to_use = SAKURA_PROMPT

        if user_info:
            log_action("INFO", f"🧠 Using model: {model_to_use}", user_info)

        history = await get_history(user_id)
        messages = [{"role": "system", "content": prompt_to_use}]
        messages.extend(history)

        current_message_content = []
        if user_message:
            current_message_content.append({"type": "text", "text": user_message})

        if image_bytes:
            image_data = base64.b64encode(image_bytes).decode('utf-8')
            current_message_content.append({
                "type": "image_url",
                "image_url": {
                    "url": f"data:image/jpeg;base64,{image_data}"
                }
            })

        if not current_message_content:
            if user_info:
                log_action("WARNING", "🤷‍♀️ No message content to send to AI.", user_info)
            return get_fallback()

        messages.append({"role": "user", "content": current_message_content})

        completion = await client_to_use.chat.completions.create(
            extra_headers={
                "HTTP-Referer": "https://t.me/SakuraHarunoBot",
                "X-Title": "Sakura Bot",
            },
            model=model_to_use,
            messages=messages
        )

        ai_response = completion.choices[0].message.content.strip() if completion.choices[0].message.content else get_fallback()

        if user_info:
            log_action("INFO", f"✅ AI response generated: '{ai_response[:50]}...'", user_info)

        return ai_response

    except Exception as e:
        if user_info:
            log_action("ERROR", f"❌ AI API error: {e}", user_info)
        else:
            logger.error(f"AI API error: {e}")
        return get_error()