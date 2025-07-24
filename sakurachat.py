import asyncio
import logging
import os
import random
import sys
import time
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from typing import Dict, Set, Optional

from telegram import (
    Update, 
    InlineKeyboardButton, 
    InlineKeyboardMarkup,
    BotCommand,
    Message
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

# Color formatter for better log readability
class ColoredFormatter(logging.Formatter):
    """Custom formatter with colors and emojis for better readability"""
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Check if we should use colors
        self.use_colors = (
            hasattr(sys.stderr, "isatty") and sys.stderr.isatty() or
            os.environ.get('FORCE_COLOR') == '1' or
            os.environ.get('TERM', '').lower() in ('xterm', 'xterm-color', 'xterm-256color', 'screen', 'screen-256color')
        )

    COLORS = {
        'DEBUG': '\x1b[36m',    # Cyan
        'INFO': '\x1b[32m',     # Green  
        'WARNING': '\x1b[33m',  # Yellow
        'ERROR': '\x1b[31m',    # Red
        'CRITICAL': '\x1b[35m', # Magenta
        'RESET': '\x1b[0m',     # Reset
        'BLUE': '\x1b[34m',     # Blue
        'PURPLE': '\x1b[35m',   # Purple
        'CYAN': '\x1b[36m',     # Cyan
        'YELLOW': '\x1b[33m',   # Yellow
        'GREEN': '\x1b[32m',    # Green
        'RED': '\x1b[31m',      # Red (alias for ERROR)
        'BOLD': '\x1b[1m',      # Bold
        'DIM': '\x1b[2m'        # Dim
    }

    def format(self, record):
        if not self.use_colors:
            return super().format(record)

        # Create a copy to avoid modifying the original
        formatted_record = logging.makeLogRecord(record.__dict__)

        # Get the basic formatted message
        message = super().format(formatted_record)

        # Apply colors to the entire message
        return self.colorize_full_message(message, record.levelname)

    def colorize_full_message(self, message, level):
        """Apply colors to the entire formatted message"""
        if not self.use_colors:
            return message
        
        color = self.COLORS.get(level, self.COLORS['RESET'])
        return f"{color}{message}{self.COLORS['RESET']}"

# Configure enhanced logging with colors
def setup_logging():
    """Setup colored logging with proper formatting"""
    try:
        # Create root logger
        root_logger = logging.getLogger()
        root_logger.setLevel(logging.DEBUG)
        
        # Clear existing handlers
        for handler in root_logger.handlers[:]:
            root_logger.removeHandler(handler)
        
        # Create console handler with colored formatter
        console_handler = logging.StreamHandler(sys.stderr)
        console_handler.setLevel(logging.INFO)
        
        # Create colored formatter
        colored_formatter = ColoredFormatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        console_handler.setFormatter(colored_formatter)
        
        # Add handler to root logger
        root_logger.addHandler(console_handler)
        
        # Get bot logger
        logger = logging.getLogger(__name__)
        logger.info("🎨 Colored logging system initialized successfully")
        return logger
        
    except Exception as e:
        print(f"❌ Failed to setup logging: {e}")
        # Fallback to basic logging
        logging.basicConfig(
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            level=logging.INFO
        )
        return logging.getLogger(__name__)

# Initialize logger
logger = setup_logging()

def extract_user_info(msg: Message):
    """Extract comprehensive user and chat information from message"""
    logger.debug("🔍 Extracting user information from message")
    
    try:
        u = msg.from_user
        c = msg.chat
        
        if not u or not c:
            logger.warning("⚠️ Missing user or chat information in message")
            return None
            
        info = {
            "user_id": u.id,
            "username": u.username or "No Username",
            "full_name": u.full_name or "Unknown User",
            "user_link": f"https://t.me/{u.username}" if u.username else "No User Link",
            "chat_id": c.id,
            "chat_type": c.type.value if hasattr(c.type, 'value') else str(c.type),
            "chat_title": c.title or c.first_name or "Unknown Chat",
            "chat_username": c.username or "No Username",
            "chat_link": f"https://t.me/{c.username}" if c.username else "No Chat Link",
            "group_id": c.id if c.type.value in ['group', 'supergroup'] else None,
            "group_name": c.title if c.type.value in ['group', 'supergroup'] else None,
            "group_link": f"https://t.me/{c.username}" if c.username and c.type.value in ['group', 'supergroup'] else "No Group Link"
        }
        
        # Log comprehensive user information
        logger.info(
            f"📑 USER INFO: {info['full_name']} (@{info['username']}) "
            f"[ID: {info['user_id']}] | User Link: {info['user_link']} | "
            f"Chat: {info['chat_title']} [ID: {info['chat_id']}] | "
            f"Chat Type: {info['chat_type']} | Chat Link: {info['chat_link']}"
        )
        
        if info['group_id']:
            logger.info(
                f"📢 GROUP INFO: Group ID: {info['group_id']} | "
                f"Group Name: {info['group_name']} | Group Link: {info['group_link']}"
            )
        
        return info
        
    except Exception as e:
        logger.error(f"❌ Error extracting user info: {e}")
        return None

# Configuration with robust validation
def load_config():
    """Load and validate configuration from environment variables"""
    logger.info("🔧 Loading configuration from environment variables")
    
    config = {}
    required_vars = {
        "BOT_TOKEN": os.getenv("BOT_TOKEN", ""),
        "GEMINI_API_KEY": os.getenv("GEMINI_API_KEY", ""),
        "OWNER_ID": os.getenv("OWNER_ID", "0")
    }
    
    optional_vars = {
        "SUPPORT_LINK": os.getenv("SUPPORT_LINK", "https://t.me/SoulMeetsHQ"),
        "UPDATE_LINK": os.getenv("UPDATE_LINK", "https://t.me/WorkGlows"),
        "GROUP_LINK": "https://t.me/SoulMeetsHQ",
        "RATE_LIMIT_SECONDS": float(os.getenv("RATE_LIMIT_SECONDS", "1.0")),
        "BROADCAST_DELAY": float(os.getenv("BROADCAST_DELAY", "0.03"))
    }
    
    # Validate required variables
    for key, value in required_vars.items():
        if not value or value == "0":
            logger.critical(f"❌ {key} not found or invalid in environment variables")
            raise ValueError(f"Missing required environment variable: {key}")
        config[key] = value
        logger.debug(f"✅ {key} loaded successfully")
    
    # Load optional variables
    for key, value in optional_vars.items():
        config[key] = value
        logger.debug(f"🔧 {key} set to: {value}")
    
    # Convert OWNER_ID to int
    try:
        config["OWNER_ID"] = int(config["OWNER_ID"])
        logger.info(f"👑 Owner ID set to: {config['OWNER_ID']}")
    except ValueError:
        logger.critical("❌ OWNER_ID must be a valid integer")
        raise ValueError("OWNER_ID must be a valid integer")
    
    logger.info("✅ Configuration loaded successfully")
    return config

# Load configuration
try:
    CONFIG = load_config()
    BOT_TOKEN = CONFIG["BOT_TOKEN"]
    GEMINI_API_KEY = CONFIG["GEMINI_API_KEY"]
    OWNER_ID = CONFIG["OWNER_ID"]
    SUPPORT_LINK = CONFIG["SUPPORT_LINK"]
    UPDATE_LINK = CONFIG["UPDATE_LINK"]
    GROUP_LINK = CONFIG["GROUP_LINK"]
    RATE_LIMIT_SECONDS = CONFIG["RATE_LIMIT_SECONDS"]
    BROADCAST_DELAY = CONFIG["BROADCAST_DELAY"]
except Exception as e:
    logger.critical(f"💥 Failed to load configuration: {e}")
    sys.exit(1)

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

# Initialize Gemini client with robust error handling
def initialize_gemini_client():
    """Initialize Gemini client with comprehensive error handling"""
    logger.info("🔮 Initializing Gemini AI client...")
    
    try:
        if not GEMINI_API_KEY:
            logger.error("❌ GEMINI_API_KEY is empty")
            return None
            
        client = genai.Client(api_key=GEMINI_API_KEY)
        logger.info("✅ Gemini client initialized successfully")
        
        # Test the client with a simple request
        logger.debug("🧪 Testing Gemini client connection...")
        test_response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents="Test connection"
        )
        logger.info("✅ Gemini client connection test successful")
        return client
        
    except Exception as e:
        logger.error(f"❌ Failed to initialize Gemini client: {e}")
        logger.warning("⚠️ Bot will continue with fallback responses only")
        return None

