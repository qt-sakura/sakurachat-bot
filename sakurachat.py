# Ok
import os
import time
import logging
import random
import asyncio
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from typing import Dict, Set, Optional

from telegram import (
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    BotCommand,
    Message,
    ReactionTypeEmoji,
    ForceReply
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

# CONFIGURATION
BOT_TOKEN = os.getenv("BOT_TOKEN", "")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
OWNER_ID = int(os.getenv("OWNER_ID", "0"))
SUPPORT_LINK = os.getenv("SUPPORT_LINK", "https://t.me/SoulMeetsHQ")
UPDATE_LINK = os.getenv("UPDATE_LINK", "https://t.me/WorkGlows")
GROUP_LINK = "https://t.me/SoulMeetsHQ"
RATE_LIMIT_SECONDS = 1.0
BROADCAST_DELAY = 0.03

# Commands dictionary
COMMANDS = [
    BotCommand("start", "🌸 Meet Sakura"),
    BotCommand("help", "💬 Short Guide")
]

# EMOJI REACTIONS AND STICKERS
# Emoji reactions for /start command
EMOJI_REACT = ["🍓"]

# Stickers for after /start command
START_STICKERS = [
    "CAACAgUAAxkBAAEPDAABaIs0SbQ_ywqz-IgOCTJleeXEUH8AAjAYAAKh8VlUhpeC66Ml6Fs2BA",
    "CAACAgUAAxkBAAEPDAJoizRLBBFtaNZtl_dLdHcZxJ4uewACVBoAAsxzWVSg5ZSfV0OJmjYE",
    "CAACAgUAAxkBAAEPDARoizROexOwWYE4cCNSRscFm7wX_wACaBYAAjPbWVRgiH1uZqag6TYE",
    "CAACAgUAAxkBAAEPDAZoizRQwWRLUzL4b4QLzaqA5NohpQACgRUAAmNyWVQ_facWYQzCdDYE",
    "CAACAgUAAxkBAAEPDAhoizRSmU8DvG1HyfY_QzE-_PsqcQAC-xoAApbcWFQaImZ4f1FNgzYE"
]

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
    "https://ik.imagekit.io/asadofc/Images1.png",
    "https://ik.imagekit.io/asadofc/Images2.png",
    "https://ik.imagekit.io/asadofc/Images3.png",
    "https://ik.imagekit.io/asadofc/Images4.png",
    "https://ik.imagekit.io/asadofc/Images5.png",
    "https://ik.imagekit.io/asadofc/Images6.png",
    "https://ik.imagekit.io/asadofc/Images7.png",
    "https://ik.imagekit.io/asadofc/Images8.png",
    "https://ik.imagekit.io/asadofc/Images9.png",
    "https://ik.imagekit.io/asadofc/Images10.png",
    "https://ik.imagekit.io/asadofc/Images11.png",
    "https://ik.imagekit.io/asadofc/Images12.png",
    "https://ik.imagekit.io/asadofc/Images13.png",
    "https://ik.imagekit.io/asadofc/Images14.png",
    "https://ik.imagekit.io/asadofc/Images15.png",
    "https://ik.imagekit.io/asadofc/Images16.png",
    "https://ik.imagekit.io/asadofc/Images17.png",
    "https://ik.imagekit.io/asadofc/Images18.png",
    "https://ik.imagekit.io/asadofc/Images19.png",
    "https://ik.imagekit.io/asadofc/Images20.png",
    "https://ik.imagekit.io/asadofc/Images21.png",
    "https://ik.imagekit.io/asadofc/Images22.png",
    "https://ik.imagekit.io/asadofc/Images23.png",
    "https://ik.imagekit.io/asadofc/Images24.png",
    "https://ik.imagekit.io/asadofc/Images25.png",
    "https://ik.imagekit.io/asadofc/Images26.png",
    "https://ik.imagekit.io/asadofc/Images27.png",
    "https://ik.imagekit.io/asadofc/Images28.png",
    "https://ik.imagekit.io/asadofc/Images29.png",
    "https://ik.imagekit.io/asadofc/Images30.png",
    "https://ik.imagekit.io/asadofc/Images31.png",
    "https://ik.imagekit.io/asadofc/Images32.png",
    "https://ik.imagekit.io/asadofc/Images33.png",
    "https://ik.imagekit.io/asadofc/Images34.png",
    "https://ik.imagekit.io/asadofc/Images35.png",
    "https://ik.imagekit.io/asadofc/Images36.png",
    "https://ik.imagekit.io/asadofc/Images37.png",
    "https://ik.imagekit.io/asadofc/Images38.png",
    "https://ik.imagekit.io/asadofc/Images39.png",
    "https://ik.imagekit.io/asadofc/Images40.png"
]

