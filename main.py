import os
import json
import re
from flask import Flask
from threading import Thread
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import ApplicationBuilder, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes

# --- CONFIGURATION ---
BOT_TOKEN = os.environ.get("BOT_TOKEN", "YOUR_BOT_TOKEN_HERE")
ADMIN_USERNAME = os.environ.get("ADMIN_USERNAME", "YOUR_ADMIN_USERNAME")
ADMIN_ID = int(os.environ.get("ADMIN_ID", "123456789"))  # Numeric Telegram User ID
UPI_ID = os.environ.get("UPI_ID", "YOUR_UPI_ID@upi")
CHANNEL_ID = os.environ.get("CHANNEL_ID", "-1002564797463")  # Optional: @YourChannelUsername or -100xxxxxxxxx
PORT = int(os.environ.get("PORT", 8080))

DATA_FILE = "files_data.json"
USERS_FILE = "users_data.json"
USER_SELECTIONS = {}  # User tracking for payment screenshots

# --- DATA LOAD / SAVE FUNCTIONS ---
def load_json(filename):
    if os.path.exists(filename):
        try:
            with open(filename, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {} if "files" in filename else []
    return {} if "files" in filename else []

def save_json(filename, data):
    with open(filename, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4, ensure_ascii=False)

def add_user(user_id):
    users = load_json(USERS_FILE)
    if not isinstance(users, list):
        users = []
    if user_id not in users:
        users.append(user_id)
        save_json(USERS_FILE, users)

# Telegram Channel Link Parser Helper
def parse_telegram_link(link):
    pattern = r"https://t\.me/(?:c/)?([^/]+)/(\d+)"
    match = re.search(pattern, link)
    if match:
        chat_id_raw = match.group(1)
        message_id = int(match.group(2))
        
        if chat_id_raw.isdigit():
            chat_id = int("-100" + chat_id_raw)
        else:
            chat_id = "@" + chat_id_raw
            
        return chat_id, message_id
    return None, None

# --- DUMMY FLASK SERVER FOR KOYEB PORT BINDING ---
app = Flask(__name__)

@app.route('/')
def home():
    return "Bot is running live on Koyeb!"

def run_flask():
    app.run(host='0.0.0.0', port=PORT)

# --- USER HANDLERS ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    add_user(user_id)

    files_data = load_json(DATA_FILE)
    keyboard = []

    if not files_data:
        msg = "<b>👋 Welcome to Movie Store Bot!</b>\n\n<i>Abhi koi movie available nahi hai.</i>"
        keyboard.append([InlineKeyboardButton("💬 Admin Support", url=f"https://t.me/{ADMIN_USERNAME}")])
        await update.message.reply_text(msg, parse_mode='HTML', reply_markup=InlineKeyboardMarkup(keyboard))
    else:
        for f_id, f_data in files_data.items():
            keyboard.append([InlineKeyboardButton(f"🎬 {f_data['name']} - {f_data['price']}", callback_data=f"file_{f_id}")])
        
        keyboard.append([InlineKeyboardButton("💬 Admin Support", url=f"https://t.me/{ADMIN_USERNAME}")])
        msg = "<b>👋 Welcome to Movie Store Bot!</b>\n\nNiche di gayi list me se movie select karein:"
        reply_markup = InlineKeyboardMarkup(keyboard)

        # Send start message
        await update.message.reply_text(msg, parse_mode='HTML', reply_markup=reply_markup)

async def button_click(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data
    files_data = load_json(DATA_FILE)
    user_id = query.from_user.id
    add_user(user_id)

    if data.startswith("file_"):
        file_id = data.split("_")[1]
        if file_id in files_data:
            selected = files_data[file_id]
            USER_SELECTIONS[user_id] = file_id  # Track user choice
            
            price_number = ''.join(filter(str.isdigit, selected["price"]))
            qr_url = f"https://api.qrserver.com/v1/create-qr-code/?size=300x300&data=upi://pay?pa={UPI_ID}&pn=MovieStore&am={price_number}"

            poster_url = selected.get("poster", qr_url)
            imdb_link = selected.get("imdb", "N/A")
            details = selected.get("details", "HD Movie")

            caption = (
                f"🎬 <b>Movie Name:</b> {selected['name']}\n"
                f"🗣️ <b>Language & Quality:</b> {details}\n"
                f"💰 <b>Price:</b> {selected['price']}\n"
                f"⭐ <b>IMDB Info:</b> <a href='{imdb_link}'>Click Here To Check IMDB</a>\n\n"
                f"💳 <b>Payment Details:</b>\n"
                f"<b>UPI ID:</b> <code>{UPI_ID}</code>\n\n"
                f"📌 <b>Direct Video Paane Ke Liye:</b>\n"
                f"1. Upar QR code scan karke {selected['price']} pay karein.\n"
                f"2. <b>Payment ka Screenshot ISI BOT CHAT me photo bhej dein.</b>\n"
                f"3. Verification hote hi Bot aapko Direct Video File bhej dega."
            )

            keyboard = [[InlineKeyboardButton("⬅️ Back to Menu", callback_data="back_menu")]]
            reply_markup = InlineKeyboardMarkup(keyboard)

            try:
                await query.message.reply_photo(photo=poster_url, caption=caption, parse_mode='HTML', reply_markup=reply_markup)
            except Exception:
                await query.message.reply_photo(photo=qr_url, caption=caption, parse_mode='HTML', reply_markup=reply_markup)

    elif data == "back_menu":
        keyboard = []
        for f_id, f_data in files_data.items():
            keyboard.append([InlineKeyboardButton(f"🎬 {f_data['name']} - {f_data['price']}", callback_data=f"file_{f_id}")])
        
        keyboard.append([InlineKeyboardButton("💬 Admin Support", url=f"https://t.me/{ADMIN_USERNAME}")])
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.message.reply_text("<b>👋 Main Menu:</b>\nMovie select karein:", parse_mode='HTML', reply_markup=reply_markup)

    elif data.startswith("approve_"):
        _, target_user_id, file_id = data.split("_")
        files_data = load_json(DATA_FILE)

        if file_id in files_data:
            file_info = files_data[file_id]
            file_link = file_info.get("file_link", "")

            from_chat_id, message_id = parse_telegram_link(file_link)

            try:
                if from_chat_id and message_id:
                    # DIRECT VIDEO FILE COPY KARKE USER KO BHEJNA
                    await context.bot.copy_message(
                        chat_id=int(target_user_id),
                        from_chat_id=from_chat_id,
                        message_id=message_id,
                        caption=f"🎉 <b>Here is your movie:</b> {file_info['name']}\n\n<i>Enjoy your movie!</i>",
                        parse_mode='HTML'
                    )
                    await query.edit_message_caption(caption=query.message.caption + "\n\n✅ <b>APPROVED & DIRECT VIDEO FILE SENT TO MEMBER!</b>")
                else:
                    await context.bot.send_message(chat_id=int(target_user_id), text=f"🎉 <b>Payment Verified!</b>\n\nLink: {file_link}", parse_mode='HTML')
                    await query.edit_message_caption(caption=query.message.caption + "\n\n⚠️ Approved with Link (Parsing Failed)")
            except Exception as e:
                await query.edit_message_caption(caption=query.message.caption + f"\n\n❌ Error sending video file: {str(e)}")

# --- PHOTO RECEIVER ---
async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    user_id = user.id
    add_user(user_id)
    files_data = load_json(DATA_FILE)

    if user_id == ADMIN_ID:
        return

    selected_file_id = USER_SELECTIONS.get(user_id)
    if not selected_file_id or selected_file_id not in files_data:
        await update.message.reply_text("⚠️ Pehle list me se movie select karein fir screenshot bhejein.")
        return

    selected_movie = files_data[selected_file_id]

    await update.message.reply_text("⏳ <b>Screenshot mil gaya hai!</b>\nAdmin verify kar rahe hain. 1-2 min me aapko direct video file mil jayegi.", parse_mode='HTML')

    caption_for_admin = (
        f"🚨 <b>NEW PAYMENT SCREENSHOT!</b>\n\n"
        f"👤 <b>User:</b> {user.full_name} (@{user.username or 'No_Username'})\n"
        f"🆔 <b>User ID:</b> <code>{user_id}</code>\n"
        f"🎬 <b>Selected Movie:</b> {selected_movie['name']}\n"
        f"🗣️ <b>Details:</b> {selected_movie.get('details', 'HD Movie')}\n"
        f"💰 <b>Price:</b> {selected_movie['price']}"
    )

    keyboard = [
        [InlineKeyboardButton("✅ Verify & Send File", callback_data=f"approve_{user_id}_{selected_file_id}")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    photo_id = update.message.photo[-1].file_id
    await context.bot.send_photo(chat_id=ADMIN_ID, photo=photo_id, caption=caption_for_admin, parse_mode='HTML', reply_markup=reply_markup)

# --- ADMIN COMMANDS ---
async def add_file(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id != ADMIN_ID:
        return

    raw_text = " ".join(context.args)
    if "|" not in raw_text:
        await update.message.reply_text(
            "<b>Format:</b>\n<code>/addfile Name | Price | Poster_URL | Video_Link | Language_Quality | IMDB_Link</code>",
            parse_mode='HTML'
        )
        return

    try:
        parts = raw_text.split("|")
        name = parts[0].strip()
        price = parts[1].strip()
        poster = parts[2].strip()
        file_link = parts[3].strip()
        details = parts[4].strip() if len(parts) > 4 else "Hindi - HD"
        imdb = parts[5].strip() if len(parts) > 5 else "https://imdb.com"

        files_data = load_json(DATA_FILE)
        new_id = str(len(files_data) + 1)

        files_data[new_id] = {
            "name": name,
            "price": price,
            "poster": poster,
            "file_link": file_link,
            "details": details,
            "imdb": imdb
        }

        save_json(DATA_FILE, files_data)

        # --- AUTO POST TO PUBLIC CHANNEL ---
        bot_info = await context.bot.get_me()
        bot_username = bot_info.username

        channel_msg = (
            f"🎬 <b>{name}</b>\n\n"
            f"🗣️ <b>Language & Quality:</b> {details}\n"
            f"💰 <b>Price:</b> {price}\n"
            f"⭐ <b>IMDB Link:</b> <a href='{imdb}'>Click Here</a>\n\n"
            f"⚡ <i>Instant Auto Delivery Bot se buy karne ke liye niche button par click karein:</i>"
        )

        channel_keyboard = [
            [InlineKeyboardButton("🛒 Buy Movie via Bot", url=f"https://t.me/{bot_username}?start=file_{new_id}")]
        ]
        
        posted_status = "ℹ️ Channel ID not configured."
        if CHANNEL_ID.strip():
            try:
                await context.bot.send_photo(
                    chat_id=CHANNEL_ID,
                    photo=poster,
                    caption=channel_msg,
                    parse_mode='HTML',
                    reply_markup=InlineKeyboardMarkup(channel_keyboard)
                )
                posted_status = "✅ Posted to Channel Successfully!"
            except Exception as ch_err:
                posted_status = f"⚠️ Added to bot, but Channel Post failed: {str(ch_err)}"

        await update.message.reply_text(f"✅ <b>Movie Added!</b>\nID: {new_id}\nName: {name}\nLanguage & Quality: {details}\n\n{posted_status}", parse_mode='HTML')

    except Exception as e:
        await update.message.reply_text(f"❌ Error: {str(e)}")

async def stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return
    
    users = load_json(USERS_FILE)
    files = load_json(DATA_FILE)
    
    total_users = len(users) if isinstance(users, list) else 0
    total_files = len(files) if isinstance(files, dict) else 0

    msg = (
        f"📊 <b>BOT STATS & OVERVIEW</b>\n\n"
        f"👥 <b>Total Users:</b> <code>{total_users}</code>\n"
        f"🎬 <b>Total Movies Added:</b> <code>{total_files}</code>"
    )
    await update.message.reply_text(msg, parse_mode='HTML')

async def broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return

    users = load_json(USERS_FILE)
    if not users or not isinstance(users, list):
        await update.message.reply_text("❌ Total users: 0")
        return

    reply_to = update.message.reply_to_message
    broadcast_text = " ".join(context.args)

    if not reply_to and not broadcast_text:
        await update.message.reply_text("⚠️ Message reply karein ya `/broadcast Hello Friends` likhein.", parse_mode='HTML')
        return

    await update.message.reply_text(f"⏳ Broadcasting to {len(users)} users...")

    success = 0
    failed = 0

    for u_id in users:
        try:
            if reply_to:
                await context.bot.copy_message(chat_id=u_id, from_chat_id=update.effective_chat.id, message_id=reply_to.message_id)
            else:
                await context.bot.send_message(chat_id=u_id, text=broadcast_text, parse_mode='HTML')
            success += 1
        except Exception:
            failed += 1

    await update.message.reply_text(f"✅ <b>Broadcast Completed!</b>\n\n🟢 Success: {success}\n🔴 Failed/Blocked: {failed}", parse_mode='HTML')

# --- MAIN RUNNER ---
if __name__ == '__main__':
    t = Thread(target=run_flask)
    t.start()

    bot_app = ApplicationBuilder().token(BOT_TOKEN).build()

    bot_app.add_handler(CommandHandler("start", start))
    bot_app.add_handler(CallbackQueryHandler(button_click))
    bot_app.add_handler(MessageHandler(filters.PHOTO, handle_photo))
    bot_app.add_handler(CommandHandler("addfile", add_file))
    bot_app.add_handler(CommandHandler("stats", stats))
    bot_app.add_handler(CommandHandler("broadcast", broadcast))

    print("Bot is running fully automated with Poster & Details...")
    bot_app.run_polling()
    
