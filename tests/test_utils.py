"""
Вспомогательные утилиты для тестирования
Содержит общие функции и моки для всех тестов
"""

import pytest
import os
import sys
import json
import tempfile
from unittest.mock import Mock, patch, MagicMock, call
from datetime import datetime
from typing import Dict, Any, List, Optional

# Добавляем путь к модулям
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))


class TestDataFactory:
    """Фабрика тестовых данных"""
    
    @staticmethod
    def create_mock_message(chat_id: int = 12345, username: str = "test_user", 
                          text: str = "Test message", content_type: str = "text",
                          user_id: int = 12345) -> Mock:
        """Создает мок сообщения Telegram"""
        message = Mock()
        message.chat.id = chat_id
        message.from_user.username = username
        message.from_user.id = user_id
        message.text = text
        message.content_type = content_type
        message.photo = None
        message.video = None
        message.document = None
        message.location = None
        return message
    
    @staticmethod
    def create_mock_location(latitude: float = 55.7558, longitude: float = 37.6176) -> Mock:
        """Создает мок геолокации"""
        location = Mock()
        location.latitude = latitude
        location.longitude = longitude
        return location
    
    @staticmethod
    def create_mock_photo(file_size: int = 1024*1024) -> List[Mock]:
        """Создает мок фото"""
        photo = Mock()
        photo.file_size = file_size
        photo.file_id = "test_photo_id"
        return [photo]
    
    @staticmethod
    def create_mock_video(file_size: int = 5*1024*1024) -> Mock:
        """Создает мок видео"""
        video = Mock()
        video.file_size = file_size
        video.file_id = "test_video_id"
        return video
    
    @staticmethod
    def create_mock_document(file_size: int = 1024*1024) -> Mock:
        """Создает мок документа"""
        document = Mock()
        document.file_size = file_size
        document.file_id = "test_document_id"
        return document
    
    @staticmethod
    def create_test_placeholders() -> Dict[str, Any]:
        """Создает тестовые заглушки"""
        return {
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
    
    @staticmethod
    def create_test_incident() -> Dict[str, Any]:
        """Создает тестовый инцидент"""
        return {
            "user_id": 12345,
            "username": "test_user",
            "description": "Пожар в здании А",
            "location": {
                "latitude": 55.7558,
                "longitude": 37.6176
            },
            "location_text": "Здание А, 1 этаж",
            "media_count": 2,
            "timestamp": datetime.now().isoformat()
        }
    
    @staticmethod
    def create_test_suggestion() -> Dict[str, Any]:
        """Создает тестовое предложение"""
        return {
            "id": 1,
            "text": "Добавить темную тему для интерфейса",
            "user_id": 12345,
            "username": "test_user",
            "timestamp": datetime.now().isoformat(),
            "votes": 0,
            "voters": [],
            "status": "pending",
            "category": "UI/UX"
        }


class MockBotFactory:
    """Фабрика моков бота"""
    
    @staticmethod
    def create_mock_bot() -> Mock:
        """Создает мок бота Telegram"""
        bot = Mock()
        bot.send_message = Mock()
        bot.send_photo = Mock()
        bot.send_document = Mock()
        bot.send_location = Mock()
        bot.get_me = Mock()
        bot.remove_webhook = Mock()
        bot.polling = Mock()
        bot.set_state = Mock()
        return bot
    
    @staticmethod
    def create_mock_keyboard() -> Mock:
        """Создает мок клавиатуры"""
        keyboard = Mock()
        keyboard.keyboard = []
        return keyboard


class TestEnvironmentManagerHelper:
    """Вспомогательные функции для менеджера тестового окружения"""
    
    @staticmethod
    def setup_test_environment():
        """Настраивает тестовое окружение"""
        # Создаем временную директорию
        temp_dir = tempfile.mkdtemp()
        
        # Сохраняем оригинальные переменные окружения
        original_env = os.environ.copy()
        
        # Устанавливаем тестовые переменные
        os.environ.update({
            'BOT_TOKEN': '123456789:ABCdefGHIjklMNOpqrsTUVwxyz',
            'ADMIN_CHAT_ID': '123456789',
            'LOG_LEVEL': 'DEBUG',
            'MAX_FILE_SIZE_MB': '20',
            'MAX_VIDEO_SIZE_MB': '300',
            'EMAIL_HOST': 'smtp.test.com',
            'EMAIL_PORT': '587',
            'EMAIL_USE_TLS': 'True',
            'EMAIL_USE_SSL': 'False',
            'EMAIL_HOST_USER': 'test@test.com',
            'EMAIL_HOST_PASSWORD': 'password',
            'DEFAULT_FROM_EMAIL': 'test@test.com'
        })
        
        return temp_dir, original_env
    
    @staticmethod
    def cleanup_test_environment(temp_dir, original_env):
        """Очищает тестовое окружение"""
        # Восстанавливаем оригинальные переменные окружения
        os.environ.clear()
        os.environ.update(original_env)
        
        # Удаляем временную директорию
        if temp_dir and os.path.exists(temp_dir):
            import shutil
            shutil.rmtree(temp_dir)
    
    @staticmethod
    def create_test_log_file(temp_dir, filename: str, content: str = "") -> str:
        """Создает тестовый лог файл"""
        file_path = os.path.join(temp_dir, filename)
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)
        
        return file_path


