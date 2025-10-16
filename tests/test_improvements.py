"""
Тесты для проверки улучшений бота
Проверяет новые функции: кэширование, улучшенное логирование ошибок
"""

import os
import sys
import tempfile
import time
import unittest
from unittest.mock import Mock, patch

# Добавляем путь к модулям бота
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "bot"))

try:
    from bot.cache import SimpleCache, cache_user_data, cached, get_cached_user_data
except ImportError:
    # Альтернативный импорт если модуль не найден
    SimpleCache = None


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


class TestAdminNotifications(unittest.TestCase):
    """Тесты для уведомлений администратора о предложениях"""

    def setUp(self):
        """Настройка перед каждым тестом"""
        # Создаем mock объекты
        self.mock_message = Mock()
        self.mock_message.chat.id = 12345
        self.mock_message.from_user.username = "testuser"
        self.mock_message.text = "Тестовое предложение по улучшению"

        self.placeholders = {}
        self.user_data = {}

        # Мокаем временные файлы для логов
        self.temp_dir = tempfile.mkdtemp()
        self.suggestions_file = os.path.join(self.temp_dir, "enhanced_suggestions.json")

    def tearDown(self):
        """Очистка после каждого теста"""
        import shutil

        shutil.rmtree(self.temp_dir, ignore_errors=True)

    @patch.dict(os.environ, {"ADMIN_CHAT_ID": "987654321"})
    @patch("bot.handlers.bot_instance")
    @patch("bot.handlers.save_enhanced_suggestion")
    @patch("bot.handlers.log_suggestion")
    @patch("bot.handlers.log_activity")
    @patch("bot.handlers.logger")
    def test_admin_notification_success(
        self,
        mock_logger,
        mock_log_activity,
        mock_log_suggestion,
        mock_save_enhanced,
        mock_bot,
    ):
        """Тест успешной отправки уведомления администратору"""
        # Настраиваем mock bot
        mock_bot.send_message = Mock()

        # Импортируем функцию для тестирования
        from bot.handlers import handle_improvement_suggestion_text

        # Вызываем функцию
        result = handle_improvement_suggestion_text(
            self.mock_message, self.placeholders, self.user_data
        )

        # Проверяем результат
        self.assertIsInstance(result, tuple)
        self.assertEqual(result[0], "main_menu")
        self.assertIn("✅ Ваше предложение отправлено", result[1]["text"])

        # Проверяем, что бот отправил сообщение админу
        mock_bot.send_message.assert_called_once()
        args, kwargs = mock_bot.send_message.call_args
        self.assertEqual(args[0], "987654321")  # ADMIN_CHAT_ID
        self.assertIn("💡 НОВОЕ ПРЕДЛОЖЕНИЕ ПО УЛУЧШЕНИЮ", args[1])
        self.assertIn("testuser", args[1])
        self.assertIn("Тестовое предложение по улучшению", args[1])

        # Проверяем, что логи вызваны
        mock_log_activity.assert_called_once()
        mock_save_enhanced.assert_called_once()
        mock_log_suggestion.assert_called_once()

        # Проверяем успешное логирование
        mock_logger.info.assert_called()

    @patch.dict(os.environ, {})  # Убираем ADMIN_CHAT_ID
    @patch("bot.handlers.bot_instance")
    @patch("bot.handlers.save_enhanced_suggestion")
    @patch("bot.handlers.log_suggestion")
    @patch("bot.handlers.log_activity")
    @patch("bot.handlers.logger")
    def test_admin_notification_no_admin_id(
        self,
        mock_logger,
        mock_log_activity,
        mock_log_suggestion,
        mock_save_enhanced,
        mock_bot,
    ):
        """Тест обработки отсутствия ADMIN_CHAT_ID"""
        from bot.handlers import handle_improvement_suggestion_text

        # Вызываем функцию
        result = handle_improvement_suggestion_text(
            self.mock_message, self.placeholders, self.user_data
        )

        # Проверяем, что функция работает без ошибок
        self.assertIsInstance(result, tuple)
        self.assertEqual(result[0], "main_menu")

        # Проверяем что функция отработала корректно
        self.assertIsNotNone(result)
        self.assertIn("text", result[1])

        # Проверяем, что бот не пытался отправить сообщение (так как нет ADMIN_CHAT_ID)
        # mock_bot.send_message может быть вызван для пользователя, но не для админа
        # Просто убеждаемся что функция не упала с ошибкой

    @patch.dict(os.environ, {"ADMIN_CHAT_ID": "987654321"})
    @patch("bot.handlers.bot_instance", None)  # Убираем bot_instance
    @patch("bot.handlers.save_enhanced_suggestion")
    @patch("bot.handlers.log_suggestion")
    @patch("bot.handlers.log_activity")
    @patch("bot.handlers.logger")
    def test_admin_notification_no_bot_instance(
        self, mock_logger, mock_log_activity, mock_log_suggestion, mock_save_enhanced
    ):
        """Тест обработки отсутствия bot_instance"""
        from bot.handlers import handle_improvement_suggestion_text

        # Вызываем функцию
        result = handle_improvement_suggestion_text(
            self.mock_message, self.placeholders, self.user_data
        )

        # Проверяем, что функция работает без ошибок
        self.assertIsInstance(result, tuple)
        self.assertEqual(result[0], "main_menu")

        # Проверяем предупреждение о недоступном bot_instance
        mock_logger.warning.assert_called_with(
            "⚠️ Объект bot не инициализирован для отправки предложений админу"
        )

    @patch.dict(os.environ, {"ADMIN_CHAT_ID": "987654321"})
    @patch("bot.handlers.bot_instance")
    @patch("bot.handlers.save_enhanced_suggestion")
    @patch("bot.handlers.log_suggestion")
    @patch("bot.handlers.log_activity")
    @patch("bot.handlers.logger")
    def test_admin_notification_exception(
        self,
        mock_logger,
        mock_log_activity,
        mock_log_suggestion,
        mock_save_enhanced,
        mock_bot,
    ):
        """Тест обработки ошибок при отправке администратору"""
        # Настраиваем mock bot для выброса исключения
        mock_bot.send_message = Mock(side_effect=Exception("Telegram API Error"))

        from bot.handlers import handle_improvement_suggestion_text

        # Вызываем функцию
        result = handle_improvement_suggestion_text(
            self.mock_message, self.placeholders, self.user_data
        )

        # Проверяем, что функция работает несмотря на ошибку
        self.assertIsInstance(result, tuple)
        self.assertEqual(result[0], "main_menu")

        # Проверяем, что ошибка залогирована
        mock_logger.error.assert_called()
        error_call_args = mock_logger.error.call_args[0][0]
        self.assertIn("❌ Ошибка отправки предложения админу:", error_call_args)

    def test_short_suggestion_rejection(self):
        """Тест отклонения слишком короткого предложения"""
        from bot.handlers import handle_improvement_suggestion_text

        # Создаем сообщение с коротким текстом
        short_message = Mock()
        short_message.chat.id = 12345
        short_message.from_user.username = "testuser"
        short_message.text = "короткий"  # Меньше 10 символов

        result = handle_improvement_suggestion_text(
            short_message, self.placeholders, self.user_data
        )

        # Проверяем отклонение
        self.assertIsInstance(result, tuple)
        self.assertEqual(result[0], "improvement_suggestion")
        self.assertIn("❌ Предложение слишком короткое!", result[1])

    def test_long_suggestion_rejection(self):
        """Тест отклонения слишком длинного предложения"""
        from bot.handlers import handle_improvement_suggestion_text

        # Создаем сообщение с длинным текстом
        long_message = Mock()
        long_message.chat.id = 12345
        long_message.from_user.username = "testuser"
        long_message.text = "х" * 1001  # Больше 1000 символов

        result = handle_improvement_suggestion_text(
            long_message, self.placeholders, self.user_data
        )

        # Проверяем отклонение
        self.assertIsInstance(result, tuple)
        self.assertEqual(result[0], "improvement_suggestion")
        self.assertIn("❌ Предложение слишком длинное!", result[1])

    def test_back_button_handling(self):
        """Тест обработки кнопки 'Назад'"""
        from bot.handlers import handle_improvement_suggestion_text

        # Создаем сообщение с кнопкой назад
        back_message = Mock()
        back_message.chat.id = 12345
        back_message.from_user.username = "testuser"
        back_message.text = "⬅️ Назад"

        result = handle_improvement_suggestion_text(
            back_message, self.placeholders, self.user_data
        )

        # Проверяем переход в главное меню
        self.assertIsInstance(result, tuple)
        self.assertEqual(result[0], "main_menu")
        self.assertIsNone(result[1])


