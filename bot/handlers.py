"""
Обработчики для MVP Telegram-бота по безопасности РПРЗ
Содержит логику для всех 4 основных функций
"""

import os
import json
import csv
from datetime import datetime

import telebot
from telebot import types
from loguru import logger

# Импорт сервиса уведомлений
try:
    import sys
    import os
    # Добавляем корневую папку в путь для импорта
    sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from yandex_notifications import send_incident_notification, set_bot_instance
    NOTIFICATIONS_AVAILABLE = True
    logger.info("✅ Модуль yandex_notifications успешно загружен")
except ImportError as e:
    NOTIFICATIONS_AVAILABLE = False
    logger.warning(f"⚠️ Модуль yandex_notifications не найден: {e}")

# Глобальная переменная для объекта bot (будет установлена из main.py)
bot_instance = None

def set_bot_instance(bot):
    """Устанавливает глобальный экземпляр бота"""
    global bot_instance
    bot_instance = bot

def log_activity(chat_id: int, username: str, action: str, payload: str = ""):
    """Логирует активность пользователя в CSV"""
    try:
        log_file = 'logs/activity.csv'
        file_exists = os.path.exists(log_file)
        
        with open(log_file, 'a', newline='', encoding='utf-8-sig') as f:
            writer = csv.writer(f)
            if not file_exists:
                writer.writerow(['timestamp', 'user_id', 'username', 'action', 'payload'])
            
            writer.writerow([
                datetime.now().isoformat(),
                chat_id,
                username,
                action,
                payload[:100]
            ])
        
        # Дополнительное логирование в user_actions.log
        logger.bind(user_id=chat_id).info(f"Activity: {action} | {username} | {payload[:50]}")
        
    except Exception as e:
        logger.error(f"Ошибка логирования активности: {e}")

def log_incident(chat_id: int, incident_data: dict):
    """Логирует инцидент в JSON"""
    try:
        log_file = 'logs/incidents.json'
        incidents = []
        
        if os.path.exists(log_file):
            with open(log_file, 'r', encoding='utf-8-sig') as f:
                incidents = json.load(f)
        
        incidents.append({
            'timestamp': datetime.now().isoformat(),
            'user_id': chat_id,
            'incident': incident_data
        })
        
        with open(log_file, 'w', encoding='utf-8-sig') as f:
            json.dump(incidents, f, ensure_ascii=False, indent=2)
    except Exception as e:
        logger.error(f"Ошибка логирования инцидента: {e}")

def log_suggestion(chat_id: int, suggestion_data: dict):
    """Логирует предложение по улучшению в JSON"""
    try:
        log_file = 'logs/suggestions.json'
        suggestions = []
        
        if os.path.exists(log_file):
            with open(log_file, 'r', encoding='utf-8-sig') as f:
                suggestions = json.load(f)
        
        suggestions.append({
            'timestamp': datetime.now().isoformat(),
            'user_id': chat_id,
            'suggestion': suggestion_data
        })
        
        with open(log_file, 'w', encoding='utf-8-sig') as f:
            json.dump(suggestions, f, ensure_ascii=False, indent=2)
    except Exception as e:
        logger.error(f"Ошибка логирования предложения: {e}")

def get_back_keyboard():
    """Возвращает клавиатуру с кнопкой 'Назад'"""
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add(types.KeyboardButton("Назад"))
    return markup

def get_main_menu_keyboard():
    """Возвращает главное меню с 4 кнопками"""
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add(
        types.KeyboardButton("❗ Сообщите об опасности"),
        types.KeyboardButton("🏠 Ближайшее укрытие"),
        types.KeyboardButton("🧑‍🏫 Консультант по безопасности РПРЗ"),
        types.KeyboardButton("💡 Предложение по улучшению")
    )
    return markup

# === ОБРАБОТЧИКИ ДЛЯ "СООБЩИТЕ ОБ ОПАСНОСТИ" ===

