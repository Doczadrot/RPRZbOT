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
    user_id = user.id
    
    logger.info(f"Пользователь {user_id} отправил сообщение: {text}")
    
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
    application.add_handler(MessageHandler(filters.PHOTO | filters.VIDEO, handle_media))
    application.add_handler(MessageHandler(filters.LOCATION, handle_location))
    
    # Запускаем бота
    logger.info("Запуск бота...")
    application.run_polling()

if __name__ == '__main__':
    main()
