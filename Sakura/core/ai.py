import base64
import hashlib
import logging
from google import genai
from telegram import Update
from telegram.ext import ContextTypes

from ..config.settings import GEMINI_API_KEY
from ..config.prompts import SAKURA_PROMPT
from ..utils.helpers import get_fallback_response, get_error_response
from ..utils.messages import log_with_user_info
from ..core.memory import get_conversation_context, add_to_conversation_history
from ..database.cache import cache_get, cache_set
from ..utils.actions import send_typing_action

logger = logging.getLogger("SAKURA 🌸")
gemini_client = None

def initialize_gemini_client():
    """Initialize the Gemini client"""
    global gemini_client
    if not GEMINI_API_KEY:
        logger.error("❌ GEMINI_API_KEY not found in environment variables")
        return
    try:
        gemini_client = genai.Client(api_key=GEMINI_API_KEY)
        logger.info("✅ Gemini client initialized successfully")
    except Exception as e:
        logger.error(f"❌ Failed to initialize Gemini client: {e}")

async def get_gemini_response(user_message: str, user_name: str = "", user_info: dict = None, user_id: int = None) -> str:
    """Get response from Gemini API with conversation context and caching"""
    if user_info:
        log_with_user_info("DEBUG", f"🤖 Getting Gemini response for message: '{user_message[:50]}...'", user_info)

    if not gemini_client:
        if user_info:
            log_with_user_info("WARNING", "❌ Gemini client not available, using fallback response", user_info)
        return get_fallback_response()

    try:
        context = ""
        if user_id:
            context = await get_conversation_context(user_id)
            if context:
                context = f"\n\nPrevious conversation:\n{context}\n"

        prompt = f"{SAKURA_PROMPT}\n\nUser name: {user_name}{context}\nCurrent user message: {user_message}\n\nSakura's response:"
        cache_key = None
        if len(user_message) <= 50 and not context and user_id:
            cache_key = f"gemini_response:{user_id}:{hashlib.md5(user_message.lower().encode()).hexdigest()}"
            cached_response = await cache_get(cache_key)
            if cached_response:
                if user_info:
                    log_with_user_info("INFO", f"📦 Using cached response for message", user_info)
                return cached_response

        response = await gemini_client.aio.models.generate_content(
            model='gemini-2.5-flash', contents=prompt
        )
        ai_response = response.text.strip() if response.text else get_fallback_response()

        if cache_key:
            await cache_set(cache_key, ai_response)

        if user_id:
            await add_to_conversation_history(user_id, user_message, is_user=True)
            await add_to_conversation_history(user_id, ai_response, is_user=False)

        if user_info:
            log_with_user_info("INFO", f"✅ Gemini response generated: '{ai_response[:50]}...'", user_info)

        return ai_response

    except Exception as e:
        if user_info:
            log_with_user_info("ERROR", f"❌ Gemini API error: {e}", user_info)
        else:
            logger.error(f"Gemini API error: {e}")
        return get_error_response()

async def analyze_image_with_gemini(image_bytes: bytes, caption: str, user_name: str = "", user_info: dict = None, user_id: int = None) -> str:
    """Analyze image using Gemini 2.5 Flash with conversation context"""
    if user_info:
        log_with_user_info("DEBUG", f"🖼️ Analyzing image with Gemini: {len(image_bytes)} bytes", user_info)

    if not gemini_client:
        if user_info:
            log_with_user_info("WARNING", "❌ Gemini client not available for image analysis", user_info)
        return "Samjh nahi paa rahi image kya hai 😔"

    try:
        context = ""
        if user_id:
            context = await get_conversation_context(user_id)
            if context:
                context = f"\n\nPrevious conversation:\n{context}\n"

        image_prompt = f"""{SAKURA_PROMPT}

User name: {user_name}{context}

User has sent an image. Caption: "{caption if caption else 'No caption'}"

Analyze this image and respond in Sakura's style about what you see. Be descriptive but keep it to one or two lines as per your character rules. Comment on what's in the image, colors, mood, or anything interesting you notice.

Sakura's response:"""

        image_part = {
            "mime_type": "image/jpeg",
            "data": image_bytes
        }

        response = await gemini_client.aio.models.generate_content(
            model='gemini-2.5-flash', contents=[image_prompt, image_part]
        )
        ai_response = response.text.strip() if response.text else "Kya cute image hai! 😍"

        if user_id:
            image_description = f"[Image: {caption}]" if caption else "[Image sent]"
            await add_to_conversation_history(user_id, image_description, is_user=True)
            await add_to_conversation_history(user_id, ai_response, is_user=False)

        if user_info:
            log_with_user_info("INFO", f"✅ Image analysis completed: '{ai_response[:50]}...'", user_info)

        return ai_response

    except Exception as e:
        if user_info:
            log_with_user_info("ERROR", f"❌ Image analysis error: {e}", user_info)
        else:
            logger.error(f"Image analysis error: {e}")
        return "Image analyze nahi kar paa rahi 😕"

