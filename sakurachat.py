import os
import logging
import asyncio
import random
import requests
import json
import google.generativeai as genai
from datetime import datetime

# ─── Imports for Dummy HTTP Server ──────────────────────────────────────────
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer

# ── Logging setup ─────────────────────────────────────────────────────────────
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# ── Configuration ──────────────────────────────────────────────────────────────
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
TELEGRAM_API_URL = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}"

if not TELEGRAM_TOKEN or not GEMINI_API_KEY:
    logger.error("TELEGRAM_TOKEN and GEMINI_API_KEY must be set.")
    exit(1)

# ── Configure Gemini ───────────────────────────────────────────────────────────
genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel("gemini-1.5-flash")

# ── In‐memory state ────────────────────────────────────────────────────────────
user_chats = {}       # Stores Gemini chat objects per user_id
last_update_id = 0    # For getUpdates offset

# ── Sakura’s sticker IDs ───────────────────────────────────────────────────────
# Replace these with the actual file_ids you collected from your sticker pack(s):
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
    "CAACAgUAAxkBAAEOnNZoOwIEftJuRGfJStGlNvCKNHnNNAACrxgAAtxdsFVMjTuKjuZHZDYE",  # ► Sakura sticker #14
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

# ── Sakura personality prompt ─────────────────────────────────────────────────
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
– Use the user’s name very rarely: only when greeting at start, or when extremely necessary for emphasis
– Otherwise, do not include the user’s name in replies

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
    "I’m right here 😇",
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
    "Say anything, I’ll listen 👀",
    "Your space, your pace ❤️",
    "Not leaving 💓",
    "Always here 💕",
    "I'm all ears 🤗",
    "Let’s be okay together 🫠",
    "You matter 💔 but you're loved 💞",
    "I care. A lot. 😕",
    "Let it out or don’t. Still love you ❤️",
    "Even if it’s messy 😝",
    "Tired? Me too 🥲"
]

ERROR_MESSAGES = [
    "Ugh… tech 😕",
    "Wait what 😬",
    "Didn’t work 🙃",
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
    "Don’t blame yourself 😇",
    "I still love you 💞",
    "That didn’t land 💔",
    "Retry? 🤗",
    "Smol error 🫠",
    "Oops but we’re fine 💕",
    "Just a hiccup 😝"
]

# ── Utility: send a message (with optional reply_to_message_id) ─────────────────
def send_message(chat_id, text, reply_to_message_id=None, reply_markup=None):
    try:
        url = f"{TELEGRAM_API_URL}/sendMessage"
        data = {
            "chat_id": chat_id,
            "text": text,
            "parse_mode": "HTML"
        }
        if reply_to_message_id:
            data["reply_to_message_id"] = reply_to_message_id
        if reply_markup:
            data["reply_markup"] = reply_markup
        response = requests.post(url, json=data)
        return response.json()
    except Exception as e:
        logger.error(f"Error sending message: {e}")
        return None

# ── Utility: send “chat action” so it looks like Sakura is doing something ────────
def send_chat_action(chat_id, action="typing"):
    """
    Use action="typing" to show “… is typing”.
    Use action="choose_sticker" to show “… is choosing a sticker”.
    """
    try:
        url = f"{TELEGRAM_API_URL}/sendChatAction"
        data = {
            "chat_id": chat_id,
            "action": action
        }
        requests.post(url, json=data)
    except Exception as e:
        logger.error(f"Error sending chat action: {e}")

# ── Utility: send a sticker (with optional reply_to_message_id) ───────────────
def send_sticker(chat_id, sticker_file_id, reply_to_message_id=None):
    """
    Send a sticker to `chat_id`. If `reply_to_message_id` is set,
    Sakura will reply to that specific message with the sticker.
    """
    try:
        url = f"{TELEGRAM_API_URL}/sendSticker"
        data = {
            "chat_id": chat_id,
            "sticker": sticker_file_id
        }
        if reply_to_message_id:
            data["reply_to_message_id"] = reply_to_message_id
        response = requests.post(url, json=data)
        return response.json()
    except Exception as e:
        logger.error(f"Error sending sticker: {e}")
        return None

# ── Utility: send a random Sakura sticker ──────────────────────────────────────
def send_random_sakura_sticker(chat_id, reply_to_message_id=None):
    """
    Chooses one sticker_file_id at random from sakura_stickers,
    shows “choosing a sticker” action, then sends it.
    """
    if not sakura_stickers:
        return

    # 1) Show “Sakura is choosing a sticker…” indicator
    send_chat_action(chat_id, action="choose_sticker")

    # 2) Pick random sticker and send
    sticker_id = random.choice(sakura_stickers)
    send_sticker(chat_id, sticker_id, reply_to_message_id=reply_to_message_id)