gemini_client = initialize_gemini_client()

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
    logger.debug("🎲 Getting fallback response")
    response = random.choice(RESPONSES)
    logger.info(f"💬 Fallback response selected: {response[:30]}...")
    return response


def get_error_response() -> str:
    """Get a random error response when something goes wrong"""
    logger.debug("⚠️ Getting error response")
    response = random.choice(ERROR)
    logger.warning(f"❌ Error response selected: {response[:30]}...")
    return response


def validate_config() -> bool:
    """Validate bot configuration"""
    logger.info("🔧 Validating bot configuration...")
    
    try:
        if not BOT_TOKEN:
            logger.error("❌ BOT_TOKEN not found in environment variables")
            return False
        if not GEMINI_API_KEY:
            logger.error("❌ GEMINI_API_KEY not found in environment variables")
            return False
        if not OWNER_ID:
            logger.error("❌ OWNER_ID not found in environment variables")
            return False
        
        logger.info("✅ Configuration validation successful")
        return True
        
    except Exception as e:
        logger.error(f"❌ Configuration validation failed: {e}")
        return False


def is_rate_limited(user_id: int) -> bool:
    """Check if user is rate limited"""
    try:
        current_time = time.time()
        last_response = user_last_response_time.get(user_id, 0)
        is_limited = current_time - last_response < RATE_LIMIT_SECONDS
        
        if is_limited:
            logger.debug(f"⏱️ User {user_id} is rate limited")
        
        return is_limited
        
    except Exception as e:
        logger.error(f"❌ Error checking rate limit for user {user_id}: {e}")
        return False


