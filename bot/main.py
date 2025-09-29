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
import threading
from datetime import datetime
from typing import Dict, List, Optional

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
    get_back_keyboard, get_main_menu_keyboard, get_media_keyboard,
    handle_danger_report_text, handle_danger_report_location, handle_danger_report_media, finish_danger_report,
    handle_shelter_finder_text, handle_shelter_finder_location, show_shelters_list,
    handle_safety_consultant_text, show_documents_list, start_question_mode, handle_safety_question,
    handle_improvement_suggestion_text
)

# Загрузка переменных окружения
load_dotenv()

# Конфигурация
BOT_TOKEN = os.getenv('BOT_TOKEN')
ADMIN_CHAT_ID = os.getenv('ADMIN_CHAT_ID')
LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')
MAX_FILE_SIZE_MB = int(os.getenv('MAX_FILE_SIZE_MB', '20'))
MAX_VIDEO_SIZE_MB = int(os.getenv('MAX_VIDEO_SIZE_MB', '300'))
SPAM_LIMIT = int(os.getenv('SPAM_LIMIT', '5'))

# Email конфигурация
EMAIL_HOST = os.getenv('EMAIL_HOST', 'smtp.yandex.ru')
EMAIL_PORT = int(os.getenv('EMAIL_PORT', '587'))
EMAIL_USE_TLS = os.getenv('EMAIL_USE_TLS', 'True').lower() == 'true'
EMAIL_USE_SSL = os.getenv('EMAIL_USE_SSL', 'False').lower() == 'true'
EMAIL_HOST_USER = os.getenv('EMAIL_HOST_USER', 'MidLNight1@yandex.ru')
EMAIL_HOST_PASSWORD = os.getenv('EMAIL_HOST_PASSWORD', 'fiaerpvcfirnsfqo')
DEFAULT_FROM_EMAIL = os.getenv('DEFAULT_FROM_EMAIL', EMAIL_HOST_USER)

# Функция для маскирования чувствительных данных
def mask_sensitive_data(text: str) -> str:
    """Маскирует чувствительные данные в логах"""
    if not text:
        return text
    
    # Маскируем токен бота (формат: 123456789:ABCdefGHIjklMNOpqrsTUVwxyz)
    if ':' in text and len(text) > 20:
        parts = text.split(':')
        if len(parts) == 2 and parts[0].isdigit():
            return f"{parts[0]}:***{parts[1][-4:]}"
    
    # Маскируем длинные строки (возможно токены)
    if len(text) > 20:
        return f"{text[:8]}***{text[-4:]}"
    
    return text

# Функция для ограничения скорости ответов
def rate_limit_response(chat_id: int, min_interval: float = 0.5) -> bool:
    """Проверяет, можно ли отправить ответ (не чаще min_interval секунд)"""
    with response_lock:
        now = time.time()
        last_response = response_timestamps.get(chat_id, 0)
        
        if now - last_response < min_interval:
            return False
        
        response_timestamps[chat_id] = now
        return True

# Функция для безопасной отправки сообщений с ограничением скорости
def safe_send_message(chat_id: int, text: str, reply_markup=None, parse_mode=None, **kwargs):
    """Отправляет сообщение с ограничением скорости"""
    logger.debug(f"Попытка отправки сообщения пользователю {chat_id}: {text[:50]}...")
    
    if not rate_limit_response(chat_id):
        logger.warning(f"Сообщение для {chat_id} пропущено из-за ограничения скорости")
        return None
    
    try:
        # Логируем детали запроса
        logger.debug(f"Отправка сообщения: chat_id={chat_id}, text_length={len(text)}, parse_mode={parse_mode}")
        
        result = bot.send_message(chat_id, text, reply_markup=reply_markup, parse_mode=parse_mode, **kwargs)
        logger.info(f"Сообщение успешно отправлено пользователю {chat_id}")
        logger.debug(f"Результат отправки: message_id={result.message_id if result else 'None'}")
        return result
    except Exception as e:
        logger.error(f"Ошибка отправки сообщения пользователю {chat_id}: {e}")
        logger.debug(f"Детали ошибки: {type(e).__name__}: {str(e)}")
        
        # Специальная обработка для ошибки 409
        if "409" in str(e) or "Conflict" in str(e):
            logger.error("🚨 Обнаружена ошибка 409 - конфликт экземпляров бота!")
            logger.info("💡 Рекомендация: остановите все экземпляры бота и перезапустите")
        
        return None

