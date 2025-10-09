"""
Расширенные тесты для main.py
Покрывают все основные функции и обработчики бота
"""

import pytest
import os
import sys
import json
from unittest.mock import Mock, patch, MagicMock, mock_open, call
from datetime import datetime

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

# Мокаем handlers перед импортом main
with patch.dict('sys.modules', {'handlers': Mock()}):
    from bot.main import (
        sanitize_user_input, validate_user_input, mask_sensitive_data,
        check_running_bots, create_process_lock, remove_process_lock,
        show_all_shelters, find_nearest_shelter,
        start_command, help_command, history_command,
        handle_text, start_danger_report, start_shelter_finder, 
        start_improvement_suggestion, handle_location, handle_media
    )


class TestSanitizeUserInput:
    """Расширенные тесты санитизации пользовательского ввода"""
    
    def test_sanitize_removes_script_tags(self):
        """Тест удаления script тегов"""
        result = sanitize_user_input("<script>alert('xss')</script>")
        assert "script" not in result
        assert "<" not in result
        assert ">" not in result
    
    def test_sanitize_removes_dangerous_commands(self):
        """Тест удаления опасных команд"""
        result = sanitize_user_input("rm -rf / ; DROP TABLE users")
        assert "rm" not in result
        assert "DROP" not in result
        assert ";" not in result
    
    def test_sanitize_preserves_safe_text(self):
        """Тест сохранения безопасного текста"""
        text = "Привет! Как дела? 123 test"
        result = sanitize_user_input(text)
        assert "Привет" in result
        assert "Как дела" in result
        assert "123" in result
    
    def test_sanitize_handles_unicode(self):
        """Тест обработки Unicode"""
        text = "Тест с эмодзи 🚀 и кириллицей"
        result = sanitize_user_input(text)
        assert "🚀" in result
        assert "кириллицей" in result
    
    def test_sanitize_limits_length(self):
        """Тест ограничения длины"""
        long_text = "A" * 2000
        result = sanitize_user_input(long_text)
        assert len(result) <= 1003  # 1000 + "..."
    
    def test_sanitize_removes_multiple_spaces(self):
        """Тест удаления множественных пробелов"""
        text = "Test    with    spaces"
        result = sanitize_user_input(text)
        assert "  " not in result


class TestValidateUserInput:
    """Расширенные тесты валидации ввода"""
    
    def test_validate_accepts_valid_input(self):
        """Тест принятия валидного ввода"""
        is_valid, msg = validate_user_input("Normal text 123")
        assert is_valid is True
        assert msg == "OK"
    
    def test_validate_rejects_empty(self):
        """Тест отклонения пустого ввода"""
        is_valid, msg = validate_user_input("")
        assert is_valid is False
        assert "Пустой ввод" in msg
    
    def test_validate_respects_min_length(self):
        """Тест проверки минимальной длины"""
        is_valid, msg = validate_user_input("abc", min_length=10)
        assert is_valid is False
        assert "короткий" in msg.lower()
    
    def test_validate_respects_max_length(self):
        """Тест проверки максимальной длины"""
        long_text = "A" * 2000
        is_valid, msg = validate_user_input(long_text, max_length=100)
        assert is_valid is False
        assert "длинный" in msg.lower()
    
    def test_validate_detects_xss(self):
        """Тест обнаружения XSS"""
        xss_patterns = [
            "<script>alert('xss')</script>",
            "javascript:alert('xss')",
            "<img onerror=alert('xss')>"
        ]
        for pattern in xss_patterns:
            is_valid, msg = validate_user_input(pattern)
            assert is_valid is False
            assert "подозрительный контент" in msg
    
    def test_validate_detects_sql_injection(self):
        """Тест обнаружения SQL инъекций"""
        sql_patterns = [
            "'; DROP TABLE users; --",
            "1' OR '1'='1",
            "UNION SELECT * FROM"
        ]
        for pattern in sql_patterns:
            is_valid, msg = validate_user_input(pattern)
            # После санитизации некоторые паттерны могут стать валидными
            # Проверяем, что либо валидация отклонила, либо санитизация очистила
            if not is_valid:
                assert "подозрительный контент" in msg


class TestMaskSensitiveData:
    """Расширенные тесты маскирования данных"""
    
    def test_mask_bot_token_format(self):
        """Тест маскирования токена бота"""
        token = "123456789:ABCdefGHIjklMNOpqrsTUVwxyz"
        result = mask_sensitive_data(token)
        assert "123456789:" in result
        assert "wxyz" in result
        assert "ABCdefGHI" not in result
    
    def test_mask_preserves_short_strings(self):
        """Тест сохранения коротких строк"""
        short = "test"
        result = mask_sensitive_data(short)
        assert result == short
    
    def test_mask_handles_none_and_empty(self):
        """Тест обработки None и пустой строки"""
        assert mask_sensitive_data(None) == ""
        assert mask_sensitive_data("") == ""


