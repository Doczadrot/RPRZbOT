#!/usr/bin/env python3
"""
MVP Telegram-бот по безопасности РПРЗ
Основной файл бота с 4 основными функциями безопасности
"""

import os
import sys
import json
import csv
import ssl
import urllib3
import time
import psutil
import signal
from datetime import datetime
from pathlib import Path

import telebot
from telebot import types
from telebot.handler_backends import State, StatesGroup
from telebot.storage import StateMemoryStorage
from loguru import logger
from dotenv import load_dotenv

# Отключаем SSL предупреждения для тестирования
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# Добавляем корневую папку в путь для импорта
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Импорт обработчиков
from handlers import (
    log_activity, log_incident, log_suggestion,
    get_back_keyboard, get_main_menu_keyboard, get_media_keyboard, get_location_keyboard,
    handle_danger_report_text, handle_danger_report_location, handle_danger_report_media, finish_danger_report,
    handle_shelter_finder_text,
    handle_safety_consultant_text, show_documents_list, start_question_mode, handle_safety_question,
    handle_improvement_suggestion_text, handle_improvement_suggestion_choice, handle_suggestion_menu,
    set_bot_instance
)

# Загрузка переменных окружения
load_dotenv('.env')

# Система блокировки процесса
PROJECT_ROOT = Path(__file__).parent.parent
LOCK_FILE = PROJECT_ROOT / "bot.lock"
PID_FILE = PROJECT_ROOT / "bot.pid"

# Конфигурация
BOT_TOKEN = os.getenv('BOT_TOKEN')
ADMIN_CHAT_ID = os.getenv('ADMIN_CHAT_ID')
LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')
MAX_FILE_SIZE_MB = int(os.getenv('MAX_FILE_SIZE_MB', '20'))
MAX_VIDEO_SIZE_MB = int(os.getenv('MAX_VIDEO_SIZE_MB', '300'))

# Email конфигурация
EMAIL_HOST = os.getenv('EMAIL_HOST', 'smtp.yandex.ru')
EMAIL_PORT = int(os.getenv('EMAIL_PORT', '587'))
EMAIL_USE_TLS = os.getenv('EMAIL_USE_TLS', 'True').lower() == 'true'
EMAIL_USE_SSL = os.getenv('EMAIL_USE_SSL', 'False').lower() == 'true'
EMAIL_HOST_USER = os.getenv('EMAIL_HOST_USER', '')
EMAIL_HOST_PASSWORD = os.getenv('EMAIL_HOST_PASSWORD', '')
DEFAULT_FROM_EMAIL = os.getenv('DEFAULT_FROM_EMAIL', EMAIL_HOST_USER)

# Функция для детального логирования ошибок админа
def log_admin_error(error_type: str, error: Exception, context: dict = None):
    """Логирует ошибку с детальной информацией для админа"""
    try:
        # Безопасная обработка контекста
        safe_context = context if isinstance(context, dict) else {}
        
        error_info = {
            'error_type': error_type,
            'error_class': type(error).__name__,
            'error_message': str(error),
            'context': safe_context,
            'timestamp': datetime.now().isoformat()
        }
        
        # Логируем в основной лог ошибок
        logger.error(f"ADMIN_ERROR | {error_type} | {type(error).__name__}: {str(error)}")
        
        # Логируем в системный лог с дополнительной информацией
        logger.bind(error_type=error_type).error(f"{type(error).__name__}: {str(error)}")
        
        # Если это критическая ошибка, логируем отдельно
        if error_type in ['BOT_CRASH', 'API_FAILURE', 'CONFIG_ERROR']:
            logger.critical(f"🚨 КРИТИЧЕСКАЯ ОШИБКА | {error_type} | {str(error)}")
            
    except Exception as log_error:
        # Если даже логирование не работает
        print(f"ОШИБКА ЛОГИРОВАНИЯ: {log_error}")

# Функция для логирования системных событий
def log_system_event(event_type: str, message: str, details: dict = None):
    """Логирует системные события для админа"""
    try:
        logger.info(f"SYSTEM_EVENT | {event_type} | {message}")
        if details:
            logger.debug(f"SYSTEM_DETAILS | {event_type} | {details}")
    except Exception as e:
        print(f"Ошибка логирования системного события: {e}")

# Функции для работы с блокировкой процесса
def check_running_bots():
    """Проверяет запущенные процессы бота"""
    running_bots = []
    
    for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
        try:
            if proc.info['name'] in ['python.exe', 'python']:
                cmdline = ' '.join(proc.info['cmdline']) if proc.info['cmdline'] else ''
                if any(keyword in cmdline.lower() for keyword in ['bot', 'main.py', 'run_bot.py']):
                    running_bots.append(proc.info['pid'])
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue
    
    return running_bots

def create_process_lock():
    """Создает блокировку процесса"""
    try:
        current_pid = os.getpid()
        
        # Проверяем существующие процессы
        running_bots = check_running_bots()
        if len(running_bots) > 1:  # Больше одного (включая текущий)
            logger.error("❌ Обнаружено несколько запущенных экземпляров бота!")
            logger.error(f"Запущенные процессы: {running_bots}")
            return False
        
        # Создаем файл блокировки
        lock_data = {
            'pid': current_pid,
            'started_at': datetime.now().isoformat(),
            'project_path': str(PROJECT_ROOT)
        }
        
        with open(LOCK_FILE, 'w', encoding='utf-8') as f:
            json.dump(lock_data, f, indent=2, ensure_ascii=False)
        
        with open(PID_FILE, 'w', encoding='utf-8') as f:
            f.write(str(current_pid))
        
        logger.info(f"✅ Создана блокировка процесса: PID {current_pid}")
        return True
        
    except Exception as e:
        logger.error(f"❌ Ошибка создания блокировки: {e}")
        return False

def remove_process_lock():
    """Удаляет блокировку процесса"""
    try:
        if LOCK_FILE.exists():
            LOCK_FILE.unlink()
        if PID_FILE.exists():
            PID_FILE.unlink()
        logger.info("✅ Блокировка процесса удалена")
    except Exception as e:
        logger.error(f"❌ Ошибка удаления блокировки: {e}")

def signal_handler(signum, frame):
    """Обработчик сигналов для корректного завершения"""
    logger.info(f"🛑 Получен сигнал {signum}, завершение работы...")
    remove_process_lock()
    sys.exit(0)

# Регистрируем обработчики сигналов
signal.signal(signal.SIGINT, signal_handler)
signal.signal(signal.SIGTERM, signal_handler)

