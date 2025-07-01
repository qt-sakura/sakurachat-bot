import os
import logging
import asyncio
import random
import requests
import json
from google import genai
from google.genai import types
from datetime import datetime

# ─── Imports for Dummy HTTP Server ──────────────────────────────────────────
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer

# ── Enhanced Logging setup with colors ───────────────────────────────────────
class ColoredFormatter(logging.Formatter):
    """Custom formatter with colors and emojis for better readability"""
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Check if we should use colors
        import os
        import sys
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

        # Color based on log level
        level_color = self.COLORS.get(level, self.COLORS['RESET'])

        # Apply level-based coloring to the entire message
        if level == 'ERROR' or level == 'CRITICAL':
            return f"{self.COLORS['ERROR']}{self.COLORS['BOLD']}{message}{self.COLORS['RESET']}"
        elif level == 'WARNING':
            return f"{self.COLORS['YELLOW']}{message}{self.COLORS['RESET']}"
        elif level == 'INFO':
            # For INFO messages, use subtle coloring
            if any(word in message for word in ['Bot', 'Sakura', 'startup', 'connected', 'Success']):
                return f"{self.COLORS['GREEN']}{message}{self.COLORS['RESET']}"
            elif any(word in message for word in ['API', 'HTTP', 'Gemini', 'Telegram']):
                return f"{self.COLORS['BLUE']}{message}{self.COLORS['RESET']}"
            elif any(word in message for word in ['User', 'message', 'reply', 'sticker']):
                return f"{self.COLORS['CYAN']}{message}{self.COLORS['RESET']}"
            else:
                return f"{self.COLORS['GREEN']}{message}{self.COLORS['RESET']}"
        else:
            return f"{level_color}{message}{self.COLORS['RESET']}"

# Force color support in terminal
os.environ['FORCE_COLOR'] = '1'
os.environ['TERM'] = 'xterm-256color'

# Setup colored logging
logger = logging.getLogger("sakurabot")
logger.setLevel(logging.INFO)

# Remove any existing handlers
for handler in logger.handlers[:]:
    logger.removeHandler(handler)

# Create and configure console handler with colors
console_handler = logging.StreamHandler()
console_handler.setLevel(logging.INFO)
console_handler.setFormatter(ColoredFormatter("%(asctime)s | %(levelname)s | %(message)s"))

# Add handler to logger
logger.addHandler(console_handler)

# Prevent propagation to root logger to avoid duplicate messages
logger.propagate = False

# ── Utility: extract user information from message ─────────────────────────────
def extract_user_info(message):
    """Extract user and chat information from Telegram message dictionary"""
    logger.debug("🔍 Extracting user information from message")
    
    try:
        user = message.get("from", {})
        chat = message.get("chat", {})
        
        # Extract user information
        user_id = user.get("id")
        username = user.get("username", "")
        first_name = user.get("first_name", "")
        last_name = user.get("last_name", "")
        full_name = f"{first_name} {last_name}".strip() if last_name else first_name
        
        # Extract chat information
        chat_id = chat.get("id")
        chat_type = chat.get("type", "")
        chat_title = chat.get("title") or chat.get("first_name") or ""
        chat_username = f"@{chat.get('username')}" if chat.get("username") else "No Username"
        chat_link = f"https://t.me/{chat.get('username')}" if chat.get("username") else "No Link"
        
        info = {
            "user_id": user_id,
            "username": username,
            "full_name": full_name,
            "chat_id": chat_id,
            "chat_type": chat_type,
            "chat_title": chat_title,
            "chat_username": chat_username,
            "chat_link": chat_link,
        }
        
        logger.info(
            f"📑 User info extracted: {info['full_name']} (@{info['username'] or 'no_username'}) "
            f"[ID: {info['user_id']}] in {info['chat_title']} [{info['chat_id']}] {info['chat_link']}"
        )
        
        return info
        
    except Exception as e:
        logger.error(f"❌ Error extracting user info: {e}")
        return None

# ── Configuration ──────────────────────────────────────────────────────────────
logger.info("🚀 Sakura bot starting up - loading configuration")
logger.debug("🔍 Reading environment variables")

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

if not TELEGRAM_TOKEN:
    logger.critical("❌ TELEGRAM_TOKEN environment variable is missing!")
    exit(1)
if not GEMINI_API_KEY:
    logger.critical("❌ GEMINI_API_KEY environment variable is missing!")
    exit(1)

logger.info(f"✅ Telegram token loaded (length: {len(TELEGRAM_TOKEN)})")
logger.info(f"✅ Gemini API key loaded (length: {len(GEMINI_API_KEY)})")

TELEGRAM_API_URL = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}"
logger.debug(f"🔗 Telegram API URL configured: {TELEGRAM_API_URL[:50]}...")

# Owner configuration for broadcast functionality
OWNER_ID = int(os.getenv("OWNER_ID", "5290407067"))
logger.info(f"👑 Bot owner ID configured: {OWNER_ID}")

# Broadcast mode tracking
broadcast_mode = set()  # Users currently in broadcast mode
user_ids = set()  # All users who have interacted with the bot
logger.info("📢 Broadcast system initialized")

# ── Configure Gemini ───────────────────────────────────────────────────────────
logger.info("🤖 Initializing Gemini AI client")
try:
    client = genai.Client(api_key=GEMINI_API_KEY)
    model = "gemini-2.5-flash"
    logger.info(f"✅ Gemini client initialized successfully with model: {model}")
except Exception as e:
    logger.critical(f"❌ Failed to initialize Gemini client: {e}")
    exit(1)

# ── In‐memory state ────────────────────────────────────────────────────────────
logger.info("💾 Initializing in-memory state storage")
user_chats = {}       # Stores Gemini chat objects per user_id
last_update_id = 0    # For getUpdates offset
logger.debug(f"📊 User chats dictionary initialized: {len(user_chats)} users")
logger.debug(f"🔢 Last update ID initialized: {last_update_id}")