def handle_danger_report_text(message, user_data, placeholders):
    """Обработка текста в процессе сообщения об опасности"""
    chat_id = message.chat.id
    username = message.from_user.username or "Unknown"
    text = message.text
    
    # Импортируем функции санитизации из main.py
    try:
        from .main import sanitize_user_input, validate_user_input
        sanitized_text = sanitize_user_input(text)
        is_valid, validation_error = validate_user_input(sanitized_text, min_length=1, max_length=1000)
        
        if not is_valid:
            return "danger_report", f"❌ {validation_error}"
    except ImportError:
        # Если импорт не удался, используем оригинальный текст
        sanitized_text = text
    
    if sanitized_text == "Назад":
        return "main_menu", None
    
    step = user_data.get('step', 'description')
    
    if step == 'description':
        # Проверяем, что это не кнопка
        if sanitized_text in ["📍 Отправить геолокацию", "📝 Указать текстом", "⏭️ Пропустить", "Назад", "📷 Продолжить"]:
            return "danger_report", "❌ Пожалуйста, введите текстовое описание инцидента, а не нажимайте кнопки"
        
        if len(sanitized_text) > 500:
            return "danger_report", "❌ Описание слишком длинное! Максимум 500 символов."
        
        if len(sanitized_text.strip()) < 10:
            return "danger_report", "❌ Описание слишком короткое! Минимум 10 символов."
        
        user_data['description'] = sanitized_text.strip()
        user_data['step'] = 'location'
        
        log_activity(chat_id, username, "danger_description", text[:50])
        
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
        markup.add(
            types.KeyboardButton("📍 Отправить геолокацию", request_location=True),
            types.KeyboardButton("📝 Указать текстом"),
            types.KeyboardButton("⏭️ Пропустить"),
            types.KeyboardButton("Назад")
        )
        
        return "danger_report", {
            'text': "📍 Укажите местоположение инцидента:\n\n• Введите текст с описанием места\n• Или нажмите кнопку 'Отправить геолокацию'\n• Или нажмите 'Пропустить'",
            'reply_markup': markup
        }
    
    elif step == 'location':
        if text == "⏭️ Пропустить":
            user_data['step'] = 'media'
            user_data['location_text'] = "Не указано"
            return "danger_report", {
                'text': "📷 Прикрепите фото/видео (до 3 файлов) или нажмите 'Продолжить':",
                'reply_markup': get_media_keyboard()
            }
        elif text == "📝 Указать текстом":
            user_data['step'] = 'location_text'
            return "danger_report", {
                'text': "📍 Укажите местоположение инцидента текстом (максимум 200 символов):",
                'reply_markup': get_back_keyboard()
            }
        elif text == "Назад":
            # Возвращаемся к описанию
            user_data['step'] = 'description'
            return "danger_report", {
                'text': "❗ Сообщите об опасности\n\n📝 Опишите что произошло (максимум 500 символов):",
                'reply_markup': get_back_keyboard()
            }
        else:
            # Если пользователь вводит текст, считаем это указанием местоположения текстом
            if len(text) > 200:
                return "danger_report", "❌ Описание места слишком длинное! Максимум 200 символов."
            
            if len(text.strip()) < 3:
                return "danger_report", "❌ Описание места слишком короткое! Минимум 3 символа."
            
            user_data['location_text'] = text.strip()
            user_data['step'] = 'media'
            
            log_activity(chat_id, username, "danger_location_text", text[:50])
            
            return "danger_report", {
                'text': f"✅ Место указано: {text.strip()}\n\n📷 Прикрепите фото/видео (до 3 файлов) или нажмите 'Продолжить':",
                'reply_markup': get_media_keyboard()
            }
    
    elif step == 'location_text':
        # Проверяем, что это не кнопка
        if text in ["📍 Отправить геолокацию", "📝 Указать текстом", "⏭️ Пропустить", "📷 Продолжить"]:
            return "danger_report", "❌ Пожалуйста, введите текстовое описание места, а не нажимайте кнопки"
        elif text == "Назад":
            # Возвращаемся к выбору способа указания места
            user_data['step'] = 'location'
            return "danger_report", {
                'text': "📍 Укажите место происшествия:",
                'reply_markup': get_location_keyboard()
            }
        
        if len(text) > 200:
            return "danger_report", "❌ Описание места слишком длинное! Максимум 200 символов."
        
        if len(text.strip()) < 3:
            return "danger_report", "❌ Описание места слишком короткое! Минимум 3 символа."
        
        user_data['location_text'] = text.strip()
        user_data['step'] = 'media'
        
        log_activity(chat_id, username, "danger_location_text", text[:50])
        
        return "danger_report", {
            'text': f"✅ Место указано: {text.strip()}\n\n📷 Прикрепите фото/видео (до 3 файлов) или нажмите 'Продолжить':",
            'reply_markup': get_media_keyboard()
        }
    
    elif step == 'media':
        if text == "📷 Продолжить":
            return finish_danger_report(message, user_data, placeholders)
        elif text == "📍 Изменить место":
            user_data['step'] = 'location'
            return "danger_report", {
                'text': "📍 Укажите место происшествия:",
                'reply_markup': get_location_keyboard()
            }
        elif text == "📝 Изменить описание":
            user_data['step'] = 'description'
            return "danger_report", {
                'text': "❗ Сообщите об опасности\n\n📝 Опишите что произошло (максимум 500 символов):",
                'reply_markup': get_back_keyboard()
            }
        elif text == "❌ Отменить":
            user_data.clear()
            return "main_menu", {
                'text': "❌ Сообщение об опасности отменено",
                'reply_markup': get_main_menu_keyboard()
            }
        elif text == "Назад":
            # Возвращаемся к выбору места
            user_data['step'] = 'location'
            return "danger_report", {
                'text': "📍 Укажите место происшествия:",
                'reply_markup': get_location_keyboard()
            }
        else:
            # Игнорируем текст, который не является кнопкой
            return "danger_report", "❌ Прикрепите медиафайлы или выберите действие из меню"

