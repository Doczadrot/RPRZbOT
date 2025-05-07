import telebot  # Импортируем библиотеку для работы с Telegram-ботом
from telebot import types  # Импортируем типы для создания кнопок и клавиатур
import sqlite3  # Модуль для работы с базой данных SQLite (хранение актов)
import json  # Для сериализации/десериализации списков фото
import os  # Для работы с файловой системой (создание папок, сохранение фото)
from telebot.handler_backends import State, StatesGroup  # для определения состояний пользователя
from telebot.storage import StateMemoryStorage # для того что бы бот запоминал состояние пользователя

# === ШАГ 1: Создание экземпляра бота ===
state_storage = StateMemoryStorage() #Память состояний -  что бы бот запоминал состояние пользователя

bot = telebot.TeleBot('7729467094:AAE45THQpWdxcf_kITJ_z6ct4cKkZFNz0IQ', state_storage = state_storage)  # Создаём объект бота с токеном (токен — ключ для управления ботом)


# === ШАГ 2: Глобальные переменные для хранения состояния ===
user_act_number = {}   # chat_id -> номер акта (чтобы знать, какой акт сейчас регистрирует пользователь)
bot_status = {}  # chat_id -> текущее состояние пользователя (например, "ожидание фото")
user_photos = {}  # chat_id -> список путей к фото (чтобы не потерять фото до сохранения)
user_history = {}  # chat_id -> история действий пользователя (для кнопки "Назад")
bot_status_state = {}  # chat_id -> состояние меню (например, 'main_menu')



class BotStates(StatesGroup):
    main_menu = State() ## Состояние: Пользователь находится в главном меню
    menu_act = State()
    act_number = State()

# === ШАГ 3: Клавиатуры для удобства пользователя ===
back_markup = types.ReplyKeyboardMarkup(resize_keyboard=True)  # Клавиатура с одной кнопкой "Назад"
btn_back = types.KeyboardButton("Назад") # Кнопка "Назад"
back_markup.add(btn_back)  # Добавляем кнопку в клавиатуру add - добавить

photo_choice_markup = types.ReplyKeyboardMarkup(resize_keyboard=True)  # Клавиатура для выбора: добавить фото или сохранить акт
btn_photo = types.KeyboardButton("📷Добавить фото") #Кнопка "📷Добавить фото"
btn_save_act = types.KeyboardButton("✅Сохранить акт")
photo_choice_markup.add(btn_photo, btn_save_act)
photo_choice_markup.add(btn_back)

