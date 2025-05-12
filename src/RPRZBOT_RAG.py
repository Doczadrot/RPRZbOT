import telebot  # Импортируем библиотеку для работы с Telegram-ботом
from telebot import types  # Импортируем типы для создания кнопок и клавиатур
import sqlite3  # Модуль для работы с базой данных SQLite (хранение актов)
import json  # Для сериализации/десериализации списков фото
import os  # Для работы с файловой системой (создание папок, сохранение фото)
from telebot.handler_backends import State, StatesGroup  # для определения состояний пользователя
from telebot.storage import StateMemoryStorage # для того что бы бот запоминал состояние пользователя
from loguru import logger  # Импортируем logger

rag_db = None  # Глобальная переменная для RAG базы данных. Используется для хранения экземпляра векторной базы данных.
from dotenv import load_dotenv # Для загрузки переменных окружения из файла .env


# ✅ ИМПОРТИРУЕМ НАШ МОДУЛЬ С ЛОГИКОЙ RAG
# Убедитесь, что файл rag_service.py находится в той же папке или доступен по пути
try:
    import rag_service # ✅ Импорт модуля rag_service.py
    logger.info("Модуль rag_service загружен.")
except ImportError:
    logger.error("Ошибка: Модуль rag_service.py не найден! Функционал Нейропомощника будет недоступен.")
    rag_service = None # Устанавливаем None, если модуль не найден


# --- Настройка логирования для бота ---
# Убедитесь, что папка 'log' существует или создайте ее вручную
os.makedirs('log', exist_ok=True)
logger.add("log/bot.log", format="{time} {level} {message}", level="DEBUG", rotation="1 MB", compression="zip")
logger.info("Бот RPRZBot запущен.") # Лог при запуске скрипта бота


# --- Загрузка переменных окружения ---
load_dotenv() # ✅ Загружаем переменные окружения из файла .env

# Получаем токен бота из .env
BOT_TOKEN = os.getenv('BOT_TOKEN') # ✅ Берем токен из .env
if not BOT_TOKEN:
    logger.error("Ошибка: Токен бота не найден в файле .env! Переменная BOT_TOKEN не установлена.")
    # ✅ В реальном приложении здесь лучше sys.exit(1) или raise Exception
    exit() # Остановка скрипта, если токен не найден

# Получаем список админов из .env (пока не используется, но оставим)
ADMIN_USER_IDS_STR = os.getenv('ADMIN_USER_IDS', '')
ADMIN_USER_IDS = [int(uid.strip()) for uid in ADMIN_USER_IDS_STR.split(',') if uid.strip().isdigit()] if ADMIN_USER_IDS_STR else []
if not ADMIN_USER_IDS:
    logger.warning("Список ADMIN_USER_IDS пуст или некорректен в файле .env! Некоторые команды могут быть недоступны.")
else:
    logger.debug(f"Загружены ID администраторов: {ADMIN_USER_IDS}")


# === ШАГ 1: Создание экземпляра бота ===
state_storage = StateMemoryStorage() #Память состояний -  что бы бот запоминал состояние пользователя

bot = telebot.TeleBot(BOT_TOKEN, state_storage = state_storage)  # ИЗМЕНЕНО: Используем BOT_TOKEN из .env


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
    # ✅ Добавлено состояние для RAG, если нужно управлять им через StatesGroup
    # rag_query = State()


# === ШАГ 3: Клавиатуры для удобства пользователя ===
back_markup = types.ReplyKeyboardMarkup(resize_keyboard=True) # Клавиатура с одной кнопкой "Назад"
btn_back = types.KeyboardButton("Назад") # Кнопка "Назад"
back_markup.add(btn_back) # Добавляем кнопку в клавиатуру add - добавить

photo_choice_markup = types.ReplyKeyboardMarkup(resize_keyboard=True) # Клавиатура для выбора: добавить фото или сохранить акт
btn_photo = types.KeyboardButton("📷Добавить фото") #Кнопка "📷Добавить фото"
btn_save_act = types.KeyboardButton("✅Сохранить акт")
photo_choice_markup.add(btn_photo, btn_save_act)
photo_choice_markup.add(btn_back)

# ✅ Клавиатура главного меню (ваш существующий код)
main_menu_keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)
main_menu_keyboard.add(
    types.KeyboardButton("📝Рег. несоответствия"),
    types.KeyboardButton("📊Акты о браке"),
    types.KeyboardButton("📋Поиск"),
    types.KeyboardButton("🤖Нейропомощник РПРЗ"), # ✅ Кнопка для Нейропомощника
)