def handle_danger_report_location(message, user_data):
    """Обработка геолокации в процессе сообщения об опасности"""
    chat_id = message.chat.id
    username = message.from_user.username or "Unknown"
    
    user_data['location'] = {
        'latitude': message.location.latitude,
        'longitude': message.location.longitude
    }
    user_data['step'] = 'media'
    
    log_activity(chat_id, username, "danger_location", f"lat: {message.location.latitude}, lon: {message.location.longitude}")
    
    return {
        'text': "✅ Геолокация получена!\n📷 Прикрепите фото/видео (до 3 файлов) или нажмите 'Продолжить':",
        'reply_markup': get_media_keyboard()
    }

def handle_danger_report_media(message, user_data, max_file_size_mb, max_video_size_mb):
    """Обработка медиафайлов в процессе сообщения об опасности"""
    chat_id = message.chat.id
    username = message.from_user.username or "Unknown"
    
    # Проверка размера файла
    file_size = 0
    if message.photo:
        file_size = message.photo[-1].file_size
        max_size = max_file_size_mb * 1024 * 1024
    elif message.video:
        file_size = message.video.file_size
        max_size = max_video_size_mb * 1024 * 1024
    elif message.document:
        file_size = message.document.file_size
        max_size = max_file_size_mb * 1024 * 1024
    
    if file_size > max_size:
        return f"❌ Файл слишком большой! Максимум: {max_file_size_mb} МБ для фото, {max_video_size_mb} МБ для видео"
    
    # Сохраняем информацию о медиа
    if 'media' not in user_data:
        user_data['media'] = []
    
    if len(user_data['media']) >= 3:
        return "❌ Максимум 3 медиафайла!"
    
    media_info = {
        'type': message.content_type,
        'file_id': message.photo[-1].file_id if message.photo else (message.video.file_id if message.video else message.document.file_id),
        'file_size': file_size
    }
    user_data['media'].append(media_info)
    
    log_activity(chat_id, username, "danger_media", f"type: {message.content_type}, size: {file_size}")
    
    remaining = 3 - len(user_data['media'])
    return f"✅ Медиафайл добавлен ({len(user_data['media'])}/3). Осталось: {remaining}"

