"""
Обработчики для MVP Telegram-бота по безопасности РПРЗ
Содержит логику для всех 4 основных функций
"""

import csv
import json
import os
import sys
from datetime import datetime

from loguru import logger
from telebot import types

# Импорт сервиса уведомлений
try:
    # Добавляем корневую папку в путь для импорта
    sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from bot.notifications import send_incident_notification

    NOTIFICATIONS_AVAILABLE = True
    logger.info("✅ Модуль notifications успешно загружен")
except ImportError as e:
    NOTIFICATIONS_AVAILABLE = False
    logger.warning(f"⚠️ Модуль notifications не найден: {e}")
    logger.warning(f"⚠️ Детали ошибки: {e}")
    logger.warning(f"⚠️ Путь: {sys.path}")

# Глобальная переменная для объекта bot (будет установлена из main.py)
bot_instance = None


def set_bot_instance(bot):
    """Устанавливает глобальный экземпляр бота"""
    global bot_instance
    bot_instance = bot


def log_activity(chat_id: int, username: str, action: str, payload: str = ""):
    """Логирует активность пользователя в CSV"""
    try:
        log_file = "logs/activity.csv"
        file_exists = os.path.exists(log_file)

        with open(log_file, "a", newline="", encoding="utf-8-sig") as f:
            writer = csv.writer(f)
            if not file_exists:
                writer.writerow(
                    ["timestamp", "user_id", "username", "action", "payload"]
                )

            writer.writerow(
                [datetime.now().isoformat(), chat_id, username, action, payload[:100]]
            )

        # Дополнительное логирование в user_actions.log
        logger.bind(user_id=chat_id).info(
            f"Activity: {action} | {username} | {payload[:50]}"
        )

    except Exception as e:
        logger.error(f"Ошибка логирования активности: {e}")


def log_incident(chat_id: int, incident_data: dict):
    """Логирует инцидент в JSON с защитой от поврежденных файлов"""
    try:
        log_file = "logs/incidents.json"
        incidents = []

        if os.path.exists(log_file):
            try:
                with open(log_file, "r", encoding="utf-8-sig") as f:
                    incidents = json.load(f)
            except json.JSONDecodeError as e:
                logger.error(f"Поврежденный JSON файл {log_file}: {e}")
                # Создаем бэкап и начинаем с чистого файла
                import time

                backup_file = f"{log_file}.backup_{int(time.time())}"
                os.rename(log_file, backup_file)
                logger.info(f"Создан бэкап поврежденного файла: {backup_file}")
                incidents = []

        incidents.append(
            {
                "timestamp": datetime.now().isoformat(),
                "user_id": chat_id,
                "incident": incident_data,
            }
        )

        with open(log_file, "w", encoding="utf-8-sig") as f:
            json.dump(incidents, f, ensure_ascii=False, indent=2)
    except Exception as e:
        logger.error(f"Ошибка логирования инцидента: {e}")


def log_suggestion(chat_id: int, suggestion_data: dict):
    """Логирует предложение по улучшению в JSON"""
    try:
        log_file = "logs/suggestions.json"
        suggestions = []

        if os.path.exists(log_file):
            with open(log_file, "r", encoding="utf-8-sig") as f:
                suggestions = json.load(f)

        suggestions.append(
            {
                "timestamp": datetime.now().isoformat(),
                "user_id": chat_id,
                "suggestion": suggestion_data,
            }
        )

        with open(log_file, "w", encoding="utf-8-sig") as f:
            json.dump(suggestions, f, ensure_ascii=False, indent=2)
    except Exception as e:
        logger.error(f"Ошибка логирования предложения: {e}")


def get_back_keyboard():
    """Возвращает клавиатуру с кнопкой 'Назад'"""
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add(types.KeyboardButton("⬅️ Назад"))
    return markup