# ── Sakura's sticker IDs ───────────────────────────────────────────────────────
logger.info("🌸 Loading Sakura sticker collection")
sakura_stickers = [
    "CAACAgUAAxkBAAEOnMFoOwHrL_E-fBs2_aLViJKbHnEKigACUxcAAtArqFXR4hxTLoFOfDYE",  # ► Sakura sticker #1
    "CAACAgUAAxkBAAEOnMNoOwH0C1-dlOS0RmhQJZaLvlWYkgACthQAAvfkqVXP72iQq0BNejYE",  # ► Sakura sticker #2
    "CAACAgUAAxkBAAEOnMVoOwH2-i7OyMryUb5UrVCOopGYlAACVhQAAiwMqFUXDEHvVKsJLTYE",  # ► Sakura sticker #3
    "CAACAgUAAxkBAAEOnMdoOwH6d_QY6h4QDaS2jvj6LwS2wQACmRsAAmwjsFWFJ6owU1WfgTYE",  # ► Sakura sticker #4
    "CAACAgUAAxkBAAEOnMloOwH-Frc6JYkZHKEk9DJw-soycgACVigAAr4JsVWLUPaAp8o1mDYE",  # ► Sakura sticker #5
    "CAACAgUAAxkBAAEOnMtoOwIAATk3m5BlXvGe1xkODAEUTQQAAi8WAALHXKlVgsQdmfn20Rg2BA",  # ► Sakura sticker #6
    "CAACAgUAAxkBAAEOnMxoOwIAAfc-QKEZvoBF6CA3j0_sFloAAtMZAALqQ6lVDLoVOcN6leU2BA",  # ► Sakura sticker #7
    "CAACAgUAAxkBAAEOnM1oOwIB1s1MYAfCcXJoHGB9cEfrmgACAhkAAjKHqVWAkaO_ky9lTzYE",  # ► Sakura sticker #8
    "CAACAgUAAxkBAAEOnM9oOwIC3QLrH3-s10uJQJOov6T5OwACKxYAAhspsFV1qXoueKQAAUM2BA",  # ► Sakura sticker #9
    "CAACAgUAAxkBAAEOnNBoOwICkOoBINNAIIhDzqTBhCyVrgACXxkAAj60sVXgsb-vzSnt_TYE",  # ► Sakura sticker #10
    "CAACAgUAAxkBAAEOnNJoOwIDTeIOn-fGkTBREAov1JN4IAACuRUAAo2isVWykxNLWnwcYTYE",  # ► Sakura sticker #11
    "CAACAgUAAxkBAAEOnNNoOwID6iuGApoGCi704xMUDSl8QQACRx4AAp2SqFXcarUkpU5jzjYE",  # ► Sakura sticker #12
    "CAACAgUAAxkBAAEOnNVoOwIE1c1lhXrYRtpd4L1YHOHt9gACaBQAAu0uqFXKL-cNi_ZBJDYE",  # ► Sakura sticker #13
    "CAACAgUAAxkBAAEOnNZoOwIEftJuRGfJStGlNvCKNHnEKigACrxgAAtxdsFVMjTuKjuZHZDYE",  # ► Sakura sticker #14
    "CAACAgUAAxkBAAEOnNdoOwIFa_3I4cjE0I3aPGM83uKt9AACCxcAAidVsFWEt7xrqmGJxjYE",  # ► Sakura sticker #15
    "CAACAgUAAxkBAAEOnNloOwIFDK96aXtc5JtwyStgnoa7qAACEBkAAg7VqFV6tAlBFHKdPDYE",  # ► Sakura sticker #16
    "CAACAgUAAxkBAAEOnNpoOwIFQ0cFElvsB0Gz95HNbnMX1QACrhQAArcDsVV3-V8JhPN1qDYE",  # ► Sakura sticker #17
    "CAACAgUAAxkBAAEOnNxoOwIHJp8uPwABywABD3yH0JJkLPvbAAIgGgACq5exVfoo05pv4lKTNgQ",  # ► Sakura sticker #18
    "CAACAgUAAxkBAAEOnN1oOwIH2nP9Ki3llmC-o7EWYtitrQACHxUAArG-qFU5OStAsdYoJTYE",  # ► Sakura sticker #19
    "CAACAgUAAxkBAAEOnN5oOwIHAZfrKdzDbGYxdIKUW2XGWQACsRUAAiqIsVULIgcY4EYPbzYE",  # ► Sakura sticker #20
    "CAACAgUAAxkBAAEOnOBoOwIIy1dzx-0RLfwHiejWGkAbMAACPxcAArtosFXxg3weTZPx5TYE",  # ► Sakura sticker #21
    "CAACAgUAAxkBAAEOnOFoOwIIxFn1uQ6a3oldQn0AAfeH4RAAAncUAAIV_KlVtbXva5FrbTs2BA",  # ► Sakura sticker #22
    "CAACAgUAAxkBAAEOnONoOwIJjSlKKjbxYm9Y91KslMq9TAACtRcAAtggqVVx1D8N-Hwp8TYE",  # ► Sakura sticker #23
    "CAACAgUAAxkBAAEOnORoOwIJO01PbkilFlnOWgABB_4MvrcAApMTAAJ8krFVr6UvAAFW7tHbNgQ",  # ► Sakura sticker #24
    "CAACAgUAAxkBAAEOnOVoOwIK09kZqD0XyGaJwtIohkjMZgACQhUAAqGYqFXmCuT6Lrdn-jYE",  # ► Sakura sticker #25
    "CAACAgUAAxkBAAEOnOdoOwIKG8KS3B5npq2JCQN8KjJRFwACHxgAAvpMqVWpxtBkEZPfPjYE",  # ► Sakura sticker #26
    "CAACAgUAAxkBAAEOnOhoOwIK5X_qo6bmnv_zDBLnHDGo-QAC6x4AAiU7sVUROxvmQwqc0zYE",  # ► Sakura sticker #27
    "CAACAgUAAxkBAAEOnOpoOwILxbwdCAdV9Mv8qMAM1HhMswACnhMAAilDsVUIsplzTkTefTYE",  # ► Sakura sticker #28
    "CAACAgUAAxkBAAEOnOtoOwIMlqIEofu7G1aSAAERkLRXZvwAAugYAAI-W7FVTuh9RbnOGIo2BA",  # ► Sakura sticker #29
    "CAACAgUAAxkBAAEOnO1oOwINU_GIGSvoi1Y_2xf8UKEcUwACuxQAAmn2qFXgLss7TmYQkzYE",  # ► Sakura sticker #30
]
logger.info(f"✅ Loaded {len(sakura_stickers)} Sakura stickers")