def finish_danger_report(message, user_data, placeholders):
    """Завершение процесса сообщения об опасности"""
    chat_id = message.chat.id
    username = message.from_user.username or "Unknown"
    
    # Создаем сводку инцидента
    incident_data = {
        'description': user_data.get('description', ''),
        'location': user_data.get('location'),
        'location_text': user_data.get('location_text'),
        'media_count': len(user_data.get('media', [])),
        'media': user_data.get('media', []),  # Добавляем медиафайлы
        'user_id': chat_id,
        'username': username
    }
    
    # Логируем инцидент
    log_incident(chat_id, incident_data)
    log_activity(chat_id, username, "danger_report_completed")
    
    # Отправляем уведомления об инциденте
    try:
        # Отправляем в Telegram админу
        admin_chat_id = os.getenv('ADMIN_CHAT_ID')
        if admin_chat_id:
            admin_text = f"🚨 НОВЫЙ ИНЦИДЕНТ\n\n"
            admin_text += f"👤 Пользователь: ID {chat_id}\n"
            admin_text += f"📝 Описание: {incident_data['description']}\n"
            if incident_data['location']:
                admin_text += f"📍 Координаты: {incident_data['location']['latitude']}, {incident_data['location']['longitude']}\n"
            elif incident_data['location_text']:
                admin_text += f"📍 Место: {incident_data['location_text']}\n"
            else:
                admin_text += f"📍 Место: Не указано\n"
            admin_text += f"📷 Медиафайлов: {incident_data['media_count']}\n"
            admin_text += f"🕐 Время: {datetime.now().strftime('%d.%m.%Y %H:%M')}"
            
            logger.info(f"Отправка админу в Telegram: {admin_text}")
            
            # Отправляем сообщение админу через глобальный объект bot
            if bot_instance:
                try:
                    bot_instance.send_message(admin_chat_id, admin_text)
                    logger.info("✅ Уведомление админу в Telegram отправлено")
                except Exception as bot_error:
                    logger.error(f"❌ Ошибка отправки админу в Telegram: {bot_error}")
            else:
                logger.warning("⚠️ Объект bot не инициализирован для отправки уведомления админу")
        else:
            logger.warning("⚠️ ADMIN_CHAT_ID не настроен")
        
        # Отправляем через Яндекс уведомления
        if NOTIFICATIONS_AVAILABLE:
            notification_success, notification_message = send_incident_notification(incident_data)
            if notification_success:
                logger.info(f"✅ Яндекс уведомления отправлены: {notification_message}")
            else:
                logger.warning(f"⚠️ Ошибка Яндекс уведомлений: {notification_message}")
        else:
            logger.warning("⚠️ Сервис Яндекс уведомлений недоступен")
            
    except Exception as e:
        logger.error(f"Ошибка отправки уведомлений: {e}")
    
    # Создаем клавиатуру с кнопками звонков
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add(
        types.KeyboardButton("📞 Позвонить в службу безопасности"),
        types.KeyboardButton("📞 Позвонить в охрану труда"),
        types.KeyboardButton("🏠 Главное меню")
    )
    
    response_text = (
        "✅ Инцидент зарегистрирован!\n\n"
        "📝 Описание: {}\n"
        "📍 Местоположение: {}\n"
        "📷 Медиафайлов: {}\n\n"
        "🚨 Срочные контакты:\n"
        "📞 Служба безопасности: {}\n"
        "📞 Охрана труда: {}\n\n"
        "Спасибо за оперативное сообщение!"
    ).format(
        incident_data['description'],
        "Координаты: {:.6f}, {:.6f}".format(incident_data['location']['latitude'], incident_data['location']['longitude']) if incident_data['location'] else (incident_data['location_text'] if incident_data['location_text'] else "Не указано"),
        incident_data['media_count'],
        placeholders.get('contacts', {}).get('security', 'Не указан'),
        placeholders.get('contacts', {}).get('safety', 'Не указан')
    )
    
    return "main_menu", {
        'text': response_text,
        'reply_markup': markup
    }

def get_location_keyboard():
    """Клавиатура для выбора места"""
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add(
        types.KeyboardButton("📍 Отправить геолокацию", request_location=True),
        types.KeyboardButton("📝 Указать текстом"),
        types.KeyboardButton("⏭️ Пропустить")
    )
    markup.add(types.KeyboardButton("Назад"))
    return markup

def get_media_keyboard():
    """Клавиатура для работы с медиа"""
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add(
        types.KeyboardButton("📷 Продолжить"),
        types.KeyboardButton("📍 Изменить место"),
        types.KeyboardButton("📝 Изменить описание")
    )
    markup.add(
        types.KeyboardButton("❌ Отменить"),
        types.KeyboardButton("Назад")
    )
    return markup

# === ОБРАБОТЧИКИ ДЛЯ "БЛИЖАЙШЕЕ УБЕЖИЩЕ" ===

