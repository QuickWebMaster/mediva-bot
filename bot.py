import os
import logging
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters

# Включаем логирование
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                    level=logging.INFO)
logger = logging.getLogger(__name__)

# Определяем команды
def start(update, context):
    update.message.reply_text('Привет! Я бот Mediva.')

def help_command(update, context):
    update.message.reply_text('Помощь!')

def echo(update, context):
    update.message.reply_text(update.message.text)

def main():
    # Получаем токен из переменных окружения
    token = os.getenv("TELEGRAM_BOT_TOKEN")
    if not token:
        raise ValueError("No TELEGRAM_BOT_TOKEN provided")

    updater = Updater(token, use_context=True)
    dp = updater.dispatcher

    dp.add_handler(CommandHandler("start", start))
    dp.add_handler(CommandHandler("help", help_command))
    dp.add_handler(MessageHandler(Filters.text & ~Filters.command, echo))

    updater.start_polling()
    updater.idle()

if __name__ == '__main__':
    main()







