"""
Обработчики для MVP Telegram-бота по безопасности РПРЗ
Содержит логику для всех 4 основных функций
"""

import os
import json
import csv
from datetime import datetime
from typing import Dict, List, Optional

import telebot
from telebot import types
from loguru import logger

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
            with open(log_file, 'r', encoding='utf-8') as f:
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
            with open(log_file, 'r', encoding='utf-8') as f:
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
    
    if text == "Назад":
        return "main_menu", None
    
    step = user_data.get('step', 'description')
    
    if step == 'description':
        # Проверяем, что это не кнопка
        if text in ["📍 Отправить геолокацию", "📝 Указать текстом", "⏭️ Пропустить", "Назад", "📷 Продолжить"]:
            return "danger_report", "❌ Пожалуйста, введите текстовое описание инцидента, а не нажимайте кнопки"
        
        if len(text) > 500:
            return "danger_report", "❌ Описание слишком длинное! Максимум 500 символов."
        
        if len(text.strip()) < 10:
            return "danger_report", "❌ Описание слишком короткое! Минимум 10 символов."
        
        user_data['description'] = text.strip()
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
            'text': "📍 Укажите местоположение инцидента:",
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
        else:
            # Игнорируем текст, который не является кнопкой
            return "danger_report", "❌ Выберите способ указания местоположения из кнопок ниже:"
    
    elif step == 'location_text':
        # Проверяем, что это не кнопка
        if text in ["📍 Отправить геолокацию", "📝 Указать текстом", "⏭️ Пропустить", "Назад", "📷 Продолжить"]:
            return "danger_report", "❌ Пожалуйста, введите текстовое описание места, а не нажимайте кнопки"
        
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
        else:
            # Игнорируем текст, который не является кнопкой
            return "danger_report", "❌ Прикрепите медиафайлы или нажмите кнопку 'Продолжить'"

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
        'user_id': chat_id,
        'username': username
    }
    
    # Логируем инцидент
    log_incident(chat_id, incident_data)
    log_activity(chat_id, username, "danger_report_completed")
    
    # Отправляем админу (заглушка)
    admin_chat_id = os.getenv('ADMIN_CHAT_ID')
    if admin_chat_id:
        try:
            admin_text = f"🚨 НОВЫЙ ИНЦИДЕНТ\n\n"
            admin_text += f"👤 Пользователь: @{username} ({chat_id})\n"
            admin_text += f"📝 Описание: {incident_data['description']}\n"
            if incident_data['location']:
                admin_text += f"📍 Координаты: {incident_data['location']['latitude']}, {incident_data['location']['longitude']}\n"
            elif incident_data['location_text']:
                admin_text += f"📍 Место: {incident_data['location_text']}\n"
            else:
                admin_text += f"📍 Место: Не указано\n"
            admin_text += f"📷 Медиафайлов: {incident_data['media_count']}\n"
            admin_text += f"🕐 Время: {datetime.now().strftime('%d.%m.%Y %H:%M')}"
            
            # Здесь должен быть bot.send_message, но передаем текст для отправки
            logger.info(f"Отправка админу: {admin_text}")
        except Exception as e:
            logger.error(f"Ошибка отправки админу: {e}")
    
    # Создаем клавиатуру с кнопками звонков
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add(
        types.KeyboardButton("📞 Позвонить в службу безопасности"),
        types.KeyboardButton("📞 Позвонить в охрану труда"),
        types.KeyboardButton("🏠 Главное меню")
    )
    
    response_text = (
        "✅ **Инцидент зарегистрирован!**\n\n"
        "📝 Описание: {}\n"
        "📍 Местоположение: {}\n"
        "📷 Медиафайлов: {}\n\n"
        "🚨 **Срочные контакты:**\n"
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

def get_media_keyboard():
    """Клавиатура для работы с медиа"""
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add(
        types.KeyboardButton("📷 Продолжить"),
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

def handle_shelter_finder_location(message, placeholders):
    """Обработка геолокации в поиске убежищ"""
    chat_id = message.chat.id
    username = message.from_user.username or "Unknown"
    
    log_activity(chat_id, username, "shelter_location", f"lat: {message.location.latitude}, lon: {message.location.longitude}")
    
    return show_shelters_list(message, placeholders, message.location.latitude, message.location.longitude)

def show_shelters_list(message, placeholders, user_lat=None, user_lon=None):
    """Показывает список убежищ с реальными изображениями"""
    chat_id = message.chat.id
    username = message.from_user.username or "Unknown"
    
    log_activity(chat_id, username, "shelters_shown")
    
    shelters = placeholders.get('shelters', [])
    
    if not shelters:
        return "main_menu", {
            'text': "❌ Список убежищ недоступен",
            'reply_markup': get_main_menu_keyboard()
        }
    
    # Отправляем изображения убежищ
    try:
        for i, shelter in enumerate(shelters, 1):
            # Отправляем изображение убежища
            photo_path = shelter.get('photo_path', '')
            if photo_path and os.path.exists(photo_path):
                with open(photo_path, 'rb') as photo_file:
                    # Здесь должен быть bot.send_photo, но передаем данные для отправки
                    logger.info(f"Отправка фото убежища {i}: {photo_path}")
            
            # Отправляем информацию об убежище
            shelter_text = (
                f"🏠 **{shelter['name']}**\n\n"
                f"📝 {shelter['description']}\n\n"
                f"📍 Координаты: {shelter['lat']}, {shelter['lon']}\n"
                f"🌐 [📍 Показать на карте]({shelter['map_link']})"
            )
            
            # Здесь должен быть bot.send_message
            logger.info(f"Отправка информации об убежище {i}: {shelter_text[:100]}...")
        
        response = "✅ **Найдено убежищ: 3**\n\nВсе убежища оснащены современными системами безопасности и готовы к использованию."
        
    except Exception as e:
        logger.error(f"Ошибка при показе убежищ: {e}")
        response = "❌ Ошибка при загрузке информации об убежищах"
    
    return "main_menu", {
        'text': response,
        'reply_markup': get_main_menu_keyboard(),
        'parse_mode': 'Markdown'
    }

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
        "🤖 **Ответ консультанта по безопасности:**\n\n"
        "📝 **Ответ:** {}\n\n"
        "📚 **Источник:** {}\n\n"
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

def handle_improvement_suggestion_text(message, placeholders):
    """Обработка текста предложения по улучшению"""
    chat_id = message.chat.id
    username = message.from_user.username or "Unknown"
    text = message.text
    
    if text == "Назад":
        return "main_menu", None
    
    # Проверяем, что это не кнопка
    if text in ["❗ Сообщите об опасности", "🏠 Ближайшее укрытие", "🧑‍🏫 Консультант по безопасности РПРЗ", "💡 Предложение по улучшению"]:
        return "improvement_suggestion", "❌ Пожалуйста, введите текстовое предложение, а не нажимайте кнопки"
    
    if len(text) > 1000:
        return "improvement_suggestion", "❌ Предложение слишком длинное! Максимум 1000 символов."
    
    if len(text.strip()) < 10:
        return "improvement_suggestion", "❌ Предложение слишком короткое! Минимум 10 символов."
    
    # Сохраняем предложение
    suggestion_data = {
        'text': text.strip(),
        'user_id': chat_id,
        'username': username
    }
    
    log_suggestion(chat_id, suggestion_data)
    log_activity(chat_id, username, "suggestion_submitted", text[:50])
    
    response_text = (
        "✅ **Спасибо за ваше предложение!**\n\n"
        "📝 Ваше предложение: {}\n\n"
        "📋 Оно будет рассмотрено администрацией завода.\n"
        "🕐 Время подачи: {}\n\n"
        "Спасибо за активное участие в улучшении безопасности!"
    ).format(
        text,
        datetime.now().strftime('%d.%m.%Y %H:%M')
    )
    
    return "main_menu", {
        'text': response_text,
        'reply_markup': get_main_menu_keyboard()
    }