def handle_shelter_finder_text(message, placeholders):
    """Обработка текста в поиске убежищ"""
    chat_id = message.chat.id
    username = message.from_user.username or "Unknown"
    text = message.text
    
    if text == "Назад":
        return "main_menu", None
    elif text == "⏭️ Пропустить":
        # Возвращаем данные для отправки изображений убежищ
        shelters = placeholders.get('shelters', [])
        return "shelter_finder", {
            'shelters': shelters,
            'action': 'show_shelters_with_photos'
        }
    else:
        return "shelter_finder", "❌ Отправьте геолокацию или нажмите 'Пропустить'"



# === ОБРАБОТЧИКИ ДЛЯ "КОНСУЛЬТАНТ ПО БЕЗОПАСНОСТИ" ===

def handle_safety_consultant_text(message, placeholders):
    """Обработка текста в консультанте по безопасности"""
    chat_id = message.chat.id
    username = message.from_user.username or "Unknown"
    text = message.text
    
    if text == "Назад":
        return "main_menu", None
    elif text == "📄 Список документов":
        return show_documents_list(message, placeholders)
    elif text == "❓ Задать вопрос":
        return start_question_mode(message)
    else:
        return "safety_consultant", "❓ Выберите действие из меню:"

def show_documents_list(message, placeholders):
    """Показывает список документов с отправкой реальных PDF"""
    chat_id = message.chat.id
    username = message.from_user.username or "Unknown"
    
    log_activity(chat_id, username, "documents_list_shown")
    
    documents = placeholders.get('documents', [])
    
    if not documents:
        return "main_menu", {
            'text': "❌ Список документов недоступен",
            'reply_markup': get_main_menu_keyboard()
        }
    
    # Возвращаем данные для отправки PDF файлов
    return "safety_consultant", {
        'documents': documents,
        'action': 'send_documents'
    }

def start_question_mode(message):
    """Начинает режим вопросов"""
    chat_id = message.chat.id
    username = message.from_user.username or "Unknown"
    
    log_activity(chat_id, username, "question_mode_started")
    
    # Устанавливаем шаг для обработки вопросов
    # Это нужно сделать в основном файле
    
    return "safety_consultant", {
        'text': "❓ Задайте ваш вопрос по безопасности:\n\n*Примеры вопросов:*\n• Что делать при пожаре?\n• Правила электробезопасности\n• Как найти убежище?",
        'reply_markup': get_back_keyboard(),
        'parse_mode': 'Markdown'
    }

def handle_safety_question(message, placeholders):
    """Обрабатывает вопрос по безопасности"""
    chat_id = message.chat.id
    username = message.from_user.username or "Unknown"
    question = message.text
    
    # Проверяем, что это не кнопка
    if question in ["🔍 Подробнее", "📄 Открыть PDF", "❓ Задать другой вопрос", "Назад", "📄 Список документов"]:
        return "safety_consultant", "❌ Пожалуйста, введите текстовый вопрос, а не нажимайте кнопки"
    
    if len(question.strip()) < 5:
        return "safety_consultant", "❌ Вопрос слишком короткий! Минимум 5 символов."
    
    log_activity(chat_id, username, "safety_question", question[:50])
    
    # Поиск подходящего ответа в заглушках
    responses = placeholders.get('safety_responses', [])
    answer = None
    source = None
    
    for response in responses:
        keywords = response.get('question_keywords', [])
        if any(keyword.lower() in question.lower() for keyword in keywords):
            answer = response['answer']
            source = response['source']
            break
    
    if not answer:
        answer = "Заглушка-ответ по вашему вопросу."
        source = "Документ №X, стр. Y, п. Z (заглушка)."
    
    response_text = (
        "🤖 Ответ консультанта по безопасности:\n\n"
        "📝 Ответ: {}\n\n"
        "📚 Источник: {}\n\n"
        "🔍 [Подробнее] | 📄 [Открыть PDF]"
    ).format(answer, source)
    
    # Создаем клавиатуру с кнопками
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add(
        types.KeyboardButton("🔍 Подробнее"),
        types.KeyboardButton("📄 Открыть PDF"),
        types.KeyboardButton("❓ Задать другой вопрос"),
        types.KeyboardButton("Назад")
    )
    
    return "safety_consultant", {
        'text': response_text,
        'reply_markup': markup,
        'parse_mode': 'Markdown'
    }