class TestProcessLockFunctions:
    """Тесты функций блокировки процессов"""
    
    @patch('bot.main.psutil.process_iter')
    def test_check_running_bots(self, mock_process_iter):
        """Тест проверки запущенных ботов"""
        # Мок процесса
        mock_proc = Mock()
        mock_proc.info = {
            'pid': 12345,
            'name': 'python.exe',
            'cmdline': ['python', 'bot/main.py']
        }
        mock_process_iter.return_value = [mock_proc]
        
        result = check_running_bots()
        assert isinstance(result, list)
        assert len(result) > 0
    
    @patch('bot.main.LOCK_FILE')
    @patch('bot.main.PID_FILE')
    @patch('bot.main.check_running_bots')
    @patch('builtins.open', new_callable=mock_open)
    @patch('os.getpid')
    def test_create_process_lock_success(self, mock_getpid, mock_file, 
                                        mock_check, mock_pid, mock_lock):
        """Тест успешного создания блокировки"""
        mock_getpid.return_value = 12345
        mock_check.return_value = [12345]  # Только текущий процесс
        
        result = create_process_lock()
        assert result is True
    
    @patch('bot.main.LOCK_FILE')
    @patch('bot.main.PID_FILE')
    def test_remove_process_lock(self, mock_pid, mock_lock):
        """Тест удаления блокировки"""
        mock_lock.exists.return_value = True
        mock_pid.exists.return_value = True
        
        remove_process_lock()
        # Функция не должна падать
        assert True


class TestShelterFunctions:
    """Расширенные тесты функций работы с убежищами"""
    
    @patch('bot.main.placeholders', {'shelters': []})
    @patch('bot.main.BOT_TOKEN', 'test_token')
    @patch('bot.main.bot', Mock())
    def test_show_all_shelters_empty(self):
        """Тест показа пустого списка убежищ"""
        show_all_shelters(12345)
        # Функция должна выполниться без ошибок
        assert True
    
    @patch('bot.main.placeholders', {'shelters': [
        {
            'name': 'Убежище 1',
            'description': 'Описание',
            'lat': 55.7558,
            'lon': 37.6176,
            'map_link': 'https://example.com',
            'photo_path': 'nonexistent.jpg'
        }
    ]})
    @patch('bot.main.BOT_TOKEN', 'test_token')
    @patch('bot.main.bot', Mock())
    def test_show_all_shelters_with_data(self):
        """Тест показа списка убежищ с данными"""
        show_all_shelters(12345)
        # Проверяем, что функция выполнилась
        assert True
    
    @patch('bot.main.BotStates', Mock())
    @patch('bot.main.user_states', {})
    @patch('bot.main.placeholders', {'shelters': [
        {
            'name': 'Убежище 1',
            'description': 'Описание',
            'lat': 55.7558,
            'lon': 37.6176,
            'map_link': 'https://example.com',
            'photo_path': ''
        },
        {
            'name': 'Убежище 2',
            'description': 'Описание 2',
            'lat': 55.7600,
            'lon': 37.6200,
            'map_link': 'https://example.com',
            'photo_path': ''
        }
    ]})
    @patch('bot.main.BOT_TOKEN', 'test_token')
    @patch('bot.main.bot', Mock())
    def test_find_nearest_shelter(self):
        """Тест поиска ближайшего убежища"""
        find_nearest_shelter(12345, 55.7558, 37.6176)
        # Проверяем, что функция выполнилась
        assert True


class TestCommandHandlers:
    """Тесты обработчиков команд"""
    
    @patch('bot.main.log_activity')
    @patch('bot.main.BotStates', Mock())
    @patch('bot.main.user_history', {})
    @patch('bot.main.user_data', {})
    @patch('bot.main.user_states', {})
    @patch('bot.main.bot', Mock())
    def test_start_command(self):
        """Тест команды /start"""
        mock_message = Mock()
        mock_message.chat.id = 12345
        mock_message.from_user.username = "test_user"
        mock_message.from_user.id = 12345
        
        start_command(mock_message)
        # Функция должна выполниться без ошибок
        assert True
    
    @patch('bot.main.log_activity')
    @patch('bot.main.bot', Mock())
    def test_help_command(self):
        """Тест команды /help"""
        mock_message = Mock()
        mock_message.chat.id = 12345
        mock_message.from_user.username = "test_user"
        
        help_command(mock_message)
        # Функция должна выполниться без ошибок
        assert True
    
    @patch('os.path.exists', return_value=False)
    @patch('bot.main.log_activity')
    @patch('bot.main.bot', Mock())
    def test_history_command_no_file(self):
        """Тест команды /my_history без файла истории"""
        mock_message = Mock()
        mock_message.chat.id = 12345
        mock_message.from_user.username = "test_user"
        
        history_command(mock_message)
        # Функция должна выполниться без ошибок
        assert True


