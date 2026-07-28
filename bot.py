import asyncio
import os
from threading import Thread
from flask import Flask, request
from motor.motor_asyncio import AsyncIOMotorClient
from pyrogram import Client, filters
from pyrogram.types import (
    CallbackQuery,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    Message,
)
from config import (
    API_HASH,
    API_ID,
    BOT_TOKEN,
    BOT_USERNAME,
    DEV_ADMIN_USERNAME,
    MAIN_CHANNEL,
    MONGO_URL,
    START_PHOTO,
)

# ==========================================
# 1. FLASK SERVER & WEBHOOK (Auto Payment)
# ==========================================
web_app = Flask("")


@web_app.route("/")
def home():
    return "Bot is Running Successfully with Auto Gateway!"


# Ye webhook route aapke UPI Gateway se payment success hone par hit hoga
@web_app.route("/payment-webhook", methods=["POST"])
def payment_webhook():
    data = request.json
    # Gateway se aane wala data (Example: user_id, txn_id, status)
    user_id = data.get("user_id")
    status = data.get("status")

    if status == "SUCCESS" and user_id:
        # Background loop me database update karne ke liye
        # (Yahan aap async task ya database direct update kar sakte hain)
        return {"status": "success"}, 200

    return {"status": "failed"}, 400


def run_flask():
    port = int(os.environ.get("PORT", 8080))
    web_app.run(host="0.0.0.0", port=port)


def keep_alive():
    t = Thread(target=run_flask)
    t.daemon = True
    t.start()


# ==========================================
# 2. CLIENT & MONGODB INITIALIZATION
# ==========================================
app = Client("MovieStoreBot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

mongo_client = AsyncIOMotorClient(MONGO_URL)
db = mongo_client["MovieStoreBotDB"]
users_col = db["users"]
files_col = db["files"]


async def get_user(user_id):
    user = await users_col.find_one({"user_id": user_id})
    if not user:
        user = {
            "user_id": user_id,
            "points": 0,
            "referred_count": 0,
            "is_premium": False,
        }
        await users_col.insert_one(user)
    return user


START_TEXT = """
👋 **Hello {first_name}!**

🤖 **Welcome to Movie Store Bot!**

🎬 **Main Features:**
• 🚀 High-Speed Direct Movie Downloads
• 🎁 **Refer & Earn:** Share with **5 Friends** = Get 1 Free Movie Access!
• 💎 **Automatic Premium:** Instant Activation via UPI Gateway!

📊 **Your Account Status:**
• 👤 Status: `{status}`
• 💎 Credits: `{points} / 5 Points`

👇 *Niche diye gaye buttons se access karein:*
"""


# ==========================================
# 3. FILE STORE BOT STYLE (Auto Link Generator)
# ==========================================
@app.on_message(
    (filters.document | filters.video) & filters.private & ~filters.me
)
async def store_file_and_get_link(client: Client, message: Message):
    if message.from_user.username != DEV_ADMIN_USERNAME:
        await message.reply_text(
            "❌ Aap Admin nahi hain, isliye files store nahi kar sakte."
        )
        return

    file_id = (
        message.document.file_id if message.document else message.video.file_id
    )
    file_name = (
        message.document.file_name
        if message.document
        else "Movie / Video File"
    )

    import random
    import string

    unique_code = "".join(
        random.choices(string.ascii_letters + string.digits, k=8)
    )

    await files_col.insert_one(
        {"code": unique_code, "file_id": file_id, "file_name": file_name}
    )
    share_link = f"https://t.me/{BOT_USERNAME}?start=file_{unique_code}"

    await message.reply_text(
        f"✅ **File Successfully Stored!**\n\n"
        f"📄 **File:** `{file_name}`\n\n"
        f"🔗 **Shareable Link (Channel ke liye):**\n`{share_link}`"
    )


# ==========================================
# 4. ADMIN COMMAND: MANUAL / AUTO PREMIUM
# ==========================================
@app.on_message(filters.command("addpremium") & filters.private)
async def add_premium(client: Client, message: Message):
    if message.from_user.username != DEV_ADMIN_USERNAME:
        return
    args = message.text.split()
    if len(args) < 2:
        await message.reply_text("⚠️ **Usage:** `/addpremium <user_id>`")
        return

    target_user_id = int(args[1])
    await users_col.update_one(
        {"user_id": target_user_id},
        {"$set": {"is_premium": True}},
        upsert=True,
    )
    await message.reply_text(
        f"✅ **User `{target_user_id}` is now a Premium Member!**"
    )


# ==========================================
# 5. START COMMAND & FILE DELIVERY LOGIC
# ==========================================
@app.on_message(filters.command("start"))
async def start_cmd(client: Client, message: Message):
    user_id = message.from_user.id
    first_name = message.from_user.first_name
    text_args = message.text.split()

    # Referral Tracking
    if len(text_args) > 1 and text_args[1].startswith("ref_"):
        try:
            referrer_id = int(text_args[1].replace("ref_", ""))
            if referrer_id != user_id:
                existing_user = await users_col.find_one({"user_id": user_id})
                if not existing_user:
                    await users_col.update_one(
                        {"user_id": referrer_id},
                        {"$inc": {"referred_count": 1, "points": 1}},
                        upsert=True,
                    )
        except ValueError:
            pass

    user_data = await get_user(user_id)

    # File Delivery Logic
    if len(text_args) > 1 and text_args[1].startswith("file_"):
        file_code = text_args[1].replace("file_", "")
        file_data = await files_col.find_one({"code": file_code})

        if file_data:
            is_premium = user_data.get("is_premium", False)
            points = user_data.get("points", 0)

            if is_premium:
                await message.reply_text(
                    "👑 **Premium Member Detected!** Direct Downloading..."
                )
                await message.reply_document(file_data["file_id"])
                return

            if points < 5:
                referral_link = f"https://t.me/{BOT_USERNAME}?start=ref_{user_id}"
                await message.reply_text(
                    f"🔒 **Locked Movie File!**\n\n"
                    f"❌ Aapke paas `{points}/5 Points` hain.\n\n"
                    f"👇 **2 Ways to Unlock:**\n"
                    f"1️⃣ **Free Way:** Share link with **5 Friends**\n👉 `{referral_link}`\n\n"
                    f"2️⃣ **Instant Automatic Way:** Buy **Auto-Premium** via Gateway!"
                )
                return

            await users_col.update_one(
                {"user_id": user_id}, {"$inc": {"points": -5}}
            )
            await message.reply_text(
                "🎉 **5 Referrals complete!** File unlocked successfully."
            )
            await message.reply_document(file_data["file_id"])
            return
        else:
            await message.reply_text("⚠️ File not found or expired.")
            return

    points = user_data.get("points", 0)
    is_premium = user_data.get("is_premium", False)
    status_str = "👑 Premium Member" if is_premium else "🆓 Free Member"

    buttons = InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton(
                    "💎 Buy Auto-Premium (Instant Pay)",
                    callback_data="pay_gateway",
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
                    "👨‍💻 Support", url=f"https://t.me/{DEV_ADMIN_USERNAME}"
                ),
            ],
        ]
    )

    await message.reply_photo(
        photo=START_PHOTO,
        caption=START_TEXT.format(
            first_name=first_name, points=points, status=status_str
        ),
        reply_markup=buttons,
    )


