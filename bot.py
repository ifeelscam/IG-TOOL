import os
import asyncio
from telegram import Update, Document
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes, ConversationHandler
from instabot import Bot
import time
from aiohttp import web

LOGIN, REPORT_TYPE, TARGET_USERNAME, REPORT_COUNT = range(4)

sessions = []
active_session_index = 0
report_types = {
    "1": "spam",
    "2": "self-harm",
    "3": "drugs",
    "4": "violence",
}

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.message.reply_text(
        "Welcome to the Instagram Moderation Bot!\nPlease upload your login file (format: username:password, one per line)."
    )
    return LOGIN

async def handle_file_upload(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    if update.message.document:
        file = await update.message.document.get_file()
        file_path = 'login_file.txt'
        await file.download(file_path)
        
        await update.message.reply_text("Login file received. Processing logins...")
        
        await load_accounts(file_path, update)
        
        await update.message.reply_text(
            f"Accounts loaded. Total accounts: {len(sessions)}.\nChoose a report type:\n1. Spam\n2. Self-harm\n3. Drugs\n4. Violence"
        )
        return REPORT_TYPE
    else:
        await update.message.reply_text("Please upload a valid login file.")
        return LOGIN

async def load_accounts(file_path, update):
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

async def select_report_type(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    choice = update.message.text
    if choice in report_types:
        context.user_data['report_type'] = report_types[choice]
        await update.message.reply_text("Enter the target Instagram username:")
        return TARGET_USERNAME
    else:
        await update.message.reply_text("Invalid choice. Please select a valid report type.")
        return REPORT_TYPE

async def set_target_username(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data['target_username'] = update.message.text
    await update.message.reply_text("How many reports would you like to send?")
    return REPORT_COUNT

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
        time.sleep(1)

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.message.reply_text("Operation cancelled.")
    return ConversationHandler.END

async def main():
    application = Application.builder().token("7043515654:AAG-KC190f6tioW4vwpTEBTv3UdDpfDeFGY").build()
    
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

    await application.initialize()  # Initialize the application
    await application.start()        # Start the bot

    async def handle_health_check(request):
        return web.Response(text="Bot is running!")

    app = web.Application()
    app.router.add_get("/", handle_health_check)

    port = int(os.getenv("PORT", 8080))
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, '0.0.0.0', port)
    await site.start()

    await application.idle()

if __name__ == "__main__":
    asyncio.run(main())
