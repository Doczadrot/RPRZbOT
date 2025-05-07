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


class TestDatabaseOperations(unittest.TestCase):
    """Тесты для проверки операций с базой данных."""
    
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
        self.mock_bot.send_photo = MagicMock()
        self.mock_bot.token = 'fake_token'
        # Патчим глобальный объект bot
        self.patcher_bot = patch('src.RPRZBOT.bot', self.mock_bot)
        self.patcher_bot.start()
        
        # Создаем временную тестовую базу данных
        self.test_db_path = 'test_acts_temp.db'
        self.conn = sqlite3.connect(self.test_db_path)
        self.cursor = self.conn.cursor()
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS acts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                chat_id INTEGER,
                act_number TEXT UNIQUE,
                photo_urls TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        self.conn.commit()
        
        # Патчим функцию connect для использования тестовой БД
        self.patcher_connect = patch('src.RPRZBOT.sqlite3.connect', return_value=self.conn)
        self.patcher_connect.start()
    
    def tearDown(self):
        """Остановка патчей и удаление тестовой БД после каждого теста."""
        self.patcher_bot.stop()
        self.patcher_connect.stop()
        self.conn.close()
        if os.path.exists(self.test_db_path):
            os.remove(self.test_db_path)
    
    def test_init_db(self):
        """Тест инициализации базы данных."""
        # Патчим connect, чтобы проверить создание таблицы
        with patch('src.RPRZBOT.sqlite3.connect') as mock_connect:
            mock_conn = MagicMock()
            mock_connect.return_value = mock_conn
            mock_cursor = MagicMock()
            mock_conn.cursor.return_value = mock_cursor
            
            init_db()
            
            # Проверяем, что был вызван execute с SQL для создания таблицы
            mock_cursor.execute.assert_called_once()
            # Проверяем, что был вызван commit
            mock_conn.commit.assert_called_once()
            # Проверяем, что соединение было закрыто
            mock_conn.close.assert_called_once()
    
    def test_save_to_db_success(self):
        """Тест успешного сохранения акта в базу данных."""
        chat_id = 7001
        act_number = '456'
        user_act_number[chat_id] = act_number
        user_photos[chat_id] = ['photo1.jpg', 'photo2.jpg']
        
        result = save_to_db(chat_id)
        
        # Проверяем, что функция вернула True (успех)
        self.assertTrue(result)
        
        # Проверяем, что данные сохранены в БД
        self.cursor.execute("SELECT act_number, photo_urls FROM acts WHERE chat_id = ?", (chat_id,))
        row = self.cursor.fetchone()
        self.assertIsNotNone(row)
        self.assertEqual(row[0], act_number)
        self.assertEqual(json.loads(row[1]), ['photo1.jpg', 'photo2.jpg'])
        
        # Проверяем, что данные пользователя очищены
        self.assertNotIn(chat_id, user_act_number)
        self.assertNotIn(chat_id, user_photos)
        self.assertNotIn(chat_id, bot_status)
    
    def test_save_to_db_no_act_number(self):
        """Тест сохранения без номера акта."""
        chat_id = 7002
        # Не устанавливаем user_act_number[chat_id]
        user_photos[chat_id] = ['photo1.jpg']
        
        result = save_to_db(chat_id)
        
        # Проверяем, что функция вернула False (ошибка)
        self.assertFalse(result)
    
    def test_save_to_db_no_photos(self):
        """Тест сохранения без фотографий."""
        chat_id = 7003
        user_act_number[chat_id] = '789'
        # Не устанавливаем user_photos[chat_id]
        
        result = save_to_db(chat_id)
        
        # Проверяем, что функция вернула False (ошибка)
        self.assertFalse(result)
    
    def test_view_acts_no_acts(self):
        """Тест просмотра актов, когда у пользователя нет актов."""
        chat_id = 7004
        message = create_mock_message(chat_id)
        
        view_acts(message)
        
        # Проверяем, что отправлено сообщение об отсутствии актов
        self.mock_bot.send_message.assert_called_with(
            chat_id, 
            "У вас пока нет сохранённых актов.", 
            reply_markup=back_markup
        )
    
    def test_view_acts_with_acts(self):
        """Тест просмотра актов, когда у пользователя есть акты."""
        chat_id = 7005
        message = create_mock_message(chat_id)
        
        # Добавляем акты в БД
        self.cursor.execute(
            "INSERT INTO acts (chat_id, act_number, photo_urls) VALUES (?, ?, ?)",
            (chat_id, '111', json.dumps(['photo1.jpg']))
        )
        self.cursor.execute(
            "INSERT INTO acts (chat_id, act_number, photo_urls) VALUES (?, ?, ?)",
            (chat_id, '222', json.dumps(['photo2.jpg']))
        )
        self.conn.commit()
        
        view_acts(message)
        
        # Проверяем, что отправлено сообщение с выбором актов
        self.mock_bot.send_message.assert_called_with(
            chat_id, 
            "Выберите номер акта:", 
            reply_markup=self.mock_bot.send_message.call_args[1]['reply_markup']
        )
        # Проверяем, что зарегистрирован обработчик следующего шага
        self.mock_bot.register_next_step_handler.assert_called_once_with(message, act_photos)
    
    def test_act_photos_not_found(self):
        """Тест просмотра фотографий для несуществующего акта."""
        chat_id = 7006
        act_number = '999'
        message = create_mock_message(chat_id, text=act_number)
        
        act_photos(message)
        
        # Проверяем, что отправлено сообщение о ненайденном акте
        self.mock_bot.send_message.assert_called_with(
            chat_id, 
            "Акт не найден.", 
            reply_markup=back_markup
        )
    
    def test_act_photos_with_photos(self):
        """Тест просмотра фотографий для акта с фотографиями."""
        chat_id = 7007
        act_number = '333'
        message = create_mock_message(chat_id, text=act_number)
        
        # Создаем временные файлы для тестирования
        os.makedirs(f"photos/{chat_id}", exist_ok=True)
        test_photo1 = f"photos/{chat_id}/act_{act_number}_1.jpg"
        test_photo2 = f"photos/{chat_id}/act_{act_number}_2.jpg"
        
        # Создаем пустые файлы
        with open(test_photo1, 'wb') as f:
            f.write(b'test_photo_content')
        with open(test_photo2, 'wb') as f:
            f.write(b'test_photo_content')
        
        # Добавляем акт в БД
        self.cursor.execute(
            "INSERT INTO acts (chat_id, act_number, photo_urls) VALUES (?, ?, ?)",
            (chat_id, act_number, json.dumps([test_photo1, test_photo2]))
        )
        self.conn.commit()
        
        # Патчим open для имитации открытия файлов
        with patch('builtins.open', create=True) as mock_open:
            mock_open.return_value.__enter__.return_value = MagicMock()
            
            act_photos(message)
            
            # Проверяем, что отправлено сообщение с фотографиями
            self.mock_bot.send_message.assert_any_call(
                chat_id, 
                f"Фотографии для акта №{act_number}:"
            )
            # Проверяем, что вызван send_photo для каждой фотографии
            self.assertEqual(self.mock_bot.send_photo.call_count, 2)
        
        # Удаляем временные файлы
        if os.path.exists(test_photo1):
            os.remove(test_photo1)
        if os.path.exists(test_photo2):
            os.remove(test_photo2)
        if os.path.exists(f"photos/{chat_id}"):
            os.rmdir(f"photos/{chat_id}")
        if os.path.exists("photos"):
            os.rmdir("photos")


