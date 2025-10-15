"""
Тесты для проверки улучшений бота
Проверяет новые функции: кэширование, улучшенное логирование ошибок
"""

import os
import sys
import tempfile
import time
import unittest
from unittest.mock import patch

# Добавляем путь к модулям бота
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "bot"))

from bot.cache import SimpleCache, cache_user_data, cached, get_cached_user_data


class TestCacheSystem(unittest.TestCase):
    """Тесты системы кэширования"""

    def setUp(self):
        """Настройка перед каждым тестом"""
        # Создаем временный файл для кэша
        self.temp_dir = tempfile.mkdtemp()
        self.cache_file = os.path.join(self.temp_dir, "test_cache.json")

        # Создаем экземпляр кэша с коротким TTL для тестов
        self.cache = SimpleCache(max_size=10, ttl=1)
        self.cache.cache_file = self.cache_file

    def tearDown(self):
        """Очистка после каждого теста"""
        # Удаляем временные файлы
        import shutil

        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_cache_set_get(self):
        """Тест базовой функциональности set/get"""
        # Сохраняем значение
        self.cache.set("test_key", "test_value")

        # Получаем значение
        value = self.cache.get("test_key")
        self.assertEqual(value, "test_value")

        # Проверяем, что значение кэшируется
        value2 = self.cache.get("test_key")
        self.assertEqual(value2, "test_value")

    def test_cache_expiration(self):
        """Тест истечения кэша"""
        # Сохраняем значение с коротким TTL
        self.cache.set("expire_key", "expire_value", 1)

        # Проверяем, что значение есть
        value = self.cache.get("expire_key")
        self.assertEqual(value, "expire_value")

        # Ждем истечения TTL
        time.sleep(1.1)

        # Проверяем, что значение истекло
        value = self.cache.get("expire_key")
        self.assertIsNone(value)

    def test_cache_max_size(self):
        """Тест ограничения размера кэша"""
        # Заполняем кэш до лимита
        for i in range(12):  # Больше чем max_size=10
            self.cache.set(f"key_{i}", f"value_{i}")

        # Проверяем, что старые элементы удалены
        stats = self.cache.get_stats()
        self.assertLessEqual(stats["total_items"], 10)

        # Проверяем, что новые элементы есть
        value = self.cache.get("key_11")
        self.assertEqual(value, "value_11")

    def test_cache_persistence(self):
        """Тест сохранения кэша на диск"""
        # Сохраняем значение
        self.cache.set("persist_key", "persist_value")

        # Принудительно сохраняем на диск
        self.cache._save_to_disk()

        # Создаем новый экземпляр кэша (имитируем перезапуск)
        new_cache = SimpleCache(max_size=10, ttl=1)
        new_cache.cache_file = self.cache_file

        # Принудительно загружаем с диска
        new_cache._load_from_disk()

        # Проверяем, что значение загрузилось
        value = new_cache.get("persist_key")
        self.assertEqual(value, "persist_value")

    def test_cached_decorator(self):
        """Тест декоратора кэширования"""
        call_count = 0

        @cached(ttl=10, key_prefix="test_")
        def expensive_function(x):
            nonlocal call_count
            call_count += 1
            return x * 2

        # Первый вызов
        result1 = expensive_function(5)
        self.assertEqual(result1, 10)
        self.assertEqual(call_count, 1)

        # Второй вызов (должен быть из кэша)
        result2 = expensive_function(5)
        self.assertEqual(result2, 10)
        self.assertEqual(call_count, 1)  # Функция не вызвалась повторно

        # Вызов с другими аргументами
        result3 = expensive_function(3)
        self.assertEqual(result3, 6)
        self.assertEqual(call_count, 2)  # Функция вызвалась для новых аргументов

    def test_user_data_cache(self):
        """Тест кэширования данных пользователя"""
        user_id = 12345
        test_data = {"name": "Test User", "settings": {"theme": "dark"}}

        # Сохраняем данные
        cache_user_data(user_id, test_data, 60)

        # Получаем данные
        retrieved_data = get_cached_user_data(user_id)
        self.assertEqual(retrieved_data, test_data)

        # Проверяем, что данные действительно кэшируются
        retrieved_data2 = get_cached_user_data(user_id)
        self.assertEqual(retrieved_data2, test_data)

    def test_cache_stats(self):
        """Тест статистики кэша"""
        # Добавляем несколько элементов
        self.cache.set("key1", "value1")
        self.cache.set("key2", "value2")

        stats = self.cache.get_stats()

        self.assertGreaterEqual(stats["total_items"], 2)
        self.assertGreaterEqual(stats["valid_items"], 2)
        self.assertIsInstance(stats["memory_usage"], int)

    def test_cache_delete(self):
        """Тест удаления элементов из кэша"""
        # Добавляем элемент
        self.cache.set("delete_key", "delete_value")

        # Проверяем, что элемент есть
        value = self.cache.get("delete_key")
        self.assertEqual(value, "delete_value")

        # Удаляем элемент
        deleted = self.cache.delete("delete_key")
        self.assertTrue(deleted)

        # Проверяем, что элемент удален
        value = self.cache.get("delete_key")
        self.assertIsNone(value)

        # Пытаемся удалить несуществующий элемент
        deleted = self.cache.delete("nonexistent_key")
        self.assertFalse(deleted)