def update_user_response_time(user_id: int) -> None:
    """Update the last response time for user"""
    try:
        user_last_response_time[user_id] = time.time()
        logger.debug(f"⏰ Updated response time for user {user_id}")
    except Exception as e:
        logger.error(f"❌ Error updating response time for user {user_id}: {e}")


def should_respond_in_group(update: Update, bot_id: int) -> bool:
    """Determine if bot should respond in group chat"""
    try:
        user_message = update.message.text or update.message.caption or ""
        
        # Respond if message contains "sakura" (case insensitive)
        if "sakura" in user_message.lower():
            logger.info("🌸 Bot mentioned by name in group")
            return True
        
        # Respond if message is a reply to bot's message
        if (update.message.reply_to_message and 
            update.message.reply_to_message.from_user.id == bot_id):
            logger.info("💬 Message is reply to bot in group")
            return True
        
        logger.debug("🤐 Bot should not respond in this group message")
        return False
        
    except Exception as e:
        logger.error(f"❌ Error determining group response: {e}")
        return False


def track_user_and_chat(update: Update) -> None:
    """Track user and chat IDs for broadcasting"""
    try:
        user_info = extract_user_info(update.message)
        if not user_info:
            logger.warning("⚠️ Could not extract user info for tracking")
            return
            
        user_id = user_info["user_id"]
        chat_id = user_info["chat_id"]
        chat_type = user_info["chat_type"]
        
        if chat_type == "private":
            user_ids.add(user_id)
            logger.info(f"👤 User {user_id} ({user_info['full_name']}) tracked for broadcasting")
        elif chat_type in ['group', 'supergroup']:
            group_ids.add(chat_id)
            user_ids.add(user_id)
            logger.info(f"📢 Group {chat_id} ({user_info['chat_title']}) tracked for broadcasting")
        
        logger.debug(f"📊 Current stats: {len(user_ids)} users, {len(group_ids)} groups tracked")
        
    except Exception as e:
        logger.error(f"❌ Error tracking user and chat: {e}")


def get_user_mention(user) -> str:
    """Create user mention for HTML parsing using first name"""
    try:
        first_name = user.first_name or "Friend"
        mention = f'<a href="tg://user?id={user.id}">{first_name}</a>'
        logger.debug(f"🏷️ Created user mention for {first_name}")
        return mention
    except Exception as e:
        logger.error(f"❌ Error creating user mention: {e}")
        return "Friend"


async def get_gemini_response(user_message: str, user_name: str = "") -> str:
    """Get response from Gemini API with fallback responses"""
    logger.info(f"🤖 Getting Gemini response for message: {user_message[:50]}...")
    
    if not gemini_client:
        logger.warning("⚠️ Gemini client not available, using fallback")
        return get_fallback_response()
    
    try:
        prompt = f"{SAKURA_PROMPT}\n\nUser name: {user_name}\nUser message: {user_message}\n\nSakura's response:"
        
        logger.debug("🔮 Sending request to Gemini API...")
        response = gemini_client.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt
        )
        
        if response.text:
            logger.info(f"✅ Gemini response received: {response.text[:50]}...")
            return response.text.strip()
        else:
            logger.warning("⚠️ Empty response from Gemini, using fallback")
            return get_fallback_response()
            
    except Exception as e:
        logger.error(f"❌ Gemini API error: {e}")
        return get_error_response()


async def send_typing_action(context: ContextTypes.DEFAULT_TYPE, chat_id: int) -> None:
    """Send typing action to show bot is processing"""
    try:
        await context.bot.send_chat_action(chat_id=chat_id, action=ChatAction.TYPING)
        logger.debug(f"⌨️ Typing action sent to chat {chat_id}")
    except Exception as e:
        logger.error(f"❌ Error sending typing action to chat {chat_id}: {e}")