# === ШАГ 4: Инициализация базы данных ===
def init_db(): #инициализация базы данных
    """Создаёт таблицу для хранения актов, если её ещё нет."""
    conn = None # Инициализация conn = None для блока finally
    try:
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
        logger.info("База данных SQLite 'acts.db' инициализирована.")
    except Exception as e:
        # ✅ Логируем ошибку инициализации базы данных
        logger.error(f"Ошибка инициализации базы данных SQLite: {e}", exc_info=True)
        # В случае ошибки инициализации, возможно, стоит выйти или уведомить пользователя.
        # Но для простоты пока просто логируем.
    finally:
        if conn:
            conn.close()


init_db() # Запускаем инициализацию при старте скрипта


# === ШАГ 5: Главное меню — команда /start ===
@bot.message_handler(commands=['start']) # Обработчик команды /start
def start(message): # Обработчик команды /start
    chat_id = message.chat.id # Получаем ID чата
    logger.info(f"Получена команда /start от пользователя {chat_id}")

    # ✅ Сбрасываем ожидающие обработчики next_step_handler для этого пользователя
    bot.clear_step_handler(message.chat.id)

    # Формируем главное меню с кнопками для пользователя
    # ✅ Используем предопределенную клавиатуру main_menu_keyboard
    markup = main_menu_keyboard

    # bot_status_state[chat_id] = 'main_menu' # Сохраняем состояние меню
    """Устанавливаем состояние пользователя"""
    # bot.set.state - устанавливает текущее состояние бота для пользователя
    # BotStates.main_menu - это состояние, которое мы создали в стартовом скрипте
    # chat_id - это ID чата, для которого мы хотим установить состояние
    bot.set_state(chat_id, BotStates.main_menu) # Устанавливаем состояние

    #user - пользователь
    # chat_id - id чата (взаимодействие с кок)
    logger.debug(f'user{chat_id} в главном меню{bot.get_state(chat_id)}') # Выводим в консоль для отладки

    user_history.setdefault(chat_id, []) # ✅ Инициализируем историю, если ее нет
    user_history[chat_id] = [] # Очищаем историю действий пользователя при старте


    #При первом входе отправляем это сообщение пользователю
    bot.send_message(
        chat_id,
        "👋 Привет! Это информационный бот завода РПРЗ для учета несоответствий.\n"
        "Я также могу ответить на ваши вопросы по внутренней документации, использую базу знаний Нейропомощника.\n\n" # ✅ Добавлено описание RAG
        "Используйте кнопки меню. Для справки — /help",
        reply_markup=markup
    ) #reply_markup=markup - отправляем клавиатуру пользователю


# ✅ НОВЫЙ ОБРАБОТЧИК ДЛЯ КНОПКИ "🤖Нейропомощник РПРЗ"
# Срабатывает, когда пользователь нажимает кнопку с текстом "🤖Нейропомощник РПРЗ"
# ✅ Используем handler для текста кнопки И проверяем состояние
@bot.message_handler(state=BotStates.main_menu, func=lambda message: message.text == "🤖Нейропомощник РПРЗ")
def ask_rag_question_prompt(message):
    chat_id = message.chat.id
    logger.info(f"Пользователь {chat_id} нажал кнопку 'Нейропомощник РПРЗ'.")

    # ✅ Добавляем шаг в историю
    user_history[chat_id].append('ask_rag')

    global rag_db # Объявляем, что используем глобальную переменную rag_db
    if rag_db is None:
        logger.error(f"База знаний RAG недоступна для пользователя {chat_id}. Отправляем сообщение об ошибке.")
        bot.send_message(chat_id, "❌ Извините, база знаний Нейропомощника сейчас недоступна. Пожалуйста, попробуйте позже.", reply_markup=main_menu_keyboard) # ✅ Возвращаем главное меню
        bot.clear_step_handler(message.chat.id)
        # ✅ Убираем шаг из истории, так как не перешли в RAG диалог
        if user_history.get(chat_id): user_history[chat_id].pop()
        return # Прерываем выполнение обработчика

    msg = bot.send_message(chat_id, "✍️ Отлично! Введите ваш вопрос по документации:", reply_markup=back_markup)

    # ✅ Регистрируем следующий шаг: ожидаем текстовое сообщение с вопросом пользователя
    logger.debug(f"Регистрируем next_step_handler для process_rag_query для пользователя {chat_id}")
    bot.register_next_step_handler(msg, process_rag_query)
    # ✅ Устанавливаем состояние ожидания RAG запроса, если нужно
    # bot.set_state(chat_id, BotStates.rag_query)


