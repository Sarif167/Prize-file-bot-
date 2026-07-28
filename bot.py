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
# 1. FLASK SERVER (Koyeb Health Check)
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
# 2. CLIENT INITIALIZATION
# ==========================================
app = Client("MovieStoreBot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

VERIFIED_USERS = {}


def get_short_url(long_url):
    try:
        response = requests.get(
            f"{SHORTENER_URL}?api={SHORTENER_API}&url={long_url}"
        )
        data = response.json()
        return data.get("shorturl", long_url)
    except Exception:
        return long_url


START_TEXT = """
👋 **Hello {first_name}!**

🤖 **Welcome to Movie Store Bot!**

🎬 **Main Features:**
• 🚀 High-Speed Direct Movie Downloads
• 🎁 **Refer & Earn:** Per refer = 1 Free Movie Access
• 📺 Multiple Qualities in 1 Click!

💎 **Your Free Credits:** `{points} Points`

👇 *Niche diye gaye buttons se access karein:*
"""


# ==========================================
# 3. DIRECT FORWARD FILE ADD COMMAND
# ==========================================
# Forwarded File par Reply karke ya Caption me Command likh kar Save karne ke liye
@app.on_message(
    filters.command("addbatch")
    & (filters.document | filters.video | filters.reply)
    & filters.private
)
async def add_batch_direct(client: Client, message: Message):
    args = message.text.split() if message.text else []

    # Agar caption me command likha hai
    if not args and message.caption:
        args = message.caption.split()

    if len(args) < 2:
        await message.reply_text(
            "⚠️ **Wrong Format!**\n\n"
            "**Kaise Add Karein:**\n"
            "1️⃣ Database Channel se Video bot par **Forward** karein.\n"
            "2️⃣ Forward ki hui file par Reply karke likhein: `/addbatch MOVIE_ID`\n"
            "*(Ya fir video forward karte waqt caption me likhein `/addbatch MOVIE_ID`)*"
        )
        return

    movie_id = args[1]
    target_msg = message.reply_to_message if message.reply_to_message else message

    # File ID Check
    file_id = None
    if target_msg.document:
        file_id = target_msg.document.file_id
    elif target_msg.video:
        file_id = target_msg.video.file_id

    if not file_id:
        await message.reply_text(
            "❌ Forwarded message me koi Video ya Document file nahi mili!"
        )
        return

    # Save to SQLite Database
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO movie_batches (movie_id, file_id) VALUES (?, ?)",
        (movie_id, file_id),
    )
    conn.commit()

    # Total files added check
    cursor.execute(
        "SELECT COUNT(*) FROM movie_batches WHERE movie_id = ?", (movie_id,)
    )
    total_added = cursor.fetchone()[0]
    conn.close()

    await message.reply_text(
        f"✅ **File Saved Successfully!**\n\n"
        f"🎬 **Movie ID:** `{movie_id}`\n"
        f"📦 **Total Files in this ID:** `{total_added}`"
    )


# Manual Multi-ID Add (Backup Command)
@app.on_message(filters.command("addids") & filters.private)
async def add_batch_manual_ids(client: Client, message: Message):
    args = message.text.split()
    if len(args) < 3:
        await message.reply_text(
            "⚠️ **Usage:** `/addids <movie_id> <file_id_1> <file_id_2>`"
        )
        return

    movie_id = args[1]
    file_ids = args[2:]

    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    for f_id in file_ids:
        cursor.execute(
            "INSERT INTO movie_batches (movie_id, file_id) VALUES (?, ?)",
            (movie_id, f_id),
        )
    conn.commit()
    conn.close()

    await message.reply_text(
        f"✅ Added `{len(file_ids)}` files manually for ID: `{movie_id}`"
    )


# ==========================================
# 4. COMMAND HANDLER (/start)
# ==========================================
@app.on_message(filters.command("start"))
async def start_cmd(client: Client, message: Message):
    user_id = message.from_user.id
    first_name = message.from_user.first_name
    text_args = message.text.split()

    # Referral Check
    referrer = None
    if len(text_args) > 1 and text_args[1].startswith("ref_"):
        try:
            referrer = int(text_args[1].replace("ref_", ""))
        except ValueError:
            pass

    add_user(user_id, referrer)

    # Verification Handler
    if len(text_args) > 1 and text_args[1].startswith("verify_"):
        VERIFIED_USERS[user_id] = datetime.datetime.now() + datetime.timedelta(
            hours=24
        )
        await message.reply_text(
            f"🎉 **Congratulations {first_name}!**\n\nVerification successful! Aapko 24 Hours ka free access mil gaya hai."
        )
        return

    # Movie Access Delivery
    if len(text_args) > 1 and (
        text_args[1].startswith("get_") or text_args[1].startswith("refget_")
    ):
        param = text_args[1]
        movie_id = param.split("_")[1]

        if param.startswith("refget_"):
            points = get_points(user_id)
            if points < 1:
                await message.reply_text(
                    "❌ **Insufficient Points!**\n\nDosto ko refer karein ya Shortener Verify karein."
                )
                return
            deduct_point(user_id)

        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        cursor.execute(
            "SELECT file_id FROM movie_batches WHERE movie_id = ?", (movie_id,)
        )
        files = cursor.fetchall()
        conn.close()

        if files:
            await message.reply_text(
                f"📦 **Sending All Qualities ({len(files)} Files)...**"
            )
            for file_item in files:
                await message.reply_document(file_item[0])
                await asyncio.sleep(1)
            return
        else:
            await message.reply_text("⚠️ No files found for this movie.")
            return

    verify_link = f"https://t.me/{BOT_USERNAME}?start=verify_{user_id}"
    short_verify_link = get_short_url(verify_link)
    user_points = get_points(user_id)

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
            [InlineKeyboardButton("❓ Help", callback_data="help_btn")],
        ]
    )

    await message.reply_photo(
        photo=START_PHOTO,
        caption=START_TEXT.format(
            first_name=first_name, points=user_points
        ),
        reply_markup=buttons,
    )


# ==========================================
# 5. CALLBACK HANDLERS
# ==========================================
@app.on_callback_query()
async def callback_handler(client: Client, query: CallbackQuery):
    user_id = query.from_user.id

    if query.data == "how_to_verify":
        verify_guide_text = """
📖 **How to Verify Free Guide:**

1️⃣ **Step 1:** Niche '🔓 Free Access' button par click karein.
2️⃣ **Step 2:** Shortener page par 10-15 sec wait karke Continue karein.
3️⃣ **Step 3:** Get Link par click karte hi 24 Hours Free Access mil jayega!
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

    elif query.data == "refer_info":
        user_points = get_points(user_id)
        referral_link = f"https://t.me/{BOT_USERNAME}?start=ref_{user_id}"

        refer_text = f"""
🎁 **Refer & Earn Program**

👉 **Aapka Referral Link:**
`{referral_link}`

💰 **Current Credits:** `{user_points} Points`
"""
        back_btn = InlineKeyboardMarkup(
            [[InlineKeyboardButton("🔙 Back to Main", callback_data="back_home")]]
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
                [InlineKeyboardButton("❓ Help", callback_data="help_btn")],
            ]
        )
        await query.message.edit_caption(
            caption=START_TEXT.format(
                first_name=first_name, points=user_points
            ),
            reply_markup=home_buttons,
        )


# ==========================================
# 6. MAIN RUNNER
# ==========================================
if __name__ == "__main__":
    init_db()
    print("Starting Flask Server...")
    keep_alive()
    print("Bot Running!")
    app.run()
    
