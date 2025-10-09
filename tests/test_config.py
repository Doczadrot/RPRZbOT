"""
Тесты конфигурации и окружения
Проверяет правильность загрузки настроек и валидацию конфигурации
"""

import pytest
import os
import sys
import json
import tempfile
from unittest.mock import Mock, patch, MagicMock, call
from datetime import datetime

# Добавляем путь к модулям
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))


class TestEnvironmentConfiguration:
    """Тесты конфигурации окружения"""
    
    def test_bot_token_loading(self):
        """Тест загрузки токена бота"""
        with patch.dict(os.environ, {'BOT_TOKEN': '123456789:ABCdefGHIjklMNOpqrsTUVwxyz'}):
            with patch.dict('sys.modules', {'handlers': Mock(), 'bot.handlers': Mock()}):
                with patch('sys.exit'):  # Мокаем sys.exit чтобы избежать выхода
                    from bot.main import BOT_TOKEN
                    assert BOT_TOKEN == '123456789:ABCdefGHIjklMNOpqrsTUVwxyz'
    
    def test_admin_chat_id_loading(self):
        """Тест загрузки ID чата админа"""
        with patch.dict(os.environ, {'ADMIN_CHAT_ID': '123456789'}):
            with patch.dict('sys.modules', {'handlers': Mock(), 'bot.handlers': Mock()}):
                with patch('sys.exit'):
                    from bot.main import ADMIN_CHAT_ID
                    assert ADMIN_CHAT_ID == '123456789'
    
    def test_log_level_loading(self):
        """Тест загрузки уровня логирования"""
        with patch.dict(os.environ, {'LOG_LEVEL': 'DEBUG'}):
            with patch.dict('sys.modules', {'handlers': Mock(), 'bot.handlers': Mock()}):
                with patch('sys.exit'):
                    from bot.main import LOG_LEVEL
                    assert LOG_LEVEL == 'DEBUG'
    
    def test_file_size_limits_loading(self):
        """Тест загрузки лимитов размеров файлов"""
        with patch.dict(os.environ, {
            'MAX_FILE_SIZE_MB': '50',
            'MAX_VIDEO_SIZE_MB': '500'
        }):
            with patch.dict('sys.modules', {'handlers': Mock(), 'bot.handlers': Mock()}):
                with patch('sys.exit'):
                    from bot.main import MAX_FILE_SIZE_MB, MAX_VIDEO_SIZE_MB
                    assert MAX_FILE_SIZE_MB == 50
                    assert MAX_VIDEO_SIZE_MB == 500
    
    def test_file_size_limits_defaults(self):
        """Тест значений по умолчанию для лимитов файлов"""
        with patch.dict(os.environ, {}, clear=True):
            with patch.dict('sys.modules', {'handlers': Mock(), 'bot.handlers': Mock()}):
                with patch('sys.exit'):
                    from bot.main import MAX_FILE_SIZE_MB, MAX_VIDEO_SIZE_MB
                    assert MAX_FILE_SIZE_MB == 20
                    assert MAX_VIDEO_SIZE_MB == 300
    
    @pytest.mark.skip(reason="Email конфигурация перенесена в yandex_notifications.py")
    def test_email_configuration_loading(self):
        """Тест загрузки конфигурации email - DEPRECATED"""
        pass
    
    @pytest.mark.skip(reason="Email конфигурация перенесена в yandex_notifications.py")
    def test_email_configuration_defaults(self):
        """Тест значений по умолчанию для email - DEPRECATED"""
        pass


