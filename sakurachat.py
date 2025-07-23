import asyncio
import logging
import os
import random
import time
from collections import defaultdict, deque
from typing import List, Optional

from telegram import (
    Update, 
    InlineKeyboardButton, 
    InlineKeyboardMarkup,
    InputMediaPhoto
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
from google.genai import types

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

# Initialize Gemini client
try:
    gemini_client = genai.Client(api_key=GEMINI_API_KEY)
except Exception as e:
    logger.error(f"Failed to initialize Gemini client: {e}")
    gemini_client = None

# Sakura character prompt
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

class SakuraBot:
    """Main Sakura Bot class"""
    
    def __init__(self):
        self.application = None
        self.help_expanded = {}  # Track help expansion state per user
        self.user_ids = set()  # Track user IDs for broadcasting
        self.group_ids = set()  # Track group IDs for broadcasting
        self.broadcast_mode = {}  # Track broadcast mode per user: {user_id: "users" or "groups"}
        self.broadcast_pending = {}  # Track pending broadcast messages
        
        # Rate limiting system
        self.user_last_response_time = {}  # Track last response time per user
        self.RATE_LIMIT_SECONDS = 1  # Minimum seconds between responses per user
    
    def is_rate_limited(self, user_id: int) -> bool:
        """Check if user is rate limited (silently)"""
        current_time = time.time()
        last_response = self.user_last_response_time.get(user_id, 0)
        
        # Check if enough time has passed since last response
        if current_time - last_response < self.RATE_LIMIT_SECONDS:
            return True  # Rate limited - ignore this message
        
        return False
    
    def update_user_response_time(self, user_id: int):
        """Update the last response time for user"""
        self.user_last_response_time[user_id] = time.time()
    
    async def get_gemini_response(self, user_message: str, user_name: str = "") -> str:
        """Get response from Gemini API"""
        if not gemini_client:
            return "Kuch gadbad hai, main samaj nahi pa rahi 😕"
        
        try:
            # Prepare the prompt with user context
            prompt = f"{SAKURA_PROMPT}\n\nUser name: {user_name}\nUser message: {user_message}\n\nSakura's response:"
            
            response = gemini_client.models.generate_content(
                model="gemini-2.5-flash",
                contents=prompt
            )
            
            if response.text:
                return response.text.strip()
            else:
                return "Kuch kehna chaah rahi hu par words nahi mil rahe 🥺"
                
        except Exception as e:
            logger.error(f"Gemini API error: {e}")
            return "Thoda sa confusion ho gaya, dobara try karo 😔"
    
    async def start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /start command"""
        try:
            # Track user and group IDs for broadcasting
            user_id = update.effective_user.id
            self.user_ids.add(user_id)
            
            # Track group IDs if command is used in a group
            if update.effective_chat.type in ['group', 'supergroup']:
                self.group_ids.add(update.effective_chat.id)
            
            # Send upload_photo chat action
            await context.bot.send_chat_action(
                chat_id=update.effective_chat.id, 
                action=ChatAction.UPLOAD_PHOTO
            )
            
            # Random image selection
            random_image = random.choice(SAKURA_IMAGES)
            
            # Create inline keyboard
            keyboard = [
                [
                    InlineKeyboardButton("📢 Updates", url="https://t.me/sakura_updates"),
                    InlineKeyboardButton("💬 Support", url="https://t.me/sakura_support")
                ],
                [
                    InlineKeyboardButton("➕ Add Bot to Group", url=f"https://t.me/{context.bot.username}?startgroup=true")
                ]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            # Caption for start message
            caption = (
                "✨ <b>Hi! Main Sakura Haruno hu</b> ✨\n\n"
                "🌸 Tumhari helpful friend jo hamesha tumhare saath hai\n"
                "💭 Kuch bhi pooch sakte ho, main help karungi\n"
                "🫶 Simple baatein, soft replies, aur lots of love\n\n"
                "<i>Kya baat karni hai aaj? 💗</i>"
            )
            
            await context.bot.send_photo(
                chat_id=update.effective_chat.id,
                photo=random_image,
                caption=caption,
                parse_mode=ParseMode.HTML,
                reply_markup=reply_markup
            )
            
        except Exception as e:
            logger.error(f"Error in start command: {e}")
            await update.message.reply_text("Kuch gadbad hui, dobara try karo 😕")
    
    async def help_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /help command"""
        user_id = update.effective_user.id
        
        # Create inline keyboard for expand/minimize
        keyboard = [
            [InlineKeyboardButton("📖 Expand Guide", callback_data=f"help_expand_{user_id}")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        help_text = (
            "🌸 <b>Sakura Bot Guide</b> 🌸\n\n"
            "✨ Main tumhari helpful friend hu\n"
            "💭 Kuch bhi pooch sakte ho\n"
            "🫶 Simple Hindi mein baat karte hai\n\n"
            "<i>Guide ko expand karne ke liye button dabao</i> ⬇️"
        )
        
        await update.message.reply_text(
            help_text,
            parse_mode=ParseMode.HTML,
            reply_markup=reply_markup
        )
    
    async def help_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle help expand/minimize callbacks"""
        query = update.callback_query
        await query.answer()
        
        callback_data = query.data
        user_id = int(callback_data.split('_')[2])
        
        # Check if user is authorized to use this button
        if update.effective_user.id != user_id:
            await query.answer("Ye button tumhare liye nahi hai 😊", show_alert=True)
            return
        
        is_expanded = self.help_expanded.get(user_id, False)
        
        if is_expanded:
            # Minimize
            keyboard = [
                [InlineKeyboardButton("📖 Expand Guide", callback_data=f"help_expand_{user_id}")]
            ]
            help_text = (
                "🌸 <b>Sakura Bot Guide</b> 🌸\n\n"
                "✨ Main tumhari helpful friend hu\n"
                "💭 Kuch bhi pooch sakte ho\n"
                "🫶 Simple Hindi mein baat karte hai\n\n"
                "<i>Guide ko expand karne ke liye button dabao</i> ⬇️"
            )
            self.help_expanded[user_id] = False
        else:
            # Expand
            keyboard = [
                [InlineKeyboardButton("📚 Minimize Guide", callback_data=f"help_expand_{user_id}")]
            ]
            help_text = (
                "🌸 <b>Sakura Bot Complete Guide</b> 🌸\n\n"
                "🗣️ <b>How to talk:</b>\n"
                "• Hindi, English, Bangla - jo bhi comfortable ho\n"
                "• Simple questions poochiye\n"
                "• Main short aur sweet reply deti hu\n\n"
                "💭 <b>What I can help with:</b>\n"
                "• Study aur homework help\n"
                "• Relationship advice\n"
                "• Emotional support\n"
                "• Math aur calculations\n"
                "• General questions\n"
                "• Friendly chat\n\n"
                "🎭 <b>Sticker fun:</b>\n"
                "• Agar tum sticker bhejoge, main bhi bhejungi\n"
                "• Group mein reply karne par sticker milega\n\n"
                "❤️ <b>My personality:</b>\n"
                "• Helpful aur caring\n"
                "• Short messages with emojis\n"
                "• Always here for you\n\n"
                "<i>Ab baat karte hai! 🫶</i>"
            )
            self.help_expanded[user_id] = True
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        try:
            await query.edit_message_text(
                help_text,
                parse_mode=ParseMode.HTML,
                reply_markup=reply_markup
            )
        except Exception as e:
            logger.error(f"Error editing help message: {e}")
    
    async def handle_sticker(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle sticker messages"""
        try:
            user_id = update.effective_user.id
            chat_type = update.effective_chat.type
            
            # Check rate limiting (silently ignore if rate limited)
            if self.is_rate_limited(user_id):
                return
            
            # In private chats, always respond with sticker
            # In groups, only respond if replying to bot's message
            should_respond = False
            
            if chat_type == "private":
                should_respond = True
            elif update.message.reply_to_message and update.message.reply_to_message.from_user.id == context.bot.id:
                should_respond = True
            
            if should_respond:
                # Show choosing sticker action dynamically
                await context.bot.send_chat_action(
                    chat_id=update.effective_chat.id, 
                    action=ChatAction.CHOOSE_STICKER
                )
                
                # Select random Sakura sticker
                random_sticker = random.choice(SAKURA_STICKERS)
                
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
                
                # Update response time AFTER sending sticker
                self.update_user_response_time(user_id)
                
        except Exception as e:
            logger.error(f"Error handling sticker: {e}")
    
    async def handle_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle text messages"""
        try:
            # Track user and group IDs for broadcasting
            user_id = update.effective_user.id
            self.user_ids.add(user_id)
            
            # Track group IDs if message is from a group
            if update.effective_chat.type in ['group', 'supergroup']:
                self.group_ids.add(update.effective_chat.id)
            
            # Check if owner is in broadcast mode (any message triggers broadcast)
            if user_id == OWNER_ID and OWNER_ID in self.broadcast_mode:
                # Execute broadcast with this message
                await self.execute_broadcast_direct(update, context, self.broadcast_mode[OWNER_ID])
                # Clear broadcast mode
                del self.broadcast_mode[OWNER_ID]
                return
            
            # Group message filtering: only respond if mentioned or replied to
            chat_type = update.effective_chat.type
            should_respond = False
            
            if chat_type == "private":
                # Always respond in private chats
                should_respond = True
            elif chat_type in ['group', 'supergroup']:
                # In groups, only respond if:
                # 1. Message contains "sakura" (case insensitive)
                # 2. Message is a reply to bot's message
                user_message = update.message.text or ""
                
                if "sakura" in user_message.lower():
                    should_respond = True
                elif (update.message.reply_to_message and 
                      update.message.reply_to_message.from_user.id == context.bot.id):
                    should_respond = True
            
            if not should_respond:
                return
            
            # Check rate limiting (silently ignore if rate limited)
            if self.is_rate_limited(user_id):
                return
            
            # Show typing action dynamically while processing
            await context.bot.send_chat_action(
                chat_id=update.effective_chat.id, 
                action=ChatAction.TYPING
            )
            
            user_message = update.message.text or ""
            user_name = update.effective_user.first_name or ""
            
            # Get response from Gemini
            response = await self.get_gemini_response(user_message, user_name)
            
            # Send response
            await update.message.reply_text(response)
            
            # Update response time AFTER sending response
            self.update_user_response_time(user_id)
            
        except Exception as e:
            logger.error(f"Error handling message: {e}")
            await update.message.reply_text("Kuch gadbad hui, dobara try karo 😕")
    
    async def broadcast_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle broadcast command (owner only)"""
        if update.effective_user.id != OWNER_ID:
            await update.message.reply_text("❌ Only owner can use broadcast")
            return
        
        logger.info(f"📢 Broadcast command by owner")
        
        # Create inline keyboard for target selection
        keyboard = InlineKeyboardMarkup([
            [
                InlineKeyboardButton(f"👥 Users ({len(self.user_ids)})", callback_data="bc_users"),
                InlineKeyboardButton(f"📢 Groups ({len(self.group_ids)})", callback_data="bc_groups")
            ]
        ])
        
        await update.message.reply_text(
            "📣 <b>Select Broadcast Target:</b>\n\n"
            f"👥 <b>Users:</b> {len(self.user_ids)} individual chats\n"
            f"📢 <b>Groups:</b> {len(self.group_ids)} group chats\n\n"
            "After selecting, send your broadcast message:",
            reply_markup=keyboard,
            parse_mode=ParseMode.HTML
        )
    
    async def broadcast_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle broadcast target selection"""
        query = update.callback_query
        await query.answer()
        
        if query.from_user.id != OWNER_ID:
            return
        
        if query.data == "bc_users":
            self.broadcast_mode[OWNER_ID] = "users"
            await query.edit_message_text(
                f"✅ <b>Ready to broadcast to {len(self.user_ids)} users</b>\n\n"
                "Send your message now (text, photo, sticker, etc.)\n"
                "It will be automatically broadcasted to all users.",
                parse_mode=ParseMode.HTML
            )
        elif query.data == "bc_groups":
            self.broadcast_mode[OWNER_ID] = "groups"
            await query.edit_message_text(
                f"✅ <b>Ready to broadcast to {len(self.group_ids)} groups</b>\n\n"
                "Send your message now (text, photo, sticker, etc.)\n"
                "It will be automatically broadcasted to all groups.",
                parse_mode=ParseMode.HTML
            )
    
    async def execute_broadcast_direct(self, update: Update, context: ContextTypes.DEFAULT_TYPE, target_type: str):
        """Execute broadcast with the current message"""
        try:
            if target_type == "users":
                target_list = [uid for uid in self.user_ids if uid != OWNER_ID]
                target_name = "users"
            elif target_type == "groups":
                target_list = list(self.group_ids)
                target_name = "groups"
            else:
                return
            
            if not target_list:
                await update.message.reply_text(f"❌ No {target_name} found")
                return
            
            # Show initial status
            status_msg = await update.message.reply_text(
                f"📡 Broadcasting to {len(target_list)} {target_name}..."
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
                    await asyncio.sleep(0.03)
                    
                except Exception as e:
                    failed_count += 1
                    logger.error(f"Failed to broadcast to {target_id}: {e}")
            
            # Final status update
            await status_msg.edit_text(
                f"✅ <b>Broadcast Completed!</b>\n\n"
                f"📊 Sent to: {broadcast_count}/{len(target_list)} {target_name}\n"
                f"❌ Failed: {failed_count}",
                parse_mode=ParseMode.HTML
            )
            
        except Exception as e:
            logger.error(f"Broadcast error: {e}")
            await update.message.reply_text(f"❌ Broadcast failed: {str(e)}")
    
    async def ping_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle ping command (owner only) with real-time response"""
        if update.effective_user.id != OWNER_ID:
            await update.message.reply_text("❌ Only owner can use this command")
            return
        
        import time
        start_time = time.time()
        
        # Send initial message
        msg = await update.message.reply_text("🏓 Pinging...")
        
        # Calculate response time
        response_time = round((time.time() - start_time) * 1000, 2)  # milliseconds
        
        # Edit message with just response time
        await msg.edit_text(f"🏓 Pong! Response time: {response_time}ms")
    
    async def error_handler(self, update: object, context: ContextTypes.DEFAULT_TYPE):
        """Handle errors"""
        logger.error(f"Exception while handling an update: {context.error}")
    
    def setup_handlers(self):
        """Setup all command and message handlers"""
        # Command handlers
        self.application.add_handler(CommandHandler("start", self.start_command))
        self.application.add_handler(CommandHandler("help", self.help_command))
        self.application.add_handler(CommandHandler("broadcast", self.broadcast_command))
        self.application.add_handler(CommandHandler("ping", self.ping_command))
        
        # Callback query handlers
        self.application.add_handler(CallbackQueryHandler(self.help_callback, pattern="^help_expand_"))
        self.application.add_handler(CallbackQueryHandler(self.broadcast_callback, pattern="^bc_"))
        
        # Message handlers
        self.application.add_handler(MessageHandler(filters.Sticker.ALL, self.handle_sticker))
        self.application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_message))
        
        # Error handler
        self.application.add_error_handler(self.error_handler)
    
    def run(self):
        """Run the bot"""
        if not BOT_TOKEN:
            logger.error("BOT_TOKEN not found in environment variables")
            return
        
        if not GEMINI_API_KEY:
            logger.error("GEMINI_API_KEY not found in environment variables")
            return
        
        if not OWNER_ID:
            logger.error("OWNER_ID not found in environment variables")
            return
        
        # Create application
        self.application = Application.builder().token(BOT_TOKEN).build()
        
        # Setup handlers
        self.setup_handlers()
        
        logger.info("🌸 Sakura Bot is starting...")
        
        # Run the bot
        self.application.run_polling(allowed_updates=Update.ALL_TYPES, drop_pending_updates=True)

def main():
    """Main function"""
    bot = SakuraBot()
    
    try:
        bot.run()
    except KeyboardInterrupt:
        logger.info("Bot stopped by user")
    except Exception as e:
        logger.error(f"Fatal error: {e}")

if __name__ == "__main__":
    main()