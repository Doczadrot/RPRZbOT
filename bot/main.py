import os
import logging
import json
import csv
from datetime import datetime
from dotenv import load_dotenv
from telegram import Update, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

# Загружаем переменные окружения
load_dotenv()

# Создаем директорию для логов перед настройкой логирования
os.makedirs('logs', exist_ok=True)

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

# Функция логирования активности
def log_activity(user_id, username, action, payload_summary="", response_ref=""):
    """Логирует активность пользователя в CSV файл"""
    try:
        activity_file = 'logs/activity.csv'
        file_exists = os.path.exists(activity_file)
        
        with open(activity_file, 'a', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            
            # Записываем заголовки, если файл новый
            if not file_exists:
                writer.writerow(['timestamp', 'user_id', 'username', 'action', 'payload_summary', 'response_ref'])
            
            # Записываем данные
            writer.writerow([
                datetime.now().isoformat(),
                user_id,
                username or 'Unknown',
                action,
                payload_summary[:100],  # Ограничиваем длину
                response_ref
            ])
            
    except Exception as e:
        logger.error(f"Ошибка логирования активности: {e}")

# Функция защиты от спама
def check_spam_protection(user_id):
    """Проверяет защиту от спама (максимум 10 сообщений в минуту)"""
    current_time = datetime.now()
    
    if user_id not in user_states:
        user_states[user_id] = {
            'state': 'idle',
            'data': {},
            'message_times': []
        }
    
    # Очищаем старые сообщения (старше минуты)
    user_states[user_id]['message_times'] = [
        msg_time for msg_time in user_states[user_id]['message_times']
        if (current_time - msg_time).total_seconds() < 60
    ]
    
    # Проверяем лимит
    if len(user_states[user_id]['message_times']) >= 10:
        return False
    
    # Добавляем текущее время
    user_states[user_id]['message_times'].append(current_time)
    return True

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
    
    # Логируем активность
    log_activity(user.id, user.username, "start_command")
    
    welcome_text = (
        "🛡️ Добро пожаловать в систему безопасности РПРЗ!\n\n"
        "Выберите нужную функцию:"
    )
    
    await update.message.reply_text(
        welcome_text,
        reply_markup=get_main_menu()
    )

# Обработчик команды /my_history
async def my_history(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    user_id = user.id
    
    # Логируем активность
    log_activity(user_id, user.username, "history_requested")
    
    try:
        # Читаем логи активности
        activity_file = 'logs/activity.csv'
        if not os.path.exists(activity_file):
            await update.message.reply_text(
                "📊 **Ваша история**\n\n"
                "История активности пока пуста.",
                reply_markup=get_main_menu()
            )
            return
        
        user_activities = []
        with open(activity_file, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                if int(row['user_id']) == user_id:
                    user_activities.append(row)
        
        if not user_activities:
            await update.message.reply_text(
                "📊 **Ваша история**\n\n"
                "История активности пока пуста.",
                reply_markup=get_main_menu()
            )
            return
        
        # Формируем сообщение с историей
        text = "📊 **Ваша история активности**\n\n"
        
        # Показываем последние 10 записей
        recent_activities = user_activities[-10:]
        
        for activity in recent_activities:
            timestamp = datetime.fromisoformat(activity['timestamp'])
            time_str = timestamp.strftime('%d.%m.%Y %H:%M')
            
            action_name = {
                'start_command': '🚀 Запуск бота',
                'text_message': '💬 Сообщение',
                'danger_report_started': '🚨 Сообщение об опасности',
                'incident_saved': '✅ Инцидент сохранен',
                'shelter_finder_started': '🏠 Поиск убежищ',
                'safety_consultant_started': '🧑‍🏫 Консультант',
                'question_asked': '❓ Вопрос задан',
                'history_requested': '📊 Запрос истории'
            }.get(activity['action'], activity['action'])
            
            text += f"• {time_str} - {action_name}\n"
            if activity['payload_summary']:
                text += f"  {activity['payload_summary']}\n"
            text += "\n"
        
        # Добавляем статистику
        total_actions = len(user_activities)
        text += f"📈 **Всего действий:** {total_actions}\n"
        
        # Подсчитываем типы действий
        action_counts = {}
        for activity in user_activities:
            action = activity['action']
            action_counts[action] = action_counts.get(action, 0) + 1
        
        text += "\n📊 **Статистика:**\n"
        for action, count in action_counts.items():
            action_name = {
                'start_command': 'Запуски бота',
                'text_message': 'Сообщения',
                'danger_report_started': 'Сообщения об опасности',
                'incident_saved': 'Сохраненные инциденты',
                'shelter_finder_started': 'Поиски убежищ',
                'safety_consultant_started': 'Обращения к консультанту',
                'question_asked': 'Заданные вопросы',
                'history_requested': 'Запросы истории'
            }.get(action, action)
            text += f"• {action_name}: {count}\n"
        
        # Разбиваем на части, если сообщение слишком длинное
        if len(text) > 4000:
            parts = text.split('\n\n')
            current_part = ""
            
            for part in parts:
                if len(current_part + part) > 4000:
                    await update.message.reply_text(
                        current_part,
                        reply_markup=get_main_menu(),
                        parse_mode='Markdown'
                    )
                    current_part = part + "\n\n"
                else:
                    current_part += part + "\n\n"
            
            if current_part.strip():
                await update.message.reply_text(
                    current_part,
                    reply_markup=get_main_menu(),
                    parse_mode='Markdown'
                )
        else:
            await update.message.reply_text(
                text,
                reply_markup=get_main_menu(),
                parse_mode='Markdown'
            )
            
    except Exception as e:
        logger.error(f"Ошибка получения истории пользователя {user_id}: {e}")
        await update.message.reply_text(
            "❌ Ошибка получения истории. Попробуйте позже.",
            reply_markup=get_main_menu()
        )

# Обработчик текстовых сообщений
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    text = update.message.text
    user_id = user.id
    
    # Проверяем защиту от спама
    if not check_spam_protection(user_id):
        await update.message.reply_text(
            "⚠️ Слишком много сообщений. Подождите минуту и попробуйте снова.",
            reply_markup=get_main_menu()
        )
        return
    
    logger.info(f"Пользователь {user_id} отправил сообщение: {text}")
    
    # Логируем активность
    log_activity(user_id, user.username, "text_message", text[:50])
    
    # Проверяем состояние пользователя для диалога "Сообщите об опасности"
    if user_id in user_states:
        state = user_states[user_id]['state']
        
        if state == 'danger_description':
            await handle_danger_description(update, context)
            return
        elif state == 'danger_location':
            await handle_danger_location(update, context)
            return
        elif state == 'danger_media':
            if text == "📷 Прикрепить фото/видео":
                await update.message.reply_text(
                    "Прикрепите фото или видео к следующему сообщению",
                    reply_markup=ReplyKeyboardMarkup([
                        ['⏭️ Пропустить'],
                        ['⬅️ Назад']
                    ], resize_keyboard=True)
                )
                return
            elif text == "⏭️ Пропустить":
                await handle_danger_skip_media(update, context)
                return
            elif text == "📷 Прикрепить еще":
                await update.message.reply_text(
                    "Прикрепите фото или видео к следующему сообщению",
                    reply_markup=ReplyKeyboardMarkup([
                        ['⏭️ Продолжить'],
                        ['⬅️ Назад']
                    ], resize_keyboard=True)
                )
                return
            elif text == "⏭️ Продолжить":
                await handle_danger_continue(update, context)
                return
        elif state == 'danger_confirm':
            if text == "✅ Отправить сообщение":
                await handle_danger_confirm(update, context)
                return
            elif text == "✏️ Редактировать":
                # Возвращаемся к началу
                user_states[user_id] = {
                    'state': 'danger_description',
                    'data': {}
                }
                await handle_danger_report(update, context)
                return
            elif text == "❌ Отменить":
                if user_id in user_states:
                    del user_states[user_id]
                await update.message.reply_text(
                    "Сообщение об опасности отменено.",
                    reply_markup=get_main_menu()
                )
                return
        elif state == 'shelter_location':
            if text == "📍 Отправить геолокацию":
                await update.message.reply_text(
                    "Отправьте вашу геолокацию кнопкой ниже",
                    reply_markup=ReplyKeyboardMarkup([
                        [KeyboardButton("📍 Отправить геолокацию", request_location=True)],
                        ['⏭️ Пропустить'],
                        ['⬅️ Назад']
                    ], resize_keyboard=True)
                )
                return
            elif text == "⏭️ Пропустить":
                await show_shelters(update, context)
                return
        elif state == 'consultant_menu':
            if text == "📄 Список документов":
                await handle_documents_list(update, context)
                return
            elif text == "❓ Задать вопрос":
                await handle_ask_question(update, context)
                return
        elif state == 'waiting_question':
            await handle_question_response(update, context)
            return
        elif state == 'question_answered':
            if text == "📖 Подробнее":
                await handle_detailed_answer(update, context)
                return
            elif text == "📄 Открыть PDF":
                await handle_open_question_pdf(update, context)
                return
            elif text == "❓ Задать другой вопрос":
                await handle_another_question(update, context)
                return
    
    # Обработка кнопок навигации
    if text == "⬅️ Назад" or text == "⬅️ Главное меню":
        if user_id in user_states:
            del user_states[user_id]
        await update.message.reply_text(
            "Главное меню",
            reply_markup=get_main_menu()
        )
        return
    
    # Обработка кнопок после отправки сообщения об опасности
    if text == "📞 Позвонить в службу безопасности":
        await handle_security_call(update, context)
        return
    elif text == "📞 Позвонить в охрану труда":
        await handle_safety_call(update, context)
        return
    
    # Обработка кнопок убежищ
    if text in ["🔍 Показать на карте", "🌐 Открыть в Яндекс.Картах"]:
        await handle_shelter_actions(update, context)
        return
    
    # Обработка кнопок документов
    if text.startswith("📄 Открыть документ "):
        await handle_open_document(update, context)
        return
    
    # Основные функции
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

# Обработчик "Сообщите об опасности"
async def handle_danger_report(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user = update.effective_user
    
    # Логируем активность
    log_activity(user_id, user.username, "danger_report_started")
    
    # Инициализируем состояние пользователя
    user_states[user_id] = {
        'state': 'danger_description',
        'data': {}
    }
    
    keyboard = [['⬅️ Назад']]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    
    await update.message.reply_text(
        "🚨 **Сообщение об опасности**\n\n"
        "Опишите, что произошло. Будьте максимально конкретны:\n"
        "• Что именно случилось?\n"
        "• Когда это произошло?\n"
        "• Есть ли пострадавшие?",
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )

# Обработчик описания опасности
async def handle_danger_description(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    
    if user_id not in user_states or user_states[user_id]['state'] != 'danger_description':
        return
    
    user_states[user_id]['data']['description'] = update.message.text
    user_states[user_id]['state'] = 'danger_location'
    
    keyboard = [['⬅️ Назад']]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    
    await update.message.reply_text(
        "📍 **Местоположение**\n\n"
        "Укажите, где именно произошла ситуация:\n"
        "• Адрес или номер корпуса\n"
        "• Этаж, кабинет, лаборатория\n"
        "• Любые ориентиры",
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )

# Обработчик местоположения
async def handle_danger_location(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    
    if user_id not in user_states or user_states[user_id]['state'] != 'danger_location':
        return
    
    user_states[user_id]['data']['location'] = update.message.text
    user_states[user_id]['state'] = 'danger_media'
    
    keyboard = [
        ['📷 Прикрепить фото/видео'],
        ['⏭️ Пропустить'],
        ['⬅️ Назад']
    ]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    
    await update.message.reply_text(
        "📎 **Медиафайлы**\n\n"
        "Можете прикрепить фото или видео, если это поможет понять ситуацию.\n"
        "Максимальный размер: фото до 20 МБ, видео до 300 МБ",
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )

# Обработчик медиафайлов
async def handle_danger_media(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    
    if user_id not in user_states or user_states[user_id]['state'] != 'danger_media':
        return
    
    if update.message.photo or update.message.video:
        # Сохраняем информацию о медиафайле
        if update.message.photo:
            file_id = update.message.photo[-1].file_id
            file_size = update.message.photo[-1].file_size
            file_type = 'photo'
        else:  # video
            file_id = update.message.video.file_id
            file_size = update.message.video.file_size
            file_type = 'video'
        
        # Проверяем размер файла
        max_photo_size = 20 * 1024 * 1024  # 20 МБ
        max_video_size = 300 * 1024 * 1024  # 300 МБ
        
        if file_type == 'photo' and file_size > max_photo_size:
            await update.message.reply_text(
                "❌ Файл слишком большой. Максимальный размер фото: 20 МБ",
                reply_markup=ReplyKeyboardMarkup([['⬅️ Назад']], resize_keyboard=True)
            )
            return
        elif file_type == 'video' and file_size > max_video_size:
            await update.message.reply_text(
                "❌ Файл слишком большой. Максимальный размер видео: 300 МБ",
                reply_markup=ReplyKeyboardMarkup([['⬅️ Назад']], resize_keyboard=True)
            )
            return
        
        if 'media_files' not in user_states[user_id]['data']:
            user_states[user_id]['data']['media_files'] = []
        
        user_states[user_id]['data']['media_files'].append({
            'file_id': file_id,
            'file_type': file_type,
            'file_size': file_size
        })
        
        await update.message.reply_text(
            f"✅ {file_type == 'photo' and 'Фото' or 'Видео'} добавлено. Можете прикрепить еще файлы или продолжить.",
            reply_markup=ReplyKeyboardMarkup([
                ['📷 Прикрепить еще'],
                ['⏭️ Продолжить'],
                ['⬅️ Назад']
            ], resize_keyboard=True)
        )
    else:
        await update.message.reply_text(
            "Пожалуйста, прикрепите фото или видео, или нажмите 'Пропустить'",
            reply_markup=ReplyKeyboardMarkup([
                ['📷 Прикрепить фото/видео'],
                ['⏭️ Пропустить'],
                ['⬅️ Назад']
            ], resize_keyboard=True)
        )

# Обработчик кнопки "Продолжить" после медиа
async def handle_danger_continue(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    
    if user_id not in user_states or user_states[user_id]['state'] != 'danger_media':
        return
    
    user_states[user_id]['state'] = 'danger_confirm'
    await show_danger_confirmation(update, context)

# Обработчик кнопки "Пропустить" медиа
async def handle_danger_skip_media(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    
    if user_id not in user_states or user_states[user_id]['state'] != 'danger_media':
        return
    
    user_states[user_id]['state'] = 'danger_confirm'
    await show_danger_confirmation(update, context)

# Показать подтверждение инцидента
async def show_danger_confirmation(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    data = user_states[user_id]['data']
    
    text = "📋 **Предварительный пакет**\n\n"
    text += f"**Описание:** {data['description']}\n\n"
    text += f"**Местоположение:** {data['location']}\n\n"
    
    if 'media_files' in data and data['media_files']:
        text += f"**Медиафайлы:** {len(data['media_files'])} файлов\n\n"
    
    text += "Проверьте информацию и подтвердите отправку."
    
    keyboard = [
        ['✅ Отправить сообщение'],
        ['✏️ Редактировать'],
        ['❌ Отменить']
    ]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    
    await update.message.reply_text(
        text,
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )

# Обработчик подтверждения отправки
async def handle_danger_confirm(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    
    if user_id not in user_states or user_states[user_id]['state'] != 'danger_confirm':
        return
    
    # Сохраняем инцидент
    await save_incident(update, context)
    
    # Отправляем в админ-чат
    await send_to_admin(update, context)
    
    # Показываем подтверждение пользователю
    await show_danger_success(update, context)
    
    # Очищаем состояние
    if user_id in user_states:
        del user_states[user_id]

# Сохранение инцидента в лог
async def save_incident(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    data = user_states[user_id]['data']
    
    incident = {
        'timestamp': datetime.now().isoformat(),
        'user_id': user_id,
        'username': update.effective_user.username,
        'description': data['description'],
        'location': data['location'],
        'media_files': data.get('media_files', [])
    }
    
    # Сохраняем в JSON файл
    try:
        incidents_file = 'logs/incidents.json'
        incidents = []
        
        # Читаем существующие инциденты
        try:
            with open(incidents_file, 'r', encoding='utf-8') as f:
                incidents = json.load(f)
        except FileNotFoundError:
            pass
        
        incidents.append(incident)
        
        # Записываем обновленный список
        with open(incidents_file, 'w', encoding='utf-8') as f:
            json.dump(incidents, f, ensure_ascii=False, indent=2)
        
        logger.info(f"Инцидент сохранен для пользователя {user_id}")
        
        # Логируем активность
        log_activity(user_id, update.effective_user.username, "incident_saved", 
                    f"Description: {data['description'][:30]}...")
        
    except Exception as e:
        logger.error(f"Ошибка сохранения инцидента: {e}")

# Отправка в админ-чат
async def send_to_admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    data = user_states[user_id]['data']
    admin_chat_id = os.getenv('ADMIN_CHAT_ID')
    
    if not admin_chat_id or admin_chat_id == 'ADMIN_ID_PLACEHOLDER':
        logger.warning("ADMIN_CHAT_ID не настроен")
        return
    
    try:
        # Формируем сообщение для админа
        admin_text = f"🚨 **НОВОЕ СООБЩЕНИЕ ОБ ОПАСНОСТИ**\n\n"
        admin_text += f"👤 **Пользователь:** @{update.effective_user.username} (ID: {user_id})\n"
        admin_text += f"🕐 **Время:** {datetime.now().strftime('%d.%m.%Y %H:%M')}\n\n"
        admin_text += f"📝 **Описание:** {data['description']}\n\n"
        admin_text += f"📍 **Местоположение:** {data['location']}\n\n"
        
        if 'media_files' in data and data['media_files']:
            admin_text += f"📎 **Медиафайлы:** {len(data['media_files'])} файлов\n\n"
        
        # Отправляем текстовое сообщение
        await context.bot.send_message(
            chat_id=admin_chat_id,
            text=admin_text,
            parse_mode='Markdown'
        )
        
        # Отправляем медиафайлы
        if 'media_files' in data and data['media_files']:
            for media in data['media_files']:
                try:
                    if media['file_type'] == 'photo':
                        await context.bot.send_photo(
                            chat_id=admin_chat_id,
                            photo=media['file_id'],
                            caption=f"Фото от @{update.effective_user.username}"
                        )
                    else:  # video
                        await context.bot.send_video(
                            chat_id=admin_chat_id,
                            video=media['file_id'],
                            caption=f"Видео от @{update.effective_user.username}"
                        )
                except Exception as e:
                    logger.error(f"Ошибка отправки медиафайла: {e}")
        
        logger.info(f"Сообщение отправлено админу для инцидента пользователя {user_id}")
        
    except Exception as e:
        logger.error(f"Ошибка отправки в админ-чат: {e}")

# Показать успешное завершение
async def show_danger_success(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        ['📞 Позвонить в службу безопасности'],
        ['📞 Позвонить в охрану труда'],
        ['⬅️ Главное меню']
    ]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    
    await update.message.reply_text(
        "✅ **Сообщение отправлено!**\n\n"
        "Ваше сообщение об опасности передано службе безопасности.\n"
        "При необходимости вы можете связаться с соответствующими службами:",
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )

# Обработчики кнопок после отправки
async def handle_security_call(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "📞 **Звонок в службу безопасности**\n\n"
        "Звонок (заглушка)\n"
        "В реальной версии здесь будет номер телефона службы безопасности.",
        reply_markup=ReplyKeyboardMarkup([['⬅️ Главное меню']], resize_keyboard=True)
    )

async def handle_safety_call(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "📞 **Звонок в охрану труда**\n\n"
        "Звонок (заглушка)\n"
        "В реальной версии здесь будет номер телефона отдела охраны труда.",
        reply_markup=ReplyKeyboardMarkup([['⬅️ Главное меню']], resize_keyboard=True)
    )

# Обработчик медиафайлов
async def handle_media(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    
    # Проверяем, находится ли пользователь в состоянии ожидания медиафайлов
    if user_id in user_states and user_states[user_id]['state'] == 'danger_media':
        await handle_danger_media(update, context)
    else:
        await update.message.reply_text(
            "Пожалуйста, выберите функцию из главного меню.",
            reply_markup=get_main_menu()
        )

# Обработчик "Ближайшее укрытие"
async def handle_shelter_finder(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user = update.effective_user
    
    # Логируем активность
    log_activity(user_id, user.username, "shelter_finder_started")
    
    # Инициализируем состояние пользователя
    user_states[user_id] = {
        'state': 'shelter_location',
        'data': {}
    }
    
    keyboard = [
        ['📍 Отправить геолокацию'],
        ['⏭️ Пропустить'],
        ['⬅️ Назад']
    ]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    
    await update.message.reply_text(
        "🏠 **Ближайшее укрытие**\n\n"
        "Для поиска ближайших убежищ отправьте вашу геолокацию или пропустите этот шаг.",
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )

# Обработчик геолокации для убежищ
async def handle_shelter_location(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    
    if user_id not in user_states or user_states[user_id]['state'] != 'shelter_location':
        return
    
    # Кэшируем координаты пользователя
    if update.message.location:
        user_states[user_id]['data']['user_lat'] = update.message.location.latitude
        user_states[user_id]['data']['user_lon'] = update.message.location.longitude
        logger.info(f"Геолокация пользователя {user_id}: {update.message.location.latitude}, {update.message.location.longitude}")
    
    # Показываем убежища
    await show_shelters(update, context)

# Показать список убежищ
async def show_shelters(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    
    # Загружаем данные убежищ
    data = load_placeholder_data()
    shelters = data.get('shelters', [])
    
    if not shelters:
        await update.message.reply_text(
            "❌ Информация об убежищах временно недоступна.",
            reply_markup=ReplyKeyboardMarkup([['⬅️ Главное меню']], resize_keyboard=True)
        )
        return
    
    # Показываем первые 3 убежища
    for i, shelter in enumerate(shelters[:3], 1):
        text = f"🏠 **{shelter['name']}**\n\n"
        text += f"{shelter['description']}\n\n"
        text += f"📍 Координаты: {shelter['lat']}, {shelter['lon']}"
        
        keyboard = [
            ['🔍 Показать на карте', '🌐 Открыть в Яндекс.Картах'],
            ['⬅️ Главное меню']
        ]
        reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
        
        # Отправляем изображение убежища (заглушка)
        try:
            with open(shelter['photo_path'], 'rb') as photo:
                await update.message.reply_photo(
                    photo=photo,
                    caption=text,
                    reply_markup=reply_markup,
                    parse_mode='Markdown'
                )
        except FileNotFoundError:
            # Если файл не найден, отправляем только текст
            await update.message.reply_text(
                text,
                reply_markup=reply_markup,
                parse_mode='Markdown'
            )
    
    # Очищаем состояние
    if user_id in user_states:
        del user_states[user_id]

# Обработчик кнопок убежищ
async def handle_shelter_actions(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    
    if text == "🔍 Показать на карте":
        await update.message.reply_text(
            "📍 **Местоположение убежища**\n\n"
            "Координаты: 55.7558, 37.6176 (заглушка)\n"
            "В реальной версии здесь будет отправлена геолокация убежища.",
            reply_markup=ReplyKeyboardMarkup([['⬅️ Главное меню']], resize_keyboard=True)
        )
    elif text == "🌐 Открыть в Яндекс.Картах":
        await update.message.reply_text(
            "🌐 **Ссылка на Яндекс.Карты**\n\n"
            "https://yandex.ru/maps/?pt=37.6176,55.7558&z=16&l=map\n"
            "В реальной версии здесь будет ссылка на конкретное убежище.",
            reply_markup=ReplyKeyboardMarkup([['⬅️ Главное меню']], resize_keyboard=True)
        )

# Обработчик геолокации
async def handle_location(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    
    # Проверяем, находится ли пользователь в состоянии ожидания геолокации для убежищ
    if user_id in user_states and user_states[user_id]['state'] == 'shelter_location':
        await handle_shelter_location(update, context)
    else:
        await update.message.reply_text(
            "Пожалуйста, выберите функцию из главного меню.",
            reply_markup=get_main_menu()
        )

# Обработчик "Консультант по безопасности РПРЗ"
async def handle_safety_consultant(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user = update.effective_user
    
    # Логируем активность
    log_activity(user_id, user.username, "safety_consultant_started")
    
    # Инициализируем состояние пользователя
    user_states[user_id] = {
        'state': 'consultant_menu',
        'data': {}
    }
    
    keyboard = [
        ['📄 Список документов'],
        ['❓ Задать вопрос'],
        ['⬅️ Назад']
    ]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    
    await update.message.reply_text(
        "🧑‍🏫 **Консультант по безопасности РПРЗ**\n\n"
        "Выберите нужную функцию:",
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )

# Обработчик списка документов
async def handle_documents_list(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    
    if user_id not in user_states or user_states[user_id]['state'] != 'consultant_menu':
        return
    
    # Загружаем данные документов
    data = load_placeholder_data()
    documents = data.get('documents', [])
    
    if not documents:
        await update.message.reply_text(
            "❌ Документы временно недоступны.",
            reply_markup=ReplyKeyboardMarkup([['⬅️ Назад']], resize_keyboard=True)
        )
        return
    
    # Показываем список документов
    text = "📄 **Список документов**\n\n"
    for i, doc in enumerate(documents, 1):
        text += f"{i}. **{doc['title']}**\n"
        text += f"   {doc['description']}\n\n"
    
    keyboard = []
    for i, doc in enumerate(documents, 1):
        keyboard.append([f"📄 Открыть документ {i}"])
    keyboard.append(['⬅️ Назад'])
    
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    
    await update.message.reply_text(
        text,
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )

# Обработчик открытия документа
async def handle_open_document(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    
    if not text.startswith("📄 Открыть документ "):
        return
    
    try:
        doc_num = int(text.split()[-1]) - 1
        data = load_placeholder_data()
        documents = data.get('documents', [])
        
        if 0 <= doc_num < len(documents):
            doc = documents[doc_num]
            
            # Отправляем PDF файл
            try:
                with open(doc['file_path'], 'rb') as pdf_file:
                    await update.message.reply_document(
                        document=pdf_file,
                        filename=f"{doc['title']}.pdf",
                        caption=f"📄 **{doc['title']}**\n\n{doc['description']}"
                    )
            except FileNotFoundError:
                await update.message.reply_text(
                    f"❌ Файл документа '{doc['title']}' не найден.",
                    reply_markup=ReplyKeyboardMarkup([['⬅️ Назад']], resize_keyboard=True)
                )
        else:
            await update.message.reply_text(
                "❌ Документ не найден.",
                reply_markup=ReplyKeyboardMarkup([['⬅️ Назад']], resize_keyboard=True)
            )
    except (ValueError, IndexError):
        await update.message.reply_text(
            "❌ Неверный номер документа.",
            reply_markup=ReplyKeyboardMarkup([['⬅️ Назад']], resize_keyboard=True)
        )

# Обработчик "Задать вопрос"
async def handle_ask_question(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    
    if user_id not in user_states or user_states[user_id]['state'] != 'consultant_menu':
        return
    
    user_states[user_id]['state'] = 'waiting_question'
    
    keyboard = [['⬅️ Назад']]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    
    await update.message.reply_text(
        "❓ **Задать вопрос**\n\n"
        "Опишите ваш вопрос по безопасности труда. Будьте максимально конкретны:\n"
        "• В чем именно нужна помощь?\n"
        "• Какая ситуация возникла?\n"
        "• Какие документы или процедуры вас интересуют?",
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )

# Обработчик ответа на вопрос
async def handle_question_response(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    
    if user_id not in user_states or user_states[user_id]['state'] != 'waiting_question':
        return
    
    question = update.message.text
    user_states[user_id]['data']['question'] = question
    user_states[user_id]['state'] = 'question_answered'
    
    # Логируем активность
    log_activity(user_id, update.effective_user.username, "question_asked", question[:50])
    
    # Загружаем шаблоны ответов
    data = load_placeholder_data()
    responses = data.get('suggestions_responses', {})
    
    # Формируем ответ
    answer_text = f"❓ **Ваш вопрос:** {question}\n\n"
    answer_text += f"💡 **Ответ:** {responses.get('default_answer', 'Заглушка-ответ по вашему вопросу.')}\n\n"
    answer_text += f"📚 **Источник:** {responses.get('default_source', 'Документ №X, стр. Y, п. Z (заглушка).')}"
    
    keyboard = [
        ['📖 Подробнее'],
        ['📄 Открыть PDF'],
        ['❓ Задать другой вопрос'],
        ['⬅️ Назад']
    ]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    
    await update.message.reply_text(
        answer_text,
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )

# Обработчик кнопки "Подробнее"
async def handle_detailed_answer(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    
    if user_id not in user_states or user_states[user_id]['state'] != 'question_answered':
        return
    
    # Загружаем детальные ответы
    data = load_placeholder_data()
    responses = data.get('suggestions_responses', {})
    detailed = responses.get('detailed_responses', {})
    
    # Выбираем подходящий детальный ответ (заглушка)
    detailed_text = detailed.get('safety', 'Подробная информация по безопасности не найдена.')
    
    keyboard = [
        ['📄 Открыть PDF'],
        ['❓ Задать другой вопрос'],
        ['⬅️ Назад']
    ]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    
    await update.message.reply_text(
        f"📖 **Подробная информация**\n\n{detailed_text}",
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )

# Обработчик кнопки "Открыть PDF"
async def handle_open_question_pdf(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    
    if user_id not in user_states or user_states[user_id]['state'] != 'question_answered':
        return
    
    # Отправляем заглушку PDF
    try:
        with open('assets/pdfs/dummy.pdf', 'rb') as pdf_file:
            await update.message.reply_document(
                document=pdf_file,
                filename="Документ_по_безопасности.pdf",
                caption="📄 **Документ по безопасности**\n\nСправочный материал по вашему вопросу."
            )
    except FileNotFoundError:
        await update.message.reply_text(
            "❌ Документ временно недоступен.",
            reply_markup=ReplyKeyboardMarkup([['⬅️ Назад']], resize_keyboard=True)
        )

# Обработчик "Задать другой вопрос"
async def handle_another_question(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    
    if user_id not in user_states:
        return
    
    user_states[user_id]['state'] = 'waiting_question'
    
    keyboard = [['⬅️ Назад']]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    
    await update.message.reply_text(
        "❓ **Задать другой вопрос**\n\n"
        "Опишите ваш новый вопрос по безопасности труда:",
        reply_markup=reply_markup,
        parse_mode='Markdown'
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
    application.add_handler(CommandHandler("my_history", my_history))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    application.add_handler(MessageHandler(filters.PHOTO | filters.VIDEO, handle_media))
    application.add_handler(MessageHandler(filters.LOCATION, handle_location))
    
    # Запускаем бота
    logger.info("Запуск бота...")
    application.run_polling()

if __name__ == '__main__':
    main()
