import os
import logging
import json
from datetime import datetime
from dotenv import load_dotenv
from telegram import Update, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

# Загружаем переменные окружения
load_dotenv()

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO,
    handlers=[
        logging.FileHandler('logs/app.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Загружаем данные-заглушки
def load_placeholder_data():
    try:
        with open('configs/data_placeholders.json', 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        logger.error("Файл data_placeholders.json не найден")
        return {}

# Словарь для хранения состояния пользователей
user_states = {}

# Главное меню
def get_main_menu():
    keyboard = [
        ['❗ Сообщите об опасности'],
        ['🏠 Ближайшее укрытие'],
        ['🧑‍🏫 Консультант по безопасности РПРЗ']
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

# Обработчик команды /start
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    logger.info(f"Пользователь {user.id} ({user.username}) запустил бота")
    
    welcome_text = (
        "🛡️ Добро пожаловать в систему безопасности РПРЗ!\n\n"
        "Выберите нужную функцию:"
    )
    
    await update.message.reply_text(
        welcome_text,
        reply_markup=get_main_menu()
    )

# Обработчик текстовых сообщений
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    text = update.message.text
    
    logger.info(f"Пользователь {user.id} отправил сообщение: {text}")
    
    if text == "❗ Сообщите об опасности":
        await handle_danger_report(update, context)
    elif text == "🏠 Ближайшее укрытие":
        await handle_shelter_finder(update, context)
    elif text == "🧑‍🏫 Консультант по безопасности РПРЗ":
        await handle_safety_consultant(update, context)
    else:
        await update.message.reply_text(
            "Пожалуйста, выберите одну из предложенных функций.",
            reply_markup=get_main_menu()
        )

# Заглушка для "Сообщите об опасности"
async def handle_danger_report(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🚨 Функция 'Сообщите об опасности' будет реализована в следующих шагах.\n"
        "Пока что это заглушка.",
        reply_markup=get_main_menu()
    )

# Заглушка для "Ближайшее укрытие"
async def handle_shelter_finder(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🏠 Функция 'Ближайшее укрытие' будет реализована в следующих шагах.\n"
        "Пока что это заглушка.",
        reply_markup=get_main_menu()
    )

# Заглушка для "Консультант по безопасности"
async def handle_safety_consultant(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🧑‍🏫 Функция 'Консультант по безопасности РПРЗ' будет реализована в следующих шагах.\n"
        "Пока что это заглушка.",
        reply_markup=get_main_menu()
    )

def main():
    # Получаем токен бота
    bot_token = os.getenv('BOT_TOKEN')
    if not bot_token:
        logger.error("BOT_TOKEN не найден в переменных окружения")
        return
    
    # Создаем приложение
    application = Application.builder().token(bot_token).build()
    
    # Добавляем обработчики
    application.add_handler(CommandHandler("start", start))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    
    # Запускаем бота
    logger.info("Запуск бота...")
    application.run_polling()

if __name__ == '__main__':
    main()
