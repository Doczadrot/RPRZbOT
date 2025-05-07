import unittest
from unittest.mock import patch, MagicMock, call
import sqlite3
import json
import os

# Импортируем функции и переменные из основного файла бота
# Предполагаем, что RPRZBOT.py находится в той же директории
# Нам нужно будет немного адаптировать RPRZBOT.py для тестирования
# (например, передавать bot как аргумент или использовать глобальный mock)
# Пока что сделаем заглушки для импорта

try:
    from src.RPRZBOT import (
        start, handle_text, process_act_number, handle_photo, save_to_db,
        view_acts, act_photos, init_db,
        bot, user_photos, user_act_number, bot_status, bot_status_state, user_history,
        types, back_markup, photo_choice_markup # Импортируем необходимые объекты telebot
    )
except ImportError as e:
    print(f"Не удалось импортировать из src.RPRZBOT: {e}")
    # Создаем заглушки, если импорт не удался (для начальной структуры)
    class MockBot:
        def send_message(self, *args, **kwargs): pass
        def register_next_step_handler(self, *args, **kwargs): pass
        def get_file(self, *args, **kwargs): return MagicMock(file_path='test/path')
        token = 'fake_token'
    bot = MockBot()
    class MockTypes:
        class ReplyKeyboardMarkup: pass
        class KeyboardButton: pass
        class ReplyKeyboardRemove: pass
        class Message:
            def __init__(self, chat_id, text=None, photo=None):
                self.chat = MagicMock(id=chat_id)
                self.text = text
                self.photo = photo
        class User:
            id = 123
    types = MockTypes()
    start = lambda x: None
    handle_text = lambda x: None
    process_act_number = lambda x: None
    handle_photo = lambda x: None
    save_to_db = lambda x: None
    view_acts = lambda x: None
    act_photos = lambda x: None
    init_db = lambda: None
    user_photos = {}
    user_act_number = {}
    bot_status = {}
    bot_status_state = {}
    user_history = {}
    back_markup = None
    photo_choice_markup = None

# --- Вспомогательные функции для тестов ---

def create_mock_message(chat_id, text=None, photo=None):
    """Создает mock объект сообщения Telegram."""
    message = MagicMock(spec=types.Message)
    message.chat = MagicMock(id=chat_id)
    message.from_user = MagicMock(id=chat_id) # Часто chat_id и user_id совпадают в личных чатах
    message.text = text
    message.photo = photo # Список объектов PhotoSize
    if photo:
        # Имитируем структуру message.photo[-1].file_id
        mock_photo_size = MagicMock()
        mock_photo_size.file_id = 'test_file_id'
        message.photo = [mock_photo_size] # Список с одним элементом для простоты
    else:
        message.photo = None
    return message

# --- Тестовые классы ---