# === ОБРАБОТЧИКИ ДЛЯ "ПРЕДЛОЖЕНИЕ ПО УЛУЧШЕНИЮ" ===

def handle_improvement_suggestion_text(message, placeholders, user_data):
    """Обработка текста предложения по улучшению с улучшенным функционалом"""
    chat_id = message.chat.id
    username = message.from_user.username or "Unknown"
    text = message.text
    
    if text == "Назад" or text == "⬅️ Назад к выбору":
        return "improvement_suggestion_choice", None
    
    # Проверяем, что это не кнопка
    if text in ["❗ Сообщите об опасности", "🏠 Ближайшее укрытие", "🧑‍🏫 Консультант по безопасности РПРЗ", "💡 Предложение по улучшению"]:
        return "improvement_suggestion", "❌ Пожалуйста, введите текстовое предложение, а не нажимайте кнопки"
    
    if len(text) > 1000:
        return "improvement_suggestion", "❌ Предложение слишком длинное! Максимум 1000 символов."
    
    if len(text.strip()) < 10:
        return "improvement_suggestion", "❌ Предложение слишком короткое! Минимум 10 символов."
    
    # Сохраняем предложение с дополнительными данными
    suggestion_data = {
        'text': text.strip(),
        'user_id': chat_id,
        'username': username,
        'timestamp': datetime.now().isoformat(),
        'votes': 0,
        'voters': [],
        'status': 'pending',  # pending, approved, rejected, voted
        'category': user_data.get(chat_id, {}).get('category', categorize_suggestion(text.strip()))
    }
    
    # Сохраняем в улучшенном формате
    save_enhanced_suggestion(chat_id, suggestion_data)
    log_suggestion(chat_id, suggestion_data)
    log_activity(chat_id, username, "suggestion_submitted", text[:50])
    
    # Создаем клавиатуру с дополнительными опциями
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add(
        types.KeyboardButton("📊 Посмотреть мои предложения"),
        types.KeyboardButton("🏆 Популярные предложения"),
        types.KeyboardButton("📝 Отправить еще предложение"),
        types.KeyboardButton("🏠 Главное меню")
    )
    
    response_text = (
        "✅ Спасибо за ваше предложение!\n\n"
        "📝 Ваше предложение: {}\n\n"
        "🏷️ Категория: {}\n"
        "🕐 Время подачи: {}\n"
        "📊 Статус: На рассмотрении\n\n"
        "💡 Что дальше?\n"
        "• Ваше предложение будет рассмотрено разработчиками\n"
        "• Лучшие предложения выносятся на общее голосование\n"
        "• Вы можете отслеживать статус своих предложений\n\n"
        "🎯 Хотите внести свой вклад в развитие проекта?\n"
        "Ваши идеи помогают сделать бота лучше!"
    ).format(
        text,
        suggestion_data['category'],
        datetime.now().strftime('%d.%m.%Y %H:%M')
    )
    
    return "improvement_suggestion_menu", {
        'text': response_text,
        'reply_markup': markup
    }

