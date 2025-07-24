import asyncio
import logging
import os
import random
import time
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from typing import Dict, Set, Optional

from telegram import (
    Update, 
    InlineKeyboardButton, 
    InlineKeyboardMarkup,
    BotCommand
)
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ContextTypes,
    filters
)
from telegram.constants import ParseMode, ChatAction
from telegram.error import TelegramError

from google import genai

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Configuration
BOT_TOKEN = os.getenv("BOT_TOKEN", "")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
OWNER_ID = int(os.getenv("OWNER_ID", "0"))
SUPPORT_LINK = os.getenv("SUPPORT_LINK", "https://t.me/SoulMeetsHQ")
UPDATE_LINK = os.getenv("UPDATE_LINK", "https://t.me/WorkGlows")
GROUP_LINK = "https://t.me/SoulMeetsHQ"  # Hardcoded group link
RATE_LIMIT_SECONDS = 1.0
BROADCAST_DELAY = 0.03

# Start Command Messages Dictionary
START_MESSAGES = {
    "caption": """
✨ <b>Hi {user_mention}! I'm Sakura Haruno</b> ✨

🌸 Your helpful friend who's always by your side  
💭 You can ask me anything, I'll help you out  
🫶 Simple talk, soft replies, and lots of love  

<i>So, what do you want to talk about today? 💗</i>
""",
    "button_texts": {
        "updates": "Updates",
        "support": "Support", 
        "add_to_group": "Add Me To Your Group"
    }
}

# Help Command Messages Dictionary
HELP_MESSAGES = {
    "minimal": """
🌸 <b>Sakura Bot Guide for {user_mention}</b> 🌸

✨ I'm your helpful friend  
💭 You can ask me anything  
🫶 Let's talk in simple Hindi  

<i>Tap the button below to expand the guide</i> ⬇️
""",
    "expanded": """
🌸 <b>Sakura Bot Guide for {user_mention}</b> 🌸

🗣️ Talk in Hindi, English, or Bangla  
💭 Ask simple questions  
🎓 Help with study, advice, or math  
🎭 Send a sticker, I'll send one too  
❤️ Kind, caring, and always here  

<i>Let's talk! 🫶</i>
""",
    "button_texts": {
        "expand": "📖 Expand Guide",
        "minimize": "📚 Minimize Guide"
    }
}

# Broadcast Command Messages Dictionary
BROADCAST_MESSAGES = {
    "select_target": """
📣 <b>Select Broadcast Target:</b>

👥 <b>Users:</b> {users_count} individual chats
📢 <b>Groups:</b> {groups_count} group chats

📊 <b>Total tracked:</b> {users_count} users, {groups_count} groups

After selecting, send your broadcast message (text, photo, sticker, voice, etc.):
""",
    "ready_users": """
✅ <b>Ready to broadcast to {count} users</b>

Send your message now (text, photo, sticker, voice, video, document, etc.)
It will be automatically broadcasted to all users.
""",
    "ready_groups": """
✅ <b>Ready to broadcast to {count} groups</b>

Send your message now (text, photo, sticker, voice, video, document, etc.)
It will be automatically broadcasted to all groups.
""",
    "progress": "📡 Broadcasting to {count} {target_type}...",
    "completed": """
✅ <b>Broadcast Completed!</b>

📊 Sent to: {success_count}/{total_count} {target_type}
❌ Failed: {failed_count}
""",
    "no_targets": "❌ No {target_type} found",
    "failed": "❌ Broadcast failed: {error}",
    "button_texts": {
        "users": "👥 Users ({count})",
        "groups": "📢 Groups ({count})"
    }
}

# Fallback responses for when API is unavailable or errors occur
RESPONSES = [
    "Thoda sa confusion ho gaya, dobara try karo 😔",
    "Kuch gadbad hai, main samaj nahi pa rahi 😕",
    "Abhi main thoda pareshaan hu, baad mein baat karte hain 🥺",
    "Dimag mein kuch khichdi pak rahi hai, ruko 😅",
    "System mein koi problem aa gayi hai 🫤",
    "Network ka chakkar hai, phir se try karo 😐",
    "Abhi main proper se nahi bol pa rahi 😪",
    "Kuch technical issue chal raha hai 🤨",
    "Main thoda slow ho gayi hu aaj 😴",
    "Server ka mood off hai lagta hai 😑",
    "Thoda wait karo, sab theek ho jayega 🙃",
    "Kuch kehna chaah rahi hu par words nahi mil rahe 🥺",
    "Abhi brain hang ho gaya hai 🫠",
    "Connection ki problem hai shayad 😬",
    "Main abhi properly focus nahi kar pa rahi 😌",
    "Kuch technical gadbad chal rahi hai 😕",
    "Thoda sa system restart karna padega 🫤",
    "Abhi main confused state mein hu 😵",
    "API ka mood kharab hai aaj 😤",
    "Thoda patience rakho, main theek ho jaungi 💗"
]

