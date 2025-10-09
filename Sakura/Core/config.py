import os

# CONFIGURATION
API_ID = int(os.getenv("API_ID", "0"))
API_HASH = os.getenv("API_HASH", "")
BOT_TOKEN = os.getenv("BOT_TOKEN", "")
VALKEY_URL = os.getenv("VALKEY_URL", "")
DATABASE_URL = os.getenv("DATABASE_URL", "")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
AI_MODEL = os.getenv("AI_MODEL", "gemini-2.5-flash")
ELEVENLABS_API_KEY = os.getenv("ELEVENLABS_API_KEY", "")
VOICE_ID = "ClQWBz2oM8pZtT7nQKk9"
OWNER_ID = int(os.getenv("OWNER_ID", "0"))
SUPPORT_LINK = os.getenv("SUPPORT_LINK", "https://t.me/SoulMeetsHQ")
UPDATE_LINK = os.getenv("UPDATE_LINK", "https://t.me/DoDotPy")
PING_LINK = os.getenv("PING_LINK", "https://t.me/DoDotPy")
SESSION_TTL = 3600
CACHE_TTL = 300
RATE_LIMIT_TTL = 60
RATE_LIMIT_COUNT = 5
MESSAGE_LIMIT = 1.0
BROADCAST_DELAY = 0.03
CHAT_LENGTH = 20
CHAT_CLEANUP = 1800
OLD_CHAT = 3600