async def send_photo_action(context: ContextTypes.DEFAULT_TYPE, chat_id: int) -> None:
    """Send upload photo action"""
    try:
        await context.bot.send_chat_action(chat_id=chat_id, action=ChatAction.UPLOAD_PHOTO)
        logger.debug(f"📸 Photo upload action sent to chat {chat_id}")
    except Exception as e:
        logger.error(f"❌ Error sending photo action to chat {chat_id}: {e}")


async def send_sticker_action(context: ContextTypes.DEFAULT_TYPE, chat_id: int) -> None:
    """Send choosing sticker action"""
    try:
        await context.bot.send_chat_action(chat_id=chat_id, action=ChatAction.CHOOSE_STICKER)
        logger.debug(f"🎭 Sticker choosing action sent to chat {chat_id}")
    except Exception as e:
        logger.error(f"❌ Error sending sticker action to chat {chat_id}: {e}")


def create_start_keyboard(bot_username: str) -> InlineKeyboardMarkup:
    """Create inline keyboard for start command"""
    try:
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
        logger.debug("⌨️ Start command keyboard created successfully")
        return InlineKeyboardMarkup(keyboard)
    except Exception as e:
        logger.error(f"❌ Error creating start keyboard: {e}")
        return InlineKeyboardMarkup([])


def get_start_caption(user_mention: str) -> str:
    """Get caption text for start command with user mention"""
    try:
        caption = START_MESSAGES["caption"].format(user_mention=user_mention)
        logger.debug("📝 Start caption generated successfully")
        return caption
    except Exception as e:
        logger.error(f"❌ Error generating start caption: {e}")
        return "Hi! I'm Sakura Haruno 🌸"


def create_help_keyboard(user_id: int, expanded: bool = False) -> InlineKeyboardMarkup:
    """Create help command keyboard"""
    try:
        if expanded:
            button_text = HELP_MESSAGES["button_texts"]["minimize"]
        else:
            button_text = HELP_MESSAGES["button_texts"]["expand"]
        
        keyboard = [[InlineKeyboardButton(button_text, callback_data=f"help_expand_{user_id}")]]
        logger.debug(f"⌨️ Help keyboard created for user {user_id}, expanded: {expanded}")
        return InlineKeyboardMarkup(keyboard)
    except Exception as e:
        logger.error(f"❌ Error creating help keyboard: {e}")
        return InlineKeyboardMarkup([])


def get_help_text(user_mention: str, expanded: bool = False) -> str:
    """Get help text based on expansion state with user mention"""
    try:
        if expanded:
            text = HELP_MESSAGES["expanded"].format(user_mention=user_mention)
        else:
            text = HELP_MESSAGES["minimal"].format(user_mention=user_mention)
        
        logger.debug(f"📝 Help text generated, expanded: {expanded}")
        return text
    except Exception as e:
        logger.error(f"❌ Error generating help text: {e}")
        return "Help information is not available right now."


def create_broadcast_keyboard() -> InlineKeyboardMarkup:
    """Create broadcast target selection keyboard"""
    try:
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
        logger.debug(f"⌨️ Broadcast keyboard created - {len(user_ids)} users, {len(group_ids)} groups")
        return InlineKeyboardMarkup(keyboard)
    except Exception as e:
        logger.error(f"❌ Error creating broadcast keyboard: {e}")
        return InlineKeyboardMarkup([])


def get_broadcast_text() -> str:
    """Get broadcast command text"""
    try:
        text = BROADCAST_MESSAGES["select_target"].format(
            users_count=len(user_ids),
            groups_count=len(group_ids)
        )
        logger.debug("📝 Broadcast text generated successfully")
        return text
    except Exception as e:
        logger.error(f"❌ Error generating broadcast text: {e}")
        return "Broadcast feature is not available right now."