# ── Sakura personality prompt ─────────────────────────────────────────────────
logger.info("🧠 Loading Sakura personality configuration")
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

# ── Predefined Sakura responses ─────────────────────────────────────────────────
START_MESSAGES = [
    "Hey you 🙃",
    "Missed you 😗",
    "Come here 🤗",
    "You okay? 👀",
    "I'm right here 😇",
    "Let it out 😕",
    "Breathe with me 😬",
    "Don't hide it 🤐",
    "I got you ❤️‍🩹",
    "Here for you 💞",
    "You're safe 🤗",
    "Talk to me ☺️",
    "No pressure 😐",
    "Whatever it is, I'm here 😕",
    "Just us now 😇",
    "Say anything, I'll listen 👀",
    "Your space, your pace ❤️",
    "Not leaving 💓",
    "Always here 💕",
    "I'm all ears 🤗",
    "Let's be okay together 🫠",
    "You matter 💔 but you're loved 💞",
    "I care. A lot. 😕",
    "Let it out or don't. Still love you ❤️",
    "Even if it's messy 😝",
    "Tired? Me too 🥲"
]

ERROR_MESSAGES = [
    "Ugh… tech 😕",
    "Wait what 😬",
    "Didn't work 🙃",
    "Oops 🫠",
    "One sec 🤐",
    "Try again maybe 😗",
    "A glitch? 😐",
    "That broke 😩",
    "Sorry 🥲",
    "Let me fix it ❤️‍🩹",
    "I messed up 😫",
    "This again 😕",
    "Give it another go 😉",
    "No clue what happened 😝",
    "Don't blame yourself 😇",
    "I still love you 💞",
    "That didn't land 💔",
    "Retry? 🤗",
    "Smol error 🫠",
    "Oops but we're fine 💕",
    "Just a hiccup 😝"
]

# ── Utility: send a message (with optional reply_to_message_id) ─────────────────
def send_message(chat_id, text, reply_to_message_id=None, reply_markup=None):
    logger.debug(f"📤 Preparing to send message to chat {chat_id}")
    logger.debug(f"💬 Message content: {text[:100]}{'...' if len(text) > 100 else ''}")
    
    try:
        url = f"{TELEGRAM_API_URL}/sendMessage"
        data = {
            "chat_id": chat_id,
            "text": text,
            "parse_mode": "HTML"
        }
        
        if reply_to_message_id:
            data["reply_to_message_id"] = reply_to_message_id
            logger.debug(f"↩️ Replying to message ID: {reply_to_message_id}")
            
        if reply_markup:
            data["reply_markup"] = reply_markup
            logger.debug(f"⌨️ Adding reply markup: {str(reply_markup)[:50]}...")
            
        logger.debug(f"🌐 Sending HTTP POST to: {url}")
        response = requests.post(url, json=data)
        
        if response.status_code == 200:
            logger.info(f"✅ Message sent successfully to chat {chat_id}")
            return response.json()
        else:
            logger.error(f"❌ Failed to send message. Status: {response.status_code}, Response: {response.text}")
            return None
            
    except requests.exceptions.RequestException as e:
        logger.error(f"🌐 Network error sending message: {e}")
        return None
    except Exception as e:
        logger.error(f"❌ Unexpected error sending message: {e}")
        return None

# ── Utility: send "chat action" so it looks like Sakura is doing something ────────
def send_chat_action(chat_id, action="typing"):
    """
    Use action="typing" to show "… is typing".
    Use action="choose_sticker" to show "… is choosing a sticker".
    """
    logger.debug(f"⚡ Sending chat action '{action}' to chat {chat_id}")
    
    try:
        url = f"{TELEGRAM_API_URL}/sendChatAction"
        data = {
            "chat_id": chat_id,
            "action": action
        }
        
        response = requests.post(url, json=data)
        
        if response.status_code == 200:
            logger.debug(f"✅ Chat action '{action}' sent successfully")
        else:
            logger.warning(f"⚠️ Chat action failed. Status: {response.status_code}")
            
    except requests.exceptions.RequestException as e:
        logger.error(f"🌐 Network error sending chat action: {e}")
    except Exception as e:
        logger.error(f"❌ Unexpected error sending chat action: {e}")

# ── Utility: send a sticker (with optional reply_to_message_id) ───────────────
def send_sticker(chat_id, sticker_file_id, reply_to_message_id=None):
    """
    Send a sticker to `chat_id`. If `reply_to_message_id` is set,
    Sakura will reply to that specific message with the sticker.
    """
    logger.debug(f"🌸 Preparing to send sticker to chat {chat_id}")
    logger.debug(f"🎭 Sticker ID: {sticker_file_id[:20]}...")
    
    try:
        url = f"{TELEGRAM_API_URL}/sendSticker"
        data = {
            "chat_id": chat_id,
            "sticker": sticker_file_id
        }
        
        if reply_to_message_id:
            data["reply_to_message_id"] = reply_to_message_id
            logger.debug(f"↩️ Replying to message ID: {reply_to_message_id}")
            
        logger.debug(f"🌐 Sending sticker HTTP POST to: {url}")
        response = requests.post(url, json=data)
        
        if response.status_code == 200:
            logger.info(f"✅ Sticker sent successfully to chat {chat_id}")
            return response.json()
        else:
            logger.error(f"❌ Failed to send sticker. Status: {response.status_code}")
            return None
            
    except requests.exceptions.RequestException as e:
        logger.error(f"🌐 Network error sending sticker: {e}")
        return None
    except Exception as e:
        logger.error(f"❌ Unexpected error sending sticker: {e}")
        return None