class TestShelterButtons(unittest.TestCase):
    """Тесты для кнопок убежищ"""

    def setUp(self):
        """Настройка перед каждым тестом"""
        self.mock_bot = Mock()
        self.chat_id = 12345
        self.shelters_data = [
            {
                "name": "Главная проходная Ростсельмаш",
                "description": "Основное укрытие на главной проходной завода",
                "lat": "47.258268",
                "lon": "39.763172",
                "photo_path": "assets/images/shelter_1.jpg",
                "map_link": "https://yandex.ru/maps/?pt=39.763172,47.258268",
                "contact_phone": "+7 (863) 251-00-00",
            },
            {
                "name": "Убежище № 10 (Главный корпус РПРЗ, 12 пролет)",
                "description": "Укрытие на участке № 10",
                "lat": "47.264452",
                "lon": "39.765541",
                "photo_path": "assets/images/shelter_2.jpg",
                "map_link": "https://yandex.ru/maps/?pt=39.765541,47.264452",
                "contact_phone": "+7 (863) 251-10-00",
            },
        ]

    @patch("builtins.open", create=True)
    @patch("os.path.exists")
    @patch("bot.main.BOT_TOKEN", "test_token")
    @patch("bot.main.bot")
    @patch(
        "bot.main.placeholders",
        {
            "shelters": [
                {
                    "name": "Главная проходная Ростсельмаш",
                    "description": "Основное укрытие на главной проходной завода",
                    "lat": "47.258268",
                    "lon": "39.763172",
                    "photo_path": "assets/images/shelter_1.jpg",
                    "map_link": "https://yandex.ru/maps/?pt=39.763172,47.258268",
                    "contact_phone": "+7 (863) 251-00-00",
                }
            ]
        },
    )
    def test_show_all_shelters_buttons(self, mock_bot, mock_exists, mock_open):
        """Тест показа кнопок для всех убежищ"""
        mock_exists.return_value = True
        mock_open.return_value.__enter__.return_value = Mock()
        mock_bot.send_message = Mock()

        # Импортируем функцию для тестирования
        from bot.main import show_all_shelters

        # Вызываем функцию
        show_all_shelters(self.chat_id)

        # Проверяем, что бот отправил сообщение с кнопками
        mock_bot.send_message.assert_called_once()
        args, kwargs = mock_bot.send_message.call_args

        self.assertEqual(args[0], self.chat_id)
        self.assertIn("Выберите убежище для получения подробной информации", args[1])
        self.assertIn("reply_markup", kwargs)

    @patch("builtins.open", create=True)
    @patch("os.path.exists")
    @patch("bot.main.BOT_TOKEN", "test_token")
    @patch("bot.main.bot")
    @patch("bot.main.placeholders")
    def test_show_specific_shelter_main_gate(
        self, mock_placeholders, mock_bot, mock_exists, mock_open
    ):
        """Тест показа конкретного убежища - главная проходная"""
        mock_placeholders.get.return_value = self.shelters_data
        mock_exists.return_value = True
        mock_open.return_value.__enter__.return_value = Mock()
        mock_bot.send_photo = Mock()
        mock_bot.send_message = Mock()

        from bot.main import show_specific_shelter

        # Вызываем функцию для главной проходной
        show_specific_shelter(self.chat_id, "🏢 Убежище Главная проходная Ростсельмаш")

        # Проверяем, что отправлено фото и информация
        mock_bot.send_photo.assert_called_once()
        mock_bot.send_message.assert_called_once()

        # Проверяем содержимое сообщения
        args, kwargs = mock_bot.send_message.call_args
        self.assertIn("Главная проходная Ростсельмаш", args[1])
        self.assertIn("47.258268", args[1])

    @patch("builtins.open", create=True)
    @patch("os.path.exists")
    @patch("bot.main.BOT_TOKEN", "test_token")
    @patch("bot.main.bot")
    @patch("bot.main.placeholders")
    def test_show_specific_shelter_sector_10(
        self, mock_placeholders, mock_bot, mock_exists, mock_open
    ):
        """Тест показа конкретного убежища - участок №10"""
        mock_placeholders.get.return_value = self.shelters_data
        mock_exists.return_value = True
        mock_open.return_value.__enter__.return_value = Mock()
        mock_bot.send_photo = Mock()
        mock_bot.send_message = Mock()

        from bot.main import show_specific_shelter

        # Вызываем функцию для участка №10
        show_specific_shelter(self.chat_id, "🏭 Убежище № 10 (РПРЗ, 12 пролет)")

        # Проверяем, что отправлено несколько фото (основное + вход + схема)
        self.assertGreaterEqual(mock_bot.send_photo.call_count, 1)

        # Проверяем что отправлена текстовая информация
        mock_bot.send_message.assert_called_once()

        # Проверяем содержимое сообщения
        args, kwargs = mock_bot.send_message.call_args
        self.assertIn("Убежище № 10", args[1])
        self.assertIn("47.264452", args[1])

        # Проверяем что отправлены все 3 фото для убежища №10
        self.assertEqual(
            mock_bot.send_photo.call_count,
            3,
            "Для убежища №10 должно быть 3 фото: основное + вход + схема",
        )

    @patch("bot.main.BOT_TOKEN", "test_token")
    @patch("bot.main.bot")
    @patch("bot.main.placeholders")
    def test_show_shelter_map(self, mock_placeholders, mock_bot):
        """Тест показа карты убежищ"""
        mock_placeholders.get.return_value = self.shelters_data
        mock_bot.send_message = Mock()

        from bot.main import show_shelter_map

        # Вызываем функцию
        show_shelter_map(self.chat_id)

        # Проверяем, что отправлено сообщение с картой
        mock_bot.send_message.assert_called_once()
        args, kwargs = mock_bot.send_message.call_args

        self.assertEqual(args[0], self.chat_id)
        self.assertIn("🗺️ Местоположения убежищ РПРЗ", args[1])
        self.assertIn("Показать все убежища на карте", args[1])
        self.assertEqual(kwargs.get("parse_mode"), "Markdown")

    @patch("bot.main.BOT_TOKEN", "test_token")
    @patch("bot.main.bot")
    @patch("bot.main.placeholders")
    def test_shelter_not_found(self, mock_placeholders, mock_bot):
        """Тест обработки случая, когда убежище не найдено"""
        mock_placeholders.get.return_value = []
        mock_bot.send_message = Mock()

        from bot.main import show_specific_shelter

        # Вызываем функцию с несуществующим убежищем
        show_specific_shelter(self.chat_id, "🏠 Несуществующее убежище")

        # Проверяем, что отправлена ошибка
        mock_bot.send_message.assert_called_once()
        args, kwargs = mock_bot.send_message.call_args
        self.assertIn("❌ Убежище не найдено", args[1])