# ✅ ФУНКЦИЯ ДЛЯ ОБРАБОТКИ ВОПРОСА ПОЛЬЗОВАТЕЛЯ И ВЫЗОВА RAG
# Вызывается через register_next_step_handler после ask_rag_question_prompt
def process_rag_query(message):
    chat_id = message.chat.id
    user_question = message.text

    logger.info(f"Получен вопрос пользователя {chat_id} для RAG: \"{user_question}\"")

    # ✅ Обработка кнопки "Назад" на этом шаге - УПРОЩЕНО
    if user_question == "Назад":
        logger.debug(f"Пользователь {chat_id} нажал 'Назад' во время ввода вопроса для RAG.")
        bot.clear_step_handler(message.chat.id) # Очищаем ожидающий обработчик
        # ✅ Удаляем последний шаг из истории
        if user_history.get(chat_id): user_history[chat_id].pop()
        # ✅ Возвращаемся в главное меню, вызывая start
        start(message)
        return # Прерываем выполнение

    global rag_db
    if rag_db is None:
        logger.error(f"База знаний RAG стала недоступна во время обработки запроса от {chat_id}.")
        bot.send_message(chat_id, "❌ Извините, база знаний Нейропомощника сейчас недоступна. Пожалуйста, попробуйте позже.", reply_markup=main_menu_keyboard)
        bot.clear_step_handler(message.chat.id)
        # ✅ Удаляем последний шаг из истории
        if user_history.get(chat_id): user_history[chat_id].pop()
        # ✅ Возвращаемся в главное меню, вызывая start
        start(message)
        return

    bot.send_message(chat_id, "⏳ Ищу ответ в базе знаний...")
    logger.debug(f"Передаем запрос пользователя {chat_id} в RAG пайплайн.")

    try:
        rag_response = rag_service.process_user_query_with_rag(user_question, rag_db)

        logger.info(f"Получен ответ от RAG для пользователя {chat_id}.")

        bot.send_message(chat_id, rag_response, reply_markup=main_menu_keyboard)

    except Exception as e:
        logger.error(f"Критическая ошибка при обработке RAG запроса от {chat_id}: {e}", exc_info=True)
        bot.send_message(chat_id, "❌ Произошла внутренняя ошибка при обработке вашего запроса.", reply_markup=main_menu_keyboard)

    finally:
        # ✅ После получения ответа или ошибки, сбрасываем ожидающие обработчики
        bot.clear_step_handler(message.chat.id)
        logger.debug(f"Cleared next_step_handler for user {chat_id} after RAG query processing.")
        # ✅ Возвращаемся в главное меню после обработки запроса, вызывая start
        # Если бот не упал, это должно быть безопасно.
        start(message)


# === ШАГ 6: Обработка текстовых сообщений (логика меню) ===
# Прописываем все кнорки, которые будут в меню
# ✅ Добавлен фильтр по состоянию main_menu
@bot.message_handler(state=BotStates.main_menu, content_types=['text']) # Обработчик текстовых сообщений