async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /start command"""
    logger.info("🚀 Start command received")
    
    try:
        user_info = extract_user_info(update.message)
        if user_info:
            logger.info(f"👋 Start command from: {user_info['full_name']} in {user_info['chat_title']}")
        
        track_user_and_chat(update)
        
        await send_photo_action(context, update.effective_chat.id)
        
        random_image = random.choice(SAKURA_IMAGES)
        keyboard = create_start_keyboard(context.bot.username)
        user_mention = get_user_mention(update.effective_user)
        caption = get_start_caption(user_mention)
        
        logger.info("📸 Sending start message with photo")
        await context.bot.send_photo(
            chat_id=update.effective_chat.id,
            photo=random_image,
            caption=caption,
            parse_mode=ParseMode.HTML,
            reply_markup=keyboard
        )
        
        logger.info("✅ Start command handled successfully")
        
    except Exception as e:
        logger.error(f"❌ Error in start command: {e}")
        try:
            await update.message.reply_text(get_error_response())
        except Exception as reply_error:
            logger.error(f"❌ Failed to send error response: {reply_error}")


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /help command"""
    logger.info("❓ Help command received")
    
    try:
        user_info = extract_user_info(update.message)
        if user_info:
            logger.info(f"💡 Help command from: {user_info['full_name']} in {user_info['chat_title']}")
        
        user_id = update.effective_user.id
        keyboard = create_help_keyboard(user_id, False)
        user_mention = get_user_mention(update.effective_user)
        help_text = get_help_text(user_mention, False)
        
        logger.info("📚 Sending help message")
        await update.message.reply_text(
            help_text,
            parse_mode=ParseMode.HTML,
            reply_markup=keyboard
        )
        
        logger.info("✅ Help command handled successfully")
        
    except Exception as e:
        logger.error(f"❌ Error in help command: {e}")
        try:
            await update.message.reply_text(get_error_response())
        except Exception as reply_error:
            logger.error(f"❌ Failed to send error response: {reply_error}")


async def help_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle help expand/minimize callbacks"""
    logger.info("🔄 Help callback received")
    
    try:
        query = update.callback_query
        await query.answer()
        
        callback_data = query.data
        user_id = int(callback_data.split('_')[2])
        
        logger.debug(f"🔍 Help callback from user {user_id}")
        
        if update.effective_user.id != user_id:
            logger.warning(f"⚠️ Unauthorized help callback attempt by user {update.effective_user.id}")
            await query.answer("Ye button tumhare liye nahi hai 😊", show_alert=True)
            return
        
        is_expanded = help_expanded.get(user_id, False)
        help_expanded[user_id] = not is_expanded
        
        keyboard = create_help_keyboard(user_id, not is_expanded)
        user_mention = get_user_mention(update.effective_user)
        help_text = get_help_text(user_mention, not is_expanded)
        
        logger.info(f"📝 Updating help message, expanded: {not is_expanded}")
        await query.edit_message_text(
            help_text,
            parse_mode=ParseMode.HTML,
            reply_markup=keyboard
        )
        
        logger.info("✅ Help callback handled successfully")
        
    except Exception as e:
        logger.error(f"❌ Error in help callback: {e}")


async def handle_sticker_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle sticker messages"""
    logger.info("🎭 Sticker message received")
    
    try:
        user_info = extract_user_info(update.message)
        if user_info:
            logger.info(f"🎭 Sticker from: {user_info['full_name']} in {user_info['chat_title']}")
            logger.info(f"💬 User sent sticker, Sakura responding with random sticker")
        
        await send_sticker_action(context, update.effective_chat.id)
        
        random_sticker = random.choice(SAKURA_STICKERS)
        chat_type = update.effective_chat.type
        
        # In groups, reply to the user's sticker when they replied to bot
        if (chat_type in ['group', 'supergroup'] and 
            update.message.reply_to_message and 
            update.message.reply_to_message.from_user.id == context.bot.id):
            logger.info("💬 Replying to sticker in group")
            await update.message.reply_sticker(sticker=random_sticker)
        else:
            # In private chats or regular stickers, send normally
            logger.info("🎭 Sending sticker response")
            await context.bot.send_sticker(
                chat_id=update.effective_chat.id,
                sticker=random_sticker
            )
        
        logger.info(f"✅ Sakura replied with sticker: {random_sticker}")
        
    except Exception as e:
        logger.error(f"❌ Error handling sticker message: {e}")