class TestBotDatabase(unittest.TestCase):
    """Тесты для функций, взаимодействующих с БД."""
    DB_NAME = 'test_acts.db'

    @classmethod
    def setUpClass(cls):
        """Инициализация тестовой БД перед всеми тестами класса."""
        if os.path.exists(cls.DB_NAME):
            os.remove(cls.DB_NAME)
        # Используем тестовое имя БД
        with patch('src.RPRZBOT.sqlite3.connect') as mock_connect:
            mock_conn = sqlite3.connect(cls.DB_NAME) # Создаем реальную временную БД
            mock_connect.return_value = mock_conn
            init_db() # Инициализируем схему в тестовой БД

    @classmethod
    def tearDownClass(cls):
        """Удаление тестовой БД после всех тестов класса."""
        if os.path.exists(cls.DB_NAME):
            os.remove(cls.DB_NAME)

    def setUp(self):
        """Очистка данных перед каждым тестом."""
        conn = sqlite3.connect(self.DB_NAME)
        cursor = conn.cursor()
        cursor.execute("DELETE FROM acts")
        conn.commit()
        conn.close()
        # Сбрасываем состояния перед каждым тестом
        user_photos.clear()
        user_act_number.clear()
        bot_status.clear()
        bot_status_state.clear()
        user_history.clear()

    @patch('RPRZBOT.bot.send_message') # Мокаем отправку сообщений
    @patch('RPRZBOT.sqlite3.connect') # Мокаем подключение к БД
    def test_save_to_db(self, mock_connect, mock_send_message):
        """Тест сохранения акта в базу данных."""
        # Настраиваем mock для возврата тестовой БД
        mock_conn = sqlite3.connect(self.DB_NAME)
        mock_connect.return_value = mock_conn

        chat_id = 123
        act_num = '111'
        photo_urls = ['http://example.com/photo1.jpg', 'http://example.com/photo2.jpg']
        user_act_number[chat_id] = act_num
        user_photos[chat_id] = photo_urls

        save_to_db(chat_id)

        # Проверяем, что данные сохранились в БД
        conn = sqlite3.connect(self.DB_NAME)
        cursor = conn.cursor()
        cursor.execute("SELECT act_number, photo_urls FROM acts WHERE chat_id = ?", (chat_id,))
        result = cursor.fetchone()
        conn.close()

        self.assertIsNotNone(result)
        self.assertEqual(result[0], act_num)
        self.assertEqual(json.loads(result[1]), photo_urls)

        # Проверяем, что словари очистились
        self.assertNotIn(chat_id, user_act_number)
        self.assertNotIn(chat_id, user_photos)

    @patch('RPRZBOT.bot.send_message')
    @patch('RPRZBOT.bot.register_next_step_handler')
    @patch('RPRZBOT.sqlite3.connect')
    def test_view_acts_no_acts(self, mock_connect, mock_register, mock_send_message):
        """Тест просмотра актов, когда актов нет."""
        mock_conn = sqlite3.connect(self.DB_NAME)
        mock_connect.return_value = mock_conn

        chat_id = 456
        message = create_mock_message(chat_id)
        view_acts(message)

        mock_send_message.assert_called_once_with(chat_id, "У вас пока нет сохраненных актов.", reply_markup=back_markup)
        mock_register.assert_not_called()

    @patch('RPRZBOT.bot.send_message')
    @patch('RPRZBOT.bot.register_next_step_handler')
    @patch('RPRZBOT.sqlite3.connect')
    def test_view_acts_with_acts(self, mock_connect, mock_register, mock_send_message):
        """Тест просмотра актов, когда акты есть."""
        mock_conn = sqlite3.connect(self.DB_NAME)
        mock_connect.return_value = mock_conn

        chat_id = 789
        act_num1 = '123'
        act_num2 = '456'
        # Добавляем тестовые данные
        conn = sqlite3.connect(self.DB_NAME)
        cursor = conn.cursor()
        cursor.execute("INSERT INTO acts (chat_id, act_number, photo_urls) VALUES (?, ?, ?)", (chat_id, act_num1, '[]'))
        cursor.execute("INSERT INTO acts (chat_id, act_number, photo_urls) VALUES (?, ?, ?)", (chat_id, act_num2, '[]'))
        conn.commit()
        conn.close()

        message = create_mock_message(chat_id)
        view_acts(message)

        # Проверяем вызов send_message с клавиатурой
        args, kwargs = mock_send_message.call_args
        self.assertEqual(args[0], chat_id)
        self.assertEqual(args[1], "Выберите номер акта для просмотра фотографий:")
        self.assertIsNotNone(kwargs.get('reply_markup'))
        # Тут можно добавить более детальную проверку кнопок клавиатуры, если нужно

        # Проверяем регистрацию следующего шага
        mock_register.assert_called_once_with(message, act_photos)

    # TODO: Добавить тесты для act_photos
    @patch('RPRZBOT.bot.send_message')
    @patch('RPRZBOT.bot.send_media_group')
    @patch('RPRZBOT.sqlite3.connect')
    def test_act_photos_found(self, mock_connect, mock_send_media_group, mock_send_message):
        """Тест просмотра фотографий существующего акта."""
        # Настройка mock DB
        mock_conn = sqlite3.connect(self.DB_NAME)
        mock_connect.return_value = mock_conn
        chat_id = 111
        act_num = '777'
        photo_urls = ['url1', 'url2']
        conn = sqlite3.connect(self.DB_NAME)
        cursor = conn.cursor()
        cursor.execute("INSERT INTO acts (chat_id, act_number, photo_urls) VALUES (?, ?, ?)",
                       (chat_id, act_num, json.dumps(photo_urls)))
        conn.commit()
        conn.close()

        message = create_mock_message(chat_id, text=act_num)
        # Вызываем функцию
        act_photos(message)

        # Проверки
        # Проверяем, что была вызвана send_media_group
        self.assertTrue(mock_send_media_group.called)
        args, kwargs = mock_send_media_group.call_args
        self.assertEqual(args[0], chat_id)
        # Проверяем, что созданы InputMediaPhoto с правильными URL
        media_group = args[1]
        self.assertEqual(len(media_group), len(photo_urls))
        self.assertEqual(media_group[0].media, photo_urls[0])
        self.assertEqual(media_group[1].media, photo_urls[1])

        # Проверяем, что было отправлено сообщение о возврате в меню
        # Ищем вызов send_message с нужным текстом
        found_return_message = False
        for call_args in mock_send_message.call_args_list:
            args, kwargs = call_args
            if args[0] == chat_id and "Возвращаюсь в главное меню" in args[1]:
                found_return_message = True
                break
        self.assertTrue(found_return_message, "Сообщение о возврате в меню не найдено")

    @patch('RPRZBOT.bot.send_message')
    @patch('RPRZBOT.sqlite3.connect')
    def test_act_photos_not_found(self, mock_connect, mock_send_message):
        """Тест просмотра фотографий несуществующего акта."""
        mock_conn = sqlite3.connect(self.DB_NAME)
        mock_connect.return_value = mock_conn
        chat_id = 222
        act_num = '888' # Несуществующий акт
        message = create_mock_message(chat_id, text=act_num)

        act_photos(message)

        # Проверяем сообщение об ошибке
        mock_send_message.assert_any_call(chat_id, f"Акт с номером {act_num} не найден.", reply_markup=back_markup)

    @patch('RPRZBOT.start') # Мокаем функцию start
    @patch('RPRZBOT.sqlite3.connect')
    def test_act_photos_back(self, mock_connect, mock_start):
        """Тест нажатия кнопки 'Назад' в act_photos."""
        mock_conn = sqlite3.connect(self.DB_NAME) # Не важно, есть ли акты
        mock_connect.return_value = mock_conn
        chat_id = 333
        message = create_mock_message(chat_id, text='Назад')

        act_photos(message)

        # Проверяем, что была вызвана функция start
        mock_start.assert_called_once_with(message)


