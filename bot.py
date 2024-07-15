import logging
import os
from telegram import Update, ForceReply
from telegram.ext import Application, CommandHandler, MessageHandler, filters, CallbackContext
import openai

# Получение ключей из переменных окружения
openai.api_key = os.getenv('OPENAI_API_KEY')
telegram_token = os.getenv('TELEGRAM_TOKEN')

# Enable logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Define a few command handlers. These usually take the two arguments update and context.
def start(update: Update, context: CallbackContext) -> None:
    """Send a message when the command /start is issued."""
    user = update.effective_user
    logger.info(f"Received /start command from user {user.id}")
    update.message.reply_markdown_v2(
        fr'Hi {user.mention_markdown_v2()}\!',
        reply_markup=ForceReply(selective=True),
    )

def help_command(update: Update, context: CallbackContext) -> None:
    """Send a message when the command /help is issued."""
    user = update.effective_user
    logger.info(f"Received /help command from user {user.id}")
    update.message.reply_text('Help!')

def handle_message(update: Update, context: CallbackContext) -> None:
    """Echo the user message."""
    user = update.effective_user
    user_message = update.message.text
    logger.info(f"Received message from user {user.id}: {user_message}")
    try:
        response = openai.Completion.create(
            engine="gpt-4o",
            prompt=user_message,
            max_tokens=1000
        )
        response_text = response.choices[0].text.strip()
        logger.info(f"OpenAI response for user {user.id}: {response_text}")
        update.message.reply_text(response_text)
    except Exception as e:
        logger.error(f"Error in OpenAI API call for user {user.id}: {e}")
        update.message.reply_text("Sorry, something went wrong with the AI response.")

def main() -> None:
    """Start the bot."""
    # Create the Application and pass it your bot's token.
    application = Application.builder().token(telegram_token).build()

    # on different commands - answer in Telegram
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))

    # on non command i.e message - echo the message on Telegram
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    # Start the Bot
    logger.info("Starting the bot...")
    application.run_polling()

if __name__ == '__main__':
    main()
