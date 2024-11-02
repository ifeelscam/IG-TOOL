from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes, ConversationHandler
from instabot import Bot
import asyncio
from aiohttp import web
import time
import json
import os

# Define conversation states
LOGIN, REPORT_TYPE, TARGET_USERNAME, REPORT_COUNT, MANUAL_LOGIN_USERNAME, MANUAL_LOGIN_PASSWORD = range(6)

# Dictionary to store sessions
sessions = []
active_session_index = 0
report_types = {
    "1": "spam",
    "2": "self-harm",
    "3": "drugs",
    "4": "violence",
}

# Set maximum login attempts
MAX_LOGIN_ATTEMPTS = 5
CREDENTIALS_FILE = "credentials.json"

# Load saved credentials from a JSON file
def load_credentials():
    if os.path.exists(CREDENTIALS_FILE):
        with open(CREDENTIALS_FILE, 'r') as f:
            return json.load(f)
    return {}

# Save new credentials to a JSON file
def save_credentials(username, password):
    credentials = load_credentials()
    credentials[username] = password
    with open(CREDENTIALS_FILE, 'w') as f:
        json.dump(credentials, f)

# Start command to initialize the bot
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.message.reply_text(
        "Welcome to the Instagram Moderation Bot!\nUse /login to enter your credentials or /fastlogin for quick login."
    )
    return ConversationHandler.END

# Handle login command
async def login(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    if sessions:
        await update.message.reply_text("You are already logged in. Use /switch to change accounts.")
        return ConversationHandler.END
    
    await update.message.reply_text("Please enter your Instagram username:")
    return MANUAL_LOGIN_USERNAME

# Fast login command
async def fast_login(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    credentials = load_credentials()
    if not credentials:
        await update.message.reply_text("No saved credentials found. Please log in first using /login.")
        return ConversationHandler.END
    
    await update.message.reply_text("Select your account to log in quickly:")
    for username in credentials.keys():
        await update.message.reply_text(username)

    return MANUAL_LOGIN_USERNAME  # Expecting a username from the user

# Set username for manual login
async def set_manual_login_username(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    username = update.message.text
    context.user_data['username'] = username

    # Check if using fast login
    credentials = load_credentials()
    if username in credentials:
        context.user_data['password'] = credentials[username]
        await update.message.reply_text(f"Using saved password for {username}. Logging in...")
        return await set_manual_login_password(update, context)
    
    await update.message.reply_text("Please enter your Instagram password:")
    return MANUAL_LOGIN_PASSWORD

# Set password for manual login and confirm login
async def set_manual_login_password(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    username = context.user_data.get('username')
    password = context.user_data.get('password', update.message.text)  # Get password from saved if fast login

    bot = Bot()
    
    for attempt in range(MAX_LOGIN_ATTEMPTS):
        try:
            bot.login(username=username, password=password)
            session_id = bot.api.sessionid
            sessions.append(bot)
            await update.message.reply_text(f"✅ Logged in successfully as {username}\nSession ID: {session_id}")

            # Ask if user wants to save credentials
            await update.message.reply_text("Do you want to save your credentials for faster login? (yes/no)")
            return LOGIN  # Expecting a yes/no response
        except Exception as e:
            if "429" in str(e):
                wait_time = (attempt + 1) * 5  # Wait longer with each attempt
                await update.message.reply_text(f"❌ Too many requests. Waiting for {wait_time} seconds...")
                time.sleep(wait_time)  # Sleep before retrying
            else:
                await update.message.reply_text(f"❌ Login failed for {username}: {str(e)}")
                return ConversationHandler.END

    await update.message.reply_text("❌ Maximum login attempts reached. Please try again later.")
    return ConversationHandler.END

# Save credentials if user agrees
async def save_user_credentials(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    if update.message.text.lower() == 'yes':
        username = context.user_data.get('username')
        password = context.user_data.get('password')
        save_credentials(username, password)
        await update.message.reply_text("✅ Credentials saved successfully!")
    else:
        await update.message.reply_text("❌ Credentials not saved.")
    
    await update.message.reply_text("Choose a report type:\n1. Spam\n2. Self-harm\n3. Drugs\n4. Violence")
    return REPORT_TYPE

# Select report type
async def select_report_type(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    choice = update.message.text
    if choice in report_types:
        context.user_data['report_type'] = report_types[choice]
        await update.message.reply_text("Enter the target Instagram username:")
        return TARGET_USERNAME
    else:
        await update.message.reply_text("Invalid choice. Please select a valid report type.")
        return REPORT_TYPE

# Set target username
async def set_target_username(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data['target_username'] = update.message.text
    await update.message.reply_text("How many reports would you like to send?")
    return REPORT_COUNT

# Set report count and start reporting
async def set_report_count(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    try:
        count = int(update.message.text)
        context.user_data['report_count'] = count
        await update.message.reply_text("Starting the reporting process...")
        await send_reports(context.user_data['target_username'], context.user_data['report_type'], count, update)
        await update.message.reply_text("Reporting complete.")
        return ConversationHandler.END
    except ValueError:
        await update.message.reply_text("Please enter a valid number.")
        return REPORT_COUNT

# Function for rotating accounts and sending reports
async def send_reports(target_username, report_type, count, update: Update):
    global active_session_index
    for i in range(count):
        session = sessions[active_session_index]
        try:
            session.report(target_username, report_type)
            await update.message.reply_text(f"Report {i+1}/{count} sent using account {session.username}")
        except Exception as e:
            await update.message.reply_text(f"Failed to report with account {session.username}: {str(e)}")
        
        active_session_index = (active_session_index + 1) % len(sessions)
        await asyncio.sleep(1)  # Respect Instagram's rate limits with a delay

# Cancel operation
async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.message.reply_text("Operation cancelled.")
    return ConversationHandler.END

# Dummy aiohttp server handler
async def handle(request):
    return web.Response(text="This is a dummy server running on port 8080.")

# Start the aiohttp server
async def start_aiohttp_server():
    app = web.Application()
    app.router.add_get('/', handle)
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", 8080)
    await site.start()
    print("Serving aiohttp on port 8080")

# Main function to set up the bot
def main():
    application = Application.builder().token("7043515654:AAG-KC190f6tioW4vwpTEBTv3UdDpfDeFGY").build()

    # Add handlers
    application.add_handler(CommandHandler('start', start))
    application.add_handler(CommandHandler('login', login))
    application.add_handler(CommandHandler('fastlogin', fast_login))

    # Conversation handler with states for login, report type selection, etc.
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler('login', login), CommandHandler('fastlogin', fast_login)],
        states={
            MANUAL_LOGIN_USERNAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, set_manual_login_username)],
            MANUAL_LOGIN_PASSWORD: [MessageHandler(filters.TEXT & ~filters.COMMAND, set_manual_login_password)],
            LOGIN: [MessageHandler(filters.TEXT & ~filters.COMMAND, save_user_credentials)],
            REPORT_TYPE: [MessageHandler(filters.TEXT & ~filters.COMMAND, select_report_type)],
            TARGET_USERNAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, set_target_username)],
            REPORT_COUNT: [MessageHandler(filters.TEXT & ~filters.COMMAND, set_report_count)],
        },
        fallbacks=[CommandHandler('cancel', cancel)],
    )

    application.add_handler(conv_handler)

    # Run aiohttp server in an asyncio event loop
    asyncio.get_event_loop().create_task(start_aiohttp_server())
    
    # Run the bot with polling
    application.run_polling()

if __name__ == "__main__":
    main()
    