def get_main_menu_keyboard():
    """Возвращает главное меню с 3 кнопками (каждая на отдельной строке)"""
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add(types.KeyboardButton("❗ Сообщите об опасности"))
    markup.add(types.KeyboardButton("🏠 Ближайшее укрытие"))
    markup.add(types.KeyboardButton("💡 Предложение по улучшению"))
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
        is_valid, validation_error = validate_user_input(
            sanitized_text, min_length=1, max_length=1000
        )

        if not is_valid:
            return "danger_report", f"❌ {validation_error}"
    except ImportError:
        # Если импорт не удался, используем оригинальный текст
        sanitized_text = text

    if sanitized_text == "⬅️ Назад":
        return "main_menu", None

    step = user_data.get("step", "description")

    if step == "description":
        # Проверяем, что это не кнопка
        if sanitized_text in [
            "📍 Отправить геолокацию",
            "📝 Указать текстом",
            "⏭️ Пропустить",
            "⬅️ Назад",
            "📷 Продолжить",
        ]:
            return (
                "danger_report",
                "❌ Пожалуйста, введите текстовое описание инцидента, а не нажимайте кнопки",
            )

        if len(sanitized_text) > 500:
            return "danger_report", "❌ Описание слишком длинное! Максимум 500 символов."

        if len(sanitized_text.strip()) < 10:
            return "danger_report", "❌ Описание слишком короткое! Минимум 10 символов."

        user_data["description"] = sanitized_text.strip()
        user_data["step"] = "location"

        log_activity(chat_id, username, "danger_description", text[:50])

        markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
        markup.add(
            types.KeyboardButton("📍 Отправить геолокацию", request_location=True)
        )
        markup.add(types.KeyboardButton("📝 Указать текстом"))
        markup.add(types.KeyboardButton("⏭️ Пропустить"))
        markup.add(types.KeyboardButton("⬅️ Назад"))

        return "danger_report", {
            "text": (
                "📍 Укажите местоположение инцидента:\n\n"
                "• Введите текст с описанием места\n"
                "• Или нажмите кнопку 'Отправить геолокацию'\n"
                "• Или нажмите 'Пропустить'"
            ),
            "reply_markup": markup,
        }

    elif step == "location":
        if text == "⏭️ Пропустить":
            user_data["step"] = "media"
            user_data["location_text"] = "Не указано"
            return "danger_report", {
                "text": "📷 Прикрепите фото/видео (до 3 файлов) или нажмите 'Продолжить':",
                "reply_markup": get_media_keyboard(),
            }
        elif text == "📝 Указать текстом":
            user_data["step"] = "location_text"
            return "danger_report", {
                "text": "📍 Укажите местоположение инцидента текстом (максимум 200 символов):",
                "reply_markup": get_back_keyboard(),
            }
        elif text == "⬅️ Назад":
            # Возвращаемся к описанию
            user_data["step"] = "description"
            return "danger_report", {
                "text": "❗ Сообщите об опасности\n\n📝 Опишите что произошло (максимум 500 символов):",
                "reply_markup": get_back_keyboard(),
            }
        else:
            # Если пользователь вводит текст, считаем это указанием
            # местоположения текстом
            if len(text) > 200:
                return (
                    "danger_report",
                    "❌ Описание места слишком длинное! Максимум 200 символов.",
                )

            if len(text.strip()) < 3:
                return (
                    "danger_report",
                    "❌ Описание места слишком короткое! Минимум 3 символа.",
                )

            user_data["location_text"] = text.strip()
            user_data["step"] = "media"

            log_activity(chat_id, username, "danger_location_text", text[:50])

            return "danger_report", {
                "text": (
                    f"✅ Место указано: {text.strip()}\n\n"
                    f"📷 Прикрепите фото/видео (до 3 файлов) или нажмите 'Продолжить':"
                ),
                "reply_markup": get_media_keyboard(),
            }

    elif step == "location_text":
        # Проверяем, что это не кнопка
        if text in [
            "📍 Отправить геолокацию",
            "📝 Указать текстом",
            "⏭️ Пропустить",
            "📷 Продолжить",
        ]:
            return (
                "danger_report",
                "❌ Пожалуйста, введите текстовое описание места, а не нажимайте кнопки",
            )
        elif text == "⬅️ Назад":
            # Возвращаемся к выбору способа указания места
            user_data["step"] = "location"
            return "danger_report", {
                "text": "📍 Укажите место происшествия:",
                "reply_markup": get_location_keyboard(),
            }

        if len(text) > 200:
            return (
                "danger_report",
                "❌ Описание места слишком длинное! Максимум 200 символов.",
            )

        if len(text.strip()) < 3:
            return (
                "danger_report",
                "❌ Описание места слишком короткое! Минимум 3 символа.",
            )

        user_data["location_text"] = text.strip()
        user_data["step"] = "media"

        log_activity(chat_id, username, "danger_location_text", text[:50])

        return "danger_report", {
            "text": (
                f"✅ Место указано: {text.strip()}\n\n"
                f"📷 Прикрепите фото/видео (до 3 файлов) или нажмите 'Продолжить':"
            ),
            "reply_markup": get_media_keyboard(),
        }

    elif step == "media":
        if text == "📷 Продолжить":
            return finish_danger_report(message, user_data, placeholders)
        elif text == "📍 Изменить место":
            user_data["step"] = "location"
            return "danger_report", {
                "text": "📍 Укажите место происшествия:",
                "reply_markup": get_location_keyboard(),
            }
        elif text == "📝 Изменить описание":
            user_data["step"] = "description"
            return "danger_report", {
                "text": "❗ Сообщите об опасности\n\n📝 Опишите что произошло (максимум 500 символов):",
                "reply_markup": get_back_keyboard(),
            }
        elif text == "❌ Отменить":
            user_data.clear()
            return "main_menu", {
                "text": "❌ Сообщение об опасности отменено",
                "reply_markup": get_main_menu_keyboard(),
            }
        elif text == "⬅️ Назад":
            # Возвращаемся к выбору места
            user_data["step"] = "location"
            return "danger_report", {
                "text": "📍 Укажите место происшествия:",
                "reply_markup": get_location_keyboard(),
            }
        else:
            # Игнорируем текст, который не является кнопкой
            return (
                "danger_report",
                "❌ Прикрепите медиафайлы или выберите действие из меню",
            )