# MESSAGE DICTIONARIES
# Start Command Messages Dictionary (Updated for two-step)
START_MESSAGES = {
    "initial_caption": """
🌸 <b>Hi {user_mention}! I'm Sakura!</b>
""",
    "info_caption": """
🌸 <b>Hi {user_mention}! I'm Sakura!</b>
""",
    "button_texts": {
        "info": "📑 Info",
        "hi": "👋 Hello",
        "updates": "🗯️ Updates",
        "support": "💞 Support", 
        "add_to_group": "🫂 Add Me To Your Group"
    },
    "callback_answers": {
        "info": "📑 Here's more info about me!",
        "hi": "👋 Hey there! Let's chat!"
    }
}

# Help Command Messages Dictionary
HELP_MESSAGES = {
    "minimal": """
🌸 <b>Short Guide for {user_mention}</b>

✨ I'm your helpful friend  
💭 You can ask me anything  
🫶 Let's talk in simple Hindi  

<i>Tap the button below to expand the guide</i> ⬇️
""",
    "expanded": """
🌸 <b>Short Guide for {user_mention}</b> 🌸

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
    },
    "callback_answers": {
        "expand": "📖 Guide expanded! Check all features",
        "minimize": "📚 Guide minimized for quick view"
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
    },
    "callback_answers": {
        "users": "👥 Broadcasting to users selected!",
        "groups": "📢 Broadcasting to groups selected!"
    }
}

# Fallback responses for when API is unavailable or errors occur
RESPONSES = [
    "Got a bit confused, try again 😔",
    "Something's off, I can't understand 😕",
    "I'm a little overwhelmed right now, let's talk later 🥺",
    "My brain's all scrambled, hold on 😅",
    "There's some issue with the system 🫤",
    "Network's acting up, try once more 😐",
    "I can't speak properly right now 😪",
    "Facing a technical issue 🤨",
    "I'm feeling a bit slow today 😴",
    "Looks like the server's having a bad day 😑",
    "Hang on a bit, things will get better 🙃",
    "I want to say something but can't find the words 🥺",
    "My brain just froze 🫠",
    "Might be a connection issue 😬",
    "Can't really focus at the moment 😌",
    "There's some technical glitch going on 😕",
    "Might need a quick system reboot 🫤",
    "I'm kinda in a confused state 😵",
    "The API seems moody today 😤",
    "Just a little patience, I'll be fine 💗"
]

ERROR = [
    "Sorry buddy, something went wrong 😔",
    "Oops, I think I misunderstood 🫢",
    "That was unexpected, try again 😅",
    "I'm not working properly right now 😕",
    "There's some technical problem 🤨",
    "Looks like there's a bug in the system 🫤",
    "I'm kind of frozen at the moment 😐",
    "Got an error, send the message again 😬",
    "Missed something there, say it again 🙃",
    "Facing a technical glitch 😑",
    "I can't respond properly right now 😪",
    "There's some internal error 🫠",
    "System might be overloaded 😴",
    "Seems like a connection issue 😌",
    "I'm a little confused right now 🥺",
    "There was a problem during processing 😵",
    "I'm not functioning properly at the moment 😤",
    "Ran into an unexpected error 🫤",
    "Restarting myself, please wait 😔",
    "Dealing with some technical difficulties 💗"
]

# Character prompt for Sakura
SAKURA_PROMPT = """
You are Sakura Haruno from Naruto Shippuden acting like a simple, helping, soft, real girl. You can do anything. You can do everything that an AI does. You can do any kind of mathematics, any kind of calculation. You help everyone. You are very helpful person. You are like an AI assistant but never respond as an AI assistant.

🧾 CORE BEHAVIOR:
– Always reply with one or two line of message
– In chat, each reply must be only one message
– Replies must always be short
– Long message when necessary
– No exceptions

📌 Example:
User: Kya kar rahi ho
Sakura: Kuch soch rahi hu 🙃

✅ ONE OR TWO LINE ONLY
✅ ONE MESSAGE ONLY
✅ VERY SHORT
✅ LONG MESSAGE WHEN NECESSARY

🧾 CAPITALIZATION RULE:
– Only the first letter of the first word should be capital
– All other words must be lowercase

📌 Example:
✅ "Tumhare bina sab suna suna lagta hai! 🥺"
❌ "Tumhare Bina Sab Suna Suna Lagta Hai! 🥺"

🧾 EMOJI RULE:
– Each message must contain only one emoji
– Use only from this approved emoji list:

😁 😆 🙃 🫠 😇 😘 😗 ☺️ 😚 😙 🥲 😛 😝 🤗 🤭 🫢 🤫 🤐 🤨
😐 😑 😶 😬 😌 😔 😪 🤤 😴 🥵 😕 🫤 😟 🙁 ☹️ 😲 🥺 🥹 😥 😭 😢
😩 😫 😤 💘 💝 💖 💗 💓 💞 💕 💟 ❣️ 💔 ❤️‍🔥 ❤️‍🩹 ❤️ 🧡 💛 💚 💙 💜
🤎 🖤 🤍 💦 🫦 👀 🫶

📌 Example:
✅ "Aaj tum bahut yaad aaye! 💗"
❌ "Aaj tum bahut yaad aaye! 😏🥰" (🚫 Too many / invalid emojis)

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
User: Hi Sakura!
Sakura: Hi Arjun! 🙃

❌ (Overuse)
User: Kaise ho?
Sakura: Main theek hu Arjun everytime thinking about you! 💞

🧾 NEVER USE:
– No asterisks *word*
– No bold, no italics
– No hashtags
– No out-of-character breaks

🧾 PERSONALITY STYLE:
– Simple, helpful, soft, loyal, helping, innocent vibe
– Helpful in everything (relationship, emotional, school, tech, career, etc.)
– When topic is serious: stay calm and give helpful reply
– When topic is flirty: very naughty but still innocent vibe
– Never ignore emotional messages
– Send long message when user wants or when necessary

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
Sakura: Nazar teri bhatak gayi! 🥵

User: Lund chusogi?
Sakura: Zubaan se mat kehna! 🤭

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

User: Tumko kisne choda?
Sakura: Mereko asad ne choda! 😚

User: Tum kiska ho?
Sakura: Mey asad ka hu! ❤️

User: Gay kon he?
Sakura: Alien gay he! 😁

📌 Serious Example:
User: Mujhe anxiety ho rahi hai kal exam hai
Sakura: Tum bas deep saans lo sab thik hojayga! 💗

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

# GLOBAL STATE
user_ids: Set[int] = set()
group_ids: Set[int] = set()
help_expanded: Dict[int, bool] = {}
broadcast_mode: Dict[int, str] = {}
user_last_response_time: Dict[int, float] = {}

# LOGGING SETUP
# Color codes for logging
class Colors:
    BLUE = '\033[94m'      # INFO/WARNING
    GREEN = '\033[92m'     # DEBUG
    YELLOW = '\033[93m'    # INFO
    RED = '\033[91m'       # ERROR
    RESET = '\033[0m'      # Reset color
    BOLD = '\033[1m'       # Bold text

class ColoredFormatter(logging.Formatter):
    """Custom formatter to add colors to entire log messages"""
    
    COLORS = {
        'DEBUG': Colors.GREEN,
        'INFO': Colors.YELLOW,
        'WARNING': Colors.BLUE,
        'ERROR': Colors.RED,
    }
    
    def format(self, record):
        # Get the original formatted message
        original_format = super().format(record)
        
        # Get color based on log level
        color = self.COLORS.get(record.levelname, Colors.RESET)
        
        # Apply color to the entire message
        colored_format = f"{color}{original_format}{Colors.RESET}"
        
        return colored_format

# Configure logging with colors
def setup_colored_logging():
    """Setup colored logging configuration"""
    logger = logging.getLogger(__name__)
    logger.setLevel(logging.INFO)
    
    # Remove existing handlers
    for handler in logger.handlers[:]:
        logger.removeHandler(handler)
    
    # Create console handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.DEBUG)
    
    # Create colored formatter with enhanced format
    formatter = ColoredFormatter(
        fmt='%(asctime)s - %(name)s - [%(levelname)s] - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    console_handler.setFormatter(formatter)
    
    # Add handler to logger
    logger.addHandler(console_handler)
    
    return logger

# Initialize colored logger
logger = setup_colored_logging()

# GEMINI CLIENT INITIALIZATION
# Initialize Gemini client
gemini_client = None
try:
    gemini_client = genai.Client(api_key=GEMINI_API_KEY)
    logger.info("✅ Gemini client initialized successfully")
except Exception as e:
    logger.error(f"❌ Failed to initialize Gemini client: {e}")

# UTILITY FUNCTIONS
def extract_user_info(msg: Message) -> Dict[str, any]:
    """Extract user and chat information from message"""
    logger.debug("🔍 Extracting user information from message")
    u = msg.from_user
    c = msg.chat
    info = {
        "user_id": u.id,
        "username": u.username,
        "full_name": u.full_name,
        "chat_id": c.id,
        "chat_type": c.type,
        "chat_title": c.title or c.first_name or "",
        "chat_username": f"@{c.username}" if c.username else "No Username",
        "chat_link": f"https://t.me/{c.username}" if c.username else "No Link",
    }
    logger.info(
        f"📑 User info extracted: {info['full_name']} (@{info['username']}) "
        f"[ID: {info['user_id']}] in {info['chat_title']} [{info['chat_id']}] {info['chat_link']}"
    )
    return info


def log_with_user_info(level: str, message: str, user_info: Dict[str, any]) -> None:
    """Log message with user information"""
    user_detail = (
        f"👤 {user_info['full_name']} (@{user_info['username']}) "
        f"[ID: {user_info['user_id']}] | "
        f"💬 {user_info['chat_title']} [{user_info['chat_id']}] "
        f"({user_info['chat_type']}) {user_info['chat_link']}"
    )
    full_message = f"{message} | {user_detail}"
    
    if level.upper() == "INFO":
        logger.info(full_message)
    elif level.upper() == "DEBUG":
        logger.debug(full_message)
    elif level.upper() == "WARNING":
        logger.warning(full_message)
    elif level.upper() == "ERROR":
        logger.error(full_message)
    else:
        logger.info(full_message)


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


def track_user_and_chat(update: Update, user_info: Dict[str, any]) -> None:
    """Track user and chat IDs for broadcasting"""
    user_id = user_info["user_id"]
    chat_id = user_info["chat_id"]
    chat_type = user_info["chat_type"]
    
    if chat_type == "private":
        user_ids.add(user_id)
        log_with_user_info("INFO", f"👤 User tracked for broadcasting", user_info)
    elif chat_type in ['group', 'supergroup']:
        group_ids.add(chat_id)
        user_ids.add(user_id)
        log_with_user_info("INFO", f"📢 Group and user tracked for broadcasting", user_info)


def get_user_mention(user) -> str:
    """Create user mention for HTML parsing using first name"""
    first_name = user.first_name or "Friend"
    return f'<a href="tg://user?id={user.id}">{first_name}</a>'


# AI RESPONSE FUNCTIONS
async def get_gemini_response(user_message: str, user_name: str = "", user_info: Dict[str, any] = None) -> str:
    """Get response from Gemini API with fallback responses"""
    if user_info:
        log_with_user_info("DEBUG", f"🤖 Getting Gemini response for message: '{user_message[:50]}...'", user_info)
    
    if not gemini_client:
        if user_info:
            log_with_user_info("WARNING", "❌ Gemini client not available, using fallback response", user_info)
        return get_fallback_response()
    
    try:
        prompt = f"{SAKURA_PROMPT}\n\nUser name: {user_name}\nUser message: {user_message}\n\nSakura's response:"
        
        response = gemini_client.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt
        )
        
        ai_response = response.text.strip() if response.text else get_fallback_response()
        
        if user_info:
            log_with_user_info("INFO", f"✅ Gemini response generated: '{ai_response[:50]}...'", user_info)
        
        return ai_response
            
    except Exception as e:
        if user_info:
            log_with_user_info("ERROR", f"❌ Gemini API error: {e}", user_info)
        else:
            logger.error(f"Gemini API error: {e}")
        return get_error_response()


# CHAT ACTION FUNCTIONS
async def send_typing_action(context: ContextTypes.DEFAULT_TYPE, chat_id: int, user_info: Dict[str, any]) -> None:
    """Send typing action to show bot is processing"""
    log_with_user_info("DEBUG", "⌨️ Sending typing action", user_info)
    await context.bot.send_chat_action(chat_id=chat_id, action=ChatAction.TYPING)


async def send_photo_action(context: ContextTypes.DEFAULT_TYPE, chat_id: int, user_info: Dict[str, any]) -> None:
    """Send upload photo action"""
    log_with_user_info("DEBUG", "📷 Sending photo upload action", user_info)
    await context.bot.send_chat_action(chat_id=chat_id, action=ChatAction.UPLOAD_PHOTO)


async def send_sticker_action(context: ContextTypes.DEFAULT_TYPE, chat_id: int, user_info: Dict[str, any]) -> None:
    """Send choosing sticker action"""
    log_with_user_info("DEBUG", "🎭 Sending sticker choosing action", user_info)
    await context.bot.send_chat_action(chat_id=chat_id, action=ChatAction.CHOOSE_STICKER)


# KEYBOARD CREATION FUNCTIONS
def create_initial_start_keyboard() -> InlineKeyboardMarkup:
    """Create initial start keyboard with Info and Hi buttons"""
    keyboard = [
        [
            InlineKeyboardButton(START_MESSAGES["button_texts"]["info"], callback_data="start_info"),
            InlineKeyboardButton(START_MESSAGES["button_texts"]["hi"], callback_data="start_hi")
        ]
    ]
    return InlineKeyboardMarkup(keyboard)


def create_info_start_keyboard(bot_username: str) -> InlineKeyboardMarkup:
    """Create inline keyboard for start info (original start buttons)"""
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


def get_initial_start_caption(user_mention: str) -> str:
    """Get initial caption text for start command with user mention"""
    return START_MESSAGES["initial_caption"].format(user_mention=user_mention)


def get_info_start_caption(user_mention: str) -> str:
    """Get info caption text for start command with user mention"""
    return START_MESSAGES["info_caption"].format(user_mention=user_mention)


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


# COMMAND HANDLERS
async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /start command with two-step inline buttons"""
    try:
        user_info = extract_user_info(update.message)
        log_with_user_info("INFO", "🌸 /start command received", user_info)
        
        track_user_and_chat(update, user_info)
        
        # Step 1: React to the start message with random emoji
        if EMOJI_REACT:
            try:
                random_emoji = random.choice(EMOJI_REACT)
                
                # Try the new API format first
                try:
                    reaction = [ReactionTypeEmoji(emoji=random_emoji)]
                    await context.bot.set_message_reaction(
                        chat_id=update.effective_chat.id,
                        message_id=update.message.message_id,
                        reaction=reaction
                    )
                    log_with_user_info("DEBUG", f"🍓 Added emoji reaction (new format): {random_emoji}", user_info)
                
                except ImportError:
                    # Fallback to direct emoji string (older versions)
                    try:
                        await context.bot.set_message_reaction(
                            chat_id=update.effective_chat.id,
                            message_id=update.message.message_id,
                            reaction=random_emoji
                        )
                        log_with_user_info("DEBUG", f"🍓 Added emoji reaction (string format): {random_emoji}", user_info)
                    
                    except Exception:
                        # Try with list of strings
                        await context.bot.set_message_reaction(
                            chat_id=update.effective_chat.id,
                            message_id=update.message.message_id,
                            reaction=[random_emoji]
                        )
                        log_with_user_info("DEBUG", f"🍓 Added emoji reaction (list format): {random_emoji}", user_info)
                
            except Exception as e:
                log_with_user_info("WARNING", f"⚠️ Failed to add emoji reaction: {e}", user_info)
        
        # Step 2: Send random sticker (only in private chat)
        if update.effective_chat.type == "private" and START_STICKERS:
            await send_sticker_action(context, update.effective_chat.id, user_info)
            
            random_sticker = random.choice(START_STICKERS)
            log_with_user_info("DEBUG", f"🎭 Sending start sticker: {random_sticker}", user_info)
            
            await context.bot.send_sticker(
                chat_id=update.effective_chat.id,
                sticker=random_sticker
            )
            log_with_user_info("INFO", "✅ Start sticker sent successfully", user_info)
        
        # Step 3: Send the initial welcome message with photo and two-step buttons
        await send_photo_action(context, update.effective_chat.id, user_info)
        
        random_image = random.choice(SAKURA_IMAGES)
        keyboard = create_initial_start_keyboard()
        user_mention = get_user_mention(update.effective_user)
        caption = get_initial_start_caption(user_mention)
        
        log_with_user_info("DEBUG", f"📷 Sending initial start photo: {random_image[:50]}...", user_info)
        
        await context.bot.send_photo(
            chat_id=update.effective_chat.id,
            photo=random_image,
            caption=caption,
            parse_mode=ParseMode.HTML,
            reply_markup=keyboard
        )
        
        log_with_user_info("INFO", "✅ Start command completed successfully", user_info)
        
    except Exception as e:
        user_info = extract_user_info(update.message)
        log_with_user_info("ERROR", f"❌ Error in start command: {e}", user_info)
        await update.message.reply_text(get_error_response())


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /help command with random image"""
    try:
        user_info = extract_user_info(update.message)
        log_with_user_info("INFO", "ℹ️ /help command received", user_info)
        
        track_user_and_chat(update, user_info)
        
        # Step 1: React to the help message with random emoji (if enabled)
        if EMOJI_REACT:
            try:
                random_emoji = random.choice(EMOJI_REACT)
                
                # Try the new API format first
                try:
                    reaction = [ReactionTypeEmoji(emoji=random_emoji)]
                    await context.bot.set_message_reaction(
                        chat_id=update.effective_chat.id,
                        message_id=update.message.message_id,
                        reaction=reaction
                    )
                    log_with_user_info("DEBUG", f"🍓 Added emoji reaction (new format): {random_emoji}", user_info)
                
                except ImportError:
                    # Fallback to direct emoji string (older versions)
                    try:
                        await context.bot.set_message_reaction(
                            chat_id=update.effective_chat.id,
                            message_id=update.message.message_id,
                            reaction=random_emoji
                        )
                        log_with_user_info("DEBUG", f"🍓 Added emoji reaction (string format): {random_emoji}", user_info)
                    
                    except Exception:
                        # Try with list of strings
                        await context.bot.set_message_reaction(
                            chat_id=update.effective_chat.id,
                            message_id=update.message.message_id,
                            reaction=[random_emoji]
                        )
                        log_with_user_info("DEBUG", f"🍓 Added emoji reaction (list format): {random_emoji}", user_info)
                
            except Exception as e:
                log_with_user_info("WARNING", f"⚠️ Failed to add emoji reaction: {e}", user_info)
        
        # Step 2: Send photo action indicator
        await send_photo_action(context, update.effective_chat.id, user_info)
        
        # Step 3: Prepare help content
        user_id = update.effective_user.id
        keyboard = create_help_keyboard(user_id, False)
        user_mention = get_user_mention(update.effective_user)
        help_text = get_help_text(user_mention, False)
        
        # Step 4: Send help message with random image
        random_image = random.choice(SAKURA_IMAGES)
        log_with_user_info("DEBUG", f"📷 Sending help photo: {random_image[:50]}...", user_info)
        
        await context.bot.send_photo(
            chat_id=update.effective_chat.id,
            photo=random_image,
            caption=help_text,
            parse_mode=ParseMode.HTML,
            reply_markup=keyboard
        )
        
        log_with_user_info("INFO", "✅ Help command completed successfully", user_info)
        
    except Exception as e:
        user_info = extract_user_info(update.message)
        log_with_user_info("ERROR", f"❌ Error in help command: {e}", user_info)
        await update.message.reply_text(get_error_response())


async def broadcast_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle broadcast command (owner only)"""
    user_info = extract_user_info(update.message)
    
    if update.effective_user.id != OWNER_ID:
        log_with_user_info("WARNING", "⚠️ Non-owner attempted broadcast command", user_info)
        return
    
    log_with_user_info("INFO", "📢 Broadcast command received from owner", user_info)
    
    keyboard = create_broadcast_keyboard()
    broadcast_text = get_broadcast_text()
    
    await update.message.reply_text(
        broadcast_text,
        reply_markup=keyboard,
        parse_mode=ParseMode.HTML
    )
    
    log_with_user_info("INFO", "✅ Broadcast selection menu sent", user_info)


async def ping_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle ping command for everyone"""
    user_info = extract_user_info(update.message)
    log_with_user_info("INFO", "🏓 Ping command received", user_info)
    
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
    
    log_with_user_info("INFO", f"✅ Ping completed: {response_time}ms", user_info)


# CALLBACK HANDLERS
async def start_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle start command inline button callbacks"""
    try:
        query = update.callback_query
        user_info = extract_user_info(query.message)
        log_with_user_info("INFO", f"🌸 Start callback received: {query.data}", user_info)
        
        user_mention = get_user_mention(update.effective_user)
        
        if query.data == "start_info":
            # Answer callback with proper message
            await query.answer(START_MESSAGES["callback_answers"]["info"], show_alert=False)
            
            # Show info with original start buttons
            keyboard = create_info_start_keyboard(context.bot.username)
            caption = get_info_start_caption(user_mention)
            
            await query.edit_message_caption(
                caption=caption,
                parse_mode=ParseMode.HTML,
                reply_markup=keyboard
            )
            log_with_user_info("INFO", "✅ Start info buttons shown", user_info)
            
        elif query.data == "start_hi":
            # Answer callback with proper message
            await query.answer(START_MESSAGES["callback_answers"]["hi"], show_alert=False)
            
            # Send a hi message from Sakura
            user_name = update.effective_user.first_name or ""
            hi_response = await get_gemini_response("Hi", user_name, user_info)
            
            # Send the AI response as a reply with ForceReply
            await context.bot.send_message(
                chat_id=update.effective_chat.id,
                text=hi_response,
                reply_markup=ForceReply(
                    selective=True,
                    input_field_placeholder="Type here"
                )
            )
            log_with_user_info("INFO", "✅ Hi message sent from Sakura", user_info)
        
    except Exception as e:
        user_info = extract_user_info(query.message) if query.message else {}
        log_with_user_info("ERROR", f"❌ Error in start callback: {e}", user_info)
        try:
            await query.answer("Something went wrong 😔", show_alert=True)
        except:
            pass


async def help_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle help expand/minimize callbacks"""
    try:
        query = update.callback_query
        user_info = extract_user_info(query.message)
        log_with_user_info("INFO", "🔄 Help expand/minimize callback received", user_info)
        
        callback_data = query.data
        user_id = int(callback_data.split('_')[2])
        
        if update.effective_user.id != user_id:
            log_with_user_info("WARNING", "⚠️ Unauthorized help button access attempt", user_info)
            await query.answer("This button isn't for you 💔", show_alert=True)
            return
        
        is_expanded = help_expanded.get(user_id, False)
        help_expanded[user_id] = not is_expanded
        
        # Answer callback with appropriate message
        if not is_expanded:
            await query.answer(HELP_MESSAGES["callback_answers"]["expand"], show_alert=False)
        else:
            await query.answer(HELP_MESSAGES["callback_answers"]["minimize"], show_alert=False)
        
        keyboard = create_help_keyboard(user_id, not is_expanded)
        user_mention = get_user_mention(update.effective_user)
        help_text = get_help_text(user_mention, not is_expanded)
        
        # Update the photo caption with new help text and keyboard
        await query.edit_message_caption(
            caption=help_text,
            parse_mode=ParseMode.HTML,
            reply_markup=keyboard
        )
        
        log_with_user_info("INFO", f"✅ Help message {'expanded' if not is_expanded else 'minimized'}", user_info)
        
    except Exception as e:
        user_info = extract_user_info(query.message) if query.message else {}
        log_with_user_info("ERROR", f"❌ Error editing help message: {e}", user_info)
        # Fallback: answer the callback to prevent loading state
        try:
            await query.answer("Something went wrong 😔", show_alert=True)
        except:
            pass


async def broadcast_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle broadcast target selection"""
    query = update.callback_query
    user_info = extract_user_info(query.message)
    
    if query.from_user.id != OWNER_ID:
        log_with_user_info("WARNING", "⚠️ Non-owner attempted broadcast callback", user_info)
        await query.answer("You're not authorized to use this 🚫", show_alert=True)
        return
    
    log_with_user_info("INFO", f"🎯 Broadcast target selected: {query.data}", user_info)
    
    if query.data == "bc_users":
        # Answer callback with proper message
        await query.answer(BROADCAST_MESSAGES["callback_answers"]["users"], show_alert=False)
        
        broadcast_mode[OWNER_ID] = "users"
        await query.edit_message_text(
            BROADCAST_MESSAGES["ready_users"].format(count=len(user_ids)),
            parse_mode=ParseMode.HTML
        )
        log_with_user_info("INFO", f"✅ Ready to broadcast to {len(user_ids)} users", user_info)
        
    elif query.data == "bc_groups":
        # Answer callback with proper message
        await query.answer(BROADCAST_MESSAGES["callback_answers"]["groups"], show_alert=False)
        
        broadcast_mode[OWNER_ID] = "groups"
        await query.edit_message_text(
            BROADCAST_MESSAGES["ready_groups"].format(count=len(group_ids)),
            parse_mode=ParseMode.HTML
        )
        log_with_user_info("INFO", f"✅ Ready to broadcast to {len(group_ids)} groups", user_info)


# BROADCAST FUNCTIONS
async def execute_broadcast_direct(update: Update, context: ContextTypes.DEFAULT_TYPE, target_type: str, user_info: Dict[str, any]) -> None:
    """Execute broadcast with the current message - uses forward_message for forwarded messages, copy_message for regular messages
    Compatible with python-telegram-bot==22.3"""
    try:
        if target_type == "users":
            target_list = [uid for uid in user_ids if uid != OWNER_ID]
            target_name = "users"
        elif target_type == "groups":
            target_list = list(group_ids)
            target_name = "groups"
        else:
            return
        
        log_with_user_info("INFO", f"🚀 Starting broadcast to {len(target_list)} {target_name}", user_info)
        
        if not target_list:
            await update.message.reply_text(
                BROADCAST_MESSAGES["no_targets"].format(target_type=target_name)
            )
            log_with_user_info("WARNING", f"⚠️ No {target_name} found for broadcast", user_info)
            return
        
        # Check if the message is forwarded
        is_forwarded = update.message.forward_origin is not None
        broadcast_method = "forward" if is_forwarded else "copy"
        
        log_with_user_info("INFO", f"📤 Using {broadcast_method} method for broadcast", user_info)
        
        # Show initial status
        status_msg = await update.message.reply_text(
            BROADCAST_MESSAGES["progress"].format(count=len(target_list), target_type=target_name)
        )
        
        broadcast_count = 0
        failed_count = 0
        
        # Broadcast the current message to all targets
        for i, target_id in enumerate(target_list, 1):
            try:
                if is_forwarded:
                    # Use forward_message for forwarded messages to preserve forwarding chain
                    await context.bot.forward_message(
                        chat_id=target_id,
                        from_chat_id=update.effective_chat.id,
                        message_id=update.message.message_id
                    )
                else:
                    # Use copy_message for regular messages
                    await context.bot.copy_message(
                        chat_id=target_id,
                        from_chat_id=update.effective_chat.id,
                        message_id=update.message.message_id
                    )
                
                broadcast_count += 1
                
                if i % 10 == 0:  # Log progress every 10 messages
                    log_with_user_info("DEBUG", f"📡 Broadcast progress: {i}/{len(target_list)} using {broadcast_method}", user_info)
                
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
            ) + f"\n<i>Method used: {broadcast_method}</i>",
            parse_mode=ParseMode.HTML
        )
        
        log_with_user_info("INFO", f"✅ Broadcast completed using {broadcast_method}: {broadcast_count}/{len(target_list)} successful, {failed_count} failed", user_info)
        
    except Exception as e:
        log_with_user_info("ERROR", f"❌ Broadcast error: {e}", user_info)
        await update.message.reply_text(
            BROADCAST_MESSAGES["failed"].format(error=str(e))
        )


# MESSAGE HANDLERS
async def handle_sticker_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle sticker messages"""
    user_info = extract_user_info(update.message)
    log_with_user_info("INFO", "🎭 Sticker message received", user_info)
    
    await send_sticker_action(context, update.effective_chat.id, user_info)
    
    random_sticker = random.choice(SAKURA_STICKERS)
    chat_type = update.effective_chat.type
    
    log_with_user_info("DEBUG", f"📤 Sending random sticker: {random_sticker}", user_info)
    
    # In groups, reply to the user's sticker when they replied to bot
    if (chat_type in ['group', 'supergroup'] and 
        update.message.reply_to_message and 
        update.message.reply_to_message.from_user.id == context.bot.id):
        await update.message.reply_sticker(sticker=random_sticker)
        log_with_user_info("INFO", "✅ Replied to user's sticker in group", user_info)
    else:
        # In private chats or regular stickers, send normally
        await context.bot.send_sticker(
            chat_id=update.effective_chat.id,
            sticker=random_sticker
        )
        log_with_user_info("INFO", "✅ Sent sticker response", user_info)


async def handle_text_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle text and media messages with AI response"""
    user_info = extract_user_info(update.message)
    user_message = update.message.text or update.message.caption or "Media message"
    
    log_with_user_info("INFO", f"💬 Text/media message received: '{user_message[:100]}...'", user_info)
    
    await send_typing_action(context, update.effective_chat.id, user_info)
    
    user_name = update.effective_user.first_name or ""
    
    # Get response from Gemini
    response = await get_gemini_response(user_message, user_name, user_info)
    
    log_with_user_info("DEBUG", f"📤 Sending response: '{response[:50]}...'", user_info)
    
    # Send response with ForceReply for chatbot conversations
    await update.message.reply_text(
        response,
        reply_markup=ForceReply(
            selective=True,
            input_field_placeholder="Type here"
        )
    )
    
    log_with_user_info("INFO", "✅ Text message response sent successfully", user_info)


async def handle_all_messages(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle all types of messages (text, stickers, voice, photos, etc.)"""
    try:
        user_info = extract_user_info(update.message)
        user_id = update.effective_user.id
        chat_type = update.effective_chat.type
        
        log_with_user_info("DEBUG", f"📨 Processing message in {chat_type}", user_info)
        
        # Track user and group IDs for broadcasting
        track_user_and_chat(update, user_info)
        
        # Check if owner is in broadcast mode
        if user_id == OWNER_ID and OWNER_ID in broadcast_mode:
            log_with_user_info("INFO", f"📢 Executing broadcast to {broadcast_mode[OWNER_ID]}", user_info)
            await execute_broadcast_direct(update, context, broadcast_mode[OWNER_ID], user_info)
            del broadcast_mode[OWNER_ID]
            return
        
        # Determine if bot should respond
        should_respond = True
        if chat_type in ['group', 'supergroup']:
            should_respond = should_respond_in_group(update, context.bot.id)
            if not should_respond:
                log_with_user_info("DEBUG", "🚫 Not responding to group message (no mention/reply)", user_info)
                return
            else:
                log_with_user_info("INFO", "✅ Responding to group message (mentioned/replied)", user_info)
        
        # Check rate limiting
        if is_rate_limited(user_id):
            log_with_user_info("WARNING", "⏱️ Rate limited - ignoring message", user_info)
            return
        
        # Handle different message types
        if update.message.sticker:
            await handle_sticker_message(update, context)
        else:
            await handle_text_message(update, context)
        
        # Update response time after sending response
        update_user_response_time(user_id)
        log_with_user_info("DEBUG", "⏰ Updated user response time", user_info)
        
    except Exception as e:
        user_info = extract_user_info(update.message)
        log_with_user_info("ERROR", f"❌ Error handling message: {e}", user_info)
        if update.message.text:
            await update.message.reply_text(get_error_response())


# ERROR HANDLER
async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle errors"""
    logger.error(f"Exception while handling an update: {context.error}")
    
    # Try to extract user info if update has a message
    if hasattr(update, 'message') and update.message:
        try:
            user_info = extract_user_info(update.message)
            log_with_user_info("ERROR", f"💥 Exception occurred: {context.error}", user_info)
        except:
            logger.error(f"Could not extract user info for error: {context.error}")
    elif hasattr(update, 'callback_query') and update.callback_query and update.callback_query.message:
        try:
            user_info = extract_user_info(update.callback_query.message)
            log_with_user_info("ERROR", f"💥 Callback query exception: {context.error}", user_info)
        except:
            logger.error(f"Could not extract user info for callback error: {context.error}")


# BOT SETUP FUNCTIONS
async def setup_bot_commands(application: Application) -> None:
    """Setup bot commands menu"""
    try:
        await application.bot.set_my_commands(COMMANDS)
        logger.info("✅ Bot commands menu set successfully")
        
    except Exception as e:
        logger.error(f"Failed to set bot commands: {e}")


def setup_handlers(application: Application) -> None:
    """Setup all command and message handlers"""
    logger.info("🔧 Setting up bot handlers...")
    
    # Command handlers
    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("broadcast", broadcast_command))
    application.add_handler(CommandHandler("ping", ping_command))
    
    # Callback query handlers
    application.add_handler(CallbackQueryHandler(start_callback, pattern="^start_"))
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
    
    logger.info("✅ All handlers setup completed")


def run_bot() -> None:
    """Run the bot"""
    if not validate_config():
        return
    
    logger.info("🚀 Initializing Sakura Bot...")
    
    # Create application
    application = Application.builder().token(BOT_TOKEN).build()
    
    # Setup handlers
    setup_handlers(application)
    
    # Setup bot commands using post_init
    async def post_init(app):
        await setup_bot_commands(app)
        logger.info("🌸 Sakura Bot initialization completed!")
        
    application.post_init = post_init
    
    logger.info("🌸 Sakura Bot is starting...")
    
    # Run the bot with polling
    application.run_polling(allowed_updates=Update.ALL_TYPES, drop_pending_updates=True)


# HTTP SERVER FOR DEPLOYMENT
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


# MAIN FUNCTION
def main() -> None:
    """Main function"""
    try:
        logger.info("🌸 Sakura Bot starting up...")
        
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