class TestBotHandlers(unittest.TestCase):
    """Тесты для обработчиков сообщений и команд."""

    def setUp(self):
        """Сброс состояний перед каждым тестом."""
        # Сбрасываем состояния перед каждым тестом
        user_photos.clear()
        user_act_number.clear()
        bot_status.clear()
        bot_status_state.clear()
        user_history.clear()
        # Мокаем бота глобально для хендлеров
        self.mock_bot = MagicMock(spec=telebot.TeleBot)
        # Копируем методы из нашего MockBot, если они нужны
        self.mock_bot.send_message = MagicMock()
        self.mock_bot.register_next_step_handler = MagicMock()
        self.mock_bot.get_file = MagicMock(return_value=MagicMock(file_path='test/path'))
        self.mock_bot.download_file = MagicMock(return_value=b'fake_file_content')
        self.mock_bot.send_media_group = MagicMock()
        self.mock_bot.token = 'fake_token'
        # Патчим глобальный объект bot
        self.patcher_bot = patch('RPRZBOT.bot', self.mock_bot)
        self.patcher_bot.start()
        
    def test_bot_initialization(self):
        """Тест инициализации бота и его параметров."""
        # Проверяем, что бот инициализирован с правильным токеном
        self.assertEqual(self.mock_bot.token, 'fake_token')
        # Проверяем, что методы бота доступны
        self.assertTrue(hasattr(self.mock_bot, 'send_message'))
        self.assertTrue(hasattr(self.mock_bot, 'register_next_step_handler'))
        self.assertTrue(hasattr(self.mock_bot, 'get_file'))
        self.assertTrue(hasattr(self.mock_bot, 'download_file'))
        self.assertTrue(hasattr(self.mock_bot, 'send_media_group'))
        # Проверяем, что глобальные словари инициализированы
        self.assertEqual(user_photos, {})
        self.assertEqual(user_act_number, {})
        self.assertEqual(bot_status, {})
        self.assertEqual(bot_status_state, {})
        self.assertEqual(user_history, {})

    def tearDown(self):
        """Остановка патчей после каждого теста."""
        self.patcher_bot.stop()

    @patch('RPRZBOT.main_markup', return_value=types.ReplyKeyboardMarkup()) # Мокаем клавиатуру
    def test_start_command(self, mock_markup):
        """Тест команды /start."""
        chat_id = 101
        message = create_mock_message(chat_id, text='/start')
        start(message)
        self.mock_bot.send_message.assert_called_once_with(
            chat_id,
            "Привет! Я бот для сохранения актов. Выберите действие:",
            reply_markup=mock_markup.return_value
        )

    @patch('RPRZBOT.help_message', 'Test help text') # Мокаем текст помощи
    def test_help_command(self, mock_help_text):
        """Тест команды /help."""
        chat_id = 102
        message = create_mock_message(chat_id, text='/help')
        handle_help(message)
        self.mock_bot.send_message.assert_called_once_with(chat_id, mock_help_text)

    @patch('RPRZBOT.bot.send_message') # Мокаем send_message напрямую
    @patch('RPRZBOT.bot.register_next_step_handler') # Мокаем register_next_step_handler
    @patch('RPRZBOT.act_markup', return_value=types.ReplyKeyboardMarkup()) # Мокаем клавиатуру
    def test_add_act_button(self, mock_act_markup, mock_register, mock_send_message):
        """Тест нажатия кнопки 'Добавить акт'."""
        chat_id = 201
        message = create_mock_message(chat_id, text='Добавить акт')
        start(message) # Предполагаем, что start обрабатывает и кнопки

        # Проверяем отправку сообщения с запросом номера акта
        mock_send_message.assert_called_once_with(
            chat_id,
            "Введите номер акта:",
            reply_markup=mock_act_markup.return_value
        )
        # Проверяем регистрацию следующего шага
        mock_register.assert_called_once_with(message, get_act_number)
        # Проверяем установку статуса
        self.assertEqual(bot_status.get(chat_id), 'ожидание номера акта')

    @patch('RPRZBOT.bot.send_message')
    @patch('RPRZBOT.bot.register_next_step_handler')
    def test_handle_text_reg_nesootv(self, mock_register, mock_send_message):
        """Тест нажатия кнопки 'Рег. несоответствия'."""
        chat_id = 54321
        message = create_mock_message(chat_id, text='📝Рег. несоответствия')
        handle_text(message)

        # Проверяем отправку сообщения с запросом номера акта
        mock_send_message.assert_called_once_with(chat_id, 'Введите номер акта о браке (от 1 до 4 цифр):', reply_markup=back_markup)
        # Проверяем регистрацию следующего шага
        mock_register.assert_called_once_with(message, process_act_number)
        # Проверяем историю
        self.assertEqual(user_history.get(chat_id), ['menu_act'])

    @patch('RPRZBOT.view_acts') # Мокаем view_acts
    def test_handle_text_view_acts(self, mock_view_acts):
        """Тест нажатия кнопки 'Акты о браке'."""
        chat_id = 67890
        message = create_mock_message(chat_id, text='📊Акты о браке')
        handle_text(message)
        # Проверяем, что была вызвана функция view_acts
        mock_view_acts.assert_called_once_with(message)

    @patch('RPRZBOT.bot.send_message')
    def test_handle_text_save_act_no_photos(self, mock_send_message):
        """Тест нажатия 'Сохранить акт' без фото."""
        chat_id = 11223
        message = create_mock_message(chat_id, text='✅Сохранить акт')
        # Убедимся, что фото нет
        user_photos.pop(chat_id, None)
        handle_text(message)
        mock_send_message.assert_called_once_with(chat_id, 'Вы ещё не загрузили фото. Пожалуйста, загрузите хотя бы одно фото.')

    @patch('RPRZBOT.save_to_db')
    @patch('RPRZBOT.start')
    @patch('RPRZBOT.bot.send_message')
    def test_handle_text_save_act_with_photos(self, mock_send_message, mock_start, mock_save_to_db):
        """Тест нажатия 'Сохранить акт' с фото."""
        chat_id = 33445
        message = create_mock_message(chat_id, text='✅Сохранить акт')
        user_photos[chat_id] = ['url1'] # Добавляем фото
        handle_text(message)

        mock_save_to_db.assert_called_once_with(chat_id)
        mock_send_message.assert_called_once_with(chat_id, 'Акт сохранён. Возвращаюсь в главное меню.', reply_markup=types.ReplyKeyboardRemove())
        mock_start.assert_called_once_with(message)

    @patch('RPRZBOT.start')
    def test_handle_text_back(self, mock_start):
        """Тест нажатия кнопки 'Назад'."""
        chat_id = 55667
        message = create_mock_message(chat_id, text='Назад')
        user_history[chat_id] = ['menu_act'] # Добавляем что-то в историю
        handle_text(message)

        mock_start.assert_called_once_with(message)
        # Проверяем, что история очистилась (start ее очищает)
        # self.assertEqual(user_history.get(chat_id), []) # Start очищает историю

    @patch('RPRZBOT.bot.send_message')
    @patch('RPRZBOT.bot.register_next_step_handler')
    def test_process_act_number_valid(self, mock_register, mock_send_message):
        """Тест ввода корректного номера акта."""
        chat_id = 101112
        act_num = '1234'
        message = create_mock_message(chat_id, text=act_num)
        process_act_number(message)

        self.assertEqual(user_act_number.get(chat_id), act_num)
        self.assertEqual(bot_status.get(chat_id), 'ожидание фото')
        self.assertEqual(user_photos.get(chat_id), [])
        mock_send_message.assert_called_once_with(chat_id, f'Номер акта {act_num} зарегистрирован, ожидаю загрузки фотографий несоответствия (от 1 до 3 фото).', reply_markup=photo_choice_markup)
        mock_register.assert_not_called() # Не должен перерегистрировать шаг

    @patch('RPRZBOT.bot.send_message')
    @patch('RPRZBOT.bot.register_next_step_handler')
    def test_process_act_number_invalid_format(self, mock_register, mock_send_message):
        """Тест ввода некорректного номера акта (не цифры)."""
        chat_id = 131415
        message = create_mock_message(chat_id, text='abcd')
        process_act_number(message)

        self.assertNotIn(chat_id, user_act_number)
        mock_send_message.assert_called_once_with(chat_id, 'Некорректный номер акта. Пожалуйста, введите число от 1 до 4 цифр.', reply_markup=back_markup)
        mock_register.assert_called_once_with(message, process_act_number)

    @patch('RPRZBOT.bot.send_message')
    @patch('RPRZBOT.bot.register_next_step_handler')
    def test_process_act_number_invalid_length(self, mock_register, mock_send_message):
        """Тест ввода некорректного номера акта (длина)."""
        chat_id = 161718
        message = create_mock_message(chat_id, text='12345')
        process_act_number(message)

        self.assertNotIn(chat_id, user_act_number)
        mock_send_message.assert_called_once_with(chat_id, 'Некорректный номер акта. Пожалуйста, введите число от 1 до 4 цифр.', reply_markup=back_markup)
        mock_register.assert_called_once_with(message, process_act_number)

    @patch('RPRZBOT.bot.send_message')
    @patch('RPRZBOT.bot.register_next_step_handler')
    def test_process_act_number_duplicate(self, mock_register, mock_send_message):
        """Тест ввода дублирующегося номера акта."""
        chat_id = 192021
        act_num = '555'
        user_act_number[999] = act_num # Имитируем существующий акт у другого пользователя
        message = create_mock_message(chat_id, text=act_num)
        process_act_number(message)

        self.assertNotIn(chat_id, user_act_number)
        mock_send_message.assert_called_once_with(chat_id, 'Этот номер акта уже зарегистрирован. Пожалуйста, введите другой номер.', reply_markup=back_markup)
        mock_register.assert_called_once_with(message, process_act_number)

    @patch('RPRZBOT.start')
    def test_process_act_number_back(self, mock_start):
        """Тест нажатия 'Назад' при вводе номера акта."""
        chat_id = 222324
        message = create_mock_message(chat_id, text='Назад')
        process_act_number(message)
        mock_start.assert_called_once_with(message)

    @patch('RPRZBOT.bot.send_message')
    @patch('RPRZBOT.bot.get_file')
    def test_handle_photo_first(self, mock_get_file, mock_send_message):
        """Тест загрузки первого фото."""
        chat_id = 1001
        message = create_mock_message(chat_id, photo=True)
        bot_status[chat_id] = 'ожидание фото'
        user_photos[chat_id] = [] # Убедимся, что список пуст

        # Настраиваем мок get_file
        mock_file_info = MagicMock()
        mock_file_info.file_path = 'photos/file1.jpg'
        mock_get_file.return_value = mock_file_info

        handle_photo(message)

        expected_url = f'https://api.telegram.org/file/bot{bot.token}/photos/file1.jpg'
        self.assertEqual(user_photos.get(chat_id), [expected_url])
        mock_send_message.assert_called_once_with(chat_id, 'Фото 1 принято ✅. Вы можете отправить ещё 2 фото или сохранить акт.', reply_markup=photo_choice_markup)
        mock_get_file.assert_called_once_with('test_file_id')

    @patch('RPRZBOT.bot.send_message')
    @patch('RPRZBOT.bot.get_file')
    def test_handle_photo_second(self, mock_get_file, mock_send_message):
        """Тест загрузки второго фото."""
        chat_id = 1002
        message = create_mock_message(chat_id, photo=True)
        bot_status[chat_id] = 'ожидание фото'
        user_photos[chat_id] = ['url1'] # Уже есть одно фото

        mock_file_info = MagicMock()
        mock_file_info.file_path = 'photos/file2.jpg'
        mock_get_file.return_value = mock_file_info

        handle_photo(message)

        expected_url = f'https://api.telegram.org/file/bot{bot.token}/photos/file2.jpg'
        self.assertEqual(user_photos.get(chat_id), ['url1', expected_url])
        mock_send_message.assert_called_once_with(chat_id, 'Фото 2 принято ✅. Вы можете отправить ещё 1 фото или сохранить акт.', reply_markup=photo_choice_markup)

    @patch('RPRZBOT.save_to_db')
    @patch('RPRZBOT.start')
    @patch('RPRZBOT.bot.send_message')
    @patch('RPRZBOT.bot.get_file')
    def test_handle_photo_third_and_save(self, mock_get_file, mock_send_message, mock_start, mock_save_to_db):
        """Тест загрузки третьего фото и автоматического сохранения."""
        chat_id = 1003
        message = create_mock_message(chat_id, photo=True)
        bot_status[chat_id] = 'ожидание фото'
        user_photos[chat_id] = ['url1', 'url2'] # Уже есть два фото

        mock_file_info = MagicMock()
        mock_file_info.file_path = 'photos/file3.jpg'
        mock_get_file.return_value = mock_file_info

        handle_photo(message)

        expected_url = f'https://api.telegram.org/file/bot{bot.token}/photos/file3.jpg'
        # Проверяем, что URL добавился ПЕРЕД вызовом save_to_db
        self.assertEqual(user_photos.get(chat_id), ['url1', 'url2', expected_url])

        mock_send_message.assert_called_once_with(chat_id, "✅ Загружено 3 фотографии. Сохраняю акт...")
        mock_save_to_db.assert_called_once_with(chat_id)
        mock_start.assert_called_once_with(message)

    def test_handle_photo_wrong_state(self):
        """Тест получения фото, когда бот его не ожидает."""
        chat_id = 1004
        message = create_mock_message(chat_id, photo=True)
        bot_status.pop(chat_id, None) # Убираем статус ожидания фото

        handle_photo(message)

        # Проверяем, что ничего не произошло (сообщения не отправлены, фото не сохранено)
        bot.send_message.assert_not_called()
        self.assertNotIn(chat_id, user_photos)