# Функция для маскирования чувствительных данных
def mask_sensitive_data(text: str) -> str:
    """Маскирует чувствительные данные в логах"""
    if not text:
        return ""
    
    # Маскируем токен бота (формат: 123456789:ABCdefGHIjklMNOpqrsTUVwxyz)
    if ':' in text and len(text) > 20:
        parts = text.split(':')
        if len(parts) == 2 and parts[0].isdigit():
            return f"{parts[0]}:***{parts[1][-4:]}"
    
    # Маскируем длинные строки (возможно токены)
    if len(text) > 20:
        return f"{text[:8]}***{text[-4:]}"
    
    return text

# Функция для санитизации пользовательского ввода
def sanitize_user_input(text: str) -> str:
    """Санитизирует пользовательский ввод для предотвращения XSS и инъекций"""
    if not text:
        return ""
    
    # Удаляем потенциально опасные символы
    dangerous_chars = ['<', '>', '"', "'", '&', ';', '|', '`', '$', '(', ')', '{', '}']
    sanitized = text
    
    for char in dangerous_chars:
        sanitized = sanitized.replace(char, '')
    
    # Удаляем опасные ключевые слова
    dangerous_keywords = [
        'script', 'javascript', 'vbscript', 'onload', 'onerror', 'onclick',
        'iframe', 'object', 'embed', 'form', 'input', 'select', 'option',
        'DROP', 'DELETE', 'INSERT', 'UPDATE', 'SELECT', 'UNION', 'OR', 'AND',
        'rm', 'del', 'format', 'shutdown', 'reboot', 'kill', 'taskkill'
    ]
    
    for keyword in dangerous_keywords:
        sanitized = sanitized.replace(keyword, '')
        sanitized = sanitized.replace(keyword.upper(), '')
        sanitized = sanitized.replace(keyword.lower(), '')
    
    # Ограничиваем длину
    if len(sanitized) > 1000:
        sanitized = sanitized[:1000] + "..."
    
    # Удаляем множественные пробелы
    sanitized = ' '.join(sanitized.split())
    
    return sanitized.strip()

# Функция для валидации пользовательского ввода
def validate_user_input(text: str, min_length: int = 1, max_length: int = 1000) -> tuple[bool, str]:
    """Валидирует пользовательский ввод"""
    if not text:
        return False, "Пустой ввод"
    
    if len(text) < min_length:
        return False, f"Слишком короткий ввод (минимум {min_length} символов)"
    
    if len(text) > max_length:
        return False, f"Слишком длинный ввод (максимум {max_length} символов)"
    
    # Проверяем на подозрительные паттерны
    suspicious_patterns = [
        r'<script', r'javascript:', r'data:', r'vbscript:',
        r'onload=', r'onerror=', r'onclick=', r'onmouseover=',
        r'<iframe', r'<object', r'<embed', r'<form',
        r'SELECT.*FROM', r'INSERT.*INTO', r'UPDATE.*SET', r'DELETE.*FROM',
        r'DROP.*TABLE', r'UNION.*SELECT', r'OR.*1=1', r'AND.*1=1'
    ]
    
    import re
    text_lower = text.lower()
    for pattern in suspicious_patterns:
        if re.search(pattern, text_lower):
            return False, "Обнаружен подозрительный контент"
    
    return True, "OK"



# Функция для отправки email уведомлений
def send_email_notification(subject: str, message: str, to_email: str = None):
    """Отправляет email уведомление о нарушении"""
    try:
        import smtplib
        from email.mime.text import MIMEText
        from email.mime.multipart import MIMEMultipart
        
        if not to_email:
            to_email = os.getenv('DEFAULT_NOTIFICATION_EMAIL', '')
        
        msg = MIMEMultipart()
        msg['From'] = DEFAULT_FROM_EMAIL
        msg['To'] = to_email
        msg['Subject'] = f"🚨 РПРЗ Бот: {subject}"
        
        body = f"""
Сообщение о нарушении безопасности:

{message}

---
Отправлено через Telegram бот РПРЗ
Время: {datetime.now().strftime('%d.%m.%Y %H:%M:%S')}
        """
        
        msg.attach(MIMEText(body, 'plain', 'utf-8'))
        
        server = smtplib.SMTP(EMAIL_HOST, EMAIL_PORT)
        if EMAIL_USE_TLS:
            server.starttls()
        server.login(EMAIL_HOST_USER, EMAIL_HOST_PASSWORD)
        text = msg.as_string()
        server.sendmail(DEFAULT_FROM_EMAIL, to_email, text)
        server.quit()
        
        logger.info(f"Email уведомление отправлено: {subject}")
        return True
        
    except Exception as e:
        log_admin_error("EMAIL_SEND_ERROR", e, {
            'subject': subject,
            'to_email': to_email,
            'message_length': len(message)
        })
        return False

# Функция для показа всех убежищ
def show_all_shelters(chat_id: int):
    """Показывает список всех убежищ"""
    if not BOT_TOKEN or not bot:
        logger.warning("BOT_TOKEN не настроен, функция show_all_shelters недоступна")
        return
    
    try:
        shelters = placeholders.get('shelters', [])
        
        if not shelters:
            bot.send_message(chat_id, "❌ Список убежищ недоступен", reply_markup=get_back_keyboard())
            return
        
        # Отправляем информацию о каждом убежище
        for i, shelter in enumerate(shelters, 1):
            # Отправляем изображение убежища
            photo_path = shelter.get('photo_path', '')
            if photo_path and os.path.exists(photo_path):
                with open(photo_path, 'rb') as photo_file:
                    bot.send_photo(chat_id, photo_file, caption=f"🏠 {shelter['name']}")
            
            # Отправляем информацию об убежище
            shelter_text = (
                f"{shelter['name']}\n\n"
                f"📝 {shelter['description']}\n\n"
                f"📍 Координаты: {shelter['lat']}, {shelter['lon']}\n"
                f"🌐 [📍 Показать на карте]({shelter['map_link']})"
            )
            
            bot.send_message(chat_id, shelter_text, parse_mode='Markdown')
        
        # Финальное сообщение
        final_text = f"✅ Найдено убежищ: {len(shelters)}\n\nВсе убежища оснащены современными системами безопасности и готовы к использованию."
        bot.send_message(chat_id, final_text, reply_markup=get_back_keyboard())
        
    except Exception as e:
        log_admin_error("SHELTER_DISPLAY_ERROR", e, {
            'chat_id': chat_id,
            'shelters_count': len(placeholders.get('shelters', []))
        })
        bot.send_message(chat_id, "❌ Ошибка при загрузке информации об убежищах", reply_markup=get_back_keyboard())