def handle_text(message): # функция для обработки текстовых сообщений
    chat_id = message.chat.id # Получаем ID чата
    user_history.setdefault(chat_id, []) # Если истории нет — создаём пустую
    text = message.text # Текст сообщения пользователя

    logger.debug(f"Получено текстовое сообщение от {chat_id} в состоянии main_menu: \"{text}\". Проверка в handle_text.")


    #если пользователь нажал на кнопку рег. несоответствия
    if text == '📝Рег. несоответствия':
        user_history[chat_id].append('menu_act') # Добавляем в историю (Append - добавляет элемент в конец списка)
        #Бот ему отвечает Введите номер акта о браке (1–4 цифры) и кнопку назад - reply_markup=back_markup
        msg = bot.send_message(chat_id, '🎮 Шаг 1/3: Введите номер акта (от 1 до 4 цифр)\nМожно вернуться назад ↩️', reply_markup=back_markup)

        #Прописываем следующий шаг, который ожидает ввод номера акта
        bot.register_next_step_handler(msg, process_act_number) # Ждём ввода номера акта
        # ✅ Устанавливаем состояние ожидания номера акта, если нужно
        # bot.set_state(chat_id, BotStates.act_number)
        logger.debug(f"Регистрируем next_step_handler для process_act_number для пользователя {chat_id}")


    elif text == '📊Акты о браке':
        user_history[chat_id].append('view_acts') # Добавляем в историю
        view_acts(message) # Показываем список актов


    elif text == '📋Поиск':
        bot.send_message(chat_id, 'Эта функция в разработке', reply_markup=main_menu_keyboard) # Заглушка


    # ✅ Кнопка Нейропомощника обрабатывается отдельным @bot.message_handler func=... выше!
    # Этот elif не нужен, т.к. есть более специфичный handler с проверкой состояния
    # elif text == '🤖Нейропомощник РПРЗ':
    #     bot.send_message(chat_id, 'Эта функция в разработке') # Заглушка


    elif text == '✅Сохранить акт':
        logger.info(f"Пользователь {chat_id} нажал '✅Сохранить акт'.")
        # Проверяем, что пользователь загрузил хотя бы одно фото И находится в правильном "диалоге"
        if bot_status.get(chat_id) == 'ожидание фото' and user_photos.get(chat_id) is not None and user_act_number.get(chat_id) is not None:
            # ✅ Сбрасываем ожидание next_step_handler, если оно было установлено перед загрузкой фото
            bot.clear_step_handler(message.chat.id)
            success = save_to_db(chat_id)
            if success:
                bot.send_message(chat_id, '✅ Акт сохранён. Возвращаюсь в главное меню.',
                                 reply_markup=main_menu_keyboard) # ✅ Возвращаем главное меню
                # ✅ Возвращаемся в главное меню
                start(message)
            else:
                bot.send_message(chat_id, '❌ Не удалось сохранить. Попробуйте ещё раз или измените фото.',
                                 reply_markup=photo_choice_markup) # Остаемся на клавиатуре фото выбора
        else:
            # Если кнопка сохранения нажата не в правильном "состоянии"
            logger.warning(f"Пользователь {chat_id} нажал '✅Сохранить акт' не в состоянии ожидания фото (bot_status).")
            bot.send_message(chat_id, 'Сейчас не время для сохранения акта. Выберите действие из меню.', reply_markup=main_menu_keyboard) # ✅ Возвращаем главное меню


    elif text == 'Назад':
        logger.info(f"Пользователь {chat_id} нажал 'Назад' в handle_text.")
        # ✅ Сбрасываем ожидающие обработчики next_step_handler на всякий случай
        bot.clear_step_handler(message.chat.id)
        # ✅ Удаляем последний шаг из истории
        if user_history.get(chat_id): # Проверка, что история существует и не пуста
            user_history[chat_id].pop()

        # ✅ Возвращаемся в главное меню, вызывая start
        start(message)


    else: # Если текст не совпадает ни с одной кнопкой главного меню и нет ожидающего next_step_handler
        logger.debug(f"Получено неопознанное текстовое сообщение от {chat_id} в состоянии main_menu: \"{text}\"")
        bot.send_message(chat_id, 'Неизвестная команда или текст. Выберите действие из меню.', reply_markup=main_menu_keyboard)


# === ШАГ 7: Ввод номера акта (валидация и переход к загрузке фото) ===
# ✅ Этот handler вызывается через register_next_step_handler после нажатия кнопки "📝Рег. несоответствия"
def process_act_number(message):
    chat_id = message.chat.id
    text = message.text

    logger.debug(f"Получен текст для номера акта от {chat_id}: \"{text}\"")

    # ✅ Обработка кнопки "Назад" на этом шаге - УПРОЩЕНО
    if text == 'Назад':
        logger.debug(f"Пользователь {chat_id} нажал 'Назад' во время ввода номера акта.")
        bot.clear_step_handler(message.chat.id) # Очищаем ожидающий обработчик следующего шага
        # ✅ Удаляем последний шаг из истории
        if user_history.get(chat_id): user_history[chat_id].pop()
        # ✅ Возвращаемся в главное меню, вызывая start
        start(message)
        return

    # Валидация номера акта
    if text.isdigit() and 1 <= len(text) <= 4:
        # Проверяем, что такого номера ещё нет в базе данных!
        conn = None
        try:
            conn = sqlite3.connect('acts.db')
            cursor = conn.cursor()
            cursor.execute("SELECT 1 FROM acts WHERE act_number = ?", (text,))
            exists = cursor.fetchone() is not None
            conn.close()
            conn = None
        except Exception as e:
            logger.error(f"Ошибка проверки существования номера акта {text} для пользователя {chat_id}: {e}", exc_info=True)
            if conn: conn.close()
            bot.send_message(chat_id, "❌ Произошла ошибка при проверке номера акта.", reply_markup=back_markup)
            # ✅ Остаемся на этом же шаге, регистрируем handler снова
            bot.register_next_step_handler(message, process_act_number)
            return


        if exists: # Если номер уже есть у пользователя
            logger.warning(f"Номер акта {text} уже существует в базе для пользователя {chat_id}.")
            bot.send_message(chat_id, f'❌ Акт с номером {text} уже существует. Введите другой:', reply_markup=back_markup)
            # ✅ Остаемся на этом же шаге, регистрируем handler снова
            bot.register_next_step_handler(message, process_act_number)
            return

        # Номер акта валиден и не существует в базе у пользователя
        user_act_number[chat_id] = text # Сохраняем номер акта
        bot_status[chat_id] = 'ожидание фото' # Ставим статус ожидания фото (старая логика)
        user_photos[chat_id] = [] # Готовим список для фото

        logger.debug(f"Номер акта {text} принят для пользователя {chat_id}. Ожидание фото.")

        bot.send_message(
            chat_id,
            f'✅ Номер акта {text} зарегистрирован. 📸 Шаг 2/3: Жду 1–3 фото.',
            reply_markup=photo_choice_markup # Переходим на клавиатуру выбора фото/сохранения
        )
        # ✅ Не регистрируем next_step_handler здесь, т.к. ожидаем фото или кнопку Сохранить/Назад,
        # которые будут обработаны handle_photo or handle_text.

    else: # Некорректный формат номера акта
        logger.warning(f"Пользователь {chat_id} ввел некорректный номер акта: \"{text}\"")
        bot.send_message(chat_id, '❌ Некорректный формат номера. Введите 1–4 цифры:', reply_markup=back_markup)
        # ✅ Остаемся на этом же шаге, регистрируем handler снова
        bot.register_next_step_handler(message, process_act_number)