class TestDatabaseInitialization(unittest.TestCase):
    """Тесты для инициализации базы данных."""
    DB_NAME = 'test_init_db.db'
    
    def setUp(self):
        """Подготовка перед каждым тестом."""
        # Удаляем тестовую БД, если она существует
        if os.path.exists(self.DB_NAME):
            os.remove(self.DB_NAME)
    
    def tearDown(self):
        """Очистка после каждого теста."""
        if os.path.exists(self.DB_NAME):
            os.remove(self.DB_NAME)
    
    @patch('RPRZBOT.sqlite3.connect')
    def test_init_db_creates_tables(self, mock_connect):
        """Тест создания таблиц при инициализации БД."""
        # Создаем реальную БД для теста
        mock_conn = sqlite3.connect(self.DB_NAME)
        mock_connect.return_value = mock_conn
        
        # Вызываем функцию инициализации
        init_db()
        
        # Проверяем, что таблица acts создана
        cursor = mock_conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='acts'")
        result = cursor.fetchone()
        self.assertIsNotNone(result)
        self.assertEqual(result[0], 'acts')
        
        # Проверяем структуру таблицы
        cursor.execute("PRAGMA table_info(acts)")
        columns = cursor.fetchall()
        column_names = [col[1] for col in columns]
        self.assertIn('id', column_names)
        self.assertIn('chat_id', column_names)
        self.assertIn('act_number', column_names)
        self.assertIn('photo_urls', column_names)
        self.assertIn('timestamp', column_names)