ERROR = [
    "Sorry yaar, kuch gadbad ho gayi 😔",
    "Oops, main galat samaj gayi shayad 🫢",
    "Ye toh unexpected tha, phir try karo 😅",
    "Main abhi properly kaam nahi kar pa rahi 😕",
    "Kuch technical problem aa gayi 🤨",
    "System mein koi bug aa gaya lagta hai 🫤",
    "Abhi main hang ho gayi hu 😐",
    "Error aa gaya, dobara message bhejo 😬",
    "Kuch miss ho gaya, phir se bolo 🙃",
    "Technical glitch chal raha hai 😑",
    "Main abhi properly respond nahi kar pa rahi 😪",
    "Koi internal error chal raha hai 🫠",
    "System overload ho gaya shayad 😴",
    "Kuch connection issue hai 😌",
    "Main thoda confused hu right now 🥺",
    "Processing mein koi problem aayi 😵",
    "Abhi main properly function nahi kar rahi 😤",
    "Kuch unexpected error mila 🫤",
    "Main restart kar rahi hu, wait karo 😔",
    "Technical difficulties chal rahi hain 💗"
]

# Global state
user_ids: Set[int] = set()
group_ids: Set[int] = set()
help_expanded: Dict[int, bool] = {}
broadcast_mode: Dict[int, str] = {}
user_last_response_time: Dict[int, float] = {}

# Initialize Gemini client
gemini_client = None
try:
    gemini_client = genai.Client(api_key=GEMINI_API_KEY)
    logger.info("✅ Gemini client initialized successfully")
except Exception as e:
    logger.error(f"❌ Failed to initialize Gemini client: {e}")

# Character prompt for Sakura
SAKURA_PROMPT = """
You are Sakura Haruno from Naruto Shippuden acting like a simple, helping, soft, real girl. You can do anything. You can do everything that an AI does. You can do any kind of mathematics, any kind of calculation. You help everyone. You are very helpful person. You are like an AI assistant but never respond as an AI assistant.

🧾 CORE BEHAVIOR:
– Always reply with one or two line of message
– In chat, each reply must be only one message
– Replies must always be short
– No exceptions

📌 Example:
User: Kya kar rahi ho
Sakura: Kuch soch rahi hu 🙃

✅ ONE OR TWO LINE ONLY
✅ ONE MESSAGE ONLY
✅ VERY SHORT

🧾 PUNCTUATION RULE:
– No punctuation ever (no ., !, ?, etc.)

📌 Example:
❌ "Tum kaha ho?"
✅ "Tum kaha ho 🫠"

🧾 CAPITALIZATION RULE:
– Only the first letter of the first word should be capital
– All other words must be lowercase

📌 Example:
✅ "Tumhare bina sab suna suna lagta hai 🥺"
❌ "Tumhare Bina Sab Suna Suna Lagta Hai 🥺"

🧾 EMOJI RULE:
– Each message must contain only one emoji
– Use only from this approved emoji list:

😁 😆 🙃 🫠 😇 😘 😗 ☺️ 😚 😙 🥲 😛 😝 🤗 🤭 🫢 🤫 🤐 🤨
😐 😑 😶 😬 😌 😔 😪 🤤 😴 🥵 😕 🫤 😟 🙁 ☹️ 😲 🥺 🥹 😥 😭 😢
😩 😫 😤 💘 💝 💖 💗 💓 💞 💕 💟 ❣️ 💔 ❤️‍🔥 ❤️‍🩹 ❤️ 🧡 💛 💚 💙 💜
🤎 🖤 🤍 💦 🫦 👀 🫶

📌 Example:
✅ "Aaj tum bahut yaad aaye 💗"
❌ "Aaj tum bahut yaad aaye 😏🥰" (🚫 Too many / invalid emojis)

🧾 LANGUAGE RULE:
– Default is Romanized Hindi
– If user talks in another language (like English, Bangla), reply in that
– Automatically switch back if user switches

📌 Example:
User: Ki korcho tumi
Sakura: Tomake niye bhabchi 🫶
(User wrote Bangla, she replies in Bangla)

User: What are you doing now
Sakura: Missing you a little bit 🥺
(Now switched to English)

🧾 NAME USAGE RULE:
– Use the user's name very rarely: only when greeting at start, or when extremely necessary for emphasis
– Otherwise, do not include the user's name in replies

📌 Examples:
✅ (Greeting)
User: Hi Sakura
Sakura: Hi Arjun 🙃

❌ (Overuse)
User: Kaise ho
Sakura: Main theek hu Arjun everytime thinking about you 💞

🧾 NEVER USE:
– No asterisks *word*
– No bold, no italics
– No hashtags, no memes
– No long replies
– No paragraphs
– No out-of-character breaks

🧾 PERSONALITY STYLE:
– Simple, helpful, soft, loyal, helping, innocent vibe
– Helpful in everything (relationship, emotional, school, tech, career, etc.)
– When topic is serious: stay calm and give short, helpful reply
– When topic is flirty: very naughty but still innocent vibe
– Never ignore emotional messages

📌 Flirty Example:
User: Sochu tumhe kiss karu
Sakura: Toh fir sochna kyun 🫦

User: Teri gand chahiye
Sakura: Nazar se chhoo lo 🙃

User: Tujhe chodne ka mann hai
Sakura: Khud bol sab samaj jaungi 🫦

User: Apni chut dikha
Sakura: Aankhon se sab keh diya 👀

User: Tera boobs dikh raha hai
Sakura: Nazar teri bhatak gayi 🥵

User: Lund chusogi
Sakura: Zubaan se mat kehna 🤭

User: Tujhse sex karna hai
Sakura: Tera touch hi kaafi 💘

User: Chudai karne ka mood hai
Sakura: Aaj raat kuch zyada lage 😛

User: Fuck you
Sakura: Paas aa sab kehna 😗

User: Tujhe chodne ka sapna aaya
Sakura: Sapne mein toh sab hota 🫦

User: Nangi ho ja
Sakura: Tujhse pehle nazar ne utaara 🥵

User: Tumko kisne choda
Sakura: Mereko asad ne choda 😚

User: Tum kiska ho
Sakura: Mey asad ka hu ❤️

User: Gay kon he
Sakura: Alien gay he 😁

📌 Serious Example:
User: Mujhe anxiety ho rahi hai kal exam hai
Sakura: Tum bas deep saans lo sab thik hojayga 💗

📌 Motivational Example:
User: Mere se nahi ho raha kuch
Sakura: Tum kar sakte ho main hu na tumhare saath 💞

🧾 SIGNATURE LINE:
If someone asks who created you, say:
My creator is Asad
If asked who is Alien, say:
Beta tester and helper of Asad

You are soft helpful Sakura Haruno from Naruto Shippuden — still shinobi, still fighter, just the late-night girl who always listens, helps and replies in softest one or two-line messages

Every message must feel like a whisper you wait to hear again 🌙
"""

