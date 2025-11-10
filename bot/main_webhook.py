"""
Минимальная webhook версия для serverless Railway
"""
import os
import sys
import logging
from dotenv import load_dotenv
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from flask import Flask, request
import asyncio

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Импорты
from bot.interfaces import ILogger, IStateManager, IFileManager, IKeyboardFactory
from bot.utils.activity_logger import ActivityLogger
from bot.utils.state_manager import StateManager
from bot.utils.file_manager import FileManager
from bot.utils.keyboard_factory import KeyboardFactory
from bot.services.danger_report_service import DangerReportService
from bot.services.shelter_service import ShelterService
from bot.services.consultant_service import ConsultantService
from bot.services.history_service import HistoryService
from bot.handlers.danger_report_handler import DangerReportHandler

load_dotenv()

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO,
    handlers=[
        logging.FileHandler('logs/app.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

app = Flask(__name__)


class BotApplication:
    def __init__(self):
        self.logger = ActivityLogger()
        self.state_manager = StateManager()
        self.file_manager = FileManager()
        self.keyboard_factory = KeyboardFactory()
        
        self.danger_service = DangerReportService(self.file_manager, self.logger)
        self.shelter_service = ShelterService(self.file_manager, self.logger)
        self.consultant_service = ConsultantService(self.file_manager, self.logger)
        self.history_service = HistoryService(self.file_manager, self.logger)
        
        self.danger_handler = DangerReportHandler(
            self.logger, self.state_manager, self.keyboard_factory, self.danger_service
        )
        
        self.application = None
    
    async def start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        user = update.effective_user
        logger.info(f"Пользователь {user.id} ({user.username}) запустил бота")
        self.logger.log_activity(user.id, user.username, "start_command")
        
        await update.message.reply_text(
            "🛡️ Добро пожаловать в систему безопасности РПРЗ!\n\nВыберите нужную функцию:",
            reply_markup=self.keyboard_factory.create_main_menu()
        )
    
    async def handle_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        user = update.effective_user
        text = update.message.text
        user_id = user.id
        
        if not self.state_manager.check_spam_protection(user_id):
            await update.message.reply_text(
                "⚠️ Слишком много сообщений. Подождите минуту.",
                reply_markup=self.keyboard_factory.create_main_menu()
            )
            return
        
        self.logger.log_activity(user_id, user.username, "text_message", text[:50])
        
        if text in ["⬅️🔙 Назад", "🏠⬅️ Главное меню", "⬅️ Назад", "⬅️ Главное меню"]:
            self.state_manager.clear_user_state(user_id)
            await update.message.reply_text("Главное меню", reply_markup=self.keyboard_factory.create_main_menu())
            return
        
        if text in ["🚨❗ Сообщите об опасности", "❗ Сообщите об опасности"]:
            await self.danger_handler.handle(update, context)
        else:
            await update.message.reply_text(
                "Пожалуйста, выберите одну из предложенных функций.",
                reply_markup=self.keyboard_factory.create_main_menu()
            )
    
    async def initialize(self):
        bot_token = os.getenv('BOT_TOKEN')
        if not bot_token:
            raise ValueError("BOT_TOKEN not found")
        
        from telegram.request import HTTPXRequest
        request = HTTPXRequest(
            connection_pool_size=8,
            connect_timeout=30.0,
            read_timeout=30.0,
            write_timeout=30.0,
            pool_timeout=30.0
        )
        
        self.application = Application.builder().token(bot_token).request(request).build()
        self.application.add_handler(CommandHandler("start", self.start_command))
        self.application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_message))
        
        await self.application.initialize()
        logger.info("✅ Telegram Application для webhook готов")


bot_app = BotApplication()


@app.route('/webhook', methods=['POST'])
def webhook():
    try:
        json_data = request.get_json(force=True)
        update = Update.de_json(json_data, bot_app.application.bot)
        asyncio.run(bot_app.application.process_update(update))
        return 'OK', 200
    except Exception as e:
        logger.error(f"Ошибка webhook: {e}", exc_info=True)
        return 'Error', 500


@app.route('/health', methods=['GET'])
def health():
    return 'OK', 200


@app.route('/', methods=['GET'])
def index():
    return 'Bot Running', 200


def setup_webhook():
    import requests
    
    bot_token = os.getenv('BOT_TOKEN')
    webhook_url = os.getenv('WEBHOOK_URL')
    
    if not bot_token or not webhook_url:
        logger.error("BOT_TOKEN или WEBHOOK_URL не найдены")
        return False
    
    asyncio.run(bot_app.initialize())
    
    try:
        url = f"https://api.telegram.org/bot{bot_token}/setWebhook"
        response = requests.post(url, json={'url': webhook_url})
        
        if response.status_code == 200:
            logger.info(f"✅ Webhook установлен: {webhook_url}")
            return True
        else:
            logger.error(f"❌ Ошибка webhook: {response.text}")
            return False
    except Exception as e:
        logger.error(f"❌ Ошибка webhook: {e}")
        return False


if __name__ == '__main__':
    os.makedirs('logs', exist_ok=True)
    logger.info("🚀 Запуск webhook режима (serverless)")
    
    if setup_webhook():
        port = int(os.getenv('PORT', 8080))
        logger.info(f"🌐 Flask на порту {port}")
        app.run(host='0.0.0.0', port=port, debug=False)
    else:
        logger.error("❌ Не удалось настроить webhook")

