import asyncio
import datetime
import os
import sqlite3
from threading import Thread
from flask import Flask
import requests
from config import (
    API_HASH,
    API_ID,
    BOT_TOKEN,
    BOT_USERNAME,
    DB_NAME,
    DEV_ADMIN_USERNAME,
    HOW_TO_VERIFY_URL,
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

# ==========================================
# 1. FLASK DUMMY SERVER (Koyeb Health Check Fix)
# ==========================================
web_app = Flask("")


@web_app.route("/")
def home():
    return "Bot is Running Successfully!"


def run_flask():
    port = int(os.environ.get("PORT", 8080))
    web_app.run(host="0.0.0.0", port=port)


def keep_alive():
    t = Thread(target=run_flask)
    t.daemon = True
    t.start()


# ==========================================
# 2. PYROGRAM BOT CLIENT INITIALIZATION
# ==========================================
app = Client("MovieStoreBot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

# In-Memory Verified Users Cache {user_id: expiry_datetime}
VERIFIED_USERS = {}


# API Call to Shorten URL
def get_short_url(long_url):
    try:
        response = requests.get(
            f"{SHORTENER_URL}?api={SHORTENER_API}&url={long_url}"
        )
        data = response.json()
        return data.get("shorturl", long_url)
    except Exception:
        return long_url


# Start Message Banner Text Template
START_TEXT = """
👋 **Hello {first_name}!**

🤖 **Welcome to Movie Store Bot!**

🎬 **Main Features:**
• 🚀 High-Speed Direct Movie Downloads
• 🎁 **Refer & Earn:** Per refer = 1 Free Movie Access
• 📺 Multiple Qualities (480p, 720p, 1080p, 4K) in 1 Click!

💎 **Your Free Credits:** `{points} Points`

👇 *Niche diye gaye buttons se access karein:*
"""


# ==========================================
# 3. COMMAND HANDLER (/start)
# ==========================================
@app.on_message(filters.command("start"))
async def start_cmd(client: Client, message: Message):
    user_id = message.from_user.id
    first_name = message.from_user.first_name
    text_args = message.text.split()

    # A. Check Referral Link (/start ref_123456)
    referrer = None
    if len(text_args) > 1 and text_args[1].startswith("ref_"):
        try:
            referrer = int(text_args[1].replace("ref_", ""))
        except ValueError:
            pass

    # Database me User add karein / Referrer points update karein
    add_user(user_id, referrer)

    # B. Shortener Verification Link Complete Handler (/start verify_123456)
    if len(text_args) > 1 and text_args[1].startswith("verify_"):
        VERIFIED_USERS[user_id] = datetime.datetime.now() + datetime.timedelta(
            hours=24
        )
        await message.reply_text(
            f"🎉 **Congratulations {first_name}!**\n\nShortener verification successful! Aapko 24 Hours ka free access mil gaya hai."
        )
        return

    # C. Movie File Batch Delivery (/start get_MOVIEID ya /start refget_MOVIEID)
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
                    "❌ **Insufficient Points!**\n\nAapke paas 0 Points hain. Dosto ko refer karein ya Shortener Verify karein."
                )
                return
            deduct_point(user_id)  # 1 Point Deduct

        # Fetch All Files (4-7 Files) for this Movie ID
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
                await asyncio.sleep(1)  # FloodWait se bachne ke liye delay
            return
        else:
            await message.reply_text("⚠️ No files found for this movie.")
            return

    # Links Setup
    verify_link = f"https://t.me/{BOT_USERNAME}?start=verify_{user_id}"
    short_verify_link = get_short_url(verify_link)
    user_points = get_points(user_id)

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
                    "❓ How to Verify Free (Tutorial)", callback_data="how_to_verify"
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

    # Welcome Banner Send Karein
    await message.reply_photo(
        photo=START_PHOTO,
        caption=START_TEXT.format(
            first_name=first_name, points=user_points
        ),
        reply_markup=buttons,
    )


# ==========================================
# 4. CALLBACK QUERY HANDLER (BUTTON CLICKS)
# ==========================================
@app.on_callback_query()
async def callback_handler(client: Client, query: CallbackQuery):
    user_id = query.from_user.id

    # 1. How To Verify Guide Button
    if query.data == "how_to_verify":
        verify_guide_text = f"""
📖 **How to Verify Free (Step-by-Step Guide):**

1️⃣ **Step 1:** Niche diye gaye **'🔓 Free Access (Verify Shortener)'** button par click karein.
2️⃣ **Step 2:** Khule hue page par 10-15 seconds wait karein aur **'Continue'** par click karein.
3️⃣ **Step 3:** Captcha complete karein aur **'Get Link'** par click karein.
4️⃣ **Step 4:** Automatic aap bot me wapas aa jayenge aur aapko **24 Hours ka Free Access** mil jayega!

📺 **Video Tutorial Dekhne ke liye Niche Button par Click Karein:**
"""
        guide_buttons = InlineKeyboardMarkup(
            [
                [
                    InlineKeyboardButton(
                        "▶️ Watch Tutorial Video", url=HOW_TO_VERIFY_URL
                    )
                ],
                [InlineKeyboardButton("🔙 Back to Main", callback_data="back_home")],
            ]
        )
        await query.message.edit_caption(
            caption=verify_guide_text, reply_markup=guide_buttons
        )

    # 2. Refer & Earn Info Button
    elif query.data == "refer_info":
        user_points = get_points(user_id)
        referral_link = f"https://t.me/{BOT_USERNAME}?start=ref_{user_id}"

        refer_text = f"""
🎁 **Refer & Earn Program**

👉 **Aapka Referral Link:**
`{referral_link}`

💰 **Current Credits:** `{user_points} Points`

✨ **Rules:**
• Har 1 Friend ke join karne par **1 Point** milega.
• **1 Point = 1 Complete Movie Bundle** (Sabhi 4-7 Files ek sath).
• Direct link share karein aur free me movie access karein!
"""
        back_btn = InlineKeyboardMarkup(
            [[InlineKeyboardButton("🔙 Back to Main", callback_data="back_home")]]
        )
        await query.message.edit_caption(caption=refer_text, reply_markup=back_btn)

    # 3. Help Button
    elif query.data == "help_btn":
        help_text = f"""
❓ **Need Help?**

1️⃣ **Verify Issue:** Clear browser cache or try another browser.
2️⃣ **Movie Request:** Join our Main Channel and comment there.
3️⃣ **Admin Support:** Contact developer for direct help.
"""
        help_buttons = InlineKeyboardMarkup(
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
        await query.message.edit_caption(caption=help_text, reply_markup=help_buttons)

    # 4. Back to Home Menu Button
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
                        "❓ How to Verify Free (Tutorial)",
                        callback_data="how_to_verify",
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


# ==========================================
# 5. MAIN BOT RUNNER
# ==========================================
if __name__ == "__main__":
    init_db()  # Database setup
    print("Starting Flask Web Server for Koyeb Health Check...")
    keep_alive()  # Koyeb TCP Health Check Fix Start
    print("Bot Successfully Started with All Features!")
    app.run()  # Run Pyrogram Bot