# ── Utility: send a random Sakura sticker ──────────────────────────────────────
def send_random_sakura_sticker(chat_id, reply_to_message_id=None):
    """
    Chooses one sticker_file_id at random from sakura_stickers,
    shows "choosing a sticker" action, then sends it.
    """
    logger.debug(f"🎲 Selecting random Sakura sticker for chat {chat_id}")
    
    if not sakura_stickers:
        logger.warning("⚠️ No Sakura stickers available!")
        return

    logger.info(f"🌸 Choosing from {len(sakura_stickers)} available stickers")
    
    # 1) Show "Sakura is choosing a sticker…" indicator
    logger.debug("⚡ Showing 'choosing sticker' action")
    send_chat_action(chat_id, action="choose_sticker")

    # 2) Pick random sticker and send
    sticker_id = random.choice(sakura_stickers)
    logger.info(f"🎭 Selected sticker: {sticker_id[:20]}...")
    send_sticker(chat_id, sticker_id, reply_to_message_id=reply_to_message_id)

# ── Poll Telegram for new updates ────────────────────────────────────────────────
def get_updates():
    global last_update_id
    logger.debug(f"📥 Polling for updates with offset: {last_update_id + 1}")
    
    try:
        url = f"{TELEGRAM_API_URL}/getUpdates"
        params = {
            "offset": last_update_id + 1,
            "timeout": 30
        }
        
        logger.debug(f"🌐 Sending GET request to: {url}")
        response = requests.get(url, params=params)
        
        if response.status_code == 200:
            data = response.json()
            if data.get("ok"):
                updates_count = len(data.get("result", []))
                if updates_count > 0:
                    logger.info(f"📨 Received {updates_count} new updates")
                else:
                    logger.debug("📭 No new updates received")
                return data
            else:
                logger.error(f"❌ Telegram API error: {data}")
                return None
        else:
            logger.error(f"❌ HTTP error {response.status_code}: {response.text}")
            return None
            
    except requests.exceptions.Timeout:
        logger.debug("⏱️ Request timeout (normal during long polling)")
        return None
    except requests.exceptions.RequestException as e:
        logger.error(f"🌐 Network error getting updates: {e}")
        return None
    except Exception as e:
        logger.error(f"❌ Unexpected error getting updates: {e}")
        return None

# ── Register /start and /help commands so Telegram shows them in UI ──────────────
def set_my_commands():
    logger.info("⚙️ Setting up bot commands for Telegram UI")
    
    commands = [
        {"command": "start", "description": "Start the bot"},
        {"command": "help", "description": "How to use Sakura bot"}
    ]
    
    logger.debug(f"📋 Commands to register: {commands}")
    
    try:
        url = f"{TELEGRAM_API_URL}/setMyCommands"
        response = requests.post(url, json={"commands": commands})
        
        if response.status_code == 200:
            logger.info("✅ Bot commands set successfully")
        else:
            logger.error(f"❌ Failed to set bot commands. Status: {response.status_code}, Response: {response.text}")
            
    except requests.exceptions.RequestException as e:
        logger.error(f"🌐 Network error setting commands: {e}")
    except Exception as e:
        logger.error(f"❌ Unexpected error setting commands: {e}")

# ── Handle /start ───────────────────────────────────────────────────────────────
def handle_start_command(chat_id, user_id):
    logger.info(f"🚀 Processing /start command for user {user_id} in chat {chat_id}")
    
    welcome_message = """
<b>Hey there… I'm Sakura Haruno!</b> Your gentle guide and safe place 🌸
  
It's so good you're here. I speak softly, listen closely, and stay with you through every quiet storm  
Whether you need a caring whisper, a patient heart, or just someone to be there, I'm all yours 💓

Even when things feel heavy… you're never alone  
Take a breath… I'm right here, and we'll face it all together  💞

You're stronger than you feel. Brighter than you know. And I believe in you always! 🤎
"""
    
    logger.debug(f"💬 Welcome message prepared (length: {len(welcome_message)})")
    
    inline_keyboard = {
        "inline_keyboard": [
            [
                {"text": "Updates", "url": "https://t.me/WorkGlows"},
                {"text": "Support", "url": "https://t.me/TheCryptoElders"}
            ],
            [
                {"text": "Add Me to Your Group", "url": f"https://t.me/SluttySakuraBot?startgroup=true"}
            ]
        ]
    }
    
    logger.debug("⌨️ Inline keyboard prepared with 3 buttons")
    
    try:
        send_message(chat_id, welcome_message, reply_markup=json.dumps(inline_keyboard))
        logger.info(f"✅ /start command completed successfully for user {user_id}")
    except Exception as e:
        logger.error(f"❌ Error handling /start command: {e}")

# ── Handle /help ────────────────────────────────────────────────────────────────
def handle_help_command(chat_id, user_id):
    logger.info(f"❓ Processing /help command for user {user_id} in chat {chat_id}")
    
    help_text = """
Hey… I'm Sakura 🌸  
I'm here as your caring partner and gentle support  
Just send me anything on your mind—your thoughts your day your feelings  
I'll respond softly with one-line messages no punctuation and always with one little emoji  

Here's what I can do for you:  
• <b>/start</b> – A warm welcome and gentle hello  
• <b>/help</b> – Show this message anytime you need it  

I speak softly in Romanized Hindi by default  
But I'll reply in English or Bangla if that's how you talk to me  

You can count on me for comfort encouragement or just quiet company 🤎  
"""
    
    logger.debug(f"📝 Help text prepared (length: {len(help_text)})")
    
    try:
        send_message(chat_id, help_text)
        logger.info(f"✅ /help command completed successfully for user {user_id}")
    except Exception as e:
        logger.error(f"❌ Error handling /help command: {e}")

# ── Handle /broadcast command (owner only) ──────────────────────────────────────
def handle_broadcast_command(chat_id, user_id, first_name):
    """Handle broadcast command (owner only)"""
    logger.info(f"📢 Broadcast command attempted by {first_name} (ID: {user_id})")

    if user_id != OWNER_ID:
        logger.warning(f"🚫 Unauthorized broadcast attempt by user {user_id}")
        send_chat_action(chat_id, "typing")
        send_message(chat_id, "⛔ This command is restricted.")
        logger.info(f"⚠️ Unauthorized access message sent to {user_id}")
        return

    send_chat_action(chat_id, "typing")
    logger.info(f"👑 Enabling broadcast mode for owner {user_id}")
    broadcast_mode.add(user_id)

    send_message(chat_id, "📣 <b>Broadcast mode enabled.</b> Send me any message (text, photo, video, document, etc.) and I will forward it to all users. Mode will automatically disable after sending.")
    logger.info(f"✅ Broadcast mode enabled for owner {user_id}")