# Функция для поиска ближайшего убежища по геолокации
def find_nearest_shelter(chat_id: int, user_lat: float, user_lon: float):
    """Находит ближайшее убежище по координатам пользователя"""
    if not BOT_TOKEN or not bot:
        logger.warning("BOT_TOKEN не настроен, функция find_nearest_shelter недоступна")
        return
    
    try:
        shelters = placeholders.get('shelters', [])
        
        if not shelters:
            bot.send_message(chat_id, "❌ Список убежищ недоступен", reply_markup=get_back_keyboard())
            return
        
        # Простой расчет расстояния (для MVP)
        def calculate_distance(lat1, lon1, lat2, lon2):
            return ((lat1 - lat2) ** 2 + (lon1 - lon2) ** 2) ** 0.5
        
        # Находим ближайшее убежище
        nearest_shelter = None
        min_distance = float('inf')
        
        for shelter in shelters:
            shelter_lat = float(shelter.get('lat', 0))
            shelter_lon = float(shelter.get('lon', 0))
            distance = calculate_distance(user_lat, user_lon, shelter_lat, shelter_lon)
            
            if distance < min_distance:
                min_distance = distance
                nearest_shelter = shelter
        
        if nearest_shelter:
            # Отправляем изображение ближайшего убежища
            photo_path = nearest_shelter.get('photo_path', '')
            if photo_path and os.path.exists(photo_path):
                with open(photo_path, 'rb') as photo_file:
                    bot.send_photo(chat_id, photo_file, caption=f"🏠 {nearest_shelter['name']}")
            
            # Отправляем информацию о ближайшем убежище
            shelter_text = (
                f"🎯 Ближайшее убежище: {nearest_shelter['name']}\n\n"
                f"📝 {nearest_shelter['description']}\n\n"
                f"📍 Координаты: {nearest_shelter['lat']}, {nearest_shelter['lon']}\n"
                f"🌐 [📍 Показать на карте]({nearest_shelter['map_link']})\n\n"
                f"📏 Примерное расстояние: {min_distance:.2f} км"
            )
            
            bot.send_message(chat_id, shelter_text, parse_mode='Markdown')
            
            # Финальное сообщение
            final_text = "✅ Ближайшее убежище найдено!\n\nСледуйте указанным координатам для быстрого доступа к убежищу."
            bot.send_message(chat_id, final_text, reply_markup=get_main_menu_keyboard())
            
            # Возвращаем в главное меню
            user_states[chat_id] = 'main_menu'
            bot.set_state(chat_id, BotStates.main_menu)
        else:
            bot.send_message(chat_id, "❌ Не удалось найти ближайшее убежище", reply_markup=get_back_keyboard())
            
    except Exception as e:
        log_admin_error("SHELTER_SEARCH_ERROR", e, {
            'chat_id': chat_id,
            'user_lat': user_lat,
            'user_lon': user_lon
        })
        bot.send_message(chat_id, "❌ Ошибка при поиске убежища", reply_markup=get_back_keyboard())

# Функция для завершения сообщения об опасности (использует handlers)
def finish_danger_report_main(chat_id: int, username: str):
    """Завершает процесс сообщения об опасности"""
    if not BOT_TOKEN or not bot:
        logger.warning("BOT_TOKEN не настроен, функция finish_danger_report_main недоступна")
        return
    
    try:
        # Создаем объект message для передачи в handlers
        class MockMessage:
            def __init__(self, chat_id, username):
                self.chat = type('Chat', (), {'id': chat_id})()
                self.from_user = type('User', (), {'username': username})()
        
        mock_message = MockMessage(chat_id, username)
        user_data_for_chat = user_data.get(chat_id, {})
        result = finish_danger_report(mock_message, user_data_for_chat, placeholders)
        
        if isinstance(result, tuple):
            new_state, response = result
            user_states[chat_id] = new_state
            bot.set_state(chat_id, BotStates.main_menu)
            
            if isinstance(response, dict):
                bot.send_message(chat_id, response['text'], reply_markup=response.get('reply_markup'), parse_mode=response.get('parse_mode'))
            else:
                bot.send_message(chat_id, response, reply_markup=get_main_menu_keyboard())
        
    except Exception as e:
        log_admin_error("DANGER_REPORT_FINISH_ERROR", e, {
            'chat_id': chat_id,
            'username': username
        })
        bot.send_message(chat_id, "❌ Ошибка при обработке сообщения", reply_markup=get_main_menu_keyboard())

# Проверка BOT_TOKEN перенесена в основной блок if __name__ == "__main__":

# Настройка логирования и инициализация бота перенесены в основной блок if __name__ == "__main__"

# Глобальные переменные для хранения состояния (инициализируются в основном блоке)
user_states = {}  # chat_id -> текущее состояние
user_data = {}    # chat_id -> данные пользователя
user_history = {} # chat_id -> история действий
bot = None  # Будет инициализирован в основном блоке


# Состояния бота
class BotStates(StatesGroup):
    main_menu = State()
    danger_report = State()
    shelter_finder = State()
    safety_consultant = State()
    improvement_suggestion = State()
    improvement_suggestion_choice = State()
    improvement_suggestion_menu = State()