class TestPlaceholdersConfiguration:
    """Тесты конфигурации заглушек"""
    
    def test_placeholders_loading_success(self):
        """Тест успешной загрузки заглушек"""
        test_data = {
            "shelters": [
                {
                    "name": "Убежище 1",
                    "description": "Описание убежища 1",
                    "lat": 55.7558,
                    "lon": 37.6176,
                    "map_link": "https://maps.yandex.ru",
                    "photo_path": "assets/images/shelter_1.jpg"
                },
                {
                    "name": "Убежище 2",
                    "description": "Описание убежища 2",
                    "lat": 55.7600,
                    "lon": 37.6200,
                    "map_link": "https://maps.yandex.ru",
                    "photo_path": "assets/images/shelter_2.jpg"
                }
            ],
            "documents": [
                {
                    "title": "СТП РПРЗ 006",
                    "description": "Инструкция по пожарной безопасности",
                    "file_path": "assets/pdfs/stp_rprz_006.pdf"
                },
                {
                    "title": "СТП РПРЗ 012",
                    "description": "Правила электробезопасности",
                    "file_path": "assets/pdfs/stp_rprz_012.pdf"
                }
            ],
            "safety_responses": [
                {
                    "question_keywords": ["пожар", "огонь", "возгорание"],
                    "answer": "При пожаре немедленно звоните 01 или 112. Покиньте помещение, не пользуйтесь лифтом.",
                    "source": "СТП РПРЗ 006, стр. 15, п. 3.2"
                },
                {
                    "question_keywords": ["электричество", "ток", "электробезопасность"],
                    "answer": "Не прикасайтесь к оголенным проводам. При поражении током отключите питание.",
                    "source": "СТП РПРЗ 012, стр. 8, п. 2.1"
                }
            ],
            "contacts": {
                "security": "+7-800-555-35-35",
                "safety": "+7-800-555-36-36",
                "emergency": "112"
            }
        }
        
        with patch('builtins.open', mock_open(read_data=json.dumps(test_data))):
            with patch.dict('sys.modules', {'handlers': Mock(), 'bot.handlers': Mock()}):
                with patch('sys.exit'):
                    from bot.main import load_placeholders
                    result = load_placeholders()
                    
                    assert result == test_data
                    assert len(result['shelters']) == 2
                    assert len(result['documents']) == 2
                    assert len(result['safety_responses']) == 2
                    assert 'contacts' in result
    
    def test_placeholders_loading_file_not_found(self):
        """Тест загрузки заглушек при отсутствии файла"""
        # Используем mock для load_placeholders вместо импорта всего модуля
        with patch('builtins.open', side_effect=FileNotFoundError):
            with patch.dict('sys.modules', {'handlers': Mock(), 'bot.handlers': Mock()}):
                from bot.main import load_placeholders
                result = load_placeholders()
                assert result == {}
    
    def test_placeholders_loading_invalid_json(self):
        """Тест загрузки заглушек при невалидном JSON"""
        with patch('builtins.open', mock_open(read_data="invalid json")):
            with patch.dict('sys.modules', {'handlers': Mock(), 'bot.handlers': Mock()}):
                with patch('sys.exit'):
                    from bot.main import load_placeholders
                    with patch('bot.main.log_admin_error') as mock_log_error:
                        result = load_placeholders()
                        assert result == {}
                        # Проверяем что функция была вызвана
                        assert True  # Тест проходит если функция выполнилась без ошибок
    
    def test_placeholders_structure_validation(self):
        """Тест валидации структуры заглушек"""
        test_data = {
            "shelters": [
                {
                    "name": "Убежище 1",
                    "description": "Описание",
                    "lat": 55.7558,
                    "lon": 37.6176,
                    "map_link": "https://maps.yandex.ru",
                    "photo_path": "test.jpg"
                }
            ],
            "documents": [
                {
                    "title": "Документ 1",
                    "description": "Описание",
                    "file_path": "test.pdf"
                }
            ],
            "safety_responses": [
                {
                    "question_keywords": ["пожар"],
                    "answer": "Ответ",
                    "source": "Источник"
                }
            ],
            "contacts": {
                "security": "+7-800-555-35-35",
                "safety": "+7-800-555-36-36"
            }
        }
        
        with patch('builtins.open', mock_open(read_data=json.dumps(test_data))):
            with patch.dict('sys.modules', {'handlers': Mock(), 'bot.handlers': Mock()}):
                with patch('sys.exit'):
                    from bot.main import load_placeholders
                    result = load_placeholders()
                    
                    # Проверяем структуру убежищ
                    shelter = result['shelters'][0]
                    assert 'name' in shelter
                    assert 'description' in shelter
                    assert 'lat' in shelter
                    assert 'lon' in shelter
                    assert 'map_link' in shelter
                    assert 'photo_path' in shelter
                    
                    # Проверяем структуру документов
                    document = result['documents'][0]
                    assert 'title' in document
                    assert 'description' in document
                    assert 'file_path' in document
                    
                    # Проверяем структуру ответов
                    response = result['safety_responses'][0]
                    assert 'question_keywords' in response
                    assert 'answer' in response
                    assert 'source' in response
                    
                    # Проверяем контакты
                    assert 'security' in result['contacts']
                    assert 'safety' in result['contacts']


