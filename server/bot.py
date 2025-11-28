import os
from telegram import (
    Update,
    ReplyKeyboardMarkup,
    KeyboardButton,
)
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters
)

BOT_TOKEN = "8540623803:AAHxLwLQx3MPdlV_yAg0RzPcPzqMBFznrvw"


# --- START: Ask for phone number ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    button = KeyboardButton("Share Phone Number", request_contact=True)
    keyboard = ReplyKeyboardMarkup([[button]], resize_keyboard=True)

    await update.message.reply_text(
        "Phone number share karo 👇",
        reply_markup=keyboard
    )


# --- When user shares phone number ---
async def handle_contact(update: Update, context: ContextTypes.DEFAULT_TYPE):
    contact = update.message.contact
    phone = contact.phone_number
    name = contact.first_name

    await update.message.reply_text(
        f"Thanks {name}! 📱 Your number: {phone}"
    )

    # After getting phone → show option menu
    options = [
        ["📤 Upload your report"],
        ["📁 See all your reports"],
        ["💬 Chat with reports"],
        ["🍲 Get best food options near you"],
        ["🏥 Get me to Hospital"],
        ["📅 Book an appointment"],
        ["💊 Book medicines"]
    ]

    keyboard = ReplyKeyboardMarkup(options, resize_keyboard=True)

    await update.message.reply_text(
        "Choose an option 👇",
        reply_markup=keyboard
    )


# --- Handle text options ---
async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text

    if text == "📤 Upload your report":
        await update.message.reply_text("Upload your report — PDF ya Image dono chalega.")
        context.user_data["waiting_for_report"] = True

    elif text == "📁 See all your reports":
        await update.message.reply_text("Fetching all reports…")

    elif text == "💬 Chat with reports":
        await update.message.reply_text("Chat with your reports — starting…")

    elif text == "🍲 Get best food options near you":
        await update.message.reply_text("Searching best food options near you…")

    elif text == "🏥 Get me to Hospital":
        await update.message.reply_text("Getting nearest hospital…")

    elif text == "📅 Book an appointment":
        await update.message.reply_text("Booking an appointment…")

    elif text == "💊 Book medicines":
        await update.message.reply_text("Ordering medicines…")

    else:
        await update.message.reply_text("Please choose a valid option.")


async def handle_file(update: Update, context: ContextTypes.DEFAULT_TYPE):

    if not context.user_data.get("waiting_for_report"):
        await update.message.reply_text("Pehle 'Upload your report' select karo.")
        return

    file_id = None
    file_name = None

    # PDF / DOC / etc
    if update.message.document:
        file_id = update.message.document.file_id
        file_name = update.message.document.file_name  # actual file name

    # Images
    elif update.message.photo:
        file_id = update.message.photo[-1].file_id
        file_name = f"{file_id}.jpg"   # default name for photos

    # Get file object from Telegram
    telegram_file = await context.bot.get_file(file_id)

    # Make uploads folder if not exist
    os.makedirs("uploads", exist_ok=True)

    # Full path to save
    save_path = os.path.join("uploads", file_name)

    # Download — no binary manipulation
    await telegram_file.download_to_drive(save_path)

    await update.message.reply_text(
        f"Report uploaded successfully! 📝\nSaved as: {save_path}"
    )

    context.user_data["waiting_for_report"] = False



if __name__ == "__main__":
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.CONTACT, handle_contact))

    # File handler (PDF + Images)
    app.add_handler(MessageHandler(filters.Document.ALL | filters.PHOTO, handle_file))

    # Normal text handler
    app.add_handler(MessageHandler(filters.TEXT, handle_text))

    print("Bot running…")
    app.run_polling()
