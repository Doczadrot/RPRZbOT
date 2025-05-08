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
        view_acts, act_photos, init_db, send_help,
        bot, user_photos, user_act_number, bot_status, bot_status_state, user_history,
        types, back_markup, photo_choice_markup
    )
except ImportError as e:
    print(f"Не удалось импортировать из src.RPRZBOT: {e}")
    # Создаем заглушки, если импорт не удался
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
    types = MockTypes()
    start = lambda x: None
    handle_text = lambda x: None
    process_act_number = lambda x: None
    handle_photo = lambda x: None
    save_to_db = lambda x: None
    view_acts = lambda x: None
    act_photos = lambda x: None
    init_db = lambda: None
    send_help = lambda x: None
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
    message = MagicMock()
    message.chat = MagicMock(id=chat_id)
    message.from_user = MagicMock(id=chat_id)
    message.text = text
    if photo:
        mock_photo_size = MagicMock()
        mock_photo_size.file_id = 'test_file_id'
        message.photo = [mock_photo_size]
    else:
        message.photo = None
    return message


class TestEdgeCases(unittest.TestCase):
    """Тесты для проверки граничных случаев и редких сценариев."""
    
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
        self.mock_bot.token = 'fake_token'
        # Патчим глобальный объект bot
        self.patcher_bot = patch('src.RPRZBOT.bot', self.mock_bot)
        self.patcher_bot.start()
    
    def tearDown(self):
        """Остановка патчей после каждого теста."""
        self.patcher_bot.stop()
    
    def test_handle_photo_with_multiple_photos(self):
        """Тест обработки сообщения с несколькими фотографиями."""
        chat_id = 13001
        message = create_mock_message(chat_id, photo=True)
        # Создаем несколько фото в сообщении
        mock_photo_size1 = MagicMock()
        mock_photo_size1.file_id = 'small_photo_id'
        mock_photo_size2 = MagicMock()
        mock_photo_size2.file_id = 'medium_photo_id'
        mock_photo_size3 = MagicMock()
        mock_photo_size3.file_id = 'large_photo_id'
        message.photo = [mock_photo_size1, mock_photo_size2, mock_photo_size3]
        
        bot_status[chat_id] = 'ожидание фото'
        user_act_number[chat_id] = '123'
        user_photos[chat_id] = []
        
        # Патчим os.makedirs и open
        with patch('src.RPRZBOT.os.makedirs') as mock_makedirs, \
             patch('builtins.open', create=True) as mock_open:
            
            mock_file = MagicMock()
            mock_open.return_value.__enter__.return_value = mock_file
            
            handle_photo(message)
            
            # Проверяем, что была создана директория
            mock_makedirs.assert_called_with(f"photos/{chat_id}", exist_ok=True)
            # Проверяем, что использовано последнее (самое большое) фото
            self.mock_bot.get_file.assert_called_with('large_photo_id')
            # Проверяем, что файл был открыт для записи
            mock_open.assert_called_once()
            # Проверяем, что в файл были записаны данные
            mock_file.write.assert_called_once_with(b'fake_file_content')
    
    def test_handle_text_with_empty_text(self):
        """Тест обработки сообщения с пустым текстом."""
        chat_id = 13002
        message = create_mock_message(chat_id, text='')
        
        handle_text(message)
        
        # Проверяем, что отправлено сообщение о выборе из меню
        self.mock_bot.send_message.assert_called_with(chat_id, 'Выберите вариант из меню')
    
    def test_process_act_number_with_special_characters(self):
        """Тест ввода номера акта со специальными символами."""
        chat_id = 13003
        message = create_mock_message(chat_id, text='123#456')
        
        process_act_number(message)
        
        # Проверяем, что номер акта отклонен
        self.assertNotIn(chat_id, user_act_number)
        # Проверяем, что отправлено сообщение об ошибке
        self.mock_bot.send_message.assert_called_with(
            chat_id, 
            'Некорректный номер. Введите 1–4 цифры:', 
            reply_markup=back_markup
        )
    
    @patch('src.RPRZBOT.sqlite3.connect')
    def test_act_photos_with_empty_photo_list(self, mock_connect):
        """Тест просмотра фотографий для акта с пустым списком фото."""
        chat_id = 13004
        act_number = '123'
        message = create_mock_message(chat_id, text=act_number)
        
        # Настраиваем mock для возврата акта с пустым списком фото
        mock_conn = MagicMock()
        mock_connect.return_value = mock_conn
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value = mock_cursor
        mock_cursor.fetchone.return_value = (1, chat_id, act_number, '[]', '2023-01-01')
        
        # Патчим view_acts для проверки вызова
        with patch('src.RPRZBOT.view_acts') as mock_view_acts:
            
            act_photos(message)
            
            # Проверяем, что отправлено сообщение о пустом списке фото
            self.mock_bot.send_message.assert_any_call(
                chat_id, 
                f"Нет фото для акта №{act_number}.", 
                reply_markup=back_markup
            )
            # Проверяем, что вызвана функция view_acts
            mock_view_acts.assert_called_once_with(message)
    
    @patch('src.RPRZBOT.sqlite3.connect')
    def test_view_acts_with_multiple_acts(self, mock_connect):
        """Тест просмотра нескольких актов."""
        chat_id = 13005
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
        
        # Проверяем, что отправлено сообщение с выбором актов
        self.mock_bot.send_message.assert_called_with(
            chat_id, 
            "Выберите номер акта:", 
            reply_markup=self.mock_bot.send_message.call_args[1]['reply_markup']
        )
        # Проверяем, что зарегистрирован обработчик следующего шага
        self.mock_bot.register_next_step_handler.assert_called_once_with(message, act_photos)


