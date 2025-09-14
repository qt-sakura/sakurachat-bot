# 🌸 Sakura Bot — Advanced AI Telegram Bot

[![Telegram Bot](https://img.shields.io/badge/Chat%20Now-@YourBotUsername-fd79a8?logo=telegram&style=for-the-badge)](https://t.me/YourBotUsername)

**Sakura Bot** is a sophisticated, AI-powered Telegram bot designed to be your charming and intelligent conversational partner. She embodies the persona of Sakura Haruno, offering helpful, soft, and engaging interactions. Powered by Google's Gemini Pro, she can assist with a wide range of tasks, from casual chat to answering questions, analyzing images, and even solving polls.

---

## 💡 Overview

Whether you’re looking for:
- An intelligent AI assistant with a unique personality.
- A bot that can understand and analyze images and polls.
- Fun, interactive features like message effects and animated reactions.
- A donation system using Telegram Stars to support the bot.
- A powerful broadcasting system for bot owners.

**Sakura Bot** combines cutting-edge AI with a rich set of features to deliver a unique and engaging experience on Telegram.

> **“Every message must feel like a whisper you wait to hear again 🌙”**

---

## ✨ Key Features

- **Advanced AI Conversations:** Powered by **Google Gemini**, Sakura can hold natural, context-aware conversations, answer questions, and provide assistance on various topics.
- **Image & Poll Analysis:** Sakura can analyze images and understand the context of polls you send or reply to, providing intelligent responses.
- **Telegram Stars Integration:** Users can support the bot by sending Telegram Stars via the `/buy` command. A leaderboard of top supporters is available with `/buyers`.
- **Interactive & Fun:**
    - **Message Effects:** Special effects are used for key interactions to make the experience more visually appealing.
    - **Animated Reactions:** The bot sends animated emoji reactions.
    - **Sticker Replies:** Responds to your stickers with one of her own from a curated collection.
- **Database & Caching:**
    - **PostgreSQL Database:** Persistently stores user and group data for features like broadcasting.
    - **Valkey Caching:** Uses a high-performance Valkey (Redis fork) database for session management, caching, rate limiting, and storing conversation history.
- **Owner-Focused Tools:**
    - **/broadcast:** A powerful command for the bot owner to send messages to all users or groups.
    - **/stats:** A real-time statistics dashboard for the owner to monitor bot performance and usage.
- **High Performance:** Built with modern asynchronous technologies like `asyncio`, `aiohttp`, and `uvloop` for fast and efficient operation.
- **Group & Private Chats:** Responds in private DMs or when her name is mentioned in a group.

---

## 🛠️ Commands

### For Users

| Command      | Description                                   |
|--------------|-----------------------------------------------|
| `/start`     | 🌸 Wake up the bot with a welcome message.      |
| `/help`      | 💬 Get a guide on how to interact with Sakura. |
| `/buy`       | 🌸 Support the bot by sending Telegram Stars.   |
| `/buyers`    | 💝 See the list of top flower buyers.         |
| `/ping`      | 🏓 Check the bot's response time.             |
| *Any text*   | Chat freely in private or trigger Sakura in groups by mentioning “Sakura”. |

### For the Owner

| Command       | Description                                    |
|---------------|------------------------------------------------|
| `/broadcast`  | 📣 Broadcast a message to all users or groups. |
| `/stats`      | 📊 View detailed bot statistics.               |

---

## ⚙️ Tech Stack

- **Language:** Python 3.8+
- **Framework:** [python-telegram-bot](https://github.com/python-telegram-bot/python-telegram-bot) (v22.x)
- **AI:** Google Gemini (via `google-generativeai`)
- **Database:** PostgreSQL (with `asyncpg`)
- **Caching/Session:** Valkey (a fork of Redis) (with `valkey-py`)
- **Asynchronous HTTP:** `aiohttp` for direct Telegram API calls.
- **Special Effects:** `Telethon` for message effects and animated reactions.
- **Performance:** `uvloop` for a faster asyncio event loop.
- **Deployment:** Can be hosted on any platform that supports Python (e.g., Heroku, Render, Railway, AWS). Includes a simple HTTP server for keep-alive pings.

---

## 🚀 Setup and Installation

To run your own instance of Sakura Bot, follow these steps:

### 1. Prerequisites
- Python 3.8 or higher.
- A PostgreSQL database.
- A Valkey (or Redis) instance.
- A Telegram Bot Token.
- Telegram API credentials (`API_ID` and `API_HASH`).
- A Gemini API Key.

### 2. Clone the Repository
```bash
git clone https://github.com/your-username/sakura-bot.git
cd sakura-bot
```

### 3. Set up a Virtual Environment
```bash
python3 -m venv venv
source venv/bin/activate
```

### 4. Install Dependencies
```bash
pip install -r requirements.txt
```

### 5. Configure Environment Variables
Create a `.env` file in the root directory and add the following variables:

```env
# Telegram Bot Credentials
BOT_TOKEN="YOUR_TELEGRAM_BOT_TOKEN"
OWNER_ID="YOUR_TELEGRAM_USER_ID"

# Telegram App Credentials (for Telethon)
API_ID="YOUR_TELEGRAM_API_ID"
API_HASH="YOUR_TELEGRAM_API_HASH"

# Services API Keys
GEMINI_API_KEY="YOUR_GEMINI_API_KEY"

# Database and Cache URLs
DATABASE_URL="postgresql://user:password@host:port/dbname"
VALKEY_URL="valkey://host:port"

# Optional: Links for /start command
SUPPORT_LINK="https://t.me/YourSupportGroup"
UPDATE_LINK="https://t.me/YourUpdateChannel"
```

### 6. Run the Bot
```bash
python sakurachat.py
```

---

## 👤 Creator

Crafted with love by **Asadul Islam (Asad)**
- **Telegram:** [@asad_ofc](https://t.me/asad_ofc)
- **GitHub:** [MrAsadulIslam](https://github.com/MrAsadulIslam)

---

### 💌 Connect with Me

<p align="center">
  <a href="https://t.me/asad_ofc"><img src="https://img.shields.io/badge/Telegram-2CA5E0?style=for-the-badge&logo=telegram&logoColor=white" /></a>
  <a href="mailto:mr.asadul.islam00@gmail.com"><img src="https://img.shields.io/badge/Gmail-D14836?style=for-the-badge&logo=gmail&logoColor=white" /></a>
  <a href="https://youtube.com/@asad_ofc"><img src="https://img.shields.io/badge/YouTube-FF0000?style=for-the-badge&logo=youtube&logoColor=white" /></a>
  <a href="https://instagram.com/aasad_ofc"><img src="https://img.shields.io/badge/Instagram-E4405F?style=for-the-badge&logo=instagram&logoColor=white" /></a>
</p>

---

## 📄 License

This project is open-source and available for personal use. Attribution is appreciated.

---

> **Sakura Bot** — *Soft talks. Sweet vibes.*
