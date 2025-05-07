import unittest
from unittest.mock import patch, MagicMock, call
import sqlite3
import json
import os
import sys

# Добавляем путь к директории src для импорта
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '')))

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
        def download_file(self, *args, **kwargs): return b'fake_file_content'
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

# --- Дополнительные тестовые классы ---

class TestExceptionHandling(unittest.TestCase):
    """Тесты для проверки обработки исключений."""
    
    def setUp(self):
        """Сброс состояний перед каждым тестом."""
        user_photos.clear()
        user_act_number.clear()
        bot_status.clear()
        bot_status_state.clear()
        user_history.clear()
        # Мокаем бота глобально для хендлеров
        self.mock_bot = MagicMock()
        self.mock_bot.send_message = MagicMock()
        self.mock_bot.register_next_step_handler = MagicMock()
        self.mock_bot.get_file = MagicMock(return_value=MagicMock(file_path='test/path'))
        self.mock_bot.download_file = MagicMock(return_value=b'fake_file_content')
        self.mock_bot.send_media_group = MagicMock()
        self.mock_bot.token = 'fake_token'
        # Патчим глобальный объект bot
        self.patcher_bot = patch('src.RPRZBOT.bot', self.mock_bot)
        self.patcher_bot.start()
    
    def tearDown(self):
        """Остановка патчей после каждого теста."""
        self.patcher_bot.stop()
    
    @patch('src.RPRZBOT.os.makedirs')
    def test_handle_photo_directory_creation_error(self, mock_makedirs):
        """Тест обработки ошибки при создании директории для фото."""
        chat_id = 4001
        message = create_mock_message(chat_id, photo=True)
        bot_status[chat_id] = 'ожидание фото'
        user_act_number[chat_id] = '123'
        user_photos[chat_id] = []
        
        # Имитируем ошибку при создании директории
        mock_makedirs.side_effect = OSError("Ошибка создания директории")
        
        handle_photo(message)
        
        # Проверяем, что отправлено сообщение об ошибке
        self.mock_bot.send_message.assert_called_with(
            chat_id, 
            "Произошла ошибка при сохранении фотографии. Пожалуйста, попробуйте позже.", 
            reply_markup=back_markup
        )
    
    @patch('src.RPRZBOT.open', create=True)
    def test_handle_photo_file_write_error(self, mock_open):
        """Тест обработки ошибки при записи файла фото."""
        chat_id = 4002
        message = create_mock_message(chat_id, photo=True)
        bot_status[chat_id] = 'ожидание фото'
        user_act_number[chat_id] = '123'
        user_photos[chat_id] = []
        
        # Имитируем ошибку при открытии файла для записи
        mock_open.side_effect = IOError("Ошибка записи файла")
        
        handle_photo(message)
        
        # Проверяем, что отправлено сообщение об ошибке
        self.mock_bot.send_message.assert_called_with(
            chat_id, 
            "Произошла ошибка при сохранении фотографии. Пожалуйста, попробуйте позже.", 
            reply_markup=back_markup
        )
    
    @patch('src.RPRZBOT.sqlite3.connect')
    def test_save_to_db_connection_error(self, mock_connect):
        """Тест обработки ошибки подключения к БД при сохранении акта."""
        chat_id = 4003
        user_act_number[chat_id] = '123'
        user_photos[chat_id] = ['url1']
        
        # Имитируем ошибку подключения к БД
        mock_connect.side_effect = sqlite3.OperationalError("Ошибка подключения к БД")
        
        result = save_to_db(chat_id)
        
        # Проверяем, что функция вернула False (ошибка)
        self.assertFalse(result)
        # Проверяем, что отправлено сообщение об ошибке
        self.mock_bot.send_message.assert_called_with(
            chat_id, 
            "Произошла ошибка при сохранении акта. Пожалуйста, попробуйте позже."
        )
    
    @patch('src.RPRZBOT.sqlite3.connect')
    def test_view_acts_connection_error(self, mock_connect):
        """Тест обработки ошибки подключения к БД при просмотре актов."""
        chat_id = 4004
        message = create_mock_message(chat_id)
        
        # Имитируем ошибку подключения к БД
        mock_connect.side_effect = sqlite3.OperationalError("Ошибка подключения к БД")
        
        view_acts(message)
        
        # Проверяем, что отправлено сообщение об ошибке
        self.mock_bot.send_message.assert_called_with(
            chat_id, 
            "Произошла ошибка при доступе к базе данных. Пожалуйста, попробуйте позже.", 
            reply_markup=back_markup
        )