class TestHelpAndMenuFunctions(unittest.TestCase):
    """Тесты для проверки функций справки и меню."""
    
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
    
    def test_send_help(self):
        """Тест отправки справки."""
        chat_id = 8001
        message = create_mock_message(chat_id)
        
        # Патчим start для проверки вызова
        with patch('src.RPRZBOT.start') as mock_start:
            send_help(message)
            
            # Проверяем, что отправлено сообщение со справкой
            self.mock_bot.send_message.assert_called_once()
            # Проверяем, что вызвана функция start
            mock_start.assert_called_once_with(message)
    
    def test_start_function(self):
        """Тест функции start (главное меню)."""
        chat_id = 8002
        message = create_mock_message(chat_id)
        
        start(message)
        
        # Проверяем, что установлено состояние главного меню
        self.assertEqual(bot_status_state.get(chat_id), 'main_menu')
        # Проверяем, что история очищена
        self.assertEqual(user_history.get(chat_id), [])
        # Проверяем, что отправлено приветственное сообщение
        self.mock_bot.send_message.assert_called_once()
    
    def test_handle_text_menu_options(self):
        """Тест обработки различных пунктов меню."""
        chat_id = 8003
        
        # Тест пункта 'Поиск'
        message1 = create_mock_message(chat_id, text='📋Поиск')
        handle_text(message1)
        self.mock_bot.send_message.assert_called_with(
            chat_id, 
            'Эта функция в разработке'
        )
        self.mock_bot.send_message.reset_mock()
        
        # Тест пункта 'Нейропомощник РПРЗ'
        message2 = create_mock_message(chat_id, text='🤖Нейропомощник РПРЗ')
        handle_text(message2)
        self.mock_bot.send_message.assert_called_with(
            chat_id, 
            'Эта функция в разработке'
        )
        self.mock_bot.send_message.reset_mock()
        
        # Тест неизвестного пункта меню
        message3 = create_mock_message(chat_id, text='Неизвестный пункт')
        handle_text(message3)
        self.mock_bot.send_message.assert_called_with(
            chat_id, 
            'Выберите вариант из меню'
        )


if __name__ == '__main__':
    unittest.main()