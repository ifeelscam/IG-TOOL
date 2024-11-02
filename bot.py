import requests
from telegram import Bot, Update
from telegram.ext import Updater, CommandHandler, CallbackContext
import schedule
import threading
import time
from datetime import datetime

# Configuration
TELEGRAM_BOT_TOKEN = 'YOUR_TELEGRAM_BOT_TOKEN'
instagram_usernames = {}
monitoring = False

bot = Bot(token=TELEGRAM_BOT_TOKEN)

def check_instagram_account(username, chat_id):
    url = f'https://www.instagram.com/{username}/'
    try:
        response = requests.get(url)
        if response.status_code == 200:
            return True, None  # Account exists
        elif response.status_code == 404:
            return False, "Account does not exist or is private."
    except Exception as e:
        return False, str(e)

def job():
    if monitoring:
        for chat_id, username in instagram_usernames.items():
            account_exists, error_message = check_instagram_account(username, chat_id)
            if not account_exists:
                time_banned = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                bot.send_message(
                    chat_id=chat_id,
                    text=f"Your Instagram account {username} has been banned or is not accessible.\n"
                         f"Reason: {error_message}\n"
                         f"Time of Check: {time_banned}"
                )

def start_monitoring(update: Update, context: CallbackContext):
    global monitoring
    monitoring = True
    welcome_message = (
        "Welcome to the Instagram Account Monitor Bot!\n"
        "Use the command /monitor followed by your Instagram username to start monitoring your account.\n"
        "You will receive notifications if your account is banned or not accessible.\n"
        "Use /stop to stop monitoring."
    )
    update.message.reply_text(welcome_message)

def stop_monitoring(update: Update, context: CallbackContext):
    global monitoring
    monitoring = False
    update.message.reply_text("Monitoring stopped!")

def set_instagram_username(update: Update, context: CallbackContext):
    username = context.args[0] if context.args else None
    if username:
        instagram_usernames[update.message.chat_id] = username
        update.message.reply_text(f'Instagram username {username} set for monitoring.')
    else:
        update.message.reply_text('Please provide an Instagram username.')

def schedule_jobs():
    schedule.every(10).minutes.do(job)
    while True:
        schedule.run_pending()
        time.sleep(1)

def main():
    # Setup Telegram bot
    updater = Updater(TELEGRAM_BOT_TOKEN)
    dispatcher = updater.dispatcher

    # Command handlers
    dispatcher.add_handler(CommandHandler("start", start_monitoring))
    dispatcher.add_handler(CommandHandler("stop", stop_monitoring))
    dispatcher.add_handler(CommandHandler("monitor", set_instagram_username))

    # Start the scheduler in a separate thread
    threading.Thread(target=schedule_jobs, daemon=True).start()

    # Start the bot
    updater.start_polling()
    updater.idle()

if __name__ == '__main__':
    main()
    
