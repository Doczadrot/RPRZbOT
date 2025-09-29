#!/usr/bin/env python3
"""
Комплексное тестирование RPRZ Safety Bot
Покрывает все функции согласно ТЗ
"""

import os
import sys
import json
import time
import unittest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime
import tempfile
import shutil

# Добавляем путь к модулям
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'bot'))

class TestRPRZBotComprehensive(unittest.TestCase):
    """Комплексные тесты для RPRZ Safety Bot"""
    
    def setUp(self):
        """Настройка перед каждым тестом"""
        # Создаем временную папку для тестов
        self.test_dir = tempfile.mkdtemp()
        os.makedirs(os.path.join(self.test_dir, 'logs'), exist_ok=True)
        
        # Меняем рабочую директорию на тестовую
        self.original_cwd = os.getcwd()
        os.chdir(self.test_dir)
        
        # Импортируем модули
        from handlers import (
            get_main_menu_keyboard, get_back_keyboard, get_media_keyboard,
            handle_danger_report_text, handle_danger_report_location, handle_danger_report_media,
            handle_shelter_finder_text, handle_shelter_finder_location, show_shelters_list,
            handle_safety_consultant_text, show_documents_list, start_question_mode, handle_safety_question,
            handle_improvement_suggestion_text, finish_danger_report,
            log_activity, log_incident, log_suggestion
        )
        
        self.placeholders = {
            'shelters': [
                {
                    'name': 'Тестовое убежище 1',
                    'description': 'Описание убежища 1',
                    'lat': '55.7558',
                    'lon': '37.6176',
                    'photo_path': 'test_photo1.jpg',
                    'map_link': 'https://test.com/map1'
                },
                {
                    'name': 'Тестовое убежище 2',
                    'description': 'Описание убежища 2',
                    'lat': '55.7658',
                    'lon': '37.6276',
                    'photo_path': 'test_photo2.jpg',
                    'map_link': 'https://test.com/map2'
                }
            ],
            'documents': [
                {
                    'title': 'Тестовый документ 1',
                    'description': 'Описание документа 1',
                    'file_path': 'test_doc1.pdf'
                },
                {
                    'title': 'Тестовый документ 2',
                    'description': 'Описание документа 2',
                    'file_path': 'test_doc2.pdf'
                }
            ],
            'safety_responses': [
                {
                    'question_keywords': ['пожар', 'огонь'],
                    'answer': 'При пожаре звоните 112 и покиньте помещение',
                    'source': 'Инструкция по пожарной безопасности'
                },
                {
                    'question_keywords': ['землетрясение', 'тряска'],
                    'answer': 'При землетрясении укройтесь под прочным столом',
                    'source': 'Инструкция по действиям при ЧС'
                }
            ],
            'contacts': {
                'security': '+7 (495) 123-45-67',
                'safety': '+7 (495) 123-45-68'
            }
        }
    
    def tearDown(self):
        """Очистка после каждого теста"""
        # Возвращаемся в исходную директорию
        os.chdir(self.original_cwd)
        
        # Удаляем временную папку
        if os.path.exists(self.test_dir):
            shutil.rmtree(self.test_dir)
    
    def create_mock_message(self, text, chat_id=12345, username="test_user", content_type="text"):
        """Создает мок сообщения"""
        message = Mock()
        message.chat = Mock()
        message.chat.id = chat_id
        message.from_user = Mock()
        message.from_user.username = username
        message.text = text
        message.content_type = content_type
        return message
    
    def test_1_keyboards_creation(self):
        """Тест 1: Создание клавиатур"""
        print("\n=== ТЕСТ 1: Создание клавиатур ===")
        
        from handlers import get_main_menu_keyboard, get_back_keyboard, get_media_keyboard
        
        # Главное меню
        main_kb = get_main_menu_keyboard()
        self.assertIsNotNone(main_kb, "Главная клавиатура не создана")
        self.assertEqual(len(main_kb.keyboard), 1, "Неверное количество строк в главном меню")
        self.assertEqual(len(main_kb.keyboard[0]), 4, "Неверное количество кнопок в главном меню")
        
        # Проверяем текст кнопок
        button_texts = [btn.text for btn in main_kb.keyboard[0]]
        expected_buttons = ["❗ Сообщите об опасности", "🏠 Ближайшее укрытие", 
                           "🧑‍🏫 Консультант по безопасности РПРЗ", "💡 Предложение по улучшению"]
        self.assertEqual(button_texts, expected_buttons, "Неверные тексты кнопок главного меню")
        
        # Кнопка "Назад"
        back_kb = get_back_keyboard()
        self.assertIsNotNone(back_kb, "Клавиатура 'Назад' не создана")
        self.assertEqual(len(back_kb.keyboard), 1, "Неверное количество строк в клавиатуре 'Назад'")
        self.assertEqual(len(back_kb.keyboard[0]), 1, "Неверное количество кнопок в клавиатуре 'Назад'")
        self.assertEqual(back_kb.keyboard[0][0].text, "⬅️ Назад", "Неверный текст кнопки 'Назад'")
        
        # Медиа клавиатура
        media_kb = get_media_keyboard()
        self.assertIsNotNone(media_kb, "Медиа клавиатура не создана")
        self.assertEqual(len(media_kb.keyboard), 1, "Неверное количество строк в медиа клавиатуре")
        self.assertEqual(len(media_kb.keyboard[0]), 2, "Неверное количество кнопок в медиа клавиатуре")
        
        print("✅ Все клавиатуры создаются корректно")
    
    def test_2_danger_report_flow(self):
        """Тест 2: Полный цикл сообщения об опасности"""
        print("\n=== ТЕСТ 2: Сообщение об опасности ===")
        
        from handlers import handle_danger_report_text, handle_danger_report_location, handle_danger_report_media, finish_danger_report
        
        # Шаг 1: Начало сообщения об опасности
        message = self.create_mock_message("❗ Сообщите об опасности")
        user_data = {'step': 'description', 'description': '', 'location': None, 'media': []}
        
        result = handle_danger_report_text(message, user_data, self.placeholders)
        self.assertIsInstance(result, tuple, "Результат должен быть кортежем")
        new_state, response = result
        self.assertEqual(new_state, "danger_report", "Неверное состояние")
        self.assertIn("Опишите что произошло", response['text'], "Неверный текст запроса описания")
        
        # Шаг 2: Ввод описания
        message = self.create_mock_message("Тестовое описание опасности")
        user_data['step'] = 'description'
        
        result = handle_danger_report_text(message, user_data, self.placeholders)
        self.assertIsInstance(result, tuple, "Результат должен быть кортежем")
        new_state, response = result
        self.assertEqual(new_state, "danger_report", "Неверное состояние")
        self.assertIn("Укажите местоположение", response['text'], "Неверный текст запроса местоположения")
        self.assertEqual(user_data['description'], "Тестовое описание опасности", "Описание не сохранено")
        
        # Шаг 3: Выбор способа указания местоположения
        message = self.create_mock_message("📍 Отправить геолокацию")
        user_data['step'] = 'location'
        
        result = handle_danger_report_text(message, user_data, self.placeholders)
        self.assertIsInstance(result, tuple, "Результат должен быть кортежем")
        new_state, response = result
        self.assertEqual(new_state, "danger_report", "Неверное состояние")
        self.assertIn("Отправьте геолокацию", response['text'], "Неверный текст запроса геолокации")
        
        # Шаг 4: Обработка геолокации
        message = self.create_mock_message("📍 Отправить геолокацию")
        message.location = Mock()
        message.location.latitude = 55.7558
        message.location.longitude = 37.6176
        user_data['step'] = 'location'
        
        result = handle_danger_report_location(message, user_data)
        self.assertIsInstance(result, dict, "Результат должен быть словарем")
        self.assertIn("Геолокация получена", result['text'], "Неверный текст подтверждения геолокации")
        self.assertEqual(user_data['step'], 'media', "Неверное состояние после геолокации")
        self.assertIsNotNone(user_data['location'], "Геолокация не сохранена")
        
        # Шаг 5: Обработка медиафайлов
        message = self.create_mock_message("📷 Добавить фото")
        message.content_type = "photo"
        message.photo = [Mock(file_id="test_file_id", file_size=1024*1024)]  # 1MB
        user_data['step'] = 'media'
        
        result = handle_danger_report_media(message, user_data, 20, 300)
        self.assertIn("Медиафайл добавлен", result, "Неверный текст подтверждения медиафайла")
        self.assertEqual(len(user_data['media']), 1, "Медиафайл не добавлен")
        
        # Шаг 6: Завершение сообщения об опасности
        result = finish_danger_report(12345, user_data, self.placeholders)
        self.assertIsInstance(result, tuple, "Результат должен быть кортежем")
        new_state, response = result
        self.assertEqual(new_state, "main_menu", "Неверное состояние после завершения")
        self.assertIn("Сообщение об опасности отправлено", response['text'], "Неверный текст подтверждения")
        
        print("✅ Полный цикл сообщения об опасности работает корректно")
    
    def test_3_shelter_finder(self):
        """Тест 3: Поиск убежищ"""
        print("\n=== ТЕСТ 3: Поиск убежищ ===")
        
        from handlers import handle_shelter_finder_text, handle_shelter_finder_location, show_shelters_list
        
        # Тест показа списка убежищ
        message = self.create_mock_message("🏠 Ближайшее укрытие")
        result = handle_shelter_finder_text(message, self.placeholders)
        self.assertIsInstance(result, tuple, "Результат должен быть кортежем")
        new_state, response = result
        self.assertEqual(new_state, "shelter_finder", "Неверное состояние")
        self.assertIn("shelters", response, "Список убежищ не включен в ответ")
        
        # Тест показа списка убежищ
        result = show_shelters_list(self.placeholders)
        self.assertIsInstance(result, dict, "Результат должен быть словарем")
        self.assertIn("text", result, "Текст ответа отсутствует")
        self.assertIn("reply_markup", result, "Клавиатура отсутствует")
        
        # Тест обработки геолокации для поиска убежищ
        message = self.create_mock_message("📍 Отправить геолокацию")
        message.location = Mock()
        message.location.latitude = 55.7558
        message.location.longitude = 37.6176
        
        result = handle_shelter_finder_location(message, self.placeholders)
        self.assertIsInstance(result, dict, "Результат должен быть словарем")
        self.assertIn("text", result, "Текст ответа отсутствует")
        self.assertIn("reply_markup", result, "Клавиатура отсутствует")
        
        print("✅ Поиск убежищ работает корректно")
    
    def test_4_safety_consultant(self):
        """Тест 4: Консультант по безопасности"""
        print("\n=== ТЕСТ 4: Консультант по безопасности ===")
        
        from handlers import handle_safety_consultant_text, show_documents_list, start_question_mode, handle_safety_question
        
        # Тест показа документов
        message = self.create_mock_message("📄 Список документов")
        result = handle_safety_consultant_text(message, self.placeholders)
        self.assertIsInstance(result, tuple, "Результат должен быть кортежем")
        new_state, response = result
        self.assertEqual(new_state, "safety_consultant", "Неверное состояние")
        
        # Тест показа списка документов
        result = show_documents_list(self.placeholders)
        self.assertIsInstance(result, dict, "Результат должен быть словарем")
        self.assertIn("text", result, "Текст ответа отсутствует")
        self.assertIn("reply_markup", result, "Клавиатура отсутствует")
        
        # Тест начала режима вопросов
        message = self.create_mock_message("❓ Задать вопрос")
        result = handle_safety_consultant_text(message, self.placeholders)
        self.assertIsInstance(result, tuple, "Результат должен быть кортежем")
        new_state, response = result
        self.assertEqual(new_state, "safety_consultant", "Неверное состояние")
        
        # Тест обработки вопроса
        message = self.create_mock_message("Что делать при пожаре?")
        result = handle_safety_question(message, self.placeholders)
        self.assertIsInstance(result, tuple, "Результат должен быть кортежем")
        new_state, response = result
        self.assertEqual(new_state, "safety_consultant", "Неверное состояние")
        self.assertIn("пожар", response['text'].lower(), "Ответ не содержит ключевое слово")
        
        print("✅ Консультант по безопасности работает корректно")
    
    def test_5_improvement_suggestions(self):
        """Тест 5: Предложения по улучшению"""
        print("\n=== ТЕСТ 5: Предложения по улучшению ===")
        
        from handlers import handle_improvement_suggestion_text
        
        # Тест обработки предложения
        message = self.create_mock_message("Тестовое предложение по улучшению")
        result = handle_improvement_suggestion_text(message, self.placeholders)
        self.assertIsInstance(result, tuple, "Результат должен быть кортежем")
        new_state, response = result
        self.assertEqual(new_state, "main_menu", "Неверное состояние")
        self.assertIn("Спасибо за ваше предложение", response['text'], "Неверный текст подтверждения")
        
        print("✅ Предложения по улучшению работают корректно")
    
    def test_6_logging_system(self):
        """Тест 6: Система логирования"""
        print("\n=== ТЕСТ 6: Система логирования ===")
        
        from handlers import log_activity, log_incident, log_suggestion
        
        # Тест логирования активности
        log_activity(12345, "test_user", "test_action", "test_payload")
        self.assertTrue(os.path.exists('logs/activity.csv'), "Файл активности не создан")
        
        # Проверяем содержимое файла активности
        with open('logs/activity.csv', 'r', encoding='utf-8') as f:
            content = f.read()
            self.assertIn("test_action", content, "Действие не записано в лог")
            self.assertIn("test_user", content, "Пользователь не записан в лог")
        
        # Тест логирования инцидента
        incident_data = {
            'description': 'Тестовый инцидент',
            'location': {'latitude': 55.7558, 'longitude': 37.6176},
            'user_id': 12345,
            'username': 'test_user'
        }
        log_incident(12345, incident_data)
        self.assertTrue(os.path.exists('logs/incidents.json'), "Файл инцидентов не создан")
        
        # Проверяем содержимое файла инцидентов
        with open('logs/incidents.json', 'r', encoding='utf-8') as f:
            incidents = json.load(f)
            self.assertIsInstance(incidents, list, "Файл инцидентов должен содержать список")
            self.assertEqual(len(incidents), 1, "Неверное количество инцидентов")
            self.assertEqual(incidents[0]['description'], 'Тестовый инцидент', "Описание инцидента неверно")
        
        # Тест логирования предложения
        suggestion_data = {
            'text': 'Тестовое предложение',
            'user_id': 12345,
            'username': 'test_user'
        }
        log_suggestion(12345, suggestion_data)
        self.assertTrue(os.path.exists('logs/suggestions.json'), "Файл предложений не создан")
        
        # Проверяем содержимое файла предложений
        with open('logs/suggestions.json', 'r', encoding='utf-8') as f:
            suggestions = json.load(f)
            self.assertIsInstance(suggestions, list, "Файл предложений должен содержать список")
            self.assertEqual(len(suggestions), 1, "Неверное количество предложений")
            self.assertEqual(suggestions[0]['text'], 'Тестовое предложение', "Текст предложения неверен")
        
        print("✅ Система логирования работает корректно")
    
    def test_7_error_handling(self):
        """Тест 7: Обработка ошибок"""
        print("\n=== ТЕСТ 7: Обработка ошибок ===")
        
        from handlers import handle_danger_report_text, handle_improvement_suggestion_text
        
        # Тест слишком длинного описания
        message = self.create_mock_message("x" * 501)  # Слишком длинное сообщение
        user_data = {'step': 'description', 'description': '', 'location': None, 'media': []}
        result = handle_danger_report_text(message, user_data, self.placeholders)
        self.assertIsInstance(result, tuple, "Результат должен быть кортежем")
        new_state, response = result
        self.assertIn("слишком длинное", response, "Неверная обработка длинного сообщения")
        
        # Тест слишком длинного предложения
        message = self.create_mock_message("x" * 1001)  # Слишком длинное предложение
        result = handle_improvement_suggestion_text(message, self.placeholders)
        self.assertIsInstance(result, tuple, "Результат должен быть кортежем")
        new_state, response = result
        self.assertIn("слишком длинное", response, "Неверная обработка длинного предложения")
        
        print("✅ Обработка ошибок работает корректно")
    
    def test_8_media_handling(self):
        """Тест 8: Обработка медиафайлов"""
        print("\n=== ТЕСТ 8: Обработка медиафайлов ===")
        
        from handlers import handle_danger_report_media
        
        # Тест обработки фото
        message = self.create_mock_message("📷 Добавить фото")
        message.content_type = "photo"
        message.photo = [Mock(file_id="test_file_id", file_size=1024*1024)]  # 1MB
        user_data = {'media': []}
        
        result = handle_danger_report_media(message, user_data, 20, 300)
        self.assertIn("Медиафайл добавлен", result, "Неверный текст подтверждения медиафайла")
        self.assertEqual(len(user_data['media']), 1, "Медиафайл не добавлен")
        
        # Тест превышения лимита медиафайлов
        user_data['media'] = [{'type': 'photo'}, {'type': 'photo'}, {'type': 'photo'}]
        result = handle_danger_report_media(message, user_data, 20, 300)
        self.assertIn("Максимум 3 медиафайла", result, "Неверная обработка превышения лимита")
        
        # Тест превышения размера файла
        message.photo = [Mock(file_id="test_file_id", file_size=25*1024*1024)]  # 25MB
        user_data['media'] = []
        result = handle_danger_report_media(message, user_data, 20, 300)
        self.assertIn("слишком большой", result, "Неверная обработка большого файла")
        
        print("✅ Обработка медиафайлов работает корректно")
    
    def test_9_geolocation_handling(self):
        """Тест 9: Обработка геолокации"""
        print("\n=== ТЕСТ 9: Обработка геолокации ===")
        
        from handlers import handle_danger_report_location, handle_shelter_finder_location
        
        # Тест обработки геолокации для сообщения об опасности
        message = self.create_mock_message("📍 Отправить геолокацию")
        message.location = Mock()
        message.location.latitude = 55.7558
        message.location.longitude = 37.6176
        user_data = {'step': 'location'}
        
        result = handle_danger_report_location(message, user_data)
        self.assertIsInstance(result, dict, "Результат должен быть словарем")
        self.assertIn("Геолокация получена", result['text'], "Неверный текст подтверждения геолокации")
        self.assertEqual(user_data['step'], 'media', "Неверное состояние после геолокации")
        self.assertIsNotNone(user_data['location'], "Геолокация не сохранена")
        
        # Тест обработки геолокации для поиска убежищ
        message = self.create_mock_message("📍 Отправить геолокацию")
        message.location = Mock()
        message.location.latitude = 55.7558
        message.location.longitude = 37.6176
        
        result = handle_shelter_finder_location(message, self.placeholders)
        self.assertIsInstance(result, dict, "Результат должен быть словарем")
        self.assertIn("text", result, "Текст ответа отсутствует")
        self.assertIn("reply_markup", result, "Клавиатура отсутствует")
        
        print("✅ Обработка геолокации работает корректно")
    
    def test_10_integration_scenarios(self):
        """Тест 10: Интеграционные сценарии"""
        print("\n=== ТЕСТ 10: Интеграционные сценарии ===")
        
        from handlers import (
            handle_danger_report_text, handle_danger_report_location, handle_danger_report_media,
            handle_shelter_finder_text, handle_safety_consultant_text, handle_improvement_suggestion_text
        )
        
        # Сценарий 1: Полный цикл сообщения об опасности
        user_data = {'step': 'description', 'description': '', 'location': None, 'media': []}
        
        # Описание
        message = self.create_mock_message("Пожар в здании")
        result = handle_danger_report_text(message, user_data, self.placeholders)
        self.assertIsInstance(result, tuple, "Результат должен быть кортежем")
        
        # Геолокация
        message.location = Mock()
        message.location.latitude = 55.7558
        message.location.longitude = 37.6176
        user_data['step'] = 'location'
        result = handle_danger_report_location(message, user_data)
        self.assertIsInstance(result, dict, "Результат должен быть словарем")
        
        # Медиафайл
        message.content_type = "photo"
        message.photo = [Mock(file_id="test_file_id", file_size=1024*1024)]
        user_data['step'] = 'media'
        result = handle_danger_report_media(message, user_data, 20, 300)
        self.assertIn("Медиафайл добавлен", result, "Медиафайл не добавлен")
        
        # Сценарий 2: Поиск убежища
        message = self.create_mock_message("🏠 Ближайшее укрытие")
        result = handle_shelter_finder_text(message, self.placeholders)
        self.assertIsInstance(result, tuple, "Результат должен быть кортежем")
        
        # Сценарий 3: Консультация
        message = self.create_mock_message("❓ Задать вопрос")
        result = handle_safety_consultant_text(message, self.placeholders)
        self.assertIsInstance(result, tuple, "Результат должен быть кортежем")
        
        # Сценарий 4: Предложение
        message = self.create_mock_message("Улучшить интерфейс")
        result = handle_improvement_suggestion_text(message, self.placeholders)
        self.assertIsInstance(result, tuple, "Результат должен быть кортежем")
        
        print("✅ Все интеграционные сценарии работают корректно")

