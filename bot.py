# bot.py

import asyncio
import datetime
import sqlite3
import requests
from config import (
    API_HASH,
    API_ID,
    BOT_TOKEN,
    BOT_USERNAME,
    DB_NAME,
    DEV_ADMIN_USERNAME,
    MAIN_CHANNEL,
    SHORTENER_API,
    SHORTENER_URL,
    START_PHOTO,
)
from database import add_user, deduct_point, get_points, init_db
from pyrogram import Client, filters
from pyrogram.types import (
    CallbackQuery,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    Message,
)

app = Client("MovieStoreBot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

# Temporary In-Memory Verified Users
VERIFIED_USERS = {}


# Helper: Shortener Function
def get_short_url(long_url):
    try:
        response = requests.get(
            f"{SHORTENER_URL}?api={SHORTENER_API}&url={long_url}"
        )
        data = response.json()
        return data.get("shorturl", long_url)
    except Exception:
        return long_url


# Start Welcome Message Text
START_TEXT = """
👋 **Hello {first_name}!**

🤖 **Welcome to Movie Store Bot!**

🎬 **Main Features:**
• 🚀 High-Speed Direct Movie Downloads
• 🎁 **Refer & Earn:** Per refer = 1 Free Movie Download
• 📺 Multiple Qualities (480p, 720p, 1080p, 4K) in 1 Click!

💎 **Your Free Credits:** `{points} Points`

👇 *Select any option below:*
"""


@app.on_message(filters.command("start"))
async def start_cmd(client: Client, message: Message):
    user_id = message.from_user.id
    first_name = message.from_user.first_name
    text_args = message.text.split()

    # 1. Check Referrals on Start
    referrer = None
    if len(text_args) > 1 and text_args[1].startswith("ref_"):
        try:
            referrer = int(text_args[1].replace("ref_", ""))
        except ValueError:
            pass

    add_user(user_id, referrer)

    # 2. Shortener Verification Link Complete Handler
    if len(text_args) > 1 and text_args[1].startswith("verify_"):
        VERIFIED_USERS[user_id] = datetime.datetime.now() + datetime.timedelta(
            hours=24
        )
        await message.reply_text(
            f"🎉 **Congratulations {first_name}!**\n\nShortener verification successful! Aapko 24 Hours ka free access mil gaya hai."
        )
        return

    # 3. Get Movie Batch Handler (When user clicks on channel post)
    if len(text_args) > 1 and (
        text_args[1].startswith("get_") or text_args[1].startswith("refget_")
    ):
        param = text_args[1]
        movie_id = param.split("_")[1]

        # Check if requested via Referral Point
        if param.startswith("refget_"):
            points = get_points(user_id)
            if points < 1:
                await message.reply_text(
                    "❌ **Insufficient Refer Points!**\n\nAapke paas 0 Points hain. Dosto ko refer karke points earn karein ya Shortener Complete karein."
                )
                return
            deduct_point(user_id)  # Deduct 1 Refer Point

        # Fetch All Files for this Movie ID and send in 1 Click
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        cursor.execute(
            "SELECT file_id FROM movie_batches WHERE movie_id = ?", (movie_id,)
        )
        files = cursor.fetchall()
        conn.close()

        if files:
            await message.reply_text(
                f"📦 **Sending All Available Qualities ({len(files)} Files)...**"
            )
            for file_item in files:
                await message.reply_document(file_item[0])
                await asyncio.sleep(1)  # Prevent Flood Wait
            return
        else:
            await message.reply_text("⚠️ No files found for this movie.")
            return

    # Generate Shortener Verify Link & Referral Link
    verify_link = f"https://t.me/{BOT_USERNAME}?start=verify_{user_id}"
    short_verify_link = get_short_url(verify_link)
    referral_link = f"https://t.me/{BOT_USERNAME}?start=ref_{user_id}"

    user_points = get_points(user_id)

    # Inline Keyboards
    buttons = InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton(
                    "🔓 Free Access (Verify Shortener)", url=short_verify_link
                )
            ],
            [
                InlineKeyboardButton(
                    "🎁 Refer & Earn (Free File)", callback_data="refer_info"
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

    await message.reply_photo(
        photo=START_PHOTO,
        caption=START_TEXT.format(
            first_name=first_name, points=user_points
        ),
        reply_markup=buttons,
    )


# Callback Handler (Refer Link Popup & Help)
@app.on_callback_query()
async def callback_handler(client: Client, query: CallbackQuery):
    user_id = query.from_user.id

    if query.data == "refer_info":
        user_points = get_points(user_id)
        referral_link = f"https://t.me/{BOT_USERNAME}?start=ref_{user_id}"

        refer_text = f"""
🎁 **Refer & Earn Program**

👉 **Aapka Referral Link:**
`{referral_link}`

💰 **Current Points:** `{user_points} Points`

✨ **Rules:**
• Har 1 Member ko join karwane par aapko **1 Point** milega.
• **1 Point = 1 Complete Movie Bundle** (Sabhi 4-7 Files ek sath).
• Apne link ko friends ke saath share karein aur free me access karein!
"""
        back_btn = InlineKeyboardMarkup(
            [[InlineKeyboardButton("🔙 Back", callback_data="back_home")]]
        )
        await query.message.edit_caption(caption=refer_text, reply_markup=back_btn)

    elif query.data == "back_home":
        first_name = query.from_user.first_name
        user_points = get_points(user_id)

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
                        "🎁 Refer & Earn (Free File)",
                        callback_data="refer_info",
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
            caption=START_TEXT.format(
                first_name=first_name, points=user_points
            ),
            reply_markup=home_buttons,
        )


# Bot Initialization
if __name__ == "__main__":
    init_db()
    print("Bot is running with Referral & Batch Files System...")
    app.run()
    
