"""
Webhook версия для serverless Railway
"""
import os
import sys
import logging
import threading
from datetime import datetime
from pathlib import Path
from dotenv import load_dotenv
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from telegram.error import TelegramError
from flask import Flask, request
import asyncio

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

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

# Определяем корневую директорию проекта (где находится bot/)
# Это гарантирует, что logs/ будет создана в правильном месте
# В Railway контейнере: /app/bot/main_webhook.py -> BASE_DIR = /app
BASE_DIR = Path(__file__).parent.parent
LOGS_DIR = BASE_DIR / 'logs'
LOG_FILE = LOGS_DIR / 'app.log'

# Создаем директорию для логов перед настройкой логирования
# Используем абсолютный путь для надежности в контейнерах
LOGS_DIR.mkdir(parents=True, exist_ok=True)

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO,
    handlers=[
        logging.FileHandler(str(LOG_FILE), encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Глобальная переменная для отслеживания времени запуска
BOT_START_TIME = None

# Глобальный event loop для обработки async операций
_loop = None
_loop_thread = None

def get_event_loop():
    """Получить или создать глобальный event loop"""
    global _loop, _loop_thread
    
    if _loop is None or _loop.is_closed():
        _loop = asyncio.new_event_loop()
        
        def run_loop():
            asyncio.set_event_loop(_loop)
            try:
                _loop.run_forever()
            except Exception as e:
                logger.error(f"Критическая ошибка в event loop: {e}", exc_info=True)
            finally:
                try:
                    _loop.close()
                except Exception:
                    pass
        
        _loop_thread = threading.Thread(target=run_loop, daemon=True, name="TelegramBotEventLoop")
        _loop_thread.start()
        # Даем время на запуск event loop
        import time
        time.sleep(0.1)
        logger.info("✅ Глобальный event loop создан и запущен в отдельном потоке")
    
    return _loop

def run_async(coro):
    """Запустить async функцию в глобальном event loop и дождаться результата"""
    loop = get_event_loop()
    try:
        future = asyncio.run_coroutine_threadsafe(coro, loop)
        return future.result(timeout=60)  # Таймаут 60 секунд для инициализации
    except asyncio.TimeoutError:
        logger.error("Таймаут при выполнении async функции")
        raise
    except Exception as e:
        logger.error(f"Ошибка при выполнении async функции: {e}", exc_info=True)
        raise

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
    
    async def my_history_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        user = update.effective_user
        user_id = user.id
        self.logger.log_activity(user_id, user.username, "history_requested")
        
        try:
            activities = self.history_service.get_user_activities(user_id)
            history_text = self.history_service.format_activity_history(activities)
            
            if len(history_text) > 4000:
                parts = history_text.split('\n\n')
                current_part = ""
                
                for part in parts:
                    if len(current_part + part) > 4000:
                        await update.message.reply_text(
                            current_part,
                            reply_markup=self.keyboard_factory.create_main_menu(),
                            parse_mode='Markdown'
                        )
                        current_part = part + "\n\n"
                    else:
                        current_part += part + "\n\n"
                
                if current_part.strip():
                    await update.message.reply_text(
                        current_part,
                        reply_markup=self.keyboard_factory.create_main_menu(),
                        parse_mode='Markdown'
                    )
            else:
                await update.message.reply_text(
                    history_text,
                    reply_markup=self.keyboard_factory.create_main_menu(),
                    parse_mode='Markdown'
                )
                
        except Exception as e:
            logger.error(f"Ошибка получения истории {user_id}: {e}")
            await update.message.reply_text(
                "❌ Ошибка получения истории.",
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
        
        # Обработка основных функций
        if text in ["🚨❗ Сообщите об опасности", "❗ Сообщите об опасности"]:
            await self.danger_handler.handle(update, context)
        elif text in ["🏠🛡️ Ближайшее укрытие", "🏠 Ближайшее укрытие"]:
            await self._handle_shelter_finder(update, context)
        elif text in ["🧑‍🏫📚 Консультант по безопасности РПРЗ", "🧑‍🏫 Консультант по безопасности РПРЗ"]:
            await self._handle_safety_consultant(update, context)
        else:
            await update.message.reply_text(
                "Пожалуйста, выберите одну из предложенных функций.",
                reply_markup=self.keyboard_factory.create_main_menu()
            )
    
    async def _handle_shelter_finder(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Обработчик поиска убежищ"""
        user_id = update.effective_user.id
        
        # Логируем активность
        self.logger.log_activity(user_id, update.effective_user.username, "shelter_finder_started")
        
        # Используем сервис для получения убежищ
        shelters = self.shelter_service.get_shelters()
        
        if not shelters:
            await update.message.reply_text(
                "🏠 **Ближайшее укрытие**\n\n"
                "Убежища не найдены. Обратитесь к администратору.",
                reply_markup=self.keyboard_factory.create_main_menu(),
                parse_mode='Markdown'
            )
            return
        
        # Отправляем информацию о первом убежище
        await self.shelter_service.send_shelter_info(update, context, shelters[0])
        
        # Предлагаем отправить геолокацию для поиска ближайших
        keyboard = [
            ['📍 Отправить геолокацию'],
            ['⬅️ Главное меню']
        ]
        from telegram import ReplyKeyboardMarkup
        await update.message.reply_text(
            "📍 Отправьте вашу геолокацию для поиска ближайших убежищ:",
            reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
        )
        
        # Устанавливаем состояние ожидания геолокации
        self.state_manager.set_user_state(user_id, {
            'state': 'shelter_location',
            'data': {}
        })
    
    async def _handle_safety_consultant(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Обработчик консультанта по безопасности"""
        user_id = update.effective_user.id
        
        # Логируем активность
        self.logger.log_activity(user_id, update.effective_user.username, "safety_consultant_started")
        
        # Получаем список документов
        documents = self.consultant_service.get_documents()
        
        if not documents:
            await update.message.reply_text(
                "🧑‍🏫 **Консультант по безопасности РПРЗ**\n\n"
                "Документы не найдены. Обратитесь к администратору.",
                reply_markup=self.keyboard_factory.create_main_menu(),
                parse_mode='Markdown'
            )
            return
        
        # Формируем список документов
        text = "🧑‍🏫 **Консультант по безопасности РПРЗ**\n\n"
        text += "📚 Доступные документы:\n\n"
        
        for i, doc in enumerate(documents[:5], 1):  # Показываем первые 5
            text += f"{i}. {doc.title}\n"
        
        keyboard = []
        for i, doc in enumerate(documents[:5], 1):
            keyboard.append([f"📄 {doc.title}"])
        keyboard.append(['❓ Задать вопрос'])
        keyboard.append(['⬅️ Главное меню'])
        
        from telegram import ReplyKeyboardMarkup
        await update.message.reply_text(
            text,
            reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True),
            parse_mode='Markdown'
        )
        
        # Устанавливаем состояние для обработки выбора документа
        self.state_manager.set_user_state(user_id, {
            'state': 'consultant_document',
            'data': {'documents': documents}
        })
    
    async def handle_media(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Обработчик медиафайлов"""
        user_id = update.effective_user.id
        
        # Проверяем, находится ли пользователь в состоянии ожидания медиафайлов
        user_state = self.state_manager.get_user_state(user_id)
        if user_state and user_state['state'] == 'danger_media':
            await self._handle_danger_media(update, context)
        else:
            await update.message.reply_text(
                "Пожалуйста, выберите функцию из главного меню.",
                reply_markup=self.keyboard_factory.create_main_menu()
            )
    
    async def _handle_danger_media(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Обработать медиафайлы для сообщения об опасности"""
        user_id = update.effective_user.id
        user_state = self.state_manager.get_user_state(user_id)
        
        if not user_state:
            return
        
        data = user_state['data']
        
        if update.message.photo:
            # Обрабатываем фото
            file_id = update.message.photo[-1].file_id
            file_size = update.message.photo[-1].file_size
            file_type = 'photo'
        elif update.message.video:
            # Обрабатываем видео
            file_id = update.message.video.file_id
            file_size = update.message.video.file_size
            file_type = 'video'
        else:
            await update.message.reply_text(
                "Пожалуйста, прикрепите фото или видео, или нажмите 'Пропустить'",
                reply_markup=self.keyboard_factory.create_media_buttons()
            )
            return
        
        # Проверяем размер файла
        if not self.danger_service.validate_media_file(file_size, file_type):
            max_size = "20 МБ" if file_type == 'photo' else "300 МБ"
            await update.message.reply_text(
                f"❌ Файл слишком большой. Максимальный размер {file_type}: {max_size}",
                reply_markup=self.keyboard_factory.create_back_button()
            )
            return
        
        if 'media_files' not in data:
            data['media_files'] = []
        
        data['media_files'].append({
            'file_id': file_id,
            'file_type': file_type,
            'file_size': file_size
        })
        
        await update.message.reply_text(
            f"✅ {file_type == 'photo' and 'Фото' or 'Видео'} добавлено. Можете прикрепить еще файлы или продолжить.",
            reply_markup=self.keyboard_factory.create_media_continue_buttons()
        )
    
    async def handle_location(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Обработчик геолокации"""
        user_id = update.effective_user.id
        
        # Проверяем, находится ли пользователь в состоянии ожидания геолокации
        user_state = self.state_manager.get_user_state(user_id)
        if user_state and user_state['state'] == 'shelter_location':
            await self._handle_shelter_location(update, context)
        else:
            await update.message.reply_text(
                "Пожалуйста, выберите функцию из главного меню.",
                reply_markup=self.keyboard_factory.create_main_menu()
            )
    
    async def _handle_shelter_location(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Обработать геолокацию для убежищ"""
        user_id = update.effective_user.id
        
        if update.message.location:
            logger.info(f"Геолокация пользователя {user_id}: {update.message.location.latitude}, {update.message.location.longitude}")
        
        await update.message.reply_text(
            "📍 Геолокация получена. Функция поиска убежищ будет реализована в следующих версиях.",
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
        
        # Добавляем обработчики команд
        self.application.add_handler(CommandHandler("start", self.start_command))
        self.application.add_handler(CommandHandler("my_history", self.my_history_command))
        
        # Добавляем обработчики сообщений
        self.application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_message))
        self.application.add_handler(MessageHandler(filters.PHOTO | filters.VIDEO, self.handle_media))
        self.application.add_handler(MessageHandler(filters.LOCATION, self.handle_location))
        
        # Добавляем обработчик ошибок
        async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
            """Обработчик ошибок Telegram"""
            logger.error(f"Ошибка в обработчике Telegram: {context.error}", exc_info=context.error)
            
            # Пытаемся отправить сообщение пользователю, если это возможно
            if update and hasattr(update, 'effective_message') and update.effective_message:
                try:
                    await update.effective_message.reply_text(
                        "❌ Произошла ошибка при обработке вашего запроса. Попробуйте позже.",
                        reply_markup=bot_app.keyboard_factory.create_main_menu()
                    )
                except Exception as e:
                    logger.error(f"Не удалось отправить сообщение об ошибке: {e}")
        
        self.application.add_error_handler(error_handler)
        
        # Инициализируем приложение
        await self.application.initialize()
        logger.info("✅ Telegram Application webhook готов")


bot_app = BotApplication()


@app.route('/webhook', methods=['POST'])
def webhook():
    """Обработчик webhook запросов от Telegram"""
    try:
        # Проверяем, что бот инициализирован
        if not bot_app.application:
            logger.error("Бот не инициализирован")
            return 'OK', 200
        
        # Получаем JSON данные от Telegram
        json_data = request.get_json(force=True)
        if not json_data:
            logger.warning("Пустой JSON в webhook запросе")
            return 'OK', 200
        
        # Создаем Update объект из JSON
        try:
            update = Update.de_json(json_data, bot_app.application.bot)
            if not update:
                logger.warning("Не удалось создать Update объект из JSON")
                return 'OK', 200
        except Exception as e:
            logger.error(f"Ошибка при создании Update объекта: {e}", exc_info=True)
            return 'OK', 200
        
        # Обрабатываем update в глобальном event loop
        # Используем run_coroutine_threadsafe для запуска async кода из синхронного контекста Flask
        try:
            loop = get_event_loop()
            # Запускаем обработку update асинхронно в глобальном event loop
            # Не ждем результата (fire-and-forget), чтобы быстро ответить Telegram
            future = asyncio.run_coroutine_threadsafe(
                bot_app.application.process_update(update),
                loop
            )
            # Не ждем результата - обработка будет происходить в фоне
            # Telegram требует быстрый ответ (в течение 5 секунд)
            logger.debug(f"Update {update.update_id} отправлен на обработку")
        except Exception as e:
            logger.error(f"Ошибка при запуске обработки update: {e}", exc_info=True)
            # Все равно возвращаем OK, чтобы Telegram не отправлял повторно
        
        # Сразу возвращаем OK Telegram (Telegram требует ответ в течение 5 секунд)
        return 'OK', 200
        
    except Exception as e:
        logger.error(f"Критическая ошибка в webhook handler: {e}", exc_info=True)
        # Все равно возвращаем OK, чтобы Telegram не отправлял повторно
        return 'OK', 200


@app.route('/health', methods=['GET'])
def health():
    """Health check endpoint"""
    global BOT_START_TIME
    if BOT_START_TIME:
        uptime = datetime.now() - BOT_START_TIME
        uptime_str = str(uptime).split('.')[0]  # Убираем микросекунды
        return {
            'status': 'OK',
            'started_at': BOT_START_TIME.isoformat(),
            'uptime': uptime_str,
            'uptime_seconds': int(uptime.total_seconds())
        }, 200
    return {'status': 'OK'}, 200


@app.route('/', methods=['GET'])
def index():
    """Главная страница с информацией о времени работы"""
    global BOT_START_TIME
    if BOT_START_TIME:
        uptime = datetime.now() - BOT_START_TIME
        uptime_str = str(uptime).split('.')[0]
        return f'Bot Running\nStarted: {BOT_START_TIME.strftime("%Y-%m-%d %H:%M:%S")}\nUptime: {uptime_str}', 200
    return 'Bot Running', 200


def setup_webhook():
    import requests
    
    bot_token = os.getenv('BOT_TOKEN')
    if not bot_token:
        logger.error("BOT_TOKEN не найден")
        return False
    
    # Инициализируем бота перед установкой webhook в глобальном event loop
    try:
        run_async(bot_app.initialize())
    except Exception as e:
        logger.error(f"Ошибка при инициализации бота: {e}", exc_info=True)
        return False
    
    # Пытаемся получить webhook URL из переменных окружения
    webhook_url = os.getenv('WEBHOOK_URL')
    
    # Если WEBHOOK_URL не установлен, пытаемся использовать Railway переменные
    if not webhook_url:
        # Проверяем различные варианты переменных Railway
        railway_public_domain = (
            os.getenv('RAILWAY_PUBLIC_DOMAIN') or
            os.getenv('RAILWAY_STATIC_URL') or
            os.getenv('PUBLIC_DOMAIN') or
            os.getenv('RAILWAY_DOMAIN')
        )
        
        if railway_public_domain:
            # Убираем протокол, если он есть
            domain = railway_public_domain.replace('https://', '').replace('http://', '').strip('/')
            webhook_url = f"https://{domain}/webhook"
            logger.info(f"🔗 Используется Railway домен: {webhook_url}")
        else:
            # Логируем все доступные переменные окружения для отладки (без секретов)
            env_vars = [k for k in os.environ.keys() if 'RAILWAY' in k or 'DOMAIN' in k or 'URL' in k]
            logger.warning(f"⚠️ WEBHOOK_URL не найден. Доступные переменные: {', '.join(env_vars) if env_vars else 'нет'}")
            
            # Пытаемся получить информацию о сервисе из переменных Railway
            service_name = os.getenv('RAILWAY_SERVICE_NAME', 'worker')
            project_name = os.getenv('RAILWAY_PROJECT_NAME', '')
            
            logger.error("❌ Webhook не может быть установлен без URL. Бот не будет получать обновления!")
            logger.error("")
            logger.error("🔧 РЕШЕНИЕ:")
            logger.error("   1. Откройте Railway Dashboard → ваш сервис → Settings → Variables")
            logger.error("   2. Нажмите '+ New' для добавления новой переменной")
            logger.error("   3. Имя переменной: WEBHOOK_URL")
            logger.error("   4. Значение переменной: https://worker-production-40f5.up.railway.app/webhook")
            logger.error("      (Замените на ваш публичный домен из Settings → Networking → Public Networking)")
            logger.error("   5. Сохраните переменную")
            logger.error("   6. Перезапустите сервис (Deployments → Redeploy)")
            logger.error("")
            logger.error("📋 Информация о вашем домене:")
            logger.error("   - Откройте Settings → Networking → Public Networking")
            logger.error("   - Найдите ваш публичный домен (например: worker-production-40f5.up.railway.app)")
            logger.error("   - Используйте этот домен в формате: https://ВАШ-ДОМЕН/webhook")
            logger.error("")
            return False
    
    try:
        # Проверяем текущий webhook
        check_url = f"https://api.telegram.org/bot{bot_token}/getWebhookInfo"
        check_response = requests.get(check_url)
        if check_response.status_code == 200:
            webhook_info = check_response.json()
            if webhook_info.get('result', {}).get('url'):
                logger.info(f"📋 Текущий webhook: {webhook_info['result']['url']}")
        
        # Устанавливаем новый webhook
        url = f"https://api.telegram.org/bot{bot_token}/setWebhook"
        response = requests.post(url, json={'url': webhook_url})
        
        if response.status_code == 200:
            result = response.json()
            if result.get('ok'):
                logger.info(f"✅ Webhook успешно установлен: {webhook_url}")
                logger.info(f"📊 Результат: {result.get('description', 'OK')}")
                return True
            else:
                logger.error(f"❌ Ошибка установки webhook: {result.get('description', 'Unknown error')}")
                return False
        else:
            logger.error(f"❌ HTTP ошибка при установке webhook: {response.status_code}")
            logger.error(f"📄 Ответ: {response.text}")
            return False
    except Exception as e:
        logger.error(f"❌ Исключение при установке webhook: {e}", exc_info=True)
        return False


if __name__ == '__main__':
    BOT_START_TIME = datetime.now()
    
    logger.info("🚀 Запуск webhook режима (serverless)")
    logger.info(f"⏰ Время запуска: {BOT_START_TIME.strftime('%Y-%m-%d %H:%M:%S')}")
    
    # Пытаемся установить webhook
    webhook_setup_success = setup_webhook()
    
    if webhook_setup_success:
        port = int(os.getenv('PORT', 8080))
        logger.info(f"🌐 Flask запускается на порту {port}")
        logger.info(f"✅ Бот запущен и работает с {BOT_START_TIME.strftime('%Y-%m-%d %H:%M:%S')}")
        logger.info("📡 Webhook настроен, бот готов принимать обновления от Telegram")
        app.run(host='0.0.0.0', port=port, debug=False)
    else:
        logger.error("❌ Не удалось настроить webhook!")
        logger.error("⚠️ Бот запущен, но НЕ будет получать обновления от Telegram!")
        logger.error("🔧 Решение:")
        logger.error("   1. Откройте Railway Dashboard → ваш сервис → Settings")
        logger.error("   2. Перейдите в раздел 'Networking' или 'Public Domain'")
        logger.error("   3. Нажмите 'Generate Domain' или настройте публичный домен")
        logger.error("   4. После создания домена Railway автоматически установит переменную RAILWAY_PUBLIC_DOMAIN")
        logger.error("   5. Перезапустите сервис")
        logger.error("   ИЛИ")
        logger.error("   6. Установите переменную WEBHOOK_URL вручную в Railway → Variables")
        logger.error("      Формат: https://your-app.railway.app/webhook")
        
        # Все равно запускаем Flask, чтобы было видно, что сервис работает
        # Но бот не будет получать обновления
        port = int(os.getenv('PORT', 8080))
        logger.warning(f"⚠️ Flask запускается на порту {port}, но webhook не настроен")
        app.run(host='0.0.0.0', port=port, debug=False)