def handle_danger_report_location(message, user_data):
    """Обработка геолокации в процессе сообщения об опасности"""
    chat_id = message.chat.id
    username = message.from_user.username or "Unknown"

    user_data["location"] = {
        "latitude": message.location.latitude,
        "longitude": message.location.longitude,
    }
    user_data["step"] = "media"

    log_activity(
        chat_id,
        username,
        "danger_location",
        f"lat: {message.location.latitude}, lon: {message.location.longitude}",
    )

    return {
        "text": "✅ Геолокация получена!\n📷 Прикрепите фото/видео (до 3 файлов) или нажмите 'Продолжить':",
        "reply_markup": get_media_keyboard(),
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
    if "media" not in user_data:
        user_data["media"] = []

    if len(user_data["media"]) >= 3:
        return "❌ Максимум 3 медиафайла!"

    media_info = {
        "type": message.content_type,
        "file_id": (
            message.photo[-1].file_id
            if message.photo
            else (message.video.file_id if message.video else message.document.file_id)
        ),
        "file_size": file_size,
    }
    user_data["media"].append(media_info)

    log_activity(
        chat_id,
        username,
        "danger_media",
        f"type: {message.content_type}, size: {file_size}",
    )

    remaining = 3 - len(user_data["media"])
    return f"✅ Медиафайл добавлен ({len(user_data['media'])}/3). Осталось: {remaining}"


def finish_danger_report(message, user_data, placeholders):
    """Завершение процесса сообщения об опасности"""
    chat_id = message.chat.id
    username = message.from_user.username or "Unknown"

    # Создаем сводку инцидента
    incident_data = {
        "description": user_data.get("description", ""),
        "location": user_data.get("location"),
        "location_text": user_data.get("location_text"),
        "media_count": len(user_data.get("media", [])),
        "media": user_data.get("media", []),  # Добавляем медиафайлы
        "user_id": chat_id,
        "username": username,
    }

    # Логируем инцидент
    log_incident(chat_id, incident_data)
    log_activity(chat_id, username, "danger_report_completed")

    # Отправляем уведомления об инциденте
    try:
        # Отправляем в Telegram админу
        admin_chat_id = os.getenv("ADMIN_CHAT_ID")
        if admin_chat_id:
            from datetime import datetime

            current_time = datetime.now()

            admin_text = "🚨 НОВЫЙ ИНЦИДЕНТ\n\n"
            admin_text += f"👤 Пользователь: {username} (ID: {chat_id})\n"
            admin_text += f"📝 Описание: {incident_data['description']}\n"
            if incident_data["location"]:
                lat = incident_data["location"]["latitude"]
                lon = incident_data["location"]["longitude"]
                admin_text += f"📍 Координаты: {lat}, {lon}\n"
            elif incident_data["location_text"]:
                admin_text += f"📍 Место: {incident_data['location_text']}\n"
            else:
                admin_text += "📍 Место: Не указано\n"
            admin_text += f"📷 Медиафайлов: {incident_data['media_count']}\n"
            admin_text += f"🕐 Время: {current_time.strftime('%d.%m.%Y %H:%M:%S')} МСК"

            logger.info(f"Отправка админу в Telegram: {admin_text}")

            # Отправляем сообщение админу через глобальный объект bot
            if bot_instance:
                try:
                    bot_instance.send_message(admin_chat_id, admin_text)
                    logger.info("✅ Уведомление админу в Telegram отправлено")

                    # Отправляем медиафайлы админу
                    if incident_data["media"]:
                        logger.info(
                            f"📷 Отправка {len(incident_data['media'])} медиафайлов админу"
                        )
                        for i, media_item in enumerate(incident_data["media"], 1):
                            try:
                                if media_item["type"] == "photo":
                                    bot_instance.send_photo(
                                        admin_chat_id,
                                        media_item["file_id"],
                                        caption=f"📷 Медиафайл {i}/{len(incident_data['media'])}",
                                    )
                                elif media_item["type"] == "video":
                                    bot_instance.send_video(
                                        admin_chat_id,
                                        media_item["file_id"],
                                        caption=f"🎥 Медиафайл {i}/{len(incident_data['media'])}",
                                    )
                                elif media_item["type"] == "document":
                                    bot_instance.send_document(
                                        admin_chat_id,
                                        media_item["file_id"],
                                        caption=f"📄 Медиафайл {i}/{len(incident_data['media'])}",
                                    )
                                logger.info(f"✅ Медиафайл {i} отправлен админу")
                            except Exception as media_error:
                                logger.error(
                                    f"❌ Ошибка отправки медиафайла {i}: {media_error}"
                                )

                except Exception as bot_error:
                    logger.error(f"❌ Ошибка отправки админу в Telegram: {bot_error}")
            else:
                logger.warning(
                    "⚠️ Объект bot не инициализирован для отправки уведомления админу"
                )
        else:
            logger.warning("⚠️ ADMIN_CHAT_ID не настроен")

        logger.info("🔍 Переход к email уведомлениям...")

        # Скачиваем медиафайлы для email
        downloaded_media = []
        if incident_data.get("media") and bot_instance:
            logger.info(
                f"📷 Скачивание {len(incident_data['media'])} медиафайлов для email..."
            )
            import mimetypes

            for media_item in incident_data["media"]:
                try:
                    file_info = bot_instance.get_file(media_item["file_id"])
                    downloaded_file = bot_instance.download_file(file_info.file_path)

                    # Определяем правильное расширение файла из пути Telegram
                    file_extension = os.path.splitext(file_info.file_path)[1] or ".jpg"

                    # Определяем MIME-тип
                    mime_type = mimetypes.guess_type(file_info.file_path)[0]
                    if not mime_type:
                        # Fallback для разных типов медиа
                        if media_item["type"] == "photo":
                            mime_type = "image/jpeg"
                        elif media_item["type"] == "video":
                            mime_type = "video/mp4"
                        elif media_item["type"] == "document":
                            mime_type = "application/octet-stream"
                        else:
                            mime_type = "application/octet-stream"

                    downloaded_media.append(
                        {
                            "data": downloaded_file,
                            "type": media_item["type"],
                            "filename": f"{media_item['type']}_{media_item['file_id'][:8]}{file_extension}",
                            "mime_type": mime_type,
                        }
                    )
                    logger.info(
                        f"✅ Медиафайл {media_item['type']} скачан для email (MIME: {mime_type})"
                    )
                except Exception as e:
                    logger.error(f"❌ Ошибка скачивания медиафайла: {e}")

        # Отправляем через Яндекс уведомления
        logger.info(f"🔍 NOTIFICATIONS_AVAILABLE: {NOTIFICATIONS_AVAILABLE}")
        if NOTIFICATIONS_AVAILABLE:
            try:
                logger.info("🔍 Вызов send_incident_notification...")
                notification_success, notification_message = send_incident_notification(
                    incident_data, downloaded_media
                )
                if notification_success:
                    logger.info(
                        f"✅ Яндекс уведомления отправлены: {notification_message}"
                    )
                else:
                    logger.warning(
                        f"⚠️ Ошибка Яндекс уведомлений: {notification_message}"
                    )
            except Exception as e:
                logger.error(f"❌ Ошибка вызова send_incident_notification: {e}")
        else:
            logger.warning("⚠️ Сервис Яндекс уведомлений недоступен")

    except Exception as e:
        logger.error(f"Ошибка отправки уведомлений: {e}")

    # Создаем клавиатуру с кнопками звонков (каждая на отдельной строке)
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add(types.KeyboardButton("📞 Позвонить в службу безопасности"))
    markup.add(types.KeyboardButton("📞 Позвонить в охрану труда"))
    markup.add(types.KeyboardButton("🏠 Главное меню"))

    response_text = (
        "✅ Инцидент зарегистрирован!\n\n"
        "📝 Описание: {}\n"
        "📍 Местоположение: {}\n"
        "📷 Медиафайлов: {}\n"
        "🕐 Время: {}\n\n"
        "🚨 Срочные контакты:\n"
        "📞 Служба безопасности: {}\n"
        "📞 Охрана труда: {}\n\n"
        "Спасибо за оперативное сообщение!"
    ).format(
        incident_data["description"],
        (
            "Координаты: {:.6f}, {:.6f}".format(
                incident_data["location"]["latitude"],
                incident_data["location"]["longitude"],
            )
            if incident_data["location"]
            else (
                incident_data["location_text"]
                if incident_data["location_text"]
                else "Не указано"
            )
        ),
        incident_data["media_count"],
        datetime.now().strftime("%d.%m.%Y %H:%M:%S") + " МСК",
        placeholders.get("contacts", {}).get("security", "Не указан"),
        placeholders.get("contacts", {}).get("safety", "Не указан"),
    )

    # Отправляем сообщение пользователю
    try:
        bot_instance.send_message(chat_id, response_text, reply_markup=markup)
        logger.info("✅ Пользователь уведомлен о регистрации инцидента")
    except Exception as e:
        logger.error(f"❌ Ошибка уведомления пользователя: {e}")

    # Возвращаем только состояние, без повторной отправки сообщения
    return "main_menu", None


def get_location_keyboard():
    """Клавиатура для выбора места"""
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add(types.KeyboardButton("📍 Отправить геолокацию", request_location=True))
    markup.add(types.KeyboardButton("📝 Указать текстом"))
    markup.add(types.KeyboardButton("⏭️ Пропустить"))
    markup.add(types.KeyboardButton("⬅️ Назад"))
    return markup


def get_media_keyboard():
    """Клавиатура для работы с медиа"""
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add(types.KeyboardButton("📷 Продолжить"))
    markup.add(types.KeyboardButton("📍 Изменить место"))
    markup.add(types.KeyboardButton("📝 Изменить описание"))
    markup.add(types.KeyboardButton("❌ Отменить"))
    markup.add(types.KeyboardButton("⬅️ Назад"))
    return markup


# === ОБРАБОТЧИКИ ДЛЯ "БЛИЖАЙШЕЕ УБЕЖИЩЕ" ===


def handle_shelter_finder_text(message, placeholders):
    """Обработка текста в поиске убежищ"""
    text = message.text

    if text == "⬅️ Назад":
        return "main_menu", None
    elif text == "⏭️ Пропустить":
        # Возвращаем данные для отправки изображений убежищ
        shelters = placeholders.get("shelters", [])
        return "shelter_finder", {
            "shelters": shelters,
            "action": "show_shelters_with_photos",
        }
    else:
        return "shelter_finder", "❌ Отправьте геолокацию или нажмите 'Пропустить'"


# === ОБРАБОТЧИКИ ДЛЯ "ПРЕДЛОЖЕНИЕ ПО УЛУЧШЕНИЮ" ===


def handle_improvement_suggestion_text(message, placeholders, user_data):
    """Обработка текста предложения по улучшению"""
    chat_id = message.chat.id
    username = message.from_user.username or "Unknown"
    text = message.text

    if text == "⬅️ Назад":
        return "main_menu", None

    # Проверяем, что это не кнопка
    if text in [
        "❗ Сообщите об опасности",
        "🏠 Ближайшее укрытие",
        "💡 Предложение по улучшению",
    ]:
        return (
            "improvement_suggestion",
            "❌ Пожалуйста, введите текстовое предложение, а не нажимайте кнопки",
        )

    if len(text) > 1000:
        return (
            "improvement_suggestion",
            "❌ Предложение слишком длинное! Максимум 1000 символов.",
        )

    if len(text.strip()) < 10:
        return (
            "improvement_suggestion",
            "❌ Предложение слишком короткое! Минимум 10 символов.",
        )

    # Сохраняем предложение
    suggestion_data = {
        "text": text.strip(),
        "user_id": chat_id,
        "username": username,
        "timestamp": datetime.now().isoformat(),
        "votes": 0,
        "voters": [],
        "status": "pending",
    }

    # Сохраняем в улучшенном формате
    save_enhanced_suggestion(chat_id, suggestion_data)
    log_suggestion(chat_id, suggestion_data)
    log_activity(chat_id, username, "suggestion_submitted", text[:50])

    response_text = (
        "✅ Ваше предложение отправлено разработчикам!\n\n"
        "📝 Ваше предложение:\n{}\n\n"
        "🗳️ Лучшие предложения будут выставлены на голосование для сотрудников завода РПРЗ.\n\n"
        "Спасибо за вашу активность!"
    ).format(text)

    return "main_menu", {
        "text": response_text,
        "reply_markup": get_main_menu_keyboard(),
    }


def save_enhanced_suggestion(chat_id, suggestion_data):
    """Сохраняет предложение в улучшенном формате"""
    try:
        suggestions_file = "logs/enhanced_suggestions.json"
        suggestions = []

        if os.path.exists(suggestions_file):
            with open(suggestions_file, "r", encoding="utf-8-sig") as f:
                suggestions = json.load(f)

        # Добавляем ID предложения
        suggestion_data["id"] = len(suggestions) + 1
        suggestions.append(suggestion_data)

        with open(suggestions_file, "w", encoding="utf-8") as f:
            json.dump(suggestions, f, ensure_ascii=False, indent=2)

    except Exception as e:
        logger.error(f"Ошибка сохранения улучшенного предложения: {e}")


def handle_improvement_suggestion_choice(message, placeholders):
    """Обработка выбора категории предложения"""
    text = message.text

    if text == "⬅️ Назад":
        return "main_menu", None

    categories = {
        "1️⃣ Производительность": "performance",
        "2️⃣ Уведомления": "notifications",
        "3️⃣ Функциональность": "functionality",
        "4️⃣ Свободная форма": "free_form",
    }

    if text in categories:
        category = categories[text]
        return "improvement_suggestion", {
            "text": f"Категория выбрана: {category}\n\nТеперь опишите ваше предложение:",
            "category": category,
        }

    return "improvement_suggestion", "❌ Выберите категорию из меню"


def categorize_suggestion(text: str) -> str:
    """Автоматическая категоризация предложений"""
    text_lower = text.lower()

    if any(word in text_lower for word in ["быстр", "медлен", "производ", "скорост"]):
        return "performance"
    elif any(word in text_lower for word in ["уведомл", "оповещ", "нотиф"]):
        return "notifications"
    elif any(
        word in text_lower for word in ["функци", "возможност", "фича", "добавить"]
    ):
        return "functionality"
    else:
        return "general"


def handle_suggestion_menu(message, user_data):
    """Обработка меню предложений"""
    text = message.text

    if text == "🏆 Популярные предложения":
        return show_popular_suggestions(message)
    elif text == "📋 Мои предложения":
        return show_user_suggestions(message)
    elif text == "💡 Новое предложение":
        return "improvement_suggestion", "📝 Напишите ваше предложение:"
    elif text == "⬅️ Назад":
        return "main_menu", None

    return "suggestion_menu", "❌ Выберите действие из меню"


def show_popular_suggestions(message):
    """Показывает топ-10 популярных предложений"""
    try:
        suggestions_file = "logs/enhanced_suggestions.json"
        if not os.path.exists(suggestions_file):
            return {
                "text": "📋 Пока нет предложений",
                "reply_markup": get_back_keyboard(),
            }

        with open(suggestions_file, "r", encoding="utf-8") as f:
            suggestions = json.load(f)

        # Сортируем по голосам
        popular = sorted(suggestions, key=lambda x: x.get("votes", 0), reverse=True)[
            :10
        ]

        if not popular:
            return {
                "text": "📋 Пока нет предложений",
                "reply_markup": get_back_keyboard(),
            }

        text = "🏆 ТОП-10 ПОПУЛЯРНЫХ ПРЕДЛОЖЕНИЙ:\n\n"
        for i, sugg in enumerate(popular, 1):
            text += f"{i}. 👍 {sugg.get('votes', 0)} | {sugg['text'][:50]}...\n\n"

        return {"text": text, "reply_markup": get_back_keyboard()}

    except Exception as e:
        logger.error(f"Ошибка показа популярных предложений: {e}")
        return {
            "text": "❌ Ошибка загрузки предложений",
            "reply_markup": get_back_keyboard(),
        }


def show_user_suggestions(message):
    """Показывает предложения пользователя"""
    chat_id = message.chat.id

    try:
        suggestions_file = "logs/enhanced_suggestions.json"
        if not os.path.exists(suggestions_file):
            return {
                "text": "📋 У вас пока нет предложений",
                "reply_markup": get_back_keyboard(),
            }

        with open(suggestions_file, "r", encoding="utf-8") as f:
            suggestions = json.load(f)

        # Фильтруем по пользователю
        user_suggestions = [s for s in suggestions if s.get("user_id") == chat_id]

        if not user_suggestions:
            return {
                "text": "📋 У вас пока нет предложений",
                "reply_markup": get_back_keyboard(),
            }

        text = "📋 ВАШИ ПРЕДЛОЖЕНИЯ:\n\n"
        for i, sugg in enumerate(user_suggestions, 1):
            text += f"{i}. 👍 {sugg.get('votes', 0)} | {sugg['text'][:50]}...\n\n"

        return {"text": text, "reply_markup": get_back_keyboard()}

    except Exception as e:
        logger.error(f"Ошибка показа предложений пользователя: {e}")
        return {
            "text": "❌ Ошибка загрузки ваших предложений",
            "reply_markup": get_back_keyboard(),
        }


def test_email_notifications(message):
    """Тестирует отправку email уведомлений (только для админов)"""
    try:
        from datetime import datetime

        from bot.notifications import send_incident_notification

        # Тестовые данные инцидента
        test_incident = {
            "type": "ТЕСТ EMAIL",
            "user_name": message.from_user.first_name or "Test User",
            "user_id": message.from_user.id,
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "description": "Тестовое уведомление для проверки настройки email в Railway",
            "severity": "НИЗКАЯ",
        }

        logger.info("🧪 Тестирование email уведомлений...")

        # Отправляем тестовое уведомление
        success, result_message = send_incident_notification(test_incident)

        if success:
            bot_instance.send_message(
                message.chat.id,
                f"✅ Тестовое email уведомление отправлено!\n\n"
                f"📧 Результат: {result_message}\n"
                f"📬 Проверьте почту: {os.getenv('ADMIN_EMAIL', 'не настроено')}",
                reply_markup=get_back_keyboard(),
            )
            logger.info(
                f"✅ Тестовое email уведомление успешно отправлено: {result_message}"
            )
        else:
            bot_instance.send_message(
                message.chat.id,
                f"❌ Ошибка отправки email уведомления!\n\n"
                f"🔍 Проблема: {result_message}\n\n"
                f"📝 Проверьте настройки SMTP в Railway Variables",
                reply_markup=get_back_keyboard(),
            )
            logger.warning(f"❌ Ошибка тестового email уведомления: {result_message}")

    except Exception as e:
        logger.error(f"Ошибка тестирования email: {e}")
        bot_instance.send_message(
            message.chat.id,
            f"❌ Ошибка тестирования email уведомлений: {str(e)}",
            reply_markup=get_back_keyboard(),
        )