async def analyze_referenced_poll(update: Update, context: ContextTypes.DEFAULT_TYPE, user_message: str, user_info: dict) -> bool:
    """Check if user is asking to analyze a previously sent poll and handle it"""
    poll_analysis_triggers = [
        "poll", "question", "answer", "correct", "option", "choice",
        "batao", "jawab", "sahi", "galat", "kya hai", "what is", "tell me",
        "this", "isme", "ismein", "yeh", "ye", "is", "mein", "sawal"
    ]
    message_lower = user_message.lower()
    contains_poll_request = any(trigger in message_lower for trigger in poll_analysis_triggers)

    if not contains_poll_request:
        return False

    log_with_user_info("DEBUG", "🔍 Detected potential poll analysis request", user_info)

    if update.message.reply_to_message and update.message.reply_to_message.poll:
        log_with_user_info("INFO", "🔍 User asking about replied poll", user_info)
        await send_typing_action(context, update.effective_chat.id, user_info)

        try:
            poll = update.message.reply_to_message.poll
            poll_question = poll.question
            poll_options = [option.text for option in poll.options]
            user_name = update.effective_user.first_name or ""

            response = await analyze_poll_with_gemini(
                poll_question, poll_options, user_name, user_info, user_info["user_id"]
            )
            await update.message.reply_text(response)
            log_with_user_info("INFO", "✅ Referenced poll analyzed successfully", user_info)
            return True
        except Exception as e:
            log_with_user_info("ERROR", f"❌ Error analyzing referenced poll: {e}", user_info)
            error_response = "Poll analyze nahi kar paa rahi 😔"
            await update.message.reply_text(error_response)
            return True
    return False

async def analyze_referenced_image(update: Update, context: ContextTypes.DEFAULT_TYPE, user_message: str, user_info: dict) -> bool:
    """Check if user is asking to analyze a previously sent image and handle it"""
    image_analysis_triggers = [
        "photo", "image", "picture", "pic", "foto", "tasveer",
        "analyze", "batao", "dekho", "kya hai", "what is", "tell me",
        "this", "isme", "ismein", "yeh", "ye", "is", "mein"
    ]
    message_lower = user_message.lower()
    contains_image_request = any(trigger in message_lower for trigger in image_analysis_triggers)

    if not contains_image_request:
        return False

    log_with_user_info("DEBUG", "🔍 Detected potential image analysis request", user_info)

    if update.message.reply_to_message and update.message.reply_to_message.photo:
        log_with_user_info("INFO", "🔍 User asking about replied image", user_info)
        await send_typing_action(context, update.effective_chat.id, user_info)

        try:
            photo = update.message.reply_to_message.photo[-1]
            file = await context.bot.get_file(photo.file_id)
            image_bytes = await file.download_as_bytearray()
            user_name = update.effective_user.first_name or ""
            caption = update.message.reply_to_message.caption or ""

            response = await analyze_image_with_gemini(
                image_bytes, caption, user_name, user_info, user_info["user_id"]
            )
            await update.message.reply_text(response)
            log_with_user_info("INFO", "✅ Referenced image analyzed successfully", user_info)
            return True
        except Exception as e:
            log_with_user_info("ERROR", f"❌ Error analyzing referenced image: {e}", user_info)
            error_response = "Image analyze nahi kar paa rahi 😔"
            await update.message.reply_text(error_response)
            return True
    return False

async def analyze_poll_with_gemini(poll_question: str, poll_options: list, user_name: str = "", user_info: dict = None, user_id: int = None) -> str:
    """Analyze poll using Gemini 2.5 Flash to suggest the correct answer"""
    if user_info:
        log_with_user_info("DEBUG", f"📊 Analyzing poll with Gemini: '{poll_question[:50]}...'", user_info)

    if not gemini_client:
        if user_info:
            log_with_user_info("WARNING", "❌ Gemini client not available for poll analysis", user_info)
        return "Poll samjh nahi paa rahi 😔"

    try:
        context = ""
        if user_id:
            context = await get_conversation_context(user_id)
            if context:
                context = f"\n\nPrevious conversation:\n{context}\n"

        options_text = "\n".join([f"{i+1}. {option}" for i, option in enumerate(poll_options)])
        poll_prompt = f"""{SAKURA_PROMPT}

User name: {user_name}{context}

User has sent a poll or asked about a poll question. Analyze this question and suggest which option might be the correct answer.

Poll Question: "{poll_question}"

Options:
{options_text}

Analyze this poll question and respond in Sakura's style about which option you think is correct and why. Keep it to one or two lines as per your character rules. Be helpful and give a quick reason.

Sakura's response:"""

        response = await gemini_client.aio.models.generate_content(
            model='gemini-2.5-flash', contents=poll_prompt
        )
        ai_response = response.text.strip() if response.text else "Poll ka answer samjh nahi aaya 😅"

        if user_id:
            poll_description = f"[Poll: {poll_question}] Options: {', '.join(poll_options)}"
            await add_to_conversation_history(user_id, poll_description, is_user=True)
            await add_to_conversation_history(user_id, ai_response, is_user=False)

        if user_info:
            log_with_user_info("INFO", f"✅ Poll analysis completed: '{ai_response[:50]}...'", user_info)

        return ai_response

    except Exception as e:
        if user_info:
            log_with_user_info("ERROR", f"❌ Poll analysis error: {e}", user_info)
        else:
            logger.error(f"Poll analysis error: {e}")
        return "Poll analyze nahi kar paa rahi 😕"

# Initialize the client when the module is loaded
initialize_gemini_client()