class TestErrorHandling(unittest.TestCase):
    """Тесты улучшенной обработки ошибок"""

    def setUp(self):
        """Настройка перед каждым тестом"""
        # Импортируем функцию логирования ошибок
        from bot.main import log_admin_error

        self.log_admin_error = log_admin_error

    @patch("bot.main.logger")
    def test_log_admin_error_basic(self, mock_logger):
        """Тест базового логирования ошибок"""
        test_error = ValueError("Test error message")
        test_context = {"user_id": 123, "action": "test"}

        # Вызываем функцию
        self.log_admin_error("TEST_ERROR", test_error, test_context)

        # Проверяем, что логирование вызвано
        self.assertTrue(mock_logger.error.called)
        self.assertTrue(mock_logger.bind.called)

    @patch("bot.main.logger")
    @patch("os.makedirs")
    @patch("builtins.open", create=True)
    def test_log_critical_error(self, mock_open, mock_makedirs, mock_logger):
        """Тест логирования критических ошибок"""
        test_error = RuntimeError("Critical system failure")

        # Вызываем функцию с критической ошибкой
        self.log_admin_error("BOT_CRASH", test_error)

        # Проверяем, что вызвано критическое логирование
        mock_logger.critical.assert_called()

        # Проверяем, что создается директория для логов
        mock_makedirs.assert_called_with("logs", exist_ok=True)

    def test_log_admin_error_without_context(self):
        """Тест логирования ошибок без контекста"""
        test_error = TypeError("Type error")

        # Не должно вызывать исключений
        try:
            self.log_admin_error("TEST_ERROR", test_error)
            result = True
        except Exception:
            result = False

        self.assertTrue(result)


class TestIntegration(unittest.TestCase):
    """Интеграционные тесты"""

    def test_cache_and_error_handling_integration(self):
        """Тест интеграции кэширования и обработки ошибок"""
        # Создаем кэш
        cache = SimpleCache(max_size=5, ttl=1)

        # Тестируем обработку ошибок в кэше
        try:
            # Это должно работать без ошибок
            cache.set("test", "value")
            value = cache.get("test")
            self.assertEqual(value, "value")

            # Тестируем очистку истекших элементов
            cache._clean_expired()

            result = True
        except Exception as e:
            # Если произошла ошибка, логируем её
            from bot.main import log_admin_error

            log_admin_error("CACHE_TEST_ERROR", e)
            result = False

        self.assertTrue(result)


if __name__ == "__main__":
    # Настройка тестового окружения
    print("🧪 Запуск тестов улучшений бота...")

    # Создаем тестовую директорию для логов
    os.makedirs("logs", exist_ok=True)

    # Запускаем тесты
    unittest.main(verbosity=2)
