import logging
import asyncio
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, CallbackContext, MessageHandler, filters, CallbackQueryHandler
import openai
import os
from dotenv import load_dotenv

# Загрузка переменных окружения из файла .env
load_dotenv()

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

logger = logging.getLogger(__name__)

# Получение API ключей из переменных окружения
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

if not TELEGRAM_BOT_TOKEN or not OPENAI_API_KEY:
    raise ValueError("Не установлены переменные окружения TELEGRAM_BOT_TOKEN или OPENAI_API_KEY")

openai.api_key = OPENAI_API_KEY

# Контактная информация клиники
CONTACT_INFO = {
    "address": "Республика Узбекистан, город Ташкент, улица Асия 26Б",
    "phone": "+998 (97) 534-44-95",
    "website": "http://medivaclinic.net"
}

# Словарь с языками
LANGUAGES = {
    "ru": "Русский",
    "uz": "Узбек",
    "en": "English"
}

# Приветственное сообщение
WELCOME_MESSAGES = {
    "ru": "Привет! Я — искусственный интеллект Медива. Чем могу помочь?",
    "uz": "Salom! Men Mediva sun'iy intellektiman. Sizga qanday yordam bera olaman?",
    "en": "Hello! I am the Mediva AI. How can I assist you?"
}

# Установка языка
async def set_language(update: Update, context: CallbackContext) -> None:
    query = update.callback_query
    language_code = query.data.split('_')[-1]
    context.user_data['language'] = language_code
    await query.edit_message_text(WELCOME_MESSAGES[language_code])

# Ответ на команды
async def start(update: Update, context: CallbackContext) -> None:
    logger.info("Получена команда /start")
    keyboard = [
        [InlineKeyboardButton("Русский", callback_data='lang_ru')],
        [InlineKeyboardButton("Узбек", callback_data='lang_uz')],
        [InlineKeyboardButton("English", callback_data='lang_en')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text("Выберите язык / Choose a language:", reply_markup=reply_markup)

async def handle_message(update: Update, context: CallbackContext) -> None:
    user_input = update.message.text.strip().lower()
    user_language = context.user_data.get('language', 'ru')

    logger.info(f"Получено сообщение: {user_input} на языке: {user_language}")

    try:
        response = openai.ChatCompletion.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": "You are a helpful assistant."},
                {"role": "user", "content": user_input}
            ],
            max_tokens=1000,
            temperature=0.5
        )

        response_text = response['choices'][0]['message']['content'].strip()
        logger.info(f"Ответ от OpenAI: {response_text}")
        await update.message.reply_text(response_text)
    except Exception as e:
        logger.error(f"Ошибка при обращении к OpenAI API: {e}")
        await update.message.reply_text("Произошла ошибка при обработке вашего запроса. Пожалуйста, попробуйте позже.")

# Обработка ошибок
async def error_handler(update: Update, context: CallbackContext) -> None:
    logger.error(msg="Exception while handling an update:", exc_info=context.error)
    await context.bot.send_message(chat_id=update.effective_chat.id, text="Произошла ошибка, попробуйте позже.")

async def main():
    logger.info("Запуск приложения...")
    try:
        application = ApplicationBuilder().token(TELEGRAM_BOT_TOKEN).build()

        application.add_handler(CommandHandler("start", start))
        application.add_handler(CallbackQueryHandler(set_language, pattern='^lang_'))
        application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
        application.add_error_handler(error_handler)

        logger.info("Бот запущен, ожидание сообщений...")
        await application.start()
        await application.updater.start_polling()
        await application.updater.idle()
    except Exception as e:
        logger.error(f"Ошибка при запуске приложения: {e}")

if __name__ == "__main__":
    asyncio.run(main())