class TestAssertions:
    """Дополнительные утверждения для тестов"""
    
    @staticmethod
    def assert_message_sent(mock_bot, chat_id: int, text_contains: str = None):
        """Проверяет, что сообщение было отправлено"""
        assert mock_bot.send_message.called
        call_args = mock_bot.send_message.call_args
        assert call_args[0][0] == chat_id  # Первый аргумент - chat_id
        
        if text_contains:
            message_text = call_args[0][1]  # Второй аргумент - текст
            assert text_contains in message_text
    
    @staticmethod
    def assert_keyboard_sent(mock_bot, keyboard_type: str = None):
        """Проверяет, что клавиатура была отправлена"""
        assert mock_bot.send_message.called
        call_args = mock_bot.send_message.call_args
        assert 'reply_markup' in call_args[1]  # reply_markup в kwargs
    
    @staticmethod
    def assert_log_written(mock_logger, level: str, message_contains: str = None):
        """Проверяет, что лог был записан"""
        assert getattr(mock_logger, level).called
        
        if message_contains:
            call_args = getattr(mock_logger, level).call_args
            log_message = call_args[0][0]
            assert message_contains in log_message
    
    @staticmethod
    def assert_file_created(file_path: str, content_contains: str = None):
        """Проверяет, что файл был создан"""
        assert os.path.exists(file_path)
        
        if content_contains:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
                assert content_contains in content


class TestFixtures:
    """Фикстуры для тестов"""
    
    @pytest.fixture
    def mock_bot(self):
        """Фикстура мок бота"""
        return MockBotFactory.create_mock_bot()
    
    @pytest.fixture
    def mock_message(self):
        """Фикстура мок сообщения"""
        return TestDataFactory.create_mock_message()
    
    @pytest.fixture
    def test_placeholders(self):
        """Фикстура тестовых заглушек"""
        return TestDataFactory.create_test_placeholders()
    
    @pytest.fixture
    def test_incident(self):
        """Фикстура тестового инцидента"""
        return TestDataFactory.create_test_incident()
    
    @pytest.fixture
    def test_suggestion(self):
        """Фикстура тестового предложения"""
        return TestDataFactory.create_test_suggestion()
    
    @pytest.fixture
    def env_manager(self):
        """Фикстура менеджера окружения"""
        temp_dir, original_env = TestEnvironmentManagerHelper.setup_test_environment()
        yield temp_dir, original_env
        TestEnvironmentManagerHelper.cleanup_test_environment(temp_dir, original_env)


class TestHelpers:
    """Вспомогательные функции для тестов"""
    
    @staticmethod
    def mock_open_with_data(data: str):
        """Создает мок open с данными"""
        from unittest.mock import mock_open
        return mock_open(read_data=data)
    
    @staticmethod
    def mock_open_with_json(data: Dict[str, Any]):
        """Создает мок open с JSON данными"""
        return TestHelpers.mock_open_with_data(json.dumps(data, ensure_ascii=False))
    
    @staticmethod
    def create_temp_file(content: str = "", suffix: str = ".txt") -> str:
        """Создает временный файл"""
        with tempfile.NamedTemporaryFile(mode='w', suffix=suffix, delete=False) as f:
            f.write(content)
            return f.name
    
    @staticmethod
    def cleanup_temp_file(file_path: str):
        """Удаляет временный файл"""
        if os.path.exists(file_path):
            os.unlink(file_path)
    
    @staticmethod
    def assert_dict_contains(dict1: Dict[str, Any], dict2: Dict[str, Any]):
        """Проверяет, что dict1 содержит все ключи из dict2"""
        for key, value in dict2.items():
            assert key in dict1
            assert dict1[key] == value
    
    @staticmethod
    def assert_list_contains(list1: List[Any], list2: List[Any]):
        """Проверяет, что list1 содержит все элементы из list2"""
        for item in list2:
            assert item in list1


