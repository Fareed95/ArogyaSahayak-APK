import logging
import os
from telegram import Update
from telegram.ext import ContextTypes
from telegram import (
    Update,
    KeyboardButton,
    ReplyKeyboardMarkup,
)
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters,
)

logging.basicConfig(level=logging.INFO)

# ---------- Persistent Always-visible Menu ----------
MAIN_MENU = ReplyKeyboardMarkup(
    [
        ["📤 Upload Report", "📁 View Reports"],
        ["💬 Chat with Reports"],
        ["🍽 Best Food Near Me"],
        ["🏥 Get Me to Hospital"],
        ["📅 Book Appointment"],
        ["💊 Order Medicines"]
    ],
    resize_keyboard=True,
    one_time_keyboard=False
)

# ---------- 📱 Ask Phone Number Button ----------
ASK_PHONE = ReplyKeyboardMarkup(
    [[KeyboardButton("📞 Share Phone Number", request_contact=True)]],
    resize_keyboard=True,
    one_time_keyboard=True
)

# -------------------- START COMMAND --------------------
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "👋 Welcome to *Health Assistant Bot!*",
        parse_mode="Markdown"
    )

    await update.message.reply_text(
        "Main tumhari medical reports manage karne, analyze karne, "
        "medicines order karne aur emergency me help karne ke liye hoon! 😇"
    )

    await update.message.reply_text(
        "Pehle apna phone number verify kara do 👇",
        reply_markup=ASK_PHONE
    )


# -------------------- PHONE NUMBER HANDLER --------------------
async def handle_contact(update: Update, context: ContextTypes.DEFAULT_TYPE):
    contact = update.message.contact

    if not contact:
        return

    user_phone = contact.phone_number
    context.user_data["phone"] = user_phone

    await update.message.reply_text(
        f"👍 Phone number verify ho gaya: {user_phone}\n"
        "Ab hamara setup complete hai!"
    )

    # Send onboarding tour
    await update.message.reply_text(
        "✨ Here's what I can do for you:\n"
        "• Upload & analyze medical reports\n"
        "• Track all old reports\n"
        "• AI-based chat with your reports\n"
        "• Best food options near you\n"
        "• Hospital emergency navigation\n"
        "• Appointment booking\n"
        "• Order medicines"
    )

    await update.message.reply_text(
        "👇 Niche se koi option choose karo",
        reply_markup=MAIN_MENU
    )


# -------------------- MAIN MENU HANDLER --------------------
async def menu_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text

    if text == "📤 Upload Report":
        await update.message.reply_text("Send your report file (PDF/Image)...")

    elif text == "📁 View Reports":
        await update.message.reply_text("Here are your stored reports...")

    elif text == "💬 Chat with Reports":
        await update.message.reply_text("Ask anything about your reports…")

    elif text == "🍽 Best Food Near Me":
        await update.message.reply_text("Finding best food options near you...")

    elif text == "🏥 Get Me to Hospital":
        await update.message.reply_text("Finding nearest hospital & route...")

    elif text == "📅 Book Appointment":
        await update.message.reply_text("Booking appointment…")

    elif text == "💊 Order Medicines":
        await update.message.reply_text("Ordering medicines…")

    else:
        await update.message.reply_text("Select from menu below 👇", reply_markup=MAIN_MENU)


# -------------------- FILE HANDLER (Upload Report) --------------------
async def file_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    file_id = None
    file_name = None

    # PDF / Document
    if update.message.document:
        file_id = update.message.document.file_id
        file_name = update.message.document.file_name  # actual name

    # Image
    elif update.message.photo:
        file_obj = update.message.photo[-1]  # highest resolution
        file_id = file_obj.file_id
        file_name = f"{file_id}.jpg"  # save as jpg

    if not file_id:
        await update.message.reply_text("Please send a valid image or PDF.")
        return

    # Make uploads folder if not exist
    os.makedirs("uploads", exist_ok=True)
    save_path = os.path.join("uploads", file_name)

    # Get Telegram file and download
    telegram_file = await context.bot.get_file(file_id)
    await telegram_file.download_to_drive(save_path)

    await update.message.reply_text(f"✔ Report uploaded successfully!\nSaved as: {save_path}")
# -------------------- MAIN APP --------------------
def main():
    BOT_TOKEN = "8540623803:AAHxLwLQx3MPdlV_yAg0RzPcPzqMBFznrvw"

    app = ApplicationBuilder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.CONTACT, handle_contact))
    app.add_handler(MessageHandler(filters.Document.ALL | filters.PHOTO, file_handler))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, menu_handler))

    print("Bot running...")
    app.run_polling()


if __name__ == "__main__":
    main()
