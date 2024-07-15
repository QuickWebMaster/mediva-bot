import logging
import asyncio
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, CallbackContext, MessageHandler, filters, CallbackQueryHandler
import openai
from datetime import datetime, timedelta
from apscheduler.schedulers.asyncio import AsyncIOScheduler
import os
from dotenv import load_dotenv
from data import prices, contact_info

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
ADMIN_CHAT_ID = os.getenv("ADMIN_CHAT_ID")

if not TELEGRAM_BOT_TOKEN or not OPENAI_API_KEY or not ADMIN_CHAT_ID:
    raise ValueError("Не установлены переменные окружения TELEGRAM_BOT_TOKEN, OPENAI_API_KEY или ADMIN_CHAT_ID")

openai.api_key = OPENAI_API_KEY

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
    
    if "цена" in user_input or "стоимость" in user_input:
        for service, price in prices.items():
            if service in user_input:
                await update.message.reply_text(f"{service.capitalize()} стоит {price}.")
                await asyncio.sleep(30)
                await update.message.reply_text("Могу Вас записать на прием или консультацию?")
                context.user_data['awaiting_appointment'] = True
                return

    response = openai.ChatCompletion.create(
        model="gpt-4o",
        messages=[
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": user_input}
        ],
        max_tokens=1000,
        temperature=0.5
    )

    await update.message.reply_text(response['choices'][0]['message']['content'].strip())

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
        admin_chat_id = ADMIN_CHAT_ID
        await context.bot.send_message(chat_id=admin_chat_id, text=f"Новая запись на прием: {user_input}")
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