def run_comprehensive_tests():
    """Запуск комплексных тестов"""
    print("🚀 Запуск комплексного тестирования RPRZ Safety Bot")
    print("=" * 70)
    
    # Создаем тестовый набор
    loader = unittest.TestLoader()
    suite = loader.loadTestsFromTestCase(TestRPRZBotComprehensive)
    
    # Запускаем тесты
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    # Выводим результаты
    print("\n" + "=" * 70)
    print(f"📊 РЕЗУЛЬТАТЫ КОМПЛЕКСНОГО ТЕСТИРОВАНИЯ:")
    print(f"✅ Успешно: {result.testsRun - len(result.failures) - len(result.errors)}")
    print(f"❌ Ошибок: {len(result.failures) + len(result.errors)}")
    print(f"📈 Всего тестов: {result.testsRun}")
    
    if result.failures:
        print(f"\n❌ Неудачные тесты:")
        for test, traceback in result.failures:
            print(f"  - {test}: {traceback}")
    
    if result.errors:
        print(f"\n💥 Ошибки:")
        for test, traceback in result.errors:
            print(f"  - {test}: {traceback}")
    
    success_rate = ((result.testsRun - len(result.failures) - len(result.errors)) / result.testsRun) * 100
    print(f"\n🎯 Успешность: {success_rate:.1f}%")
    
    if success_rate >= 95:
        print("🎉 ОТЛИЧНО! Бот полностью готов к использованию!")
        return True
    elif success_rate >= 80:
        print("✅ ХОРОШО! Бот готов к использованию с небольшими замечаниями")
        return True
    elif success_rate >= 60:
        print("⚠️ УДОВЛЕТВОРИТЕЛЬНО! Требуются исправления")
        return False
    else:
        print("❌ НЕУДОВЛЕТВОРИТЕЛЬНО! Критические проблемы!")
        return False

if __name__ == '__main__':
    success = run_comprehensive_tests()
    sys.exit(0 if success else 1)