# === ШАГ 8: Приём и сохранение фото (локально) ===
# ✅ Этот handler срабатывает для фото в любом состоянии.
# Проверка bot_status ограничивает его использование для регистрации актов.
@bot.message_handler(content_types=['photo'])
def handle_photo(message):
    chat_id = message.chat.id
    logger.info(f"Получено фото от пользователя {chat_id}. Проверка в handle_photo.")

    # ✅ Проверяем, что пользователь находится в правильном "диалоге"
    if bot_status.get(chat_id) == 'ожидание фото' and user_act_number.get(chat_id) is not None:
        try:
            # Получаем file_id последнего фото
            file_id = message.photo[-1].file_id
            file_info = bot.get_file(file_id)
            downloaded_file = bot.download_file(file_info.file_path) # ✅ Переименована переменная

            # Создаём папку для фото пользователя
            folder = f"photos/{chat_id}"
            os.makedirs(folder, exist_ok=True)
            # Формируем имя файла
            act_number = user_act_number.get(chat_id, 'unknown')
            user_photos.setdefault(chat_id, [])
            count = len(user_photos[chat_id]) + 1
            filename = f"act_{act_number}_{count}.jpg" # ✅ Имя файла с расширением .jpg

            full_filename_path = os.path.join(folder, filename) # ✅ Полный путь к файлу
            user_photos[chat_id].append(full_filename_path) # ✅ Добавляем полный путь в список

            # Сохраняем фото на диск по полному пути
            with open(full_filename_path, 'wb') as f:
                f.write(downloaded_file)

            # Считаем, сколько фото уже загружено
            uploaded = len(user_photos[chat_id])
            remaining = 3 - uploaded

            logger.debug(f"Фото {uploaded}/{3} принято для акта {act_number} от пользователя {chat_id}. Сохранено как {full_filename_path}")

            if uploaded < 3:
                bot.send_message(
                    chat_id,
                    f'Фото {uploaded} принято ✅. Можно добавить ещё {remaining} или сохранить акт.',
                    reply_markup=photo_choice_markup
                )
            else:
                logger.info(f"Пользователь {chat_id} загрузил 3 фото для акта {act_number}. Попытка сохранения.")
                bot.send_message(chat_id, '✅ Загружено 3 фото. Сохраняю акт...', reply_markup=main_menu_keyboard) # ✅ Возвращаем главное меню
                bot.clear_step_handler(message.chat.id)
                save_to_db(chat_id) # Сохраняем в базу
                # ✅ Возвращаемся в главное меню после сохранения
                start(message)


        except Exception as e:
            logger.error(f"Ошибка в handle_photo для пользователя {chat_id}: {e}", exc_info=True)
            bot.send_message(chat_id, 'Что-то пошло не так при загрузке фото.', reply_markup=photo_choice_markup) # Остаемся на клавиатуре фото выбора


    else: # Если фото получено не в состоянии ожидания фото
        logger.warning(f"Получено фото от пользователя {chat_id} не в состоянии ожидания фото.")
        bot.send_message(chat_id, 'Сейчас я не ожидаю фото. Выберите действие из меню.', reply_markup=main_menu_keyboard)


