"""
Простые тесты без импорта main.py
Тестирует основные функции без сложных зависимостей
"""

import pytest
import os
import sys
import json
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime

# Добавляем путь к модулям
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))


class TestBasicFunctionality:
    """Базовые тесты функциональности"""
    
    def test_import_handlers(self):
        """Тест импорта обработчиков"""
        with patch.dict('sys.modules', {'yandex_notifications': Mock()}):
            from bot.handlers import (
                log_activity, log_incident, log_suggestion,
                get_back_keyboard, get_main_menu_keyboard
            )
            
            # Проверяем, что функции импортированы
            assert callable(log_activity)
            assert callable(log_incident)
            assert callable(log_suggestion)
            assert callable(get_back_keyboard)
            assert callable(get_main_menu_keyboard)
    
    def test_import_notifications(self):
        """Тест импорта системы уведомлений"""
        from yandex_notifications import (
            IncidentFormatter, SMTPNotificationChannel,
            NotificationService, NotificationServiceFactory
        )
        
        # Проверяем, что классы импортированы
        assert callable(IncidentFormatter)
        assert callable(SMTPNotificationChannel)
        assert callable(NotificationService)
        assert callable(NotificationServiceFactory)
    
    def test_handlers_keyboards(self):
        """Тест создания клавиатур"""
        with patch.dict('sys.modules', {'yandex_notifications': Mock()}):
            from bot.handlers import get_back_keyboard, get_main_menu_keyboard
            
            # Тест клавиатуры "Назад"
            back_kb = get_back_keyboard()
            assert back_kb is not None
            assert hasattr(back_kb, 'keyboard')
            
            # Тест главного меню
            main_kb = get_main_menu_keyboard()
            assert main_kb is not None
            assert hasattr(main_kb, 'keyboard')
    
    def test_incident_formatter(self):
        """Тест форматтера инцидентов"""
        from yandex_notifications import IncidentFormatter
        
        formatter = IncidentFormatter()
        
        test_incident = {
            'user_id': 12345,
            'description': 'Test incident',
            'location_text': 'Test location',
            'media_count': 2
        }
        
        # Тест форматирования email
        email_result = formatter.format_email(test_incident)
        assert isinstance(email_result, str)
        assert 'Test incident' in email_result
        assert 'Test location' in email_result
        assert 'Медиафайлов: 2' in email_result
        
        # Тест форматирования Cloud сообщения
        cloud_result = formatter.format_cloud_message(test_incident)
        assert isinstance(cloud_result, str)
        assert 'ИНЦИДЕНТ БЕЗОПАСНОСТИ РПРЗ' in cloud_result
        assert '12345' in cloud_result
    
    def test_smtp_channel_creation(self):
        """Тест создания SMTP канала"""
        from yandex_notifications import SMTPNotificationChannel, IncidentFormatter
        
        smtp_config = {
            'host': 'smtp.test.com',
            'port': 587,
            'user': 'test@test.com',
            'password': 'password',
            'use_tls': True
        }
        
        recipients = ['admin@test.com']
        formatter = IncidentFormatter()
        
        channel = SMTPNotificationChannel(smtp_config, recipients, formatter)
        
        assert channel.smtp_config == smtp_config
        assert channel.recipients == recipients
        assert channel.formatter == formatter
    
    def test_notification_service_creation(self):
        """Тест создания сервиса уведомлений"""
        from yandex_notifications import NotificationService, SMTPNotificationChannel, IncidentFormatter
        
        smtp_config = {
            'host': 'smtp.test.com',
            'port': 587,
            'user': 'test@test.com',
            'password': 'password',
            'use_tls': True
        }
        
        channel = SMTPNotificationChannel(smtp_config, ['admin@test.com'], IncidentFormatter())
        service = NotificationService([channel])
        
        assert len(service.channels) == 1
        assert service.channels[0] == channel
    
    def test_handlers_logging(self):
        """Тест функций логирования"""
        with patch.dict('sys.modules', {'yandex_notifications': Mock()}):
            from bot.handlers import log_activity, log_incident, log_suggestion
            
            # Тест с моками
            with patch('bot.handlers.open', mock_open()):
                with patch('bot.handlers.logger') as mock_logger:
                    # Тест логирования активности
                    log_activity(12345, "test_user", "test_action", "test_payload")
                    mock_logger.bind.assert_called_once_with(user_id=12345)
                    
                    # Тест логирования инцидента
                    incident_data = {"test": "data"}
                    log_incident(12345, incident_data)
                    
                    # Тест логирования предложения
                    suggestion_data = {"test": "data"}
                    log_suggestion(12345, suggestion_data)
    
    def test_handlers_danger_report_text(self):
        """Тест обработки текста сообщения об опасности"""
        with patch.dict('sys.modules', {'yandex_notifications': Mock()}):
            from bot.handlers import handle_danger_report_text
            
            # Создаем мок сообщения
            mock_message = Mock()
            mock_message.chat.id = 12345
            mock_message.from_user.username = "test_user"
            mock_message.text = "Пожар в здании А"
            
            user_data = {'step': 'description'}
            placeholders = {}
            
            result = handle_danger_report_text(mock_message, user_data, placeholders)
            
            assert isinstance(result, tuple)
            state, response = result
            assert state == "danger_report"
            assert isinstance(response, dict)
            assert "text" in response
            assert "reply_markup" in response
    
    def test_handlers_safety_question(self):
        """Тест обработки вопроса по безопасности"""
        with patch.dict('sys.modules', {'yandex_notifications': Mock()}):
            from bot.handlers import handle_safety_question
            
            mock_message = Mock()
            mock_message.text = "Что делать при пожаре?"
            
            placeholders = {
                'safety_responses': [
                    {
                        'question_keywords': ['пожар', 'огонь'],
                        'answer': 'При пожаре звоните 01',
                        'source': 'Инструкция по пожарной безопасности'
                    }
                ]
            }
            
            result = handle_safety_question(mock_message, placeholders)
            
            assert isinstance(result, tuple)
            state, response = result
            assert state == "safety_consultant"
            assert isinstance(response, dict)
            assert "Ответ консультанта" in response['text']
    
    def test_handlers_improvement_suggestion(self):
        """Тест обработки предложения по улучшению"""
        with patch.dict('sys.modules', {'yandex_notifications': Mock()}):
            from bot.handlers import handle_improvement_suggestion_text, categorize_suggestion
            
            mock_message = Mock()
            mock_message.chat.id = 12345
            mock_message.from_user.username = "test_user"
            mock_message.text = "Добавить темную тему"
            
            placeholders = {}
            user_data = {}
            
            # Тест категоризации
            category = categorize_suggestion("Улучшить дизайн кнопок")
            assert category == 'UI/UX'
            
            # Тест обработки предложения
            result = handle_improvement_suggestion_text(mock_message, placeholders, user_data)
            
            assert isinstance(result, tuple)
            state, response = result
            assert state == "improvement_suggestion_menu"
            assert isinstance(response, dict)
            assert "Спасибо за ваше предложение" in response['text']