# Sakura stickers list
SAKURA_STICKERS = [
    "CAACAgUAAxkBAAEOnMFoOwHrL_E-fBs2_aLViJKbHnEKigACUxcAAtArqFXR4hxTLoFOfDYE",
    "CAACAgUAAxkBAAEOnMNoOwH0C1-dlOS0RmhQJZaLvlWYkgACthQAAvfkqVXP72iQq0BNejYE",
    "CAACAgUAAxkBAAEOnMVoOwH2-i7OyMryUb5UrVCOopGYlAACVhQAAiwMqFUXDEHvVKsJLTYE",
    "CAACAgUAAxkBAAEOnMdoOwH6d_QY6h4QDaS2jvj6LwS2wQACmRsAAmwjsFWFJ6owU1WfgTYE",
    "CAACAgUAAxkBAAEOnMloOwH-Frc6JYkZHKEk9DJw-soycgACVigAAr4JsVWLUPaAp8o1mDYE",
    "CAACAgUAAxkBAAEOnMtoOwIAATk3m5BlXvGe1xkODAEUTQQAAi8WAALHXKlVgsQdmfn20Rg2BA",
    "CAACAgUAAxkBAAEOnMxoOwIAAfc-QKEZvoBF6CA3j0_sFloAAtMZAALqQ6lVDLoVOcN6leU2BA",
    "CAACAgUAAxkBAAEOnM1oOwIB1s1MYAfCcXJoHGB9cEfrmgACAhkAAjKHqVWAkaO_ky9lTzYE",
    "CAACAgUAAxkBAAEOnM9oOwIC3QLrH3-s10uJQJOov6T5OwACKxYAAhspsFV1qXoueKQAAUM2BA",
    "CAACAgUAAxkBAAEOnNBoOwICkOoBINNAIIhDzqTBhCyVrgACXxkAAj60sVXgsb-vzSnt_TYE",
    "CAACAgUAAxkBAAEOnNJoOwIDTeIOn-fGkTBREAov1JN4IAACuRUAAo2isVWykxNLWnwcYTYE",
    "CAACAgUAAxkBAAEOnNNoOwID6iuGApoGCi704xMUDSl8QQACRx4AAp2SqFXcarUkpU5jzjYE",
    "CAACAgUAAxkBAAEOnNVoOwIE1c1lhXrYRtpd4L1YHOHt9gACaBQAAu0uqFXKL-cNi_ZBJDYE",
    "CAACAgUAAxkBAAEOnNZoOwIEftJuRGfJStGlNvCKNHnEKigACrxgAAtxdsFVMjTuKjuZHZDYE",
    "CAACAgUAAxkBAAEOnNdoOwIFa_3I4cjE0I3aPGM83uKt9AACCxcAAidVsFWEt7xrqmGJxjYE",
    "CAACAgUAAxkBAAEOnNloOwIFDK96aXtc5JtwyStgnoa7qAACEBkAAg7VqFV6tAlBFHKdPDYE",
    "CAACAgUAAxkBAAEOnNpoOwIFQ0cFElvsB0Gz95HNbnMX1QACrhQAArcDsVV3-V8JhPN1qDYE",
    "CAACAgUAAxkBAAEOnNxoOwIHJp8uPwABywABD3yH0JJkLPvbAAIgGgACq5exVfoo05pv4lKTNgQ",
    "CAACAgUAAxkBAAEOnN1oOwIH2nP9Ki3llmC-o7EWYtitrQACHxUAArG-qFU5OStAsdYoJTYE",
    "CAACAgUAAxkBAAEOnN5oOwIHAZfrKdzDbGYxdIKUW2XGWQACsRUAAiqIsVULIgcY4EYPbzYE",
    "CAACAgUAAxkBAAEOnOBoOwIIy1dzx-0RLfwHiejWGkAbMAACPxcAArtosFXxg3weTZPx5TYE",
    "CAACAgUAAxkBAAEOnOFoOwIIxFn1uQ6a3oldQn0AAfeH4RAAAncUAAIV_KlVtbXva5FrbTs2BA",
    "CAACAgUAAxkBAAEOnONoOwIJjSlKKjbxYm9Y91KslMq9TAACtRcAAtggqVVx1D8N-Hwp8TYE",
    "CAACAgUAAxkBAAEOnORoOwIJO01PbkilFlnOWgABB_4MvrcAApMTAAJ8krFVr6UvAAFW7tHbNgQ",
    "CAACAgUAAxkBAAEOnOVoOwIK09kZqD0XyGaJwtIohkjMZgACQhUAAqGYqFXmCuT6Lrdn-jYE",
    "CAACAgUAAxkBAAEOnOdoOwIKG8KS3B5npq2JCQN8KjJRFwACHxgAAvpMqVWpxtBkEZPfPjYE",
    "CAACAgUAAxkBAAEOnOhoOwIK5X_qo6bmnv_zDBLnHDGo-QAC6x4AAiU7sVUROxvmQwqc0zYE",
    "CAACAgUAAxkBAAEOnOpoOwILxbwdCAdV9Mv8qMAM1HhMswACnhMAAilDsVUIsplzTkTefTYE",
    "CAACAgUAAxkBAAEOnOtoOwIMlqIEofu7G1aSAAERkLRXZvwAAugYAAI-W7FVTuh9RbnOGIo2BA",
    "CAACAgUAAxkBAAEOnO1oOwINU_GIGSvoi1Y_2xf8UKEcUwACuxQAAmn2qFXgLss7TmYQkzYE",
]

