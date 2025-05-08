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


class TestErrorHandlingAdvanced(unittest.TestCase):
    """Расширенные тесты обработки ошибок."""
    
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
    
    @patch('src.RPRZBOT.sqlite3.connect')
    def test_save_to_db_integrity_error(self, mock_connect):
        """Тест обработки ошибки уникальности при сохранении акта."""
        chat_id = 11001
        act_number = '123'
        user_act_number[chat_id] = act_number
        user_photos[chat_id] = ['photo1.jpg']
        
        # Настраиваем mock для имитации ошибки уникальности
        mock_conn = MagicMock()
        mock_connect.return_value = mock_conn
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value = mock_cursor
        mock_cursor.execute.side_effect = sqlite3.IntegrityError("UNIQUE constraint failed")
        
        result = save_to_db(chat_id)
        
        # Проверяем, что функция вернула False (ошибка)
        self.assertFalse(result)
        # Проверяем, что отправлено сообщение об ошибке
        self.mock_bot.send_message.assert_called_with(
            chat_id, 
            f"❌ Акт {act_number} уже существует."
        )
    
    @patch('src.RPRZBOT.sqlite3.connect')
    def test_save_to_db_general_exception(self, mock_connect):
        """Тест обработки общей ошибки при сохранении акта."""
        chat_id = 11002
        act_number = '456'
        user_act_number[chat_id] = act_number
        user_photos[chat_id] = ['photo1.jpg']
        
        # Настраиваем mock для имитации общей ошибки
        mock_conn = MagicMock()
        mock_connect.return_value = mock_conn
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value = mock_cursor
        mock_cursor.execute.side_effect = Exception("Общая ошибка")
        
        result = save_to_db(chat_id)
        
        # Проверяем, что функция вернула False (ошибка)
        self.assertFalse(result)
        # Проверяем, что отправлено сообщение об ошибке
        self.mock_bot.send_message.assert_called_with(
            chat_id, 
            "❌ Ошибка при сохранении акта."
        )
    
    @patch('src.RPRZBOT.sqlite3.connect')
    def test_act_photos_json_decode_error(self, mock_connect):
        """Тест обработки ошибки декодирования JSON при просмотре фотографий."""
        chat_id = 11003
        act_number = '789'
        message = create_mock_message(chat_id, text=act_number)
        
        # Настраиваем mock для возврата некорректного JSON
        mock_conn = MagicMock()
        mock_connect.return_value = mock_conn
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value = mock_cursor
        mock_cursor.fetchone.return_value = (1, chat_id, act_number, '{некорректный json}', '2023-01-01')
        
        act_photos(message)
        
        # Проверяем, что отправлено сообщение об ошибке
        self.mock_bot.send_message.assert_any_call(
            chat_id, 
            "❌ Ошибка при показе фото.", 
            reply_markup=back_markup
        )
    
    @patch('src.RPRZBOT.sqlite3.connect')
    def test_act_photos_file_not_found(self, mock_connect):
        """Тест обработки ошибки отсутствия файла при просмотре фотографий."""
        chat_id = 11004
        act_number = '101'
        message = create_mock_message(chat_id, text=act_number)
        
        # Настраиваем mock для возврата существующего акта
        mock_conn = MagicMock()
        mock_connect.return_value = mock_conn
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value = mock_cursor
        mock_cursor.fetchone.return_value = (1, chat_id, act_number, json.dumps(['несуществующий_файл.jpg']), '2023-01-01')
        
        # Патчим open для имитации ошибки отсутствия файла
        with patch('builtins.open', create=True) as mock_open:
            mock_open.side_effect = FileNotFoundError("Файл не найден")
            
            act_photos(message)
            
            # Проверяем, что отправлено сообщение о ненайденном файле
            self.mock_bot.send_message.assert_any_call(
                chat_id, 
                f"Не найден файл: несуществующий_файл.jpg"
            )
    
    @patch('src.RPRZBOT.sqlite3.connect')
    def test_view_acts_general_exception(self, mock_connect):
        """Тест обработки общей ошибки при просмотре актов."""
        chat_id = 11005
        message = create_mock_message(chat_id)
        
        # Настраиваем mock для имитации общей ошибки
        mock_connect.side_effect = Exception("Общая ошибка")
        
        view_acts(message)
        
        # Проверяем, что отправлено сообщение об ошибке
        self.mock_bot.send_message.assert_called_with(
            chat_id, 
            "Произошла ошибка при доступе к базе данных. Пожалуйста, попробуйте позже.", 
            reply_markup=back_markup
        )


class TestSpecialCases(unittest.TestCase):
    """Тесты для проверки специальных случаев."""
    
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
    
    def test_handle_text_with_empty_history(self):
        """Тест нажатия кнопки 'Назад' с пустой историей."""
        chat_id = 12001
        message = create_mock_message(chat_id, text='Назад')
        # Не инициализируем историю
        
        # Патчим start для проверки вызова
        with patch('src.RPRZBOT.start') as mock_start:
            
            handle_text(message)
            
            # Проверяем, что вызвана функция start
            mock_start.assert_called_once_with(message)
            # Проверяем, что история создана как пустой список
            self.assertEqual(user_history.get(chat_id), [])
    
    def test_handle_text_save_act_without_status(self):
        """Тест сохранения акта без установленного статуса."""
        chat_id = 12002
        message = create_mock_message(chat_id, text='✅Сохранить акт')
        # Не устанавливаем bot_status[chat_id]
        
        handle_text(message)
        
        # Проверяем, что отправлено сообщение о выборе из меню
        self.mock_bot.send_message.assert_called_with(chat_id, 'Выберите вариант из меню')
    
    @patch('src.RPRZBOT.sqlite3.connect')
    def test_act_photos_empty_result(self, mock_connect):
        """Тест просмотра фотографий для несуществующего акта."""
        chat_id = 12003
        act_number = '999'
        message = create_mock_message(chat_id, text=act_number)
        
        # Настраиваем mock для возврата пустого результата
        mock_conn = MagicMock()
        mock_connect.return_value = mock_conn
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value = mock_cursor
        mock_cursor.fetchone.return_value = None
        
        # Патчим view_acts для проверки вызова
        with patch('src.RPRZBOT.view_acts') as mock_view_acts:
            
            act_photos(message)
            
            # Проверяем, что отправлено сообщение о ненайденном акте
            self.mock_bot.send_message.assert_called_with(
                chat_id, 
                "Акт не найден.", 
                reply_markup=back_markup
            )
            # Проверяем, что вызвана функция view_acts
            mock_view_acts.assert_called_once_with(message)
    
    def test_act_photos_back_button(self):
        """Тест нажатия кнопки 'Назад' при просмотре фотографий."""
        chat_id = 12004
        message = create_mock_message(chat_id, text='Назад')
        
        # Патчим start для проверки вызова
        with patch('src.RPRZBOT.start') as mock_start:
            
            act_photos(message)
            
            # Проверяем, что вызвана функция start
            mock_start.assert_called_once_with(message)
            # Проверяем, что не было вызовов send_message
            self.mock_bot.send_message.assert_not_called()


if __name__ == '__main__':
    unittest.main()