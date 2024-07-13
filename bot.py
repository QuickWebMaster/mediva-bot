import logging
import os

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, CallbackContext, MessageHandler, filters, CallbackQueryHandler
import openai
from datetime import datetime, timedelta
from data import services

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

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
    "ru": "Я - искусственный интеллект клиники Медива. Моя задача - предоставлять информацию о предоставляемых услугах и ценах, помочь с записью на прием, отвечать на вопросы об услугах и процедурах, а также предоставлять другую полезную информацию о нашей клинике.",
    "uz": "Men Mediva klinikasining sun'iy intellektiman. Mening vazifam - taqdim etilayotgan xizmatlar va narxlar haqida ma'lumot berish, qabulga yozilishda yordam berish, xizmatlar va protseduralar haqida savollarga javob berish, shuningdek, bizning klinikamiz haqida boshqa foydali ma'lumotlarni taqdim etish.",
    "en": "I am the artificial intelligence of the Mediva Clinic. My task is to provide information about the services and prices, help with making appointments, answer questions about services and procedures, and also provide other useful information about our clinic."
}

# Установка языка
async def set_language(update: Update, context: CallbackContext) -> None:
    query = update.callback_query
    language_code = query.data.split('_')[-1]
    context.user_data['language'] = language_code
    await query.edit_message_text(WELCOME_MESSAGES[language_code])

# Ответ на команду /start
async def start(update: Update, context: CallbackContext) -> None:
    keyboard = [
        [InlineKeyboardButton("Русский", callback_data='lang_ru')],
        [InlineKeyboardButton("Ўзбек", callback_data='lang_uz')],
        [InlineKeyboardButton("English", callback_data='lang_en')],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text("Выберите язык / Choose a language:", reply_markup=reply_markup)

# Обработка сообщений
async def handle_message(update: Update, context: CallbackContext) -> None:
    user_input = update.message.text.strip().lower()
    user_language = context.user_data.get('language', 'ru')
    response = openai.Completion.create(
        model="gpt-4",
        prompt=user_input,
        max_tokens=1000,
        n=1,
        stop=None,
        temperature=0.5
    )
    await update.message.reply_text(response.choices[0].text.strip())

# Обработка ошибок
async def error_handler(update: Update, context: CallbackContext) -> None:
    logging.error(msg="Exception while handling an update:", exc_info=context.error)
    if update and update.effective_chat:
        await context.bot.send_message(chat_id=update.effective_chat.id, text="Произошла ошибка, попробуйте позже.")
    else:
        logging.error("Update or update.effective_chat is None")

# Запуск бота
if __name__ == "__main__":
    application = ApplicationBuilder().token(TELEGRAM_BOT_TOKEN).build()
    
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CallbackQueryHandler(set_language, pattern='^lang_'))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    application.add_error_handler(error_handler)
    
    application.run_polling()