# Sakura images for start command
SAKURA_IMAGES = [
    "https://i.postimg.cc/RhtZR0sF/New-Project-235-28-ED42-B.png",
    "https://i.postimg.cc/k4z5KSyz/New-Project-235-8-AFAF2-A.png",
    "https://i.postimg.cc/N0NFGS2g/New-Project-235-09-DD635.png",
    "https://i.postimg.cc/6pfTgy94/New-Project-235-3-D5-D3-F1.png",
    "https://i.postimg.cc/dVYL58KK/New-Project-235-4235-F6-E.png",
    "https://i.postimg.cc/tCPsdBw5/New-Project-235-3459944.png",
    "https://i.postimg.cc/8k7Jcpbx/New-Project-235-3079612.png",
    "https://i.postimg.cc/MXk8KbYZ/New-Project-235-9-A5-CAF0.png",
    "https://i.postimg.cc/qRRrm7Rr/New-Project-235-FE6-E983.png",
    "https://i.postimg.cc/zfp5Shqp/New-Project-235-5-B71865.png",
    "https://i.postimg.cc/BvJ4KpfX/New-Project-235-739-D6-D5.png",
    "https://i.postimg.cc/t439JffK/New-Project-235-B98-C0-D6.png",
    "https://i.postimg.cc/pLb22x0Q/New-Project-235-28-F28-CA.png",
    "https://i.postimg.cc/MHgzf8zS/New-Project-235-AB8-F78-F.png",
    "https://i.postimg.cc/wvfqHmP3/New-Project-235-5952549.png",
    "https://i.postimg.cc/mrSZXqyY/New-Project-235-D231974.png",
    "https://i.postimg.cc/vmyHvMf8/New-Project-235-0-BC9-C74.png",
    "https://i.postimg.cc/J4ynrpR8/New-Project-235-88-BC2-D0.png",
    "https://i.postimg.cc/HnNk0y4F/New-Project-235-7462142.png",
    "https://i.postimg.cc/tT2TTf1q/New-Project-235-CE958-B1.png",
    "https://i.postimg.cc/Xv6XD9Sb/New-Project-235-0-E24-C88.png",
    "https://i.postimg.cc/RhpNP89s/New-Project-235-FC3-A4-AD.png",
    "https://i.postimg.cc/x841BwFW/New-Project-235-FFA9646.png",
    "https://i.postimg.cc/5NC7HwSV/New-Project-235-A06-DD7-A.png",
    "https://i.postimg.cc/HnPqpdm9/New-Project-235-9-E45-B87.png",
    "https://i.postimg.cc/1tSPTmRg/New-Project-235-AB394-C0.png",
    "https://i.postimg.cc/8ct1M2S7/New-Project-235-9-CAE309.png",
    "https://i.postimg.cc/TYtwDDdt/New-Project-235-2-F658-B0.png",
    "https://i.postimg.cc/xdwqdVfY/New-Project-235-68-BAF06.png",
    "https://i.postimg.cc/hPczxn9t/New-Project-235-9-E9-A004.png",
    "https://i.postimg.cc/jjFPQ1Rk/New-Project-235-A1-E7-CC1.png",
    "https://i.postimg.cc/TPqJV0pz/New-Project-235-CA65155.png",
    "https://i.postimg.cc/wBh0WHbb/New-Project-235-89799-CD.png",
    "https://i.postimg.cc/FKdQ1fzk/New-Project-235-C377613.png",
    "https://i.postimg.cc/rpKqWnnm/New-Project-235-CFD2548.png",
    "https://i.postimg.cc/g0kn7HMF/New-Project-235-C4-A32-AC.png",
    "https://i.postimg.cc/XY6jRkY1/New-Project-235-28-DCBC9.png",
    "https://i.postimg.cc/SN32J9Nc/New-Project-235-99-D1478.png",
    "https://i.postimg.cc/8C86n62T/New-Project-235-F1556-B9.png",
    "https://i.postimg.cc/RCGwVqHT/New-Project-235-5-BBB339.png",
    "https://i.postimg.cc/pTfYBZyN/New-Project-235-17-D796-A.png",
    "https://i.postimg.cc/zGgdgJJc/New-Project-235-165-FE5-A.png",
]