# === ШАГ 9: Сохранение данных в базу ===
def save_to_db(chat_id):
    """Сохраняет акт и фото в базу данных. Возвращает True/False."""
    act_number = user_act_number.get(chat_id)
    # ✅ Проверяем, есть ли вообще данные для сохранения
    if not act_number or chat_id not in user_photos or not user_photos[chat_id]:
        logger.warning(f"Пользователь {chat_id}: Попытка сохранения акта без номера ({act_number}) или фото ({len(user_photos.get(chat_id, [])) if chat_id in user_photos else 'N/A'}).")
        # Сбрасываем состояние, если возможно
        user_act_number.pop(chat_id, None)
        user_photos.pop(chat_id, None)
        bot_status.pop(chat_id, None)
        return False # Нет данных для сохранения


    photos = user_photos[chat_id]

    logger.info(f"Пользователь {chat_id}: Попытка сохранения акта {act_number} с {len(photos)} фото.")

    conn = None
    try:
        conn = sqlite3.connect('acts.db')
        cursor = conn.cursor()
        # Проверяем, существует ли акт с таким номером уже в базе ДЛЯ ЭТОГО chat_id
        cursor.execute("SELECT 1 FROM acts WHERE chat_id = ? AND act_number = ?", (chat_id, act_number))
        exists_for_user = cursor.fetchone() is not None

        if exists_for_user:
            logger.warning(f"Пользователь {chat_id}: Акт {act_number} уже существует в базе ДЛЯ ЭТОГО ПОЛЬЗОВАТЕЛЯ при попытке сохранения.")
            bot.send_message(chat_id, f"❌ Акт с номером {act_number} уже существует у вас.", reply_markup=main_menu_keyboard) # ✅ Возвращаем главное меню
            return False

        cursor.execute(
            "INSERT INTO acts (chat_id, act_number, photo_urls) VALUES (?, ?, ?)",
            (chat_id, act_number, json.dumps(photos))
        )
        conn.commit()
        logger.info(f"Акт {act_number} для пользователя {chat_id} успешно сохранён в acts.db.")

        # ✅ Очистка временных данных после успешного сохранения
        user_act_number.pop(chat_id, None)
        user_photos.pop(chat_id, None)
        bot_status.pop(chat_id, None)

        return True

    except sqlite3.IntegrityError:
        logger.warning(f"Пользователь {chat_id}: Попытка сохранения акта {act_number}, который уже существует (IntegrityError).")
        bot.send_message(chat_id, f"❌ Акт {act_number} уже существует.", reply_markup=main_menu_keyboard) # ✅ Возвращаем главное меню
        return False

    except Exception as e:
        logger.error(f"Ошибка save_to_db для акта {act_number} пользователя {chat_id}: {e}", exc_info=True)
        # bot.send_message(chat_id, "❌ Ошибка при сохранении акта.") # Это сообщение отправляется уже в handle_text
        return False

    finally:
        if conn:
            conn.close()
        # Очистка временных данных и сброс статуса теперь происходит при успешном сохранении или в handle_text/handle_photo при ошибке


# === ШАГ 10: Просмотр актов пользователя ===
# ✅ Этот обработчик вызывается из handle_text
# @bot.message_handler(commands=['view_acts']) # ✅ Больше не нужно, вызывается из handle_text
def view_acts(message, page=0, page_size=5):
    chat_id = message.chat.id
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    
    conn = sqlite3.connect('acts.db')
    cursor = conn.cursor()
    
    # Общее количество актов
    cursor.execute("SELECT COUNT(*) FROM acts", ())
    total_acts = cursor.fetchone()[0]
    
    # Получаем акты для текущей страницы
    cursor.execute(
        "SELECT act_number FROM acts LIMIT ? OFFSET ?",
            (page_size, page * page_size)
    )
    
    acts = cursor.fetchall()
    conn.close()
    
    # Добавляем кнопки навигации
    if page > 0:
        markup.add(types.KeyboardButton("⬅️ Назад"))
        
    for (act_num,) in acts:
        markup.add(types.KeyboardButton(act_num))
    
    if (page + 1) * page_size < total_acts:
        markup.add(types.KeyboardButton("➡️ Вперед"))
    
    markup.add(btn_back)
    
    msg = bot.send_message(
        chat_id,
        f"Страница {page+1}\nВыберите номер акта:",
        reply_markup=markup
    )
    bot.register_next_step_handler(msg, lambda m: handle_pagination(m, page))

