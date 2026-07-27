import os
import json
from flask import Flask
from threading import Thread
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import ApplicationBuilder, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes

# --- CONFIGURATION ---
BOT_TOKEN = os.environ.get("BOT_TOKEN", "YOUR_BOT_TOKEN_HERE")
ADMIN_USERNAME = os.environ.get("ADMIN_USERNAME", "YOUR_ADMIN_USERNAME")
ADMIN_ID = int(os.environ.get("ADMIN_ID", "123456789"))  # Numeric Telegram User ID
UPI_ID = os.environ.get("UPI_ID", "YOUR_UPI_ID@upi")
PORT = int(os.environ.get("PORT", 8080))

DATA_FILE = "files_data.json"
USER_SELECTIONS = {}  # User tracking for payment screenshots

# --- DATA LOAD / SAVE FUNCTIONS ---
def load_files():
    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {}
    return {}

def save_files(data):
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4, ensure_ascii=False)

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
        msg = "<b>👋 Welcome to Movie Store Bot!</b>\n\n<i>Abhi koi movie available nahi hai.</i>"
    else:
        for f_id, f_data in files_data.items():
            keyboard.append([InlineKeyboardButton(f"🎬 {f_data['name']} - {f_data['price']}", callback_data=f"file_{f_id}")])
        msg = "<b>👋 Welcome to Movie Store Bot!</b>\n\nNiche di gayi list me se movie select karein:"

    keyboard.append([InlineKeyboardButton("💬 Admin Support", url=f"https://t.me/{ADMIN_USERNAME}")])
    reply_markup = InlineKeyboardMarkup(keyboard)

    await update.message.reply_text(msg, parse_mode='HTML', reply_markup=reply_markup)