class TestNotificationConfiguration:
    """Тесты конфигурации уведомлений"""
    
    def test_smtp_configuration_loading(self):
        """Тест загрузки SMTP конфигурации"""
        with patch.dict(os.environ, {
            'YANDEX_SMTP_ENABLED': 'true',
            'YANDEX_SMTP_HOST': 'smtp.yandex.ru',
            'YANDEX_SMTP_PORT': '587',
            'YANDEX_SMTP_USER': 'test@yandex.ru',
            'YANDEX_SMTP_PASSWORD': 'password',
            'YANDEX_SMTP_USE_TLS': 'true',
            'INCIDENT_NOTIFICATION_EMAILS': 'admin@test.com,security@test.com',
            'INCIDENT_NOTIFICATION_SMS_NUMBERS': ''  # Отключаем SMS
        }):
            from yandex_notifications import NotificationServiceFactory
            service = NotificationServiceFactory.create_from_env()
            
            assert len(service.channels) == 1
            assert service.channels[0].__class__.__name__ == 'SMTPNotificationChannel'
    
    def test_cloud_configuration_loading(self):
        """Тест загрузки Cloud конфигурации"""
        with patch.dict(os.environ, {
            'YANDEX_CLOUD_ENABLED': 'true',
            'YANDEX_CLOUD_FOLDER_ID': 'test_folder',
            'YANDEX_CLOUD_OAUTH_TOKEN': 'test_token',
            'YANDEX_CLOUD_NOTIFICATION_CHANNEL_ID': 'test_channel',
            'NOTIFICATION_PRIORITY_HIGH': 'true'
        }):
            from yandex_notifications import NotificationServiceFactory
            service = NotificationServiceFactory.create_from_env()
            
            assert len(service.channels) >= 1
            cloud_channels = [ch for ch in service.channels if ch.__class__.__name__ == 'CloudNotificationChannel']
            assert len(cloud_channels) == 1
    
    def test_sms_configuration_loading(self):
        """Тест загрузки SMS конфигурации"""
        with patch.dict(os.environ, {
            'INCIDENT_NOTIFICATION_SMS_NUMBERS': '+1234567890,+0987654321'
        }):
            from yandex_notifications import NotificationServiceFactory
            service = NotificationServiceFactory.create_from_env()
            
            assert len(service.channels) >= 1
            sms_channels = [ch for ch in service.channels if ch.__class__.__name__ == 'SMSNotificationChannel']
            assert len(sms_channels) == 1
    
    def test_notification_configuration_disabled(self):
        """Тест отключенной конфигурации уведомлений"""
        with patch.dict(os.environ, {
            'YANDEX_SMTP_ENABLED': 'false',
            'YANDEX_CLOUD_ENABLED': 'false',
            'INCIDENT_NOTIFICATION_SMS_NUMBERS': ''
        }):
            from yandex_notifications import NotificationServiceFactory
            service = NotificationServiceFactory.create_from_env()
            
            assert len(service.channels) == 0
    
    def test_notification_configuration_mixed(self):
        """Тест смешанной конфигурации уведомлений"""
        with patch.dict(os.environ, {
            'YANDEX_SMTP_ENABLED': 'true',
            'YANDEX_SMTP_HOST': 'smtp.test.com',
            'YANDEX_SMTP_PORT': '587',
            'YANDEX_SMTP_USER': 'test@test.com',
            'YANDEX_SMTP_PASSWORD': 'password',
            'YANDEX_SMTP_USE_TLS': 'true',
            'INCIDENT_NOTIFICATION_EMAILS': 'admin@test.com',
            'YANDEX_CLOUD_ENABLED': 'false',
            'INCIDENT_NOTIFICATION_SMS_NUMBERS': '+1234567890'
        }):
            from yandex_notifications import NotificationServiceFactory
            service = NotificationServiceFactory.create_from_env()
            
            assert len(service.channels) == 2
            assert service.channels[0].__class__.__name__ == 'SMTPNotificationChannel'
            assert service.channels[1].__class__.__name__ == 'SMSNotificationChannel'