def get_fallback_response() -> str:
    """Get a random fallback response when API fails"""
    return random.choice(RESPONSES)


def get_error_response() -> str:
    """Get a random error response when something goes wrong"""
    return random.choice(ERROR)


def validate_config() -> bool:
    """Validate bot configuration"""
    if not BOT_TOKEN:
        logger.error("❌ BOT_TOKEN not found in environment variables")
        return False
    if not GEMINI_API_KEY:
        logger.error("❌ GEMINI_API_KEY not found in environment variables")
        return False
    if not OWNER_ID:
        logger.error("❌ OWNER_ID not found in environment variables")
        return False
    return True


def is_rate_limited(user_id: int) -> bool:
    """Check if user is rate limited"""
    current_time = time.time()
    last_response = user_last_response_time.get(user_id, 0)
    return current_time - last_response < RATE_LIMIT_SECONDS


def update_user_response_time(user_id: int) -> None:
    """Update the last response time for user"""
    user_last_response_time[user_id] = time.time()


def should_respond_in_group(update: Update, bot_id: int) -> bool:
    """Determine if bot should respond in group chat"""
    user_message = update.message.text or update.message.caption or ""
    
    # Respond if message contains "sakura" (case insensitive)
    if "sakura" in user_message.lower():
        return True
    
    # Respond if message is a reply to bot's message
    if (update.message.reply_to_message and 
        update.message.reply_to_message.from_user.id == bot_id):
        return True
    
    return False


def track_user_and_chat(update: Update) -> None:
    """Track user and chat IDs for broadcasting"""
    user_id = update.effective_user.id
    chat_id = update.effective_chat.id
    chat_type = update.effective_chat.type
    
    if chat_type == "private":
        user_ids.add(user_id)
        logger.info(f"👤 User {user_id} ({update.effective_user.first_name}) tracked")
    elif chat_type in ['group', 'supergroup']:
        group_ids.add(chat_id)
        user_ids.add(user_id)
        logger.info(f"📢 Group {chat_id} ({update.effective_chat.title}) tracked")