# ── Handle /stop_broadcast command (owner only) ─────────────────────────────────
def handle_stop_broadcast_command(chat_id, user_id, first_name):
    """Handle stop broadcast command (owner only)"""
    logger.info(f"🛑 Stop broadcast command attempted by {first_name} (ID: {user_id})")

    if user_id != OWNER_ID:
        logger.warning(f"🚫 Unauthorized stop_broadcast attempt by user {user_id}")
        send_chat_action(chat_id, "typing")
        send_message(chat_id, "⛔ This command is restricted.")
        logger.info(f"⚠️ Unauthorized access message sent to {user_id}")
        return

    if user_id in broadcast_mode:
        broadcast_mode.remove(user_id)
        send_chat_action(chat_id, "typing")
        send_message(chat_id, "📴 <b>Broadcast mode disabled.</b> Back to normal Sakura mode.")
        logger.info(f"✅ Broadcast mode disabled for owner {user_id}")
    else:
        send_chat_action(chat_id, "typing")
        send_message(chat_id, "ℹ️ Broadcast mode is not currently active.")
        logger.info(f"ℹ️ Owner {user_id} tried to disable broadcast mode when it wasn't active")

# ── Enhanced media sending functions ───────────────────────────────────────────
def send_photo(chat_id, photo_file_id, caption=None, reply_to_message_id=None):
    """Send a photo to chat"""
    logger.debug(f"📸 Sending photo to chat {chat_id}")
    try:
        url = f"{TELEGRAM_API_URL}/sendPhoto"
        data = {"chat_id": chat_id, "photo": photo_file_id}
        if caption:
            data["caption"] = caption
            data["parse_mode"] = "HTML"
        if reply_to_message_id:
            data["reply_to_message_id"] = reply_to_message_id
        
        response = requests.post(url, json=data)
        return response.json() if response.status_code == 200 else None
    except Exception as e:
        logger.error(f"❌ Error sending photo: {e}")
        return None

def send_video(chat_id, video_file_id, caption=None, reply_to_message_id=None):
    """Send a video to chat"""
    logger.debug(f"🎥 Sending video to chat {chat_id}")
    try:
        url = f"{TELEGRAM_API_URL}/sendVideo"
        data = {"chat_id": chat_id, "video": video_file_id}
        if caption:
            data["caption"] = caption
            data["parse_mode"] = "HTML"
        if reply_to_message_id:
            data["reply_to_message_id"] = reply_to_message_id
        
        response = requests.post(url, json=data)
        return response.json() if response.status_code == 200 else None
    except Exception as e:
        logger.error(f"❌ Error sending video: {e}")
        return None

def send_document(chat_id, document_file_id, caption=None, reply_to_message_id=None):
    """Send a document to chat"""
    logger.debug(f"📄 Sending document to chat {chat_id}")
    try:
        url = f"{TELEGRAM_API_URL}/sendDocument"
        data = {"chat_id": chat_id, "document": document_file_id}
        if caption:
            data["caption"] = caption
            data["parse_mode"] = "HTML"
        if reply_to_message_id:
            data["reply_to_message_id"] = reply_to_message_id
        
        response = requests.post(url, json=data)
        return response.json() if response.status_code == 200 else None
    except Exception as e:
        logger.error(f"❌ Error sending document: {e}")
        return None

def send_audio(chat_id, audio_file_id, caption=None, reply_to_message_id=None):
    """Send an audio to chat"""
    logger.debug(f"🎵 Sending audio to chat {chat_id}")
    try:
        url = f"{TELEGRAM_API_URL}/sendAudio"
        data = {"chat_id": chat_id, "audio": audio_file_id}
        if caption:
            data["caption"] = caption
            data["parse_mode"] = "HTML"
        if reply_to_message_id:
            data["reply_to_message_id"] = reply_to_message_id
        
        response = requests.post(url, json=data)
        return response.json() if response.status_code == 200 else None
    except Exception as e:
        logger.error(f"❌ Error sending audio: {e}")
        return None

def send_voice(chat_id, voice_file_id, caption=None, reply_to_message_id=None):
    """Send a voice message to chat"""
    logger.debug(f"🎤 Sending voice to chat {chat_id}")
    try:
        url = f"{TELEGRAM_API_URL}/sendVoice"
        data = {"chat_id": chat_id, "voice": voice_file_id}
        if caption:
            data["caption"] = caption
            data["parse_mode"] = "HTML"
        if reply_to_message_id:
            data["reply_to_message_id"] = reply_to_message_id
        
        response = requests.post(url, json=data)
        return response.json() if response.status_code == 200 else None
    except Exception as e:
        logger.error(f"❌ Error sending voice: {e}")
        return None

def send_video_note(chat_id, video_note_file_id, reply_to_message_id=None):
    """Send a video note (circle video) to chat"""
    logger.debug(f"📹 Sending video note to chat {chat_id}")
    try:
        url = f"{TELEGRAM_API_URL}/sendVideoNote"
        data = {"chat_id": chat_id, "video_note": video_note_file_id}
        if reply_to_message_id:
            data["reply_to_message_id"] = reply_to_message_id
        
        response = requests.post(url, json=data)
        return response.json() if response.status_code == 200 else None
    except Exception as e:
        logger.error(f"❌ Error sending video note: {e}")
        return None

def send_animation(chat_id, animation_file_id, caption=None, reply_to_message_id=None):
    """Send an animation/GIF to chat"""
    logger.debug(f"🎬 Sending animation to chat {chat_id}")
    try:
        url = f"{TELEGRAM_API_URL}/sendAnimation"
        data = {"chat_id": chat_id, "animation": animation_file_id}
        if caption:
            data["caption"] = caption
            data["parse_mode"] = "HTML"
        if reply_to_message_id:
            data["reply_to_message_id"] = reply_to_message_id
        
        response = requests.post(url, json=data)
        return response.json() if response.status_code == 200 else None
    except Exception as e:
        logger.error(f"❌ Error sending animation: {e}")
        return None

