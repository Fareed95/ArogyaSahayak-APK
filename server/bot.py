import logging
import os
import asyncio
import random
import requests
from datetime import datetime, timedelta
from telegram import Update, KeyboardButton, ReplyKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, ContextTypes, filters
from telegram.error import TimedOut, NetworkError

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

# API Configuration
API_BASE_URL = "https://arogya-sahayak-django.crodlin.in/api/reports"
UPLOAD_REPORT_URL = f"{API_BASE_URL}/upload_report_telegram/"
VIEW_REPORTS_URL = "https://arogya-sahayak-django.crodlin.in/api/reports/get_user_instances/"
AUTH_URL = "https://arogya-sahayak-django.crodlin.in/api/authentication/telegram-login/"

# Timeout settings
REQUEST_TIMEOUT = 300
TELEGRAM_TIMEOUT = 600

# ---------- Persistent Main Menu ----------
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

# ---------- Request Phone Number ----------
ASK_PHONE = ReplyKeyboardMarkup(
    [[KeyboardButton("📞 Share Phone Number", request_contact=True)]],
    resize_keyboard=True,
    one_time_keyboard=True
)

# ---------- Mumbai Dummy Hospitals ----------
HOSPITALS = [
    "🟢 Kokilaben Dhirubhai Ambani Hospital (Andheri)",
    "🏥 Nanavati Max Super Speciality Hospital (Vile Parle)",
    "🚑 H.N. Reliance Foundation Hospital (Girgaon)",
    "💙 Lilavati Hospital (Bandra)",
    "🧡 S.L. Raheja Hospital (Mahim)"
]

HOSPITAL_MENU = ReplyKeyboardMarkup(
    [[h] for h in HOSPITALS],
    resize_keyboard=True,
    one_time_keyboard=True
)

# ---------- Scheduling Options ----------
SCHEDULE_MENU = ReplyKeyboardMarkup(
    [
        ["🚕 Book Cab Now", "⏰ Schedule for Later"],
        ["↩ Back to Hospitals"]
    ],
    resize_keyboard=True,
    one_time_keyboard=True
)

TIME_OPTIONS = ReplyKeyboardMarkup(
    [
        ["15 minutes", "30 minutes", "1 hour"],
        ["2 hours", "Custom time", "↩ Back"]
    ],
    resize_keyboard=True,
    one_time_keyboard=True
)

# ---------- Medicine Ordering ----------
MEDICINE_MENU = ReplyKeyboardMarkup(
    [
        ["💊 Common Medicines", "📝 Prescription Upload"],
        ["🔍 Search Medicines", "↩ Main Menu"]
    ],
    resize_keyboard=True,
    one_time_keyboard=True
)

COMMON_MEDICINES = ReplyKeyboardMarkup(
    [
        ["Paracetamol 500mg", "Ibuprofen 400mg"],
        ["Cetirizine 10mg", "Amoxicillin 500mg"],
        ["Metformin 500mg", "Atorvastatin 10mg"],
        ["↩ Back to Medicine Menu"]
    ],
    resize_keyboard=True,
    one_time_keyboard=True
)

DELIVERY_OPTIONS = ReplyKeyboardMarkup(
    [
        ["🚚 Express Delivery (2 hours)", "📦 Standard Delivery (1 day)"],
        ["⏰ Schedule Delivery", "↩ Back to Medicines"]
    ],
    resize_keyboard=True,
    one_time_keyboard=True
)

# ---------- Appointment Booking ----------
APPOINTMENT_MENU = ReplyKeyboardMarkup(
    [
        ["🩺 General Physician", "❤️ Cardiologist"],
        ["🧠 Neurologist", "🦴 Orthopedist"],
        ["👁️ Ophthalmologist", "🔍 Other Specialist"],
        ["↩ Main Menu"]
    ],
    resize_keyboard=True,
    one_time_keyboard=True
)

DOCTORS = {
    "🩺 General Physician": [
        "Dr. Sharma - Apollo Hospital",
        "Dr. Patel - Kokilaben Hospital", 
        "Dr. Desai - Local Clinic"
    ],
    "❤️ Cardiologist": [
        "Dr. Kumar - Asian Heart Institute",
        "Dr. Mehta - Lilavati Hospital",
        "Dr. Joshi - Nanavati Hospital"
    ],
    "🧠 Neurologist": [
        "Dr. Reddy - Jaslok Hospital",
        "Dr. Iyer - Fortis Hospital", 
        "Dr. Khan - Global Hospital"
    ],
    "🦴 Orthopedist": [
        "Dr. Gupta - Bone & Joint Clinic",
        "Dr. Singh - Ortho Care Center",
        "Dr. Nair - Sports Medicine"
    ],
    "👁️ Ophthalmologist": [
        "Dr. Kapoor - Eye Care Center",
        "Dr. Choudhary - Vision Hospital",
        "Dr. Rao - Netra Clinic"
    ]
}

TIME_SLOTS = ReplyKeyboardMarkup(
    [
        ["🕘 9:00 AM", "🕙 10:00 AM", "🕚 11:00 AM"],
        ["🕛 12:00 PM", "🕐 1:00 PM", "🕑 2:00 PM"],
        ["🕒 3:00 PM", "🕓 4:00 PM", "🕔 5:00 PM"],
        ["↩ Back to Specialists"]
    ],
    resize_keyboard=True,
    one_time_keyboard=True
)

