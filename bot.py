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
    context.user_data[update.effective_chat.id] = language_code
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
        for service, price in items.items():
            if service_name.lower() in service.lower():
                results.append(f"{service}: {price}")
    return results

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_input = update.message.text.strip().lower()
    user_language = context.user_data.get(update.effective_chat.id, 'ru')

    logging.info(f"Received message: {user_input} from user: {update.effective_chat.id} in language: {user_language}")

    # Поиск услуги в данных
    service_info = find_service(user_input)
    if service_info:
        response_text = "\n".join(service_info)
    else:
        try:
            response = openai.ChatCompletion.create(
                model="gpt-4o",
                messages=[
                    {"role": "system", "content": "You are a helpful assistant for a clinic, providing information about medical services and their prices."},
                    {"role": "user", "content": user_input}
                ],
                max_tokens=1000,
                temperature=0.5
            )
            response_text = response['choices'][0]['message']['content'].strip()
        except openai.error.InvalidRequestError as e:
            logging.error(f"OpenAI API error: {e}")
            response_text = "Произошла ошибка при обращении к OpenAI API. Пожалуйста, попробуйте позже."

    logging.info(f"Response to user {update.effective_chat.id}: {response_text}")
    await update.message.reply_text(response_text)

# Обработка ошибок
async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    logging.error(msg="Exception while handling an update:", exc_info=context.error)
    await context.bot.send_message(chat_id=update.effective_chat.id, text="Произошла ошибка, попробуйте позже.")

# Настройка планировщика
scheduler = AsyncIOScheduler()

def job():
    logging.info("Scheduled job executed")

scheduler.add_job(job, 'interval', minutes=60)
scheduler.start()

# Запуск бота
if __name__ == "__main__":
    logging.info("Запуск приложения...")
    application = ApplicationBuilder().token(TELEGRAM_BOT_TOKEN).build()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(CallbackQueryHandler(set_language, pattern='^lang_'))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    application.add_error_handler(error_handler)

    logging.info("Бот запущен, ожидание сообщений...")
    application.run_polling()