# ==========================================
# 6. CALLBACK HANDLERS (Auto Gateway Link)
# ==========================================
@app.on_callback_query()
async def callback_handler(client: Client, query: CallbackQuery):
    user_id = query.from_user.id

    if query.data == "pay_gateway":
        # Yahan aap apne UPI Gateway (Jaise Upigateway.com ya koi aur) ka payment link generate kar sakte hain
        # Example Dynamic Payment URL with User ID parameter:
        gateway_payment_url = (
            f"https://your-upigateway-domain.com/pay?user_id={user_id}&amount=29"
        )

        gateway_text = """
💎 **Automatic UPI Gateway Payment**

🚀 **Instant Activation:**
Niche diye gaye button par click karke Payment karein. Payment successful hote hi bot aapko automatic **Premium Member** bana dega!

💰 **Price:** ₹29 (1 Month Access)
"""
        pay_btn = InlineKeyboardMarkup(
            [
                [
                    InlineKeyboardButton(
                        "💳 Pay Now (Instant UPI)", url=gateway_payment_url
                    )
                ],
                [InlineKeyboardButton("🔙 Back to Main", callback_data="back_home")],
            ]
        )
        await query.message.edit_caption(
            caption=gateway_text, reply_markup=pay_btn
        )

    elif query.data == "refer_info":
        user_data = await get_user(user_id)
        points = user_data.get("points", 0)
        referred_count = user_data.get("referred_count", 0)
        referral_link = f"https://t.me/{BOT_USERNAME}?start=ref_{user_id}"

        refer_text = f"""
🎁 **Refer & Earn Program**

👉 **Aapka Referral Link:**
`{referral_link}`

📊 **Aapke Stats:**
• Total Referred Friends: `{referred_count}`
• Current Points: `{points} / 5`
"""
        back_btn = InlineKeyboardMarkup(
            [[InlineKeyboardButton("🔙 Back to Main", callback_data="back_home")]]
        )
        await query.message.edit_caption(caption=refer_text, reply_markup=back_btn)

    elif query.data == "back_home":
        first_name = query.from_user.first_name
        user_data = await get_user(user_id)
        points = user_data.get("points", 0)
        is_premium = user_data.get("is_premium", False)
        status_str = "👑 Premium Member" if is_premium else "🆓 Free Member"

        home_buttons = InlineKeyboardMarkup(
            [
                [
                    InlineKeyboardButton(
                        "💎 Buy Auto-Premium (Instant Pay)",
                        callback_data="pay_gateway",
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
                        "👨‍💻 Support", url=f"https://t.me/{DEV_ADMIN_USERNAME}"
                    ),
                ],
            ]
        )
        await query.message.edit_caption(
            caption=START_TEXT.format(
                first_name=first_name, points=points, status=status_str
            ),
            reply_markup=home_buttons,
        )


# ==========================================
# 7. MAIN RUNNER
# ==========================================
if __name__ == "__main__":
    print("Starting Flask Server with Webhook Support...")
    keep_alive()
    print("Bot Successfully Running!")
    app.run()
    