def handle_pagination(message, current_page):
    chat_id = message.chat.id
    text = message.text
    
    if text == "➡️ Вперед":
        view_acts(message, page=current_page + 1)
    elif text == "⬅️ Назад Страница":
        logger.debug(f"Пользователь {chat_id} нажал '⬅️ Назад Страница'.")
        bot.clear_step_handler(message.chat.id)
        # ✅ Не удаляем из истории, т.k. остаемся в просмотре актов
        view_acts(message, page=max(0, current_page - 1))
    else:
        # Если это не кнопка навигации и не "Назад", предполагаем, что это номер акта
        act_number = text
        logger.debug(f"Пользователь {chat_id} выбрал акт для просмотра фото: \"{act_number}\"")

        # ✅ Проверяем, что введенный текст - это номер акта, который действительно есть у пользователя
        conn = None
        try:
            conn = sqlite3.connect('acts.db')
            cursor = conn.cursor()
            cursor.execute("SELECT 1 FROM acts WHERE chat_id = ? AND act_number = ?", (chat_id, act_number))
            exists = cursor.fetchone() is not None
            conn.close()
            conn = None
        except Exception as e:
            logger.error(f"Ошибка проверки существования акта {act_number} для пользователя {chat_id} в handle_view_acts_input: {e}", exc_info=True)
            if conn: conn.close()
            bot.send_message(chat_id, "❌ Произошла ошибка при проверке номера акта.", reply_markup=main_menu_keyboard) # ✅ Возвращаем главное меню
            bot.clear_step_handler(message.chat.id)
            # ✅ Удаляем последний шаг из истории
            if user_history.get(chat_id): user_history[chat_id].pop()
            return # Прерываем выполнение

        if exists:
            # Если акт существует, вызываем функцию просмотра фото
            # ✅ Добавляем шаг в историю
            user_history[chat_id].append(f'act_photos_{act_number}')
            act_photos(message) # message содержит act_number в text
            # ✅ После показа фото, act_photos сам вернет в главное меню или список актов
            # Очищаем ожидающий handler здесь после обработки выбора акта
            bot.clear_step_handler(message.chat.id)


        else:
            logger.warning(f"Пользователь {chat_id} ввел неверный номер акта или текст: \"{text}\" после просмотра актов.")
            bot.send_message(chat_id, "Неверный номер акта. Выберите номер из списка или используйте навигацию.", reply_markup=main_menu_keyboard) # ✅ Возвращаем главное меню
            # ✅ Остаемся на том же шаге, регистрируем handler снова
            bot.clear_step_handler(message.chat.id)
            view_acts(message, page=current_page) # ✅ Возвращаемся к списку актов на текущей странице


# === ШАГ 11: Отправка фото по выбранному акту ===
def act_photos(message):
    chat_id = message.chat.id
    act_number = message.text
    logger.info(f"Пользователь {chat_id} запросил фото для акта №{act_number}.")

    # ✅ Кнопка Назад здесь не обрабатывается, т.к. она должна быть обработана в handle_view_acts_input


    conn = None
    try:
        conn = sqlite3.connect('acts.db')
        cursor = conn.cursor()
        cursor.execute(
            "SELECT photo_urls FROM acts WHERE act_number = ?",
            (act_number,)
        )
        row = cursor.fetchone()
        conn.close()
        conn = None

        if not row:
            logger.warning(f"Акт №{act_number} не найден для пользователя {chat_id}.")
            bot.send_message(chat_id, "Акт не найден.", reply_markup=main_menu_keyboard) # ✅ Возвращаем главное меню
            # ✅ Удаляем последний шаг из истории
            if user_history.get(chat_id): user_history[chat_id].pop()
            return

        photo_paths_json = row[0]
        if not photo_paths_json:
            logger.warning(f"Для акта №{act_number} пользователя {chat_id} нет сохраненных путей фото.")
            bot.send_message(chat_id, f"Нет фото для акта №{act_number}.", reply_markup=main_menu_keyboard) # ✅ Возвращаем главное меню
            # ✅ Удаляем последний шаг из истории
            if user_history.get(chat_id): user_history[chat_id].pop()
            return


        photo_paths = json.loads(photo_paths_json)

        if not photo_paths:
            logger.warning(f"Список путей фото для акта №{act_number} пользователя {chat_id} пуст после парсинга.")
            bot.send_message(chat_id, f"Нет фото для акта №{act_number}.", reply_markup=main_menu_keyboard) # ✅ Возвращаем главное меню
            # ✅ Удаляем последний шаг из истории
            if user_history.get(chat_id): user_history[chat_id].pop()
            return

        logger.info(f"Отправка {len(photo_paths)} фото для акта №{act_number} пользователю {chat_id}.")

        bot.send_message(chat_id, f"Фотографии для акта №{act_number}:", reply_markup=types.ReplyKeyboardRemove())

        sent = 0
        for path in photo_paths:
            try:
                with open(path, 'rb') as ph:
                    bot.send_photo(chat_id, ph)
                    sent += 1
                logger.debug(f"Отправлено фото: {path}")

            except Exception as e:
                logger.error(f"Ошибка отправки фото {path} для акта №{act_number} пользователя {chat_id}: {e}", exc_info=True)
                bot.send_message(chat_id, f"❌ Ошибка при отправке фото: {os.path.basename(path)}")


        logger.info(f"Всего отправлено {sent}/{len(photo_paths)} фото для акта №{act_number} пользователю {chat_id}.")
        # ✅ Возвращаемся в список актов после отправки фото
        # bot.send_message(chat_id, f"✅ Отправлено {sent} фото.", reply_markup=main_menu_keyboard) # ✅ Возвращаем главное меню
        # ✅ Удаляем последний шаг из истории (просмотр фото)
        if user_history.get(chat_id): user_history[chat_id].pop()
        # ✅ Возвращаемся в список актов
        # Нужно передать message, чтобы view_acts мог получить chat_id
        # Создаем фиктивное сообщение или используем исходное, если доступно
        # Проще всего использовать исходное message, которое пришло в handle_view_acts_input
        # Но act_photos вызывается напрямую из handle_view_acts_input, message там - это ввод пользователя (номер акта).
        # Чтобы вернуться в view_acts, нужно знать текущую страницу.
        # Простейший вариант - вернуться в главное меню, как это было в предыдущих версиях, чтобы избежать проблем с состоянием пагинации.
        bot.send_message(chat_id, f"✅ Отправлено {sent} фото.", reply_markup=main_menu_keyboard)
        start(message) # ✅ Возвращаемся в главное меню после показа фото


    except Exception as e:
        print(f"Ошибка в act_photos: {e}")
        bot.send_message(chat_id, "❌ Ошибка при показе фото.", reply_markup=back_markup)
        bot.register_next_step_handler(message, view_acts)

