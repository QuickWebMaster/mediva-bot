import logging
import os
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, ContextTypes, filters
import openai
from dotenv import load_dotenv
from data import services

# Загрузка переменных окружения
load_dotenv()

# Настройка логирования
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

# Получение API ключей
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

if not TELEGRAM_BOT_TOKEN or not OPENAI_API_KEY:
    raise ValueError("Не установлены переменные окружения TELEGRAM_BOT_TOKEN или OPENAI_API_KEY")

openai.api_key = OPENAI_API_KEY

# Приветственные сообщения
WELCOME_MESSAGES = {
    "ru": "Привет! Я — искусственный интеллект клиники МЕДИВА. Чем могу помочь?",
    "uz": "Salom! Men MEDIVA klinikasining sun'iy intellektiman. Sizga qanday yordam bera olaman?",
    "en": "Hello! I am the MEDIVA clinic AI. How can I assist you?"
}

# Функция для поиска услуги и цены
def find_service(service_name):
    results = []
    for category, items in services.items():
        for service, price in items.items():
            if isinstance(price, dict):
                for sub_service, sub_price in price.items():
                    if service_name.lower() in sub_service.lower():
                        results.append(f"{sub_service}: {sub_price}")
            else:
                if service_name.lower() in service.lower():
                    results.append(f"{service}: {price}")
    return results

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    keyboard = [
        [InlineKeyboardButton("Русский", callback_data='lang_ru')],
        [InlineKeyboardButton("O'zbek", callback_data='lang_uz')],
        [InlineKeyboardButton("English", callback_data='lang_en')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text("Выберите язык / Tilni tanlang / Choose a language:", reply_markup=reply_markup)

async def set_language(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    language_code = query.data.split('_')[-1]
    context.user_data['language'] = language_code
    await query.edit_message_text(WELCOME_MESSAGES[language_code])

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_input = update.message.text.strip()
    user_language = context.user_data.get('language', 'ru')

    logger.info(f"Received message: {user_input} in language: {user_language}")

    # Поиск услуги в данных
    service_info = find_service(user_input)
    if service_info:
        response_text = "\n".join(service_info)
    else:
        try:
            response = openai.ChatCompletion.create(
                model="gpt-4o",
                messages=[
                    {"role": "system", "content": f"You are a helpful assistant for MEDIVA clinic, providing information about medical services and their prices. Respond in {user_language}."},
                    {"role": "user", "content": user_input}
                ],
                max_tokens=1000,
                temperature=0.7
            )
            response_text = response['choices'][0]['message']['content'].strip()
        except openai.error.InvalidRequestError as e:
            logger.error(f"OpenAI API error: {e}")
            response_text = "Произошла ошибка при обращении к OpenAI API. Пожалуйста, попробуйте позже."
        except Exception as e:
            logger.error(f"Unexpected error: {e}")
            response_text = "Произошла ошибка при обработке запроса. Пожалуйста, попробуйте позже."

    logger.info(f"Response: {response_text}")
    await update.message.reply_text(response_text)

async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    logger.error("Exception while handling an update:", exc_info=context.error)
    await update.message.reply_text("Произошла ошибка при обработке запроса. Пожалуйста, попробуйте позже.")

def main() -> None:
    application = Application.builder().token(TELEGRAM_BOT_TOKEN).build()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(CallbackQueryHandler(set_language, pattern='^lang_'))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    application.add_error_handler(error_handler)

    logger.info("Starting bot...")
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == '__main__':
    main()