# === ШАГ 4: Инициализация базы данных ===
def init_db(): #инициализация базы данных
    """Создаёт таблицу для хранения актов, если её ещё нет."""
    conn = sqlite3.connect('acts.db') # Подключаемся к базе данных
    cursor = conn.cursor() # Создаём курсор для выполнения SQL-запросов
    # Создаём таблицу для хранения актов
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS acts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            chat_id INTEGER,
            act_number TEXT UNIQUE,
            photo_urls TEXT 
        )
    ''')
    conn.commit() # Сохраняем изменения
    conn.close()# Закрываем соединение


init_db()  # Запускаем инициализацию при старте скрипта

# === ШАГ 5: Главное меню — команда /start ===
@bot.message_handler(commands=['start']) # Обработчик команды /start
def start(message): # Обработчик команды /start
    chat_id = message.chat.id  # Получаем ID чата
    # Формируем главное меню с кнопками для пользователя
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)  # Клавиатура для выбора
    markup.add(
        types.KeyboardButton("📝Рег. несоответствия"),
        types.KeyboardButton("📊Акты о браке"),
        types.KeyboardButton("📋Поиск"),
        types.KeyboardButton("🤖Нейропомощник РПРЗ"),
    )
    # bot_status_state[chat_id] = 'main_menu'  # Сохраняем состояние меню
    """Устанавливаем состояние пользователя"""
    # bot.set.state - устанавливает текущее состояние бота для пользователя
    # BotStates.main_menu - это состояние, которое мы создали в стартовом скрипте
    # chat_id - это ID чата, для которого мы хотим установить состояние
    bot.set.state(chat_id, BotStates.main_menu)  # Устанавливаем состояние

    #user - пользователь
    # chat_id - id чата (взаимодействие с кок)
    #get_state - получает текущее состояние бота для пользователя
    print(f'user{chat_id} в главном меню{bot.get_state(chat_id)}') # Выводим в консоль для отладки

    user_history[chat_id] = []  # Очищаем историю действий пользователя


    #При первом входе отправляем это сообщение пользователю
    bot.send_message(
        chat_id,
        "👋 Привет! Это информационный бот завода РПРЗ для учета несоответствий.\n"
        "Используйте кнопки меню. Для справки — /help",
        reply_markup=markup
    ) #reply_markup=markup - отправляем клавиатуру пользователю

# === ШАГ 6: Обработка текстовых сообщений (логика меню) ===
# Прописываем все кнорки, которые будут в меню
@bot.message_handler(content_types=['text']) # Обработчик текстовых сообщений

def handle_text(message): # функция для обработки текстовых сообщений
    chat_id = message.chat.id  # Получаем ID чата
    user_history.setdefault(chat_id, [])  # Если истории нет — создаём пустую
    text = message.text  # Текст сообщения пользователя

    #если пользователь нажал на кнопку рег. несоответствия
    if text == '📝Рег. несоответствия':
        user_history[chat_id].append('menu_act')  # Добавляем в историю (Append - добавляет элемент в конец списка)
        #Бот ему отвечает Введите номер акта о браке (1–4 цифры) и кнопку назад - reply_markup=back_markup
        bot.send_message(chat_id, 'Введите номер акта о браке (1–4 цифры):', reply_markup=back_markup)

        #Прописываем следующий шаг, который ожидает ввод номера акта
        bot.register_next_step_handler(message, process_act_number)  # Ждём ввода номера акта
    elif text == '📊Акты о браке':
        view_acts(message)  # Показываем список актов
    elif text == '📋Поиск':
        bot.send_message(chat_id, 'Эта функция в разработке')  # Заглушка
    elif text == '🤖Нейропомощник РПРЗ':
        bot.send_message(chat_id, 'Эта функция в разработке')  # Заглушка
    elif text == '✅Сохранить акт':
        # Проверяем, что пользователь загрузил хотя бы одно фото
        if bot_status.get(chat_id) == 'ожидание фото' and user_photos.get(chat_id):
            success = save_to_db(chat_id)
            # Если 
            if success:
                bot.send_message(chat_id, '✅ Акт сохранён. Возвращаюсь в главное меню.',
                                 reply_markup=types.ReplyKeyboardRemove())
                start(message)
            else:
                bot.send_message(chat_id, '❌ Не удалось сохранить. Попробуйте ещё раз или измените фото.',
                                 reply_markup=photo_choice_markup)
        else:
            bot.send_message(chat_id, 'Вы ещё не загрузили фото. Пожалуйста, загрузите хотя бы одно фото.',
                             reply_markup=photo_choice_markup)
    elif text == 'Назад':
        if user_history[chat_id]:
            user_history[chat_id].pop()  # Удаляем последний шаг из истории
        start(message)  # Возвращаемся в главное меню
    else:
        bot.send_message(chat_id, 'Выберите вариант из меню')  # Сообщение по умолчанию

# === ШАГ 7: Ввод номера акта (валидация и переход к загрузке фото) ===
def process_act_number(message):
    chat_id = message.chat.id
    text = message.text
    if text == 'Назад':
        start(message)
        return
    if text.isdigit() and 1 <= len(text) <= 4:
        # Проверяем, что такого номера ещё нет среди введённых
        if text in user_act_number.values():
            bot.send_message(chat_id, 'Этот номер уже вводился. Введите другой:', reply_markup=back_markup)
            bot.register_next_step_handler(message, process_act_number)
            return
        user_act_number[chat_id] = text  # Сохраняем номер акта
        bot_status[chat_id] = 'ожидание фото'  # Ставим статус ожидания фото
        user_photos[chat_id] = []  # Готовим список для фото
        bot.send_message(
            chat_id,
            f'Номер акта {text} зарегистрирован. Жду 1–3 фото.',
            reply_markup=photo_choice_markup
        )
    else:
        bot.send_message(chat_id, 'Некорректный номер. Введите 1–4 цифры:', reply_markup=back_markup)
        bot.register_next_step_handler(message, process_act_number)

# === ШАГ 8: Приём и сохранение фото (локально) ===
@bot.message_handler(content_types=['photo'])
def handle_photo(message):
    chat_id = message.chat.id
    if bot_status.get(chat_id) != 'ожидание фото':
        bot.send_message(chat_id, 'Сначала начните регистрацию акта (/start).')
        return
    try:
        # Получаем file_id последнего фото
        file_id = message.photo[-1].file_id
        file_info = bot.get_file(file_id)
        downloaded = bot.download_file(file_info.file_path)
        # Создаём папку для фото пользователя
        folder = f"photos/{chat_id}"
        os.makedirs(folder, exist_ok=True)
        # Формируем имя файла
        act_number = user_act_number.get(chat_id, 'unknown')
        count = len(user_photos[chat_id]) + 1
        filename = f"{folder}/act_{act_number}_{count}.jpg"
        # Сохраняем фото на диск
        with open(filename, 'wb') as f:
            f.write(downloaded)
        # Добавляем путь к фото в список
        user_photos[chat_id].append(filename)
        # Считаем, сколько фото уже загружено
        uploaded = len(user_photos[chat_id])
        remaining = 3 - uploaded
        if uploaded < 3:
            bot.send_message(
                chat_id,
                f'Фото {uploaded} принято ✅. Можно добавить ещё {remaining} или сохранить акт.',
                reply_markup=photo_choice_markup
            )
        else:
            bot.send_message(chat_id, '✅ Загружено 3 фото. Сохраняю акт...', reply_markup=types.ReplyKeyboardRemove())
            save_to_db(chat_id)
            start(message)
    except Exception as e:
        print(f"Ошибка в handle_photo: {e}")
        bot.send_message(chat_id, 'Что-то пошло не так при загрузке фото.', reply_markup=back_markup)

# === ШАГ 9: Сохранение данных в базу ===
def save_to_db(chat_id):
    """Сохраняет акт и фото в базу данных. Возвращает True/False."""
    act_number = user_act_number.get(chat_id)
    if not act_number:
        print(f"Номер акта не найден для {chat_id}")
        return False
    photos = user_photos.get(chat_id, [])
    if not photos:
        print(f"Нет фото для акта {act_number}")
        return False
    try:
        conn = sqlite3.connect('acts.db')
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO acts (chat_id, act_number, photo_urls) VALUES (?, ?, ?)",
            (chat_id, act_number, json.dumps(photos))
        )
        conn.commit()
        print(f"Акт {act_number} сохранён.")
        return True
    except sqlite3.IntegrityError:
        bot.send_message(chat_id, f"❌ Акт {act_number} уже существует.")
        return False
    except Exception as e:
        print(f"Ошибка save_to_db: {e}")
        bot.send_message(chat_id, "❌ Ошибка при сохранении акта.")
        return False
    finally:
        if 'conn' in locals():
            conn.close()
        user_act_number.pop(chat_id, None)
        user_photos.pop(chat_id, None)
        bot_status.pop(chat_id, None)

# === ШАГ 10: Просмотр актов пользователя ===
@bot.message_handler(commands=['view_acts'])
def view_acts(message):
    chat_id = message.chat.id
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    conn = sqlite3.connect('acts.db')
    cursor = conn.cursor()
    cursor.execute("SELECT act_number FROM acts WHERE chat_id = ?", (chat_id,))
    acts = cursor.fetchall()
    conn.close()
    if not acts:
        bot.send_message(chat_id, "У вас пока нет сохранённых актов.", reply_markup=back_markup)
        return
    for (act_num,) in acts:
        markup.add(types.KeyboardButton(act_num))
    markup.add(btn_back)
    bot.send_message(chat_id, "Выберите номер акта:", reply_markup=markup)
    bot.register_next_step_handler(message, act_photos)

# === ШАГ 11: Отправка фото по выбранному акту ===
def act_photos(message):
    chat_id = message.chat.id
    act_number = message.text
    if act_number == 'Назад':
        start(message)
        return
    try:
        conn = sqlite3.connect('acts.db')
        cursor = conn.cursor()
        cursor.execute(
            "SELECT photo_urls FROM acts WHERE chat_id = ? AND act_number = ?",
            (chat_id, act_number)
        )
        row = cursor.fetchone()
        conn.close()
        if not row:
            bot.send_message(chat_id, "Акт не найден.", reply_markup=back_markup)
            return view_acts(message)
        photo_paths = json.loads(row[0])
        if not photo_paths:
            bot.send_message(chat_id, f"Нет фото для акта №{act_number}.", reply_markup=back_markup)
            return view_acts(message)
        bot.send_message(chat_id, f"Фотографии для акта №{act_number}:")
        sent = 0
        for path in photo_paths:
            try:
                with open(path, 'rb') as ph:
                    bot.send_photo(chat_id, ph)
                    sent += 1
            except FileNotFoundError:
                bot.send_message(chat_id, f"Не найден файл: {os.path.basename(path)}")
        bot.send_message(chat_id, f"Отправлено {sent} фото.", reply_markup=types.ReplyKeyboardRemove())
        start(message)
    except Exception as e:
        print(f"Ошибка в act_photos: {e}")
        bot.send_message(chat_id, "❌ Ошибка при показе фото.", reply_markup=back_markup)
        bot.register_next_step_handler(message, view_acts)

# === ШАГ 12: Справка по команде /help ===
@bot.message_handler(commands=['help'])
def send_help(message):
    chat_id = message.chat.id
    help_text = (
        "🤖 Справка по боту РПРЗ 🤖\n\n"
        "📝Рег. несоответствия — начать регистрацию акта.\n"
        "📊Акты о браке       — посмотреть сохранённые акты.\n"
        "📋Поиск             — в разработке.\n"
        "🤖Нейропомощник РПРЗ — в разработке.\n"
        "Назад               — вернуться назад.\n"
        "/help               — эта справка.\n"
    )
    bot.send_message(chat_id, help_text, reply_markup=None)
    start(message)

# === ШАГ 13: Запуск бота (основной цикл) ===
bot.polling(non_stop=True)  # Бот начинает слушать сообщения и реагировать на них