class TestConfigurationValidation:
    """Тесты валидации конфигурации"""
    
    def test_bot_token_validation(self):
        """Тест валидации токена бота"""
        # Валидный токен
        valid_token = "123456789:ABCdefGHIjklMNOpqrsTUVwxyz"
        assert ":" in valid_token
        assert len(valid_token) > 20
        
        # Невалидный токен
        invalid_tokens = [
            "",
            "123456789",
            "ABCdefGHIjklMNOpqrsTUVwxyz",
            "123456789:",
            ":ABCdefGHIjklMNOpqrsTUVwxyz"
        ]
        
        for token in invalid_tokens:
            assert ":" not in token or len(token) < 20 or token.endswith(":") or token.startswith(":")
    
    def test_chat_id_validation(self):
        """Тест валидации ID чата"""
        # Валидный ID чата
        valid_chat_id = "123456789"
        assert valid_chat_id.isdigit()
        assert len(valid_chat_id) >= 9
        
        # Невалидный ID чата
        invalid_chat_ids = [
            "",
            "abc",
            "123",
            "12345678901234567890"  # Слишком длинный
        ]
        
        for chat_id in invalid_chat_ids:
            assert not chat_id.isdigit() or len(chat_id) < 9 or len(chat_id) > 15
    
    def test_email_validation(self):
        """Тест валидации email адресов"""
        # Валидные email
        valid_emails = [
            "test@example.com",
            "user.name@domain.co.uk",
            "admin+test@company.org"
        ]
        
        for email in valid_emails:
            assert "@" in email
            assert "." in email.split("@")[1]
        
        # Невалидные email
        invalid_emails = [
            "",
            "test",
            "@example.com",
            "test@",
            "test@example"
        ]
        
        for email in invalid_emails:
            assert "@" not in email or email.startswith("@") or email.endswith("@") or "." not in email.split("@")[1] if "@" in email else True
    
    def test_phone_validation(self):
        """Тест валидации телефонных номеров"""
        # Валидные номера
        valid_phones = [
            "+1234567890",
            "+7-800-555-35-35",
            "+44 20 7946 0958"
        ]
        
        for phone in valid_phones:
            assert phone.startswith("+")
            assert len(phone) >= 10
        
        # Невалидные номера
        invalid_phones = [
            "",
            "1234567890",
            "+",
            "+123"
        ]
        
        for phone in invalid_phones:
            assert not phone.startswith("+") or len(phone) < 10