# -------------------- START COMMAND --------------------
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        await update.message.reply_text(
            "👋 Welcome to *Health Assistant Bot!*",
            parse_mode="Markdown"
        )

        await update.message.reply_text(
            "I can help you manage and analyze your medical reports, order medicines, "
            "and assist you in emergencies."
        )

        await update.message.reply_text(
            "Please verify your phone number first 👇",
            reply_markup=ASK_PHONE
        )
    except (TimedOut, NetworkError) as e:
        logging.error(f"Network error in start command: {e}")
    except Exception as e:
        logging.error(f"Unexpected error in start command: {e}")




# -------------------- SIMULATE THINKING --------------------
async def simulate_thinking(update: Update, message: str, delay: float = 2.0):
    """Simulate bot thinking with typing action"""
    try:
        thinking_msg = await update.message.reply_text("🤔 " + message)
        await asyncio.sleep(delay)
        return thinking_msg
    except (TimedOut, NetworkError) as e:
        logging.error(f"Network error in simulate_thinking: {e}")
        return None

# -------------------- AUTHENTICATION HANDLERS --------------------
async def handle_contact(update: Update, context: ContextTypes.DEFAULT_TYPE):
    contact = update.message.contact

    if not contact:
        return

    user_phone = contact.phone_number
    user_name = contact.first_name  # Get user's first name from Telegram contact
    
    thinking_msg = None
    try:
        # Step 1: Check if user exists
        check_data = {'phone': user_phone}
        
        thinking_msg = await simulate_thinking(update, "Checking your account...", 2.0)
        if not thinking_msg:
            return
            
        response = requests.post(AUTH_URL, json=check_data, timeout=REQUEST_TIMEOUT)
        
        if response.status_code == 200:
            result = response.json()
            
            if result.get("password") == True:
                # User exists, ask for password
                await thinking_msg.edit_text("🔐 Please enter your password:")
                context.user_data["phone"] = user_phone
                context.user_data["name"] = user_name  # Store name for later use
                context.user_data["awaiting_password"] = True
                
            else:
                # New user, proceed with setup
                await thinking_msg.edit_text(f"✅ Phone number verified: {user_phone}\nYour setup is now complete!")
                context.user_data["phone"] = user_phone
                context.user_data["name"] = user_name  # Store name
                
                # Onboarding for new user
                await send_onboarding_messages(update)
                
        else:
            await thinking_msg.edit_text("❌ Server error during authentication. Please try again.")
            logging.error(f"Auth API error: {response.status_code} - {response.text}")
            
    except requests.exceptions.Timeout:
        if thinking_msg:
            await thinking_msg.edit_text("❌ Authentication timeout. Please try again.")
    except requests.exceptions.RequestException as e:
        if thinking_msg:
            await thinking_msg.edit_text("❌ Network error. Please check your connection and try again.")
        logging.error(f"Auth API request failed: {e}")
    except Exception as e:
        if thinking_msg:
            await thinking_msg.edit_text("❌ An error occurred during authentication.")
        logging.error(f"Auth error: {e}")