class TestDataValidation:
    """Тесты валидации данных"""
    
    def test_incident_data_structure(self):
        """Тест структуры данных инцидента"""
        incident = {
            'user_id': 12345,
            'username': 'test_user',
            'description': 'Пожар в здании А',
            'location_text': 'Здание А, 1 этаж',
            'media_count': 2,
            'timestamp': datetime.now().isoformat()
        }
        
        # Проверяем обязательные поля
        required_fields = ['user_id', 'description', 'media_count']
        for field in required_fields:
            assert field in incident
        
        # Проверяем типы данных
        assert isinstance(incident['user_id'], int)
        assert isinstance(incident['description'], str)
        assert isinstance(incident['media_count'], int)
        assert len(incident['description']) > 0
    
    def test_suggestion_data_structure(self):
        """Тест структуры данных предложения"""
        suggestion = {
            'id': 1,
            'text': 'Добавить темную тему',
            'user_id': 12345,
            'username': 'test_user',
            'timestamp': datetime.now().isoformat(),
            'votes': 0,
            'voters': [],
            'status': 'pending',
            'category': 'UI/UX'
        }
        
        # Проверяем обязательные поля
        required_fields = ['text', 'user_id', 'username', 'category']
        for field in required_fields:
            assert field in suggestion
        
        # Проверяем типы данных
        assert isinstance(suggestion['text'], str)
        assert isinstance(suggestion['user_id'], int)
        assert isinstance(suggestion['category'], str)
        assert len(suggestion['text']) > 0
    
    def test_placeholders_data_structure(self):
        """Тест структуры данных заглушек"""
        placeholders = {
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
        
        # Проверяем основные секции
        assert "shelters" in placeholders
        assert "documents" in placeholders
        assert "safety_responses" in placeholders
        assert "contacts" in placeholders
        
        # Проверяем структуру убежища
        shelter = placeholders["shelters"][0]
        shelter_fields = ["name", "description", "lat", "lon", "map_link", "photo_path"]
        for field in shelter_fields:
            assert field in shelter
        
        # Проверяем структуру документа
        document = placeholders["documents"][0]
        document_fields = ["title", "description", "file_path"]
        for field in document_fields:
            assert field in document


class TestUtilityFunctions:
    """Тесты утилитарных функций"""
    
    def test_mock_data_factory(self):
        """Тест фабрики тестовых данных"""
        # Имитируем функции из test_utils.py
        def create_mock_message(chat_id=12345, username="test_user", text="Test message"):
            message = Mock()
            message.chat.id = chat_id
            message.from_user.username = username
            message.text = text
            return message
        
        def create_test_incident():
            return {
                'user_id': 12345,
                'username': 'test_user',
                'description': 'Test incident',
                'media_count': 1
            }
        
        # Тестируем создание мок сообщения
        message = create_mock_message()
        assert message.chat.id == 12345
        assert message.from_user.username == "test_user"
        assert message.text == "Test message"
        
        # Тестируем создание тестового инцидента
        incident = create_test_incident()
        assert incident['user_id'] == 12345
        assert incident['description'] == 'Test incident'
        assert incident['media_count'] == 1
    
    def test_json_serialization(self):
        """Тест сериализации JSON"""
        test_data = {
            'user_id': 12345,
            'description': 'Test incident',
            'timestamp': datetime.now().isoformat(),
            'nested': {
                'key': 'value',
                'number': 42
            }
        }
        
        # Тест сериализации
        json_str = json.dumps(test_data, ensure_ascii=False)
        assert isinstance(json_str, str)
        assert 'Test incident' in json_str
        
        # Тест десериализации
        parsed_data = json.loads(json_str)
        assert parsed_data['user_id'] == 12345
        assert parsed_data['description'] == 'Test incident'
        assert parsed_data['nested']['key'] == 'value'
    
    def test_string_validation(self):
        """Тест валидации строк"""
        # Валидные строки
        valid_strings = [
            "Пожар в здании А",
            "Что делать при пожаре?",
            "Добавить темную тему для интерфейса"
        ]
        
        for text in valid_strings:
            assert isinstance(text, str)
            assert len(text) > 0
            assert len(text.strip()) > 0
        
        # Невалидные строки
        invalid_strings = [
            "",
            "   ",
            None
        ]
        
        for text in invalid_strings:
            if text is not None:
                assert len(text.strip()) == 0


# Вспомогательные функции
def mock_open(read_data=None):
    """Создает мок для функции open"""
    from unittest.mock import mock_open as original_mock_open
    return original_mock_open(read_data=read_data)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