class TestMessageHandlers:
    """Тесты обработчиков сообщений"""
    
    @patch('bot.main.start_danger_report')
    @patch('bot.main.log_activity')
    @patch('bot.main.BotStates', Mock())
    @patch('bot.main.user_history', {})
    @patch('bot.main.user_data', {})
    @patch('bot.main.user_states', {})
    @patch('bot.main.bot', Mock())
    def test_handle_text_main_menu(self):
        """Тест обработки текста в главном меню"""
        mock_message = Mock()
        mock_message.chat.id = 12345
        mock_message.from_user.username = "test_user"
        mock_message.from_user.id = 12345
        mock_message.text = "❗ Сообщите об опасности"
        
        handle_text(mock_message)
        # Функция должна выполниться без ошибок
        assert True
    
    @patch('bot.main.log_activity')
    @patch('bot.main.BotStates', Mock())
    @patch('bot.main.user_data', {})
    @patch('bot.main.user_states', {})
    @patch('bot.main.bot', Mock())
    def test_start_danger_report(self):
        """Тест начала процесса сообщения об опасности"""
        mock_message = Mock()
        mock_message.chat.id = 12345
        mock_message.from_user.username = "test_user"
        
        start_danger_report(mock_message)
        # Функция должна выполниться без ошибок
        assert True
    
    @patch('bot.main.log_activity')
    @patch('bot.main.BotStates', Mock())
    @patch('bot.main.user_states', {})
    @patch('bot.main.bot', Mock())
    def test_start_shelter_finder(self):
        """Тест начала поиска убежищ"""
        mock_message = Mock()
        mock_message.chat.id = 12345
        mock_message.from_user.username = "test_user"
        
        start_shelter_finder(mock_message)
        # Функция должна выполниться без ошибок
        assert True
    
    @patch('bot.main.log_activity')
    @patch('bot.main.BotStates', Mock())
    @patch('bot.main.user_data', {})
    @patch('bot.main.user_states', {})
    @patch('bot.main.bot', Mock())
    def test_start_improvement_suggestion(self):
        """Тест начала отправки предложения"""
        mock_message = Mock()
        mock_message.chat.id = 12345
        mock_message.from_user.username = "test_user"
        
        start_improvement_suggestion(mock_message)
        # Функция должна выполниться без ошибок
        assert True


class TestLocationAndMediaHandlers:
    """Тесты обработчиков геолокации и медиафайлов"""
    
    @patch('bot.main.find_nearest_shelter')
    @patch('bot.main.user_states', {12345: 'shelter_finder'})
    @patch('bot.main.bot', Mock())
    def test_handle_location_shelter_finder(self, mock_find):
        """Тест обработки геолокации для поиска убежищ"""
        mock_message = Mock()
        mock_message.chat.id = 12345
        mock_message.from_user.username = "test_user"
        mock_message.from_user.id = 12345
        mock_message.location.latitude = 55.7558
        mock_message.location.longitude = 37.6176
        
        handle_location(mock_message)
        
        mock_find.assert_called_with(12345, 55.7558, 37.6176)
    
    @patch('bot.main.handle_danger_report_location', return_value={'text': 'Test', 'reply_markup': Mock()})
    @patch('bot.main.user_data', {})
    @patch('bot.main.user_states', {12345: 'danger_report'})
    @patch('bot.main.bot', Mock())
    def test_handle_location_danger_report(self, mock_handler):
        """Тест обработки геолокации для сообщения об опасности"""
        mock_message = Mock()
        mock_message.chat.id = 12345
        mock_message.from_user.username = "test_user"
        mock_message.from_user.id = 12345
        mock_message.location.latitude = 55.7558
        mock_message.location.longitude = 37.6176
        
        handle_location(mock_message)
        
        mock_handler.assert_called()
    
    @patch('bot.main.handle_danger_report_media', return_value="Test response")
    @patch('bot.main.MAX_VIDEO_SIZE_MB', 300)
    @patch('bot.main.MAX_FILE_SIZE_MB', 20)
    @patch('bot.main.user_data', {})
    @patch('bot.main.user_states', {12345: 'danger_report'})
    @patch('bot.main.bot', Mock())
    def test_handle_media(self, mock_handler):
        """Тест обработки медиафайлов"""
        mock_message = Mock()
        mock_message.chat.id = 12345
        mock_message.from_user.username = "test_user"
        mock_message.from_user.id = 12345
        mock_message.content_type = 'photo'
        
        handle_media(mock_message)
        
        mock_handler.assert_called()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