async def handle_password(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.user_data.get("awaiting_password"):
        return False

    password = update.message.text
    user_phone = context.user_data.get("phone")
    user_name = context.user_data.get("name", "test")  # Get stored name
    
    thinking_msg = None
    try:
        thinking_msg = await simulate_thinking(update, "Verifying password...", 2.0)
        if not thinking_msg:
            return True
            
        # Step 2: Login with password - INCLUDING NAME
        login_data = {
            'phone': user_phone,
            'password': password,
            'name': user_name  # Include name in the request
        }
        
        # Send PUT request for login
        response = requests.put(AUTH_URL, json=login_data, timeout=REQUEST_TIMEOUT)
        
        if response.status_code == 200:
            result = response.json()
            
            if result.get("success") == True:
                await thinking_msg.edit_text("✅ Login successful!")
                
                # Clear password state
                context.user_data["awaiting_password"] = False
                
                # Onboarding
                await send_onboarding_messages(update)
                
            else:
                await thinking_msg.edit_text("Your Data is Saved")
                # Keep awaiting_password as True to ask for password again
                
        else:
            await thinking_msg.edit_text("❌ Login failed. Please try again.")
            logging.error(f"Login API error: {response.status_code} - {response.text}")
            
    except requests.exceptions.Timeout:
        if thinking_msg:
            await thinking_msg.edit_text("❌ Login timeout. Please try again.")
    except requests.exceptions.RequestException as e:
        if thinking_msg:
            await thinking_msg.edit_text("❌ Network error. Please try again.")
        logging.error(f"Login API request failed: {e}")
    except Exception as e:
        if thinking_msg:
            await thinking_msg.edit_text("❌ An error occurred during login.")
        logging.error(f"Login error: {e}")
        
    return True

async def send_onboarding_messages(update: Update):
    """Helper function to send onboarding messages with error handling"""
    try:
        await update.message.reply_text(
            "✨ Here's what I can do for you:\n"
            "• Upload & analyze medical reports\n"
            "• Track all previous reports\n"
            "• AI-based chat with your reports\n"
            "• Suggest best food options near you\n"
            "• Provide hospital navigation in emergencies\n"
            "• Book appointments\n"
            "• Order medicines online"
        )
        
        await update.message.reply_text(
            "👇 Select an option from the menu below:",
            reply_markup=MAIN_MENU
        )
    except (TimedOut, NetworkError) as e:
        logging.error(f"Network error in onboarding: {e}")
    except Exception as e:
        logging.error(f"Error in onboarding: {e}")

# -------------------- FILE HANDLER (UPDATED FOR PDF ONLY) --------------------
async def file_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Check if user has verified phone number
    user_phone = context.user_data.get("phone")
    if not user_phone:
        try:
            await update.message.reply_text(
                "❌ Please verify your phone number first using the /start command."
            )
        except (TimedOut, NetworkError):
            pass
        return

    file_id = None
    file_name = None

    # Only accept PDF files
    if update.message.document:
        document = update.message.document
        if document.mime_type == 'application/pdf':
            file_id = document.file_id
            file_name = document.file_name or f"report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
        else:
            try:
                await update.message.reply_text(
                    "❌ Please upload a PDF file only. Other formats are not supported."
                )
            except (TimedOut, NetworkError):
                pass
            return
    else:
        try:
            await update.message.reply_text(
                "❌ Please upload a PDF document. Images are not supported for reports."
            )
        except (TimedOut, NetworkError):
            pass
        return

    # Create uploads directory
    os.makedirs("uploads", exist_ok=True)
    save_path = os.path.join("uploads", file_name)

    thinking_msg = None
    try:
        # Download the file
        thinking_msg = await simulate_thinking(update, "Downloading your report...", 1.5)
        if not thinking_msg:
            return
            
        telegram_file = await context.bot.get_file(file_id)
        await telegram_file.download_to_drive(save_path)
        
        await thinking_msg.edit_text("📤 Uploading to our secure server...")
        
        # Prepare the file for API upload
        with open(save_path, 'rb') as file:
            files = {'file': (file_name, file, 'application/pdf')}
            data = {'phone_number': user_phone}
            
            # Send to API
            response = requests.post(UPLOAD_REPORT_URL, files=files, data=data, timeout=REQUEST_TIMEOUT)
            
            if response.status_code == 200:
                result = response.json()
                await thinking_msg.edit_text("✅ Report uploaded successfully!")
                
                # Show report ID and analysis
                report_id = result.get('report_id', 'N/A')
                final_summary = result.get('final_summary', 'No analysis available.')
                
                # Send report ID
                await update.message.reply_text(
                    f"📋 *Report ID:* {report_id}\n"
                    f"✅ Report processed successfully!",
                    parse_mode="Markdown"
                )
                
                # Send the analysis summary
                await update.message.reply_text(
                    f"📊 *Report Analysis:*\n\n{final_summary}",
                    parse_mode="Markdown"
                )
                
                # Show doctor and hospital details if available
                structured_json = result.get('structured_json', [])
                if structured_json and len(structured_json) > 0:
                    details = structured_json[0].get('details', {})
                    doctor_name = details.get('doctor_name', 'Not specified')
                    hospital_address = details.get('hospital_address', 'Not specified')
                    
                    await update.message.reply_text(
                        f"👨‍⚕️ *Doctor:* {doctor_name}\n"
                        f"🏥 *Hospital:* {hospital_address}",
                        parse_mode="Markdown"
                    )
                    
            elif response.status_code == 400:
                error_msg = response.json().get('error', 'Unknown error')
                await thinking_msg.edit_text(f"❌ Upload failed: {error_msg}")
            else:
                await thinking_msg.edit_text("❌ Server error. Please try again later.")
                logging.error(f"API error: {response.status_code} - {response.text}")
                
  
   
    finally:
        # Clean up downloaded file
        try:
            if os.path.exists(save_path):
                os.remove(save_path)
        except Exception as e:
            logging.error(f"Error cleaning up file: {e}")

    try:
        await update.message.reply_text(
            "How else can I assist you?",
            reply_markup=MAIN_MENU
        )
    except (TimedOut, NetworkError):
        pass

# -------------------- VIEW REPORTS HANDLER --------------------
async def handle_view_reports(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Check if user has verified phone number
    user_phone = context.user_data.get("phone")
    if not user_phone:
        try:
            await update.message.reply_text(
                "❌ Please verify your phone number first using the /start command."
            )
        except (TimedOut, NetworkError):
            pass
        return

    thinking_msg = None
    try:
        thinking_msg = await simulate_thinking(update, "Fetching your reports...", 2.0)
        if not thinking_msg:
            return
            
        # Prepare data for API request
        data = {'phone': user_phone}
        
        # Send POST request to get user reports
        response = requests.post(VIEW_REPORTS_URL, json=data, timeout=REQUEST_TIMEOUT)
        
        if response.status_code == 200:
            result = response.json()
            await thinking_msg.edit_text("✅ Found your reports!")
            
            # Check if reports exist
            if isinstance(result, list) and len(result) > 0:
                await update.message.reply_text(
                    f"📁 *Your Medical Reports* ({len(result)} found)\n",
                    parse_mode="Markdown"
                )
                
                # Display each report
                for i, report in enumerate(result, 1):
                    report_id = report.get('id', 'N/A')
                    created_at = report.get('created_at', 'Unknown date')
                    summary = report.get('final_summary', 'No summary available.')
                    
                    # Shorten summary for preview
                    short_summary = summary[:150] + "..." if len(summary) > 150 else summary
                    
                    await update.message.reply_text(
                        f"📄 *Report #{i}*\n"
                        f"🆔 ID: {report_id}\n"
                        f"📅 Date: {created_at}\n"
                        f"📝 Summary: {short_summary}\n"
                        f"────────────────────",
                        parse_mode="Markdown"
                    )
                
                # Add option to view detailed report
                await update.message.reply_text(
                    "💡 *Tip:* Use the report ID to chat with specific reports or view detailed analysis.",
                    parse_mode="Markdown"
                )
                
            else:
                await update.message.reply_text(
                    "📭 No reports found. Upload your first medical report using the '📤 Upload Report' option!"
                )
                
        elif response.status_code == 404:
            await thinking_msg.edit_text("📭 No reports found for your account.")
        else:
            await thinking_msg.edit_text("❌ Server error. Please try again later.")
            logging.error(f"API error: {response.status_code} - {response.text}")
            
    except requests.exceptions.Timeout:
        if thinking_msg:
            await thinking_msg.edit_text("❌ Request timeout. Please try again.")
    except requests.exceptions.RequestException as e:
        if thinking_msg:
            await thinking_msg.edit_text("❌ Network error. Please check your connection and try again.")
        logging.error(f"API request failed: {e}")
    except Exception as e:
        if thinking_msg:
            await thinking_msg.edit_text("❌ An error occurred while fetching your reports.")
        logging.error(f"View reports error: {e}")

    try:
        await update.message.reply_text(
            "How else can I assist you?",
            reply_markup=MAIN_MENU
        )
    except (TimedOut, NetworkError):
        pass

# -------------------- HOSPITAL CAB BOOKING FUNCTIONS --------------------
async def handle_hospital_choice(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.user_data.get("awaiting_hospital_choice"):
        return False

    selected = update.message.text

    if selected not in HOSPITALS:
        try:
            await update.message.reply_text("Please select a valid hospital from the list.")
        except (TimedOut, NetworkError):
            pass
        return True

    context.user_data["selected_hospital"] = selected
    context.user_data["awaiting_hospital_choice"] = False
    context.user_data["awaiting_schedule_choice"] = True

    try:
        await update.message.reply_text(
            f"🏥 Selected Hospital:\n*{selected}*",
            parse_mode="Markdown"
        )

        await update.message.reply_text(
            "🚕 Would you like to book a cab now or schedule for later?",
            reply_markup=SCHEDULE_MENU
        )
    except (TimedOut, NetworkError):
        pass

    return True


# -------------------- CHAT WITH REPORTS HANDLER --------------------
async def handle_chat_with_reports(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Check if user has verified phone number
    user_phone = context.user_data.get("phone")
    if not user_phone:
        try:
            await update.message.reply_text(
                "❌ Please verify your phone number first using the /start command."
            )
        except (TimedOut, NetworkError):
            pass
        return

    # Set state for ongoing chat
    context.user_data["chatting_with_reports"] = True
    
    try:
        thinking_msg = await simulate_thinking(update, "Starting chat with your reports...", 2.0)
        if not thinking_msg:
            return
            
        await thinking_msg.edit_text("💬 *Chat with Reports Started*", parse_mode="Markdown")
        
        # HARDCODED RESPONSE - No API call
        bot_response = "Based on your medical reports, this appears to be related to cardiovascular health. The report indicates potential heart-related issues that should be discussed with a cardiologist. I recommend consulting with a healthcare professional for detailed analysis of your specific condition."
        
        # Show the bot's response with end chat button
        await update.message.reply_text(
            f"🤖 {bot_response}",
            reply_markup=ReplyKeyboardMarkup(
                [["❌ End Chat"]],
                resize_keyboard=True,
                one_time_keyboard=False
            )
        )
            
    except Exception as e:
        if thinking_msg:
            await thinking_msg.edit_text("❌ An error occurred while starting the chat.")
        logging.error(f"Chat with reports error: {e}")
        context.user_data["chatting_with_reports"] = False

# -------------------- CHAT MESSAGE HANDLER --------------------
async def handle_chat_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Check if user is in chat mode
    if not context.user_data.get("chatting_with_reports"):
        return False

    user_message = update.message.text
    
    # Check if user wants to end chat
    if user_message == "❌ End Chat":
        context.user_data["chatting_with_reports"] = False
        await update.message.reply_text(
            "💬 Chat ended. How else can I assist you?",
            reply_markup=MAIN_MENU
        )
        return True
    
    thinking_msg = None
    try:
        thinking_msg = await simulate_thinking(update, "Analyzing your reports...", 2.0)
        if not thinking_msg:
            return True
            
        # HARDCODED RESPONSE - No API call, always same answer
        bot_response = "This medical report analysis indicates cardiovascular concerns. The data shows potential heart-related issues that require professional medical attention. I strongly advise consulting with a cardiologist for proper diagnosis and treatment recommendations specific to your condition."
        
        await thinking_msg.edit_text(f"🤖 {bot_response}")
            
    except Exception as e:
        if thinking_msg:
            await thinking_msg.edit_text("❌ An error occurred while processing your message.")
        logging.error(f"Chat message error: {e}")
        
    return True

async def handle_schedule_choice(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.user_data.get("awaiting_schedule_choice"):
        return False

    choice = update.message.text
    selected_hospital = context.user_data.get("selected_hospital")
    
    if choice == "🚕 Book Cab Now":
        context.user_data["awaiting_schedule_choice"] = False
        await book_cab_now(update, context, selected_hospital)
        return True
        
    elif choice == "⏰ Schedule for Later":
        try:
            await update.message.reply_text(
                "⏰ When would you like to schedule the cab?",
                reply_markup=TIME_OPTIONS
            )
        except (TimedOut, NetworkError):
            pass
        context.user_data["awaiting_time_choice"] = True
        context.user_data["awaiting_schedule_choice"] = False
        return True
        
    elif choice == "↩ Back to Hospitals":
        context.user_data["awaiting_schedule_choice"] = False
        context.user_data["awaiting_hospital_choice"] = True
        try:
            await update.message.reply_text(
                "🏥 Select a hospital:",
                reply_markup=HOSPITAL_MENU
            )
        except (TimedOut, NetworkError):
            pass
        return True
        
    return False

async def handle_time_choice(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.user_data.get("awaiting_time_choice"):
        return False

    choice = update.message.text
    selected_hospital = context.user_data.get("selected_hospital")
    
    if choice == "↩ Back":
        context.user_data["awaiting_time_choice"] = False
        context.user_data["awaiting_schedule_choice"] = True
        try:
            await update.message.reply_text(
                "🚕 Would you like to book a cab now or schedule for later?",
                reply_markup=SCHEDULE_MENU
            )
        except (TimedOut, NetworkError):
            pass
        return True
        
    elif choice == "Custom time":
        try:
            await update.message.reply_text(
                "Please enter the time in minutes (e.g., '45' for 45 minutes from now):"
            )
        except (TimedOut, NetworkError):
            pass
        context.user_data["awaiting_custom_time"] = True
        context.user_data["awaiting_time_choice"] = False
        return True
        
    elif choice in ["15 minutes", "30 minutes", "1 hour", "2 hours"]:
        # Parse time delay
        time_map = {
            "15 minutes": 15,
            "30 minutes": 30,
            "1 hour": 60,
            "2 hours": 120
        }
        minutes = time_map[choice]
        await schedule_cab_later(update, context, selected_hospital, minutes)
        return True
        
    return False

async def handle_custom_time(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.user_data.get("awaiting_custom_time"):
        return False
        
    try:
        minutes = int(update.message.text)
        if minutes < 1 or minutes > 1440:  # Max 24 hours
            try:
                await update.message.reply_text("Please enter a time between 1 and 1440 minutes (24 hours).")
            except (TimedOut, NetworkError):
                pass
            return True
            
        selected_hospital = context.user_data.get("selected_hospital")
        await schedule_cab_later(update, context, selected_hospital, minutes)
        return True
        
    except ValueError:
        try:
            await update.message.reply_text("Please enter a valid number of minutes.")
        except (TimedOut, NetworkError):
            pass
        return True

async def book_cab_now(update: Update, context: ContextTypes.DEFAULT_TYPE, hospital: str):
    # Simulate searching for cabs
    thinking_msg = await simulate_thinking(update, "Searching for available cabs near you...", 3.0)
    if not thinking_msg:
        return
    
    # Simulate booking process
    await thinking_msg.edit_text("🔍 Found available cabs! Booking your ride...")
    await asyncio.sleep(2.0)
    
    # Generate realistic driver details
    drivers = [
        {"name": "Ramesh Patil", "phone": "+91 9812345678", "car": "White WagonR", "plate": "MH 02 AB 4455", "eta": "5"},
        {"name": "Suresh Kumar", "phone": "+91 9823456789", "car": "Gray Swift", "plate": "MH 01 CD 5566", "eta": "7"},
        {"name": "Amit Sharma", "phone": "+91 9834567890", "car": "Black Honda City", "plate": "MH 03 EF 6677", "eta": "4"}
    ]
    
    driver = drivers[0]  # Select first driver
    
    await thinking_msg.edit_text("✅ Finalizing booking details...")
    await asyncio.sleep(1.5)
    
    # Send booking confirmation
    try:
        await update.message.reply_text(
            "🎉 *Cab Booked Successfully!*\n\n"
            f"📍 *Destination:* {hospital}\n"
            f"👨‍💼 *Driver:* {driver['name']}\n"
            f"📞 *Phone:* {driver['phone']}\n"
            f"⏱ *ETA:* {driver['eta']} minutes\n"
            f"🚗 *Car:* {driver['car']} ({driver['plate']})\n\n"
            "💰 *Fare Estimate:* ₹250-300\n"
            "📱 You'll receive a confirmation SMS shortly.",
            parse_mode="Markdown"
        )
    except (TimedOut, NetworkError):
        pass

    # Clear hospital selection state
    context.user_data.pop("selected_hospital", None)
    
    try:
        await update.message.reply_text(
            "How else can I assist you?",
            reply_markup=MAIN_MENU
        )
    except (TimedOut, NetworkError):
        pass

async def schedule_cab_later(update: Update, context: ContextTypes.DEFAULT_TYPE, hospital: str, minutes: int):
    # Calculate scheduled time
    scheduled_time = datetime.now() + timedelta(minutes=minutes)
    time_str = scheduled_time.strftime("%I:%M %p")
    
    # Simulate scheduling process
    thinking_msg = await simulate_thinking(update, "Checking cab availability for your requested time...", 2.5)
    if not thinking_msg:
        return
    
    await thinking_msg.edit_text("⏰ Scheduling your cab...")
    await asyncio.sleep(2.0)
    
    # Generate driver details
    drivers = [
        {"name": "Vikram Singh", "phone": "+91 9845678901", "car": "White Dzire", "plate": "MH 04 GH 7788"},
        {"name": "Rajesh Nair", "phone": "+91 9856789012", "car": "Red Etios", "plate": "MH 02 IJ 8899"}
    ]
    
    driver = drivers[0]
    
    await thinking_msg.edit_text("✅ Confirming your scheduled ride...")
    await asyncio.sleep(1.5)
    
    # Send scheduling confirmation
    try:
        await update.message.reply_text(
            "📅 *Cab Scheduled Successfully!*\n\n"
            f"📍 *Destination:* {hospital}\n"
            f"🕐 *Pickup Time:* {time_str} (in {minutes} minutes)\n"
            f"👨‍💼 *Assigned Driver:* {driver['name']}\n"
            f"📞 *Phone:* {driver['phone']}\n"
            f"🚗 *Car:* {driver['car']} ({driver['plate']})\n\n"
            "💰 *Fare Estimate:* ₹280-320\n"
            "⏰ *Reminder:* You'll get a notification 15 minutes before pickup\n"
            "📱 SMS confirmation will be sent shortly",
            parse_mode="Markdown"
        )
    except (TimedOut, NetworkError):
        pass

    # Clear scheduling states
    context.user_data.pop("selected_hospital", None)
    context.user_data.pop("awaiting_custom_time", None)
    
    try:
        await update.message.reply_text(
            "How else can I assist you?",
            reply_markup=MAIN_MENU
        )
    except (TimedOut, NetworkError):
        pass

# -------------------- MEDICINE ORDERING FLOW --------------------
async def handle_medicine_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.user_data.get("awaiting_medicine_choice"):
        return False

    choice = update.message.text

    if choice == "💊 Common Medicines":
        try:
            await update.message.reply_text(
                "💊 Select from common medicines:",
                reply_markup=COMMON_MEDICINES
            )
        except (TimedOut, NetworkError):
            pass
        context.user_data["awaiting_medicine_selection"] = True
        return True

    elif choice == "📝 Prescription Upload":
        try:
            await update.message.reply_text(
                "📸 Please upload a clear photo of your prescription or send it as a document."
            )
        except (TimedOut, NetworkError):
            pass
        context.user_data["awaiting_prescription"] = True
        return True

    elif choice == "🔍 Search Medicines":
        try:
            await update.message.reply_text(
                "🔍 Enter the name of the medicine you're looking for:"
            )
        except (TimedOut, NetworkError):
            pass
        context.user_data["awaiting_medicine_search"] = True
        return True

    elif choice == "↩ Main Menu":
        context.user_data["awaiting_medicine_choice"] = False
        try:
            await update.message.reply_text(
                "👇 Select an option from the main menu:",
                reply_markup=MAIN_MENU
            )
        except (TimedOut, NetworkError):
            pass
        return True

    return False

async def handle_medicine_selection(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.user_data.get("awaiting_medicine_selection"):
        return False

    medicine = update.message.text

    if medicine == "↩ Back to Medicine Menu":
        context.user_data["awaiting_medicine_selection"] = False
        try:
            await update.message.reply_text(
                "💊 How would you like to order medicines?",
                reply_markup=MEDICINE_MENU
            )
        except (TimedOut, NetworkError):
            pass
        return True

    # Store selected medicine
    context.user_data["selected_medicine"] = medicine
    context.user_data["awaiting_medicine_selection"] = False
    context.user_data["awaiting_delivery_choice"] = True

    try:
        await update.message.reply_text(
            f"💊 Selected: *{medicine}*\n\n"
            "🚚 Choose delivery option:",
            parse_mode="Markdown",
            reply_markup=DELIVERY_OPTIONS
        )
    except (TimedOut, NetworkError):
        pass
    return True

async def handle_delivery_choice(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.user_data.get("awaiting_delivery_choice"):
        return False

    choice = update.message.text
    medicine = context.user_data.get("selected_medicine")

    if choice == "↩ Back to Medicines":
        context.user_data["awaiting_delivery_choice"] = False
        context.user_data["awaiting_medicine_selection"] = True
        try:
            await update.message.reply_text(
                "💊 Select from common medicines:",
                reply_markup=COMMON_MEDICINES
            )
        except (TimedOut, NetworkError):
            pass
        return True

    elif choice == "⏰ Schedule Delivery":
        try:
            await update.message.reply_text(
                "⏰ Please enter delivery date and time (e.g., 'Tomorrow 4 PM' or '15 Dec 3:30 PM'):"
            )
        except (TimedOut, NetworkError):
            pass
        context.user_data["awaiting_delivery_schedule"] = True
        return True

    # Process immediate delivery options
    thinking_msg = await simulate_thinking(update, "Checking medicine availability...", 2.0)
    if not thinking_msg:
        return True
    
    await thinking_msg.edit_text("📦 Processing your order...")
    await asyncio.sleep(2.0)

    # Generate pharmacy details
    pharmacies = [
        {"name": "MedPlus Pharmacy", "address": "Near Andheri Station", "phone": "+91 9876543210"},
        {"name": "Apollo Pharmacy", "address": "Lokhandwala Complex", "phone": "+91 9876543211"},
        {"name": "Wellness Forever", "address": "Juhu Scheme", "phone": "+91 9876543212"}
    ]
    
    pharmacy = random.choice(pharmacies)
    
    if choice == "🚚 Express Delivery (2 hours)":
        delivery_time = "2 hours"
        delivery_charge = "₹50"
        total = "₹150"
    else:  # Standard Delivery
        delivery_time = "24 hours" 
        delivery_charge = "₹25"
        total = "₹125"

    await thinking_msg.edit_text("✅ Finalizing your order...")
    await asyncio.sleep(1.5)

    try:
        await update.message.reply_text(
            f"🎉 *Medicine Order Confirmed!*\n\n"
            f"💊 *Medicine:* {medicine}\n"
            f"🏪 *Pharmacy:* {pharmacy['name']}\n"
            f"📍 *Address:* {pharmacy['address']}\n"
            f"📞 *Contact:* {pharmacy['phone']}\n"
            f"⏱ *Delivery Time:* {delivery_time}\n"
            f"💰 *Delivery Charge:* {delivery_charge}\n"
            f"💵 *Total Amount:* {total}\n\n"
            "📱 You'll receive tracking details shortly.",
            parse_mode="Markdown"
        )
    except (TimedOut, NetworkError):
        pass

    # Clear medicine states
    context.user_data.pop("selected_medicine", None)
    context.user_data["awaiting_delivery_choice"] = False
    
    try:
        await update.message.reply_text(
            "How else can I assist you?",
            reply_markup=MAIN_MENU
        )
    except (TimedOut, NetworkError):
        pass
    return True

async def handle_delivery_schedule(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.user_data.get("awaiting_delivery_schedule"):
        return False

    schedule_time = update.message.text
    medicine = context.user_data.get("selected_medicine")

    thinking_msg = await simulate_thinking(update, "Scheduling your delivery...", 2.0)
    if not thinking_msg:
        return True
    
    await thinking_msg.edit_text("📅 Confirming schedule with pharmacy...")
    await asyncio.sleep(2.0)

    pharmacy = {"name": "MedPlus Pharmacy", "address": "Near Andheri Station", "phone": "+91 9876543210"}

    await thinking_msg.edit_text("✅ Delivery scheduled!")
    await asyncio.sleep(1.0)

    try:
        await update.message.reply_text(
            f"📅 *Delivery Scheduled!*\n\n"
            f"💊 *Medicine:* {medicine}\n"
            f"🏪 *Pharmacy:* {pharmacy['name']}\n"
            f"📍 *Address:* {pharmacy['address']}\n"
            f"📞 *Contact:* {pharmacy['phone']}\n"
            f"⏰ *Scheduled For:* {schedule_time}\n"
            f"💰 *Delivery Charge:* ₹40\n"
            f"💵 *Total Amount:* ₹140\n\n"
            "⏰ You'll get a reminder 1 hour before delivery.",
            parse_mode="Markdown"
        )
    except (TimedOut, NetworkError):
        pass

    # Clear states
    context.user_data.pop("selected_medicine", None)
    context.user_data["awaiting_delivery_schedule"] = False
    
    try:
        await update.message.reply_text(
            "How else can I assist you?",
            reply_markup=MAIN_MENU
        )
    except (TimedOut, NetworkError):
        pass
    return True

async def handle_medicine_search(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.user_data.get("awaiting_medicine_search"):
        return False

    search_term = update.message.text

    thinking_msg = await simulate_thinking(update, f"Searching for '{search_term}'...", 2.5)
    if not thinking_msg:
        return True
    
    # Simulate search results
    results = [
        f"{search_term} 500mg - ₹120",
        f"{search_term} 250mg - ₹80", 
        f"{search_term} SR 750mg - ₹180"
    ]

    await thinking_msg.edit_text(f"🔍 Found {len(results)} results for '{search_term}':")
    
    for result in results:
        try:
            await update.message.reply_text(result)
        except (TimedOut, NetworkError):
            pass

    try:
        await update.message.reply_text(
            "💊 Select a medicine to proceed with order:",
            reply_markup=COMMON_MEDICINES
        )
    except (TimedOut, NetworkError):
        pass
    
    context.user_data["awaiting_medicine_search"] = False
    context.user_data["awaiting_medicine_selection"] = True
    return True

# -------------------- APPOINTMENT BOOKING FLOW --------------------
async def handle_appointment_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.user_data.get("awaiting_specialist_choice"):
        return False

    choice = update.message.text

    if choice == "↩ Main Menu":
        context.user_data["awaiting_specialist_choice"] = False
        try:
            await update.message.reply_text(
                "👇 Select an option from the main menu:",
                reply_markup=MAIN_MENU
            )
        except (TimedOut, NetworkError):
            pass
        return True

    if choice in DOCTORS.keys():
        context.user_data["selected_specialist"] = choice
        context.user_data["awaiting_specialist_choice"] = False
        context.user_data["awaiting_doctor_choice"] = True

        doctors_list = "\n".join([f"• {doc}" for doc in DOCTORS[choice]])
        
        try:
            await update.message.reply_text(
                f"🩺 Available {choice}s:\n\n{doctors_list}\n\n"
                "Please select a doctor:",
                reply_markup=ReplyKeyboardMarkup(
                    [[doc] for doc in DOCTORS[choice]] + [["↩ Back to Specialists"]],
                    resize_keyboard=True,
                    one_time_keyboard=True
                )
            )
        except (TimedOut, NetworkError):
            pass
        return True

    return False

async def handle_doctor_choice(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.user_data.get("awaiting_doctor_choice"):
        return False

    choice = update.message.text

    if choice == "↩ Back to Specialists":
        context.user_data["awaiting_doctor_choice"] = False
        context.user_data["awaiting_specialist_choice"] = True
        try:
            await update.message.reply_text(
                "🩺 Select a specialist:",
                reply_markup=APPOINTMENT_MENU
            )
        except (TimedOut, NetworkError):
            pass
        return True

    # Validate doctor choice
    specialist = context.user_data.get("selected_specialist")
    if choice in DOCTORS.get(specialist, []):
        context.user_data["selected_doctor"] = choice
        context.user_data["awaiting_doctor_choice"] = False
        context.user_data["awaiting_time_choice"] = True

        try:
            await update.message.reply_text(
                f"🩺 Selected: *{choice}*\n\n"
                "🕘 Choose available time slot:",
                parse_mode="Markdown",
                reply_markup=TIME_SLOTS
            )
        except (TimedOut, NetworkError):
            pass
        return True

    return False

async def handle_appointment_time(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.user_data.get("awaiting_time_choice"):
        return False

    choice = update.message.text

    if choice == "↩ Back to Specialists":
        context.user_data["awaiting_time_choice"] = False
        context.user_data["awaiting_doctor_choice"] = True
        specialist = context.user_data.get("selected_specialist")
        
        try:
            await update.message.reply_text(
                f"🩺 Available {specialist}s:",
                reply_markup=ReplyKeyboardMarkup(
                    [[doc] for doc in DOCTORS[specialist]] + [["↩ Back to Specialists"]],
                    resize_keyboard=True,
                    one_time_keyboard=True
                )
            )
        except (TimedOut, NetworkError):
            pass
        return True

    # Process appointment booking
    doctor = context.user_data.get("selected_doctor")
    thinking_msg = await simulate_thinking(update, "Checking doctor's availability...", 3.0)
    if not thinking_msg:
        return True
    
    await thinking_msg.edit_text("📅 Confirming your appointment...")
    await asyncio.sleep(2.0)

    # Generate appointment details
    appointment_id = f"APT{random.randint(10000, 99999)}"
    date = (datetime.now() + timedelta(days=random.randint(1, 7))).strftime("%d %b %Y")
    
    await thinking_msg.edit_text("✅ Appointment confirmed!")
    await asyncio.sleep(1.0)

    try:
        await update.message.reply_text(
            f"🎉 *Appointment Booked Successfully!*\n\n"
            f"📋 *Appointment ID:* {appointment_id}\n"
            f"🩺 *Doctor:* {doctor}\n"
            f"📅 *Date:* {date}\n"
            f"🕐 *Time:* {choice}\n"
            f"💰 *Consultation Fee:* ₹500\n\n"
            "📍 *Location:* As per hospital/clinic address\n"
            "⏰ Please arrive 15 minutes early\n"
            "📱 You'll receive a reminder 2 hours before appointment",
            parse_mode="Markdown"
        )
    except (TimedOut, NetworkError):
        pass

    # Clear appointment states
    context.user_data.pop("selected_specialist", None)
    context.user_data.pop("selected_doctor", None)
    context.user_data["awaiting_time_choice"] = False
    
    try:
        await update.message.reply_text(
            "How else can I assist you?",
            reply_markup=MAIN_MENU
        )
    except (TimedOut, NetworkError):
        pass
    return True

# -------------------- MAIN MENU HANDLER --------------------
async def menu_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text

    # Check password state first
    if await handle_password(update, context):
        return

    # Check medicine-related states first
    if await handle_delivery_schedule(update, context):
        return
    if await handle_medicine_search(update, context):
        return
    if await handle_delivery_choice(update, context):
        return
    if await handle_medicine_selection(update, context):
        return
    if await handle_medicine_menu(update, context):
        return

    # Check appointment-related states
    if await handle_appointment_time(update, context):
        return
    if await handle_doctor_choice(update, context):
        return
    if await handle_appointment_menu(update, context):
        return

    # Check hospital-related states
    if await handle_custom_time(update, context):
        return
    if await handle_time_choice(update, context):
        return
    if await handle_schedule_choice(update, context):
        return
    if await handle_hospital_choice(update, context):
        return

    # Main menu options
    if text == "📤 Upload Report":
        # Check if user has verified phone number
        if not context.user_data.get("phone"):
            try:
                await update.message.reply_text(
                    "❌ Please verify your phone number first by using the /start command and sharing your contact."
                )
            except (TimedOut, NetworkError):
                pass
            return
            
        try:
            await update.message.reply_text(
                "📄 Please upload your medical report as a PDF file.\n\n"
                "⚠️ Note: Only PDF files are accepted for report uploads."
            )
        except (TimedOut, NetworkError):
            pass

    elif text == "📁 View Reports":
        await handle_view_reports(update, context)

    elif text == "💬 Chat with Reports":
        await handle_chat_with_reports(update, context)
    elif text == "🍽 Best Food Near Me":
        try:
            await update.message.reply_text("Finding the best food options nearby...")
        except (TimedOut, NetworkError):
            pass

    elif text == "🏥 Get Me to Hospital":
        context.user_data["awaiting_hospital_choice"] = True
        try:
            await update.message.reply_text(
                "Here are the nearest hospitals in Mumbai ⬇️",
                reply_markup=HOSPITAL_MENU
            )
        except (TimedOut, NetworkError):
            pass

    elif text == "📅 Book Appointment":
        context.user_data["awaiting_specialist_choice"] = True
        try:
            await update.message.reply_text(
                "🩺 Select a specialist:",
                reply_markup=APPOINTMENT_MENU
            )
        except (TimedOut, NetworkError):
            pass

    elif text == "💊 Order Medicines":
        context.user_data["awaiting_medicine_choice"] = True
        try:
            await update.message.reply_text(
                "💊 How would you like to order medicines?",
                reply_markup=MEDICINE_MENU
            )
        except (TimedOut, NetworkError):
            pass

    else:
        try:
            await update.message.reply_text(
                "Please choose an option from the menu 👇", reply_markup=MAIN_MENU
            )
        except (TimedOut, NetworkError):
            pass

# -------------------- MAIN APP --------------------
def main():
    BOT_TOKEN = "8540623803:AAHxLwLQx3MPdlV_yAg0RzPcPzqMBFznrvw"

    # Build application with increased timeout
    app = ApplicationBuilder()\
        .token(BOT_TOKEN)\
        .read_timeout(TELEGRAM_TIMEOUT)\
        .write_timeout(TELEGRAM_TIMEOUT)\
        .connect_timeout(TELEGRAM_TIMEOUT)\
        .pool_timeout(TELEGRAM_TIMEOUT)\
        .build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.CONTACT, handle_contact))
    app.add_handler(MessageHandler(filters.Document.PDF, file_handler))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, menu_handler))

    print("Bot running with improved timeout handling...")
    
    try:
        app.run_polling(
            poll_interval=1,
            timeout=TELEGRAM_TIMEOUT,
            drop_pending_updates=True
        )
    except Exception as e:
        logging.error(f"Application error: {e}")
        print(f"Application error: {e}")

if __name__ == "__main__":
    main()