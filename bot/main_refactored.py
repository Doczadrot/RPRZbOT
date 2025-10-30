"""
Рефакторенный главный файл бота с соблюдением принципов SOLID
"""
import os
import sys
import logging
from datetime import datetime, time
from zoneinfo import ZoneInfo
from dotenv import load_dotenv
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

# Добавляем путь к модулям
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Импорты интерфейсов и утилит
from bot.interfaces import ILogger, IStateManager, IFileManager, IKeyboardFactory
from bot.utils.activity_logger import ActivityLogger
from bot.utils.state_manager import StateManager
from bot.utils.file_manager import FileManager
from bot.utils.keyboard_factory import KeyboardFactory

# Импорты сервисов
from bot.services.danger_report_service import DangerReportService
from bot.services.shelter_service import ShelterService
from bot.services.consultant_service import ConsultantService
from bot.services.history_service import HistoryService

# Импорты обработчиков
from bot.handlers.danger_report_handler import DangerReportHandler

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


class BotApplication:
    """Главный класс приложения бота"""
    
    def __init__(self):
        # Инициализируем зависимости
        self.logger = ActivityLogger()
        self.state_manager = StateManager()
        self.file_manager = FileManager()
        self.keyboard_factory = KeyboardFactory()
        
        # Инициализируем сервисы
        self.danger_service = DangerReportService(self.file_manager, self.logger)
        self.shelter_service = ShelterService(self.file_manager, self.logger)
        self.consultant_service = ConsultantService(self.file_manager, self.logger)
        self.history_service = HistoryService(self.file_manager, self.logger)
        
        # Инициализируем обработчики
        self.danger_handler = DangerReportHandler(
            self.logger, self.state_manager, self.keyboard_factory, self.danger_service
        )
    
    async def start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Обработчик команды /start"""
        user = update.effective_user
        logger.info(f"Пользователь {user.id} ({user.username}) запустил бота")
        
        # Логируем активность
        self.logger.log_activity(user.id, user.username, "start_command")
        
        welcome_text = (
            "🛡️ Добро пожаловать в систему безопасности РПРЗ!\n\n"
            "Выберите нужную функцию:"
        )
        
        # Создаем клавиатуру напрямую для гарантии
        keyboard = [
            ['🚨❗ Сообщите об опасности'],
            ['🏠🛡️ Ближайшее укрытие'],
            ['🧑‍🏫📚 Консультант по безопасности РПРЗ']
        ]
        
        from telegram import ReplyKeyboardMarkup
        reply_markup = ReplyKeyboardMarkup(
            keyboard, 
            resize_keyboard=True, 
            one_time_keyboard=False,
            input_field_placeholder="Выберите функцию"
        )
        
        logger.info(f"Создана клавиатура напрямую: {reply_markup}")
        
        try:
            await update.message.reply_text(
                welcome_text,
                reply_markup=reply_markup
            )
            logger.info("✅ Команда /start обработана, клавиатура отправлена успешно")
        except Exception as e:
            logger.error(f"❌ Ошибка отправки клавиатуры: {e}")
            # Отправляем без клавиатуры
            await update.message.reply_text(welcome_text)
    
    async def my_history_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Обработчик команды /my_history"""
        user = update.effective_user
        user_id = user.id
        
        # Логируем активность
        self.logger.log_activity(user_id, user.username, "history_requested")
        
        try:
            # Получаем активность пользователя
            activities = self.history_service.get_user_activities(user_id)
            
            # Форматируем историю
            history_text = self.history_service.format_activity_history(activities)
            
            # Разбиваем на части, если сообщение слишком длинное
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
            logger.error(f"Ошибка получения истории пользователя {user_id}: {e}")
            await update.message.reply_text(
                "❌ Ошибка получения истории. Попробуйте позже.",
                reply_markup=self.keyboard_factory.create_main_menu()
            )
    
    async def handle_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Обработчик текстовых сообщений"""
        user = update.effective_user
        text = update.message.text
        user_id = user.id
        
        # Проверяем защиту от спама
        if not self.state_manager.check_spam_protection(user_id):
            await update.message.reply_text(
                "⚠️ Слишком много сообщений. Подождите минуту и попробуйте снова.",
                reply_markup=self.keyboard_factory.create_main_menu()
            )
            return
        
        logger.info(f"Пользователь {user_id} отправил сообщение: {text}")
        
        # Логируем активность
        self.logger.log_activity(user_id, user.username, "text_message", text[:50])
        
        # Обработка кнопок навигации
        if text in ["⬅️🔙 Назад", "🏠⬅️ Главное меню", "⬅️ Назад", "⬅️ Главное меню"]:
            self.state_manager.clear_user_state(user_id)
            await update.message.reply_text(
                "Главное меню",
                reply_markup=self.keyboard_factory.create_main_menu()
            )
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
        """Обработчик поиска убежищ (заглушка)"""
        user_id = update.effective_user.id
        
        # Логируем активность
        self.logger.log_activity(user_id, update.effective_user.username, "shelter_finder_started")
        
        await update.message.reply_text(
            "🏠 **Ближайшее укрытие**\n\n"
            "Функция поиска убежищ будет реализована в следующих версиях.\n"
            "Пока что это заглушка.",
            reply_markup=self.keyboard_factory.create_main_menu(),
            parse_mode='Markdown'
        )
    
    async def _handle_safety_consultant(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Обработчик консультанта по безопасности (заглушка)"""
        user_id = update.effective_user.id
        
        # Логируем активность
        self.logger.log_activity(user_id, update.effective_user.username, "safety_consultant_started")
        
        await update.message.reply_text(
            "🧑‍🏫 **Консультант по безопасности РПРЗ**\n\n"
            "Функция консультанта будет реализована в следующих версиях.\n"
            "Пока что это заглушка.",
            reply_markup=self.keyboard_factory.create_main_menu(),
            parse_mode='Markdown'
        )
    
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
        """Обработать геолокацию для убежищ (заглушка)"""
        user_id = update.effective_user.id
        
        if update.message.location:
            logger.info(f"Геолокация пользователя {user_id}: {update.message.location.latitude}, {update.message.location.longitude}")
        
        await update.message.reply_text(
            "📍 Геолокация получена. Функция поиска убежищ будет реализована в следующих версиях.",
            reply_markup=self.keyboard_factory.create_main_menu()
        )
    
    async def error_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Обработчик ошибок"""
        logger.error(f"Ошибка при обработке обновления: {context.error}")
        if update and update.effective_message:
            try:
                await update.effective_message.reply_text(
                    "❌ Произошла ошибка. Попробуйте позже.",
                    reply_markup=self.keyboard_factory.create_main_menu()
                )
            except:
                pass
    
    def run(self):
        """Запустить бота"""
        # Получаем токен бота
        bot_token = os.getenv('BOT_TOKEN')
        if not bot_token:
            logger.error("BOT_TOKEN не найден в переменных окружения")
            return
        
        # Проверяем рабочие часы по МСК (07:00–20:00)
        disable_hours = os.getenv("DISABLE_WORKING_HOURS", "0") == "1"
        if not disable_hours:
            try:
                now_utc = datetime.utcnow().replace(tzinfo=ZoneInfo("UTC"))
                now_msk = now_utc.astimezone(ZoneInfo("Europe/Moscow"))
                start_msk = time(7, 0)
                end_msk = time(20, 0)
                within_hours = start_msk <= now_msk.time() <= end_msk
                logger.info(
                    f"🕐 Проверка рабочего времени: сейчас {now_msk.strftime('%Y-%m-%d %H:%M:%S')} МСК; "
                    f"допустимо {start_msk.strftime('%H:%M')}-{end_msk.strftime('%H:%M')}"
                )
                if not within_hours:
                    logger.warning("⏰ Нерабочее время! Бот не запускается вне 07:00–20:00 МСК. Установите DISABLE_WORKING_HOURS=1 для принудительного запуска.")
                    return
            except Exception as e:
                logger.error(f"Ошибка проверки рабочего времени: {e}. Продолжаем запуск по умолчанию.")
        
        # Создаем приложение
        application = Application.builder().token(bot_token).build()
        
        # Добавляем обработчики
        application.add_handler(CommandHandler("start", self.start_command))
        application.add_handler(CommandHandler("my_history", self.my_history_command))
        application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_message))
        application.add_handler(MessageHandler(filters.PHOTO | filters.VIDEO, self.handle_media))
        application.add_handler(MessageHandler(filters.LOCATION, self.handle_location))
        
        # Добавляем обработчик ошибок
        application.add_error_handler(self.error_handler)
        
        # Запускаем бота
        logger.info("Запуск рефакторенного бота...")
        application.run_polling()


def main():
    """Главная функция"""
    app = BotApplication()
    app.run()


if __name__ == '__main__':
    main()