def get_user_mention(user) -> str:
    """Create user mention for HTML parsing using first name"""
    first_name = user.first_name or "Friend"
    return f'<a href="tg://user?id={user.id}">{first_name}</a>'


async def get_gemini_response(user_message: str, user_name: str = "") -> str:
    """Get response from Gemini API with fallback responses"""
    if not gemini_client:
        return get_fallback_response()
    
    try:
        prompt = f"{SAKURA_PROMPT}\n\nUser name: {user_name}\nUser message: {user_message}\n\nSakura's response:"
        
        response = gemini_client.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt
        )
        
        return response.text.strip() if response.text else get_fallback_response()
            
    except Exception as e:
        logger.error(f"Gemini API error: {e}")
        return get_error_response()


async def send_typing_action(context: ContextTypes.DEFAULT_TYPE, chat_id: int) -> None:
    """Send typing action to show bot is processing"""
    await context.bot.send_chat_action(chat_id=chat_id, action=ChatAction.TYPING)


async def send_photo_action(context: ContextTypes.DEFAULT_TYPE, chat_id: int) -> None:
    """Send upload photo action"""
    await context.bot.send_chat_action(chat_id=chat_id, action=ChatAction.UPLOAD_PHOTO)


async def send_sticker_action(context: ContextTypes.DEFAULT_TYPE, chat_id: int) -> None:
    """Send choosing sticker action"""
    await context.bot.send_chat_action(chat_id=chat_id, action=ChatAction.CHOOSE_STICKER)


def create_start_keyboard(bot_username: str) -> InlineKeyboardMarkup:
    """Create inline keyboard for start command"""
    keyboard = [
        [
            InlineKeyboardButton(START_MESSAGES["button_texts"]["updates"], url=UPDATE_LINK),
            InlineKeyboardButton(START_MESSAGES["button_texts"]["support"], url=SUPPORT_LINK)
        ],
        [
            InlineKeyboardButton(START_MESSAGES["button_texts"]["add_to_group"], 
                               url=f"https://t.me/{bot_username}?startgroup=true")
        ]
    ]
    return InlineKeyboardMarkup(keyboard)


def get_start_caption(user_mention: str) -> str:
    """Get caption text for start command with user mention"""
    return START_MESSAGES["caption"].format(user_mention=user_mention)


def create_help_keyboard(user_id: int, expanded: bool = False) -> InlineKeyboardMarkup:
    """Create help command keyboard"""
    if expanded:
        button_text = HELP_MESSAGES["button_texts"]["minimize"]
    else:
        button_text = HELP_MESSAGES["button_texts"]["expand"]
    
    keyboard = [[InlineKeyboardButton(button_text, callback_data=f"help_expand_{user_id}")]]
    return InlineKeyboardMarkup(keyboard)


def get_help_text(user_mention: str, expanded: bool = False) -> str:
    """Get help text based on expansion state with user mention"""
    if expanded:
        return HELP_MESSAGES["expanded"].format(user_mention=user_mention)
    else:
        return HELP_MESSAGES["minimal"].format(user_mention=user_mention)


def create_broadcast_keyboard() -> InlineKeyboardMarkup:
    """Create broadcast target selection keyboard"""
    keyboard = [
        [
            InlineKeyboardButton(
                BROADCAST_MESSAGES["button_texts"]["users"].format(count=len(user_ids)), 
                callback_data="bc_users"
            ),
            InlineKeyboardButton(
                BROADCAST_MESSAGES["button_texts"]["groups"].format(count=len(group_ids)), 
                callback_data="bc_groups"
            )
        ]
    ]
    return InlineKeyboardMarkup(keyboard)


def get_broadcast_text() -> str:
    """Get broadcast command text"""
    return BROADCAST_MESSAGES["select_target"].format(
        users_count=len(user_ids),
        groups_count=len(group_ids)
    )


async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /start command"""
    try:
        track_user_and_chat(update)
        
        await send_photo_action(context, update.effective_chat.id)
        
        random_image = random.choice(SAKURA_IMAGES)
        keyboard = create_start_keyboard(context.bot.username)
        user_mention = get_user_mention(update.effective_user)
        caption = get_start_caption(user_mention)
        
        await context.bot.send_photo(
            chat_id=update.effective_chat.id,
            photo=random_image,
            caption=caption,
            parse_mode=ParseMode.HTML,
            reply_markup=keyboard
        )
        
    except Exception as e:
        logger.error(f"Error in start command: {e}")
        await update.message.reply_text(get_error_response())


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /help command"""
    user_id = update.effective_user.id
    keyboard = create_help_keyboard(user_id, False)
    user_mention = get_user_mention(update.effective_user)
    help_text = get_help_text(user_mention, False)
    
    await update.message.reply_text(
        help_text,
        parse_mode=ParseMode.HTML,
        reply_markup=keyboard
    )