def handle_improvement_suggestion_choice(message, placeholders):
    """Обработка выбора категории предложения"""
    chat_id = message.chat.id
    username = message.from_user.username or "Unknown"
    text = message.text
    
    if text == "🏠 Главное меню":
        return "main_menu", None
    
    # Определяем категорию и создаем соответствующий запрос
    category_map = {
        "🛡️ Безопасность и защита": {
            'category': 'Безопасность',
            'prompt': "🛡️ Предложение по безопасности и защите\n\nОпишите, какие функции безопасности вы хотели бы добавить или улучшить:",
            'examples': [
                "• Двухфакторная аутентификация",
                "• Шифрование данных",
                "• Система мониторинга",
                "• Контроль доступа"
            ]
        },
        "🎨 Интерфейс и дизайн": {
            'category': 'UI/UX',
            'prompt': "🎨 Предложение по интерфейсу и дизайну\n\nОпишите, как можно улучшить внешний вид и удобство использования:",
            'examples': [
                "• Новые цветовые схемы",
                "• Улучшение навигации",
                "• Адаптивный дизайн",
                "• Анимации и эффекты"
            ]
        },
        "⚡ Производительность": {
            'category': 'Производительность',
            'prompt': "⚡ Предложение по производительности\n\nОпишите, как можно ускорить работу бота:",
            'examples': [
                "• Оптимизация запросов",
                "• Кэширование данных",
                "• Асинхронная обработка",
                "• Сжатие данных"
            ]
        },
        "🔔 Уведомления": {
            'category': 'Уведомления',
            'prompt': "🔔 Предложение по уведомлениям\n\nОпишите, какие уведомления вы хотели бы получать:",
            'examples': [
                "• Push-уведомления",
                "• Email-рассылки",
                "• SMS-оповещения",
                "• Настраиваемые алерты"
            ]
        },
        "🔧 Функциональность": {
            'category': 'Функциональность',
            'prompt': "🔧 Предложение по функциональности\n\nОпишите, какие новые функции вы хотели бы видеть:",
            'examples': [
                "• Новые команды",
                "• Интеграции с сервисами",
                "• Автоматизация процессов",
                "• Аналитика и отчеты"
            ]
        },
        "💭 Свободная форма": {
            'category': 'Общее',
            'prompt': "💭 Свободное предложение\n\nОпишите ваше предложение по улучшению проекта:",
            'examples': [
                "• Любые идеи по улучшению",
                "• Инновационные решения",
                "• Улучшение пользовательского опыта",
                "• Новые возможности"
            ]
        }
    }
    
    if text in category_map:
        category_info = category_map[text]
        # Сохраняем категорию в user_data (передается из main.py)
        # user_data будет обновлен в main.py
        
        # Создаем клавиатуру с кнопкой "Назад" (возврат к выбору категории)
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
        markup.add(types.KeyboardButton("⬅️ Назад к выбору"))
        markup.add(types.KeyboardButton("🏠 Главное меню"))
        
        # Формируем текст с примерами
        examples_text = "\n".join(category_info['examples'])
        
        response_text = (
            f"{category_info['prompt']}\n\n"
            f"💡 Примеры:\n{examples_text}\n\n"
            f"📝 Опишите ваше предложение (максимум 1000 символов):"
        )
        
        log_activity(chat_id, username, "suggestion_category_chosen", text)
        
        return "improvement_suggestion", {
            'text': response_text,
            'reply_markup': markup,
            'category': category_info['category']
        }
    else:
        return "improvement_suggestion_choice", "❓ Выберите категорию из предложенных вариантов:"

def categorize_suggestion(text):
    """Определяет категорию предложения"""
    text_lower = text.lower()
    
    if any(word in text_lower for word in ['интерфейс', 'кнопк', 'меню', 'дизайн', 'внешний вид']):
        return 'UI/UX'
    elif any(word in text_lower for word in ['функц', 'возможност', 'новый', 'добавить']):
        return 'Функциональность'
    elif any(word in text_lower for word in ['безопасность', 'защита', 'приватность']):
        return 'Безопасность'
    elif any(word in text_lower for word in ['скорость', 'производительность', 'оптимизация']):
        return 'Производительность'
    elif any(word in text_lower for word in ['уведомления', 'алерт', 'оповещение']):
        return 'Уведомления'
    else:
        return 'Общее'

def save_enhanced_suggestion(chat_id, suggestion_data):
    """Сохраняет предложение в улучшенном формате"""
    try:
        suggestions_file = 'logs/enhanced_suggestions.json'
        suggestions = []
        
        if os.path.exists(suggestions_file):
            with open(suggestions_file, 'r', encoding='utf-8-sig') as f:
                suggestions = json.load(f)
        
        # Добавляем ID предложения
        suggestion_data['id'] = len(suggestions) + 1
        suggestions.append(suggestion_data)
        
        with open(suggestions_file, 'w', encoding='utf-8') as f:
            json.dump(suggestions, f, ensure_ascii=False, indent=2)
            
    except Exception as e:
        logger.error(f"Ошибка сохранения улучшенного предложения: {e}")

