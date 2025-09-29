#!/usr/bin/env python3
"""
Полное тестирование функционала RPRZ Safety Bot
"""

import os
import sys
import json
import time
import unittest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime

# Добавляем путь к модулям
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'bot'))

# Импорты
from handlers import (
    get_main_menu_keyboard, get_back_keyboard, get_media_keyboard,
    handle_danger_report_text, handle_danger_report_location, handle_danger_report_media,
    handle_shelter_finder_text, handle_shelter_finder_location, show_shelters_list,
    handle_safety_consultant_text, show_documents_list, start_question_mode, handle_safety_question,
    handle_improvement_suggestion_text, finish_danger_report,
    log_activity, log_incident, log_suggestion
)

class TestRPRZBot(unittest.TestCase):
    """Тесты для RPRZ Safety Bot"""
    
    def setUp(self):
        """Настройка перед каждым тестом"""
        self.placeholders = {
            'shelters': [
                {
                    'name': 'Тестовое убежище 1',
                    'description': 'Описание убежища 1',
                    'lat': '55.7558',
                    'lon': '37.6176',
                    'photo_path': 'test_photo1.jpg',
                    'map_link': 'https://test.com/map1'
                }
            ],
            'documents': [
                {
                    'title': 'Тестовый документ',
                    'description': 'Описание документа',
                    'file_path': 'test_doc.pdf'
                }
            ],
            'safety_responses': [
                {
                    'question_keywords': ['пожар'],
                    'answer': 'При пожаре звоните 112',
                    'source': 'Инструкция по пожарной безопасности'
                }
            ],
            'contacts': {
                'security': '+7 (495) 123-45-67',
                'safety': '+7 (495) 123-45-68'
            }
        }
        
        # Создаем папку для тестовых логов
        os.makedirs('test_logs', exist_ok=True)
        
    def tearDown(self):
        """Очистка после каждого теста"""
        # Удаляем тестовые файлы
        test_files = ['test_logs/activity.csv', 'test_logs/incidents.json', 'test_logs/suggestions.json']
        for file_path in test_files:
            if os.path.exists(file_path):
                os.remove(file_path)
    
    def test_keyboards(self):
        """Тест создания клавиатур"""
        print("🧪 Тестирование клавиатур...")
        
        # Главное меню
        main_kb = get_main_menu_keyboard()
        self.assertIsNotNone(main_kb)
        self.assertEqual(len(main_kb.keyboard), 1)  # Одна строка
        self.assertEqual(len(main_kb.keyboard[0]), 4)  # Четыре кнопки
        
        # Кнопка "Назад"
        back_kb = get_back_keyboard()
        self.assertIsNotNone(back_kb)
        self.assertEqual(len(back_kb.keyboard), 1)
        self.assertEqual(len(back_kb.keyboard[0]), 1)
        
        # Медиа клавиатура
        media_kb = get_media_keyboard()
        self.assertIsNotNone(media_kb)
        self.assertEqual(len(media_kb.keyboard), 1)
        self.assertEqual(len(media_kb.keyboard[0]), 2)
        
        print("✅ Клавиатуры работают корректно")
    
    def test_danger_report_flow(self):
        """Тест полного цикла сообщения об опасности"""
        print("🧪 Тестирование сообщения об опасности...")
        
        # Создаем мок сообщения
        message = Mock()
        message.chat.id = 12345
        message.from_user.username = "test_user"
        message.text = "Тестовое сообщение об опасности"
        
        user_data = {'step': 'description', 'description': '', 'location': None}
        
        # Шаг 1: Описание
        result = handle_danger_report_text(message, user_data, self.placeholders)
        self.assertIsInstance(result, tuple)
        new_state, response = result
        self.assertEqual(new_state, "danger_report")
        self.assertIn("Укажите местоположение", response['text'])
        
        # Шаг 2: Место (текстом)
        message.text = "📝 Указать текстом"
        user_data['step'] = 'location'
        result = handle_danger_report_text(message, user_data, self.placeholders)
        self.assertIsInstance(result, tuple)
        new_state, response = result
        self.assertEqual(new_state, "danger_report")
        self.assertIn("Укажите местоположение", response['text'])
        
        # Шаг 3: Ввод адреса
        message.text = "Тестовый адрес"
        user_data['step'] = 'location_text'
        result = handle_danger_report_text(message, user_data, self.placeholders)
        self.assertIsInstance(result, tuple)
        new_state, response = result
        self.assertEqual(new_state, "danger_report")
        self.assertIn("Медиафайлов", response['text'])
        
        print("✅ Сообщение об опасности работает корректно")
    
    def test_shelter_finder(self):
        """Тест поиска убежищ"""
        print("🧪 Тестирование поиска убежищ...")
        
        message = Mock()
        message.chat.id = 12345
        message.from_user.username = "test_user"
        message.text = "📋 Показать список убежищ"
        
        # Тест показа списка убежищ
        result = handle_shelter_finder_text(message, self.placeholders)
        self.assertIsInstance(result, tuple)
        new_state, response = result
        self.assertEqual(new_state, "shelter_finder")
        self.assertIn("shelters", response)
        
        print("✅ Поиск убежищ работает корректно")
    
    def test_safety_consultant(self):
        """Тест консультанта по безопасности"""
        print("🧪 Тестирование консультанта...")
        
        message = Mock()
        message.chat.id = 12345
        message.from_user.username = "test_user"
        message.text = "📄 Список документов"
        
        # Тест показа документов
        result = handle_safety_consultant_text(message, self.placeholders)
        self.assertIsInstance(result, tuple)
        new_state, response = result
        self.assertEqual(new_state, "safety_consultant")
        
        # Тест вопросов
        message.text = "❓ Задать вопрос"
        result = handle_safety_consultant_text(message, self.placeholders)
        self.assertIsInstance(result, tuple)
        new_state, response = result
        self.assertEqual(new_state, "safety_consultant")
        
        # Тест ответа на вопрос
        message.text = "Что делать при пожаре?"
        result = handle_safety_question(message, self.placeholders)
        self.assertIsInstance(result, tuple)
        new_state, response = result
        self.assertEqual(new_state, "safety_consultant")
        self.assertIn("пожар", response['text'].lower())
        
        print("✅ Консультант работает корректно")
    
    def test_improvement_suggestion(self):
        """Тест предложений по улучшению"""
        print("🧪 Тестирование предложений...")
        
        message = Mock()
        message.chat.id = 12345
        message.from_user.username = "test_user"
        message.text = "Тестовое предложение по улучшению"
        
        result = handle_improvement_suggestion_text(message, self.placeholders)
        self.assertIsInstance(result, tuple)
        new_state, response = result
        self.assertEqual(new_state, "main_menu")
        self.assertIn("Спасибо за ваше предложение", response['text'])
        
        print("✅ Предложения работают корректно")
    
    def test_logging_functions(self):
        """Тест функций логирования"""
        print("🧪 Тестирование логирования...")
        
        # Тест логирования активности
        log_activity(12345, "test_user", "test_action", "test_payload")
        self.assertTrue(os.path.exists('logs/activity.csv'))
        
        # Тест логирования инцидента
        incident_data = {
            'description': 'Тестовый инцидент',
            'location': {'latitude': 55.7558, 'longitude': 37.6176},
            'user_id': 12345,
            'username': 'test_user'
        }
        log_incident(12345, incident_data)
        self.assertTrue(os.path.exists('logs/incidents.json'))
        
        # Тест логирования предложения
        suggestion_data = {
            'text': 'Тестовое предложение',
            'user_id': 12345,
            'username': 'test_user'
        }
        log_suggestion(12345, suggestion_data)
        self.assertTrue(os.path.exists('logs/suggestions.json'))
        
        print("✅ Логирование работает корректно")
    
    def test_media_handling(self):
        """Тест обработки медиафайлов"""
        print("🧪 Тестирование медиафайлов...")
        
        message = Mock()
        message.chat.id = 12345
        message.from_user.username = "test_user"
        message.content_type = "photo"
        message.photo = [Mock(file_id="test_file_id", file_size=1024*1024)]  # 1MB
        message.video = None
        message.document = None
        
        user_data = {'media': []}
        
        # Тест обработки фото
        result = handle_danger_report_media(message, user_data, 20, 300)
        self.assertIn("Медиафайл добавлен", result)
        self.assertEqual(len(user_data['media']), 1)
        
        # Тест превышения лимита
        user_data['media'] = [{'type': 'photo'}, {'type': 'photo'}, {'type': 'photo'}]
        result = handle_danger_report_media(message, user_data, 20, 300)
        self.assertIn("Максимум 3 медиафайла", result)
        
        print("✅ Обработка медиафайлов работает корректно")
    
    def test_geolocation_handling(self):
        """Тест обработки геолокации"""
        print("🧪 Тестирование геолокации...")
        
        message = Mock()
        message.chat.id = 12345
        message.from_user.username = "test_user"
        message.location = Mock()
        message.location.latitude = 55.7558
        message.location.longitude = 37.6176
        
        user_data = {'step': 'location'}
        
        result = handle_danger_report_location(message, user_data)
        self.assertIsInstance(result, dict)
        self.assertIn("Геолокация получена", result['text'])
        self.assertEqual(user_data['step'], 'media')
        
        print("✅ Обработка геолокации работает корректно")
    
    def test_error_handling(self):
        """Тест обработки ошибок"""
        print("🧪 Тестирование обработки ошибок...")
        
        # Тест слишком длинного описания
        message = Mock()
        message.chat.id = 12345
        message.from_user.username = "test_user"
        message.text = "x" * 501  # Слишком длинное сообщение
        
        user_data = {'step': 'description', 'description': '', 'location': None}
        result = handle_danger_report_text(message, user_data, self.placeholders)
        self.assertIsInstance(result, tuple)
        new_state, response = result
        self.assertIn("слишком длинное", response)
        
        # Тест слишком длинного предложения
        message.text = "x" * 1001  # Слишком длинное предложение
        result = handle_improvement_suggestion_text(message, self.placeholders)
        self.assertIsInstance(result, tuple)
        new_state, response = result
        self.assertIn("слишком длинное", response)
        
        print("✅ Обработка ошибок работает корректно")

def run_all_tests():
    """Запуск всех тестов"""
    print("🚀 Запуск полного тестирования RPRZ Safety Bot")
    print("=" * 60)
    
    # Создаем тестовый набор
    loader = unittest.TestLoader()
    suite = loader.loadTestsFromTestCase(TestRPRZBot)
    
    # Запускаем тесты
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    # Выводим результаты
    print("\n" + "=" * 60)
    print(f"📊 Результаты тестирования:")
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
    
    if success_rate >= 90:
        print("🎉 Отлично! Бот готов к использованию!")
        return True
    elif success_rate >= 70:
        print("⚠️ Хорошо, но есть проблемы для исправления")
        return False
    else:
        print("❌ Критические проблемы! Требуется исправление")
        return False

if __name__ == '__main__':
    success = run_all_tests()
    sys.exit(0 if success else 1)