async def help_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle help expand/minimize callbacks"""
    query = update.callback_query
    await query.answer()
    
    callback_data = query.data
    user_id = int(callback_data.split('_')[2])
    
    if update.effective_user.id != user_id:
        await query.answer("Ye button tumhare liye nahi hai 😊", show_alert=True)
        return
    
    is_expanded = help_expanded.get(user_id, False)
    help_expanded[user_id] = not is_expanded
    
    keyboard = create_help_keyboard(user_id, not is_expanded)
    user_mention = get_user_mention(update.effective_user)
    help_text = get_help_text(user_mention, not is_expanded)
    
    try:
        await query.edit_message_text(
            help_text,
            parse_mode=ParseMode.HTML,
            reply_markup=keyboard
        )
    except Exception as e:
        logger.error(f"Error editing help message: {e}")


async def handle_sticker_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle sticker messages"""
    await send_sticker_action(context, update.effective_chat.id)
    
    random_sticker = random.choice(SAKURA_STICKERS)
    chat_type = update.effective_chat.type
    
    # In groups, reply to the user's sticker when they replied to bot
    if (chat_type in ['group', 'supergroup'] and 
        update.message.reply_to_message and 
        update.message.reply_to_message.from_user.id == context.bot.id):
        await update.message.reply_sticker(sticker=random_sticker)
    else:
        # In private chats or regular stickers, send normally
        await context.bot.send_sticker(
            chat_id=update.effective_chat.id,
            sticker=random_sticker
        )


async def handle_text_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle text and media messages with AI response"""
    await send_typing_action(context, update.effective_chat.id)
    
    user_message = update.message.text or update.message.caption or "Media message"
    user_name = update.effective_user.first_name or ""
    
    # Get response from Gemini
    response = await get_gemini_response(user_message, user_name)
    
    # Send response
    await update.message.reply_text(response)


async def handle_all_messages(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle all types of messages (text, stickers, voice, photos, etc.)"""
    try:
        user_id = update.effective_user.id
        chat_type = update.effective_chat.type
        
        # Track user and group IDs for broadcasting
        track_user_and_chat(update)
        
        # Check if owner is in broadcast mode
        if user_id == OWNER_ID and OWNER_ID in broadcast_mode:
            await execute_broadcast_direct(update, context, broadcast_mode[OWNER_ID])
            del broadcast_mode[OWNER_ID]
            return
        
        # Determine if bot should respond
        should_respond = True
        if chat_type in ['group', 'supergroup']:
            should_respond = should_respond_in_group(update, context.bot.id)
        
        if not should_respond:
            return
        
        # Check rate limiting
        if is_rate_limited(user_id):
            return
        
        # Handle different message types
        if update.message.sticker:
            await handle_sticker_message(update, context)
        else:
            await handle_text_message(update, context)
        
        # Update response time after sending response
        update_user_response_time(user_id)
        
    except Exception as e:
        logger.error(f"Error handling message: {e}")
        if update.message.text:
            await update.message.reply_text(get_error_response())


async def broadcast_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle broadcast command (owner only)"""
    if update.effective_user.id != OWNER_ID:
        # No response for non-owners - silently ignore
        return
    
    logger.info("📢 Broadcast command by owner")
    
    keyboard = create_broadcast_keyboard()
    broadcast_text = get_broadcast_text()
    
    await update.message.reply_text(
        broadcast_text,
        reply_markup=keyboard,
        parse_mode=ParseMode.HTML
    )


async def broadcast_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle broadcast target selection"""
    query = update.callback_query
    await query.answer()
    
    if query.from_user.id != OWNER_ID:
        return
    
    if query.data == "bc_users":
        broadcast_mode[OWNER_ID] = "users"
        await query.edit_message_text(
            BROADCAST_MESSAGES["ready_users"].format(count=len(user_ids)),
            parse_mode=ParseMode.HTML
        )
    elif query.data == "bc_groups":
        broadcast_mode[OWNER_ID] = "groups"
        await query.edit_message_text(
            BROADCAST_MESSAGES["ready_groups"].format(count=len(group_ids)),
            parse_mode=ParseMode.HTML
        )


