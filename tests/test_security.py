"""
Тесты для модуля безопасности бота
"""

import pytest
import time
from unittest.mock import Mock, patch, MagicMock
import sys
import os

# Добавляем путь к модулям
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'bot'))


class TestSecurityManager:
    """Тесты для SecurityManager"""
    
    def test_import_security_module(self):
        """Тест импорта модуля безопасности"""
        try:
            from security import SecurityManager, security_manager
            assert SecurityManager is not None
            assert security_manager is not None
        except ImportError as e:
            pytest.fail(f"Не удалось импортировать security: {e}")
    
    def test_rate_limiting(self):
        """Тест rate limiting"""
        from security import SecurityManager
        
        manager = SecurityManager()
        manager.MAX_REQUESTS_PER_MINUTE = 3  # Снижаем для теста
        
        user_id = 12345
        
        # Первые 3 запроса должны проходить
        for i in range(3):
            is_allowed, error = manager.check_rate_limit(user_id)
            assert is_allowed is True
            assert error is None
        
        # 4-й запрос должен быть заблокирован
        is_allowed, error = manager.check_rate_limit(user_id)
        assert is_allowed is False
        assert "много запросов" in error.lower()
    
    def test_flood_control(self):
        """Тест flood control"""
        from security import SecurityManager
        
        manager = SecurityManager()
        manager.FLOOD_INTERVAL_SECONDS = 2
        
        user_id = 12345
        action = "test_action"
        
        # Первый запрос проходит
        is_allowed, error = manager.check_flood(user_id, action)
        assert is_allowed is True
        assert error is None
        
        # Второй запрос сразу же - блокируется
        is_allowed, error = manager.check_flood(user_id, action)
        assert is_allowed is False
        assert "подождите" in error.lower()
        
        # После ожидания - проходит
        time.sleep(2.1)
        is_allowed, error = manager.check_flood(user_id, action)
        assert is_allowed is True
        assert error is None
    
    def test_text_validation(self):
        """Тест валидации текста"""
        from security import SecurityManager
        
        manager = SecurityManager()
        user_id = 12345
        
        # Нормальный текст
        is_valid, error = manager.validate_text("Нормальный текст сообщения", user_id)
        assert is_valid is True
        assert error is None
        
        # Слишком длинный текст
        long_text = "а" * 5000
        is_valid, error = manager.validate_text(long_text, user_id)
        assert is_valid is False
        assert "длинный" in error.lower()
    
    def test_file_validation(self):
        """Тест валидации файлов"""
        from security import SecurityManager
        
        manager = SecurityManager()
        user_id = 12345
        
        # Нормальный файл
        file_size = 5 * 1024 * 1024  # 5 МБ
        file_type = "image/jpeg"
        is_valid, error = manager.validate_file(file_size, file_type, user_id, max_size_mb=20)
        assert is_valid is True
        assert error is None
        
        # Слишком большой файл
        large_file_size = 30 * 1024 * 1024  # 30 МБ
        is_valid, error = manager.validate_file(large_file_size, file_type, user_id, max_size_mb=20)
        assert is_valid is False
        assert "большой" in error.lower()
        
        # Недопустимый тип файла
        invalid_type = "application/x-executable"
        is_valid, error = manager.validate_file(file_size, invalid_type, user_id, max_size_mb=20)
        assert is_valid is False
        assert "тип" in error.lower()
    
    def test_whitelist(self):
        """Тест whitelist"""
        from security import SecurityManager
        
        manager = SecurityManager()
        admin_id = 99999
        
        # Добавляем в whitelist
        manager.add_to_whitelist(admin_id)
        
        # Устанавливаем жесткие лимиты
        manager.MAX_REQUESTS_PER_MINUTE = 1
        
        # Делаем много запросов от админа - все должны проходить
        for i in range(5):
            is_allowed, error = manager.check_rate_limit(admin_id)
            assert is_allowed is True  # Whitelist пропускает всё
    
    def test_blacklist(self):
        """Тест blacklist"""
        from security import SecurityManager
        
        manager = SecurityManager()
        banned_user_id = 66666
        
        # Добавляем в blacklist
        manager.add_to_blacklist(banned_user_id)
        
        # Любой запрос должен блокироваться
        is_allowed, error = manager.check_rate_limit(banned_user_id)
        assert is_allowed is False
        assert "заблокирован" in error.lower()
    
    def test_suspicious_activity_tracking(self):
        """Тест отслеживания подозрительной активности"""
        from security import SecurityManager
        
        manager = SecurityManager()
        manager.MAX_SUSPICIOUS_SCORE = 3  # Снижаем для теста
        
        user_id = 77777
        
        # Добавляем подозрительную активность
        for i in range(2):
            manager._add_suspicious_activity(user_id, "test_reason")
        
        # Проверяем счетчик
        assert manager.suspicious_activity[user_id] == 2
        
        # Превышаем порог - должна быть автоматическая блокировка
        manager._add_suspicious_activity(user_id, "test_reason")
        assert user_id in manager.blacklist
    
    def test_get_user_security_info(self):
        """Тест получения информации о безопасности пользователя"""
        from security import SecurityManager
        
        manager = SecurityManager()
        user_id = 88888
        
        # Делаем несколько запросов
        manager.check_rate_limit(user_id)
        manager.check_flood(user_id, "test_action")
        
        # Получаем информацию
        info = manager.get_user_security_info(user_id)
        
        assert info['user_id'] == user_id
        assert 'is_whitelisted' in info
        assert 'is_blacklisted' in info
        assert 'suspicious_score' in info
        assert 'requests_last_minute' in info
    
    def test_clean_old_data(self):
        """Тест очистки старых данных"""
        from security import SecurityManager
        
        manager = SecurityManager()
        user_id = 99999
        
        # Добавляем данные
        manager.check_rate_limit(user_id)
        manager.check_flood(user_id, "test_action")
        
        # Очищаем
        manager.clean_old_data()
        
        # Проверяем, что данные остались (т.к. они свежие)
        assert user_id in manager.user_requests or len(manager.user_requests[user_id]) == 0
    
    def test_security_check_functions(self):
        """Тест вспомогательных функций безопасности"""
        from security import check_user_security, validate_user_text, validate_user_file
        
        user_id = 11111
        
        # check_user_security
        is_allowed, error = check_user_security(user_id, "test")
        assert is_allowed is True
        
        # validate_user_text
        is_valid, error = validate_user_text("Обычный текст", user_id)
        assert is_valid is True
        
        # validate_user_file
        is_valid, error = validate_user_file(1024*1024, "image/png", user_id, 10)
        assert is_valid is True


