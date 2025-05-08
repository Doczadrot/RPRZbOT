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


class TestPhotoHandling(unittest.TestCase):
    """Тесты для проверки обработки фотографий."""
    
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
        
        # Создаем временную директорию для тестов
        self.test_photos_dir = 'test_photos'
        os.makedirs(self.test_photos_dir, exist_ok=True)
    
    def tearDown(self):
        """Остановка патчей и удаление временных файлов после каждого теста."""
        self.patcher_bot.stop()
        # Удаляем временную директорию
        if os.path.exists(self.test_photos_dir):
            for file in os.listdir(self.test_photos_dir):
                os.remove(os.path.join(self.test_photos_dir, file))
            os.rmdir(self.test_photos_dir)
    
    @patch('src.RPRZBOT.os.makedirs')
    def test_handle_photo_first_photo(self, mock_makedirs):
        """Тест обработки первой фотографии."""
        chat_id = 9001
        message = create_mock_message(chat_id, photo=True)
        bot_status[chat_id] = 'ожидание фото'
        user_act_number[chat_id] = '123'
        user_photos[chat_id] = []
        
        # Патчим open для имитации записи файла
        with patch('builtins.open', create=True) as mock_open:
            mock_file = MagicMock()
            mock_open.return_value.__enter__.return_value = mock_file
            
            handle_photo(message)
            
            # Проверяем, что была создана директория
            mock_makedirs.assert_called_with(f"photos/{chat_id}", exist_ok=True)
            # Проверяем, что файл был открыт для записи
            mock_open.assert_called_once()
            # Проверяем, что в файл были записаны данные
            mock_file.write.assert_called_once_with(b'fake_file_content')
            # Проверяем, что путь к фото добавлен в список
            self.assertEqual(len(user_photos[chat_id]), 1)
            # Проверяем, что отправлено сообщение о принятии фото
            self.mock_bot.send_message.assert_called_with(
                chat_id, 
                'Фото 1 принято ✅. Можно добавить ещё 2 или сохранить акт.', 
                reply_markup=photo_choice_markup
            )
    
    @patch('src.RPRZBOT.os.makedirs')
    def test_handle_photo_third_photo_auto_save(self, mock_makedirs):
        """Тест автоматического сохранения после загрузки третьего фото."""
        chat_id = 9002
        message = create_mock_message(chat_id, photo=True)
        bot_status[chat_id] = 'ожидание фото'
        user_act_number[chat_id] = '456'
        user_photos[chat_id] = ['photo1.jpg', 'photo2.jpg']
        
        # Патчим open и save_to_db
        with patch('builtins.open', create=True) as mock_open, \
             patch('src.RPRZBOT.save_to_db', return_value=True) as mock_save_to_db, \
             patch('src.RPRZBOT.start') as mock_start:
            
            mock_file = MagicMock()
            mock_open.return_value.__enter__.return_value = mock_file
            
            handle_photo(message)
            
            # Проверяем, что была создана директория
            mock_makedirs.assert_called_with(f"photos/{chat_id}", exist_ok=True)
            # Проверяем, что файл был открыт для записи
            mock_open.assert_called_once()
            # Проверяем, что в файл были записаны данные
            mock_file.write.assert_called_once_with(b'fake_file_content')
            # Проверяем, что путь к фото добавлен в список
            self.assertEqual(len(user_photos[chat_id]), 3)
            # Проверяем, что отправлено сообщение о загрузке 3 фото
            self.mock_bot.send_message.assert_called_with(
                chat_id, 
                '✅ Загружено 3 фото. Сохраняю акт...', 
                reply_markup=types.ReplyKeyboardRemove()
            )
            # Проверяем, что вызвана функция save_to_db
            mock_save_to_db.assert_called_once_with(chat_id)
            # Проверяем, что вызвана функция start
            mock_start.assert_called_once_with(message)
    
    def test_handle_photo_without_status(self):
        """Тест обработки фото без установленного статуса."""
        chat_id = 9003
        message = create_mock_message(chat_id, photo=True)
        # Не устанавливаем bot_status[chat_id]
        
        handle_photo(message)
        
        # Проверяем, что отправлено сообщение о необходимости начать регистрацию
        self.mock_bot.send_message.assert_called_with(
            chat_id, 
            'Сначала начните регистрацию акта (/start).'
        )
    
    @patch('src.RPRZBOT.bot.get_file')
    def test_handle_photo_download_error(self, mock_get_file):
        """Тест обработки ошибки при скачивании фото."""
        chat_id = 9004
        message = create_mock_message(chat_id, photo=True)
        bot_status[chat_id] = 'ожидание фото'
        user_act_number[chat_id] = '789'
        user_photos[chat_id] = []
        
        # Имитируем ошибку при получении информации о файле
        mock_get_file.side_effect = Exception("Ошибка получения файла")
        
        handle_photo(message)
        
        # Проверяем, что отправлено сообщение об ошибке
        self.mock_bot.send_message.assert_called_with(
            chat_id, 
            'Что-то пошло не так при загрузке фото.', 
            reply_markup=back_markup
        )
        # Проверяем, что список фото не изменился
        self.assertEqual(user_photos[chat_id], [])