def send_location(chat_id, latitude, longitude, reply_to_message_id=None):
    """Send a location to chat"""
    logger.debug(f"📍 Sending location to chat {chat_id}")
    try:
        url = f"{TELEGRAM_API_URL}/sendLocation"
        data = {"chat_id": chat_id, "latitude": latitude, "longitude": longitude}
        if reply_to_message_id:
            data["reply_to_message_id"] = reply_to_message_id
        
        response = requests.post(url, json=data)
        return response.json() if response.status_code == 200 else None
    except Exception as e:
        logger.error(f"❌ Error sending location: {e}")
        return None

def send_contact(chat_id, phone_number, first_name, last_name=None, reply_to_message_id=None):
    """Send a contact to chat"""
    logger.debug(f"👤 Sending contact to chat {chat_id}")
    try:
        url = f"{TELEGRAM_API_URL}/sendContact"
        data = {"chat_id": chat_id, "phone_number": phone_number, "first_name": first_name}
        if last_name:
            data["last_name"] = last_name
        if reply_to_message_id:
            data["reply_to_message_id"] = reply_to_message_id
        
        response = requests.post(url, json=data)
        return response.json() if response.status_code == 200 else None
    except Exception as e:
        logger.error(f"❌ Error sending contact: {e}")
        return None

def send_poll(chat_id, question, options, reply_to_message_id=None):
    """Send a poll to chat"""
    logger.debug(f"📊 Sending poll to chat {chat_id}")
    try:
        url = f"{TELEGRAM_API_URL}/sendPoll"
        data = {"chat_id": chat_id, "question": question, "options": options}
        if reply_to_message_id:
            data["reply_to_message_id"] = reply_to_message_id
        
        response = requests.post(url, json=data)
        return response.json() if response.status_code == 200 else None
    except Exception as e:
        logger.error(f"❌ Error sending poll: {e}")
        return None

# ── Enhanced broadcast message transmission ─────────────────────────────────────
async def handle_broadcast_message(chat_id, user_id, message, first_name):
    """Handle broadcasting any type of message to all users"""
    logger.info(f"📡 Broadcasting message from owner {first_name} (ID: {user_id})")

    send_chat_action(chat_id, "typing")

    success_count = 0
    fail_count = 0

    # Get message content for logging
    text = message.get("text", "")
    caption = message.get("caption", "")
    content_preview = text or caption or "[Media content]"

    logger.info(f"📊 Starting broadcast to {len(user_ids)} users")
    logger.info(f"📄 Content preview: {content_preview[:50]}{'...' if len(content_preview) > 50 else ''}")

    for target_user_id in user_ids.copy():
        try:
            # Determine message type and send accordingly
            if "text" in message and message["text"]:
                # Text message
                send_message(target_user_id, message["text"])
            elif "photo" in message:
                # Photo message
                photo_file_id = message["photo"][-1]["file_id"]  # Get highest resolution
                send_photo(target_user_id, photo_file_id, caption)
            elif "video" in message:
                # Video message
                video_file_id = message["video"]["file_id"]
                send_video(target_user_id, video_file_id, caption)
            elif "document" in message:
                # Document message
                document_file_id = message["document"]["file_id"]
                send_document(target_user_id, document_file_id, caption)
            elif "audio" in message:
                # Audio message
                audio_file_id = message["audio"]["file_id"]
                send_audio(target_user_id, audio_file_id, caption)
            elif "voice" in message:
                # Voice message
                voice_file_id = message["voice"]["file_id"]
                send_voice(target_user_id, voice_file_id, caption)
            elif "video_note" in message:
                # Video note (circle video)
                video_note_file_id = message["video_note"]["file_id"]
                send_video_note(target_user_id, video_note_file_id)
            elif "sticker" in message:
                # Sticker message
                sticker_file_id = message["sticker"]["file_id"]
                send_sticker(target_user_id, sticker_file_id)
            elif "animation" in message:
                # Animation/GIF message
                animation_file_id = message["animation"]["file_id"]
                send_animation(target_user_id, animation_file_id, caption)
            elif "location" in message:
                # Location message
                location = message["location"]
                send_location(target_user_id, location["latitude"], location["longitude"])
            elif "contact" in message:
                # Contact message
                contact = message["contact"]
                send_contact(target_user_id, contact["phone_number"], contact["first_name"], contact.get("last_name"))
            elif "poll" in message:
                # Poll message
                poll = message["poll"]
                options = [option["text"] for option in poll["options"]]
                send_poll(target_user_id, poll["question"], options)
            else:
                # Fallback for unsupported message types
                fallback_msg = "📢 Broadcast message (unsupported media type)"
                send_message(target_user_id, fallback_msg)

            success_count += 1
            logger.debug(f"✅ Broadcast sent successfully to user {target_user_id}")
            # Add small delay to avoid rate limiting
            await asyncio.sleep(0.1)
        except Exception as e:
            fail_count += 1
            logger.warning(f"❌ Failed to send broadcast to user {target_user_id}: {str(e)}")
            # Remove inactive users from the list
            user_ids.discard(target_user_id)

    logger.info(f"📈 Broadcast complete. Success: {success_count}, Failed: {fail_count}")

    # Automatically disable broadcast mode after sending
    if user_id in broadcast_mode:
        broadcast_mode.remove(user_id)
        logger.info(f"📴 Broadcast mode automatically disabled for owner {user_id}")

    summary_message = f"📊 Broadcast complete!\n✅ Sent: {success_count}\n❌ Failed: {fail_count}\n📴 Broadcast mode disabled."
    send_message(chat_id, summary_message)
    logger.info(f"📋 Broadcast summary sent to owner")