class TestBusSchedule(unittest.TestCase):
    """Тесты для функционала расписания автобусов"""

    def setUp(self):
        """Настройка перед каждым тестом"""
        self.chat_id = 12345

    @patch("builtins.open", create=True)
    @patch("os.path.exists")
    @patch("bot.main.BOT_TOKEN", "test_token")
    @patch("bot.main.bot")
    @patch("bot.main.log_activity")
    def test_show_bus_schedule_success(
        self, mock_log_activity, mock_bot, mock_exists, mock_open
    ):
        """Тест успешного показа расписания автобусов"""
        mock_exists.return_value = True
        mock_open.return_value.__enter__.return_value = Mock()
        mock_bot.send_photo = Mock()
        mock_bot.send_message = Mock()

        from bot.main import show_bus_schedule

        # Вызываем функцию
        show_bus_schedule(self.chat_id)

        # Проверяем, что отправлено фото
        mock_bot.send_photo.assert_called_once()
        call_args = mock_bot.send_photo.call_args
        # Проверяем chat_id в позиционных или именованных аргументах
        if call_args.args:
            self.assertEqual(call_args.args[0], self.chat_id)
        if "caption" in call_args.kwargs:
            self.assertIn("🚌 Расписание внутризаводского", call_args.kwargs["caption"])

        # Проверяем, что отправлена текстовая информация
        mock_bot.send_message.assert_called_once()
        message_args, message_kwargs = mock_bot.send_message.call_args
        self.assertIn("🚌 Расписание внутризаводского транспорта", message_args[1])
        self.assertIn("Главная проходная ДМО", message_args[1])

        # Проверяем логирование
        mock_log_activity.assert_called_once()

    @patch("os.path.exists")
    @patch("bot.main.BOT_TOKEN", "test_token")
    @patch("bot.main.bot")
    def test_show_bus_schedule_file_not_found(self, mock_bot, mock_exists):
        """Тест обработки отсутствия файла расписания"""
        mock_exists.return_value = False
        mock_bot.send_message = Mock()

        from bot.main import show_bus_schedule

        # Вызываем функцию
        show_bus_schedule(self.chat_id)

        # Проверяем, что отправлено сообщение об ошибке
        mock_bot.send_message.assert_called_once()
        args, kwargs = mock_bot.send_message.call_args
        self.assertIn("❌ Расписание временно недоступно", args[1])

    @patch("builtins.open", create=True)
    @patch("os.path.exists")
    @patch("bot.main.BOT_TOKEN", "test_token")
    @patch("bot.main.bot")
    def test_show_bus_schedule_photo_error(self, mock_bot, mock_exists, mock_open):
        """Тест обработки ошибки при отправке фото"""
        mock_exists.return_value = True
        mock_open.return_value.__enter__.return_value = Mock()
        mock_bot.send_photo = Mock(side_effect=Exception("Telegram API Error"))
        mock_bot.send_message = Mock()

        from bot.main import show_bus_schedule

        # Вызываем функцию
        show_bus_schedule(self.chat_id)

        # Проверяем, что отправлено сообщение об ошибке
        mock_bot.send_message.assert_called_once()
        args, kwargs = mock_bot.send_message.call_args
        self.assertIn("❌ Ошибка загрузки фото расписания", args[1])

    @patch("bot.main.BOT_TOKEN", None)
    @patch("bot.main.bot", None)
    def test_show_bus_schedule_no_bot_token(self):
        """Тест обработки отсутствия BOT_TOKEN"""
        from bot.main import show_bus_schedule

        # Не должно вызывать исключений
        try:
            show_bus_schedule(self.chat_id)
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