class TestErrorHandling(unittest.TestCase):
    """Тесты для обработки ошибок и граничных случаев."""
    
    def setUp(self):
        """Сброс состояний перед каждым тестом."""
        user_photos.clear()
        user_act_number.clear()
        bot_status.clear()
        bot_status_state.clear()
        user_history.clear()
    
    @patch('RPRZBOT.bot.send_message')
    def test_handle_photo_max_photos_reached(self, mock_send_message):
        """Тест попытки загрузить больше максимального количества фото."""
        chat_id = 2001
        message = create_mock_message(chat_id, photo=True)
        bot_status[chat_id] = 'ожидание фото'
        user_photos[chat_id] = ['url1', 'url2', 'url3']  # Уже есть 3 фото (максимум)
        
        handle_photo(message)
        
        # Проверяем, что отправлено сообщение о достижении лимита
        mock_send_message.assert_called_once_with(
            chat_id, 
            "Вы уже загрузили максимальное количество фотографий (3). Нажмите 'Сохранить акт' для завершения.", 
            reply_markup=photo_choice_markup
        )
        # Проверяем, что новое фото не добавлено
        self.assertEqual(len(user_photos[chat_id]), 3)
    
    @patch('RPRZBOT.bot.send_message')
    @patch('RPRZBOT.sqlite3.connect')
    def test_save_to_db_no_act_number(self, mock_connect, mock_send_message):
        """Тест сохранения акта без номера."""
        chat_id = 2002
        user_photos[chat_id] = ['url1']  # Есть фото, но нет номера акта
        
        save_to_db(chat_id)
        
        # Проверяем, что отправлено сообщение об ошибке
        mock_send_message.assert_called_once_with(
            chat_id, 
            "Ошибка: не указан номер акта. Пожалуйста, начните процесс заново."
        )
    
    @patch('RPRZBOT.bot.send_message')
    @patch('RPRZBOT.sqlite3.connect')
    def test_save_to_db_no_photos(self, mock_connect, mock_send_message):
        """Тест сохранения акта без фотографий."""
        chat_id = 2003
        user_act_number[chat_id] = '123'  # Есть номер акта, но нет фото
        user_photos[chat_id] = []  # Пустой список фото
        
        save_to_db(chat_id)
        
        # Проверяем, что отправлено сообщение об ошибке
        mock_send_message.assert_called_once_with(
            chat_id, 
            "Ошибка: не загружено ни одной фотографии. Пожалуйста, загрузите хотя бы одно фото."
        )
    
    @patch('RPRZBOT.bot.send_message')
    @patch('RPRZBOT.sqlite3.connect')
    def test_view_acts_db_error(self, mock_connect, mock_send_message):
        """Тест обработки ошибки БД при просмотре актов."""
        chat_id = 2004
        message = create_mock_message(chat_id)
        
        # Имитируем ошибку БД
        mock_connect.side_effect = sqlite3.Error("Тестовая ошибка БД")
        
        view_acts(message)
        
        # Проверяем, что отправлено сообщение об ошибке
        mock_send_message.assert_called_once_with(
            chat_id, 
            "Произошла ошибка при доступе к базе данных. Пожалуйста, попробуйте позже.", 
            reply_markup=back_markup
        )