class TestBoundaryConditions(unittest.TestCase):
    """Тесты для проверки граничных условий."""
    
    def setUp(self):
        """Сброс состояний перед каждым тестом."""
        user_photos.clear()
        user_act_number.clear()
        bot_status.clear()
        bot_status_state.clear()
        user_history.clear()
        # Мокаем бота глобально для хендлеров
        self.mock_bot = MagicMock()
        self.mock_bot.send_message = MagicMock()
        self.mock_bot.register_next_step_handler = MagicMock()
        self.mock_bot.get_file = MagicMock(return_value=MagicMock(file_path='test/path'))
        self.mock_bot.download_file = MagicMock(return_value=b'fake_file_content')
        self.mock_bot.send_media_group = MagicMock()
        self.mock_bot.token = 'fake_token'
        # Патчим глобальный объект bot
        self.patcher_bot = patch('src.RPRZBOT.bot', self.mock_bot)
        self.patcher_bot.start()
    
    def tearDown(self):
        """Остановка патчей после каждого теста."""
        self.patcher_bot.stop()
    
    def test_process_act_number_single_digit(self):
        """Тест ввода однозначного номера акта."""
        chat_id = 5001
        message = create_mock_message(chat_id, text='1')
        
        process_act_number(message)
        
        # Проверяем, что номер акта принят
        self.assertEqual(user_act_number.get(chat_id), '1')
        self.assertEqual(bot_status.get(chat_id), 'ожидание фото')
        self.assertEqual(user_photos.get(chat_id), [])
    
    def test_process_act_number_four_digits(self):
        """Тест ввода четырехзначного номера акта (граничное значение)."""
        chat_id = 5002
        message = create_mock_message(chat_id, text='9999')
        
        process_act_number(message)
        
        # Проверяем, что номер акта принят
        self.assertEqual(user_act_number.get(chat_id), '9999')
        self.assertEqual(bot_status.get(chat_id), 'ожидание фото')
        self.assertEqual(user_photos.get(chat_id), [])
    
    def test_process_act_number_five_digits(self):
        """Тест ввода пятизначного номера акта (превышение лимита)."""
        chat_id = 5003
        message = create_mock_message(chat_id, text='10000')
        
        process_act_number(message)
        
        # Проверяем, что номер акта отклонен
        self.assertNotIn(chat_id, user_act_number)
        # Проверяем, что отправлено сообщение об ошибке
        self.mock_bot.send_message.assert_called_with(
            chat_id, 
            'Некорректный номер. Введите 1–4 цифры:', 
            reply_markup=back_markup
        )
    
    def test_process_act_number_non_digit(self):
        """Тест ввода нецифрового номера акта."""
        chat_id = 5004
        message = create_mock_message(chat_id, text='abc')
        
        process_act_number(message)
        
        # Проверяем, что номер акта отклонен
        self.assertNotIn(chat_id, user_act_number)
        # Проверяем, что отправлено сообщение об ошибке
        self.mock_bot.send_message.assert_called_with(
            chat_id, 
            'Некорректный номер. Введите 1–4 цифры:', 
            reply_markup=back_markup
        )
    
    def test_process_act_number_empty(self):
        """Тест ввода пустого номера акта."""
        chat_id = 5005
        message = create_mock_message(chat_id, text='')
        
        process_act_number(message)
        
        # Проверяем, что номер акта отклонен
        self.assertNotIn(chat_id, user_act_number)
        # Проверяем, что отправлено сообщение об ошибке
        self.mock_bot.send_message.assert_called_with(
            chat_id, 
            'Некорректный номер. Введите 1–4 цифры:', 
            reply_markup=back_markup
        )


