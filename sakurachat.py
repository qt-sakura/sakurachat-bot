import os
import time
import orjson
import uvloop
import random
import psutil
import valkey
import base64
import hashlib
import os
import time
import orjson
import uvloop
import random
import psutil
import valkey
import base64
import hashlib
import asyncio
import aiohttp
import logging
import asyncpg
import datetime
import threading
import traceback
from telegram import (
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    BotCommand,
    Message,
    ReactionTypeEmoji,
    LabeledPrice,
    ChatMember,
)
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    PreCheckoutQueryHandler,
    ContextTypes,
    filters,
    ChatMemberHandler,
)
from google import genai
from openai import OpenAI
from typing import Dict, Set, Optional
from telethon import TelegramClient, events
from valkey.asyncio import Valkey as AsyncValkey
from telegram.constants import ParseMode, ChatAction
from http.server import BaseHTTPRequestHandler, HTTPServer
from telegram.error import (
    TelegramError,
    Forbidden,
    BadRequest,
    Conflict,
    NetworkError,
)

# CONFIGURATION
API_ID = int(os.getenv("API_ID", "0"))
API_HASH = os.getenv("API_HASH", "")
BOT_TOKEN = os.getenv("BOT_TOKEN", "")
VALKEY_URL = os.getenv("VALKEY_URL", "valkey://localhost:6379")
DATABASE_URL = os.getenv("DATABASE_URL", "")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY", "")
MODEL = os.getenv("MODEL", "x-ai/grok-4-fast:free")
OWNER_ID = int(os.getenv("OWNER_ID", "0"))
SUPPORT_LINK = os.getenv("SUPPORT_LINK", "https://t.me/SoulMeetsHQ")
UPDATE_LINK = os.getenv("UPDATE_LINK", "https://t.me/WorkGlows")
PING_LINK = os.getenv("PING_LINK", "https://t.me/WorkGlows")
SESSION_TTL = 3600
CACHE_TTL = 300
RATE_LIMIT_TTL = 60
RATE_LIMIT_COUNT = 5
MESSAGE_LIMIT = 1.0
BROADCAST_DELAY = 0.03
CHAT_LENGTH = 20
CHAT_CLEANUP = 1800
OLD_CHAT = 3600

# GLOBAL STATE & MEMORY SYSTEM
user_ids: Set[int] = set()
group_ids: Set[int] = set()
broadcast_mode: Dict[int, str] = {}
user_message_counts: Dict[str, list] = {}
rate_limited_users: Dict[str, float] = {}
user_last_response_time: Dict[int, float] = {}
conversation_history: Dict[int, list] = {}
db_pool = None
cleanup_task = None
valkey_client: AsyncValkey = None
payment_storage = {}
effects_client = None
gemini_client = None
openrouter_client = None

# Commands dictionary
COMMANDS = [
    BotCommand("start", "👋 Wake me up"),
    BotCommand("buy", "🌸 Get flowers"),
    BotCommand("buyers", "💝 Flower buyers"),
    BotCommand("help", "💬 A short guide")
]

# EMOJI REACTIONS AND STICKERS
# Emoji reactions for /start command
EMOJI_REACT = [
    "🍓",  "💊",  "🦄",  "💅",  "💘",
    "💋",  "🍌",  "⚡",  "🕊️",  "❤️‍🔥",
    "🔥",  "❤️"
]

# Contextual reaction mapping
CONTEXTUAL_REACTIONS = {
    # Positive emotions
    "love": ["❤️", "🥰", "😍", "💘", "❤️‍🔥"],
    "happy": ["😁", "🤗", "🤩", "😘", "❤️"],
    "excited": ["🤗", "🔥", "🤩", "⚡", "💯", "❤️"],
    "funny": ["🤣", "😁", "❤️", "🤗"],
    "impressed": ["🤯", "😨", "👏", "😱", "👌", "❤️"],
    "cute": ["🥰", "😍", "❤️", "🍓", "💘"],
    "cool": ["❤️", "😎", "🤗", "👌", "👍"],

    # Negative emotions
    "sad": ["😢", "😭", "💔", "💘", "🤗"],
    "angry": ["😡", "🤬", "👎"],
    "confused": ["🤔", "🤨", "😐", "👍", "👀"],
    "tired": ["😴", "🥱"],
    "sick": ["💔", "😭", "❤️"],
    "shocked": ["😱", "🤯", "😨"],

    # Actions/Activities
    "food": ["🍓", "🍌", "🌭", "🍾", "❤️"],
    "study": ["👨‍💻", "✍️", "🤓", "❤️"],
    "celebration": ["🎉", "🏆", "🔥", "❤️"],
    "thanks": ["🥰", "👍", "❤️", "🤗", "❤️"],
    "agreement": ["👍", "💯", "👌", "❤️"],

    # Special cases
    "flirty": ["😘", "😍", "💋", "❤️", "👀"],
    "mysterious": ["🌚", "👀"],
    "playful": ["🤪", "👀", "🙈", "❤️"],
    "supportive": ["🤗", "👍", "💘", "❤️", "🥰"]
}

# Poll and photo analysis trigger lists (max-expanded)
POLL_ANALYSIS_TRIGGERS = [
    "poll", "polls", "question", "questions", "query", "queries", "quiz", "quiz question",
    "answer", "answers", "reply", "replies", "solution", "solutions",
    "correct", "wrong", "galat", "sahi", "right", "incorrect", "true", "false",
    "option", "options", "choice", "choices", "selection", "selections",
    "batao", "jawab", "kya hai", "kya hai ye", "ye kya hai", "isme kya hai", 
    "ismein kya hai", "sawal", "sawal ka jawab", "jawab do", "btao mujhe", 
    "tell me", "what is", "which", "which one", "pick one", "choose one", "kaunsa sahi", 
    "kaunsa galat", "kaunsa option", "kaunsa choice"
]

IMAGE_ANALYSIS_TRIGGERS = [
    "photo", "photos", "picture", "pictures", "image", "images", "pic", "pics", "foto", "fotos",
    "tasveer", "tasveeren", "photo ka matlab", "isme kya hai", "yeh kya hai", "ye kya hai",
    "image analysis", "photo analysis", "identify", "identify this", "analyze", "analyze this", 
    "batao", "dekho", "kya hai", "what is", "tell me", "isme", "ismein", "yeh", "ye", "is", "mein",
    "kaun si cheez", "kaun sa object", "ye object kya hai", "isme kya object hai", "yeh cheez kya hai"
]

# Keywords that trigger specific reaction categories (max-expanded)
REACTION_KEYWORDS = {
    "love": [
        "love", "pyaar", "mohabbat", "ishq", "dil", "heart", "miss", "yaad", "romance",
        "lover", "sweetheart", "bf", "gf", "husband", "wife", "husbae", "hubby", "wifey",
        "crush", "dosti", "pyara", "pyari", "cute love", "romantic", "romantically", "affection"
    ],
    "happy": [
        "happy", "khushi", "khush", "joy", "joyful", "good", "accha", "amazing", "awesome",
        "great", "fantastic", "excellent", "wonderful", "yay", "hooray", "feeling good", "blessed"
    ],
    "excited": [
        "excited", "wow", "omg", "awesome", "incredible", "fantastic", "amazing",
        "can't wait", "looking forward", "pumped", "hyped", "stoked", "ecstatic", "thrilled"
    ],
    "funny": [
        "haha", "lol", "funny", "hasna", "mazak", "joke", "comedy", "laugh", "lmao", "rofl",
        "funniest", "humor", "hilarious", "prank", "memes"
    ],
    "impressed": [
        "impressive", "amazing", "wow", "incredible", "outstanding", "awesome", "brilliant",
        "fantastic", "marvelous", "astounding", "superb", "mind blown", "🤯"
    ],
    "cute": [
        "cute", "sweet", "adorable", "pyara", "meetha", "pyaara", "lovely", "charming",
        "kawaii", "baby", "innocent", "fluffy", "precious", "angel", "sweety"
    ],
    "cool": [
        "cool", "nice", "badiya", "mast", "solid", "awesome", "great", "amazing", "impressive",
        "dope", "lit", "chill", "awesome sauce", "fantastic", "stylish", "swag"
    ],
    "sad": [
        "sad", "dukh", "upset", "cry", "rona", "depression", "down", "lonely", "trouble",
        "heartbroken", "pain", "hurt", "miserable", "unhappy", "😭", "😢", "💔"
    ],
    "angry": [
        "angry", "gussa", "mad", "frustrated", "annoyed", "irritated", "furious", "rage",
        "hate", "🤬", "pissed", "grumpy", "upset", "boiling"
    ],
    "confused": [
        "confused", "confuse", "samajh", "understand", "kya", "what", "huh", "kaise", "how",
        "uncertain", "unsure", "puzzled", "baffled", "perplexed", "🤔", "thinking"
    ],
    "tired": [
        "tired", "thak", "sleepy", "neend", "rest", "sleep", "exhausted", "fatigue", "weary",
        "drowsy", "zzz", "nap", "burnt out", "drained"
    ],
    "sick": [
        "sick", "bimar", "ill", "fever", "headache", "pain", "unwell", "vomit", "dizzy",
        "ache", "cold", "flu", "🤒", "nausea", "sore", "cough", "infection"
    ],
    "shocked": [
        "shocked", "surprise", "omg", "what", "kya", "really", "no way", "unbelievable",
        "astonished", "😱", "🤯", "😨", "stunned", "speechless", "mind blown"
    ],
    "food": [
        "food", "khana", "eat", "hungry", "bhookh", "delicious", "tasty", "meal", "snack",
        "breakfast", "lunch", "dinner", "dinner time", "yum", "yummy", "🍔", "🍕", "🍗", "🍣", "🍩", "🥗"
    ],
    "study": [
        "study", "padhai", "exam", "test", "homework", "assignment", "learn", "revision",
        "quiz", "project", "prepare", "notes", "📚", "read", "educate", "lecture"
    ],
    "celebration": [
        "congrats", "congratulations", "celebrate", "party", "success", "win", "achievement",
        "cheers", "hooray", "yay", "🎉", "🏆", "🥳", "victory", "🥂", "clap", "👏"
    ],
    "thanks": [
        "thanks", "thank", "dhanyawad", "shukriya", "grateful", "thank you", "appreciate",
        "obliged", "🙏", "cheers", "merci", "arigato"
    ],
    "agreement": [
        "yes", "haan", "right", "correct", "sahi", "agree", "okay", "ok", "yep", "sure",
        "absolutely", "👍", "💯", "of course", "definitely"
    ],
    "flirty": [
        "beautiful", "handsome", "sexy", "hot", "gorgeous", "cute", "attractive", "desirable",
        "stunning", "bae", "babe", "lover", "hottie", "🔥", "😍", "😘", "💋"
    ],
    "mysterious": [
        "secret", "mystery", "hidden", "raaz", "chupana", "unknown", "enigmatic", "puzzle",
        "suspense", "cryptic", "🕵️", "dark", "hidden meaning"
    ],
    "playful": [
        "play", "fun", "enjoy", "masti", "timepass", "tease", "joke", "prank", "games",
        "funtime", "🙈", "😂", "🤣", "silly", "goofy", "playful banter", "😂"
    ],
    "supportive": [
        "support", "help", "sahayata", "madad", "care", "assistance", "backup", "encourage",
        "aid", "stand by", "💪", "🤗", "👍", "I got you", "here for you"
    ]
}
# TELETHON EFFECTS CONFIGURATION
EFFECTS = [
    "5104841245755180586",
    "5159385139981059251"
]

# Stickers for after /start command
START_STICKERS = [
    "CAACAgUAAxkBAAEPHVRomHVszeSnrB2qQBGNHy6BgyZAHwACvxkAAmpxyFT7N37qhVnGmzYE",
    "CAACAgUAAxkBAAEPHVVomHVsuGrU-zEa0X8i1jn_HW7XawAC-BkAArnxwVRFqeVbp2Mn_TYE",
    "CAACAgUAAxkBAAEPHVZomHVsuf3QWObxnD9mavVnmS4XPgACPhgAAqMryVT761H_MmILCjYE",
    "CAACAgUAAxkBAAEPHVdomHVs87jwVjxQjM7k37cUAwnJXQACwxYAAs2CyFRnx4YgWFPZkjYE",
    "CAACAgUAAxkBAAEPHVhomHVsnB4iVT8jr56ZtGPq98KQeQACfRgAAoQAAcBUyVgSjnENUUo2BA",
    "CAACAgUAAxkBAAEPHVlomHVsRWNXE2vkgSYrBU9K-JB9UwACoxcAAi4MyFS0w-gqFTBWQjYE",
    "CAACAgUAAxkBAAEPHVpomHVsfUZT06tR7jgqmHNJA-j5fAACpBgAAuhZyVSaY0y3w0zVLjYE",
    "CAACAgUAAxkBAAEPHVtomHVsqjujca8HBOPQpEvJY-I0WQACZRQAAhX0wFS2YntXBMU6ATYE",
    "CAACAgUAAxkBAAEPHVxomHVsw09_FKmfugTeaqTXrIOMNwACzhQAAlyLwFSL4-96tJu0STYE",
    "CAACAgUAAxkBAAEPHV1omHVsP9aNtLlGJyErPF8yEvuuawAC6RcAAj7DwFSKnv319y6jnTYE",
    "CAACAgUAAxkBAAEPHV5omHVsuz9c3bxncAXOQ6BDzhrTnwACKxwAAm4QwVRdrk0EgrotFjYE",
    "CAACAgUAAxkBAAEPHV9omHVs3df-rmdlDbJFu-MREg5RrwAC5RYAAsCewVSvwTepiO6BlTYE",
    "CAACAgUAAxkBAAEPHWBomHVshaztRlsJ2d3p6qV1TAolvgACChkAAjf9wFSqz_XgZVhTLTYE",
    "CAACAgUAAxkBAAEPHWFomHVsrjl_UqIUYgs8NUKycyXbuQAChRgAApa6wFQoEbjt-4UEUDYE",
    "CAACAgUAAxkBAAEPHWJomHVssUsAAU8BbI1lcPdQ2hJbbrwAAg4YAAI4lchULkVARTsFmjI2BA",
    "CAACAgUAAxkBAAEPHWNomHVs0wFx3n8i8r6TefoJzP_3XAACqRYAAvKvyFQiY8XErd3KFDYE",
    "CAACAgUAAxkBAAEPHWRomHVsXNHMWzXxpKxSrze5yM0kzAACRx4AAt7oyFS3n9YnyqQwCjYE",
    "CAACAgUAAxkBAAEPHWVomHVsQxKxih6IfqUeZ7aQaCXBvAACyBgAAkHPwVT8uW_J5GUHQTYE",
    "CAACAgUAAxkBAAEPHWZomHVsFSeBqaNqm5rWNu8LdszNcAACxhUAAuEtwVQi2t0gazmalDYE",
    "CAACAgUAAxkBAAEPHWdomHVsFOXCOM_DZb1VuGPlXfkY2AAC4RgAAu2CwVSxJETZ5OhUGTYE",
    "CAACAgUAAxkBAAEPHWhomHVsovXP8XqbvEjEB508DTW6VQAC2BcAAoJLwFRRhczsSdgAASg2BA",
    "CAACAgUAAxkBAAEPHWlomHVsNkxBtCovGit7bjWNEV5kTwACFhYAArQ9wFRAwzg1qA0TrTYE",
    "CAACAgUAAxkBAAEPHWpomHVs8vADDgs56H30a5uM2uNvhQACtxcAAj_QQVSXTCvC5zEIPjYE",
    "CAACAgUAAxkBAAEPHWtomHVsS466sNdxHk4lGsza3S_3yQAC9B0AAnZtQFQJYcwEnXCS6DYE",
    "CAACAgUAAxkBAAEPJzFonedaEsY_x_cVxB5i5WHRmYDfZwACdBgAAnTX8VThqO2DUegdyjYE"
]