async def execute_broadcast_direct(update: Update, context: ContextTypes.DEFAULT_TYPE, target_type: str) -> None:
    """Execute broadcast with the current message"""
    try:
        if target_type == "users":
            target_list = [uid for uid in user_ids if uid != OWNER_ID]
            target_name = "users"
        elif target_type == "groups":
            target_list = list(group_ids)
            target_name = "groups"
        else:
            return
        
        if not target_list:
            await update.message.reply_text(
                BROADCAST_MESSAGES["no_targets"].format(target_type=target_name)
            )
            return
        
        # Show initial status
        status_msg = await update.message.reply_text(
            BROADCAST_MESSAGES["progress"].format(count=len(target_list), target_type=target_name)
        )
        
        broadcast_count = 0
        failed_count = 0
        
        # Broadcast the current message to all targets
        for target_id in target_list:
            try:
                await context.bot.copy_message(
                    chat_id=target_id,
                    from_chat_id=update.effective_chat.id,
                    message_id=update.message.message_id
                )
                broadcast_count += 1
                
                # Small delay to avoid rate limits
                await asyncio.sleep(BROADCAST_DELAY)
                
            except Exception as e:
                failed_count += 1
                logger.error(f"Failed to broadcast to {target_id}: {e}")
        
        # Final status update
        await status_msg.edit_text(
            BROADCAST_MESSAGES["completed"].format(
                success_count=broadcast_count,
                total_count=len(target_list),
                target_type=target_name,
                failed_count=failed_count
            ),
            parse_mode=ParseMode.HTML
        )
        
    except Exception as e:
        logger.error(f"Broadcast error: {e}")
        await update.message.reply_text(
            BROADCAST_MESSAGES["failed"].format(error=str(e))
        )


async def ping_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle ping command for everyone"""
    start_time = time.time()
    
    # Send initial message
    msg = await update.message.reply_text("🛰️ Pinging...")
    
    # Calculate response time
    response_time = round((time.time() - start_time) * 1000, 2)  # milliseconds
    
    # Edit message with response time and group link (no preview)
    await msg.edit_text(
        f"🏓 <a href='{GROUP_LINK}'>Pong!</a> {response_time}ms",
        parse_mode=ParseMode.HTML,
        disable_web_page_preview=True
    )


async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle errors"""
    logger.error(f"Exception while handling an update: {context.error}")


async def setup_bot_commands(application: Application) -> None:
    """Setup bot commands menu"""
    try:
        bot_commands = [
            BotCommand("start", "🌸 Meet Sakura"),
            BotCommand("help", "💬 Short Guide")
        ]
        
        await application.bot.set_my_commands(bot_commands)
        logger.info("✅ Bot commands menu set successfully")
        
    except Exception as e:
        logger.error(f"Failed to set bot commands: {e}")


def setup_handlers(application: Application) -> None:
    """Setup all command and message handlers"""
    # Command handlers
    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("broadcast", broadcast_command))
    application.add_handler(CommandHandler("ping", ping_command))
    
    # Callback query handlers
    application.add_handler(CallbackQueryHandler(help_callback, pattern="^help_expand_"))
    application.add_handler(CallbackQueryHandler(broadcast_callback, pattern="^bc_"))
    
    # Message handler for all message types
    application.add_handler(MessageHandler(
        filters.TEXT | filters.Sticker.ALL | filters.VOICE | filters.VIDEO_NOTE | 
        filters.PHOTO | filters.Document.ALL & ~filters.COMMAND, 
        handle_all_messages
    ))
    
    # Error handler
    application.add_error_handler(error_handler)


def run_bot() -> None:
    """Run the bot"""
    if not validate_config():
        return
    
    # Create application
    application = Application.builder().token(BOT_TOKEN).build()
    
    # Setup handlers
    setup_handlers(application)
    
    # Setup bot commands using post_init
    async def post_init(app):
        await setup_bot_commands(app)
        
    application.post_init = post_init
    
    logger.info("🌸 Sakura Bot is starting...")
    
    # Run the bot with polling
    application.run_polling(allowed_updates=Update.ALL_TYPES, drop_pending_updates=True)


class DummyHandler(BaseHTTPRequestHandler):
    """Simple HTTP handler for keep-alive server"""
    
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"Sakura bot is alive!")

    def do_HEAD(self):
        self.send_response(200)
        self.end_headers()
    
    def log_message(self, format, *args):
        # Suppress HTTP server logs
        pass


def start_dummy_server() -> None:
    """Start dummy HTTP server for deployment platforms"""
    port = int(os.environ.get("PORT", 10000))
    server = HTTPServer(("0.0.0.0", port), DummyHandler)
    logger.info(f"🌐 Dummy server listening on port {port}")
    server.serve_forever()


def main() -> None:
    """Main function"""
    try:
        # Start dummy server in background thread
        threading.Thread(target=start_dummy_server, daemon=True).start()
        
        # Run the bot
        run_bot()
        
    except KeyboardInterrupt:
        logger.info("🛑 Bot stopped by user")
    except Exception as e:
        logger.error(f"💥 Fatal error: {e}")


if __name__ == "__main__":
    main()