# ── Poll Telegram for new updates ────────────────────────────────────────────────
def get_updates():
    global last_update_id
    try:
        url = f"{TELEGRAM_API_URL}/getUpdates"
        params = {
            "offset": last_update_id + 1,
            "timeout": 30
        }
        response = requests.get(url, params=params)
        return response.json()
    except Exception as e:
        logger.error(f"Error getting updates: {e}")
        return None

# ── Register /start and /help commands so Telegram shows them in UI ──────────────
def set_my_commands():
    commands = [
        {"command": "start", "description": "Start the bot"},
        {"command": "help", "description": "How to use Sakura bot"}
    ]
    url = f"{TELEGRAM_API_URL}/setMyCommands"
    response = requests.post(url, json={"commands": commands})
    if response.status_code == 200:
        logger.info("Bot commands set successfully")
    else:
        logger.error("Failed to set bot commands")

# ── Handle /start ───────────────────────────────────────────────────────────────
def handle_start_command(chat_id, user_id):
    welcome_message = """
<b>Hey there… I’m Sakura Haruno!</b> Your gentle guide and safe place 🌸
  
It’s so good you’re here. I speak softly, listen closely, and stay with you through every quiet storm  
Whether you need a caring whisper, a patient heart, or just someone to be there, I’m all yours 💓

Even when things feel heavy… you’re never alone  
Take a breath… I’m right here, and we’ll face it all together  💞

You’re stronger than you feel. Brighter than you know. And I believe in you always! 🤎
"""
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
    send_message(chat_id, welcome_message, reply_markup=json.dumps(inline_keyboard))
    logger.info(f"Sent /start to user {user_id}")

# ── Handle /help ────────────────────────────────────────────────────────────────
def handle_help_command(chat_id, user_id):
    help_text = """
Hey… I’m Sakura 🌸  
I’m here as your caring partner and gentle support  
Just send me anything on your mind—your thoughts your day your feelings  
I’ll respond softly with one-line messages no punctuation and always with one little emoji  

Here’s what I can do for you:  
• <b>/start</b> – A warm welcome and gentle hello  
• <b>/help</b> – Show this message anytime you need it  

I speak softly in Romanized Hindi by default  
But I’ll reply in English or Bangla if that’s how you talk to me  

You can count on me for comfort encouragement or just quiet company 🤎  
"""
    send_message(chat_id, help_text)
    logger.info(f"Sent /help to user {user_id}")

# ── Handle a normal text message (injecting the user's first name) ─────────────
def handle_text_message(chat_id, user_id, first_name, text, reply_to_message_id=None):
    try:
        # Show “typing…” indicator before generating reply
        send_chat_action(chat_id, action="typing")

        # If this is the first time this user chats, create a new Gemini chat for them
        if user_id not in user_chats:
            user_chats[user_id] = model.start_chat(history=[])

        chat = user_chats[user_id]

        # ── 1) Normalize the user’s incoming text ────────────────────────────
        normalized = text.lower().strip()

        # ── 2) Check for simple greetings ──────────────────────────────────
        greeting_keywords = {"hi", "hello", "hey", "namaste", "konichiwa"}
        is_greeting = normalized in greeting_keywords

        # ── 3) Check for “emotional” keywords ──────────────────────────────
        # Add or remove words as you like—these are examples of strong emotions.
        emotional_keywords = {
            "sad", "lonely", "anxiety", "anxious", "depressed", 
            "heartbroken", "upset", "failed", "tired", "hurt"
        }
        # Split on whitespace and see if any emotional word appears
        contains_emotion = any(word in normalized.split() for word in emotional_keywords)

        # ── 4) Build name_instruction only when greeting OR emotional ─────
        if is_greeting or contains_emotion:
            name_instruction = (
                f"# The user’s first name is “{first_name}”.\n"
                f"# When you reply, address them by {first_name} sometime in your flirty, "
                f"sugary-romantic style.\n"
            )
        else:
            name_instruction = ""  # no forced name usage here

        # ── 5) Assemble the final prompt to send to Gemini ─────────────────
        enhanced_prompt = (
            f"{SAKURA_PROMPT}\n\n"
            f"{name_instruction}"
            f"User: {text}\n\n"
            f"Respond as Sakura Haruno:"
        )

        # ── 6) Send to Gemini and get Sakura’s reply ───────────────────────
        response = chat.send_message(enhanced_prompt)
        reply = response.text

        # Trim if it’s excessively long
        if len(reply) > 4000:
            reply = reply[:3900] + "... (message too long, sorry!) 🙃"

        # ── 7) Send Sakura’s reply back to Telegram ────────────────────────
        send_message(chat_id, reply, reply_to_message_id=reply_to_message_id)
        logger.info(f"Sakura → [{first_name}]: {reply[:30]}…")

    except Exception as e:
        logger.error(f"Error in handle_text_message: {e}")
        error_msg = random.choice(ERROR_MESSAGES)
        send_message(chat_id, error_msg)