class TestDataValidators:
    """Валидаторы тестовых данных"""
    
    @staticmethod
    def validate_incident_data(incident: Dict[str, Any]) -> bool:
        """Валидирует данные инцидента"""
        required_fields = ['user_id', 'description', 'media_count']
        return all(field in incident for field in required_fields)
    
    @staticmethod
    def validate_suggestion_data(suggestion: Dict[str, Any]) -> bool:
        """Валидирует данные предложения"""
        required_fields = ['text', 'user_id', 'username', 'category']
        return all(field in suggestion for field in required_fields)
    
    @staticmethod
    def validate_placeholders_data(placeholders: Dict[str, Any]) -> bool:
        """Валидирует данные заглушек"""
        required_sections = ['shelters', 'documents', 'safety_responses', 'contacts']
        return all(section in placeholders for section in required_sections)
    
    @staticmethod
    def validate_shelter_data(shelter: Dict[str, Any]) -> bool:
        """Валидирует данные убежища"""
        required_fields = ['name', 'description', 'lat', 'lon', 'map_link', 'photo_path']
        return all(field in shelter for field in required_fields)
    
    @staticmethod
    def validate_document_data(document: Dict[str, Any]) -> bool:
        """Валидирует данные документа"""
        required_fields = ['title', 'description', 'file_path']
        return all(field in document for field in required_fields)


class TestPerformanceHelpers:
    """Вспомогательные функции для тестов производительности"""
    
    @staticmethod
    def measure_execution_time(func, *args, **kwargs) -> float:
        """Измеряет время выполнения функции"""
        import time
        start_time = time.time()
        func(*args, **kwargs)
        end_time = time.time()
        return end_time - start_time
    
    @staticmethod
    def assert_execution_time_under(func, max_time: float, *args, **kwargs):
        """Проверяет, что функция выполняется быстрее указанного времени"""
        execution_time = TestPerformanceHelpers.measure_execution_time(func, *args, **kwargs)
        assert execution_time < max_time, f"Функция выполнилась за {execution_time:.3f}s, что больше {max_time}s"
    
    @staticmethod
    def create_large_test_data(size: int = 1000) -> List[Dict[str, Any]]:
        """Создает большой объем тестовых данных"""
        data = []
        for i in range(size):
            data.append({
                'id': i,
                'text': f'Test suggestion {i}',
                'user_id': 12345 + i,
                'username': f'user_{i}',
                'timestamp': datetime.now().isoformat(),
                'votes': i % 10,
                'status': 'pending',
                'category': 'Test'
            })
        return data


# Глобальные фикстуры для всех тестов
@pytest.fixture(scope="session")
def test_data_factory():
    """Глобальная фикстура фабрики тестовых данных"""
    return TestDataFactory


@pytest.fixture(scope="session")
def mock_bot_factory():
    """Глобальная фикстура фабрики моков бота"""
    return MockBotFactory


@pytest.fixture(scope="session")
def test_assertions():
    """Глобальная фикстура утверждений"""
    return TestAssertions


@pytest.fixture(scope="session")
def test_helpers():
    """Глобальная фикстура вспомогательных функций"""
    return TestHelpers


@pytest.fixture(scope="session")
def test_validators():
    """Глобальная фикстура валидаторов"""
    return TestDataValidators


if __name__ == "__main__":
    # Тестируем утилиты
    print("🧪 Тестирование утилит...")
    
    # Тест фабрики данных
    factory = TestDataFactory()
    message = factory.create_mock_message()
    assert message.chat.id == 12345
    assert message.from_user.username == "test_user"
    
    placeholders = factory.create_test_placeholders()
    assert len(placeholders['shelters']) == 2
    assert len(placeholders['documents']) == 2
    
    # Тест валидаторов
    validators = TestDataValidators()
    incident = factory.create_test_incident()
    assert validators.validate_incident_data(incident)
    
    suggestion = factory.create_test_suggestion()
    assert validators.validate_suggestion_data(suggestion)
    
    print("✅ Все утилиты работают корректно!")
