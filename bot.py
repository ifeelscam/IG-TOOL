import sys
import subprocess
import json
import time
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes, ConversationHandler

# Function to check and install required packages
def install(package):
    subprocess.check_call([sys.executable, "-m", "pip", "install", package])

# Check if required modules are installed; if not, attempt to install them
try:
    from telegram import __version__ as TG_VER
    from telegram.ext import __version__ as TG_EXT_VER
    from instabot import Bot
except ImportError:
    print("Installing required packages...")
    install("python-telegram-bot")
    install("instabot")

# Dictionary to store sessions and related information
sessions = []
active_session_index = 0
report_types = {
    "1": "spam",
    "2": "self-harm",
    "3": "drugs",
    "4": "violence",
}

# Function to load accounts from file and confirm login with session ID
async def load_accounts(file_path="login_file.txt", update=None):
    global sessions
    with open(file_path, 'r') as f:
        for line in f:
            username, password = line.strip().split(':')
            bot = Bot()
            try:
                bot.login(username=username, password=password)
                session_id = bot.api.sessionid
                sessions.append(bot)
                await update.message.reply_text(f"✅ Logged in successfully as {username}\nSession ID: {session_id}")
            except Exception as e:
                await update.message.reply_text(f"❌ Login failed for {username}: {str(e)}")

# Define conversation states
LOGIN, REPORT_TYPE, TARGET_USERNAME, REPORT_COUNT, HELP = range(5)

# Start command to initialize the bot
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.message.reply_text(
        "Welcome to the Instagram Moderation Bot!\nPlease upload your login file (format: username:password, one per line)."
    )
    return LOGIN

# Help command to provide information about the bot
async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    help_text = (
        "This bot helps you report Instagram accounts based on various categories.\n"
        "Commands:\n"
        "/start - Start the bot and upload your login file.\n"
        "/help - Show this help message.\n"
        "/cancel - Cancel the current operation."
    )
    await update.message.reply_text(help_text)

# Handle file upload and account login
async def handle_file_upload(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    file = await update.message.document.get_file()
    file.download('login_file.txt')
    await load_accounts("login_file.txt", update)
    await update.message.reply_text(f"Accounts loaded. Total accounts: {len(sessions)}.\nChoose a report type:\n1. Spam\n2. Self-harm\n3. Drugs\n4. Violence")
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
        time.sleep(1)  # Respect Instagram's rate limits with a delay

# Cancel operation
async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.message.reply_text("Operation cancelled.")
    return ConversationHandler.END

# Main function to run the bot
def main():
    application = Application.builder().token("7043515654:AAG-KC190f6tioW4vwpTEBTv3UdDpfDeFGY").build()

    # Conversation handler for the reporting workflow
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler('start', start)],
        states={
            LOGIN: [MessageHandler(filters.Document.FileExtension("txt"), handle_file_upload)],
            REPORT_TYPE: [MessageHandler(filters.TEXT & ~filters.COMMAND, select_report_type)],
            TARGET_USERNAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, set_target_username)],
            REPORT_COUNT: [MessageHandler(filters.TEXT & ~filters.COMMAND, set_report_count)],
        },
        fallbacks=[CommandHandler('cancel', cancel)],
    )

    application.add_handler(conv_handler)
    application.add_handler(CommandHandler('help', help_command))  # Adding help command
    application.run_polling()

if __name__ == "__main__":
    main()
    