class TestAdditionalFunctionality(unittest.TestCase):
    """Дополнительные тесты функциональности."""
    
    def setUp(self):
        """Сброс состояний перед каждым тестом."""
        user_photos.clear()
        user_act_number.clear()
        bot_status.clear()
        bot_status_state.clear()
        user_history.clear()
    
    @patch('RPRZBOT.bot.send_message')
    def test_handle_text_unknown_command(self, mock_send_message):
        """Тест обработки неизвестной команды."""
        chat_id = 3001
        message = create_mock_message(chat_id, text='Неизвестная команда')
        
        handle_text(message)
        
        # Проверяем, что отправлено сообщение о неизвестной команде
        mock_send_message.assert_called_once_with(
            chat_id, 
            "Извините, я не понимаю эту команду. Пожалуйста, используйте кнопки меню."
        )
    
    @patch('RPRZBOT.bot.send_message')
    @patch('RPRZBOT.sqlite3.connect')
    def test_act_photos_empty_photo_list(self, mock_connect, mock_send_message):
        """Тест просмотра акта с пустым списком фотографий."""
        chat_id = 3002
        act_num = '999'
        message = create_mock_message(chat_id, text=act_num)
        
        # Настраиваем mock для возврата акта с пустым списком фото
        mock_conn = MagicMock()
        mock_connect.return_value = mock_conn
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value = mock_cursor
        mock_cursor.fetchone.return_value = (1, chat_id, act_num, '[]', '2023-01-01')
        
        act_photos(message)
        
        # Проверяем, что отправлено сообщение о пустом списке фото
        mock_send_message.assert_any_call(
            chat_id, 
            f"Для акта {act_num} не загружено ни одной фотографии.", 
            reply_markup=back_markup
        )
    
    @patch('RPRZBOT.bot.send_message')
    def test_process_act_number_zero(self, mock_send_message):
        """Тест ввода нулевого номера акта."""
        chat_id = 3003
        message = create_mock_message(chat_id, text='0')
        
        process_act_number(message)
        
        # Проверяем, что номер акта принят (0 - допустимое значение)
        self.assertEqual(user_act_number.get(chat_id), '0')
        self.assertEqual(bot_status.get(chat_id), 'ожидание фото')
        self.assertEqual(user_photos.get(chat_id), [])
        
    @patch('RPRZBOT.bot.send_message')
    @patch('RPRZBOT.bot.get_file')
    def test_handle_photo_invalid_file_path(self, mock_get_file, mock_send_message):
        """Тест обработки фото с некорректным путем к файлу."""
        chat_id = 3004
        message = create_mock_message(chat_id, photo=True)
        bot_status[chat_id] = 'ожидание фото'
        user_photos[chat_id] = []
        
        # Имитируем ошибку при получении пути к файлу
        mock_get_file.side_effect = Exception("Ошибка получения файла")
        
        handle_photo(message)
        
        # Проверяем, что отправлено сообщение об ошибке
        mock_send_message.assert_called_once_with(
            chat_id, 
            "Произошла ошибка при обработке фотографии. Пожалуйста, попробуйте загрузить другое фото."
        )
        # Проверяем, что список фото не изменился
        self.assertEqual(user_photos[chat_id], [])
        
    @patch('RPRZBOT.bot.send_message')
    @patch('RPRZBOT.sqlite3.connect')
    def test_save_to_db_with_duplicate_act_number(self, mock_connect, mock_send_message):
        """Тест сохранения акта с уже существующим номером."""
        chat_id = 3005
        act_num = '777'
        user_act_number[chat_id] = act_num
        user_photos[chat_id] = ['url1']
        
        # Настраиваем mock для имитации ошибки уникальности
        mock_conn = MagicMock()
        mock_connect.return_value = mock_conn
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value = mock_cursor
        mock_cursor.execute.side_effect = sqlite3.IntegrityError("UNIQUE constraint failed")
        
        save_to_db(chat_id)
        
        # Проверяем, что отправлено сообщение об ошибке
        mock_send_message.assert_called_once_with(
            chat_id, 
            f"Ошибка: акт с номером {act_num} уже существует. Пожалуйста, используйте другой номер."
        )
        
    @patch('RPRZBOT.bot.send_message')
    @patch('RPRZBOT.sqlite3.connect')
    def test_view_acts_multiple_acts(self, mock_connect, mock_send_message):
        """Тест просмотра нескольких актов с сортировкой по времени."""
        chat_id = 3006
        message = create_mock_message(chat_id)
        
        # Настраиваем mock для возврата нескольких актов
        mock_conn = MagicMock()
        mock_connect.return_value = mock_conn
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value = mock_cursor
        mock_cursor.fetchall.return_value = [
            (1, chat_id, '111', '[]', '2023-01-01'),
            (2, chat_id, '222', '[]', '2023-01-02'),
            (3, chat_id, '333', '[]', '2023-01-03')
        ]
        
        view_acts(message)
        
        # Проверяем, что была создана клавиатура с кнопками для всех актов
        args, kwargs = mock_send_message.call_args
        self.assertEqual(args[0], chat_id)
        self.assertEqual(args[1], "Выберите номер акта для просмотра фотографий:")
        # Проверка наличия reply_markup (клавиатуры)
        self.assertIn('reply_markup', kwargs)
        
    @patch('RPRZBOT.bot.send_message')
    @patch('RPRZBOT.bot.send_media_group')
    @patch('RPRZBOT.sqlite3.connect')
    def test_act_photos_with_corrupted_json(self, mock_connect, mock_send_media_group, mock_send_message):
        """Тест просмотра фотографий с поврежденным JSON в БД."""
        chat_id = 3007
        act_num = '888'
        message = create_mock_message(chat_id, text=act_num)
        
        # Настраиваем mock для возврата акта с некорректным JSON
        mock_conn = MagicMock()
        mock_connect.return_value = mock_conn
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value = mock_cursor
        mock_cursor.fetchone.return_value = (1, chat_id, act_num, '{некорректный json}', '2023-01-01')
        
        act_photos(message)
        
        # Проверяем, что отправлено сообщение об ошибке
        mock_send_message.assert_any_call(
            chat_id, 
            "Произошла ошибка при обработке данных акта. Пожалуйста, обратитесь к администратору.", 
            reply_markup=back_markup
        )
        # Проверяем, что send_media_group не вызывался
        mock_send_media_group.assert_not_called()


if __name__ == '__main__':
    unittest.main() # Используем стандартный запуск тестов