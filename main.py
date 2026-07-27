import os
import json
from flask import Flask
from threading import Thread
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import ApplicationBuilder, CommandHandler, CallbackQueryHandler, ContextTypes

# --- CONFIGURATION (Environment Variables se Read Hoga) ---
BOT_TOKEN = os.environ.get("BOT_TOKEN", "YOUR_BOT_TOKEN_HERE")
ADMIN_USERNAME = os.environ.get("ADMIN_USERNAME", "YOUR_ADMIN_USERNAME")  # Bina @ ke
ADMIN_ID = int(os.environ.get("ADMIN_ID", "123456789"))  # Aapka Numeric Telegram ID
UPI_ID = os.environ.get("UPI_ID", "YOUR_UPI_ID@upi")
PORT = int(os.environ.get("PORT", 8080))

DATA_FILE = "files_data.json"

# --- DATA LOAD / SAVE FUNCTIONS ---
def load_files():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, "r") as f:
            return json.load(f)
    return {}

def save_files(data):
    with open(DATA_FILE, "w") as f:
        json.dump(data, f, indent=4)

# --- DUMMY FLASK SERVER FOR KOYEB PORT BINDING ---
app = Flask(__name__)

@app.route('/')
def home():
    return "Bot is running live on Koyeb!"

def run_flask():
    app.run(host='0.0.0.0', port=PORT)

# --- USER HANDLERS ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    files_data = load_files()
    keyboard = []

    if not files_data:
        msg = "<b>👋 Welcome to Store Bot!</b>\n\n<i>Abhi koi file available nahi hai.</i>"
    else:
        for f_id, f_data in files_data.items():
            keyboard.append([InlineKeyboardButton(f"🎬 {f_data['name']} - {f_data['price']}", callback_data=f"file_{f_id}")])
        msg = "<b>👋 Welcome to Store Bot!</b>\n\nNiche di gayi list me se apni file select karein:"

    keyboard.append([InlineKeyboardButton("💬 Admin Support", url=f"https://t.me/{ADMIN_USERNAME}")])
    reply_markup = InlineKeyboardMarkup(keyboard)

    await update.message.reply_text(msg, parse_mode='HTML', reply_markup=reply_markup)

async def button_click(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data
    files_data = load_files()

    if data.startswith("file_"):
        file_id = data.split("_")[1]
        if file_id in files_data:
            selected = files_data[file_id]
            price_number = ''.join(filter(str.isdigit, selected["price"]))
            
            # Dynamic UPI QR Generator
            qr_url = f"https://api.qrserver.com/v1/create-qr-code/?size=300x300&data=upi://pay?pa={UPI_ID}&pn=Store&am={price_number}"

            caption = (
                f"<b>📄 File Name:</b> {selected['name']}\n"
                f"<b>💰 Price:</b> {selected['price']}\n"
                f"<b>⭐ IMDB Info:</b> <a href='{selected['imdb']}'>Click Here</a>\n\n"
                f"<b>💳 Payment Details:</b>\n"
                f"<b>UPI ID:</b> <code>{UPI_ID}</code>\n\n"
                f"📌 <i>Payment karne ke baad screenshot niche diye gaye Admin button par bhejein.</i>"
            )

            keyboard = [
                [InlineKeyboardButton("📲 Send Payment Screenshot", url=f"https://t.me/{ADMIN_USERNAME}")],
                [InlineKeyboardButton("⬅️ Back to Menu", callback_data="back_menu")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)

            await query.message.reply_photo(photo=qr_url, caption=caption, parse_mode='HTML', reply_markup=reply_markup)

    elif data == "back_menu":
        keyboard = []
        for f_id, f_data in files_data.items():
            keyboard.append([InlineKeyboardButton(f"🎬 {f_data['name']} - {f_data['price']}", callback_data=f"file_{f_id}")])
        
        keyboard.append([InlineKeyboardButton("💬 Admin Support", url=f"https://t.me/{ADMIN_USERNAME}")])
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.message.reply_text("<b>👋 Main Menu:</b>\nFile select karein:", parse_mode='HTML', reply_markup=reply_markup)

# --- ADMIN COMMAND HANDLERS ---
async def add_file(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id != ADMIN_ID:
        await update.message.reply_text("❌ Aap Admin nahi hain!")
        return

    raw_text = " ".join(context.args)
    if "|" not in raw_text:
        await update.message.reply_text(
            "<b>Format Sahi Bhejein:</b>\n"
            "<code>/addfile Movie Name | Price | IMDB_Link</code>\n\n"
            "<b>Example:</b>\n"
            "<code>/addfile Border 2 | ₹49 | https://imdb.com/title/xxx</code>",
            parse_mode='HTML'
        )
        return

    try:
        parts = raw_text.split("|")
        name = parts[0].strip()
        price = parts[1].strip()
        imdb = parts[2].strip()

        files_data = load_files()
        new_id = str(len(files_data) + 1)

        files_data[new_id] = {
            "name": name,
            "price": price,
            "imdb": imdb
        }

        save_files(files_data)
        await update.message.reply_text(f"✅ <b>File Added Successfully!</b>\n\n🆔 <b>ID:</b> {new_id}\n🎬 <b>Name:</b> {name}\n💰 <b>Price:</b> {price}", parse_mode='HTML')
    except Exception as e:
        await update.message.reply_text(f"❌ Error: {str(e)}")

async def del_file(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id != ADMIN_ID:
        return

    if not context.args:
        await update.message.reply_text("Usage: <code>/delfile <ID></code>", parse_mode='HTML')
        return

    file_id = context.args[0]
    files_data = load_files()

    if file_id in files_data:
        deleted = files_data.pop(file_id)
        save_files(files_data)
        await update.message.reply_text(f"🗑️ <b>Deleted:</b> {deleted['name']}", parse_mode='HTML')
    else:
        await update.message.reply_text("❌ Ye File ID nahi mili!")

async def list_files_admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id != ADMIN_ID:
        return

    files_data = load_files()
    if not files_data:
        await update.message.reply_text("Abhi koi file add nahi hai.")
        return

    msg = "<b>📋 All Added Files:</b>\n\n"
    for f_id, f_data in files_data.items():
        msg += f"<b>ID {f_id}:</b> {f_data['name']} - {f_data['price']}\n"

    await update.message.reply_text(msg, parse_mode='HTML')

# --- MAIN RUNNER ---
if __name__ == '__main__':
    t = Thread(target=run_flask)
    t.start()

    bot_app = ApplicationBuilder().token(BOT_TOKEN).build()

    # User commands
    bot_app.add_handler(CommandHandler("start", start))
    bot_app.add_handler(CallbackQueryHandler(button_click))

    # Admin commands
    bot_app.add_handler(CommandHandler("addfile", add_file))
    bot_app.add_handler(CommandHandler("delfile", del_file))
    bot_app.add_handler(CommandHandler("files", list_files_admin))

    print("Bot is starting...")
    bot_app.run_polling()