async def handle_text_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle text and media messages with AI response"""
    logger.info("💬 Text/media message received")
    
    try:
        user_info = extract_user_info(update.message)
        if user_info:
            logger.info(f"💬 Message from: {user_info['full_name']} in {user_info['chat_title']}")
        
        await send_typing_action(context, update.effective_chat.id)
        
        user_message = update.message.text or update.message.caption or "Media message"
        user_name = update.effective_user.first_name or ""
        
        logger.info(f"📝 User wrote to Sakura: {user_message}")
        
        # Get response from Gemini
        response = await get_gemini_response(user_message, user_name)
        
        # Send response
        logger.info(f"💬 Sakura replied to them: {response}")
        await update.message.reply_text(response)
        
        logger.info("✅ Text message handled successfully")
        
    except Exception as e:
        logger.error(f"❌ Error handling text message: {e}")
        try:
            await update.message.reply_text(get_error_response())
        except Exception as reply_error:
            logger.error(f"❌ Failed to send error response: {reply_error}")


async def handle_all_messages(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle all types of messages (text, stickers, voice, photos, etc.)"""
    logger.debug("📨 Processing incoming message")
    
    try:
        user_id = update.effective_user.id
        chat_type = update.effective_chat.type
        
        # Extract and log user info
        user_info = extract_user_info(update.message)
        
        # Track user and group IDs for broadcasting
        track_user_and_chat(update)
        
        # Check if owner is in broadcast mode
        if user_id == OWNER_ID and OWNER_ID in broadcast_mode:
            logger.info("📢 Owner in broadcast mode, executing broadcast")
            await execute_broadcast_direct(update, context, broadcast_mode[OWNER_ID])
            del broadcast_mode[OWNER_ID]
            return
        
        # Determine if bot should respond
        should_respond = True
        if chat_type in ['group', 'supergroup']:
            should_respond = should_respond_in_group(update, context.bot.id)
        
        if not should_respond:
            logger.debug("🤐 Bot should not respond to this message")
            return
        
        # Check rate limiting
        if is_rate_limited(user_id):
            logger.debug(f"⏱️ User {user_id} is rate limited, skipping response")
            return
        
        # Handle different message types
        if update.message.sticker:
            await handle_sticker_message(update, context)
        else:
            await handle_text_message(update, context)
        
        # Update response time after sending response
        update_user_response_time(user_id)
        
        logger.debug("✅ Message handling completed successfully")
        
    except Exception as e:
        logger.error(f"❌ Error handling message: {e}")
        try:
            if update.message and update.message.text:
                await update.message.reply_text(get_error_response())
        except Exception as reply_error:
            logger.error(f"❌ Failed to send error response: {reply_error}")


async def broadcast_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle broadcast command (owner only)"""
    logger.info("📢 Broadcast command received")
    
    try:
        if update.effective_user.id != OWNER_ID:
            logger.warning(f"⚠️ Non-owner {update.effective_user.id} attempted broadcast command")
            return
        
        user_info = extract_user_info(update.message)
        if user_info:
            logger.info(f"👑 Broadcast command from owner: {user_info['full_name']}")
        
        keyboard = create_broadcast_keyboard()
        broadcast_text = get_broadcast_text()
        
        logger.info(f"📊 Showing broadcast options - {len(user_ids)} users, {len(group_ids)} groups")
        await update.message.reply_text(
            broadcast_text,
            reply_markup=keyboard,
            parse_mode=ParseMode.HTML
        )
        
        logger.info("✅ Broadcast command handled successfully")
        
    except Exception as e:
        logger.error(f"❌ Error in broadcast command: {e}")


async def broadcast_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle broadcast target selection"""
    logger.info("🎯 Broadcast callback received")
    
    try:
        query = update.callback_query
        await query.answer()
        
        if query.from_user.id != OWNER_ID:
            logger.warning(f"⚠️ Non-owner {query.from_user.id} attempted broadcast callback")
            return
        
        logger.info(f"👑 Broadcast target selection: {query.data}")
        
        if query.data == "bc_users":
            broadcast_mode[OWNER_ID] = "users"
            await query.edit_message_text(
                BROADCAST_MESSAGES["ready_users"].format(count=len(user_ids)),
                parse_mode=ParseMode.HTML
            )
            logger.info(f"✅ Ready to broadcast to {len(user_ids)} users")
            
        elif query.data == "bc_groups":
            broadcast_mode[OWNER_ID] = "groups"
            await query.edit_message_text(
                BROADCAST_MESSAGES["ready_groups"].format(count=len(group_ids)),
                parse_mode=ParseMode.HTML
            )
            logger.info(f"✅ Ready to broadcast to {len(group_ids)} groups")
        
    except Exception as e:
        logger.error(f"❌ Error in broadcast callback: {e}")