# ── Handle a normal text message (injecting the user's first name) ─────────────
def handle_text_message(chat_id, user_id, first_name, text, reply_to_message_id=None):
    logger.info(f"💬 Processing text message from {first_name} (ID: {user_id}) in chat {chat_id}")
    logger.debug(f"📝 Message content: {text[:100]}{'...' if len(text) > 100 else ''}")
    
    try:
        # Show "typing…" indicator before generating reply
        logger.debug("⚡ Sending typing indicator")
        send_chat_action(chat_id, action="typing")

        # If this is the first time this user chats, create a new conversation history for them
        if user_id not in user_chats:
            logger.info(f"👤 New user detected: {first_name} ({user_id}). Creating chat history.")
            user_chats[user_id] = []
        else:
            logger.debug(f"👤 Existing user: {first_name} ({user_id}). Chat history length: {len(user_chats[user_id])}")

        chat_history = user_chats[user_id]

        # ── 1) Normalize the user's incoming text ────────────────────────────
        logger.debug("🔍 Analyzing message content")
        normalized = text.lower().strip()
        logger.debug(f"📝 Normalized text: {normalized}")

        # ── 2) Check for simple greetings ──────────────────────────────────
        greeting_keywords = {"hi", "hello", "hey", "namaste", "konichiwa"}
        is_greeting = normalized in greeting_keywords
        logger.debug(f"👋 Is greeting: {is_greeting}")

        # ── 3) Check for "emotional" keywords ──────────────────────────────
        emotional_keywords = {
            "sad", "lonely", "anxiety", "anxious", "depressed", 
            "heartbroken", "upset", "failed", "tired", "hurt"
        }
        contains_emotion = any(word in normalized.split() for word in emotional_keywords)
        logger.debug(f"😢 Contains emotional keywords: {contains_emotion}")
        
        if contains_emotion:
            detected_emotions = [word for word in normalized.split() if word in emotional_keywords]
            logger.info(f"💔 Emotional message detected. Keywords: {detected_emotions}")

        # ── 4) Build name_instruction only when greeting OR emotional ─────
        use_name = is_greeting or contains_emotion
        logger.debug(f"📛 Will use name in response: {use_name}")
        
        if use_name:
            name_instruction = (
                f"# The user's first name is \"{first_name}\".\n"
                f"# When you reply, address them by {first_name} sometime in your flirty, "
                f"sugary-romantic style.\n"
            )
            logger.debug(f"📝 Name instruction prepared for {first_name}")
        else:
            name_instruction = ""  # no forced name usage here
            logger.debug("📝 No name instruction - will not force name usage")

        # ── 5) Assemble the final prompt to send to Gemini ─────────────────
        logger.debug("🧠 Preparing prompt for Gemini AI")
        enhanced_prompt = (
            f"{SAKURA_PROMPT}\n\n"
            f"{name_instruction}"
            f"User: {text}\n\n"
            f"Respond as Sakura Haruno:"
        )
        logger.debug(f"📝 Enhanced prompt length: {len(enhanced_prompt)} characters")

        # ── 6) Send to Gemini and get Sakura's reply ───────────────────────
        logger.info("🤖 Generating AI response with Gemini")
        try:
            response = client.models.generate_content(
                model=model,
                contents=enhanced_prompt
            )
            
            if response and response.text:
                reply = response.text.strip()
                logger.info(f"✅ AI response generated successfully (length: {len(reply)})")
            else:
                logger.warning("⚠️ Empty response from Gemini, using error message")
                reply = random.choice(ERROR_MESSAGES)
                
        except Exception as gemini_error:
            logger.error(f"❌ Gemini API error: {gemini_error}")
            reply = random.choice(ERROR_MESSAGES)

        # Trim if it's excessively long
        if len(reply) > 4000:
            logger.warning(f"⚠️ Response too long ({len(reply)} chars), trimming to 3900")
            reply = reply[:3900] + "... (message too long, sorry!) 🙃"

        # ── 7) Send Sakura's reply back to Telegram ────────────────────────
        logger.info(f"💬 Sending Sakura's response: {reply[:50]}{'...' if len(reply) > 50 else ''}")
        send_message(chat_id, reply, reply_to_message_id=reply_to_message_id)
        logger.info(f"✅ Message handling completed for {first_name} ({user_id})")

    except Exception as e:
        logger.error(f"❌ Critical error in handle_text_message: {e}")
        logger.debug(f"🔍 Error details: {type(e).__name__}: {str(e)}")
        error_msg = random.choice(ERROR_MESSAGES)
        logger.info(f"💔 Sending error message to user: {error_msg}")
        try:
            send_message(chat_id, error_msg)
        except Exception as send_error:
            logger.critical(f"💥 Failed to send error message: {send_error}")

# ── Process each update from getUpdates ─────────────────────────────────────────
async def process_update(update):
    logger.debug(f"📋 Processing update ID: {update.get('update_id', 'unknown')}")
    
    try:
        if "message" not in update:
            logger.debug("⚠️ Update has no message, skipping")
            return

        message = update["message"]
        
        # Extract comprehensive user and chat information
        user_info = extract_user_info(message)
        if not user_info:
            logger.warning("⚠️ Could not extract user info, skipping message")
            return
            
        chat_id = user_info["chat_id"]
        chat_type = user_info["chat_type"]
        user_id = user_info["user_id"]
        first_name = user_info["full_name"].split()[0] if user_info["full_name"] else "Unknown"
        text = message.get("text", "").strip()
        reply_to = message.get("reply_to_message")
        
        logger.debug(f"💬 Message: {text[:100]}{'...' if len(text) > 100 else ''}")
        
        if reply_to:
            logger.debug(f"↩️ Reply to message ID: {reply_to.get('message_id')}")

        # Track all users who interact with the bot
        user_ids.add(user_id)
        logger.debug(f"👥 User {user_id} added to user tracking. Total users: {len(user_ids)}")

        # ── 1) Handle commands ─────────────────────────────────────────────────
        if text.startswith("/start"):
            logger.info(f"🚀 Processing /start command from {first_name}")
            handle_start_command(chat_id, user_id)
            return
        elif text.startswith("/help"):
            logger.info(f"❓ Processing /help command from {first_name}")
            handle_help_command(chat_id, user_id)
            return
        elif text.startswith("/broadcast"):
            logger.info(f"📢 Processing /broadcast command from {first_name}")
            handle_broadcast_command(chat_id, user_id, first_name)
            return
        elif text.startswith("/stop_broadcast"):
            logger.info(f"📢 Processing /stop_broadcast command from {first_name}")
            handle_stop_broadcast_command(chat_id, user_id, first_name)
            return

        # ── 2) Check if user is in broadcast mode ─────────────────────────────
        if user_id in broadcast_mode:
            logger.info(f"📡 User {first_name} ({user_id}) is in broadcast mode")
            await handle_broadcast_message(chat_id, user_id, message, first_name)
            return

        # ── 3) If this is a private chat, respond to every text ───────────────
        if chat_type == "private":
            logger.info(f"🔒 Private message from {first_name} ({user_id}): responding")
            handle_text_message(chat_id, user_id, first_name, text)
            return

        # ── 2.5) If someone REPLIES to Sakura's message with a STICKER ─────────
        if reply_to:
            from_field = reply_to.get("from", {})
            bot_username = from_field.get("username", "").lower()
            logger.debug(f"🔍 Checking if reply is to bot. Reply from: {bot_username}")
            
            if bot_username == "sluttysakurabot":
                if "sticker" in message:
                    logger.info(f"🎭 User replied with sticker to Sakura in chat {chat_id}")
                    send_random_sakura_sticker(
                        chat_id,
                        reply_to_message_id=message["message_id"]
                    )
                    return

        # ── 3) In group chats, detect if it's a reply TO Sakura's text message ───
        is_reply_to_bot = False
        if reply_to:
            from_field = reply_to.get("from", {})
            bot_username = from_field.get("username", "").lower()
            if bot_username == "sluttysakurabot":
                is_reply_to_bot = True
                logger.debug(f"✅ Detected reply to Sakura's message")

        if is_reply_to_bot:
            logger.info(f"💬 Group reply to Sakura from {first_name} ({user_id}) in chat {chat_id}")
            handle_text_message(
                chat_id,
                user_id,
                first_name,
                text,
                reply_to_message_id=message["message_id"]
            )
            return

        # ── 4) In group chats, if someone types "Sakura", respond ─────────────
        if "sakura" in text.lower():
            logger.info(f"🌸 Keyword 'Sakura' detected in group {chat_id} by {first_name} ({user_id})")
            logger.debug(f"💬 Keyword trigger message: {text}")
            handle_text_message(
                chat_id,
                user_id,
                first_name,
                text,
                reply_to_message_id=message["message_id"]
            )
            return

        # ── 5) Otherwise, do nothing ──────────────────────────────────────────
        logger.debug(f"⭕ No action needed for message from {first_name} in {chat_type} chat {chat_id}")
        return

    except Exception as e:
        logger.error(f"❌ Critical error processing update: {e}")
        logger.debug(f"🔍 Update content: {str(update)[:200]}...")
        
 # ─── Dummy HTTP Server to Keep Render Happy ─────────────────────────────────
class DummyHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        logger.debug(f"🌐 HTTP GET request from {self.client_address[0]}")
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"Sakura bot is alive!")

    def do_HEAD(self):
        logger.debug(f"🌐 HTTP HEAD request from {self.client_address[0]}")
        self.send_response(200)
        self.end_headers()
        
    def log_message(self, format, *args):
        # Override to prevent default HTTP logs from cluttering our colored logs
        pass

def start_dummy_server():
    logger.info("🌐 Starting HTTP health check server")
    port = int(os.environ.get("PORT", 5000))
    
    try:
        server = HTTPServer(("0.0.0.0", port), DummyHandler)
        logger.info(f"✅ HTTP server listening on 0.0.0.0:{port}")
        server.serve_forever()
    except Exception as e:
        logger.error(f"❌ Failed to start HTTP server: {e}")
        raise

# ── Main loop: poll getUpdates, then process each update ──────────────────────
def delete_webhook():
    """Delete any existing webhook to ensure polling works"""
    try:
        url = f"{TELEGRAM_API_URL}/deleteWebhook"
        response = requests.post(url)
        if response.status_code == 200:
            logger.info("🔧 Webhook deleted successfully - polling mode enabled")
        else:
            logger.warning(f"⚠️ Failed to delete webhook: {response.text}")
    except Exception as e:
        logger.error(f"❌ Error deleting webhook: {e}")

async def main():
    global last_update_id

    logger.info("🌸 Sakura Bot is starting up! 🌸")
    logger.info("📢 Make sure Privacy Mode is OFF so I see all messages in groups.")
    
    # Delete webhook to prevent conflicts with polling
    delete_webhook()
    
    # Initialize bot commands
    set_my_commands()
    
    logger.info(f"📊 Starting main polling loop with update ID: {last_update_id}")
    logger.info("🔄 Bot is now actively listening for messages...")
    
    loop_count = 0
    
    while True:
        try:
            loop_count += 1
            if loop_count % 100 == 0:  # Log every 100 loops to show activity
                logger.debug(f"🔄 Main loop iteration #{loop_count}, last update: {last_update_id}")
            
            result = get_updates()
            if result and result.get("ok"):
                updates = result.get("result", [])
                if updates:
                    logger.debug(f"📨 Processing {len(updates)} updates")
                    for update in updates:
                        old_update_id = last_update_id
                        last_update_id = update["update_id"]
                        logger.debug(f"📝 Update ID: {old_update_id} → {last_update_id}")
                        await process_update(update)
                        
            await asyncio.sleep(1)

        except KeyboardInterrupt:
            logger.info("🛑 Received KeyboardInterrupt - shutting down gracefully")
            break
        except asyncio.CancelledError:
            logger.info("🛑 Async task cancelled - shutting down")
            break
        except Exception as e:
            logger.error(f"💥 Critical error in main loop: {e}")
            logger.debug(f"🔍 Error type: {type(e).__name__}")
            logger.warning("⏳ Waiting 5 seconds before retrying...")
            await asyncio.sleep(5)

def main_entry_point():
    """Entry point for the bot with comprehensive error handling"""
    logger.info("🚀 Sakura bot entry point started")
    
    try:
        # Start dummy HTTP server in background thread
        logger.info("🌐 Starting background HTTP server thread")
        http_thread = threading.Thread(target=start_dummy_server, daemon=True)
        http_thread.start()
        logger.info("✅ HTTP server thread started successfully")
        
        # Run the main bot loop
        logger.info("🤖 Starting main bot async loop")
        asyncio.run(main())
        
    except KeyboardInterrupt:
        logger.info("🛑 Application stopped by user (Ctrl+C)")
    except Exception as e:
        logger.critical(f"💥 Fatal error in main entry point: {e}")
        logger.debug(f"🔍 Fatal error details: {type(e).__name__}: {str(e)}")
        raise
    finally:
        logger.info("🌸 Sakura bot shutting down. Goodbye! 💞")

if __name__ == "__main__":
    main_entry_point()