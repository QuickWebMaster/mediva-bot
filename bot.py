import logging
import asyncio
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, CallbackContext, MessageHandler, filters, CallbackQueryHandler
import openai
from apscheduler.schedulers.asyncio import AsyncIOScheduler
import os
from dotenv import load_dotenv
from data import services  # Импортируем услуги из data.py

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

# Контактная информация клиники
contact_info = {
    "address": "Республика Узбекистан, город Ташкент, улица Асия 26Б",
    "phone": "+998 (97) 534-44-95",
    "website": "http://medivaclinic.net"
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
    
    logging.info(f"Received message: {user_input}")
    
    if "цена" in user_input or "стоимость" in user_input:
        for service, price in services.items():
            if service in user_input:
                await update.message.reply_text(f"{service.capitalize()} стоит {price}.")
                logging.info(f"Sent price info for {service}")
                await asyncio.sleep(30)
                await update.message.reply_text("Могу Вас записать на прием или консультацию?")
                context.user_data['awaiting_appointment'] = True
                return

    await update.message.reply_text("Прошу прощения, я не могу помочь с этим запросом. Пожалуйста, свяжитесь с администрацией клиники для более подробной информации.")
    logging.info(f"Sent default response")

async def handle_appointment(update: Update, context: CallbackContext) -> None:
    if context.user_data.get('awaiting_appointment'):
        user_input = update.message.text.strip().lower()
        if any(confirm in user_input for confirm in ["да", "хорошо", "конечно"]):
            await update.message.reply_text("Пожалуйста, предоставьте ваше Ф.И.О, номер телефона и удобные даты и время для записи.")
            context.user_data['awaiting_details'] = True
            context.user_data['awaiting_appointment'] = False
            return
    elif context.user_data.get('awaiting_details'):
        context.user_data['appointment_details'] = user_input
        # здесь вы можете добавить логику для отправки данных администратору
        await update.message.reply_text("Ваши данные переданы администратору. Спасибо!")
        context.user_data['awaiting_details'] = False
    else:
        await handle_message(update, context)

# Обработка ошибок
async def error_handler(update: Update, context: CallbackContext) -> None:
    logging.error(msg="Exception while handling an update:", exc_info=context.error)
    await context.bot.send_message(chat_id=update.effective_chat.id, text="Произошла ошибка, попробуйте позже.")

# Запуск бота
if __name__ == "__main__":
    logging.info("Запуск приложения...")
    application = ApplicationBuilder().token(TELEGRAM_BOT_TOKEN).build()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(CallbackQueryHandler(set_language, pattern='^lang_'))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_appointment))
    application.add_error_handler(error_handler)

    logging.info("Бот запущен, ожидание сообщений...")
    application.run_polling()