async def execute_broadcast_direct(update: Update, context: ContextTypes.DEFAULT_TYPE, target_type: str) -> None:
    """Execute broadcast with the current message using forward/copy logic"""
    logger.info(f"🚀 Executing broadcast to {target_type}")
    
    try:
        if target_type == "users":
            target_list = [uid for uid in user_ids if uid != OWNER_ID]
            target_name = "users"
        elif target_type == "groups":
            target_list = list(group_ids)
            target_name = "groups"
        else:
            logger.error(f"❌ Invalid broadcast target type: {target_type}")
            return
        
        if not target_list:
            logger.warning(f"⚠️ No {target_name} available for broadcast")
            await update.message.reply_text(
                BROADCAST_MESSAGES["no_targets"].format(target_type=target_name)
            )
            return
        
        logger.info(f"📡 Starting broadcast to {len(target_list)} {target_name}")
        
        # Show initial status
        status_msg = await update.message.reply_text(
            BROADCAST_MESSAGES["progress"].format(count=len(target_list), target_type=target_name)
        )
        
        broadcast_count = 0
        failed_count = 0
        
        # Check if message is forwarded
        is_forwarded = update.message.forward_from or update.message.forward_from_chat
        
        # Broadcast the current message to all targets
        for i, target_id in enumerate(target_list, 1):
            try:
                if is_forwarded:
                    # If message is forwarded, use forward_message
                    await context.bot.forward_message(
                        chat_id=target_id,
                        from_chat_id=update.effective_chat.id,
                        message_id=update.message.message_id
                    )
                    logger.debug(f"📤 Message forwarded to {target_id}")
                else:
                    # If not forwarded, use copy_message
                    await context.bot.copy_message(
                        chat_id=target_id,
                        from_chat_id=update.effective_chat.id,
                        message_id=update.message.message_id
                    )
                    logger.debug(f"📤 Message copied to {target_id}")
                
                broadcast_count += 1
                
                # Log progress every 10 messages
                if i % 10 == 0:
                    logger.info(f"📊 Broadcast progress: {i}/{len(target_list)} ({target_name})")
                
                # Small delay to avoid rate limits
                await asyncio.sleep(BROADCAST_DELAY)
                
            except Exception as e:
                failed_count += 1
                logger.error(f"❌ Failed to broadcast to {target_id}: {e}")
        
        # Final status update
        logger.info(f"✅ Broadcast completed: {broadcast_count}/{len(target_list)} successful, {failed_count} failed")
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
        logger.error(f"❌ Broadcast error: {e}")
        try:
            await update.message.reply_text(
                BROADCAST_MESSAGES["failed"].format(error=str(e))
            )
        except Exception as reply_error:
            logger.error(f"❌ Failed to send broadcast error message: {reply_error}")


async def ping_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle ping command for everyone"""
    logger.info("🏓 Ping command received")
    
    try:
        user_info = extract_user_info(update.message)
        if user_info:
            logger.info(f"🏓 Ping from: {user_info['full_name']} in {user_info['chat_title']}")
        
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
        
        logger.info(f"✅ Ping command completed in {response_time}ms")
        
    except Exception as e:
        logger.error(f"❌ Error in ping command: {e}")


async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle errors"""
    logger.error(f"💥 Exception while handling an update: {context.error}")
    
    try:
        # Log additional context if available
        if update and hasattr(update, 'effective_user') and update.effective_user:
            logger.error(f"🔍 Error context - User: {update.effective_user.id}, Chat: {getattr(update.effective_chat, 'id', 'Unknown')}")
        
        # Try to extract more error details
        import traceback
        logger.error(f"📋 Full traceback: {traceback.format_exc()}")
        
    except Exception as log_error:
        logger.error(f"❌ Error in error handler: {log_error}")


async def setup_bot_commands(application: Application) -> None:
    """Setup bot commands menu"""
    logger.info("⚙️ Setting up bot commands menu...")
    
    try:
        bot_commands = [
            BotCommand("start", "🌸 Meet Sakura"),
            BotCommand("help", "💬 Short Guide"),
            BotCommand("ping", "🏓 Check Bot Status")
        ]
        
        await application.bot.set_my_commands(bot_commands)
        logger.info("✅ Bot commands menu set successfully")
        
        # Log bot info
        bot_info = await application.bot.get_me()
        logger.info(f"🤖 Bot info: @{bot_info.username} ({bot_info.first_name})")
        
    except Exception as e:
        logger.error(f"❌ Failed to set bot commands: {e}")


def setup_handlers(application: Application) -> None:
    """Setup all command and message handlers"""
    logger.info("🔧 Setting up message handlers...")
    
    try:
        # Command handlers
        application.add_handler(CommandHandler("start", start_command))
        application.add_handler(CommandHandler("help", help_command))
        application.add_handler(CommandHandler("broadcast", broadcast_command))
        application.add_handler(CommandHandler("ping", ping_command))
        logger.info("✅ Command handlers added")
        
        # Callback query handlers
        application.add_handler(CallbackQueryHandler(help_callback, pattern="^help_expand_"))
        application.add_handler(CallbackQueryHandler(broadcast_callback, pattern="^bc_"))
        logger.info("✅ Callback query handlers added")
        
        # Message handler for all message types
        application.add_handler(MessageHandler(
            filters.TEXT | filters.Sticker.ALL | filters.VOICE | filters.VIDEO_NOTE | 
            filters.PHOTO | filters.Document.ALL & ~filters.COMMAND, 
            handle_all_messages
        ))
        logger.info("✅ Message handlers added")
        
        # Error handler
        application.add_error_handler(error_handler)
        logger.info("✅ Error handler added")
        
        logger.info("🎯 All handlers setup completed successfully")
        
    except Exception as e:
        logger.error(f"❌ Error setting up handlers: {e}")
        raise