class TestUserInteractionFlow(unittest.TestCase):
    """Тесты для проверки потока взаимодействия с пользователем."""
    
    def setUp(self):
        """Сброс состояний перед каждым тестом."""
        user_photos.clear()
        user_act_number.clear()
        bot_status.clear()
        bot_status_state.clear()
        user_history.clear()
        # Мокаем бота глобально для хендлеров
        self.mock_bot = MagicMock()
        self.mock_bot.send_message = MagicMock()
        self.mock_bot.register_next_step_handler = MagicMock()
        self.mock_bot.get_file = MagicMock(return_value=MagicMock(file_path='test/path'))
        self.mock_bot.download_file = MagicMock(return_value=b'fake_file_content')
        self.mock_bot.send_media_group = MagicMock()
        self.mock_bot.token = 'fake_token'
        # Патчим глобальный объект bot
        self.patcher_bot = patch('src.RPRZBOT.bot', self.mock_bot)
        self.patcher_bot.start()
    
    def tearDown(self):
        """Остановка патчей после каждого теста."""
        self.patcher_bot.stop()
    
    def test_complete_act_registration_flow(self):
        """Тест полного потока регистрации акта: ввод номера, загрузка фото, сохранение."""
        chat_id = 6001
        
        # Шаг 1: Нажатие кнопки 'Рег. несоответствия'
        message1 = create_mock_message(chat_id, text='📝Рег. несоответствия')
        handle_text(message1)
        
        # Проверяем, что запрошен номер акта
        self.mock_bot.send_message.assert_called_with(
            chat_id, 
            'Введите номер акта о браке (от 1 до 4 цифр):', 
            reply_markup=back_markup
        )
        self.assertEqual(user_history.get(chat_id), ['menu_act'])
        
        # Сбрасываем моки для следующего шага
        self.mock_bot.send_message.reset_mock()
        
        # Шаг 2: Ввод номера акта
        message2 = create_mock_message(chat_id, text='123')
        process_act_number(message2)
        
        # Проверяем, что номер акта принят
        self.assertEqual(user_act_number.get(chat_id), '123')
        self.assertEqual(bot_status.get(chat_id), 'ожидание фото')
        self.assertEqual(user_photos.get(chat_id), [])
        
        # Сбрасываем моки для следующего шага
        self.mock_bot.send_message.reset_mock()
        
        # Шаг 3: Загрузка фото
        message3 = create_mock_message(chat_id, photo=True)
        handle_photo(message3)
        
        # Проверяем, что фото добавлено
        self.assertEqual(len(user_photos.get(chat_id)), 1)
        
        # Сбрасываем моки для следующего шага
        self.mock_bot.send_message.reset_mock()
        
        # Шаг 4: Сохранение акта
        message4 = create_mock_message(chat_id, text='✅Сохранить акт')
        
        # Мокаем save_to_db для успешного сохранения
        with patch('src.RPRZBOT.save_to_db', return_value=True):
            handle_text(message4)
        
        # Проверяем, что отправлено сообщение об успешном сохранении
        self.mock_bot.send_message.assert_called_with(
            chat_id, 
            'Акт сохранён. Возвращаюсь в главное меню.', 
            reply_markup=types.ReplyKeyboardRemove()
        )
    
    def test_navigation_history(self):
        """Тест навигации по истории действий пользователя."""
        chat_id = 6002
        
        # Шаг 1: Добавляем историю действий
        user_history[chat_id] = ['menu_act', 'view_acts']
        
        # Шаг 2: Нажатие кнопки 'Назад'
        message = create_mock_message(chat_id, text='Назад')
        
        # Мокаем start для проверки вызова
        with patch('src.RPRZBOT.start') as mock_start:
            handle_text(message)
            
            # Проверяем, что была вызвана функция start
            mock_start.assert_called_once_with(message)
            
            # Проверяем, что из истории удален последний элемент
            self.assertEqual(user_history.get(chat_id), ['menu_act'])
    
    def test_handle_text_unknown_button(self):
        """Тест нажатия неизвестной кнопки."""
        chat_id = 6003
        message = create_mock_message(chat_id, text='Неизвестная кнопка')
        
        handle_text(message)
        
        # Проверяем, что отправлено сообщение о выборе из меню
        self.mock_bot.send_message.assert_called_with(chat_id, 'Выберите вариант из меню')


if __name__ == '__main__':
    unittest.main()