class TestCommandHandlers(unittest.TestCase):
    """Тесты для проверки обработчиков команд."""
    
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
        self.mock_bot.token = 'fake_token'
        # Патчим глобальный объект bot
        self.patcher_bot = patch('src.RPRZBOT.bot', self.mock_bot)
        self.patcher_bot.start()
    
    def tearDown(self):
        """Остановка патчей после каждого теста."""
        self.patcher_bot.stop()
    
    def test_start_command(self):
        """Тест команды /start."""
        chat_id = 14001
        message = create_mock_message(chat_id)
        
        start(message)
        
        # Проверяем, что установлено состояние главного меню
        self.assertEqual(bot_status_state.get(chat_id), 'main_menu')
        # Проверяем, что история очищена
        self.assertEqual(user_history.get(chat_id), [])
        # Проверяем, что отправлено приветственное сообщение
        self.mock_bot.send_message.assert_called_once()
        # Проверяем, что в сообщении есть приветствие
        self.assertIn('Привет', self.mock_bot.send_message.call_args[0][1])
    
    def test_help_command(self):
        """Тест команды /help."""
        chat_id = 14002
        message = create_mock_message(chat_id)
        
        # Патчим start для проверки вызова
        with patch('src.RPRZBOT.start') as mock_start:
            
            send_help(message)
            
            # Проверяем, что отправлено сообщение со справкой
            self.mock_bot.send_message.assert_called_once()
            # Проверяем, что в сообщении есть слово 'Справка'
            self.assertIn('Справка', self.mock_bot.send_message.call_args[0][1])
            # Проверяем, что вызвана функция start
            mock_start.assert_called_once_with(message)
    
    def test_view_acts_command(self):
        """Тест команды /view_acts."""
        chat_id = 14003
        message = create_mock_message(chat_id)
        
        # Патчим sqlite3.connect для имитации пустого результата
        with patch('src.RPRZBOT.sqlite3.connect') as mock_connect:
            mock_conn = MagicMock()
            mock_connect.return_value = mock_conn
            mock_cursor = MagicMock()
            mock_conn.cursor.return_value = mock_cursor
            mock_cursor.fetchall.return_value = []
            
            view_acts(message)
            
            # Проверяем, что отправлено сообщение об отсутствии актов
            self.mock_bot.send_message.assert_called_with(
                chat_id, 
                "У вас пока нет сохранённых актов.", 
                reply_markup=back_markup
            )


class TestComplexScenarios(unittest.TestCase):
    """Тесты для проверки сложных сценариев взаимодействия."""
    
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
        self.mock_bot.token = 'fake_token'
        # Патчим глобальный объект bot
        self.patcher_bot = patch('src.RPRZBOT.bot', self.mock_bot)
        self.patcher_bot.start()
    
    def tearDown(self):
        """Остановка патчей после каждого теста."""
        self.patcher_bot.stop()
    
    def test_full_act_registration_flow_with_multiple_photos(self):
        """Тест полного потока регистрации акта с несколькими фотографиями."""
        chat_id = 15001
        
        # Шаг 1: Нажатие кнопки 'Рег. несоответствия'
        message1 = create_mock_message(chat_id, text='📝Рег. несоответствия')
        handle_text(message1)
        
        # Проверяем, что запрошен номер акта
        self.mock_bot.send_message.assert_called_with(
            chat_id, 
            'Введите номер акта о браке (1–4 цифры):', 
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
        
        # Шаг 3: Загрузка первого фото
        message3 = create_mock_message(chat_id, photo=True)
        
        # Патчим os.makedirs и open для первого фото
        with patch('src.RPRZBOT.os.makedirs') as mock_makedirs, \
             patch('builtins.open', create=True) as mock_open:
            
            mock_file = MagicMock()
            mock_open.return_value.__enter__.return_value = mock_file
            
            handle_photo(message3)
            
            # Проверяем, что фото добавлено
            self.assertEqual(len(user_photos.get(chat_id)), 1)
        
        # Сбрасываем моки для следующего шага
        self.mock_bot.send_message.reset_mock()
        
        # Шаг 4: Загрузка второго фото
        message4 = create_mock_message(chat_id, photo=True)
        
        # Патчим os.makedirs и open для второго фото
        with patch('src.RPRZBOT.os.makedirs') as mock_makedirs, \
             patch('builtins.open', create=True) as mock_open:
            
            mock_file = MagicMock()
            mock_open.return_value.__enter__.return_value = mock_file
            
            handle_photo(message4)
            
            # Проверяем, что фото добавлено
            self.assertEqual(len(user_photos.get(chat_id)), 2)
        
        # Сбрасываем моки для следующего шага
        self.mock_bot.send_message.reset_mock()
        
        # Шаг 5: Сохранение акта
        message5 = create_mock_message(chat_id, text='✅Сохранить акт')
        
        # Патчим save_to_db для успешного сохранения
        with patch('src.RPRZBOT.save_to_db', return_value=True) as mock_save_to_db, \
             patch('src.RPRZBOT.start') as mock_start:
            
            handle_text(message5)
            
            # Проверяем, что вызвана функция save_to_db
            mock_save_to_db.assert_called_once_with(chat_id)
            # Проверяем, что отправлено сообщение об успешном сохранении
            self.mock_bot.send_message.assert_called_with(
                chat_id, 
                '✅ Акт сохранён. Возвращаюсь в главное меню.', 
                reply_markup=types.ReplyKeyboardRemove()
            )
            # Проверяем, что вызвана функция start
            mock_start.assert_called_once_with(message5)


if __name__ == '__main__':
    unittest.main()