# === ШАГ 12: Справка по команде /help ===
@bot.message_handler(commands=['help'])
def send_help(message):
    chat_id = message.chat.id
    logger.info(f"Получена команда /help от пользователя {chat_id}")

    bot.clear_step_handler(message.chat.id)

    help_text = (
        "🤖 Справка по боту РПРЗ 🤖\n\n"
        "📝Рег. несоответствия — начать регистрацию акта.\n"
        "📊Акты о браке — посмотреть сохранённые акты.\n"
        "📋Поиск — в разработке.\n"
        "🤖Нейропомощник РПРЗ — спросить у базы знаний.\n" # ✅ Обновлен текст описания
        "Назад — вернуться назад.\n"
        "/start — вернуться в главное меню.\n" # ✅ Добавлено описание команды start
        "/help — эта справка.\n"
    )
    bot.send_message(chat_id, help_text, reply_markup=main_menu_keyboard) # ✅ Возвращаем главное меню
    # start(message) # ✅ Не нужно вызывать start, т.к. отправляем главное меню напрямую


# === ШАГ 13: Запуск бота (основной цикл) ===
if __name__ == '__main__':
    
    # ✅ Инициализация Базы Знаний RAG перед запуском бота
    logger.info("Начинаем инициализацию базы знаний RAG перед запуском бота...")
    # Проверяем, успешно ли импортировался rag_service
    if rag_service:
        try:
            # Убедитесь, что в rag_service.py указаны правильные пути к папкам с PDF и индексом FAISS
            # Создайте папку db/db_01, если ее нет
            os.makedirs('db/db_01', exist_ok=True)

            # ✅ Вызываем функцию get_or_create_vector_db из rag_service
            # Declare global variable before assignment
            rag_db = rag_service.get_or_create_vector_db()

            if rag_db:
                logger.info("База знаний RAG успешно загружена или создана. Бот готов к работе с RAG.")
                logger.info("Бот запускает пуллинг...")
                # ✅ Запускаем бота. none_stop=True перезапускает при ошибках.
                bot.polling(none_stop=True)
                logger.info("Бот остановлен.")
            else:
                # Если rag_db не загрузился/создался (вернул None), бот не запускает пуллинг
                logger.error("Не удалось загрузить или создать базу знаний RAG! Бот не будет запущен с RAG функционалом.")
                print("\n\nКРИТИЧЕСКАЯ ОШИБКА: База знаний RAG недоступна. Бот не запущен.\nПроверьте логи в log/rag_service.log и log/bot.log\n\n")

        except Exception as e:
             logger.critical(f"Критическая ошибка при инициализации базы знаний RAG и запуске бота: {e}", exc_info=True)
             print(f"\n\nКРИТИЧЕСКАЯ ОШИБКА ПРИ ЗАПУСКЕ: {e}\nБот не запущен.\nПроверьте логи в log/rag_service.log и log/bot.log\n\n")
    else:
        # Если rag_service не импортировался, запускаем бота без RAG функционала
        logger.warning("Модуль rag_service не загружен. Запуск бота без функционала Нейропомощника.")
        logger.info("Бот запускает пуллинг...")
        bot.polling(none_stop=True)
        logger.info("Бот остановлен.")