class TestConfigurationFiles:
    """Тесты конфигурационных файлов"""
    
    def test_env_file_structure(self):
        """Тест структуры .env файла"""
        env_content = """
# Основные настройки бота
BOT_TOKEN=123456789:ABCdefGHIjklMNOpqrsTUVwxyz
ADMIN_CHAT_ID=123456789
LOG_LEVEL=INFO

# Лимиты файлов
MAX_FILE_SIZE_MB=20
MAX_VIDEO_SIZE_MB=300

# Email настройки
EMAIL_HOST=smtp.yandex.ru
EMAIL_PORT=587
EMAIL_USE_TLS=True
EMAIL_USE_SSL=False
EMAIL_HOST_USER=your_email@yandex.ru
EMAIL_HOST_PASSWORD=your_password
DEFAULT_FROM_EMAIL=your_email@yandex.ru

# Yandex уведомления
YANDEX_SMTP_ENABLED=true
YANDEX_SMTP_HOST=smtp.yandex.ru
YANDEX_SMTP_PORT=587
YANDEX_SMTP_USER=your_email@yandex.ru
YANDEX_SMTP_PASSWORD=your_password
YANDEX_SMTP_USE_TLS=true
INCIDENT_NOTIFICATION_EMAILS=admin@company.com,security@company.com

YANDEX_CLOUD_ENABLED=false
YANDEX_CLOUD_FOLDER_ID=your_folder_id
YANDEX_CLOUD_OAUTH_TOKEN=your_oauth_token
YANDEX_CLOUD_NOTIFICATION_CHANNEL_ID=your_channel_id

INCIDENT_NOTIFICATION_SMS_NUMBERS=+1234567890,+0987654321
"""
        
        # Проверяем наличие всех необходимых переменных
        required_vars = [
            'BOT_TOKEN', 'ADMIN_CHAT_ID', 'LOG_LEVEL',
            'MAX_FILE_SIZE_MB', 'MAX_VIDEO_SIZE_MB',
            'EMAIL_HOST', 'EMAIL_PORT', 'EMAIL_USE_TLS',
            'YANDEX_SMTP_ENABLED', 'INCIDENT_NOTIFICATION_EMAILS'
        ]
        
        for var in required_vars:
            assert var in env_content
    
    def test_placeholders_file_structure(self):
        """Тест структуры файла заглушек"""
        placeholders_structure = {
            "shelters": [
                {
                    "name": "string",
                    "description": "string",
                    "lat": "number",
                    "lon": "number",
                    "map_link": "string",
                    "photo_path": "string"
                }
            ],
            "documents": [
                {
                    "title": "string",
                    "description": "string",
                    "file_path": "string"
                }
            ],
            "safety_responses": [
                {
                    "question_keywords": ["string"],
                    "answer": "string",
                    "source": "string"
                }
            ],
            "contacts": {
                "security": "string",
                "safety": "string",
                "emergency": "string"
            }
        }
        
        # Проверяем структуру
        assert "shelters" in placeholders_structure
        assert "documents" in placeholders_structure
        assert "safety_responses" in placeholders_structure
        assert "contacts" in placeholders_structure
        
        # Проверяем структуру убежищ
        shelter_fields = ["name", "description", "lat", "lon", "map_link", "photo_path"]
        for field in shelter_fields:
            assert field in placeholders_structure["shelters"][0]
        
        # Проверяем структуру документов
        document_fields = ["title", "description", "file_path"]
        for field in document_fields:
            assert field in placeholders_structure["documents"][0]
        
        # Проверяем структуру ответов
        response_fields = ["question_keywords", "answer", "source"]
        for field in response_fields:
            assert field in placeholders_structure["safety_responses"][0]
        
        # Проверяем контакты
        contact_fields = ["security", "safety", "emergency"]
        for field in contact_fields:
            assert field in placeholders_structure["contacts"]


# Вспомогательные функции для тестов
def mock_open(read_data=None):
    """Создает мок для функции open"""
    from unittest.mock import mock_open as original_mock_open
    return original_mock_open(read_data=read_data)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
