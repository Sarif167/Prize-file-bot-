# bot.py

import datetime
import requests
from config import (
    API_HASH,
    API_ID,
    BOT_TOKEN,
    BOT_USERNAME,
    DEV_ADMIN_USERNAME,
    MAIN_CHANNEL,
    SHORTENER_API,
    SHORTENER_URL,
    START_PHOTO,
)
from pyrogram import Client, filters
from pyrogram.types import (
    CallbackQuery,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    Message,
)

app = Client("MovieStoreBot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

# Verified Users Cache (In-Memory)
VERIFIED_USERS = {}  # {user_id: expiry_datetime}


# Shortener Function
def get_short_url(long_url):
    try:
        response = requests.get(
            f"{SHORTENER_URL}?api={SHORTENER_API}&url={long_url}"
        )
        data = response.json()
        return data.get("shorturl", long_url)
    except Exception:
        return long_url


# Start Message Text
START_TEXT = """
👋 **Hello {first_name}!**

🤖 **Welcome to the Ultimate Movie Store Bot!**

🎬 **Main Features:**
• 🚀 High-Speed Direct Movie Downloads
• 📺 HD Streaming Links (720p, 1080p, 4K)
• ⚡ Fast & Automated Delivery

🔓 **Free Access:** Shortener complete karke free me movie download karein.
🛒 **Paid Access:** Bina ad ke instant download ke liye ₹5 me buy karein.

👇 *Niche diye gaye buttons me se apna option select karein:*
"""

# Help Message Text
HELP_TEXT = """
❓ **How to use this Bot?**

1️⃣ **Free Access (Verify):**
   • 'Free Access' button par click karein.
   • Shortener link bypass karke verify complete karein.
   • Verification ke baad aapko 24 Hours ka free access mil jayega.

2️⃣ **Direct Buy:**
   • 'Buy Movie Direct' button par click karke direct UPI se payment karein aur fast delivery paein.

💬 Kisi bhi issue ke liye Admin/Developer se contact karein.
"""


# /start Handler
@app.on_message(filters.command("start"))
async def start_cmd(client: Client, message: Message):
    user_id = message.from_user.id
    first_name = message.from_user.first_name
    text_args = message.text.split()

    # 1. Verification Callback via Shortener
    if len(text_args) > 1 and text_args[1].startswith("verify_"):
        VERIFIED_USERS[user_id] = datetime.datetime.now() + datetime.timedelta(
            hours=24
        )
        await message.reply_text(
            f"🎉 **Congratulations {first_name}!**\n\nAapka verification successfully complete ho gaya hai! Aap agle 24 ghante tak bot ki files free access kar sakte hain."
        )
        return

    # Shortener Link Generator
    verify_link = f"https://t.me/{BOT_USERNAME}?start=verify_{user_id}"
    short_verify_link = get_short_url(verify_link)

    # Main Start Inline Keyboards
    buttons = InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton(
                    "🔓 Free Access (Verify Shortener)", url=short_verify_link
                )
            ],
            [
                InlineKeyboardButton(
                    "📢 Main Channel", url=MAIN_CHANNEL
                ),
                InlineKeyboardButton(
                    "👨‍💻 Developer / Admin",
                    url=f"https://t.me/{DEV_ADMIN_USERNAME}",
                ),
            ],
            [
                InlineKeyboardButton("❓ Help", callback_data="help_btn"),
            ],
        ]
    )

    # Photo ke saath Start Text send karna
    await message.reply_photo(
        photo=START_PHOTO,
        caption=START_TEXT.format(first_name=first_name),
        reply_markup=buttons,
    )


# Callback Query Handler (Help Button & Back)
@app.on_callback_query()
async def callback_handler(client: Client, query: CallbackQuery):
    if query.data == "help_btn":
        back_button = InlineKeyboardMarkup(
            [
                [
                    InlineKeyboardButton(
                        "👨‍💻 Contact Admin",
                        url=f"https://t.me/{DEV_ADMIN_USERNAME}",
                    )
                ],
                [InlineKeyboardButton("🔙 Back to Main", callback_data="back_home")],
            ]
        )
        await query.message.edit_caption(
            caption=HELP_TEXT, reply_markup=back_button
        )

    elif query.data == "back_home":
        first_name = query.from_user.first_name
        user_id = query.from_user.id

        verify_link = f"https://t.me/{BOT_USERNAME}?start=verify_{user_id}"
        short_verify_link = get_short_url(verify_link)

        home_buttons = InlineKeyboardMarkup(
            [
                [
                    InlineKeyboardButton(
                        "🔓 Free Access (Verify Shortener)",
                        url=short_verify_link,
                    )
                ],
                [
                    InlineKeyboardButton(
                        "📢 Main Channel", url=MAIN_CHANNEL
                    ),
                    InlineKeyboardButton(
                        "👨‍💻 Developer / Admin",
                        url=f"https://t.me/{DEV_ADMIN_USERNAME}",
                    ),
                ],
                [
                    InlineKeyboardButton("❓ Help", callback_data="help_btn"),
                ],
            ]
        )
        await query.message.edit_caption(
            caption=START_TEXT.format(first_name=first_name),
            reply_markup=home_buttons,
        )


# Bot Run Execution
if __name__ == "__main__":
    print("Bot is running successfully...")
    app.run()
  
