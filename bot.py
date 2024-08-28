import logging
import os
from flask import Flask, request, jsonify
from telegram import Update, Bot
from telegram.ext import Application, CommandHandler, MessageHandler, filters, CallbackContext
import openai
from datetime import datetime, timedelta
from data import services
from dotenv import load_dotenv
import requests

# Загрузка переменных окружения
load_dotenv()

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

# Ваши API ключи из .env файла
TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')
ZAPIER_WEBHOOK_URL = os.getenv('ZAPIER_WEBHOOK_URL')

openai.api_key = OPENAI_API_KEY

# Инициализация Flask приложения
app = Flask(__name__)

# Контактная информация клиники
CONTACT_INFO = {
    "address": "Республика Узбекистан, город Ташкент, улица Аския 26Б",
    "phone": "+998(71) 253-84-44, +998(97)554-44-55",
    "email": "info@mediva.uz",
    "website": "https://medivaclinic.net/"
}

# Словарь с языками
LANGUAGES = {
    "ru": "Русский",
    "uz": "Uzbek",
    "en": "English"
}

# Информация о врачах
DOCTORS = {
    "dermatologists": [
        "Рахматова Дина Валерьевна",
        "Ухватова Ирина Васильевна",
        "Квон Инна Трофимовна",
        "Хасаншина Тамилла Леннаровна",
        "Шаякубова Джамиля Ялкиновна",
        "Гиязова Насиба Исламовна"
    ],
    "dentists": [
        "Амиров Нодир Кудратуллаевич",
        "Ташкенбаева Индира Улугбековна"
    ],
    "recommended": {
        "dermatologists": [
            "Рахматова Дина Валерьевна",
            "Ухватова Ирина Васильевна",
            "Квон Инна Трофимовна"
        ],
        "dentists": [
            "Амиров Нодир Кудратуллаевич",
            "Ташкенбаева Индира Улугбековна"
        ]
    }
}

# Приветственное сообщение
WELCOME_MESSAGES = {
    "ru": "Я — искусственный интеллект клиники Медива. Моя задача — предоставлять информацию о предоставляемых услугах и ценах, помогать с записью на прием, отвечать на вопросы об услугах и процедурах, а также предоставлять другую полезную информацию о нашей клинике. Чем могу помочь?",
    "uz": "Men Mediva klinikasining sun'iy intellekti. Mening vazifam - taqdim etilgan xizmatlar va narxlar haqida ma'lumot berish, qabulga yozilishda yordam berish, xizmatlar va protseduralar haqida savollarga javob berish, shuningdek, bizning klinikamiz haqida boshqa foydali ma'lumotlarni taqdim etish. Sizga qanday yordam bera olaman?",
    "en": "I am the artificial intelligence of the Mediva clinic. My task is to provide information about the services and prices, help with making appointments, answer questions about services and procedures, and also provide other useful information about our clinic. How can I help you?"
}

# Стартовая команда
async def start(update: Update, context: CallbackContext) -> None:
    await update.message.reply_text('Выберите язык / Choose a language:', 
                                    reply_markup={"keyboard": [["Русский"], ["Uzbek"], ["English"]], "one_time_keyboard": True})

# Обработчик выбора языка
async def set_language(update: Update, context: CallbackContext) -> None:
    language = update.message.text
    if language == "Русский":
        context.user_data['language'] = 'ru'
    elif language == "Uzbek":
        context.user_data['language'] = 'uz'
    else:
        context.user_data['language'] = 'en'
    await update.message.reply_text(WELCOME_MESSAGES[context.user_data['language']])

# Преобразование словаря услуг в текст
def services_to_text(services):
    service_text = ""
    for category, items in services.items():
        if isinstance(items, dict):
            service_text += f"{category}:\n"
            for service, price in items.items():
                service_text += f"  {service}: {price}\n"
        else:
            service_text += f"{category}: {items}\n"
    return service_text

# Функция для рекомендации врачей
async def recommend_doctors(update: Update, context: CallbackContext) -> None:
    user_language = context.user_data.get('language', 'ru')
    user_input = update.message.text.lower()

    if "дерматолог" in user_input or "косметолог" in user_input:
        doctors = DOCTORS["recommended"]["dermatologists"]
    elif "стоматолог" in user_input:
        doctors = DOCTORS["recommended"]["dentists"]
    else:
        doctors = DOCTORS["recommended"]["dermatologists"] + DOCTORS["recommended"]["dentists"]

    response = f"Вот рекомендуемые врачи по вашему запросу:\n" + "\n".join(doctors)
    await update.message.reply_text(response)