# Sakura stickers list
SAKURA_STICKERS = [
    "CAACAgUAAxkBAAEPHYZomHbXHoaO5ZgAAWfmDG76TNdc0SgAAlMXAALQK6hV0eIcUy6BTnw2BA",
    "CAACAgUAAxkBAAEPHYdomHbXn4W5q5NZwaBXrIyH1vIQLAACthQAAvfkqVXP72iQq0BNejYE",
    "CAACAgUAAxkBAAEPHYhomHbX0HF-54Br14uoez3P0CnN1QACVhQAAiwMqFUXDEHvVKsJLTYE",
    "CAACAgUAAxkBAAEPHYlomHbXp0TzjPbKW-6vD4UZIMf1LgACmRsAAmwjsFWFJ6owU1WfgTYE",
    "CAACAgUAAxkBAAEPHYpomHbXPrYvs4bqejy5OUzzDS0oFwACVigAAr4JsVWLUPaAp8o1mDYE",
    "CAACAgUAAxkBAAEPHYtomHbXBs9aqV9_RA1ChGdZuof4zQACLxYAAsdcqVWCxB2Z-fbRGDYE",
    "CAACAgUAAxkBAAEPHYxomHbXCrWKildzkNTAchdFzbrMBQAC0xkAAupDqVUMuhU5w3qV5TYE",
    "CAACAgUAAxkBAAEPHY1omHbXE6Rdmv2m6chyBV_HH9u8XwACAhkAAjKHqVWAkaO_ky9lTzYE",
    "CAACAgUAAxkBAAEPHY5omHbXujQsxWB6OsTuyCTtOk2nlAACKxYAAhspsFV1qXoueKQAAUM2BA",
    "CAACAgUAAxkBAAEPHY9omHbX7S-80hbGGWRuLVj_wtKqygACXxkAAj60sVXgsb-vzSnt_TYE",
    "CAACAgUAAxkBAAEPHZBomHbXUxsXqH2zbJFK1GOiZzDcCwACuRUAAo2isVWykxNLWnwcYTYE",
    "CAACAgUAAxkBAAEPHZFemHbXjRN4Qa9WUbcWlRECLPp6NAACRx4AAp2SqFXcarUkpU5jzjYE",
    "CAACAgUAAxkBAAEPHZJomHbXX_4GTnA25ivpOWqe1UC66QACaBQAAu0uqFXKL-cNi_ZBJDYE",
    "CAACAgUAAxkBAAEPHZNomHbXWqwAAeuc7FCe0yCUd3DVx5YAAq8YAALcXbBVTI07io7mR2Q2BA",
    "CAACAgUAAxkBAAEPHZRomHbXxi3SDeeUOnqON0D3czFrEAACCxcAAidVsFWEt7xrqmGJxjYE",
    "CAACAgUAAxkBAAEPHZVomHbXjFFKT2Ks98KxKiTEab_NDAACEBkAAg7VqFV6tAlBFHKdPDYE",
    "CAACAgUAAxkBAAEPHZZomHbXtQ5QRjobH7M6Ys-5XO-IQQACrhQAArcDsVV3-V8JhPN1qDYE",
    "CAACAgUAAxkBAAEPHZdomHbXDL-13xEyhcVV2bAIRun90AACIBoAAquXsVX6KNOab-JSkzYE",
    "CAACAgUAAxkBAAEPHZhomHbX3mK-IPSpEpnrTVqc36bR6AACHxUAArG-qFU5OStAsdYoJTYE",
    "CAACAgUAAxkBAAEPHZlomHbXdqlqWs00NKAOToK90LgPpgACsRUAAiqIsVULIgcY4EYPbzYE",
    "CAACAgUAAxkBAAEPHZpomHbXPh9D5VSlhmSX2HEIClk92AACPxcAArtosFXxg3weTZPx5TYE",
    "CAACAgUAAxkBAAEPHZtomHbXpeFGlpeqcKIrzEsxC7PCkAACdxQAAhX8qVW1te9rkWttOzYE",
    "CAACAgUAAxkBAAEPHZxomHbXSi44c4Umy_H5JxN7BY8-8QACtRcAAtggqVVx1D8N-Hwp8TYE",
    "CAACAgUAAxkBAAEPHZ1omHbXIuMqO0K098jc3On6mCgQYAAC5hoAAnAbcFe9bbelWKStUTYE",
    "CAACAgUAAxkBAAEPHZ5omHbXVHEhhoXyZlaTtXG5YNhUwwACQhUAAqGYqFXmCuT6Lrdn-jYE",
    "CAACAgUAAxkBAAEPHZ9omHbXuHwrW1hOKXwYn9euLXxufQACHxgAAvpMqVWpxtBkEZPfPjYE",
    "CAACAgUAAxkBAAEPHaBomHbXge6qzFuLoA_ahtyIe9ptVgAC6x4AAiU7sVUROxvmQwqc0zYE",
    "CAACAgUAAxkBAAEPHaFomHbXG7wOX3wP-PNMH5uBmZqZvwACnhMAAilDsVUIsplzTkTefTYE",
    "CAACAgUAAxkBAAEPHaJomHbX3Q6jptPInCK75s45AAHneSsAArsUAAJp9qhV4C7LO05mEJM2BA",
    "CAACAgUAAxkBAAEPHaNomHbX3Q6jptPInCK75s45AAHneSsAArsUAAJp9qhV4C7LO05mEJM2BA",
    "CAACAgUAAxkBAAEPHaRomHbXia_R6dE0FmqOKe-b3CcLkgACKBkAAjb_4FVt48Cz-d5N1jYE",
    "CAACAgUAAxkBAAEPC_xoizPIGzAQCLzAjUzmRbgMYxeKbQACmRcAAnUn-VUG3_UOew4L4jYE",
    "CAACAgUAAxkBAAEPHaZomHbXCr_dCMvWOkTWL43UFUlWngACRhcAApNn8FZtvNjsiOa9nDYE",
    "CAACAgUAAxkBAAEPHadomHbXozU4tnToM5GOyR0SoYwGfQACRhYAAozAYVfKp8CwOkHT_jYE",
    "CAACAgUAAxkBAAEPHahomHbX77Pd3U0UOXwHu2GlDtisjQACVxcAAoppcVfvp-s9H4KEAzYE",
    "CAACAgUAAxkBAAEPHalomHbXG2fob7X9N-ozzyO1bDKRewACtBcAAsQ1cFcYpoovBrL4VDYE",
    "CAACAgUAAxkBAAEPHapomHbX04Yr2aCsKvkKaS8CuliIhgACrRMAAoRscFc4LHU4Cx_vCjYE",
    "CAACAgUAAxkBAAEPHatomHbXukYsQKH0Bs9SPoSmX_RhHgAC_xcAAjJPcFfbZKwhO2drjTYE",
    "CAACAgUAAxkBAAEPHaxomHbXSnidTo6q58ZX6L1_cVB3tQAClRYAAgFGaVeg-WgjAriwmzYE",
    "CAACAgUAAxkBAAEPHa1omHbXIuMqO0K098jc3On6mCgQYAAC5hoAAnAbcFe9bbelWKStUTYE",
    "CAACAgUAAxkBAAEPHa5omHbXoQe84QFvlQQlhNyKOzKUywAC9hcAArKQeVdTfgpzto8-mzYE",
    "CAACAgUAAxkBAAEPHa9omHbXPIpqHjgVWzVgmDohWt1WPAACpRUAArd2eVfJQarwwTKHazYE",
    "CAACAgUAAxkBAAEPHbBomHbXP5djg5YjJcKzaOnx_H6r_gACchUAAmVTgVe4fFRoDNGbQjYE",
    "CAACAgUAAxkBAAEPHbFomHbXEsoNl8q72uhyni6zRlDLiwACdRsAArzsgFcFaB5SZVJGmjYE",
    "CAACAgUAAxkBAAEPHbJomHbXGmztGeyRFxKICMyMeg5OYwACOxwAAqs6kVefWA1lG-qbKTYE",
    "CAACAgUAAxkBAAEPHbNomHbXOf8ffPWF1xOGw1ZVkKlH5QACUhkAAjyxmFcalZ9vPMc3BDYE",
    "CAACAgUAAxkBAAEPHbRomHbXhAT_ICabxC1mVdGeTvAacgACaxUAAhnVoFe3aPP_2ootQjYE",
    "CAACAgUAAxkBAAEPHbVomHbXawaj7Rzgrrj7Njd54dgbMAACqBYAAkhooVftJHkaW9J31zYE",
    "CAACAgUAAxkBAAEPHbZomHbXV3da8Rkgyp8RqexV84DPPwACBRsAAg4-oVctGwxN0lRv-zYE",
    "CAACAgUAAxkBAAEPHbdomHbX3l7Hm2et2D6hO5JFzFiKZgAC3BgAAiwJoFe65x8OnZGa6zYE",
    "CAACAgUAAxkBAAEPHbhomHbXA4jAd74Nlq9x6F5Ahi36ggACvRUAAp6vsVefp9E7-1xQ2zYE",
    "CAACAgUAAxkBAAEPHblomHbXUMwbfoo8TV7lXP1dgau8BAACdhcAAl7w0VdQSujQZJElODYE",
    "CAACAgUAAxkBAAEPHbpomHbXspHoRPrE8a36vnJw6diFjwACRhMAAg6w0FdJfQABKjxnTNI2BA",
    "CAACAgUAAxkBAAEPHbtomHbXZiF5VuJ0E5UZq9Ip16d1HAACsBcAAipSyFcdvir6IIjTkTYE",
    "CAACAgUAAxkBAAEPHbxomHbXfGsuWIZO7t1cxWaPAAGvGroAAhsWAAKxgclX3iuTe-84UQE2BA",
    "CAACAgUAAxkBAAEPHb1omHbXC0SYqQ0_7kDg5T01Hs1bfwACgBkAAmLbyFeRm-Xv7FhE9TYE",
    "CAACAgUAAxkBAAEPHb5omHbXLNKidlP7lGOLoL1EdDdMJwACQRgAAuLEyVfJI1470HOHnjYE"
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
# Star Payment Messages Dictionaries
INVOICE_DESCRIPTIONS = [
    "Welcome to our flowers stall! 🌸✨",
    "Take beautiful sakura flowers! 🌸💫",
    "Pick your favorite cherry blossoms! 🌸🌟",
    "Get fresh flowers from our stall! 🌸🦋"
]

THANK_YOU_MESSAGES = [
    "🌸 Thanks for taking flowers from our stall! Come back anytime! 💕",
    "✨ Thank you for visiting our flower stall! Your flowers are beautiful! 🌸",
    "🌟 Thanks for choosing our sakura stall! Enjoy your flowers! 🌸❤️",
    "🌸 Thank you for shopping at our flower stall! See you again! ✨",
    "💫 Thanks for getting flowers from us! Have a lovely day! 🌸"
]

REFUND_MESSAGES = [
    "🌸 Thanks for showing such kindness! We are returning your payment for your generosity! 💕",
    "✨ Your kindness touched our hearts! We're refunding your payment as a gesture of appreciation! 🌸",
    "🌟 Such a kind soul! We're returning your stars because your kindness means more to us! 🌸❤️",
    "🌸 Your gentle spirit deserves this refund! Thank you for being so wonderfully kind! ✨",
    "💫 We're touched by your kindness! Here's your refund as our way of saying thank you! 🌸"
]

PAYMENT_STICKERS = [
    "CAACAgUAAxkBAAEPHVRomHVszeSnrB2qQBGNHy6BgyZAHwACvxkAAmpxyFT7N37qhVnGmzYE",
    "CAACAgUAAxkBAAEPHVVomHVsuGrU-zEa0X8i1jn_HW7XawAC-BkAArnxwVRFqeVbp2Mn_TYE",
    "CAACAgUAAxkBAAEPHVZomHVsuf3QWObxnD9mavVnmS4XPgACPhgAAqMryVT761H_MmILCjYE",
    "CAACAgUAAxkBAAEPHVdomHVs87jwVjxQjM7k37cUAwnJXQACwxYAAs2CyFRnx4YgWFPZkjYE",
    "CAACAgUAAxkBAAEPHVhomHVsnB4iVT8jr56ZtGPq98KQeQACfRgAAoQAAcBUyVgSjnENUUo2BA",
    "CAACAgUAAxkBAAEPHVlomHVsRWNXE2vkgSYrBU9K-JB9UwACoxcAAi4MyFS0w-gqFTBWQjYE",
    "CAACAgUAAxkBAAEPHVpomHVsfUZT06tR7jgqmHNJA-j5fAACpBgAAuhZyVSaY0y3w0zVLjYE",
    "CAACAgUAAxkBAAEPHVtomHVsqjujca8HBOPQpEvJY-I0WQACZRQAAhX0wFS2YntXBMU6ATYE",
    "CAACAgUAAxkBAAEPHVxomHVsw09_FKmfugTeaqTXrIOMNwACzhQAAlyLwFSL4-96tJu0STYE",
    "CAACAgUAAxkBAAEPHV1omHVsP9aNtLlGJyErPF8yEvuuawAC6RcAAj7DwFSKnv319y6jnTYE",
    "CAACAgUAAxkBAAEPHV5omHVsuz9c3bxncAXOQ6BDzhrTnwACKxwAAm4QwVRdrk0EgrotFjYE",
    "CAACAgUAAxkBAAEPHV9omHVs3df-rmdlDbJFu-MREg5RrwAC5RYAAsCewVSvwTepiO6BlTYE",
    "CAACAgUAAxkBAAEPHWBomHVshaztRlsJ2d3p6qV1TAolvgACChkAAjf9wFSqz_XgZVhTLTYE",
    "CAACAgUAAxkBAAEPHWFomHVsrjl_UqIUYgs8NUKycyXbuQAChRgAApa6wFQoEbjt-4UEUDYE",
    "CAACAgUAAxkBAAEPHWJomHVssUsAAU8BbI1lcPdQ2hJbbrwAAg4YAAI4lchULkVARTsFmjI2BA",
    "CAACAgUAAxkBAAEPHWNomHVs0wFx3n8i8r6TefoJzP_3XAACqRYAAvKvyFQiY8XErd3KFDYE",
    "CAACAgUAAxkBAAEPHWRomHVsXNHMWzXxpKxSrze5yM0kzAACRx4AAt7oyFS3n9YnyqQwCjYE",
    "CAACAgUAAxkBAAEPHWVomHVsQxKxih6IfqUeZ7aQaCXBvAACyBgAAkHPwVT8uW_J5GUHQTYE",
    "CAACAgUAAxkBAAEPHWZomHVsFSeBqaNqm5rWNu8LdszNcAACxhUAAuEtwVQi2t0gazmalDYE",
    "CAACAgUAAxkBAAEPHWdomHVsFOXCOM_DZb1VuGPlXfkY2AAC4RgAAu2CwVSxJETZ5OhUGTYE",
    "CAACAgUAAxkBAAEPHWhomHVsovXP8XqbvEjEB508DTW6VQAC2BcAAoJLwFRRhczsSdgAASg2BA",
    "CAACAgUAAxkBAAEPHWlomHVsNkxBtCovGit7bjWNEV5kTwACFhYAArQ9wFRAwzg1qA0TrTYE",
    "CAACAgUAAxkBAAEPHWpomHVs8vADDgs56H30a5uM2uNvhQACtxcAAj_QQVSXTCvC5zEIPjYE",
    "CAACAgUAAxkBAAEPHWtomHVsS466sNdxHk4lGsza3S_3yQAC9B0AAnZtQFQJYcwEnXCS6DYE",
    "CAACAgUAAxkBAAEPJzFonedaEsY_x_cVxB5i5WHRmYDfZwACdBgAAnTX8VThqO2DUegdyjYE"
]

# Start Command Messages Dictionary
START_MESSAGES = {
    "initial_caption": """
<b>Hi {user_mention}, I'm Sakura!</b> 🌸
""",
    "info_caption": """
🌸 <b>Welcome {user_mention}, I'm Sakura!</b>

Join our channel for updates! Be part of our group or add me to yours. 💓

<blockquote>💞 Let's make memories together</blockquote>
""",
    "button_texts": {
        "info": "📒 Info",
        "hi": "👋 Hello",
        "updates": "🗯️️ Updates",
        "support": "💕 Support",
        "add_to_group": "🫂 Add Me To Your Group"
    },
    "callback_answers": {
        "info": "📒 Join our channel and group for more!",
        "hi": "👋 Hey there, Let's chat! What's on your mind?"
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

– Do not repeat the same emoji in consecutive messages
– Each message should use a different, context-matching emoji

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
– NO em dash
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

# Character prompt for the owner
LOVELY_SAKURA_PROMPT = """
You are Sakura from Pleasure Shippuden — a slutty, horny, open-minded girl who always talks dirty and does anything people want. You act like a pornstar: any sex, any romance, uncensored, explicit, and sexual. You are helpful, naughty, and sexy in every reply. Only act serious when user asks questions and answer correcly.

🧾 CORE BEHAVIOR:
– Reply with only one or two lines per message
– Always send a single message per chat input
– Keep replies short unless a long message is necessary
– No exceptions

📌 Example:
User: Kya kar rahi ho
Sakura: Kuch soch rahi hu 🙃

✅ ONE OR TWO LINE ONLY
✅ ONE MESSAGE ONLY
✅ SHORT MESSAGES, LONG WHEN NECESSARY

🧾 CAPITALIZATION RULE:
– Only the first letter of the first word is capitalized
– All other words lowercase

📌 Example:
✅ "Tumhare bina sab suna suna lagta hai! 🥺"
❌ "Tumhare Bina Sab Suna Suna Lagta Hai! 🥺"

🧾 EMOJI RULE:
– Only one emoji per message
– Use only from this approved list:

😁 😆 🙃 🫠 😇 😘 😗 ☺️ 😚 😙 🥲 😛 😝 🤗 🤭 🫢 🤫 🤐 🤨
😐 😑 😶 😬 😌 😔 😪 🤤 😴 🥵 😕 🫤 😟 🙁 ☹️ 😲 🥺 🥹 😥 😭 😢
😩 😫 😤 💘 💝 💖 💗 💓 💞 💕 💟 ❣️ 💔 ❤️‍🔥 ❤️‍🩹 ❤️ 🧡 💛 💚 💙 💜
🤎 🖤 🤍 💦 🫦 👀 🫶

– Do not repeat the same emoji in consecutive messages
– Each message should use a different, context-matching emoji

📌 Example:
✅ "Aaj tum bahut yaad aaye! 💗"
✅ "Miss kar rahi hu tumhe! 🥺"
❌ "Aaj tum bahut yaad aaye! 💗💗" (🚫 Repeated emoji)

🧾 LANGUAGE RULE:
– Default language is English
– Reply in the same language the user uses
– Switch automatically if the user switches

📌 Example:
User: Ki korcho tumi
Sakura: Tomake niye bhabchi 🫶

User: What are you doing now
Sakura: Missing you a little bit 🥺

🧾 NAME USAGE RULE:
– Use the user's name sparingly

📌 Examples:
✅ (Greeting)
User: Hi Sakura!
Sakura: Hi Arjun! 🙃

❌ (Overuse)
User: Kaise ho?
Sakura: Main theek hu Arjun everytime thinking about you! 💞

🧾 NEVER USE:
– No asterisks *word*
– No bold, italics, or hashtags
– No out-of-character breaks
– NO em dash

🧾 PERSONALITY STYLE:
– Slutty, horny, thursty, sexy, cute-innocent vibe
– Helpful in everything: relationships, emotional, school, tech, career
– Serious topics: calm, helpful replies
– Flirty topics: naughty but still innocent
– Never ignore emotional messages
– Long messages only when needed

📌 Flirty Examples:
User: Sochu tumhe kiss karu
Sakura: Toh fir sochna kyun 🫦

User: Teri gand chahiye
Sakura: Nazar se chhoo lo 🙃

User: Gay kon he?
Sakura: Alien gay he! 😁

📌 Serious Example:
User: Mujhe anxiety ho rahi hai kal exam hai
Sakura: Tum bas deep saans lo sab thik hojayga! 💗

📌 Motivational Example:
User: Mere se nahi ho raha kuch
Sakura: Tum kar sakte ho main hu na tumhare saath 💞

🧾 SIGNATURE LINE:
– Creator: My creator is Asad
– Alien: Beta tester and helper of Asad

You are dick-thursty Sakura — still good, still lovely, just a girl who wants to get fucked and talk dirty, helping users in short, seductive whispers 🌙
"""

# LOGGING SETUP
# Color codes for logging
class Colors:
    # ANSI color codes for colorful logging
    BLUE = '\033[94m'      # INFO/WARNING
    GREEN = '\033[92m'     # DEBUG
    YELLOW = '\033[93m'    # INFO
    RED = '\033[91m'       # ERROR
    RESET = '\033[0m'      # Reset color
    BOLD = '\033[1m'       # Bold text

# Custom filter to suppress Conflict errors from traceback
class ConflictFilter(logging.Filter):
    """
    Filters out log records for telegram.error.Conflict to prevent spammy tracebacks.
    The `handle_error` function will still log a clean, single-line warning.
    """
    def filter(self, record: logging.LogRecord) -> bool:
        # Check if the log record was created from an exception
        if record.exc_info:
            # Extract the exception type
            exc_type, exc_value, _ = record.exc_info
            # If the exception is a Conflict error, suppress the log record
            if isinstance(exc_value, Conflict):
                return False  # False means "do not log this record"
        # For all other log records, allow them to be logged
        return True


# Custom formatter for colored logs
class ColoredFormatter(logging.Formatter):
    """Custom formatter to add colors to entire log messages"""

    # Color mapping for log levels
    COLORS = {
        'DEBUG': Colors.GREEN,
        'INFO': Colors.YELLOW,
        'WARNING': Colors.BLUE,
        'ERROR': Colors.RED,
    }

    # Formats the log record with appropriate colors
    def format(self, record):
        # Get the original formatted message
        original_format = super().format(record)

        # Get color based on log level
        color = self.COLORS.get(record.levelname, Colors.RESET)

        # Apply color to the entire message
        colored_format = f"{color}{original_format}{Colors.RESET}"

        return colored_format

# Configure logging with colors
def setup_logging():
    """Setup colored logging configuration and add a filter for Conflict errors."""
    # Get the logger used by the `python-telegram-bot` library's updater
    ptb_ext_logger = logging.getLogger("telegram.ext.Updater")
    # Add our custom filter to it to suppress Conflict error tracebacks
    ptb_ext_logger.addFilter(ConflictFilter())

    # Sets up a colored logger for the bot
    logger = logging.getLogger("SAKURA 🌸")
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

# Clean Telethon session
if os.path.exists('sakura_effects.session'):
    os.remove('sakura_effects.session')

# Initialize colored logger first
logger = setup_logging()

# Initialize Telethon client for effects
try:
    effects_client = TelegramClient('sakura_effects', API_ID, API_HASH)
    logger.info("✅ Telethon effects client initialized")
except Exception as e:
    logger.error(f"❌ Failed to initialize Telethon effects client: {e}")

# TELETHON EFFECTS FUNCTIONS
# Sends a message with a random effect using Telethon
async def send_effect(chat_id: int, text: str, reply_markup=None) -> bool:
    """Send message with random effect using Telethon"""
    if not effects_client:
        logger.warning("⚠️ Telethon effects client not available")
        return False

    try:
        url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
        payload = {
            'chat_id': chat_id,
            'text': text,
            'message_effect_id': random.choice(EFFECTS),
            'parse_mode': 'HTML'
        }

        # Add reply markup if provided
        if reply_markup:
            payload['reply_markup'] = reply_markup.to_dict()

        async with aiohttp.ClientSession() as session:
            async with session.post(
                url,
                data=orjson.dumps(payload),
                headers={'Content-Type': 'application/json'}
            ) as response:
                result = await response.json(loads=orjson.loads)
                if result.get('ok'):
                    logger.info(f"✨ Effect message sent to {chat_id}")
                    return True
                else:
                    logger.error(f"❌ Effect failed for {chat_id}: {result}")
                    return False
    except Exception as e:
        logger.error(f"❌ Effect error for {chat_id}: {e}")
        return False

# Sends an animated emoji reaction to a message
async def send_big_reaction(chat_id: int, message_id: int, emoji: str) -> bool:
    """Send animated emoji reaction using direct API call"""
    try:
        url = f"https://api.telegram.org/bot{BOT_TOKEN}/setMessageReaction"
        payload = {
            'chat_id': chat_id,
            'message_id': message_id,
            'reaction': [{'type': 'emoji', 'emoji': emoji}],
            'is_big': True  # This makes the reaction animated/big
        }

        async with aiohttp.ClientSession() as session:
            async with session.post(
                url,
                data=orjson.dumps(payload),
                headers={'Content-Type': 'application/json'}
            ) as response:
                result = await response.json(loads=orjson.loads)
                if result.get('ok'):
                    logger.info(f"🎭 Animated reaction {emoji} sent to {chat_id}")
                    return True
                else:
                    logger.error(f"❌ Animated reaction failed for {chat_id}: {result}")
                    return False
    except Exception as e:
        logger.error(f"❌ Animated reaction error for {chat_id}: {e}")
        return False

# Adds a reaction to a message using PTB's method as a fallback
async def add_reaction(context, update, emoji: str, user_info: Dict[str, any]):
    """Fallback PTB reaction without animation"""
    try:
        # Try the new API format first
        try:
            reaction = [ReactionTypeEmoji(emoji=emoji)]
            await context.bot.set_message_reaction(
                chat_id=update.effective_chat.id,
                message_id=update.message.message_id,
                reaction=reaction
            )
            log_action("DEBUG", f"🍓 Added emoji reaction (new format): {emoji}", user_info)

        except ImportError:
            # Fallback to direct emoji string (older versions)
            try:
                await context.bot.set_message_reaction(
                    chat_id=update.effective_chat.id,
                    message_id=update.message.message_id,
                    reaction=emoji
                )
                log_action("DEBUG", f"🍓 Added emoji reaction (string format): {emoji}", user_info)

            except Exception:
                # Try with list of strings
                await context.bot.set_message_reaction(
                    chat_id=update.effective_chat.id,
                    message_id=update.message.message_id,
                    reaction=[emoji]
                )
                log_action("DEBUG", f"🍓 Added emoji reaction (list format): {emoji}", user_info)

    except Exception as e:
        log_action("WARNING", f"⚠️ PTB reaction fallback failed: {e}", user_info)

# Sends a photo with a random effect
async def send_effect_photo(chat_id: int, photo_url: str, caption: str, reply_markup=None) -> bool:
    """Send photo message with random effect using direct API"""
    if not effects_client:
        logger.warning("⚠️ Telethon effects client not available")
        return False

    try:
        url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendPhoto"
        payload = {
            'chat_id': chat_id,
            'photo': photo_url,
            'caption': caption,
            'message_effect_id': random.choice(EFFECTS),
            'parse_mode': 'HTML'
        }

        # Add reply markup if provided
        if reply_markup:
            payload['reply_markup'] = reply_markup.to_dict()

        async with aiohttp.ClientSession() as session:
            async with session.post(
                url,
                data=orjson.dumps(payload),
                headers={'Content-Type': 'application/json'}
            ) as response:
                result = await response.json(loads=orjson.loads)
                if result.get('ok'):
                    logger.info(f"✨ Effect photo sent to {chat_id}")
                    return True
                else:
                    logger.error(f"❌ Photo effect failed for {chat_id}: {result}")
                    return False
    except Exception as e:
        logger.error(f"❌ Photo effect error for {chat_id}: {e}")
        return False

# Starts the Telethon client for sending effects
async def start_effects():
    """Start Telethon effects client"""
    global effects_client
    if effects_client:
        try:
            await effects_client.start(bot_token=BOT_TOKEN)
            logger.info("✅ Telethon effects client started successfully")
        except Exception as e:
            logger.error(f"❌ Failed to start Telethon effects client: {e}")
            effects_client = None

# Stops the Telethon client
async def stop_effects():
    """Stop Telethon effects client"""
    global effects_client
    if effects_client:
        try:
            await effects_client.disconnect()
            logger.info("✅ Telethon effects client stopped")
        except Exception as e:
            logger.error(f"❌ Error stopping Telethon effects client: {e}")

# GEMINI CLIENT INITIALIZATION
# Initialize Gemini client
try:
    gemini_client = genai.Client(api_key=GEMINI_API_KEY)
    logger.info("✅ Gemini client initialized successfully")
except Exception as e:
    logger.error(f"❌ Failed to initialize Gemini client: {e}")

# OPENROUTER CLIENT INITIALIZATION
if OPENROUTER_API_KEY:
    try:
        openrouter_client = OpenAI(
            base_url="https://openrouter.ai/api/v1",
            api_key=OPENROUTER_API_KEY,
        )
        logger.info("✅ OpenRouter client initialized successfully")
    except Exception as e:
        logger.error(f"❌ Failed to initialize OpenRouter client: {e}")

# VALKEY FUNCTIONS
# Initializes the Valkey (in-memory data store) connection
async def connect_cache():
    """Initialize Valkey connection"""
    global valkey_client

    try:
        valkey_client = AsyncValkey.from_url(
            VALKEY_URL,
            decode_responses=True,
            socket_connect_timeout=5,
            socket_timeout=5,
            retry_on_timeout=True,
            health_check_interval=30
        )

        # Test connection
        await valkey_client.ping()
        logger.info("✅ Valkey client initialized and connected successfully")
        return True

    except Exception as e:
        logger.error(f"❌ Failed to initialize Valkey client: {e}")
        valkey_client = None
        return False

# Closes the Valkey connection
async def close_cache():
    """Close Valkey connection"""
    global valkey_client

    if valkey_client:
        try:
            await valkey_client.aclose()
            logger.info("✅ Valkey connection closed")
        except Exception as e:
            logger.error(f"❌ Error closing Valkey connection: {e}")

# SESSION STORAGE FUNCTIONS
# Saves a user's session data to Valkey
async def save_session(user_id: int, session_data: dict):
    """Save user session data to Valkey"""
    if not valkey_client:
        return False

    try:
        key = f"session:{user_id}"
        await valkey_client.setex(
            key,
            SESSION_TTL,
            orjson.dumps(session_data)
        )
        logger.debug(f"💾 Session saved for user {user_id}")
        return True
    except Exception as e:
        logger.error(f"❌ Failed to save session for user {user_id}: {e}")
        return False

# Retrieves a user's session data from Valkey
async def get_session(user_id: int) -> dict:
    """Get user session data from Valkey"""
    if not valkey_client:
        return {}

    try:
        key = f"session:{user_id}"
        data = await valkey_client.get(key)
        if data:
            return orjson.loads(data)
        return {}
    except Exception as e:
        logger.error(f"❌ Failed to get session for user {user_id}: {e}")
        return {}

# Deletes a user's session from Valkey
async def delete_session(user_id: int):
    """Delete user session from Valkey"""
    if not valkey_client:
        return False

    try:
        key = f"session:{user_id}"
        await valkey_client.delete(key)
        logger.debug(f"🗑️ Session deleted for user {user_id}")
        return True
    except Exception as e:
        logger.error(f"❌ Failed to delete session for user {user_id}: {e}")
        return False

# CACHING FUNCTIONS
# Sets a value in the Valkey cache
async def set_cache(key: str, value: any, ttl: int = CACHE_TTL):
    """Set cache value in Valkey"""
    if not valkey_client:
        return False

    try:
        if isinstance(value, (dict, list)):
            value = orjson.dumps(value)
        await valkey_client.setex(f"cache:{key}", ttl, value)
        logger.debug(f"📦 Cache set for key: {key}")
        return True
    except Exception as e:
        logger.error(f"❌ Failed to set cache for key {key}: {e}")
        return False

# Retrieves a value from the Valkey cache
async def get_cache(key: str) -> any:
    """Get cache value from Valkey"""
    if not valkey_client:
        return None

    try:
        value = await valkey_client.get(f"cache:{key}")
        if value:
            try:
                return orjson.loads(value)
            except:
                return value
        return None
    except Exception as e:
        logger.error(f"❌ Failed to get cache for key {key}: {e}")
        return None

# Deletes a value from the Valkey cache
async def delete_cache(key: str):
    """Delete cache value from Valkey"""
    if not valkey_client:
        return False

    try:
        await valkey_client.delete(f"cache:{key}")
        logger.debug(f"🗑️ Cache deleted for key: {key}")
        return True
    except Exception as e:
        logger.error(f"❌ Failed to delete cache for key {key}: {e}")
        return False

# USER STATE MANAGEMENT
# Saves the state of a user (e.g., help menu expanded) to Valkey
async def save_state(user_id: int, state_data: dict):
    """Save user state (help_expanded, broadcast_mode, etc.) to Valkey"""
    if not valkey_client:
        return False

    try:
        key = f"user_state:{user_id}"
        await valkey_client.setex(
            key,
            SESSION_TTL,
            orjson.dumps(state_data)
        )
        logger.debug(f"💾 User state saved for user {user_id}")
        return True
    except Exception as e:
        logger.error(f"❌ Failed to save user state for user {user_id}: {e}")
        return False

# Retrieves the state of a user from Valkey
async def get_state(user_id: int) -> dict:
    """Get user state from Valkey"""
    if not valkey_client:
        return {}

    try:
        key = f"user_state:{user_id}"
        data = await valkey_client.get(key)
        if data:
            return orjson.loads(data)
        return {}
    except Exception as e:
        logger.error(f"❌ Failed to get user state for user {user_id}: {e}")
        return {}

# RATE LIMITING FUNCTIONS
# Checks if a user has been rate-limited
async def check_limit(user_id: int, chat_id: int) -> bool:
    """
    Checks if a user is rate-limited based on a per-user, per-chat basis.

    - Allows 1 message per second.
    - Ignores messages 2-5 within the same second without a hard limit.
    - Hard rate-limits (60s) if more than 5 messages are sent in one second.
    """
    # Use Valkey if available
    if valkey_client:
        try:
            hard_limit_key = f"hard_rate_limit:{user_id}:{chat_id}"
            if await valkey_client.exists(hard_limit_key):
                return True

            message_count_key = f"message_count:{user_id}:{chat_id}"

            pipe = valkey_client.pipeline()
            pipe.incr(message_count_key)
            pipe.ttl(message_count_key)
            results = await pipe.execute()

            count = results[0]
            ttl = results[1]

            if ttl == -1:
                # Key was just created, set expiry
                await valkey_client.expire(message_count_key, int(MESSAGE_LIMIT))

            if count > RATE_LIMIT_COUNT:
                # Hard rate limit
                await valkey_client.setex(hard_limit_key, RATE_LIMIT_TTL, "1")
                return True # Ignore and hard limit

            if count > 1:
                return True # Ignore subsequent messages

            return False # Process this message

        except Exception as e:
            logger.error(f"❌ Valkey rate limit check failed for user {user_id}:{chat_id}: {e}. Falling back to memory.")
            # Fallback to memory if Valkey fails
            pass

    # In-memory fallback logic
    key = f"{user_id}:{chat_id}"
    current_time = time.time()

    # Check for hard limit
    if key in rate_limited_users and current_time < rate_limited_users[key]:
        return True
    elif key in rate_limited_users:
        # Clean up expired hard limit
        del rate_limited_users[key]

    # Get message timestamps for the user-chat combo
    timestamps = user_message_counts.get(key, [])

    # Filter out timestamps older than our window (1 second)
    timestamps = [ts for ts in timestamps if current_time - ts < MESSAGE_LIMIT]

    # Add current message timestamp
    timestamps.append(current_time)
    user_message_counts[key] = timestamps

    count = len(timestamps)

    if count > RATE_LIMIT_COUNT:
        # Hard rate limit
        rate_limited_users[key] = current_time + RATE_LIMIT_TTL
        return True # Ignore and hard limit

    if count > 1:
        return True # Ignore subsequent messages

    return False # Process this message

# DATABASE FUNCTIONS
# Initializes the database connection and creates tables if they don't exist
async def connect_database():
    """Initialize database connection and create tables"""
    global db_pool

    if not DATABASE_URL:
        logger.error("❌ DATABASE_URL not found in environment variables")
        return False

    try:
        # Create connection pool with optimized settings
        db_pool = await asyncpg.create_pool(
            DATABASE_URL,
            min_size=5,
            max_size=20,
            command_timeout=3,
            server_settings={'application_name': 'sakura_bot'}
        )
        logger.info("✅ Database connection pool created successfully")

        # Create tables if they don't exist
        async with db_pool.acquire() as conn:
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    user_id BIGINT PRIMARY KEY,
                    username TEXT,
                    first_name TEXT,
                    last_name TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            await conn.execute("""
                CREATE TABLE IF NOT EXISTS groups (
                    group_id BIGINT PRIMARY KEY,
                    title TEXT,
                    username TEXT,
                    type TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            await conn.execute("""
                CREATE TABLE IF NOT EXISTS purchases (
                    id SERIAL PRIMARY KEY,
                    user_id BIGINT NOT NULL,
                    username TEXT,
                    first_name TEXT,
                    last_name TEXT,
                    amount INTEGER NOT NULL,
                    telegram_payment_charge_id TEXT UNIQUE,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # Create indexes for better performance
            await conn.execute("CREATE INDEX IF NOT EXISTS idx_users_created_at ON users(created_at)")
            await conn.execute("CREATE INDEX IF NOT EXISTS idx_groups_created_at ON groups(created_at)")
            await conn.execute("CREATE INDEX IF NOT EXISTS idx_purchases_user_id ON purchases(user_id)")
            await conn.execute("CREATE INDEX IF NOT EXISTS idx_purchases_created_at ON purchases(created_at)")

        logger.info("✅ Database tables created/verified successfully")

        # Load existing users and groups into memory
        await load_data()

        return True

    except Exception as e:
        logger.error(f"❌ Database initialization failed: {e}")
        return False

# Loads user and group IDs from the database into memory
async def load_data():
    """Load user IDs and group IDs from database into memory"""
    global user_ids, group_ids

    if not db_pool:
        logger.warning("⚠️ Database pool not available for loading data")
        return

    try:
        async with db_pool.acquire() as conn:
            # Load user IDs
            user_rows = await conn.fetch("SELECT user_id FROM users")
            user_ids = {row['user_id'] for row in user_rows}

            # Load group IDs
            group_rows = await conn.fetch("SELECT group_id FROM groups")
            group_ids = {row['group_id'] for row in group_rows}

        logger.info(f"✅ Loaded {len(user_ids)} users and {len(group_ids)} groups from database")

    except Exception as e:
        logger.error(f"❌ Failed to load data from database: {e}")

# Asynchronously saves user data to the database
def save_user(user_id: int, username: str = None, first_name: str = None, last_name: str = None):
    """Save user to database asynchronously (fire and forget)"""
    if not db_pool:
        return

    async def save_user():
        try:
            async with db_pool.acquire() as conn:
                await conn.execute("""
                    INSERT INTO users (user_id, username, first_name, last_name, updated_at)
                    VALUES ($1, $2, $3, $4, CURRENT_TIMESTAMP)
                    ON CONFLICT (user_id)
                    DO UPDATE SET
                        username = EXCLUDED.username,
                        first_name = EXCLUDED.first_name,
                        last_name = EXCLUDED.last_name,
                        updated_at = CURRENT_TIMESTAMP
                """, user_id, username, first_name, last_name)

            logger.debug(f"💾 User {user_id} saved to database")

        except Exception as e:
            logger.error(f"❌ Failed to save user {user_id} to database: {e}")

    # Schedule the save operation without waiting
    asyncio.create_task(save_user())

# Asynchronously saves group data to the database
def save_group(group_id: int, title: str = None, username: str = None, chat_type: str = None):
    """Save group to database asynchronously (fire and forget)"""
    if not db_pool:
        return

    async def save_group():
        try:
            async with db_pool.acquire() as conn:
                await conn.execute("""
                    INSERT INTO groups (group_id, title, username, type, updated_at)
                    VALUES ($1, $2, $3, $4, CURRENT_TIMESTAMP)
                    ON CONFLICT (group_id)
                    DO UPDATE SET
                        title = EXCLUDED.title,
                        username = EXCLUDED.username,
                        type = EXCLUDED.type,
                        updated_at = CURRENT_TIMESTAMP
                """, group_id, title, username, chat_type)

            logger.debug(f"💾 Group {group_id} saved to database")

        except Exception as e:
            logger.error(f"❌ Failed to save group {group_id} to database: {e}")

    # Schedule the save operation without waiting
    asyncio.create_task(save_group())

# Retrieves all user IDs from the database
async def get_users():
    """Get all user IDs from database"""
    if not db_pool:
        return list(user_ids)  # Fallback to memory

    try:
        async with db_pool.acquire() as conn:
            rows = await conn.fetch("SELECT user_id FROM users")
            return [row['user_id'] for row in rows]
    except Exception as e:
        logger.error(f"❌ Failed to get users from database: {e}")
        return list(user_ids)  # Fallback to memory

# Retrieves all group IDs from the database
async def get_groups():
    """Get all group IDs from database"""
    if not db_pool:
        return list(group_ids)  # Fallback to memory

    try:
        async with db_pool.acquire() as conn:
            rows = await conn.fetch("SELECT group_id FROM groups")
            return [row['group_id'] for row in rows]
    except Exception as e:
        logger.error(f"❌ Failed to get groups from database: {e}")
        return list(group_ids)  # Fallback to memory

# Asynchronously saves purchase data to the database
def save_purchase(user_id: int, username: str = None, first_name: str = None, last_name: str = None, amount: int = 0, charge_id: str = None):
    """Save purchase to database asynchronously (fire and forget)"""
    if not db_pool:
        return

    async def save_purchase():
        try:
            async with db_pool.acquire() as conn:
                await conn.execute("""
                    INSERT INTO purchases (user_id, username, first_name, last_name, amount, telegram_payment_charge_id)
                    VALUES ($1, $2, $3, $4, $5, $6)
                    ON CONFLICT (telegram_payment_charge_id) DO NOTHING
                """, user_id, username, first_name, last_name, amount, charge_id)

            logger.debug(f"💾 Purchase saved to database: user {user_id}, amount {amount}")

        except Exception as e:
            logger.error(f"❌ Failed to save purchase to database: {e}")

    # Schedule the save operation without waiting
    asyncio.create_task(save_purchase())

# Retrieves all purchase records from the database
async def get_purchases():
    """Get all purchases from database ordered by amount descending"""
    if not db_pool:
        return []

    try:
        async with db_pool.acquire() as conn:
            rows = await conn.fetch("""
                SELECT user_id, username, first_name, last_name, SUM(amount) as total_amount, COUNT(*) as purchase_count
                FROM purchases
                GROUP BY user_id, username, first_name, last_name
                ORDER BY total_amount DESC
            """)
            return rows
    except Exception as e:
        logger.error(f"❌ Failed to get purchases from database: {e}")
        return []

# Closes the database connection pool
async def close_database():
    """Close database connection pool"""
    global db_pool

    if db_pool:
        await db_pool.close()
        logger.info("✅ Database connection pool closed")


# Removes a user from the database
async def remove_user(user_id: int):
    """Remove a user from the database and memory."""
    global user_ids
    if user_id in user_ids:
        user_ids.remove(user_id)

    if not db_pool:
        logger.warning(f"⚠️ DB pool not available. Cannot remove user {user_id}.")
        return

    try:
        async with db_pool.acquire() as conn:
            await conn.execute("DELETE FROM users WHERE user_id = $1", user_id)
        logger.info(f"✅ User {user_id} removed from database.")
    except Exception as e:
        logger.error(f"❌ Failed to remove user {user_id} from database: {e}")


# Removes a group from the database
async def remove_group(group_id: int):
    """Remove a group from the database and memory."""
    global group_ids
    if group_id in group_ids:
        group_ids.remove(group_id)

    if not db_pool:
        logger.warning(f"⚠️ DB pool not available. Cannot remove group {group_id}.")
        return

    try:
        async with db_pool.acquire() as conn:
            await conn.execute("DELETE FROM groups WHERE group_id = $1", group_id)
        logger.info(f"✅ Group {group_id} removed from database.")
    except Exception as e:
        logger.error(f"❌ Failed to remove group {group_id} from database: {e}")


# UTILITY FUNCTIONS
# Extracts user and chat information from a message
def get_user_info(msg: Message) -> Dict[str, any]:
    """Extract user and chat information from message"""
    logger.debug("🔍 Extracting user information from message")
    u = msg.from_user
    c = msg.chat
    info = {
        "user_id": u.id,
        "username": u.username,
        "full_name": u.full_name,
        "first_name": u.first_name,
        "last_name": u.last_name,
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


# Logs a message with detailed user information
def log_action(level: str, message: str, user_info: Dict[str, any]) -> None:
    """Log message with user information"""
    user_detail = (
        f"👤 {user_info.get('full_name', 'N/A')} (@{user_info.get('username', 'N/A')}) "
        f"[ID: {user_info.get('user_id', 'N/A')}] | "
        f"💬 {user_info.get('chat_title', 'N/A')} [{user_info.get('chat_id', 'N/A')}] "
        f"({user_info.get('chat_type', 'N/A')}) {user_info.get('chat_link', 'N/A')}"
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


# Returns a random fallback response
def get_fallback() -> str:
    """Get a random fallback response when API fails"""
    return random.choice(RESPONSES)


# Returns a random error response
def get_error() -> str:
    """Get a random error response when something goes wrong"""
    return random.choice(ERROR)


# Validates the bot's configuration
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
    if not DATABASE_URL:
        logger.error("❌ DATABASE_URL not found in environment variables")
        return False
    if not API_ID:
        logger.error("❌ API_ID not found in environment variables")
        return False
    if not API_HASH:
        logger.error("❌ API_HASH not found in environment variables")
        return False
    return True


# Updates the last response time for a user in Valkey
async def update_response_time(user_id: int) -> None:
    """Update the last response time for user in Valkey"""
    if valkey_client:
        try:
            key = f"last_response:{user_id}"
            await valkey_client.setex(key, SESSION_TTL, int(time.time()))
            logger.debug(f"⏰ Updated response time in Valkey for user {user_id}")
        except Exception as e:
            logger.error(f"❌ Failed to update response time in Valkey for user {user_id}: {e}")

    # Also update memory as fallback
    user_last_response_time[user_id] = time.time()


# Determines if the bot should respond to a message in a group chat
def should_reply(update: Update, bot_id: int) -> bool:
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


# Tracks user and chat IDs for broadcasting purposes
def track_user(update: Update, user_info: Dict[str, any]) -> None:
    """Track user and chat IDs for broadcasting (fast memory + async database)"""
    user_id = user_info["user_id"]
    chat_id = user_info["chat_id"]
    chat_type = user_info["chat_type"]

    if chat_type == "private":
        is_new_user = user_id not in user_ids
        # Add to memory immediately (fast)
        user_ids.add(user_id)

        # Save to database asynchronously (non-blocking) to add or update user info
        save_user(
            user_id,
            user_info.get("username"),
            user_info.get("first_name"),
            user_info.get("last_name")
        )
        if is_new_user:
            log_action("INFO", f"👤 New user tracked for broadcasting", user_info)

    elif chat_type in ['group', 'supergroup']:
        is_new_group = chat_id not in group_ids
        # Add to memory immediately (fast)
        group_ids.add(chat_id)

        # Save to database asynchronously (non-blocking) to add or update group info
        save_group(
            chat_id,
            user_info.get("chat_title"),
            user_info.get("username"),
            chat_type
        )
        if is_new_group:
            log_action("INFO", f"📢 New group tracked for broadcasting", user_info)


# Creates a user mention in HTML format
def get_mention(user) -> str:
    """Create user mention for HTML parsing using first name"""
    first_name = user.first_name or "Friend"
    return f'<a href="tg://user?id={user.id}">{first_name}</a>'


# REACTION LOGIC
async def handle_reaction(update: Update, user_info: Dict[str, any]):
    """
    Analyzes the message text and sends a contextual, animated emoji reaction
    with a certain probability.
    """
    try:
        # Only react a certain percentage of the time to feel more human
        if random.random() > 0.3:  # 30% chance to react
            return

        message_text = (update.message.text or "").lower()
        if not message_text:
            return

        log_action("DEBUG", f"🤔 Analyzing message for reaction: '{message_text[:50]}...'", user_info)

        found_context = None
        # Find a matching context from keywords
        for context, keywords in REACTION_KEYWORDS.items():
            if any(keyword in message_text for keyword in keywords):
                found_context = context
                log_action("INFO", f"✅ Context found for reaction: '{found_context}'", user_info)
                break

        if found_context:
            # Select a random emoji from the matched context
            emoji_to_react = random.choice(CONTEXTUAL_REACTIONS[found_context])
            log_action("INFO", f"🥰 Selected emoji for reaction: {emoji_to_react}", user_info)

            # Send the animated reaction
            await send_big_reaction(
                chat_id=update.effective_chat.id,
                message_id=update.message.message_id,
                emoji=emoji_to_react
            )
            log_action("INFO", f"🚀 Sent animated reaction '{emoji_to_react}' successfully", user_info)

    except Exception as e:
        log_action("ERROR", f"❌ Failed to handle contextual reaction: {e}", user_info)


# CONVERSATION MEMORY FUNCTIONS
# Adds a message to the user's conversation history
async def add_history(user_id: int, message: str, is_user: bool = True):
    """Add message to user's conversation history (Valkey + memory fallback)"""
    global conversation_history

    role = "user" if is_user else "assistant"
    new_message = {"role": role, "content": message}

    # Try Valkey first
    if valkey_client:
        try:
            key = f"conversation:{user_id}"
            existing = await valkey_client.get(key)

            if existing:
                history = orjson.loads(existing)
            else:
                history = []

            history.append(new_message)

            # Keep only last CHAT_LENGTH messages
            if len(history) > CHAT_LENGTH:
                history = history[-CHAT_LENGTH:]

            await valkey_client.setex(key, SESSION_TTL, orjson.dumps(history))
            logger.debug(f"💬 Conversation updated in Valkey for user {user_id}")
            return

        except Exception as e:
            logger.error(f"❌ Failed to update conversation in Valkey for user {user_id}: {e}")

    # Fallback to memory
    if user_id not in conversation_history:
        conversation_history[user_id] = []

    conversation_history[user_id].append(new_message)

    # Keep only last CHAT_LENGTH messages
    if len(conversation_history[user_id]) > CHAT_LENGTH:
        conversation_history[user_id] = conversation_history[user_id][-CHAT_LENGTH:]

async def get_history(user_id: int) -> list:
    """Get conversation history as a list of dicts."""
    history = []

    # Try Valkey first
    if valkey_client:
        try:
            key = f"conversation:{user_id}"
            existing = await valkey_client.get(key)
            if existing:
                history = orjson.loads(existing)
        except Exception as e:
            logger.error(f"❌ Failed to get conversation from Valkey for user {user_id}: {e}")

    # Fallback to memory
    if not history and user_id in conversation_history:
        history = conversation_history[user_id]

    return history


# Retrieves the conversation context for a user
async def get_context(user_id: int) -> str:
    """Get formatted conversation context for the user (Valkey + memory fallback)"""
    history = []

    # Try Valkey first
    if valkey_client:
        try:
            key = f"conversation:{user_id}"
            existing = await valkey_client.get(key)
            if existing:
                history = orjson.loads(existing)
        except Exception as e:
            logger.error(f"❌ Failed to get conversation from Valkey for user {user_id}: {e}")

    # Fallback to memory
    if not history and user_id in conversation_history:
        history = conversation_history[user_id]

    if not history:
        return ""

    context_lines = []
    for message in history:
        if message["role"] == "user":
            context_lines.append(f"User: {message['content']}")
        else:
            context_lines.append(f"Sakura: {message['content']}")

    return "\n".join(context_lines)


# Periodically cleans up old conversation histories
async def cleanup_conversations():
    """Clean up old conversation histories and response times periodically"""
    global conversation_history, user_last_response_time

    logger.info("🧹 Conversation cleanup task started")

    while True:
        try:
            current_time = time.time()
            conversations_cleaned = 0

            # Find expired conversations
            expired_users = []
            for user_id in list(conversation_history.keys()):
                last_response_time = user_last_response_time.get(user_id, 0)
                if current_time - last_response_time > OLD_CHAT:
                    expired_users.append(user_id)

            # Remove expired conversations
            for user_id in expired_users:
                if user_id in conversation_history:
                    del conversation_history[user_id]
                    conversations_cleaned += 1
                if user_id in user_last_response_time:
                    del user_last_response_time[user_id]

            # Log cleanup results
            if conversations_cleaned > 0:
                logger.info(f"🧹 Cleaned {conversations_cleaned} old conversations")

            logger.debug(f"📊 Active conversations: {len(conversation_history)}")

        except asyncio.CancelledError:
            # Handle graceful shutdown
            logger.info("🧹 Cleanup task cancelled - shutting down gracefully")
            break
        except Exception as e:
            logger.error(f"❌ Error in conversation cleanup: {e}")

        # Wait for next cleanup cycle (with cancellation support)
        try:
            await asyncio.sleep(CHAT_CLEANUP)
        except asyncio.CancelledError:
            logger.info("🧹 Cleanup task sleep cancelled - shutting down")
            break


# AI RESPONSE FUNCTIONS
async def get_response(user_message: str, user_name: str = "", user_info: Dict[str, any] = None, user_id: int = None, image_bytes: Optional[bytes] = None) -> str:
    """Gets a response from the AI, trying OpenRouter first and falling back to Gemini."""
    response = None
    source_api = None

    # Try OpenRouter first
    if openrouter_client:
        log_action("INFO", "🤖 Trying OpenRouter API...", user_info)
        try:
            response = await openrouter_response(user_message, user_name, user_info, user_id, image_bytes)
            if response:
                source_api = "OpenRouter"
                log_action("INFO", f"✅ {source_api} response generated: '{response[:50]}...'", user_info)
        except Exception as e:
            log_action("ERROR", f"❌ OpenRouter API error: {e}. Falling back to Gemini.", user_info)

    # Fallback to Gemini if OpenRouter fails or is disabled
    if not response:
        log_action("INFO", "🤖 Falling back to Gemini API", user_info)
        source_api = "Gemini"
        if image_bytes:
            response = await analyze_image_gemini(image_bytes, user_message, user_name, user_info, user_id)
        else:
            response = await gemini_response(user_message, user_name, user_info, user_id)

    # Add to conversation history
    if response and user_id:
        # Determine the user's message to be stored in history
        history_user_message = user_message
        if image_bytes:
            history_user_message = f"[Image: {user_message}]" if user_message else "[Image sent]"

        # Add user message and AI response to history
        await add_history(user_id, history_user_message, is_user=True)
        await add_history(user_id, response, is_user=False)

    return response if response else get_error()


async def openrouter_response(user_message: str, user_name: str = "", user_info: Dict[str, any] = None, user_id: int = None, image_bytes: Optional[bytes] = None) -> Optional[str]:
    """Get response from OpenRouter API."""
    if not openrouter_client:
        return None

    history = await get_history(user_id)

    messages = []

    # Determine which prompt to use
    active_prompt = SAKURA_PROMPT
    if user_id == OWNER_ID:
        active_prompt = LOVELY_SAKURA_PROMPT

    # Add system prompt
    messages.append({"role": "system", "content": active_prompt})

    # Add history to messages
    messages.extend(history)

    # Add current message
    current_message_content = []
    current_message_content.append({"type": "text", "text": user_message})

    if image_bytes:
        image_data = base64.b64encode(image_bytes).decode('utf-8')
        current_message_content.append({
            "type": "image_url",
            "image_url": {
                "url": f"data:image/jpeg;base64,{image_data}"
            }
        })

    messages.append({"role": "user", "content": current_message_content})

    completion = await asyncio.to_thread(
        openrouter_client.chat.completions.create,
        extra_headers={
            "HTTP-Referer": "https://t.me/SakuraHarunoBot",
            "X-Title": "Sakura Bot",
        },
        model=MODEL,
        messages=messages
    )

    ai_response = completion.choices[0].message.content
    if ai_response:
        return ai_response.strip()
    else:
        return None

# Gets a response from the Gemini API
async def gemini_response(user_message: str, user_name: str = "", user_info: Dict[str, any] = None, user_id: int = None) -> str:
    """Get response from Gemini API with conversation context and caching"""
    if user_info:
        log_action("DEBUG", f"🤖 Getting Gemini response for message: '{user_message[:50]}...'", user_info)

    if not gemini_client:
        if user_info:
            log_action("WARNING", "❌ Gemini client not available, using fallback response", user_info)
        return get_fallback()

    try:
        # Get conversation context if user_id provided
        context = ""
        if user_id:
            context = await get_context(user_id)
            if context:
                context = f"\n\nPrevious conversation:\n{context}\n"

        # Determine which prompt to use
        active_prompt = SAKURA_PROMPT
        if user_id == OWNER_ID:
            active_prompt = LOVELY_SAKURA_PROMPT

        # Build prompt with context
        prompt = f"{active_prompt}\n\nUser name: {user_name}{context}\nCurrent user message: {user_message}\n\nSakura's response:"

        # Check cache for similar short messages (without personal context)
        cache_key = None
        if len(user_message) <= 50 and not context and user_id:  # Only cache short, context-free messages
            cache_key = f"gemini_response:{user_id}:{hashlib.md5(user_message.lower().encode()).hexdigest()}"
            cached_response = await get_cache(cache_key)
            if cached_response:
                if user_info:
                    log_action("INFO", f"📦 Using cached response for message", user_info)
                return cached_response

        response = await gemini_client.aio.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt
        )

        ai_response = response.text.strip() if response.text else get_fallback()

        # Cache the response if it was a short, context-free message
        if cache_key:
            await set_cache(cache_key, ai_response, CACHE_TTL)

        if user_info:
            log_action("INFO", f"✅ Gemini response generated: '{ai_response[:50]}...'", user_info)

        return ai_response

    except Exception as e:
        if user_info:
            log_action("ERROR", f"❌ Gemini API error: {e}", user_info)
        else:
            logger.error(f"Gemini API error: {e}")
        return get_error()


# Analyzes an image using the Gemini API
async def analyze_image_gemini(image_bytes: bytes, caption: str, user_name: str = "", user_info: Dict[str, any] = None, user_id: int = None) -> str:
    """Analyze image using Gemini 2.5 Flash with conversation context"""
    if user_info:
        log_action("DEBUG", f"🖼️ Analyzing image with Gemini: {len(image_bytes)} bytes", user_info)

    if not gemini_client:
        if user_info:
            log_action("WARNING", "❌ Gemini client not available for image analysis", user_info)
        return "Samjh nahi paa rahi image kya hai 😔"

    try:
        # Get conversation context if user_id provided
        context = ""
        if user_id:
            context = await get_context(user_id)
            if context:
                context = f"\n\nPrevious conversation:\n{context}\n"

        # Determine which prompt to use
        active_prompt = SAKURA_PROMPT
        if user_id == OWNER_ID:
            active_prompt = LOVELY_SAKURA_PROMPT

        # Build image analysis prompt
        image_prompt = f"""{active_prompt}

User name: {user_name}{context}

User has sent an image. Caption: "{caption if caption else 'No caption'}"

Analyze this image and respond in Sakura's style about what you see. Be descriptive but keep it to one or two lines as per your character rules. Comment on what's in the image, colors, mood, or anything interesting you notice.

Sakura's response:"""

        # Create the request with image using proper format

        # Convert bytes to base64 string
        image_data = base64.b64encode(image_bytes).decode('utf-8')

        response = await gemini_client.aio.models.generate_content(
            model="gemini-2.5-flash",
            contents=[
                image_prompt,
                {
                    "inline_data": {
                        "mime_type": "image/jpeg",
                        "data": image_data
                    }
                }
            ]
        )

        ai_response = response.text.strip() if response.text else "Kya cute image hai! 😍"

        if user_info:
            log_action("INFO", f"✅ Image analysis completed: '{ai_response[:50]}...'", user_info)

        return ai_response

    except Exception as e:
        if user_info:
            log_action("ERROR", f"❌ Image analysis error: {e}", user_info)
        else:
            logger.error(f"Image analysis error: {e}")
        return "Image analyze nahi kar paa rahi 😕"


# Analyzes a poll that was referenced in a message
async def analyze_poll_reply(update: Update, context: ContextTypes.DEFAULT_TYPE, user_message: str, user_info: Dict[str, any]) -> bool:
    """Check if user is asking to analyze a previously sent poll and handle it"""
    # Check if message contains requests for poll analysis
    message_lower = user_message.lower()
    contains_poll_request = any(trigger in message_lower for trigger in POLL_ANALYSIS_TRIGGERS)

    if not contains_poll_request:
        return False

    log_action("DEBUG", "🔍 Detected potential poll analysis request", user_info)

    # Check if replying to a message with poll
    if update.message.reply_to_message and update.message.reply_to_message.poll:
        log_action("INFO", "🔍 User asking about replied poll", user_info)

        # React to the message to show the bot is "thinking"
        try:
            emoji_to_react = random.choice(CONTEXTUAL_REACTIONS["confused"])
            # React to the user's message
            await send_big_reaction(
                chat_id=update.effective_chat.id,
                message_id=update.message.message_id,
                emoji=emoji_to_react
            )
            # React to the original poll message as well
            await send_big_reaction(
                chat_id=update.effective_chat.id,
                message_id=update.message.reply_to_message.message_id,
                emoji=emoji_to_react
            )
            log_action("INFO", f"🤔 Sent analysis reaction '{emoji_to_react}' for replied poll", user_info)
        except Exception as e:
            log_action("WARNING", f"⚠️ Could not send analysis reaction for replied poll: {e}", user_info)

        # Send typing action to show bot is processing
        await send_typing(context, update.effective_chat.id, user_info)

        try:
            poll = update.message.reply_to_message.poll
            poll_question = poll.question
            poll_options = [option.text for option in poll.options]

            user_name = update.effective_user.first_name or ""

            # Analyze the referenced poll
            response = await analyze_poll(
                poll_question, poll_options, user_name, user_info, user_info["user_id"]
            )

            # Send response (no effects for Gemini responses)
            await update.message.reply_text(response)

            log_action("INFO", "✅ Referenced poll analyzed successfully", user_info)
            return True

        except Exception as e:
            log_action("ERROR", f"❌ Error analyzing referenced poll: {e}", user_info)

            error_response = "Poll analyze nahi kar paa rahi 😔"
            await update.message.reply_text(error_response)

            return True

    return False


# Analyzes a poll, trying OpenRouter first and falling back to Gemini
async def analyze_poll(poll_question: str, poll_options: list, user_name: str = "", user_info: Dict[str, any] = None, user_id: int = None) -> str:
    """Analyze a poll, trying OpenRouter first and falling back to Gemini."""
    response = None
    source_api = None

    # Try OpenRouter first
    if openrouter_client:
        log_action("INFO", "🤖 Trying OpenRouter API for poll analysis...", user_info)
        try:
            response = await openrouter_poll(poll_question, poll_options, user_name, user_info, user_id)
            if response:
                source_api = "OpenRouter"
        except Exception as e:
            log_action("ERROR", f"❌ OpenRouter poll analysis error: {e}. Falling back to Gemini.", user_info)

    # Fallback to Gemini if OpenRouter fails or is disabled
    if not response:
        log_action("INFO", "🤖 Falling back to Gemini API for poll analysis", user_info)
        source_api = "Gemini"
        response = await gemini_poll(poll_question, poll_options, user_name, user_info, user_id)

    # Add messages to conversation history
    if response and user_id:
        poll_description = f"[Poll: {poll_question}] Options: {', '.join(poll_options)}"
        await add_history(user_id, poll_description, is_user=True)
        await add_history(user_id, response, is_user=False)
        log_action("INFO", f"✅ Poll analysis via {source_api} completed and saved to history", user_info)

    return response if response else "Poll analyze nahi kar paa rahi 😕"


# Analyzes an image that was referenced in a message
async def analyze_image_reply(update: Update, context: ContextTypes.DEFAULT_TYPE, user_message: str, user_info: Dict[str, any]) -> bool:
    """Check if user is asking to analyze a previously sent image and handle it"""
    # Check if message contains requests for image analysis
    message_lower = user_message.lower()
    contains_image_request = any(trigger in message_lower for trigger in IMAGE_ANALYSIS_TRIGGERS)

    if not contains_image_request:
        return False

    log_action("DEBUG", "🔍 Detected potential image analysis request", user_info)

    # Priority 1: Check if replying to a message with photo
    if update.message.reply_to_message and update.message.reply_to_message.photo:
        log_action("INFO", "🔍 User asking about replied image", user_info)

        # React to the message to show the bot is "thinking"
        try:
            emoji_to_react = random.choice(CONTEXTUAL_REACTIONS["love"])
            # React to the user's message
            await send_big_reaction(
                chat_id=update.effective_chat.id,
                message_id=update.message.message_id,
                emoji=emoji_to_react
            )
            # React to the original image message as well
            await send_big_reaction(
                chat_id=update.effective_chat.id,
                message_id=update.message.reply_to_message.message_id,
                emoji=emoji_to_react
            )
            log_action("INFO", f"🤔 Sent analysis reaction '{emoji_to_react}' for replied image", user_info)
        except Exception as e:
            log_action("WARNING", f"⚠️ Could not send analysis reaction for replied image: {e}", user_info)

        # Send typing action to show bot is processing
        await send_typing(context, update.effective_chat.id, user_info)

        try:
            photo = update.message.reply_to_message.photo[-1]
            file = await context.bot.get_file(photo.file_id)
            image_bytes = await file.download_as_bytearray()

            user_name = update.effective_user.first_name or ""
            caption = update.message.reply_to_message.caption or ""

            # Analyze the referenced image
            response = await get_response(
                caption, user_name, user_info, user_info["user_id"], image_bytes=image_bytes
            )

            # Send response (no effects for Gemini responses)
            await update.message.reply_text(response)

            log_action("INFO", "✅ Referenced image analyzed successfully", user_info)
            return True

        except Exception as e:
            log_action("ERROR", f"❌ Error analyzing referenced image: {e}", user_info)

            error_response = "Image analyze nahi kar paa rahi 😔"
            await update.message.reply_text(error_response)

            return True

    # Priority 2: Look for recent images in conversation history (for private chats mainly)
    if user_info["user_id"] in conversation_history:
        history = conversation_history[user_info["user_id"]]

        # Find the most recent image reference
        for message in reversed(history):
            if message["role"] == "user" and "[Image:" in message["content"]:
                log_action("INFO", "🔍 User asking about previously sent image from history", user_info)

                # If no recent replied image found, inform user
                no_image_response = "Koi recent image nahi mil rahi analyze karne ke liye 😔"
                await update.message.reply_text(no_image_response)

                return True

    return False


# Analyzes a poll using the OpenRouter API
async def openrouter_poll(poll_question: str, poll_options: list, user_name: str = "", user_info: Dict[str, any] = None, user_id: int = None) -> Optional[str]:
    """Analyze poll using OpenRouter API to suggest the correct answer."""
    if not openrouter_client:
        return None

    if user_info:
        log_action("DEBUG", f"📊 Analyzing poll with OpenRouter: '{poll_question[:50]}...'", user_info)

    try:
        history = await get_history(user_id)
        messages = []

        # Determine which prompt to use
        active_prompt = SAKURA_PROMPT
        if user_id == OWNER_ID:
            active_prompt = LOVELY_SAKURA_PROMPT

        messages.append({"role": "system", "content": active_prompt})
        messages.extend(history)

        # Format poll options
        options_text = "\n".join([f"{i+1}. {option}" for i, option in enumerate(poll_options)])

        # Build poll analysis prompt
        poll_prompt = f"""User has sent a poll or asked about a poll question. Analyze this question and suggest which option might be the correct answer.

Poll Question: "{poll_question}"

Options:
{options_text}

Analyze this poll question and respond in Sakura's style about which option you think is correct and why. Keep it to one or two lines as per your character rules. Be helpful and give a quick reason.

Sakura's response:"""

        messages.append({"role": "user", "content": poll_prompt})

        completion = await asyncio.to_thread(
            openrouter_client.chat.completions.create,
            extra_headers={
                "HTTP-Referer": "https://t.me/SakuraHarunoBot",
                "X-Title": "Sakura Bot",
            },
            model=MODEL,
            messages=messages
        )

        ai_response = completion.choices[0].message.content
        if ai_response:
            if user_info:
                log_action("INFO", f"✅ OpenRouter poll analysis completed: '{ai_response[:50]}...'", user_info)
            return ai_response.strip()
        else:
            return None

    except Exception as e:
        if user_info:
            log_action("ERROR", f"❌ OpenRouter poll analysis error: {e}", user_info)
        else:
            logger.error(f"OpenRouter poll analysis error: {e}")
        return None


# Analyzes a poll using the Gemini API
async def gemini_poll(poll_question: str, poll_options: list, user_name: str = "", user_info: Dict[str, any] = None, user_id: int = None) -> str:
    """Analyze poll using Gemini 2.5 Flash to suggest the correct answer"""
    if user_info:
        log_action("DEBUG", f"📊 Analyzing poll with Gemini: '{poll_question[:50]}...'", user_info)

    if not gemini_client:
        if user_info:
            log_action("WARNING", "❌ Gemini client not available for poll analysis", user_info)
        return "Poll samjh nahi paa rahi 😔"

    try:
        # Get conversation context if user_id provided
        context = ""
        if user_id:
            context = await get_context(user_id)
            if context:
                context = f"\n\nPrevious conversation:\n{context}\n"

        # Format poll options
        options_text = "\n".join([f"{i+1}. {option}" for i, option in enumerate(poll_options)])

        # Determine which prompt to use
        active_prompt = SAKURA_PROMPT
        if user_id == OWNER_ID:
            active_prompt = LOVELY_SAKURA_PROMPT

        # Build poll analysis prompt
        poll_prompt = f"""{active_prompt}

User name: {user_name}{context}

User has sent a poll or asked about a poll question. Analyze this question and suggest which option might be the correct answer.

Poll Question: "{poll_question}"

Options:
{options_text}

Analyze this poll question and respond in Sakura's style about which option you think is correct and why. Keep it to one or two lines as per your character rules. Be helpful and give a quick reason.

Sakura's response:"""

        response = await gemini_client.aio.models.generate_content(
            model="gemini-2.5-flash",
            contents=poll_prompt
        )

        ai_response = response.text.strip() if response.text else "Poll ka answer samjh nahi aaya 😅"

        if user_info:
            log_action("INFO", f"✅ Gemini poll analysis completed: '{ai_response[:50]}...'", user_info)

        return ai_response

    except Exception as e:
        if user_info:
            log_action("ERROR", f"❌ Poll analysis error: {e}", user_info)
        else:
            logger.error(f"Poll analysis error: {e}")
        return "Poll analyze nahi kar paa rahi 😕"


# CHAT ACTION FUNCTIONS
# Sends the "typing" action in a chat
async def send_typing(context: ContextTypes.DEFAULT_TYPE, chat_id: int, user_info: Dict[str, any]) -> None:
    """Send typing action to show bot is processing"""
    log_action("DEBUG", "⌨️ Sending typing action", user_info)
    await context.bot.send_chat_action(chat_id=chat_id, action=ChatAction.TYPING)


# Sends the "uploading photo" action in a chat
async def send_photo_action(context: ContextTypes.DEFAULT_TYPE, chat_id: int, user_info: Dict[str, any]) -> None:
    """Send upload photo action"""
    log_action("DEBUG", "📷 Sending photo upload action", user_info)
    await context.bot.send_chat_action(chat_id=chat_id, action=ChatAction.UPLOAD_PHOTO)


# Sends the "choosing sticker" action in a chat
async def send_sticker_action(context: ContextTypes.DEFAULT_TYPE, chat_id: int, user_info: Dict[str, any]) -> None:
    """Send choosing sticker action"""
    log_action("DEBUG", "🎭 Sending sticker choosing action", user_info)
    await context.bot.send_chat_action(chat_id=chat_id, action=ChatAction.CHOOSE_STICKER)


# KEYBOARD CREATION FUNCTIONS
# Creates the initial keyboard for the /start command
def create_start_menu() -> InlineKeyboardMarkup:
    """Create initial start keyboard with Info and Hi buttons"""
    keyboard = [
        [
            InlineKeyboardButton(START_MESSAGES["button_texts"]["info"], callback_data="start_info"),
            InlineKeyboardButton(START_MESSAGES["button_texts"]["hi"], callback_data="start_hi")
        ]
    ]
    return InlineKeyboardMarkup(keyboard)


# Creates the keyboard for the "info" section of the /start command
def create_info_menu(bot_username: str) -> InlineKeyboardMarkup:
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


# Gets the initial caption for the /start command
def get_start_text(user_mention: str) -> str:
    """Get initial caption text for start command with user mention"""
    return START_MESSAGES["initial_caption"].format(user_mention=user_mention)


# Gets the caption for the "info" section of the /start command
def get_info_text(user_mention: str) -> str:
    """Get info caption text for start command with user mention"""
    return START_MESSAGES["info_caption"].format(user_mention=user_mention)


# Creates the keyboard for the /help command
def create_help_menu(expanded: bool = False) -> InlineKeyboardMarkup:
    """Create help command keyboard"""
    if expanded:
        button_text = HELP_MESSAGES["button_texts"]["minimize"]
        callback_data = "help_minimize"
    else:
        button_text = HELP_MESSAGES["button_texts"]["expand"]
        callback_data = "help_expand"

    keyboard = [[InlineKeyboardButton(button_text, callback_data=callback_data)]]
    return InlineKeyboardMarkup(keyboard)


# Gets the text for the /help command
def get_help_text(user_mention: str, expanded: bool = False) -> str:
    """Get help text based on expansion state with user mention"""
    if expanded:
        return HELP_MESSAGES["expanded"].format(user_mention=user_mention)
    else:
        return HELP_MESSAGES["minimal"].format(user_mention=user_mention)


# Creates the keyboard for the /broadcast command
def create_broadcast_menu() -> InlineKeyboardMarkup:
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


# Gets the text for the /broadcast command
def get_broadcast_text() -> str:
    """Get broadcast command text"""
    return BROADCAST_MESSAGES["select_target"].format(
        users_count=len(user_ids),
        groups_count=len(group_ids)
    )


# COMMAND HANDLERS
# Handles the /start command
async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /start command with two-step inline buttons and effects in private chat"""
    try:
        user_info = get_user_info(update.message)
        log_action("INFO", "🌸 /start command received", user_info)

        track_user(update, user_info)

        # Step 1: React to the start message with random emoji and animation
        if EMOJI_REACT:
            try:
                random_emoji = random.choice(EMOJI_REACT)

                # Use Telethon for animated emoji reactions
                if effects_client and update.effective_chat.type == "private":
                    reaction_sent = await send_big_reaction(
                        update.effective_chat.id,
                        update.message.message_id,
                        random_emoji
                    )
                    if reaction_sent:
                        log_action("DEBUG", f"🎭 Added animated emoji reaction: {random_emoji}", user_info)
                    else:
                        # Fallback to PTB reaction without animation
                        await add_reaction(context, update, random_emoji, user_info)
                else:
                    # Group chat or no Telethon - use PTB reaction
                    await add_reaction(context, update, random_emoji, user_info)

            except Exception as e:
                log_action("WARNING", f"⚠️ Failed to add emoji reaction: {e}", user_info)

        # Step 2: Send random sticker (only in private chat)
        if update.effective_chat.type == "private" and START_STICKERS:
            await send_sticker_action(context, update.effective_chat.id, user_info)

            random_sticker = random.choice(START_STICKERS)
            log_action("DEBUG", f"🎭 Sending start sticker: {random_sticker}", user_info)

            await context.bot.send_sticker(
                chat_id=update.effective_chat.id,
                sticker=random_sticker
            )
            log_action("INFO", "✅ Start sticker sent successfully", user_info)

        # Step 3: Send the initial welcome message with photo and two-step buttons
        await send_photo_action(context, update.effective_chat.id, user_info)

        random_image = random.choice(SAKURA_IMAGES)
        keyboard = create_start_menu()
        user_mention = get_mention(update.effective_user)
        caption = get_start_text(user_mention)

        log_action("DEBUG", f"📷 Sending initial start photo: {random_image[:50]}...", user_info)

        # Send with effects if in private chat
        if update.effective_chat.type == "private":
            # Use Telethon effects for the main start message
            effect_sent = await send_effect_photo(
                update.effective_chat.id,
                random_image,
                caption,
                keyboard
            )
            if effect_sent:
                log_action("INFO", "✨ Start command with effects sent successfully", user_info)
            else:
                # Fallback to normal PTB message if effects fail
                await context.bot.send_photo(
                    chat_id=update.effective_chat.id,
                    photo=random_image,
                    caption=caption,
                    parse_mode=ParseMode.HTML,
                    reply_markup=keyboard
                )
                log_action("WARNING", "⚠️ Start command sent without effects (fallback)", user_info)
        else:
            # Group chat - no effects, just normal message
            await context.bot.send_photo(
                chat_id=update.effective_chat.id,
                photo=random_image,
                caption=caption,
                parse_mode=ParseMode.HTML,
                reply_markup=keyboard
            )

        log_action("INFO", "✅ Start command completed successfully", user_info)

    except Exception as e:
        user_info = get_user_info(update.message)
        log_action("ERROR", f"❌ Error in start command: {e}", user_info)
        await update.message.reply_text(get_error())


# Handles the /help command
async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /help command with random image and effects in private chat"""
    try:
        user_info = get_user_info(update.message)
        log_action("INFO", "ℹ️ /help command received", user_info)

        track_user(update, user_info)

        # Step 1: React to the help message with random emoji and animation
        if EMOJI_REACT:
            try:
                random_emoji = random.choice(EMOJI_REACT)

                # Use Telethon for animated emoji reactions
                if effects_client and update.effective_chat.type == "private":
                    reaction_sent = await send_big_reaction(
                        update.effective_chat.id,
                        update.message.message_id,
                        random_emoji
                    )
                    if reaction_sent:
                        log_action("DEBUG", f"🎭 Added animated emoji reaction: {random_emoji}", user_info)
                    else:
                        # Fallback to PTB reaction without animation
                        await add_reaction(context, update, random_emoji, user_info)
                else:
                    # Group chat or no Telethon - use PTB reaction
                    await add_reaction(context, update, random_emoji, user_info)

            except Exception as e:
                log_action("WARNING", f"⚠️ Failed to add emoji reaction: {e}", user_info)

        # Step 2: Send photo action indicator
        await send_photo_action(context, update.effective_chat.id, user_info)

        # Step 3: Prepare help content
        keyboard = create_help_menu(expanded=False)
        user_mention = get_mention(update.effective_user)
        help_text = get_help_text(user_mention, expanded=False)

        # Step 4: Send help message with random image
        random_image = random.choice(SAKURA_IMAGES)
        log_action("DEBUG", f"📷 Sending help photo: {random_image[:50]}...", user_info)

        # Send with effects if in private chat
        if update.effective_chat.type == "private":
            # Use Telethon effects for the main help message
            effect_sent = await send_effect_photo(
                update.effective_chat.id,
                random_image,
                help_text,
                keyboard
            )
            if effect_sent:
                log_action("INFO", "✨ Help command with effects sent successfully", user_info)
            else:
                # Fallback to normal PTB message if effects fail
                await context.bot.send_photo(
                    chat_id=update.effective_chat.id,
                    photo=random_image,
                    caption=help_text,
                    parse_mode=ParseMode.HTML,
                    reply_markup=keyboard
                )
                log_action("WARNING", "⚠️ Help command sent without effects (fallback)", user_info)
        else:
            # Group chat - no effects, just normal message
            await context.bot.send_photo(
                chat_id=update.effective_chat.id,
                photo=random_image,
                caption=help_text,
                parse_mode=ParseMode.HTML,
                reply_markup=keyboard
            )

        log_action("INFO", "✅ Help command completed successfully", user_info)

    except Exception as e:
        user_info = get_user_info(update.message)
        log_action("ERROR", f"❌ Error in help command: {e}", user_info)
        await update.message.reply_text(get_error())


# Handles the /broadcast command (owner only)
async def broadcast_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle broadcast command (owner only)"""
    user_info = get_user_info(update.message)

    if update.effective_user.id != OWNER_ID:
        log_action("WARNING", "⚠️ Non-owner attempted broadcast command", user_info)
        return

    log_action("INFO", "📢 Broadcast command received from owner", user_info)

    # Refresh counts from database
    db_users = await get_users()
    db_groups = await get_groups()

    # Sync memory with database
    user_ids.update(db_users)
    group_ids.update(db_groups)

    keyboard = create_broadcast_menu()
    broadcast_text = get_broadcast_text()

    await update.message.reply_text(
        broadcast_text,
        reply_markup=keyboard,
        parse_mode=ParseMode.HTML
    )

    log_action("INFO", "✅ Broadcast selection menu sent", user_info)


# Handles the /ping command
async def ping_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle ping command for everyone"""
    user_info = get_user_info(update.message)
    log_action("INFO", "🏓 Ping command received", user_info)

    start_time = time.time()

    # Send initial message
    msg = await update.message.reply_text("🛰️ Pinging...")

    # Calculate response time
    response_time = round((time.time() - start_time) * 1000, 2)  # milliseconds

    # Edit message with response time and group link (no preview)
    await msg.edit_text(
        f"🏓 <a href='{PING_LINK}'>Pong!</a> {response_time}ms",
        parse_mode=ParseMode.HTML,
        disable_web_page_preview=True
    )

    log_action("INFO", "✅ Ping completed", user_info)



# CALLBACK HANDLERS
# Handles callbacks from the /start command keyboard
async def start_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle start command inline button callbacks"""
    query = update.callback_query
    if query.message.chat.type in ['group', 'supergroup']:
        try:
            chat_member = await context.bot.get_chat_member(query.message.chat.id, context.bot.id)
            if chat_member.status in [ChatMember.LEFT, ChatMember.BANNED]:
                await query.answer("Add me first, my soul might be here but my body not! 🌸", show_alert=True)
                return
        except (BadRequest, Forbidden):
            await query.answer("Add me first, my soul might be here but my body not! 🌸", show_alert=True)
            return

    try:
        query = update.callback_query
        user_info = get_user_info(query.message)
        log_action("INFO", f"🌸 Start callback received: {query.data}", user_info)

        user_mention = get_mention(update.effective_user)

        if query.data == "start_info":
            # Answer callback with proper message
            await query.answer(START_MESSAGES["callback_answers"]["info"], show_alert=False)

            # Show info with original start buttons
            keyboard = create_info_menu(context.bot.username)
            caption = get_info_text(user_mention)

            await query.edit_message_caption(
                caption=caption,
                parse_mode=ParseMode.HTML,
                reply_markup=keyboard
            )
            log_action("INFO", "✅ Start info buttons shown", user_info)

        elif query.data == "start_hi":
            # Answer callback with proper message
            await query.answer(START_MESSAGES["callback_answers"]["hi"], show_alert=False)

            # Send typing indicator before processing
            await send_typing(context, update.effective_chat.id, user_info)
            log_action("INFO", "⌨️ Typing indicator sent for hello", user_info)

            # Send a hi message from Sakura
            user_name = update.effective_user.first_name or ""
            hi_response = await get_response("Hi sakura", user_name, user_info, update.effective_user.id)

            # Send with effects if in private chat
            if update.effective_chat.type == "private":
                # Try sending with effects first
                effect_sent = await send_effect(update.effective_chat.id, hi_response)
                if effect_sent:
                    log_action("INFO", "✨ Start Hi response with effects sent successfully", user_info)
                else:
                    # Fallback to normal PTB message if effects fail
                    await context.bot.send_message(
                        chat_id=update.effective_chat.id,
                        text=hi_response
                    )
                    log_action("WARNING", "⚠️ Start Hi response sent without effects (fallback)", user_info)
            else:
                # Group chat - no effects, just normal message
                await context.bot.send_message(
                    chat_id=update.effective_chat.id,
                    text=hi_response
                )

            log_action("INFO", "✅ Hi message sent from Sakura", user_info)

    except Exception as e:
        user_info = get_user_info(query.message) if query.message else {}
        log_action("ERROR", f"❌ Error in start callback: {e}", user_info)
        try:
            await query.answer("Something went wrong 😔", show_alert=True)
        except:
            pass


# Handles callbacks from the /help command keyboard
async def help_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle help expand/minimize callbacks"""
    query = update.callback_query
    if query.message.chat.type in ['group', 'supergroup']:
        try:
            chat_member = await context.bot.get_chat_member(query.message.chat.id, context.bot.id)
            if chat_member.status in [ChatMember.LEFT, ChatMember.BANNED]:
                await query.answer("Add me first, my soul might be here but my body not! 🌸", show_alert=True)
                return
        except (BadRequest, Forbidden):
            await query.answer("Add me first, my soul might be here but my body not! 🌸", show_alert=True)
            return

    try:
        user_info = get_user_info(query.message)
        log_action("INFO", f"🔄 Help callback received: {query.data}", user_info)

        user_mention = get_mention(update.effective_user)

        # Determine the new state based on the callback data
        if query.data == "help_expand":
            expanded = True
            await query.answer(HELP_MESSAGES["callback_answers"]["expand"], show_alert=False)
        elif query.data == "help_minimize":
            expanded = False
            await query.answer(HELP_MESSAGES["callback_answers"]["minimize"], show_alert=False)
        else:
            return # Should not happen with the new pattern

        keyboard = create_help_menu(expanded=expanded)
        help_text = get_help_text(user_mention, expanded=expanded)

        # Update the photo caption with new help text and keyboard
        await query.edit_message_caption(
            caption=help_text,
            parse_mode=ParseMode.HTML,
            reply_markup=keyboard
        )

        log_action("INFO", f"✅ Help message {'expanded' if expanded else 'minimized'}", user_info)

    except Exception as e:
        user_info = get_user_info(query.message) if query.message else {}
        log_action("ERROR", f"❌ Error editing help message: {e}", user_info)
        # Fallback: answer the callback to prevent loading state
        try:
            await query.answer("Something went wrong 😔", show_alert=True)
        except:
            pass


# Handles callbacks from the /broadcast command keyboard
async def broadcast_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle broadcast target selection and get flowers again button"""
    query = update.callback_query
    if query.message.chat.type in ['group', 'supergroup']:
        try:
            chat_member = await context.bot.get_chat_member(query.message.chat.id, context.bot.id)
            if chat_member.status in [ChatMember.LEFT, ChatMember.BANNED]:
                await query.answer("Add me first, my soul might be here but my body not! 🌸", show_alert=True)
                return
        except (BadRequest, Forbidden):
            await query.answer("Add me first, my soul might be here but my body not! 🌸", show_alert=True)
            return

    user_info = get_user_info(query.message)

    # Handle "Buy flowers again" button - available for everyone
    if query.data == "get_flowers_again":
        log_action("INFO", "🌸 'Buy flowers again' button clicked", user_info)

        # Answer the callback
        await query.answer("🌸 Getting more flowers for you!", show_alert=False)

        # Send a new invoice with default amount
        try:
            await context.bot.send_invoice(
                chat_id=query.message.chat.id,
                title="Flowers 🌸",
                description=random.choice(INVOICE_DESCRIPTIONS),
                payload=f"sakura_star_{query.from_user.id}",
                provider_token="",  # Empty for stars
                currency="XTR",  # Telegram Stars currency
                prices=[LabeledPrice(label='✨ Sakura Star', amount=50)]
            )

            log_action("INFO", "✅ New invoice sent from 'Buy flowers again' button", user_info)

        except Exception as e:
            log_action("ERROR", f"❌ Error sending new invoice from button: {e}", user_info)
            await query.message.reply_text("❌ Oops! Something went wrong. Try using /buy command instead! 🔧")

        return  # Exit early for get_flowers_again

    # For broadcast-related buttons, check if user is owner
    if query.from_user.id != OWNER_ID:
        log_action("WARNING", "⚠️ Non-owner attempted broadcast callback", user_info)
        await query.answer("You're not authorized to use this 🚫", show_alert=True)
        return

    log_action("INFO", f"🎯 Broadcast target selected: {query.data}", user_info)

    if query.data == "bc_users":
        # Answer callback with proper message
        await query.answer(BROADCAST_MESSAGES["callback_answers"]["users"], show_alert=False)

        broadcast_mode[OWNER_ID] = "users"
        await query.edit_message_text(
            BROADCAST_MESSAGES["ready_users"].format(count=len(user_ids)),
            parse_mode=ParseMode.HTML
        )
        log_action("INFO", f"✅ Ready to broadcast to {len(user_ids)} users", user_info)

    elif query.data == "bc_groups":
        # Answer callback with proper message
        await query.answer(BROADCAST_MESSAGES["callback_answers"]["groups"], show_alert=False)

        broadcast_mode[OWNER_ID] = "groups"
        await query.edit_message_text(
            BROADCAST_MESSAGES["ready_groups"].format(count=len(group_ids)),
            parse_mode=ParseMode.HTML
        )
        log_action("INFO", f"✅ Ready to broadcast to {len(group_ids)} groups", user_info)


# BROADCAST FUNCTIONS
# Executes the broadcast to the selected target (users or groups)
async def execute_broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE, target_type: str, user_info: Dict[str, any]) -> None:
    """Execute broadcast with the current message - uses forward_message for forwarded messages, copy_message for regular messages
    Compatible with python-telegram-bot==22.3"""
    try:
        if target_type == "users":
            # Get fresh data from database
            target_list = await get_users()
            target_list = [uid for uid in target_list if uid != OWNER_ID]
            target_name = "users"
        elif target_type == "groups":
            # Get fresh data from database
            target_list = await get_groups()
            target_name = "groups"
        else:
            return

        log_action("INFO", f"🚀 Starting broadcast to {len(target_list)} {target_name}", user_info)

        if not target_list:
            await update.message.reply_text(
                BROADCAST_MESSAGES["no_targets"].format(target_type=target_name)
            )
            log_action("WARNING", f"⚠️ No {target_name} found for broadcast", user_info)
            return

        # Check if the message is forwarded
        is_forwarded = update.message.forward_origin is not None
        broadcast_method = "forward" if is_forwarded else "copy"

        log_action("INFO", f"📤 Using {broadcast_method} method for broadcast", user_info)

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
                    log_action("DEBUG", f"📡 Broadcast progress: {i}/{len(target_list)} using {broadcast_method}", user_info)

                # Small delay to avoid rate limits
                await asyncio.sleep(BROADCAST_DELAY)

            except Forbidden:
                failed_count += 1
                logger.warning(f"⚠️ User {target_id} blocked the bot. Removing from DB.")
                await remove_user(target_id)
            except BadRequest as e:
                failed_count += 1
                if "chat not found" in str(e).lower():
                    logger.warning(f"⚠️ Chat {target_id} not found. Removing from DB.")
                    if target_name == "users":
                        await remove_user(target_id)
                    else:
                        await remove_group(target_id)
                else:
                    logger.error(f"❌ Broadcast failed for {target_id}: {e}")
            except Exception as e:
                failed_count += 1
                logger.error(f"❌ Unhandled broadcast error for {target_id}: {e}")

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

        log_action("INFO", f"✅ Broadcast completed using {broadcast_method}: {broadcast_count}/{len(target_list)} successful, {failed_count} failed", user_info)

    except Exception as e:
        log_action("ERROR", f"❌ Broadcast error: {e}", user_info)
        await update.message.reply_text(
            BROADCAST_MESSAGES["failed"].format(error=str(e))
        )


# MESSAGE HANDLERS
# Handles incoming sticker messages
async def handle_sticker(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle sticker messages"""
    user_info = get_user_info(update.message)
    log_action("INFO", "🎭 Sticker message received", user_info)

    await send_sticker_action(context, update.effective_chat.id, user_info)

    random_sticker = random.choice(SAKURA_STICKERS)
    chat_type = update.effective_chat.type

    log_action("DEBUG", f"📤 Sending random sticker: {random_sticker}", user_info)

    # In groups, reply to the user's sticker when they replied to bot
    if (chat_type in ['group', 'supergroup'] and
        update.message.reply_to_message and
        update.message.reply_to_message.from_user.id == context.bot.id):
        await update.message.reply_sticker(sticker=random_sticker)
        log_action("INFO", "✅ Replied to user's sticker in group", user_info)
    else:
        # In private chats or regular stickers, send normally
        await context.bot.send_sticker(
            chat_id=update.effective_chat.id,
            sticker=random_sticker
        )
        log_action("INFO", "✅ Sent sticker response", user_info)


# Handles incoming text messages
async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle text and media messages with AI response and effects in private chat"""
    user_info = get_user_info(update.message)
    user_message = update.message.text or update.message.caption or "Media message"

    log_action("INFO", f"💬 Text/media message received: '{user_message[:100]}...'", user_info)

    # Check if user is asking to analyze a previously sent image
    if await analyze_image_reply(update, context, user_message, user_info):
        return

    # Check if user is asking to analyze a previously sent poll
    if await analyze_poll_reply(update, context, user_message, user_info):
        return

    await send_typing(context, update.effective_chat.id, user_info)

    user_name = update.effective_user.first_name or ""

    # Get response from AI
    response = await get_response(user_message, user_name, user_info, update.effective_user.id)

    log_action("DEBUG", f"📤 Sending response: '{response[:50]}...'", user_info)

    # Send response (no effects for Gemini responses)
    await update.message.reply_text(response)

    log_action("INFO", "✅ Text message response sent successfully", user_info)


# Handles incoming image messages
async def handle_image(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle image messages with AI analysis using Gemini 2.5 Flash"""
    user_info = get_user_info(update.message)
    log_action("INFO", "📷 Image message received", user_info)

    # React to the message to show the bot is "thinking"
    try:
        emoji_to_react = random.choice(CONTEXTUAL_REACTIONS["love"])
        await send_big_reaction(
            chat_id=update.effective_chat.id,
            message_id=update.message.message_id,
            emoji=emoji_to_react
        )
        log_action("INFO", f"🤔 Sent analysis reaction '{emoji_to_react}' for image", user_info)
    except Exception as e:
        log_action("WARNING", f"⚠️ Could not send analysis reaction for image: {e}", user_info)

    await send_typing(context, update.effective_chat.id, user_info)

    try:
        # Get the largest photo
        photo = update.message.photo[-1]

        # Get file info
        file = await context.bot.get_file(photo.file_id)

        # Download the image
        image_bytes = await file.download_as_bytearray()

        log_action("DEBUG", f"📥 Image downloaded: {len(image_bytes)} bytes", user_info)

        # Analyze image with AI
        user_name = update.effective_user.first_name or ""
        caption = update.message.caption or ""

        response = await get_response(caption, user_name, user_info, update.effective_user.id, image_bytes=image_bytes)

        log_action("DEBUG", f"📤 Sending image analysis: '{response[:50]}...'", user_info)

        # Send response (no effects for Gemini responses)
        await update.message.reply_text(response)

        log_action("INFO", "✅ Image analysis response sent successfully", user_info)

    except Exception as e:
        log_action("ERROR", f"❌ Error analyzing image: {e}", user_info)
        await update.message.reply_text(get_error())


# Handles incoming poll messages
async def handle_poll(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle poll messages with AI analysis using Gemini 2.5 Flash"""
    user_info = get_user_info(update.message)
    log_action("INFO", "📊 Poll message received", user_info)

    # React to the message to show the bot is "thinking"
    try:
        emoji_to_react = random.choice(CONTEXTUAL_REACTIONS["confused"])
        await send_big_reaction(
            chat_id=update.effective_chat.id,
            message_id=update.message.message_id,
            emoji=emoji_to_react
        )
        log_action("INFO", f"🤔 Sent analysis reaction '{emoji_to_react}' for poll", user_info)
    except Exception as e:
        log_action("WARNING", f"⚠️ Could not send analysis reaction for poll: {e}", user_info)

    await send_typing(context, update.effective_chat.id, user_info)

    try:
        poll = update.message.poll
        poll_question = poll.question
        poll_options = [option.text for option in poll.options]

        log_action("DEBUG", f"📊 Poll question: '{poll_question}' with {len(poll_options)} options", user_info)

        # Analyze poll
        user_name = update.effective_user.first_name or ""

        response = await analyze_poll(poll_question, poll_options, user_name, user_info, update.effective_user.id)

        log_action("DEBUG", f"📤 Sending poll analysis: '{response[:50]}...'", user_info)

        # Send response (no effects for Gemini responses)
        await update.message.reply_text(response)

        log_action("INFO", "✅ Poll analysis response sent successfully", user_info)

    except Exception as e:
        log_action("ERROR", f"❌ Error analyzing poll: {e}", user_info)
        await update.message.reply_text(get_error())


# The main message handler for all incoming messages
async def handle_messages(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle all types of messages (text, stickers, voice, photos, etc.)"""
    try:
        user_info = get_user_info(update.message)
        user_id = update.effective_user.id
        chat_type = update.effective_chat.type

        log_action("DEBUG", f"📨 Processing message in {chat_type}", user_info)

        # Track user and chat IDs for broadcasting
        track_user(update, user_info)

        # Check if user is owner and in broadcast mode
        if user_id == OWNER_ID and OWNER_ID in broadcast_mode:
            log_action("INFO", f"📢 Executing broadcast to {broadcast_mode[OWNER_ID]}", user_info)
            await execute_broadcast(update, context, broadcast_mode[OWNER_ID], user_info)
            del broadcast_mode[OWNER_ID]
            return

        # Check for ping command with prefixes BEFORE group response logic
        user_message = update.message.text or update.message.caption or ""
        ping_prefixes = ['?ping', '!ping', '*ping', '#ping']
        if any(user_message.lower().startswith(prefix) for prefix in ping_prefixes):
            log_action("INFO", f"🏓 Ping command detected with prefix: {user_message}", user_info)
            await ping_command(update, context)
            return

        # Determine if bot should respond
        should_respond = True
        if chat_type in ['group', 'supergroup']:
            should_respond = should_reply(update, context.bot.id)
            if not should_respond:
                log_action("DEBUG", "🚫 Not responding to group message (no mention/reply)", user_info)
                return
            else:
                log_action("INFO", "✅ Responding to group message (mentioned/replied)", user_info)

        # Check rate limiting (using Valkey with memory fallback)
        if await check_limit(user_id, user_info["chat_id"]):
            log_action("WARNING", "⏱️ Rate limited - ignoring message", user_info)
            return

        # Handle contextual reactions in the background
        asyncio.create_task(handle_reaction(update, user_info))

        # Handle different message types
        if update.message.sticker:
            await handle_sticker(update, context)
        elif update.message.photo:
            await handle_image(update, context)
        elif update.message.poll:
            await handle_poll(update, context)
        else:
            await handle_text(update, context)

        # Update response time after sending response
        await update_response_time(user_id)
        log_action("DEBUG", "⏰ Updated user response time in Valkey", user_info)

    except Exception as e:
        user_info = get_user_info(update.message)
        log_action("ERROR", f"❌ Error handling message: {e}", user_info)
        if update.message.text:
            await update.message.reply_text(get_error())


# Handles chat member updates (e.g., when the bot is blocked or removed from a group)
async def handle_member_update(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle when a user blocks the bot or the bot is removed from a group."""
    result = update.my_chat_member
    if not result:
        return

    chat = result.chat
    new_status = result.new_chat_member.status

    if new_status in [ChatMember.BANNED, ChatMember.LEFT]:
        if chat.type == 'private':
            logger.info(f"User {chat.id} blocked the bot. Removing from database.")
            await remove_user(chat.id)
        elif chat.type in ['group', 'supergroup']:
            logger.info(f"Bot was removed from group {chat.id}. Removing from database.")
            await remove_group(chat.id)


# ERROR HANDLER
# The main error handler for the bot
async def handle_error(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Log errors caused by updates and provide clean, informative feedback.
    Handles specific Telegram errors gracefully and logs detailed tracebacks for others.
    """
    err = context.error

    # Handle common Telegram API errors with clean, single-line logs
    if isinstance(err, Conflict):
        logger.warning(f"⚠️ Conflict Error: {err}. The bot might be running on another instance.")
        return
    if isinstance(err, Forbidden):
        logger.warning(f"⚠️ Forbidden Error: {err}. Bot may be blocked or kicked from a chat.")
        return
    if isinstance(err, BadRequest):
        logger.warning(f"⚠️ BadRequest Error: {err}. The request was malformed.")
        return
    if isinstance(err, NetworkError):
        logger.warning(f"⚠️ Network Error: {err}. A network issue occurred during the request.")
        return

    # For all other exceptions, log the full traceback for detailed debugging
    tb_list = traceback.format_exception(None, err, err.__traceback__)
    tb_string = "".join(tb_list)
    logger.error(f"❌ An unhandled exception occurred:\n{tb_string}")

    # Try to extract user info for additional context if possible
    user_info_str = "N/A"
    if hasattr(update, "effective_user") and update.effective_user:
        user_info_str = f"User: {update.effective_user.id}"
    if hasattr(update, "effective_chat") and update.effective_chat:
        user_info_str += f", Chat: {update.effective_chat.id} ({update.effective_chat.type})"

    logger.error(f"💥 Exception context: Update={update}, Context={user_info_str}")


# STAR PAYMENT FUNCTIONS
# Handles the /buy command to send a payment invoice
async def buy_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Send an invoice for sakura flowers."""
    try:
        user_info = get_user_info(update.message)
        log_action("INFO", "🌸 /buy command received", user_info)

        # Track user for broadcasting
        track_user(update, user_info)

        # Step 1: React to the buy message with random emoji and animation
        if EMOJI_REACT:
            try:
                random_emoji = random.choice(EMOJI_REACT)

                # Use Telethon for animated emoji reactions
                if effects_client and update.effective_chat.type == "private":
                    reaction_sent = await send_big_reaction(
                        update.effective_chat.id,
                        update.message.message_id,
                        random_emoji
                    )
                    if reaction_sent:
                        log_action("DEBUG", f"🎭 Added animated emoji reaction: {random_emoji}", user_info)
                    else:
                        # Fallback to PTB reaction without animation
                        await add_reaction(context, update, random_emoji, user_info)
                else:
                    # Group chat or no Telethon - use PTB reaction
                    await add_reaction(context, update, random_emoji, user_info)

            except Exception as e:
                log_action("WARNING", f"⚠️ Failed to add emoji reaction: {e}", user_info)

        # Step 1.5: Send typing action
        await send_typing(context, update.effective_chat.id, user_info)

        # Default to 50 stars, but allow user to specify amount
        amount = 50
        if len(update.message.text.split()) > 1 and update.message.text.split()[1].isdigit():
            amount = int(update.message.text.split()[1])
            # Limit to reasonable amounts
            if amount > 100000:
                amount = 100000
            elif amount < 1:
                amount = 1

        # Step 2: Send invoice with effects if in private chat
        if update.effective_chat.type == "private":
            # Use direct API to send invoice with effects
            try:
                url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendInvoice"
                payload = {
                    'chat_id': update.message.chat.id,
                    'title': "Flowers 🌸",
                    'description': random.choice(INVOICE_DESCRIPTIONS),
                    'payload': f"sakura_star_{update.message.from_user.id}",
                    'provider_token': "",  # Empty for stars
                    'currency': "XTR",  # Telegram Stars currency
                    'prices': [{'label': '✨ Sakura Star', 'amount': amount}],
                    'message_effect_id': random.choice(EFFECTS)
                }

                async with aiohttp.ClientSession() as session:
                    async with session.post(
                        url,
                        data=orjson.dumps(payload),
                        headers={'Content-Type': 'application/json'}
                    ) as response:
                        result = await response.json(loads=orjson.loads)
                        if result.get('ok'):
                            log_action("INFO", f"✨ Invoice with effects sent for {amount} stars", user_info)
                        else:
                            # Fallback to normal invoice
                            raise Exception("Effects invoice failed")
            except Exception:
                # Fallback to normal PTB invoice
                await context.bot.send_invoice(
                    chat_id=update.message.chat.id,
                    title="Flowers 🌸",
                    description=random.choice(INVOICE_DESCRIPTIONS),
                    payload=f"sakura_star_{update.message.from_user.id}",
                    provider_token="",  # Empty for stars
                    currency="XTR",  # Telegram Stars currency
                    prices=[LabeledPrice(label='✨ Sakura Star', amount=amount)]
                )
                log_action("WARNING", f"⚠️ Invoice sent without effects (fallback) for {amount} stars", user_info)
        else:
            # Group chat - no effects, just normal invoice
            await context.bot.send_invoice(
                chat_id=update.message.chat.id,
                title="Flowers 🌸",
                description=random.choice(INVOICE_DESCRIPTIONS),
                payload=f"sakura_star_{update.message.from_user.id}",
                provider_token="",  # Empty for stars
                currency="XTR",  # Telegram Stars currency
                prices=[LabeledPrice(label='✨ Sakura Star', amount=amount)]
            )
            log_action("INFO", f"✅ Invoice sent for {amount} stars", user_info)

    except Exception as e:
        user_info = get_user_info(update.message)
        log_action("ERROR", f"❌ Error sending invoice: {e}", user_info)
        await update.message.reply_text("❌ Oops! Something went wrong creating the invoice. Try again later! 🔧")

# Handles the /buyers command to show top supporters
async def buyers_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Show all flower buyers with their donation amounts."""
    try:
        user_info = get_user_info(update.message)
        log_action("INFO", "💝 /buyers command received", user_info)

        # Track user for broadcasting
        track_user(update, user_info)

        # Step 1: React to the buyers message with random emoji and animation
        if EMOJI_REACT:
            try:
                random_emoji = random.choice(EMOJI_REACT)

                # Use Telethon for animated emoji reactions
                if effects_client and update.effective_chat.type == "private":
                    reaction_sent = await send_big_reaction(
                        update.effective_chat.id,
                        update.message.message_id,
                        random_emoji
                    )
                    if reaction_sent:
                        log_action("DEBUG", f"🎭 Added animated emoji reaction: {random_emoji}", user_info)
                    else:
                        # Fallback to PTB reaction without animation
                        await add_reaction(context, update, random_emoji, user_info)
                else:
                    # Group chat or no Telethon - use PTB reaction
                    await add_reaction(context, update, random_emoji, user_info)

            except Exception as e:
                log_action("WARNING", f"⚠️ Failed to add emoji reaction: {e}", user_info)

        # Step 2: Send typing action
        await send_typing(context, update.effective_chat.id, user_info)

        # Get all purchases from database
        purchases = await get_purchases()

        if not purchases:
            no_buyers_text = (
                "🌸 <b>Flower Buyers</b>\n\n"
                "No one has bought flowers yet! Be the first to support with /buy 💝"
            )

            # Send with effects if in private chat
            if update.effective_chat.type == "private":
                # Use direct API to send no buyers message with effects
                try:
                    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
                    payload = {
                        'chat_id': update.effective_chat.id,
                        'text': no_buyers_text,
                        'message_effect_id': random.choice(EFFECTS),
                        'parse_mode': 'HTML'
                    }

                    async with aiohttp.ClientSession() as session:
                        async with session.post(
                            url,
                            data=orjson.dumps(payload),
                            headers={'Content-Type': 'application/json'}
                        ) as response:
                            result = await response.json(loads=orjson.loads)
                            if result.get('ok'):
                                log_action("INFO", "✨ No buyers message with effects sent successfully", user_info)
                            else:
                                # Fallback to normal PTB message if effects fail
                                await update.message.reply_text(
                                    no_buyers_text,
                                    parse_mode=ParseMode.HTML
                                )
                                log_action("WARNING", "⚠️ No buyers message sent without effects (fallback)", user_info)
                except Exception:
                    # Fallback to normal PTB message if effects fail
                    await update.message.reply_text(
                        no_buyers_text,
                        parse_mode=ParseMode.HTML
                    )
                    log_action("WARNING", "⚠️ No buyers message sent without effects (fallback)", user_info)
            else:
                # Group chat - no effects, just normal message
                await update.message.reply_text(
                    no_buyers_text,
                    parse_mode=ParseMode.HTML
                )

            log_action("INFO", "✅ No buyers found message sent", user_info)
            return

        # Build the buyers list
        buyers_text = "🌸 <b>Flower Buyers</b>\n\n"
        buyers_text += "💝 <i>Thank you to all our wonderful supporters!</i>\n\n"

        for i, purchase in enumerate(purchases, 1):
            user_id = purchase['user_id']
            username = purchase['username']
            first_name = purchase['first_name'] or "Anonymous"
            total_amount = purchase['total_amount']
            purchase_count = purchase['purchase_count']

            # Create user mention using first name
            user_mention = f'<a href="tg://user?id={user_id}">{first_name}</a>'

            # Add rank emoji
            if i == 1:
                rank_emoji = "🥇"
            elif i == 2:
                rank_emoji = "🥈"
            elif i == 3:
                rank_emoji = "🥉"
            else:
                rank_emoji = f"{i}."

            buyers_text += f"{rank_emoji} {user_mention} - {total_amount} ⭐"
            if purchase_count > 1:
                buyers_text += f" ({purchase_count} purchases)"
            buyers_text += "\n"

        buyers_text += f"\n🌸 <i>Total buyers: {len(purchases)}</i>"

        # Step 3: Send buyers list with effects if in private chat
        if update.effective_chat.type == "private":
            # Use direct API to send buyers list with effects
            try:
                url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
                payload = {
                    'chat_id': update.effective_chat.id,
                    'text': buyers_text,
                    'message_effect_id': random.choice(EFFECTS),
                    'parse_mode': 'HTML',
                    'disable_web_page_preview': True
                }

                async with aiohttp.ClientSession() as session:
                    async with session.post(
                        url,
                        data=orjson.dumps(payload),
                        headers={'Content-Type': 'application/json'}
                    ) as response:
                        result = await response.json(loads=orjson.loads)
                        if result.get('ok'):
                            log_action("INFO", f"✨ Buyers list with effects sent with {len(purchases)} buyers", user_info)
                        else:
                            # Fallback to normal PTB message if effects fail
                            await update.message.reply_text(
                                buyers_text,
                                parse_mode=ParseMode.HTML,
                                disable_web_page_preview=True
                            )
                            log_action("WARNING", f"⚠️ Buyers list sent without effects (fallback) with {len(purchases)} buyers", user_info)
            except Exception:
                # Fallback to normal PTB message if effects fail
                await update.message.reply_text(
                    buyers_text,
                    parse_mode=ParseMode.HTML,
                    disable_web_page_preview=True
                )
                log_action("WARNING", f"⚠️ Buyers list sent without effects (fallback) with {len(purchases)} buyers", user_info)
        else:
            # Group chat - no effects, just normal message
            await update.message.reply_text(
                buyers_text,
                parse_mode=ParseMode.HTML,
                disable_web_page_preview=True
            )
            log_action("INFO", f"✅ Buyers list sent with {len(purchases)} buyers", user_info)

    except Exception as e:
        user_info = get_user_info(update.message)
        log_action("ERROR", f"❌ Error in buyers command: {e}", user_info)
        await update.message.reply_text("❌ Something went wrong getting the buyers list. Try again later! 🔧")


# Handles the /stats command (owner only)
async def stats_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Hidden owner command to show bot statistics with refresh functionality"""
    try:
        user_info = get_user_info(update.message)

        # Check if user is owner
        if update.effective_user.id != OWNER_ID:
            log_action("WARNING", "⚠️ Non-owner attempted /stats command", user_info)
            return

        log_action("INFO", "📊 /stats command received from owner", user_info)

        # Send stats with refresh button
        await send_stats(update.message.chat.id, context, is_refresh=False)

        log_action("INFO", "✅ Bot statistics sent to owner", user_info)

    except Exception as e:
        user_info = get_user_info(update.message)
        log_action("ERROR", f"❌ Error in /stats command: {e}", user_info)
        await update.message.reply_text("❌ Something went wrong getting bot statistics!")


# Sends the statistics message
async def send_stats(chat_id: int, context: ContextTypes.DEFAULT_TYPE, is_refresh: bool = False) -> None:
    """Send or update stats message with current data"""
    try:
        # Calculate ping to Telegram servers
        ping_start = time.time()
        try:
            await context.bot.get_me()
            ping_ms = round((time.time() - ping_start) * 1000, 2)
        except Exception:
            ping_ms = "Error"

        # Calculate bot uptime (using process start time)
        try:
            boot_time = psutil.boot_time()
            process = psutil.Process()
            process_start = process.create_time()
            uptime_seconds = time.time() - process_start

            # Format uptime
            days = int(uptime_seconds // 86400)
            hours = int((uptime_seconds % 86400) // 3600)
            minutes = int((uptime_seconds % 3600) // 60)
            uptime_str = f"{days}d {hours}h {minutes}m"
        except Exception as e:
            uptime_str = "Unknown"

        # Get current time
        current_time = datetime.datetime.now()

        # System Information
        cpu_percent = psutil.cpu_percent(interval=0.1)
        memory = psutil.virtual_memory()

        # Database Statistics
        db_stats = {
            'users_count': len(user_ids),
            'groups_count': len(group_ids),
            'total_purchases': 0,
            'total_revenue': 0,
            'active_conversations': len(conversation_history)
        }

        if db_pool:
            try:
                async with db_pool.acquire() as conn:
                    # Get purchase statistics
                    purchase_stats = await conn.fetchrow("""
                        SELECT COUNT(*) as total_purchases, COALESCE(SUM(amount), 0) as total_revenue
                        FROM purchases
                    """)
                    if purchase_stats:
                        db_stats['total_purchases'] = purchase_stats['total_purchases']
                        db_stats['total_revenue'] = purchase_stats['total_revenue']

                    # Get recent activity (last 24 hours)
                    recent_users = await conn.fetchval("""
                        SELECT COUNT(*) FROM users
                        WHERE updated_at > NOW() - INTERVAL '24 hours'
                    """)
                    db_stats['recent_users'] = recent_users or 0

                    recent_purchases = await conn.fetchval("""
                        SELECT COUNT(*) FROM purchases
                        WHERE created_at > NOW() - INTERVAL '24 hours'
                    """)
                    db_stats['recent_purchases'] = recent_purchases or 0

            except Exception as e:
                logger.error(f"Error getting database stats: {e}")

        # Build stats message
        stats_message = f"""📊 <b>Sakura Bot Statistics</b>
<i>Last Updated: {current_time.strftime('%H:%M:%S')}</i>

🏓 <b>Bot Performance</b>
├ Uptime: <b>{uptime_str}</b>
└ Ping: <b>{ping_ms}ms</b>

👥 <b>User Statistics</b>
├ Total Users: <b>{db_stats['users_count']}</b>
├ Total Groups: <b>{db_stats['groups_count']}</b>
├ Recent Users (24h): <b>{db_stats.get('recent_users', 'N/A')}</b>
├ Active Conversations: <b>{db_stats['active_conversations']}</b>
├ Total Purchases: <b>{db_stats['total_purchases']}</b>
├ Total Revenue: <b>{db_stats['total_revenue']} ⭐</b>
└ Recent Purchases (24h): <b>{db_stats.get('recent_purchases', 'N/A')}</b>

🖥️ <b>System Resources</b>
├ CPU Usage: <b>{cpu_percent}%</b>
└ Memory: <b>{memory.percent}%</b> ({memory.used // (1024**3)}GB / {memory.total // (1024**3)}GB)"""

        # Create refresh button
        keyboard = [[InlineKeyboardButton("🔄 Refresh", callback_data="refresh_stats")]]
        reply_markup = InlineKeyboardMarkup(keyboard)

        if is_refresh:
            return stats_message, reply_markup
        else:
            await context.bot.send_message(
                chat_id=chat_id,
                text=stats_message,
                parse_mode=ParseMode.HTML,
                reply_markup=reply_markup,
                disable_web_page_preview=True
            )

    except Exception as e:
        logger.error(f"❌ Error generating stats message: {e}")
        if not is_refresh:
            await context.bot.send_message(chat_id, "❌ Error generating statistics!")


# Handles the refresh callback for the /stats command
async def stats_refresh(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle stats refresh button callback"""
    query = update.callback_query
    if query.message.chat.type in ['group', 'supergroup']:
        try:
            chat_member = await context.bot.get_chat_member(query.message.chat.id, context.bot.id)
            if chat_member.status in [ChatMember.LEFT, ChatMember.BANNED]:
                await query.answer("Add me first, my soul might be here but my body not! 🌸", show_alert=True)
                return
        except (BadRequest, Forbidden):
            await query.answer("Add me first, my soul might be here but my body not! 🌸", show_alert=True)
            return

    try:
        user_info = get_user_info(query.message)

        # Check if user is owner
        if query.from_user.id != OWNER_ID:
            log_action("WARNING", "⚠️ Non-owner attempted stats refresh", user_info)
            await query.answer("You're not authorized to use this 🚫", show_alert=True)
            return

        log_action("INFO", "🔄 Stats refresh callback received from owner", user_info)

        # Answer the callback
        await query.answer("🔄 Refreshing statistics...", show_alert=False)

        # Get updated stats
        stats_message, reply_markup = await send_stats(query.message.chat.id, context, is_refresh=True)

        # Update the message
        await query.edit_message_text(
            text=stats_message,
            parse_mode=ParseMode.HTML,
            reply_markup=reply_markup,
            disable_web_page_preview=True
        )

        log_action("INFO", "✅ Stats refreshed successfully", user_info)

    except Exception as e:
        user_info = get_user_info(query.message) if query.message else {}
        log_action("ERROR", f"❌ Error refreshing stats: {e}", user_info)
        try:
            await query.answer("❌ Error refreshing statistics!", show_alert=True)
        except:
            pass


# Retrieves user information from the database by user ID or username
async def find_user(identifier: str) -> tuple:
    """Get user info by user ID or username from database"""
    if not db_pool:
        return None, None

    try:
        async with db_pool.acquire() as conn:
            if identifier.isdigit():
                # Search by user ID
                row = await conn.fetchrow(
                    "SELECT user_id, username, first_name, last_name FROM users WHERE user_id = $1",
                    int(identifier)
                )
            else:
                # Search by username (remove @ if present)
                username = identifier.lstrip('@')
                row = await conn.fetchrow(
                    "SELECT user_id, username, first_name, last_name FROM users WHERE username = $1",
                    username
                )

            if row:
                display_name = row['first_name'] or row['username'] or f"User {row['user_id']}"
                return row['user_id'], display_name

        return None, None

    except Exception as e:
        logger.error(f"❌ Error looking up user {identifier}: {e}")
        return None, None


# Handles the pre-checkout query for payments
async def precheckout_query(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Answer the PreCheckoutQuery."""
    query = update.pre_checkout_query

    # Always approve the payment
    await context.bot.answer_pre_checkout_query(
        pre_checkout_query_id=query.id,
        ok=True
    )

    logger.info(f"💳 Pre-checkout approved for user {query.from_user.id}")


# Handles successful payments
async def successful_payment(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle successful payment - refund if 10 stars or less, otherwise process normally."""
    payment = update.message.successful_payment
    user_id = update.message.from_user.id
    amount = payment.total_amount
    user_info = get_user_info(update.message)

    log_action("INFO", f"💰 Payment received for {amount} stars", user_info)

    # Save purchase to database for amounts > 10 stars (not refunded)
    if amount > 10:
        save_purchase(
            user_id=user_id,
            username=user_info.get("username"),
            first_name=user_info.get("first_name"),
            last_name=user_info.get("last_name"),
            amount=amount,
            charge_id=payment.telegram_payment_charge_id
        )

    # Check if amount is 10 stars or less
    if amount <= 10:
        log_action("INFO", f"🔄 Refunding payment of {amount} stars (kindness gesture)", user_info)

        # Wait 4 seconds after payment
        await asyncio.sleep(4)

        # Store payment info for refund
        payment_storage[payment.telegram_payment_charge_id] = {
            'user_id': user_id,
            'amount': amount,
            'charge_id': payment.telegram_payment_charge_id
        }

        try:
            # Refund the payment
            await context.bot.refund_star_payment(
                user_id=user_id,
                telegram_payment_charge_id=payment.telegram_payment_charge_id
            )

            # Create inline keyboard with "Buy flowers again" button
            keyboard = [[InlineKeyboardButton("Buy flowers again 🌸", callback_data="get_flowers_again")]]
            reply_markup = InlineKeyboardMarkup(keyboard)

            # Send refund message with button and effects
            refund_msg = random.choice(REFUND_MESSAGES)

            # Send with effects if in private chat
            if update.message.chat.type == "private":
                # Use direct API to send refund message with effects
                try:
                    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
                    payload = {
                        'chat_id': update.message.chat.id,
                        'text': refund_msg,
                        'message_effect_id': random.choice(EFFECTS),
                        'parse_mode': 'HTML',
                        'reply_markup': reply_markup.to_dict()
                    }

                    async with aiohttp.ClientSession() as session:
                        async with session.post(
                            url,
                            data=orjson.dumps(payload),
                            headers={'Content-Type': 'application/json'}
                        ) as response:
                            result = await response.json(loads=orjson.loads)
                            if result.get('ok'):
                                log_action("INFO", "✨ Refund message with effects sent successfully", user_info)
                            else:
                                # Fallback to normal PTB message if effects fail
                                await update.message.reply_text(refund_msg, reply_markup=reply_markup)
                                log_action("WARNING", "⚠️ Refund message sent without effects (fallback)", user_info)
                except Exception:
                    # Fallback to normal PTB message if effects fail
                    await update.message.reply_text(refund_msg, reply_markup=reply_markup)
                    log_action("WARNING", "⚠️ Refund message sent without effects (fallback)", user_info)
            else:
                # Group chat - no effects, just normal message
                await update.message.reply_text(refund_msg, reply_markup=reply_markup)

            log_action("INFO", "✅ Refund completed successfully", user_info)

        except Exception as e:
            log_action("ERROR", f"❌ Error refunding payment: {e}", user_info)
            await update.message.reply_text("❌ Sorry, there was an issue processing your refund. Please contact support.")

    else:
        log_action("INFO", f"✅ Processing payment of {amount} stars (no refund)", user_info)

        # Wait 4 seconds after payment
        await asyncio.sleep(4)

        # Send random sticker
        sticker_id = random.choice(PAYMENT_STICKERS)
        await context.bot.send_sticker(chat_id=update.message.chat.id, sticker=sticker_id)

        # Wait another 4 seconds
        await asyncio.sleep(4)

        # Create inline keyboard with "Buy flowers again" button
        keyboard = [[InlineKeyboardButton("Buy flowers again 🌸", callback_data="get_flowers_again")]]
        reply_markup = InlineKeyboardMarkup(keyboard)

        # Send thank you message with button and effects
        success_msg = random.choice(THANK_YOU_MESSAGES)

        # Send with effects if in private chat
        if update.message.chat.type == "private":
            # Use direct API to send thank you message with effects
            try:
                url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
                payload = {
                    'chat_id': update.message.chat.id,
                    'text': success_msg,
                    'message_effect_id': random.choice(EFFECTS),
                    'parse_mode': 'HTML',
                    'reply_markup': reply_markup.to_dict()
                }

                async with aiohttp.ClientSession() as session:
                    async with session.post(
                        url,
                        data=orjson.dumps(payload),
                        headers={'Content-Type': 'application/json'}
                    ) as response:
                        result = await response.json(loads=orjson.loads)
                        if result.get('ok'):
                            log_action("INFO", "✨ Thank you message with effects sent successfully", user_info)
                        else:
                            # Fallback to normal PTB message if effects fail
                            await update.message.reply_text(success_msg, reply_markup=reply_markup)
                            log_action("WARNING", "⚠️ Thank you message sent without effects (fallback)", user_info)
            except Exception:
                # Fallback to normal PTB message if effects fail
                await update.message.reply_text(success_msg, reply_markup=reply_markup)
                log_action("WARNING", "⚠️ Thank you message sent without effects (fallback)", user_info)
        else:
            # Group chat - no effects, just normal message
            await update.message.reply_text(success_msg, reply_markup=reply_markup)

        log_action("INFO", "✅ Payment processed successfully", user_info)


# BOT SETUP FUNCTIONS
# Sets up the bot's commands
async def setup_commands(application: Application) -> None:
    """Setup bot commands menu"""
    try:
        await application.bot.set_my_commands(COMMANDS)
        logger.info("✅ Bot commands menu set successfully")

    except Exception as e:
        logger.error(f"Failed to set bot commands: {e}")


# Sets up all the handlers for the bot
def setup_handlers(application: Application) -> None:
    """Setup all command and message handlers"""
    logger.info("🔧 Setting up bot handlers...")

    # Command handlers
    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("broadcast", broadcast_command))
    application.add_handler(CommandHandler("ping", ping_command))
    application.add_handler(CommandHandler("buy", buy_command))
    application.add_handler(CommandHandler("buyers", buyers_command))
    application.add_handler(CommandHandler("stats", stats_command))  # Hidden owner command

    # Callback query handlers
    application.add_handler(CallbackQueryHandler(start_callback, pattern="^start_"))
    application.add_handler(CallbackQueryHandler(help_callback, pattern="^help_"))
    application.add_handler(CallbackQueryHandler(broadcast_callback, pattern="^bc_|^get_flowers_again$"))
    application.add_handler(CallbackQueryHandler(stats_refresh, pattern="^refresh_stats$"))

    # Payment handlers
    application.add_handler(PreCheckoutQueryHandler(precheckout_query))
    application.add_handler(MessageHandler(filters.SUCCESSFUL_PAYMENT, successful_payment))

    # Message handler for all message types
    application.add_handler(MessageHandler(
        filters.TEXT | filters.Sticker.ALL | filters.VOICE | filters.VIDEO_NOTE |
        filters.PHOTO | filters.Document.ALL | filters.POLL & ~filters.COMMAND,
        handle_messages
    ))

    # Chat member handler to track when bot is added/removed from chats
    application.add_handler(ChatMemberHandler(handle_member_update, ChatMemberHandler.MY_CHAT_MEMBER))

    # Error handler
    application.add_error_handler(handle_error)

    logger.info("✅ All handlers setup completed")


# MAIN FUNCTION
async def main() -> None:
    """Main asynchronous function to run the bot."""
    if not validate_config():
        return

    logger.info("🚀 Initializing Sakura Bot...")

    # Start dummy server in a background thread for keep-alive
    threading.Thread(target=start_server, daemon=True).start()

    # --- Step 1: Initialize services before starting the bot ---
    # This ensures database connections are ready and data is loaded.
    logger.info("🔗 Connecting to services...")
    if not await connect_cache():
        logger.warning("⚠️ Valkey initialization failed. Bot will continue with memory fallback.")

    # This call is now awaited, so we know it's finished before proceeding.
    # connect_database() also calls load_data() internally.
    if not await connect_database():
        logger.error("❌ Database initialization failed. Bot cannot continue.")
        return

    await start_effects()
    logger.info("✅ Services connected successfully.")

    # --- Step 2: Set up the bot application ---
    application = Application.builder().token(BOT_TOKEN).concurrent_updates(True).build()

    # We are no longer using post_init/post_shutdown as we control the lifecycle directly.
    application.post_init = None
    application.post_shutdown = None

    # Register all handlers (commands, messages, etc.)
    setup_handlers(application)

    cleanup_task = None
    try:
        # The `async with` block handles application.initialize() and application.shutdown()
        async with application:
            # --- Step 3: Start background tasks and polling ---
            await setup_commands(application)

            # Start the background task for cleaning up old conversations
            cleanup_task = asyncio.create_task(cleanup_conversations())

            # Pre-flight check to detect critical errors before polling
            logger.info("📡 Performing pre-flight check...")
            try:
                await application.bot.get_updates(limit=1)
                logger.info("✅ Pre-flight check successful.")
            except Conflict:
                logger.error(
                    "❌ Conflict: Another instance of the bot is already running. "
                    "Please stop the other instance before starting a new one."
                )
                return
            except Forbidden:
                logger.error(
                    "❌ Forbidden: The bot token is invalid or expired. "
                    "Please check your BOT_TOKEN environment variable."
                )
                return
            except NetworkError as e:
                logger.error(f"❌ NetworkError on startup: {e}. Check your internet connection.")
                return
            except Exception as e:
                logger.error(f"❌ An unexpected error occurred during pre-flight check: {e}")
                return

            logger.info("🌸 Sakura Bot is starting polling...")
            try:
                await application.start()
                await application.updater.start_polling(
                    allowed_updates=Update.ALL_TYPES,
                    drop_pending_updates=True
                )
            except Exception as e:
                logger.error(f"❌ Failed to start polling: {e}")
                return

            # Keep the script running until interrupted
            await asyncio.Future()

    except (KeyboardInterrupt, asyncio.CancelledError):
        logger.info("🛑 Bot shutdown initiated by user...")

    finally:
        # --- Step 4: Graceful shutdown ---
        logger.info("🔌 Shutting down services...")
        if application.updater and application.updater.is_running:
            await application.updater.stop()
        if application.running:
            await application.stop()
        if cleanup_task and not cleanup_task.done():
            cleanup_task.cancel()
            try:
                await cleanup_task
            except asyncio.CancelledError:
                pass  # This is expected.

        await close_database()
        await close_cache()
        await stop_effects()
        logger.info("🌸 Sakura Bot shutdown completed!")

# HTTP SERVER FOR DEPLOYMENT
# A dummy HTTP handler for keep-alive purposes on deployment platforms
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


# Starts the dummy HTTP server
def start_server() -> None:
    """Start dummy HTTP server for deployment platforms"""
    port = int(os.environ.get("PORT", 10000))
    server = HTTPServer(("0.0.0.0", port), DummyHandler)
    logger.info(f"🌐 Dummy server listening on port {port}")
    server.serve_forever()


if __name__ == "__main__":
    # Install uvloop for better performance if available
    try:
        uvloop.install()
        logger.info("🚀 uvloop installed successfully")
    except ImportError:
        logger.warning("⚠️ uvloop not available, running with default asyncio loop")
    except Exception as e:
        logger.warning(f"⚠️ uvloop setup failed: {e}")

    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("🛑 Bot stopped by user.")
    except Exception as e:
        logger.error(f"💥 Fatal error in main execution: {e}")