def handle_suggestion_menu(message, placeholders):
    """Обработка меню предложений"""
    chat_id = message.chat.id
    username = message.from_user.username or "Unknown"
    text = message.text
    
    if text == "🏠 Главное меню":
        return "main_menu", None
    elif text == "📊 Посмотреть мои предложения":
        return show_user_suggestions(message)
    elif text == "🏆 Популярные предложения":
        return show_popular_suggestions(message)
    elif text == "📝 Отправить еще предложение":
        return "improvement_suggestion", {
            'text': "💡 Отправьте еще одно предложение по улучшению:\n\n"
                   "Опишите, как бы вы улучшили проект. Лучшие предложения будут вынесены на общее голосование!",
            'reply_markup': get_back_keyboard()
        }
    else:
        return "improvement_suggestion_menu", "❓ Выберите действие из меню:"

def show_user_suggestions(message):
    """Показывает предложения пользователя"""
    chat_id = message.chat.id
    username = message.from_user.username or "Unknown"
    
    try:
        suggestions_file = 'logs/enhanced_suggestions.json'
        if not os.path.exists(suggestions_file):
            return "improvement_suggestion_menu", {
                'text': "📝 У вас пока нет предложений.\n\nОтправьте первое предложение по улучшению проекта!",
                'reply_markup': get_back_keyboard()
            }
        
        with open(suggestions_file, 'r', encoding='utf-8-sig') as f:
            all_suggestions = json.load(f)
        
        user_suggestions = [s for s in all_suggestions if s['user_id'] == chat_id]
        
        if not user_suggestions:
            return "improvement_suggestion_menu", {
                'text': "📝 У вас пока нет предложений.\n\nОтправьте первое предложение по улучшению проекта!",
                'reply_markup': get_back_keyboard()
            }
        
        response_text = f"📊 Ваши предложения ({len(user_suggestions)}):\n\n"
        
        for i, suggestion in enumerate(user_suggestions[-5:], 1):  # Последние 5
            timestamp = datetime.fromisoformat(suggestion['timestamp']).strftime('%d.%m %H:%M')
            votes = suggestion.get('votes', 0)
            status = suggestion['status']
            status_emoji = {
                'pending': '⏳',
                'approved': '✅',
                'rejected': '❌',
                'voted': '🗳️'
            }.get(status, '❓')
            
            response_text += (
                f"{i}. {status_emoji} {suggestion['category']}\n"
                f"📝 {suggestion['text'][:60]}...\n"
                f"🗳️ Голосов: {votes} | 📅 {timestamp}\n\n"
            )
        
        return "improvement_suggestion_menu", {
            'text': response_text,
            'reply_markup': get_back_keyboard()
        }
        
    except Exception as e:
        logger.error(f"Ошибка показа предложений пользователя: {e}")
        return "improvement_suggestion_menu", {
            'text': "❌ Ошибка при загрузке ваших предложений",
            'reply_markup': get_back_keyboard()
        }

def show_popular_suggestions(message):
    """Показывает популярные предложения"""
    chat_id = message.chat.id
    
    try:
        suggestions_file = 'logs/enhanced_suggestions.json'
        if not os.path.exists(suggestions_file):
            return "improvement_suggestion_menu", {
                'text': "🏆 Пока нет предложений для голосования.",
                'reply_markup': get_back_keyboard()
            }
        
        with open(suggestions_file, 'r', encoding='utf-8-sig') as f:
            all_suggestions = json.load(f)
        
        # Сортируем по количеству голосов
        popular_suggestions = sorted(all_suggestions, key=lambda x: x.get('votes', 0), reverse=True)
        
        response_text = "🏆 Популярные предложения для голосования:\n\n"
        
        for i, suggestion in enumerate(popular_suggestions[:5], 1):
            votes = suggestion.get('votes', 0)
            username = suggestion.get('username', 'Unknown')
            category = suggestion['category']
            
            response_text += (
                f"{i}. 🗳️ {votes} голосов\n"
                f"📝 {suggestion['text'][:70]}...\n"
                f"👤 @{username} | 🏷️ {category}\n\n"
            )
        
        if not popular_suggestions:
            response_text = "🏆 Пока нет предложений для голосования."
        
        return "improvement_suggestion_menu", {
            'text': response_text,
            'reply_markup': get_back_keyboard()
        }
        
    except Exception as e:
        logger.error(f"Ошибка показа популярных предложений: {e}")
        return "improvement_suggestion_menu", {
            'text': "❌ Ошибка при загрузке популярных предложений",
            'reply_markup': get_back_keyboard()
    }