# Загрузка заглушек
def load_placeholders():
    """Загружает данные-заглушки из JSON файла"""
    try:
        with open('configs/data_placeholders.json', 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        log_admin_error("CONFIG_LOAD_ERROR", e, {
            'config_file': 'configs/data_placeholders.json'
        })
        return {}

placeholders = load_placeholders()


# Обработчики команд (регистрируются только при инициализации бота)
# Обработчик для неинициализированных пользователей
def handle_uninitialized_user(message):
    """Обрабатывает сообщения от неинициализированных пользователей"""
    chat_id = message.chat.id
    username = message.from_user.username or "Unknown"
    user_id = message.from_user.id
    
    logger.info(f"Неинициализированный пользователь {username} ({chat_id}) отправил: {message.text}")
    
    # Инициализируем пользователя
    user_states[chat_id] = 'main_menu'
    user_data[chat_id] = {}
    user_history[chat_id] = []
    bot.set_state(chat_id, BotStates.main_menu)
    
    # Отправляем приветствие
    welcome_text = (
        "👋 Добро пожаловать в бот безопасности РПРЗ!\n\n"
        "Я помогу вам:\n"
        "❗ Сообщить об опасности\n"
        "🏠 Найти ближайшее укрытие\n"
        "🧑‍🏫 Получить консультацию по безопасности\n"
        "💡 Предложить улучшения\n\n"
        "Выберите действие из меню:"
    )
    
    bot.send_message(chat_id, welcome_text, reply_markup=get_main_menu_keyboard())
    log_activity(chat_id, username, "auto_initialization")

def start_command(message):
    """Обработчик команды /start"""
    chat_id = message.chat.id
    username = message.from_user.username or "Unknown"
    user_id = message.from_user.id
    
    logger.info(f"Пользователь {username} ({chat_id}) запустил бота")
    logger.bind(user_id=user_id).info(f"Команда /start от пользователя {username}")
    
    log_activity(chat_id, username, "start")
    
    # Сброс состояния
    user_states[chat_id] = 'main_menu'
    user_data[chat_id] = {}
    user_history[chat_id] = []
    
    logger.debug(f"Состояние пользователя {chat_id} сброшено в main_menu")
    
    bot.set_state(chat_id, BotStates.main_menu)
    
    welcome_text = (
        "👋 Добро пожаловать в бот безопасности РПРЗ!\n\n"
        "Я помогу вам:\n"
        "❗ Сообщить об опасности\n"
        "🏠 Найти ближайшее укрытие\n"
        "🧑‍🏫 Получить консультацию по безопасности\n"
        "💡 Предложить улучшения\n\n"
        "Выберите действие из меню:"
    )
    
    logger.debug(f"Отправка приветственного сообщения пользователю {chat_id}")
    bot.send_message(chat_id, welcome_text, reply_markup=get_main_menu_keyboard())

def help_command(message):
    """Обработчик команды /help"""
    chat_id = message.chat.id
    username = message.from_user.username or "Unknown"
    
    log_activity(chat_id, username, "help")
    
    help_text = (
        "🤖 Справка по боту безопасности РПРЗ\n\n"
        "❗ Сообщите об опасности - зарегистрировать инцидент\n"
        "🏠 Ближайшее укрытие - найти убежище рядом\n"
        "🧑‍🏫 Консультант по безопасности - получить ответы по документации\n"
        "💡 Предложение по улучшению - отправить идею\n\n"
        "Назад - вернуться в главное меню\n"
        "/start - перезапустить бота\n"
        "/help - эта справка"
    )
    
    bot.send_message(chat_id, help_text, reply_markup=get_main_menu_keyboard())

def history_command(message):
    """Показывает историю действий пользователя"""
    chat_id = message.chat.id
    username = message.from_user.username or "Unknown"
    
    log_activity(chat_id, username, "history_request")
    
    try:
        # Читаем историю из CSV
        history_text = "📋 Ваша история действий:\n\n"
        
        if os.path.exists('logs/activity.csv'):
            with open('logs/activity.csv', 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                user_actions = [row for row in reader if int(row['user_id']) == chat_id]
                
                if user_actions:
                    for action in user_actions[-10:]:  # Последние 10 действий
                        timestamp = action['timestamp'][:19]  # Убираем микросекунды
                        history_text += f"🕐 {timestamp}\n"
                        history_text += f"📝 {action['action']}\n"
                        if action['payload']:
                            history_text += f"📄 {action['payload'][:50]}...\n"
                        history_text += "\n"
                else:
                    history_text += "История пуста"
        else:
            history_text += "История не найдена"
        
        bot.send_message(chat_id, history_text, reply_markup=get_main_menu_keyboard())
        
    except Exception as e:
        logger.error(f"Ошибка получения истории: {e}")
        bot.send_message(chat_id, "❌ Ошибка при получении истории", reply_markup=get_main_menu_keyboard())

# Обработчик текстовых сообщений
def handle_text(message):
    """Обработчик текстовых сообщений"""
    chat_id = message.chat.id
    username = message.from_user.username or "Unknown"
    user_id = message.from_user.id
    text = message.text
    
    # Санитизируем и валидируем пользовательский ввод
    sanitized_text = sanitize_user_input(text)
    is_valid, validation_error = validate_user_input(sanitized_text, min_length=1, max_length=1000)
    
    if not is_valid:
        logger.warning(f"Невалидный ввод от {username}: {validation_error}")
        bot.send_message(chat_id, f"❌ {validation_error}")
        return
    
    logger.bind(user_id=user_id).info(f"Получено текстовое сообщение от {username}: {sanitized_text[:100]}...")
    logger.debug(f"Детали сообщения: chat_id={chat_id}, user_id={user_id}, username={username}, text_length={len(sanitized_text)}")
    logger.debug(f"Текущее состояние пользователя: {user_states.get(chat_id, 'None')}")
    
    
    log_activity(chat_id, username, "text_message", sanitized_text)
    
    # Если пользователь не инициализирован, инициализируем его
    if chat_id not in user_states:
        user_states[chat_id] = 'main_menu'
        user_data[chat_id] = {}
        user_history[chat_id] = []
        bot.set_state(chat_id, BotStates.main_menu)
        logger.info(f"Пользователь {username} ({chat_id}) автоматически инициализирован")
    
    # Обработка кнопки "Назад"
    if sanitized_text == "Назад":
        user_states[chat_id] = 'main_menu'
        bot.set_state(chat_id, BotStates.main_menu)
        bot.send_message(chat_id, "🏠 Главное меню:", reply_markup=get_main_menu_keyboard())
        return
    
    # Обработка главного меню (включая случай когда состояние None)
    if user_states.get(chat_id) in ['main_menu', None]:
        logger.bind(user_id=user_id).debug(f"Обработка главного меню для пользователя {username}, состояние: {user_states.get(chat_id)}")
        
        # Если состояние None, устанавливаем main_menu
        if user_states.get(chat_id) is None:
            user_states[chat_id] = 'main_menu'
            bot.set_state(chat_id, BotStates.main_menu)
        
        if sanitized_text == "❗ Сообщите об опасности":
            logger.bind(user_id=user_id).info("Пользователь выбрал 'Сообщить об опасности'")
            start_danger_report(message)
        elif sanitized_text == "🏠 Ближайшее укрытие":
            logger.bind(user_id=user_id).info("Пользователь выбрал 'Ближайшее укрытие'")
            start_shelter_finder(message)
        elif sanitized_text == "🧑‍🏫 Консультант по безопасности РПРЗ":
            logger.bind(user_id=user_id).info("Пользователь выбрал 'Консультант по безопасности'")
            start_safety_consultant(message)
        elif sanitized_text == "💡 Предложение по улучшению":
            logger.bind(user_id=user_id).info("Пользователь выбрал 'Предложение по улучшению'")
            start_improvement_suggestion(message)
        else:
            # Любой другой текст в главном меню - показываем подсказку
            logger.bind(user_id=user_id).warning(f"Неизвестная команда в главном меню: {sanitized_text}")
            bot.send_message(chat_id, "❓ Выберите действие из меню:", reply_markup=get_main_menu_keyboard())
    
    # Обработка состояний
    elif user_states.get(chat_id) == 'danger_report':
        logger.bind(user_id=user_id).debug(f"Обработка состояния 'danger_report' для пользователя {username}")
        result = handle_danger_report_text(message, user_data[chat_id], placeholders)
        if isinstance(result, tuple):
            new_state, response = result
            logger.bind(user_id=user_id).info(f"Переход состояния: {user_states[chat_id]} -> {new_state}")
            user_states[chat_id] = new_state
            if new_state == "main_menu":
                bot.set_state(chat_id, BotStates.main_menu)
                if isinstance(response, dict):
                    bot.send_message(chat_id, response['text'], reply_markup=response.get('reply_markup'), parse_mode=response.get('parse_mode'))
                elif response is not None:
                    bot.send_message(chat_id, response, reply_markup=get_main_menu_keyboard())
                else:
                    bot.send_message(chat_id, "🏠 Главное меню:", reply_markup=get_main_menu_keyboard())
            else:
                if isinstance(response, dict):
                    bot.send_message(chat_id, response['text'], reply_markup=response.get('reply_markup'), parse_mode=response.get('parse_mode'))
                elif response is not None:
                    bot.send_message(chat_id, response, reply_markup=get_back_keyboard())
                else:
                    bot.send_message(chat_id, "❓ Выберите действие:", reply_markup=get_back_keyboard())
        else:
            bot.send_message(chat_id, result, reply_markup=get_back_keyboard())
    
    elif user_states.get(chat_id) == 'shelter_finder':
        if text == "📋 Показать список убежищ":
            show_all_shelters(chat_id)
        elif text == "📍 Отправить геолокацию":
            bot.send_message(chat_id, "📍 Нажмите кнопку 'Отправить геолокацию' для поиска ближайшего убежища")
        else:
            bot.send_message(chat_id, "❓ Выберите действие из меню:", reply_markup=get_back_keyboard())
    
    elif user_states.get(chat_id) == 'safety_consultant':
        result = handle_safety_consultant_text(message, placeholders)
        if isinstance(result, tuple):
            new_state, response = result
            user_states[chat_id] = new_state
            if new_state == "main_menu":
                bot.set_state(chat_id, BotStates.main_menu)
                if isinstance(response, dict):
                    bot.send_message(chat_id, response['text'], reply_markup=response.get('reply_markup'), parse_mode=response.get('parse_mode'))
                elif response is not None:
                    bot.send_message(chat_id, response, reply_markup=get_main_menu_keyboard())
                else:
                    bot.send_message(chat_id, "🏠 Главное меню:", reply_markup=get_main_menu_keyboard())
            else:
                # Если переходим в режим вопросов, устанавливаем шаг
                if text == "❓ Задать вопрос":
                    user_data[chat_id]['step'] = 'question'
                
                # Обработка отправки документов
                if isinstance(response, dict) and response.get('action') == 'send_documents':
                    documents = response.get('documents', [])
                    try:
                        for i, doc in enumerate(documents, 1):
                            # Отправляем PDF файл
                            file_path = doc.get('file_path', '')
                            if file_path and os.path.exists(file_path):
                                with open(file_path, 'rb') as pdf_file:
                                    bot.send_document(chat_id, pdf_file, caption=f"📄 {doc['title']}")
                            
                            # Отправляем описание документа
                            doc_text = (
                                f"{doc['title']}\n\n"
                                f"📝 {doc['description']}\n\n"
                                f"📎 Документ отправлен выше"
                            )
                            bot.send_message(chat_id, doc_text, parse_mode='Markdown')
                        
                        # Финальное сообщение
                        final_text = "✅ Отправлено документов: 5\n\nВсе документы по безопасности РПРЗ готовы к изучению."
                        bot.send_message(chat_id, final_text, reply_markup=get_main_menu_keyboard())
                        
                        user_states[chat_id] = 'main_menu'
                        bot.set_state(chat_id, BotStates.main_menu)
                        
                    except Exception as e:
                        logger.error(f"Ошибка при отправке документов: {e}")
                        bot.send_message(chat_id, "❌ Ошибка при загрузке документов", reply_markup=get_main_menu_keyboard())
                        user_states[chat_id] = 'main_menu'
                        bot.set_state(chat_id, BotStates.main_menu)
                elif isinstance(response, dict):
                    bot.send_message(chat_id, response['text'], reply_markup=response.get('reply_markup'), parse_mode=response.get('parse_mode'))
                elif response is not None:
                    bot.send_message(chat_id, response, reply_markup=get_back_keyboard())
                else:
                    bot.send_message(chat_id, "❓ Выберите действие:", reply_markup=get_back_keyboard())
        else:
            # Обработка вопросов
            if user_data.get(chat_id, {}).get('step') == 'question':
                result = handle_safety_question(message, placeholders)
                if isinstance(result, tuple):
                    new_state, response = result
                    if isinstance(response, dict):
                        bot.send_message(chat_id, response['text'], reply_markup=response.get('reply_markup'), parse_mode=response.get('parse_mode'))
                    else:
                        bot.send_message(chat_id, response, reply_markup=get_back_keyboard())
                else:
                    bot.send_message(chat_id, result, reply_markup=get_back_keyboard())
            else:
                # Если это не кнопка меню, то это вопрос
                user_data[chat_id]['step'] = 'question'
                result = handle_safety_question(message, placeholders)
                if isinstance(result, tuple):
                    new_state, response = result
                    if isinstance(response, dict):
                        bot.send_message(chat_id, response['text'], reply_markup=response.get('reply_markup'), parse_mode=response.get('parse_mode'))
                    else:
                        bot.send_message(chat_id, response, reply_markup=get_back_keyboard())
                else:
                    bot.send_message(chat_id, result, reply_markup=get_back_keyboard())
    
    elif user_states.get(chat_id) == 'improvement_suggestion_choice':
        result = handle_improvement_suggestion_choice(message, placeholders)
        if isinstance(result, tuple):
            new_state, response = result
            user_states[chat_id] = new_state
            if new_state == "main_menu":
                bot.set_state(chat_id, BotStates.main_menu)
                if isinstance(response, dict):
                    bot.send_message(chat_id, response['text'], reply_markup=response.get('reply_markup'))
                elif response is not None:
                    bot.send_message(chat_id, response, reply_markup=get_main_menu_keyboard())
                else:
                    bot.send_message(chat_id, "🏠 Главное меню:", reply_markup=get_main_menu_keyboard())
            elif new_state == "improvement_suggestion":
                bot.set_state(chat_id, BotStates.improvement_suggestion)
                # Обновляем user_data с категорией из response
                if isinstance(response, dict):
                    user_data[chat_id] = {
                        'step': 'suggestion', 
                        'category': response.get('category', 'Общее')
                    }
                    bot.send_message(chat_id, response['text'], reply_markup=response.get('reply_markup'))
                else:
                    bot.send_message(chat_id, response, reply_markup=get_back_keyboard())
            else:
                if isinstance(response, dict):
                    bot.send_message(chat_id, response['text'], reply_markup=response.get('reply_markup'))
                elif response is not None:
                    bot.send_message(chat_id, response, reply_markup=get_back_keyboard())
                else:
                    bot.send_message(chat_id, "❓ Выберите действие:", reply_markup=get_back_keyboard())
        else:
            bot.send_message(chat_id, result, reply_markup=get_back_keyboard())
    
    elif user_states.get(chat_id) == 'improvement_suggestion':
        result = handle_improvement_suggestion_text(message, placeholders, user_data)
        if isinstance(result, tuple):
            new_state, response = result
            user_states[chat_id] = new_state
            if new_state == "main_menu":
                bot.set_state(chat_id, BotStates.main_menu)
                if isinstance(response, dict):
                    bot.send_message(chat_id, response['text'], reply_markup=response.get('reply_markup'))
                elif response is not None:
                    bot.send_message(chat_id, response, reply_markup=get_main_menu_keyboard())
                else:
                    bot.send_message(chat_id, "🏠 Главное меню:", reply_markup=get_main_menu_keyboard())
            elif new_state == "improvement_suggestion_choice":
                bot.set_state(chat_id, BotStates.improvement_suggestion_choice)
                # Возвращаем к выбору категории
                start_improvement_suggestion(message)
            elif new_state == "improvement_suggestion_menu":
                bot.set_state(chat_id, BotStates.improvement_suggestion_menu)
                if isinstance(response, dict):
                    bot.send_message(chat_id, response['text'], reply_markup=response.get('reply_markup'))
                else:
                    # Создаем правильную клавиатуру для меню предложений
                    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
                    markup.add(
                        types.KeyboardButton("📊 Посмотреть мои предложения"),
                        types.KeyboardButton("📝 Отправить еще предложение"),
                        types.KeyboardButton("🏠 Главное меню")
                    )
                    bot.send_message(chat_id, response, reply_markup=markup)
            else:
                if isinstance(response, dict):
                    bot.send_message(chat_id, response['text'], reply_markup=response.get('reply_markup'))
                elif response is not None:
                    bot.send_message(chat_id, response, reply_markup=get_back_keyboard())
                else:
                    bot.send_message(chat_id, "❓ Выберите действие:", reply_markup=get_back_keyboard())
        else:
            bot.send_message(chat_id, result, reply_markup=get_back_keyboard())
    
    elif user_states.get(chat_id) == 'improvement_suggestion_menu':
        result = handle_suggestion_menu(message, placeholders)
        if isinstance(result, tuple):
            new_state, response = result
            user_states[chat_id] = new_state
            if new_state == "main_menu":
                bot.set_state(chat_id, BotStates.main_menu)
                if isinstance(response, dict):
                    bot.send_message(chat_id, response['text'], reply_markup=response.get('reply_markup'))
                elif response is not None:
                    bot.send_message(chat_id, response, reply_markup=get_main_menu_keyboard())
                else:
                    bot.send_message(chat_id, "🏠 Главное меню:", reply_markup=get_main_menu_keyboard())
            elif new_state == "improvement_suggestion":
                bot.set_state(chat_id, BotStates.improvement_suggestion)
                if isinstance(response, dict):
                    bot.send_message(chat_id, response['text'], reply_markup=response.get('reply_markup'))
                elif response is not None:
                    bot.send_message(chat_id, response, reply_markup=get_back_keyboard())
                else:
                    bot.send_message(chat_id, "❓ Выберите действие:", reply_markup=get_back_keyboard())
            else:
                if isinstance(response, dict):
                    bot.send_message(chat_id, response['text'], reply_markup=response.get('reply_markup'))
                else:
                    # Создаем правильную клавиатуру для меню предложений
                    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
                    markup.add(
                        types.KeyboardButton("📊 Посмотреть мои предложения"),
                        types.KeyboardButton("🏆 Популярные предложения"),
                        types.KeyboardButton("📝 Отправить еще предложение"),
                        types.KeyboardButton("🏠 Главное меню")
                    )
                    bot.send_message(chat_id, response, reply_markup=markup)
        else:
            # Создаем правильную клавиатуру для меню предложений
            markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
            markup.add(
                types.KeyboardButton("📊 Посмотреть мои предложения"),
                types.KeyboardButton("🏆 Популярные предложения"),
                types.KeyboardButton("📝 Отправить еще предложение"),
                types.KeyboardButton("🏠 Главное меню")
            )
            bot.send_message(chat_id, result, reply_markup=markup)

# Функции для каждого раздела будут добавлены в следующих этапах
def start_danger_report(message):
    """Начало процесса сообщения об опасности"""
    chat_id = message.chat.id
    username = message.from_user.username or "Unknown"
    
    log_activity(chat_id, username, "danger_report_start")
    
    # Устанавливаем состояние для сообщения об опасности
    user_states[chat_id] = 'danger_report'
    user_data[chat_id] = {'step': 'description', 'description': '', 'location': None}
    bot.set_state(chat_id, BotStates.danger_report)
    
    bot.send_message(
        chat_id,
        "❗ Сообщите об опасности\n\n"
        "📝 Опишите, что произошло, максимум 500 символов, и написать «Ваше сообщение будет отправлено в службу безопасности для оперативного реагирования». Пожалуйста, не используйте это сообщение просто так или как спам-рассылку.\n\n"
        
        "Введите текст с описанием места. Пример нужен – ЦГТ-025, 4-й участок.\n"
        "Прикрепите, пожалуйста, фото или видео. Ваше фото облегчит или ускорит решение вопроса.\n\n"
        "📝 Опишите что произошло (максимум 500 символов):",
        reply_markup=get_back_keyboard()
    )

def start_shelter_finder(message):
    """Начало поиска ближайшего укрытия"""
    chat_id = message.chat.id
    username = message.from_user.username or "Unknown"
    
    log_activity(chat_id, username, "shelter_finder_start")
    
    user_states[chat_id] = 'shelter_finder'
    bot.set_state(chat_id, BotStates.shelter_finder)
    
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add(
        types.KeyboardButton("📍 Отправить геолокацию", request_location=True),
        types.KeyboardButton("📋 Показать список убежищ"),
        types.KeyboardButton("Назад")
    )
    
    bot.send_message(
        chat_id,
        "🏠 Поиск ближайшего укрытия\n\n"
        "Выберите действие:",
        reply_markup=markup
    )

def start_safety_consultant(message):
    """Начало работы с консультантом по безопасности"""
    chat_id = message.chat.id
    username = message.from_user.username or "Unknown"
    
    log_activity(chat_id, username, "safety_consultant_start")
    
    user_states[chat_id] = 'safety_consultant'
    bot.set_state(chat_id, BotStates.safety_consultant)
    
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add(
        types.KeyboardButton("📄 Список документов"),
        types.KeyboardButton("❓ Задать вопрос"),
        types.KeyboardButton("Назад")
    )
    
    bot.send_message(
        chat_id,
        "🧑‍🏫 Консультант по безопасности РПРЗ\n\n"
        "Выберите действие:",
        reply_markup=markup
    )

def start_improvement_suggestion(message):
    """Начало отправки предложения по улучшению с вариантами"""
    chat_id = message.chat.id
    username = message.from_user.username or "Unknown"
    
    log_activity(chat_id, username, "improvement_suggestion_start")
    
    user_states[chat_id] = 'improvement_suggestion_choice'
    user_data[chat_id] = {'step': 'choice'}
    bot.set_state(chat_id, BotStates.improvement_suggestion_choice)
    
    # Создаем клавиатуру с вариантами предложений
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add(
        types.KeyboardButton("🛡️ Безопасность и защита"),
        types.KeyboardButton("🎨 Интерфейс и дизайн"),
        types.KeyboardButton("⚡ Производительность"),
        types.KeyboardButton("🔔 Уведомления"),
        types.KeyboardButton("🔧 Функциональность"),
        types.KeyboardButton("💭 Свободная форма")
    )
    markup.add(types.KeyboardButton("🏠 Главное меню"))
    
    welcome_text = (
        "💡 Предложение по улучшению проекта\n\n"
        "🎯 Выберите категорию для вашего предложения:\n\n"
        "🛡️ Безопасность и защита - новые функции безопасности\n"
        "🎨 Интерфейс и дизайн - улучшение внешнего вида\n"
        "⚡ Производительность - оптимизация скорости работы\n"
        "🔔 Уведомления - новые способы оповещения\n"
        "🔧 Функциональность - дополнительные возможности\n"
        "💭 Свободная форма - опишите свое предложение\n\n"
        "🏆 Лучшие предложения будут предложены на общем голосовании!"
    )
    
    bot.send_message(
        chat_id,
        welcome_text,
        reply_markup=markup
    )

# Обработчик геолокации
def handle_location(message):
    """Обработчик геолокации"""
    chat_id = message.chat.id
    username = message.from_user.username or "Unknown"
    user_id = message.from_user.id
    user_lat = message.location.latitude
    user_lon = message.location.longitude
    
    logger.bind(user_id=user_id).info(f"Получена геолокация от {username}: {user_lat}, {user_lon}")
    
    if user_states.get(chat_id) == 'shelter_finder':
        # Ищем ближайшее убежище по геолокации
        logger.bind(user_id=user_id).info("Поиск ближайшего убежища по геолокации")
        find_nearest_shelter(chat_id, user_lat, user_lon)
    elif user_states.get(chat_id) == 'danger_report':
        # Обрабатываем геолокацию через handlers
        logger.bind(user_id=user_id).info("Обработка геолокации для сообщения об опасности")
        result = handle_danger_report_location(message, user_data[chat_id])
        if isinstance(result, dict):
            bot.send_message(chat_id, result['text'], reply_markup=result.get('reply_markup'), parse_mode=result.get('parse_mode'))
    else:
        logger.bind(user_id=user_id).warning(f"Геолокация получена в неподходящем состоянии: {user_states.get(chat_id)}")
        bot.send_message(chat_id, "❌ Геолокация не нужна в текущем режиме")

# Обработчик медиафайлов
def handle_media(message):
    """Обработчик медиафайлов"""
    chat_id = message.chat.id
    username = message.from_user.username or "Unknown"
    user_id = message.from_user.id
    content_type = message.content_type
    
    logger.bind(user_id=user_id).info(f"Получен медиафайл от {username}: {content_type}")
    
    if user_states.get(chat_id) == 'danger_report':
        logger.bind(user_id=user_id).info("Обработка медиафайла для сообщения об опасности")
        result = handle_danger_report_media(message, user_data[chat_id], MAX_FILE_SIZE_MB, MAX_VIDEO_SIZE_MB)
        bot.send_message(chat_id, result, reply_markup=get_media_keyboard())
    else:
        logger.bind(user_id=user_id).warning(f"Медиафайл получен в неподходящем состоянии: {user_states.get(chat_id)}")
        bot.send_message(chat_id, "❌ Медиафайлы можно прикреплять только при сообщении об опасности")

# Основной цикл
if __name__ == '__main__':
    # Проверка блокировки процесса
    logger.info("🔍 Проверка блокировки процесса...")
    if not create_process_lock():
        logger.error("❌ Не удалось создать блокировку процесса")
        logger.info("💡 Возможно, уже запущен другой экземпляр бота")
        sys.exit(1)
    
    # Настройка подробного логирования
    os.makedirs('logs', exist_ok=True)

    # Основной лог файл
    logger.add("logs/app.log", 
              format="{time:YYYY-MM-DD HH:mm:ss.SSS} | {level: <8} | {name}:{function}:{line} - {message}", 
              level="DEBUG", 
              rotation="10 MB", 
              compression="zip", 
              encoding="utf-8",
              errors="replace")

    # Отдельный лог для ошибок с детальной информацией
    logger.add("logs/errors.log", 
              format="{time:YYYY-MM-DD HH:mm:ss.SSS} | {level: <8} | {name}:{function}:{line} - {message}", 
              level="ERROR", 
              rotation="10 MB", 
              compression="zip", 
              encoding="utf-8",
              errors="replace")

    # Лог для критических ошибок админа
    logger.add("logs/admin_critical.log", 
              format="{time:YYYY-MM-DD HH:mm:ss.SSS} | CRITICAL | {name}:{function}:{line} - {message}", 
              level="CRITICAL", 
              rotation="5 MB", 
              compression="zip", 
              encoding="utf-8",
              errors="replace",
              filter=lambda record: record["level"].name == "CRITICAL")

    # Лог для системных ошибок
    logger.add("logs/system_errors.log", 
              format="{time:YYYY-MM-DD HH:mm:ss.SSS} | SYSTEM | {extra[error_type]} | {name}:{function}:{line} - {message}", 
              level="ERROR", 
              rotation="5 MB", 
              compression="zip", 
              encoding="utf-8",
              errors="replace",
              filter=lambda record: "error_type" in record["extra"])

    # Лог для пользовательских действий
    logger.add("logs/user_actions.log", 
              format="{time:YYYY-MM-DD HH:mm:ss.SSS} | USER:{extra[user_id]} | {message}", 
              level="INFO", 
              rotation="5 MB", 
              compression="zip", 
              encoding="utf-8",
              errors="replace",
              filter=lambda record: "user_id" in record["extra"])

    # Лог для API запросов
    logger.add("logs/api_requests.log", 
              format="{time:YYYY-MM-DD HH:mm:ss.SSS} | API | {message}", 
              level="DEBUG", 
              rotation="5 MB", 
              compression="zip", 
              encoding="utf-8",
              errors="replace")

    logger.info("Запуск MVP бота безопасности РПРЗ")
    
    # Проверяем наличие токена
    if not BOT_TOKEN or BOT_TOKEN == 'your_telegram_bot_token_here':
        log_admin_error("CONFIG_ERROR", Exception("BOT_TOKEN не найден"), {
            'config_file': '.env',
            'required_vars': ['BOT_TOKEN', 'ADMIN_CHAT_ID']
        })
        logger.error("❌ BOT_TOKEN не настроен! Создайте файл .env с токеном бота")
        logger.info("📝 Пример содержимого .env:")
        logger.info("BOT_TOKEN=1234567890:ABCdefGHIjklMNOpqrsTUVwxyz")
        logger.info("ADMIN_CHAT_ID=123456789")
        sys.exit(1)
    
    # Инициализация бота
    state_storage = StateMemoryStorage()
    bot = telebot.TeleBot(BOT_TOKEN, state_storage=state_storage)
    
    # Устанавливаем глобальный экземпляр бота для handlers
    set_bot_instance(bot)
    
    # Устанавливаем глобальный экземпляр бота для yandex_notifications
    try:
        from yandex_notifications import set_bot_instance as set_yandex_bot_instance
        set_yandex_bot_instance(bot)
        logger.info("✅ Bot instance установлен для yandex_notifications")
    except ImportError:
        logger.warning("⚠️ Не удалось установить bot instance для yandex_notifications")
    
    # Регистрируем обработчики
    bot.message_handler(func=lambda message: message.chat.id not in user_states and message.content_type == 'text' and not message.text.startswith('/'))(handle_uninitialized_user)
    bot.message_handler(commands=['start'])(start_command)
    bot.message_handler(commands=['help'])(help_command)
    bot.message_handler(commands=['my_history'])(history_command)
    bot.message_handler(content_types=['text'])(handle_text)
    bot.message_handler(content_types=['location'])(handle_location)
    bot.message_handler(content_types=['photo', 'video', 'document'])(handle_media)
    
    try:
        # Настройка SSL контекста для обхода проблем с сертификатами
        ssl_context = ssl.create_default_context()
        ssl_context.check_hostname = False
        ssl_context.verify_mode = ssl.CERT_NONE
        
        # Тестируем подключение к боту
        logger.info("Проверка подключения к Telegram API...")
        bot_info = bot.get_me()
        logger.info(f"Бот подключен: @{bot_info.username}")
        logger.info(f"Токен: {mask_sensitive_data(BOT_TOKEN)}")
        
        # Очищаем webhook перед запуском polling
        logger.info("Очистка webhook...")
        try:
            bot.remove_webhook()
            logger.info("Webhook очищен")
        except Exception as e:
            logger.warning(f"Не удалось очистить webhook: {e}")
        
        # Проверяем и останавливаем другие экземпляры бота
        logger.info("Проверка на конфликтующие экземпляры...")
        try:
            import psutil
            python_processes = [p for p in psutil.process_iter(['pid', 'name', 'cmdline']) 
                              if p.info['name'] == 'python.exe' and 
                              'main.py' in ' '.join(p.info['cmdline'] or [])]
            
            if len(python_processes) > 1:
                logger.warning(f"Найдено {len(python_processes)} экземпляров Python с main.py")
                for proc in python_processes[1:]:  # Оставляем первый, остальные убиваем
                    try:
                        proc.terminate()
                        logger.info(f"Остановлен процесс {proc.info['pid']}")
                    except:
                        pass
                time.sleep(2)
        except ImportError:
            logger.warning("psutil не установлен, пропускаем проверку процессов")
        except Exception as e:
            logger.warning(f"Ошибка проверки процессов: {e}")
        
        # Ждем немного перед запуском
        logger.info("Ожидание 3 секунды...")
        time.sleep(3)
        
        logger.info("Запуск polling...")
        logger.info(f"Настройки polling: interval=3, timeout=20, none_stop=True")
        
        try:
            bot.polling(none_stop=True, interval=3, timeout=20)
        except Exception as polling_error:
            error_str = str(polling_error)
            log_admin_error("BOT_POLLING_ERROR", polling_error, {
                'error_type': 'polling_critical',
                'bot_token_masked': mask_sensitive_data(BOT_TOKEN)
            })
            
            if "409" in error_str or "Conflict" in error_str:
                log_admin_error("BOT_INSTANCE_CONFLICT", polling_error, {
                    'error_type': 'instance_conflict',
                    'recommended_actions': [
                        'Остановить все процессы Python',
                        'Перезагрузить компьютер',
                        'Подождать 2-3 минуты'
                    ]
                })
                
                # Пытаемся остановить процессы автоматически
                try:
                    import subprocess
                    logger.info("🔄 Попытка автоматической остановки процессов...")
                    
                    # Безопасная остановка процессов через psutil
                    try:
                        import psutil
                        for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
                            if (proc.info['name'] == 'python.exe' and 
                                'main.py' in ' '.join(proc.info['cmdline'] or [])):
                                try:
                                    proc.terminate()
                                    logger.info(f"Остановлен процесс {proc.info['pid']}")
                                except:
                                    pass
                    except ImportError:
                        logger.warning("psutil не установлен, пропускаем автоматическую остановку")
                        pass
                    
                    logger.info("⏳ Ожидание 5 секунд...")
                    time.sleep(5)
                    
                    # Очищаем webhook еще раз
                    try:
                        bot.remove_webhook()
                        logger.info("Webhook очищен повторно")
                    except:
                        pass
                    
                    logger.info("🔄 Повторная попытка запуска...")
                    bot.polling(none_stop=True, interval=3, timeout=20)
                    
                except Exception as auto_stop_error:
                    logger.error(f"❌ Ошибка автоматической остановки: {auto_stop_error}")
                    logger.info("🔄 Попробуйте запустить restart_clean.py")
                    sys.exit(1)
            else:
                logger.error(f"❌ Неизвестная ошибка polling: {polling_error}")
                sys.exit(1)
        
    except KeyboardInterrupt:
        logger.info("⏹️ Остановка бота пользователем")
        remove_process_lock()
        sys.exit(0)
    except ssl.SSLError as e:
        logger.error(f"❌ SSL ошибка: {e}")
        logger.info("💡 Попробуйте обновить сертификаты или использовать VPN")
        remove_process_lock()
        sys.exit(1)
    except Exception as e:
        logger.error(f"❌ Ошибка запуска бота: {e}")
        logger.info("💡 Проверьте правильность BOT_TOKEN в файле .env")
        remove_process_lock()
        sys.exit(1)