# Функция для отправки email уведомлений
def send_email_notification(subject: str, message: str, to_email: str = None):
    """Отправляет email уведомление о нарушении"""
    try:
        import smtplib
        from email.mime.text import MIMEText
        from email.mime.multipart import MIMEMultipart
        
        if not to_email:
            to_email = "MidLNight1@yandex.ru"  # Используем email для уведомлений
        
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
        logger.error(f"Ошибка отправки email: {e}")
        return False

# Функция для показа всех убежищ
def show_all_shelters(chat_id: int):
    """Показывает список всех убежищ"""
    try:
        shelters = placeholders.get('shelters', [])
        
        if not shelters:
            safe_send_message(chat_id, "❌ Список убежищ недоступен", reply_markup=get_back_keyboard())
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
                f"**{shelter['name']}**\n\n"
                f"📝 {shelter['description']}\n\n"
                f"📍 Координаты: {shelter['lat']}, {shelter['lon']}\n"
                f"🌐 [📍 Показать на карте]({shelter['map_link']})"
            )
            
            safe_send_message(chat_id, shelter_text, parse_mode='Markdown')
        
        # Финальное сообщение
        final_text = f"✅ **Найдено убежищ: {len(shelters)}**\n\nВсе убежища оснащены современными системами безопасности и готовы к использованию."
        safe_send_message(chat_id, final_text, reply_markup=get_back_keyboard())
        
    except Exception as e:
        logger.error(f"Ошибка при показе убежищ: {e}")
        safe_send_message(chat_id, "❌ Ошибка при загрузке информации об убежищах", reply_markup=get_back_keyboard())

# Функция для поиска ближайшего убежища по геолокации
def find_nearest_shelter(chat_id: int, user_lat: float, user_lon: float):
    """Находит ближайшее убежище по координатам пользователя"""
    try:
        shelters = placeholders.get('shelters', [])
        
        if not shelters:
            safe_send_message(chat_id, "❌ Список убежищ недоступен", reply_markup=get_back_keyboard())
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
                f"🎯 **Ближайшее убежище: {nearest_shelter['name']}**\n\n"
                f"📝 {nearest_shelter['description']}\n\n"
                f"📍 Координаты: {nearest_shelter['lat']}, {nearest_shelter['lon']}\n"
                f"🌐 [📍 Показать на карте]({nearest_shelter['map_link']})\n\n"
                f"📏 Примерное расстояние: {min_distance:.2f} км"
            )
            
            safe_send_message(chat_id, shelter_text, parse_mode='Markdown')
            
            # Финальное сообщение
            final_text = "✅ **Ближайшее убежище найдено!**\n\nСледуйте указанным координатам для быстрого доступа к убежищу."
            safe_send_message(chat_id, final_text, reply_markup=get_main_menu_keyboard())
            
            # Возвращаем в главное меню
            user_states[chat_id] = 'main_menu'
            bot.set_state(chat_id, BotStates.main_menu)
        else:
            safe_send_message(chat_id, "❌ Не удалось найти ближайшее убежище", reply_markup=get_back_keyboard())
            
    except Exception as e:
        logger.error(f"Ошибка при поиске ближайшего убежища: {e}")
        safe_send_message(chat_id, "❌ Ошибка при поиске убежища", reply_markup=get_back_keyboard())

# Функция для завершения сообщения об опасности (использует handlers)
def finish_danger_report_main(chat_id: int, username: str):
    """Завершает процесс сообщения об опасности"""
    try:
        # Создаем объект message для передачи в handlers
        class MockMessage:
            def __init__(self, chat_id, username):
                self.chat = type('Chat', (), {'id': chat_id})()
                self.from_user = type('User', (), {'username': username})()
        
        mock_message = MockMessage(chat_id, username)
        result = finish_danger_report(mock_message, user_data[chat_id], placeholders)
        
        if isinstance(result, tuple):
            new_state, response = result
            user_states[chat_id] = new_state
            bot.set_state(chat_id, BotStates.main_menu)
            
            if isinstance(response, dict):
                safe_send_message(chat_id, response['text'], reply_markup=response.get('reply_markup'), parse_mode=response.get('parse_mode'))
            else:
                safe_send_message(chat_id, response, reply_markup=get_main_menu_keyboard())
        
    except Exception as e:
        logger.error(f"Ошибка при завершении сообщения об опасности: {e}")
        safe_send_message(chat_id, "❌ Ошибка при обработке сообщения", reply_markup=get_main_menu_keyboard())

if not BOT_TOKEN:
    logger.error("BOT_TOKEN не найден в переменных окружения!")
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

# Отдельный лог для ошибок
logger.add("logs/errors.log", 
          format="{time:YYYY-MM-DD HH:mm:ss.SSS} | {level: <8} | {name}:{function}:{line} - {message}", 
          level="ERROR", 
          rotation="5 MB", 
          compression="zip", 
          encoding="utf-8",
          errors="replace")

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

