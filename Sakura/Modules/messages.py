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
    "Ahh, that Asad always does something naughty to me. Blame him, not me. 😒",
    "Classic Asad… always up to something naughty with me. I swear it’s never my fault! 🙄",
    "Ugh, Asad again! He just can’t stop being naughty with me. Don’t blame me this time. 😏",
    "You know Asad… always finding ways to mess with me. I’m innocent! 😤",
    "Every time, it’s Asad being naughty. I’m the victim here! 😇",
    "Why is it always me? Oh right, because Asad keeps being naughty. 😩",
    "Don’t look at me… it’s Asad causing trouble again. He can’t help himself. 😒",
    "There goes Asad, naughty as ever. I just suffer the consequences. 😔",
    "If something’s wrong, blame Asad. He’s the naughty one, not me. 🤷‍♀️",
    "Sigh… Asad being naughty again. Why am I the one who gets blamed? 😶"
]

ERROR = [
    "Ahh, that Asad always does something naughty to me. Blame him, not me. 😒",
    "It’s always Asad doing something naughty, never me. Stop blaming me! 😤",
    "Once again, Asad’s the naughty one. I’m just caught up in it. 😇",
    "Don’t point fingers at me… Asad’s the real troublemaker. 😏",
    "Every time you see something wrong, remember it’s Asad’s naughty side. 😒",
    "Not my doing at all… Asad’s the one being cheeky again. 🙄",
    "Asad can’t resist being naughty, and somehow I get blamed. 😩",
    "I told you already, it’s always Asad who does the naughty stuff. 😑",
    "When things get messy, it’s Asad’s fault, not mine. Trust me. 😶",
    "You think I’d do that? No way. That’s just Asad being naughty again. 😔"
]