async def button_click(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data
    files_data = load_files()
    user_id = query.from_user.id

    if data.startswith("file_"):
        file_id = data.split("_")[1]
        if file_id in files_data:
            selected = files_data[file_id]
            USER_SELECTIONS[user_id] = file_id  # Track which file user selected
            
            price_number = ''.join(filter(str.isdigit, selected["price"]))
            qr_url = f"https://api.qrserver.com/v1/create-qr-code/?size=300x300&data=upi://pay?pa={UPI_ID}&pn=MovieStore&am={price_number}"

            caption = (
                f"🎬 <b>Movie Name:</b> {selected['name']}\n"
                f"💰 <b>Price:</b> {selected['price']}\n"
                f"⭐ <b>IMDB Link:</b> <a href='{selected['imdb']}'>Click Here</a>\n\n"
                f"📝 <b>Details:</b>\n{selected.get('details', 'HD Movie')}\n\n"
                f"💳 <b>Payment Details:</b>\n"
                f"<b>UPI ID:</b> <code>{UPI_ID}</code>\n\n"
                f"📌 <b>File Paane Ke Liye:</b>\n"
                f"1. QR code scan karke {selected['price']} pay karein.\n"
                f"2. <b>Payment ka Screenshot ISI BOT CHAT me photo bhej dein.</b>\n"
                f"3. Verification hote hi Bot aapko Direct Video File bhej dega."
            )

            keyboard = [[InlineKeyboardButton("⬅️ Back to Menu", callback_data="back_menu")]]
            reply_markup = InlineKeyboardMarkup(keyboard)

            await query.message.reply_photo(photo=qr_url, caption=caption, parse_mode='HTML', reply_markup=reply_markup)

    elif data == "back_menu":
        keyboard = []
        for f_id, f_data in files_data.items():
            keyboard.append([InlineKeyboardButton(f"🎬 {f_data['name']} - {f_data['price']}", callback_data=f"file_{f_id}")])
        
        keyboard.append([InlineKeyboardButton("💬 Admin Support", url=f"https://t.me/{ADMIN_USERNAME}")])
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.message.reply_text("<b>👋 Main Menu:</b>\nMovie select karein:", parse_mode='HTML', reply_markup=reply_markup)

    elif data.startswith("approve_"):
        # Format: approve_USERID_FILEID
        _, target_user_id, file_id = data.split("_")
        files_data = load_files()

        if file_id in files_data:
            file_info = files_data[file_id]
            file_link = file_info.get("file_link", "")

            try:
                # Member ko message/file bhejna
                msg = (
                    f"🎉 <b>Payment Verified Successfully!</b>\n\n"
                    f"🎬 <b>Movie:</b> {file_info['name']}\n"
                    f"📥 <b>Download / Access Link:</b>\n{file_link}\n\n"
                    f"<i>Thank you for buying! Enjoy your movie.</i>"
                )
                await context.bot.send_message(chat_id=int(target_user_id), text=msg, parse_mode='HTML')
                await query.edit_message_caption(caption=query.message.caption + "\n\n✅ <b>APPROVED & FILE SENT TO MEMBER!</b>")
            except Exception as e:
                await query.edit_message_caption(caption=f"❌ Error sending file: {str(e)}")

# --- PHOTO / SCREENSHOT RECEIVER HANDLER ---
async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    user_id = user.id
    files_data = load_files()

    if user_id == ADMIN_ID:
        return  # Ignore admin sending photos

    selected_file_id = USER_SELECTIONS.get(user_id)
    if not selected_file_id or selected_file_id not in files_data:
        await update.message.reply_text("⚠️ Pehle list me se movie select karein fir screenshot bhejein.")
        return

    selected_movie = files_data[selected_file_id]

    # Member ko confirmation
    await update.message.reply_text("⏳ <b>Screenshot mil gaya hai!</b>\nAdmin verify kar rahe hain. 1-2 min me aapko video file mil jayegi.", parse_mode='HTML')

    # Admin ko notification & Photo forward karna
    caption_for_admin = (
        f"🚨 <b>NEW PAYMENT SCREENSHOT!</b>\n\n"
        f"👤 <b>User:</b> {user.full_name} (@{user.username or 'No_Username'})\n"
        f"🆔 <b>User ID:</b> <code>{user_id}</code>\n"
        f"🎬 <b>Selected Movie:</b> {selected_movie['name']}\n"
        f"💰 <b>Price:</b> {selected_movie['price']}"
    )

    keyboard = [
        [InlineKeyboardButton("✅ Verify & Send File", callback_data=f"approve_{user_id}_{selected_file_id}")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    photo_id = update.message.photo[-1].file_id
    await context.bot.send_photo(chat_id=ADMIN_ID, photo=photo_id, caption=caption_for_admin, parse_mode='HTML', reply_markup=reply_markup)

# --- ADMIN COMMAND HANDLERS ---
async def add_file(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id != ADMIN_ID:
        return

    raw_text = " ".join(context.args)
    if "|" not in raw_text:
        await update.message.reply_text(
            "<b>Format:</b>\n<code>/addfile Name | Price | IMDB | File_Link_or_Msg | Details</code>",
            parse_mode='HTML'
        )
        return

    try:
        parts = raw_text.split("|")
        name = parts[0].strip()
        price = parts[1].strip()
        imdb = parts[2].strip()
        file_link = parts[3].strip()
        details = parts[4].strip() if len(parts) > 4 else "HD Movie"

        files_data = load_files()
        new_id = str(len(files_data) + 1)

        files_data[new_id] = {
            "name": name,
            "price": price,
            "imdb": imdb,
            "file_link": file_link,
            "details": details
        }

        save_files(files_data)
        await update.message.reply_text(f"✅ <b>Movie Added!</b>\nID: {new_id} | Name: {name}", parse_mode='HTML')
    except Exception as e:
        await update.message.reply_text(f"❌ Error: {str(e)}")

# --- MAIN RUNNER ---
if __name__ == '__main__':
    t = Thread(target=run_flask)
    t.start()

    bot_app = ApplicationBuilder().token(BOT_TOKEN).build()

    bot_app.add_handler(CommandHandler("start", start))
    bot_app.add_handler(CallbackQueryHandler(button_click))
    bot_app.add_handler(MessageHandler(filters.PHOTO, handle_photo))
    bot_app.add_handler(CommandHandler("addfile", add_file))

    print("Bot is starting Auto Delivery System...")
    bot_app.run_polling()
    
