import logging
import random
import requests
import time
from telegram import Update
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters, CallbackContext
from faker import Faker
from user_agent import generate_user_agent

# Set up logging
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize Faker
faker = Faker()

def start(update: Update, context: CallbackContext) -> None:
    update.message.reply_text('Welcome to the Instagram Report Bot! Please use /report <username> <name> to report a user.')

def report(update: Update, context: CallbackContext) -> None:
    if len(context.args) != 2:
        update.message.reply_text('Usage: /report <username> <name>')
        return

    user = context.args[0]
    target_name = context.args[1]
    
    update.message.reply_text(f'Reporting {user} (Target Name: {target_name})...')
    
    if InstaGramReporter(user, target_name):
        update.message.reply_text('Report submitted successfully!')
    else:
        update.message.reply_text('Failed to submit the report.')

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
            # Add other required fields here...
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

def main() -> None:
    # Replace 'YOUR_TOKEN' with your bot's token
    updater = Updater("YOUR_TOKEN")

    dispatcher = updater.dispatcher

    dispatcher.add_handler(CommandHandler("start", start))
    dispatcher.add_handler(CommandHandler("report", report))

    # Start the Bot
    updater.start_polling()
    updater.idle()

if __name__ == '__main__':
    main()