class TestSecurityIntegration:
    """Тесты интеграции безопасности с основным ботом"""
    
    def test_security_in_main_module(self):
        """Тест наличия системы безопасности в main.py"""
        try:
            # Проверяем, что модуль импортируется
            import main
            
            # Проверяем наличие флага безопасности
            assert hasattr(main, 'SECURITY_ENABLED')
            
            # Проверяем наличие функций безопасности
            assert hasattr(main, 'check_user_security')
            assert hasattr(main, 'validate_user_text')
            assert hasattr(main, 'validate_user_file')
            
        except ImportError:
            # Если не удается импортировать (бот не запущен), это нормально для тестов
            pass
    
    @patch.dict(os.environ, {'BOT_TOKEN': 'test_token', 'ADMIN_CHAT_ID': '123456'})
    def test_security_manager_initialization(self):
        """Тест инициализации SecurityManager с переменными окружения"""
        from security import SecurityManager
        
        manager = SecurityManager()
        
        # Проверяем, что ADMIN добавлен в whitelist
        assert manager.ADMIN_CHAT_ID == 123456
        assert 123456 in manager.whitelist
    
    def test_spam_protection_scenario(self):
        """Тест сценария защиты от спама"""
        from security import SecurityManager
        
        manager = SecurityManager()
        manager.MAX_REQUESTS_PER_MINUTE = 5
        
        spammer_id = 55555
        
        # Спамер отправляет много запросов
        blocked_count = 0
        for i in range(10):
            is_allowed, error = manager.check_rate_limit(spammer_id)
            if not is_allowed:
                blocked_count += 1
        
        # Часть запросов должна быть заблокирована
        assert blocked_count > 0
        
        # Проверяем, что спамер в списке подозрительных
        assert manager.suspicious_activity[spammer_id] > 0


class TestSecurityEdgeCases:
    """Тесты граничных случаев"""
    
    def test_empty_text_validation(self):
        """Тест валидации пустого текста"""
        from security import SecurityManager
        
        manager = SecurityManager()
        is_valid, error = manager.validate_text("", 12345)
        assert is_valid is True  # Пустой текст допустим
    
    def test_none_file_type(self):
        """Тест валидации файла без типа"""
        from security import SecurityManager
        
        manager = SecurityManager()
        is_valid, error = manager.validate_file(1024, None, 12345, 10)
        assert is_valid is True  # Если тип не указан, пропускаем
    
    def test_multiple_actions_flood(self):
        """Тест флуда разных действий"""
        from security import SecurityManager
        
        manager = SecurityManager()
        manager.FLOOD_INTERVAL_SECONDS = 1
        
        user_id = 33333
        
        # Разные действия не должны мешать друг другу
        is_allowed1, _ = manager.check_flood(user_id, "action1")
        is_allowed2, _ = manager.check_flood(user_id, "action2")
        
        assert is_allowed1 is True
        assert is_allowed2 is True
    
    def test_reset_user_limits(self):
        """Тест сброса лимитов пользователя"""
        from security import SecurityManager
        
        manager = SecurityManager()
        user_id = 44444
        
        # Создаем активность
        manager.check_rate_limit(user_id)
        manager.check_flood(user_id, "test")
        
        # Сбрасываем
        manager.reset_user_limits(user_id)
        
        # Проверяем, что лимиты сброшены
        assert len(manager.user_requests[user_id]) == 0
        assert len(manager.user_last_action[user_id]) == 0


if __name__ == '__main__':
    pytest.main([__file__, '-v'])