# Инициализация бота
state_storage = StateMemoryStorage()
bot = telebot.TeleBot(BOT_TOKEN, state_storage=state_storage)

# Глобальные переменные для хранения состояния
user_states = {}  # chat_id -> текущее состояние
user_data = {}    # chat_id -> данные пользователя
user_history = {} # chat_id -> история действий
spam_protection = {}  # chat_id -> счетчик сообщений

# Система ограничения скорости ответов
response_timestamps = {}  # chat_id -> последнее время ответа
response_lock = threading.Lock()  # Блокировка для потокобезопасности

# Состояния бота
class BotStates(StatesGroup):
    main_menu = State()
    danger_report = State()
    shelter_finder = State()
    safety_consultant = State()
    improvement_suggestion = State()

# Загрузка заглушек
def load_placeholders():
    """Загружает данные-заглушки из JSON файла"""
    try:
        with open('configs/data_placeholders.json', 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        logger.error(f"Ошибка загрузки заглушек: {e}")
        return {}

placeholders = load_placeholders()

# Проверка спама
def check_spam(chat_id: int) -> bool:
    """Проверяет, не превышен ли лимит сообщений"""
    now = datetime.now()
    if chat_id not in spam_protection:
        spam_protection[chat_id] = {'count': 0, 'last_reset': now}
    
    # Сбрасываем счетчик каждую минуту
    if (now - spam_protection[chat_id]['last_reset']).seconds > 30:
        spam_protection[chat_id] = {'count': 0, 'last_reset': now}
    
    spam_protection[chat_id]['count'] += 1
    return spam_protection[chat_id]['count'] > SPAM_LIMIT

# Обработчики команд
@bot.message_handler(commands=['start'])
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
    safe_send_message(chat_id, welcome_text, reply_markup=get_main_menu_keyboard())

@bot.message_handler(commands=['help'])
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
    
    safe_send_message(chat_id, help_text, reply_markup=get_main_menu_keyboard())

@bot.message_handler(commands=['my_history'])
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
        
        safe_send_message(chat_id, history_text, reply_markup=get_main_menu_keyboard())
        
    except Exception as e:
        logger.error(f"Ошибка получения истории: {e}")
        safe_send_message(chat_id, "❌ Ошибка при получении истории", reply_markup=get_main_menu_keyboard())

# Обработчик текстовых сообщений
@bot.message_handler(content_types=['text'])
def handle_text(message):
    """Обработчик текстовых сообщений"""
    chat_id = message.chat.id
    username = message.from_user.username or "Unknown"
    user_id = message.from_user.id
    text = message.text
    
    logger.bind(user_id=user_id).info(f"Получено текстовое сообщение от {username}: {text[:100]}...")
    logger.debug(f"Детали сообщения: chat_id={chat_id}, user_id={user_id}, username={username}, text_length={len(text)}")
    logger.debug(f"Текущее состояние пользователя: {user_states.get(chat_id, 'None')}")
    
    # Проверка спама
    if check_spam(chat_id):
        logger.warning(f"Спам-защита сработала для пользователя {chat_id} ({username})")
        logger.debug(f"Счетчик спама: {spam_protection.get(chat_id, {}).get('count', 0)}")
        safe_send_message(chat_id, "⚠️ Слишком много сообщений! Подождите минуту.")
        return
    
    log_activity(chat_id, username, "text_message", text)
    
    # Обработка кнопки "Назад"
    if text == "Назад":
        user_states[chat_id] = 'main_menu'
        bot.set_state(chat_id, BotStates.main_menu)
        safe_send_message(chat_id, "🏠 Главное меню:", reply_markup=get_main_menu_keyboard())
        return
    
    # Обработка главного меню
    if user_states.get(chat_id) == 'main_menu':
        logger.bind(user_id=user_id).debug(f"Обработка главного меню для пользователя {username}")
        
        if text == "❗ Сообщите об опасности":
            logger.bind(user_id=user_id).info("Пользователь выбрал 'Сообщить об опасности'")
            start_danger_report(message)
        elif text == "🏠 Ближайшее укрытие":
            logger.bind(user_id=user_id).info("Пользователь выбрал 'Ближайшее укрытие'")
            start_shelter_finder(message)
        elif text == "🧑‍🏫 Консультант по безопасности РПРЗ":
            logger.bind(user_id=user_id).info("Пользователь выбрал 'Консультант по безопасности'")
            start_safety_consultant(message)
        elif text == "💡 Предложение по улучшению":
            logger.bind(user_id=user_id).info("Пользователь выбрал 'Предложение по улучшению'")
            start_improvement_suggestion(message)
        else:
            # Любой другой текст в главном меню - показываем подсказку
            logger.bind(user_id=user_id).warning(f"Неизвестная команда в главном меню: {text}")
            safe_send_message(chat_id, "❓ Выберите действие из меню:", reply_markup=get_main_menu_keyboard())
    
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
                    safe_send_message(chat_id, response['text'], reply_markup=response.get('reply_markup'), parse_mode=response.get('parse_mode'))
                else:
                    safe_send_message(chat_id, response, reply_markup=get_main_menu_keyboard())
            else:
                if isinstance(response, dict):
                    safe_send_message(chat_id, response['text'], reply_markup=response.get('reply_markup'), parse_mode=response.get('parse_mode'))
                else:
                    safe_send_message(chat_id, response, reply_markup=get_back_keyboard())
        else:
            safe_send_message(chat_id, result, reply_markup=get_back_keyboard())
    
    elif user_states.get(chat_id) == 'shelter_finder':
        if text == "📋 Показать список убежищ":
            show_all_shelters(chat_id)
        elif text == "📍 Отправить геолокацию":
            safe_send_message(chat_id, "📍 Нажмите кнопку 'Отправить геолокацию' для поиска ближайшего убежища")
        else:
            safe_send_message(chat_id, "❓ Выберите действие из меню:", reply_markup=get_back_keyboard())
    
    elif user_states.get(chat_id) == 'safety_consultant':
        result = handle_safety_consultant_text(message, placeholders)
        if isinstance(result, tuple):
            new_state, response = result
            user_states[chat_id] = new_state
            if new_state == "main_menu":
                bot.set_state(chat_id, BotStates.main_menu)
                if isinstance(response, dict):
                    safe_send_message(chat_id, response['text'], reply_markup=response.get('reply_markup'), parse_mode=response.get('parse_mode'))
                else:
                    safe_send_message(chat_id, response, reply_markup=get_main_menu_keyboard())
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
                                f"**{doc['title']}**\n\n"
                                f"📝 {doc['description']}\n\n"
                                f"📎 Документ отправлен выше"
                            )
                            safe_send_message(chat_id, doc_text, parse_mode='Markdown')
                        
                        # Финальное сообщение
                        final_text = "✅ **Отправлено документов: 5**\n\nВсе документы по безопасности РПРЗ готовы к изучению."
                        safe_send_message(chat_id, final_text, reply_markup=get_main_menu_keyboard())
                        
                        user_states[chat_id] = 'main_menu'
                        bot.set_state(chat_id, BotStates.main_menu)
                        
                    except Exception as e:
                        logger.error(f"Ошибка при отправке документов: {e}")
                        safe_send_message(chat_id, "❌ Ошибка при загрузке документов", reply_markup=get_main_menu_keyboard())
                        user_states[chat_id] = 'main_menu'
                        bot.set_state(chat_id, BotStates.main_menu)
                elif isinstance(response, dict):
                    safe_send_message(chat_id, response['text'], reply_markup=response.get('reply_markup'), parse_mode=response.get('parse_mode'))
                else:
                    safe_send_message(chat_id, response, reply_markup=get_back_keyboard())
        else:
            # Обработка вопросов
            if user_data.get(chat_id, {}).get('step') == 'question':
                result = handle_safety_question(message, placeholders)
                if isinstance(result, tuple):
                    new_state, response = result
                    if isinstance(response, dict):
                        safe_send_message(chat_id, response['text'], reply_markup=response.get('reply_markup'), parse_mode=response.get('parse_mode'))
                    else:
                        safe_send_message(chat_id, response, reply_markup=get_back_keyboard())
                else:
                    safe_send_message(chat_id, result, reply_markup=get_back_keyboard())
            else:
                # Если это не кнопка меню, то это вопрос
                user_data[chat_id]['step'] = 'question'
                result = handle_safety_question(message, placeholders)
                if isinstance(result, tuple):
                    new_state, response = result
                    if isinstance(response, dict):
                        safe_send_message(chat_id, response['text'], reply_markup=response.get('reply_markup'), parse_mode=response.get('parse_mode'))
                    else:
                        safe_send_message(chat_id, response, reply_markup=get_back_keyboard())
                else:
                    safe_send_message(chat_id, result, reply_markup=get_back_keyboard())
    
    elif user_states.get(chat_id) == 'improvement_suggestion':
        result = handle_improvement_suggestion_text(message, placeholders)
        if isinstance(result, tuple):
            new_state, response = result
            user_states[chat_id] = new_state
            if new_state == "main_menu":
                bot.set_state(chat_id, BotStates.main_menu)
                if isinstance(response, dict):
                    safe_send_message(chat_id, response['text'], reply_markup=response.get('reply_markup'))
                else:
                    safe_send_message(chat_id, response, reply_markup=get_main_menu_keyboard())
            else:
                if isinstance(response, dict):
                    safe_send_message(chat_id, response['text'], reply_markup=response.get('reply_markup'))
                else:
                    safe_send_message(chat_id, response, reply_markup=get_back_keyboard())
        else:
            safe_send_message(chat_id, result, reply_markup=get_back_keyboard())

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
    
    safe_send_message(
        chat_id,
        "❗ **Сообщите об опасности**\n\n"
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
    
    safe_send_message(
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
    
    safe_send_message(
        chat_id,
        "🧑‍🏫 Консультант по безопасности РПРЗ\n\n"
        "Выберите действие:",
        reply_markup=markup
    )

def start_improvement_suggestion(message):
    """Начало отправки предложения по улучшению"""
    chat_id = message.chat.id
    username = message.from_user.username or "Unknown"
    
    log_activity(chat_id, username, "improvement_suggestion_start")
    
    user_states[chat_id] = 'improvement_suggestion'
    user_data[chat_id] = {'step': 'suggestion'}
    bot.set_state(chat_id, BotStates.improvement_suggestion)
    
    safe_send_message(
        chat_id,
        "💡 Предложение по улучшению\n\n"
        "Опишите ваше предложение (максимум 1000 символов):",
        reply_markup=get_back_keyboard()
    )

# Обработчик геолокации
@bot.message_handler(content_types=['location'])
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
            safe_send_message(chat_id, result['text'], reply_markup=result.get('reply_markup'), parse_mode=result.get('parse_mode'))
    else:
        logger.bind(user_id=user_id).warning(f"Геолокация получена в неподходящем состоянии: {user_states.get(chat_id)}")
        safe_send_message(chat_id, "❌ Геолокация не нужна в текущем режиме")

# Обработчик медиафайлов
@bot.message_handler(content_types=['photo', 'video', 'document'])
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
        safe_send_message(chat_id, result, reply_markup=get_media_keyboard())
    else:
        logger.bind(user_id=user_id).warning(f"Медиафайл получен в неподходящем состоянии: {user_states.get(chat_id)}")
        safe_send_message(chat_id, "❌ Медиафайлы можно прикреплять только при сообщении об опасности")

# Основной цикл
if __name__ == '__main__':
    logger.info("Запуск MVP бота безопасности РПРЗ")
    
    # Проверяем наличие токена
    if not BOT_TOKEN or BOT_TOKEN == 'your_telegram_bot_token_here':
        logger.error("❌ BOT_TOKEN не настроен! Создайте файл .env с токеном бота")
        logger.info("📝 Пример содержимого .env:")
        logger.info("BOT_TOKEN=1234567890:ABCdefGHIjklMNOpqrsTUVwxyz")
        logger.info("ADMIN_CHAT_ID=123456789")
        sys.exit(1)
    
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
            logger.error(f"❌ Критическая ошибка polling: {error_str}")
            
            if "409" in error_str or "Conflict" in error_str:
                logger.error("❌ Ошибка 409: Конфликт экземпляров бота")
                logger.info("💡 Решения:")
                logger.info("1. Запустите: .\\stop_bot.ps1")
                logger.info("2. Или выполните: Get-Process python | Stop-Process -Force")
                logger.info("3. Или перезагрузите компьютер")
                logger.info("4. Подождите 2-3 минуты и попробуйте снова")
                
                # Пытаемся остановить процессы автоматически
                try:
                    import subprocess
                    logger.info("🔄 Попытка автоматической остановки процессов...")
                    
                    # Сначала пробуем остановить через taskkill
                    result = subprocess.run(["taskkill", "/f", "/im", "python.exe"], 
                                          capture_output=True, timeout=10, text=True)
                    
                    if result.returncode == 0:
                        logger.info("✅ Процессы остановлены через taskkill")
                    else:
                        logger.warning("⚠️ taskkill не сработал, пробуем через psutil...")
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
                        except:
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
        sys.exit(0)
    except ssl.SSLError as e:
        logger.error(f"❌ SSL ошибка: {e}")
        logger.info("💡 Попробуйте обновить сертификаты или использовать VPN")
        sys.exit(1)
    except Exception as e:
        logger.error(f"❌ Ошибка запуска бота: {e}")
        logger.info("💡 Проверьте правильность BOT_TOKEN в файле .env")
        sys.exit(1)
