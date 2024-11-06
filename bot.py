import logging
import random
import requests
from flask import Flask, request
from telegram import Update
from telegram.ext import CommandHandler, MessageHandler, Filters, ConversationHandler, CallbackContext
from telegram.ext import Dispatcher
from faker import Faker
from user_agent import generate_user_agent

# Set up logging
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize Faker and Flask app
faker = Faker()
app = Flask(__name__)

# Initialize Telegram Bot
TOKEN = "YOUR_TOKEN"  # Replace with your actual token
bot = telegram.Bot(token=TOKEN)

# Define conversation states
USERNAME, TARGET_NAME = range(2)

@app.route('/' + TOKEN, methods=['POST'])
def webhook() -> str:
    update = Update.de_json(request.get_json(force=True), bot)
    dispatcher.process_update(update)
    return 'ok'

def start(update: Update, context: CallbackContext) -> None:
    update.message.reply_text('Welcome to the Instagram Report Bot! Use /report to start reporting a user.')
    return ConversationHandler.END

def report(update: Update, context: CallbackContext) -> int:
    update.message.reply_text('Please enter the username of the account you want to report:')
    return USERNAME

def get_username(update: Update, context: CallbackContext) -> int:
    context.user_data['username'] = update.message.text
    update.message.reply_text('Please enter the target name of the account:')
    return TARGET_NAME

def get_target_name(update: Update, context: CallbackContext) -> int:
    username = context.user_data['username']
    target_name = update.message.text
    update.message.reply_text(f'Reporting {username} (Target Name: {target_name})...')

    if InstaGramReporter(username, target_name):
        update.message.reply_text('Report submitted successfully!')
    else:
        update.message.reply_text('Failed to submit the report.')

    return ConversationHandler.END

def cancel(update: Update, context: CallbackContext) -> int:
    update.message.reply_text('Report canceled.')
    return ConversationHandler.END

def InstaGramReporter(user: str, target_name: str) -> bool:
    try:
        lsd = ''.join(random.choices('abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789', k=12))
        em = "".join(random.choice('1234567890qwertyuiopasdfghjklzxcvbnm.') for _ in range(10)) + "@gmail.com"
        funame = faker.name()
        url = "https://help.instagram.com/ajax/help/contact/submit/page"
        
        payload = {
            "jazoest": str(random.randint(1000, 9999)),
            "lsd": lsd,
            "radioDescribeSituation": "represent_impersonation",
            "inputFullName": funame,
            "inputEmail": em,
            "Field249579765548460": target_name,
            "inputReportedUsername": user,
        }
        
        headers = {
            'User -Agent': str(generate_user_agent()),
            'Content-Type': "application/x-www-form-urlencoded",
            'Referer': "https://help.instagram.com/contact/636276399721841",
        }
        
        response = requests.post(url, data=payload, headers=headers)
        
        if "The given Instagram user ID is invalid." in response.text:
            logger.info("UsernameNotFound: Available ..!!")
            return False
        elif "We limit how often you can post" in response.text:
            logger.warning("Use VPN: You have got blocked")
            return False
        else:
            logger.info("Done Report")
            return True

    except Exception as e:
        logger.error(f"Error: {e}")
        return False

# Set up the conversation handler
conv_handler = ConversationHandler(
    entry_points=[CommandHandler('report', report)],
    states={
        USERNAME: [MessageHandler(Filters.text & ~Filters.command, get_username)],
        TARGET_NAME: [MessageHandler(Filters.text & ~Filters.command, get_target_name)],
    },
    fallbacks=[CommandHandler('cancel', cancel)]
)

dispatcher = Dispatcher(bot, None)
dispatcher.add_handler(CommandHandler("start", start))
dispatcher.add_handler(conv_handler)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