# ── Process each update from getUpdates ─────────────────────────────────────────
def process_update(update):
    try:
        if "message" not in update:
            return

        message    = update["message"]
        chat       = message["chat"]
        chat_id    = chat["id"]
        chat_type  = chat.get("type", "")
        user_id    = message["from"]["id"]
        first_name = message["from"].get("first_name", "").strip()
        text       = message.get("text", "").strip()
        reply_to   = message.get("reply_to_message")  # None if not a reply

        # ── 1) Always allow /start and /help ─────────────────────────────────
        if text.startswith("/start"):
            handle_start_command(chat_id, user_id)
            return
        elif text.startswith("/help"):
            handle_help_command(chat_id, user_id)
            return

        # ── 2) If this is a private chat, respond to every text ───────────────
        if chat_type == "private":
            logger.info(f"Private message from {first_name} ({user_id}): “{text}” → responding")
            handle_text_message(chat_id, user_id, first_name, text)
            return

        # ── 2.5) If someone REPLIES to Sakura’s message with a STICKER ─────────
        if reply_to:
            from_field = reply_to.get("from", {})
            # Replace "sluttysakurabot" with your actual bot username (no “@”)
            if from_field.get("username", "").lower() == "sluttysakurabot":
                # Check if incoming message contains a sticker
                if "sticker" in message:
                    logger.info(f"Detected user replied with a sticker to Sakura's message (chat: {chat_id}).")
                    # Sakura chooses and sends a random sticker back
                    send_random_sakura_sticker(
                        chat_id,
                        reply_to_message_id=message["message_id"]
                    )
                    return

        # ── 3) In group chats, detect if it’s a reply TO Sakura’s text message ───
        is_reply_to_bot = False
        if reply_to:
            from_field = reply_to.get("from", {})
            if from_field.get("username", "").lower() == "sluttysakurabot":
                is_reply_to_bot = True

        if is_reply_to_bot:
            logger.info(
                f"Detected reply to Sakura in group {chat_id} by {first_name} ({user_id}): “{text}”"
            )
            handle_text_message(
                chat_id,
                user_id,
                first_name,
                text,
                reply_to_message_id=message["message_id"]
            )
            return

        # ── 4) In group chats, if someone types “Sakura”, respond ─────────────
        if "sakura" in text.lower():
            logger.info(
                f"Detected keyword “Sakura” in group {chat_id} by {first_name} ({user_id}): “{text}”"
            )
            handle_text_message(
                chat_id,
                user_id,
                first_name,
                text,
                reply_to_message_id=message["message_id"]
            )
            return

        # ── 5) Otherwise, do nothing ──────────────────────────────────────────
        return

    except Exception as e:
        logger.error(f"Error processing update: {e}")
        
 # ─── Dummy HTTP Server to Keep Render Happy ─────────────────────────────────
class DummyHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"AFK bot is alive!")

    def do_HEAD(self):
        self.send_response(200)
        self.end_headers()

def start_dummy_server():
    port = int(os.environ.get("PORT", 10000))  # Render injects this
    server = HTTPServer(("0.0.0.0", port), DummyHandler)
    print(f"Dummy server listening on port {port}")
    server.serve_forever()

# ── Main loop: poll getUpdates, then process each update ──────────────────────
async def main():
    global last_update_id

    logger.info("🌸 Sakura Bot is starting up! 🌸")
    logger.info("Make sure Privacy Mode is OFF so I see all messages in groups.")
    set_my_commands()

    while True:
        try:
            result = get_updates()
            if result and result.get("ok"):
                updates = result.get("result", [])
                for update in updates:
                    last_update_id = update["update_id"]
                    process_update(update)

            await asyncio.sleep(1)

        except KeyboardInterrupt:
            logger.info("Bot stopped by user")
            break
        except Exception as e:
            logger.error(f"Error in main loop: {e}")
            await asyncio.sleep(5)

if __name__ == "__main__":
    
# Start dummy HTTP server (needed for Render health check)
    threading.Thread(target=start_dummy_server, daemon=True).start()

    asyncio.run(main())