# Обработка сообщений
async def handle_message(update: Update, context: CallbackContext) -> None:
    user_input = update.message.text.lower()
    user_language = context.user_data.get('language', 'ru')

    if "врач" in user_input or "доктор" in user_input:
        await recommend_doctors(update, context)
    else:
        services_text = services_to_text(services)
        response = openai.ChatCompletion.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": f"You are a helpful assistant for a medical clinic. Respond in {LANGUAGES[user_language]}."},
                {"role": "system", "content": f"Here is the list of services and their prices:\n{services_text}"},
                {"role": "system", "content": f"Here is the contact information:\n{CONTACT_INFO}"},
                {"role": "system", "content": f"Here is the information about doctors:\n{DOCTORS}"},
                {"role": "user", "content": user_input}
            ]
        )
        await update.message.reply_text(response.choices[0].message['content'].strip())

# Функция для отправки данных в Zapier
def send_to_zapier(data):
    response = requests.post(ZAPIER_WEBHOOK_URL, json=data)
    return response.status_code == 200

# Запись на прием
async def book_appointment(update: Update, context: CallbackContext) -> None:
    user_language = context.user_data.get('language', 'ru')
    await update.message.reply_text(f"Укажите Ваше И.Ф.О, полную дату рождения и удобное время для записи ({LANGUAGES[user_language]}).")

# Обработчик записи данных для записи на прием
async def handle_appointment(update: Update, context: CallbackContext) -> None:
    user_data = update.message.text.split(',')
    if len(user_data) == 3:
        fio, dob, time = user_data
        appointment_data = {
            "fio": fio.strip(),
            "dob": dob.strip(),
            "time": time.strip(),
            "platform": "Telegram"
        }
        if send_to_zapier(appointment_data):
            await update.message.reply_text(
                f"{fio}, благодарим за ваше обращение.\n\n"
                f"Мы записали вас на прием.\n\n"
                f"Дата: {datetime.strptime(dob.strip(), '%Y-%m-%d').date()}\n"
                f"Время: {time.strip()}\n\n"
                f"Если у вас возникнут дополнительные вопросы или изменения, пожалуйста, сообщите нам по номеру {CONTACT_INFO['phone']}.\n\n"
                f"Хорошего дня!"
            )
        else:
            await update.message.reply_text("Извините, произошла ошибка при обработке вашего запроса. Пожалуйста, попробуйте еще раз позже.")
    else:
        await update.message.reply_text(f"Пожалуйста, предоставьте всю информацию в формате: И.Ф.О, дата рождения, удобное время. ({LANGUAGES[context.user_data['language']]})")

# Справочная информация
async def provide_info(update: Update, context: CallbackContext) -> None:
    user_language = context.user_data.get('language', 'ru')
    contact_info = (
        f"Адрес: {CONTACT_INFO['address']}\n"
        f"Номер телефона: {CONTACT_INFO['phone']}\n"
        f"Email: {CONTACT_INFO['email']}\n"
        f"Ссылка на официальный сайт: {CONTACT_INFO['website']}"
    )
    await update.message.reply_text(f"{contact_info} ({LANGUAGES[user_language]})")

# Обработчик вебхука
@app.route('/webhook', methods=['POST'])
def webhook():
    update = Update.de_json(request.get_json(force=True), bot)
    application.process_update(update)
    return jsonify({"ok": True})

# Маршрут для проверки работоспособности
@app.route('/')
def index():
    return 'Бот клиники Медива работает!'

# Запуск бота
def main() -> None:
    global application
    global bot
    application = Application.builder().token(TELEGRAM_BOT_TOKEN).build()
    bot = application.bot

    application.add_handler(CommandHandler("start", start))
    application.add_handler(MessageHandler(filters.Regex('^(Русский|Uzbek|English)$'), set_language))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    application.add_handler(CommandHandler("book", book_appointment))
    application.add_handler(CommandHandler("info", provide_info))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_appointment))

if __name__ == "__main__":
    main()
    # Запуск Flask приложения
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)








