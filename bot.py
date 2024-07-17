import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes, MessageHandler, filters, CallbackQueryHandler
import openai
from apscheduler.schedulers.asyncio import AsyncIOScheduler
import os
from dotenv import load_dotenv
from data import services  # Импортируем данные из data.py

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

# Приветственное сообщение
WELCOME_MESSAGES = {
    "ru": "Привет! Я — искусственный интеллект Медива. Чем могу помочь?",
    "uz": "Salom! Men Mediva sun'iy intellektiman. Sizga qanday yordam bera olaman?",
    "en": "Hello! I am the Mediva AI. How can I assist you?"
}

# Установка языка
async def set_language(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    language_code = query.data.split('_')[-1]
    context.user_data['language'] = language_code
    await query.edit_message_text(WELCOME_MESSAGES[language_code])

# Ответ на команды
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    keyboard = [
        [InlineKeyboardButton("Русский", callback_data='lang_ru')],
        [InlineKeyboardButton("Узбек", callback_data='lang_uz')],
        [InlineKeyboardButton("English", callback_data='lang_en')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text("Выберите язык / Choose a language:", reply_markup=reply_markup)

# Функция для поиска услуги и цены
def find_service(service_name):
    results = []
    for category, items in services.items():
        if service_name.lower() in category.lower():
            for service, price in items.items():
                results.append(f"{service}: {price}")
        elif any(service_name.lower() in service.lower() for service in items):
            for service, price in items.items():
                if service_name.lower() in service.lower():
                    results.append(f"{service}: {price}")
    return results

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_input = update.message.text.strip().lower()
    user_language = context.user_data.get('language', 'ru')

    # Поиск услуги в данных
    service_info = find_service(user_input)
    if service_info:
        response_text = "\n".join(service_info)
    else:
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
        except Exception as e:
            logger.error(f"Error with OpenAI API: {e}")
            response_text = "Произошла ошибка при обработке вашего запроса. Пожалуйста, попробуйте позже."

    await update.message.reply_text(response_text)

# Обработка ошибок
async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    logger.error(msg="Exception while handling an update:", exc_info=context.error)
    try:
        if update and update.effective_chat:
            await context.bot.send_message(chat_id=update.effective_chat.id, text="Произошла ошибка, попробуйте позже.")
    except Exception as e:
        logger.error(f"Error while sending error message: {e}")

# Запуск бота
if __name__ == "__main__":
    logger.info("Запуск приложения...")
    application = ApplicationBuilder().token(TELEGRAM_BOT_TOKEN).build()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(CallbackQueryHandler(set_language, pattern='^lang_'))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    application.add_error_handler(error_handler)

    logger.info("Бот запущен, ожидание сообщений...")
    application.run_polling()






