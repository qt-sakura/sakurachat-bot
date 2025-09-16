import os

# CONFIGURATION
API_ID = int(os.getenv("API_ID", "0"))
API_HASH = os.getenv("API_HASH", "")
BOT_TOKEN = os.getenv("BOT_TOKEN", "")
VALKEY_URL = os.getenv("VALKEY_URL", "valkey://localhost:6379")
DATABASE_URL = os.getenv("DATABASE_URL", "")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
OWNER_ID = int(os.getenv("OWNER_ID", "0"))
SESSION_TTL = 3600
CACHE_TTL = 300
RATE_LIMIT_TTL = 60
RATE_LIMIT_COUNT = 5
MESSAGE_LIMIT = 1.0
CHAT_LENGTH = 20
CHAT_CLEANUP = 1800
OLD_CHAT = 3600