class TestUserInteractionAdvanced(unittest.TestCase):
    """Расширенные тесты взаимодействия с пользователем."""
    
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
    
    def test_handle_text_save_act_without_photos(self):
        """Тест сохранения акта без загруженных фотографий."""
        chat_id = 10001
        message = create_mock_message(chat_id, text='✅Сохранить акт')
        bot_status[chat_id] = 'ожидание фото'
        user_act_number[chat_id] = '123'
        # Не добавляем фотографии
        user_photos[chat_id] = []
        
        handle_text(message)
        
        # Проверяем, что отправлено сообщение о необходимости загрузить фото
        self.mock_bot.send_message.assert_called_with(
            chat_id, 
            'Вы ещё не загрузили фото. Пожалуйста, загрузите хотя бы одно фото.', 
            reply_markup=photo_choice_markup
        )
    
    def test_handle_text_save_act_with_photos_success(self):
        """Тест успешного сохранения акта с фотографиями."""
        chat_id = 10002
        message = create_mock_message(chat_id, text='✅Сохранить акт')
        bot_status[chat_id] = 'ожидание фото'
        user_act_number[chat_id] = '456'
        user_photos[chat_id] = ['photo1.jpg']
        
        # Патчим save_to_db для успешного сохранения
        with patch('src.RPRZBOT.save_to_db', return_value=True) as mock_save_to_db, \
             patch('src.RPRZBOT.start') as mock_start:
            
            handle_text(message)
            
            # Проверяем, что вызвана функция save_to_db
            mock_save_to_db.assert_called_once_with(chat_id)
            # Проверяем, что отправлено сообщение об успешном сохранении
            self.mock_bot.send_message.assert_called_with(
                chat_id, 
                '✅ Акт сохранён. Возвращаюсь в главное меню.', 
                reply_markup=types.ReplyKeyboardRemove()
            )
            # Проверяем, что вызвана функция start
            mock_start.assert_called_once_with(message)
    
    def test_handle_text_save_act_with_photos_failure(self):
        """Тест неудачного сохранения акта с фотографиями."""
        chat_id = 10003
        message = create_mock_message(chat_id, text='✅Сохранить акт')
        bot_status[chat_id] = 'ожидание фото'
        user_act_number[chat_id] = '789'
        user_photos[chat_id] = ['photo1.jpg']
        
        # Патчим save_to_db для неудачного сохранения
        with patch('src.RPRZBOT.save_to_db', return_value=False) as mock_save_to_db:
            
            handle_text(message)
            
            # Проверяем, что вызвана функция save_to_db
            mock_save_to_db.assert_called_once_with(chat_id)
            # Проверяем, что отправлено сообщение о неудачном сохранении
            self.mock_bot.send_message.assert_called_with(
                chat_id, 
                '❌ Не удалось сохранить. Попробуйте ещё раз или измените фото.', 
                reply_markup=photo_choice_markup
            )
    
    def test_process_act_number_duplicate(self):
        """Тест ввода дублирующегося номера акта."""
        chat_id1 = 10004
        chat_id2 = 10005
        act_number = '123'
        
        # Сначала регистрируем акт для первого пользователя
        user_act_number[chat_id1] = act_number
        
        # Теперь пытаемся зарегистрировать такой же номер для второго пользователя
        message = create_mock_message(chat_id2, text=act_number)
        
        process_act_number(message)
        
        # Проверяем, что отправлено сообщение о дублировании номера
        self.mock_bot.send_message.assert_called_with(
            chat_id2, 
            'Этот номер уже вводился. Введите другой:', 
            reply_markup=back_markup
        )
        # Проверяем, что зарегистрирован обработчик следующего шага
        self.mock_bot.register_next_step_handler.assert_called_once_with(message, process_act_number)
    
    def test_process_act_number_back_button(self):
        """Тест нажатия кнопки 'Назад' при вводе номера акта."""
        chat_id = 10006
        message = create_mock_message(chat_id, text='Назад')
        
        # Патчим start для проверки вызова
        with patch('src.RPRZBOT.start') as mock_start:
            
            process_act_number(message)
            
            # Проверяем, что вызвана функция start
            mock_start.assert_called_once_with(message)
            # Проверяем, что не было вызовов send_message
            self.mock_bot.send_message.assert_not_called()


if __name__ == '__main__':
    unittest.main()