def run_bot() -> None:
    """Run the bot"""
    logger.info("🚀 Starting Sakura Bot...")
    
    try:
        if not validate_config():
            logger.critical("❌ Configuration validation failed, exiting")
            return
        
        # Create application
        logger.info("🔧 Creating Telegram application...")
        application = Application.builder().token(BOT_TOKEN).build()
        
        # Setup handlers
        setup_handlers(application)
        
        # Setup bot commands using post_init
        async def post_init(app):
            logger.info("🔄 Running post-initialization tasks...")
            await setup_bot_commands(app)
            logger.info("✅ Post-initialization completed")
            
        application.post_init = post_init
        
        logger.info("🌸 Sakura Bot is starting...")
        logger.info(f"👑 Owner ID: {OWNER_ID}")
        logger.info(f"⏱️ Rate limit: {RATE_LIMIT_SECONDS}s")
        logger.info(f"📡 Broadcast delay: {BROADCAST_DELAY}s")
        
        # Run the bot with polling
        logger.info("🔄 Starting polling...")
        application.run_polling(
            allowed_updates=Update.ALL_TYPES, 
            drop_pending_updates=True,
            close_loop=False
        )
        
    except KeyboardInterrupt:
        logger.info("🛑 Bot stopped by user (Ctrl+C)")
    except Exception as e:
        logger.critical(f"💥 Fatal error in run_bot: {e}")
        import traceback
        logger.critical(f"📋 Full traceback: {traceback.format_exc()}")


class DummyHandler(BaseHTTPRequestHandler):
    """Simple HTTP handler for keep-alive server"""
    
    def do_GET(self):
        try:
            self.send_response(200)
            self.send_header('Content-type', 'text/plain')
            self.end_headers()
            
            status_info = f"""
🌸 Sakura Bot Status 🌸

✅ Bot is running
👥 Tracked Users: {len(user_ids)}
📢 Tracked Groups: {len(group_ids)}
🤖 Gemini Client: {'✅ Active' if gemini_client else '❌ Inactive'}
⏰ Uptime: Running

Last updated: {time.strftime('%Y-%m-%d %H:%M:%S')}
            """
            
            self.wfile.write(status_info.encode('utf-8'))
            logger.debug("🌐 HTTP status request served")
            
        except Exception as e:
            logger.error(f"❌ Error in HTTP handler GET: {e}")

    def do_HEAD(self):
        try:
            self.send_response(200)
            self.send_header('Content-type', 'text/plain')
            self.end_headers()
            logger.debug("🌐 HTTP HEAD request served")
        except Exception as e:
            logger.error(f"❌ Error in HTTP handler HEAD: {e}")
    
    def log_message(self, format, *args):
        # Suppress HTTP server logs to avoid spam
        pass


def start_dummy_server() -> None:
    """Start dummy HTTP server for deployment platforms"""
    try:
        port = int(os.environ.get("PORT", 10000))
        server = HTTPServer(("0.0.0.0", port), DummyHandler)
        logger.info(f"🌐 HTTP keep-alive server starting on port {port}")
        server.serve_forever()
    except Exception as e:
        logger.error(f"❌ Error starting HTTP server: {e}")


def main() -> None:
    """Main function"""
    logger.info("🎬 Sakura Bot main function started")
    
    try:
        # Start dummy server in background thread
        logger.info("🌐 Starting HTTP server in background thread")
        server_thread = threading.Thread(target=start_dummy_server, daemon=True)
        server_thread.start()
        logger.info("✅ HTTP server thread started")
        
        # Run the bot
        run_bot()
        
    except KeyboardInterrupt:
        logger.info("🛑 Bot stopped by user")
    except Exception as e:
        logger.critical(f"💥 Fatal error in main: {e}")
        import traceback
        logger.critical(f"📋 Full traceback: {traceback.format_exc()}")
    finally:
        logger.info("🏁 Sakura Bot shutdown completed")


if __name__ == "__main__":
    main()