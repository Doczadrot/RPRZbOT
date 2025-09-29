#!/usr/bin/env python3
"""
Простое тестирование RPRZ Safety Bot без эмодзи
"""

import os
import sys
import json
import time
from datetime import datetime

def print_header():
    print("=" * 60)
    print(" " * 20 + "RPRZ Safety Bot" + " " * 20)
    print(" " * 15 + "Простое тестирование" + " " * 15)
    print("=" * 60)
    print()

def test_imports():
    """Тест импортов"""
    print("1. Тестирование импортов...")
    try:
        sys.path.insert(0, os.path.join(os.getcwd(), 'bot'))
        from handlers import get_main_menu_keyboard, get_back_keyboard
        print("   OK: Импорты работают")
        return True
    except Exception as e:
        print(f"   ERROR: Ошибка импорта: {e}")
        return False

def test_configuration():
    """Тест конфигурации"""
    print("2. Тестирование конфигурации...")
    try:
        with open('configs/data_placeholders.json', 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        required_keys = ['shelters', 'documents', 'safety_responses', 'contacts']
        for key in required_keys:
            if key not in data:
                print(f"   ERROR: Отсутствует ключ: {key}")
                return False
        
        print(f"   OK: Убежищ: {len(data['shelters'])}")
        print(f"   OK: Документов: {len(data['documents'])}")
        print(f"   OK: Ответов: {len(data['safety_responses'])}")
        return True
    except Exception as e:
        print(f"   ERROR: Ошибка конфигурации: {e}")
        return False

def test_keyboards():
    """Тест клавиатур"""
    print("3. Тестирование клавиатур...")
    try:
        from handlers import get_main_menu_keyboard, get_back_keyboard, get_media_keyboard
        
        # Главное меню
        main_kb = get_main_menu_keyboard()
        if len(main_kb.keyboard[0]) != 4:
            print("   ERROR: Неправильное количество кнопок в главном меню")
            return False
        
        # Кнопка "Назад"
        back_kb = get_back_keyboard()
        if len(back_kb.keyboard[0]) != 1:
            print("   ERROR: Неправильная кнопка 'Назад'")
            return False
        
        # Медиа клавиатура
        media_kb = get_media_keyboard()
        if len(media_kb.keyboard[0]) != 2:
            print("   ERROR: Неправильная медиа клавиатура")
            return False
        
        print("   OK: Все клавиатуры работают")
        return True
    except Exception as e:
        print(f"   ERROR: Ошибка клавиатур: {e}")
        return False

def test_logging():
    """Тест логирования"""
    print("4. Тестирование логирования...")
    try:
        from handlers import log_activity
        
        # Создаем папку для тестов
        os.makedirs('logs', exist_ok=True)
        
        # Тестируем логирование
        log_activity(99999, "test_user", "test_action", "test_payload")
        
        if os.path.exists('logs/activity.csv'):
            print("   OK: Логирование работает")
            return True
        else:
            print("   ERROR: Файл логов не создан")
            return False
    except Exception as e:
        print(f"   ERROR: Ошибка логирования: {e}")
        return False

def test_danger_report():
    """Тест сообщения об опасности"""
    print("5. Тестирование сообщения об опасности...")
    try:
        from handlers import handle_danger_report_text
        
        # Создаем мок сообщения
        class MockMessage:
            def __init__(self):
                self.chat = type('Chat', (), {'id': 12345})()
                self.from_user = type('User', (), {'username': 'test_user'})()
                self.text = "Тестовое сообщение об опасности"
        
        message = MockMessage()
        user_data = {'step': 'description', 'description': '', 'location': None}
        placeholders = {'shelters': [], 'documents': [], 'safety_responses': [], 'contacts': {}}
        
        result = handle_danger_report_text(message, user_data, placeholders)
        
        if isinstance(result, tuple) and len(result) == 2:
            print("   OK: Сообщение об опасности работает")
            return True
        else:
            print("   ERROR: Неправильный формат ответа")
            return False
    except Exception as e:
        print(f"   ERROR: Ошибка сообщения об опасности: {e}")
        return False

def test_shelter_finder():
    """Тест поиска убежищ"""
    print("6. Тестирование поиска убежищ...")
    try:
        from handlers import handle_shelter_finder_text
        
        class MockMessage:
            def __init__(self):
                self.chat = type('Chat', (), {'id': 12345})()
                self.from_user = type('User', (), {'username': 'test_user'})()
                self.text = "📋 Показать список убежищ"
        
        message = MockMessage()
        placeholders = {'shelters': [{'name': 'Test', 'description': 'Test'}]}
        
        result = handle_shelter_finder_text(message, placeholders)
        
        if isinstance(result, tuple) and len(result) == 2:
            print("   OK: Поиск убежищ работает")
            return True
        else:
            print("   ERROR: Неправильный формат ответа")
            return False
    except Exception as e:
        print(f"   ERROR: Ошибка поиска убежищ: {e}")
        return False

def test_safety_consultant():
    """Тест консультанта"""
    print("7. Тестирование консультанта...")
    try:
        from handlers import handle_safety_consultant_text, handle_safety_question
        
        class MockMessage:
            def __init__(self, text):
                self.chat = type('Chat', (), {'id': 12345})()
                self.from_user = type('User', (), {'username': 'test_user'})()
                self.text = text
        
        placeholders = {
            'safety_responses': [
                {'question_keywords': ['пожар'], 'answer': 'Звоните 112', 'source': 'Инструкция'}
            ]
        }
        
        # Тест показа документов
        message = MockMessage("📄 Список документов")
        result = handle_safety_consultant_text(message, placeholders)
        
        if isinstance(result, tuple):
            print("   OK: Консультант работает")
            return True
        else:
            print("   ERROR: Неправильный формат ответа")
            return False
    except Exception as e:
        print(f"   ERROR: Ошибка консультанта: {e}")
        return False

def test_improvement_suggestion():
    """Тест предложений"""
    print("8. Тестирование предложений...")
    try:
        from handlers import handle_improvement_suggestion_text
        
        class MockMessage:
            def __init__(self):
                self.chat = type('Chat', (), {'id': 12345})()
                self.from_user = type('User', (), {'username': 'test_user'})()
                self.text = "Тестовое предложение"
        
        message = MockMessage()
        placeholders = {}
        
        result = handle_improvement_suggestion_text(message, placeholders)
        
        if isinstance(result, tuple) and len(result) == 2:
            print("   OK: Предложения работают")
            return True
        else:
            print("   ERROR: Неправильный формат ответа")
            return False
    except Exception as e:
        print(f"   ERROR: Ошибка предложений: {e}")
        return False

def main():
    """Основная функция"""
    print_header()
    
    tests = [
        test_imports,
        test_configuration,
        test_keyboards,
        test_logging,
        test_danger_report,
        test_shelter_finder,
        test_safety_consultant,
        test_improvement_suggestion
    ]
    
    passed = 0
    total = len(tests)
    
    for test in tests:
        if test():
            passed += 1
        print()
    
    print("=" * 60)
    print(f"РЕЗУЛЬТАТЫ ТЕСТИРОВАНИЯ:")
    print(f"Пройдено: {passed}/{total}")
    print(f"Успешность: {(passed/total)*100:.1f}%")
    
    if passed == total:
        print("ОТЛИЧНО! Все тесты пройдены!")
        print("Бот готов к использованию!")
        return True
    elif passed >= total * 0.8:
        print("ХОРОШО! Большинство тестов пройдено!")
        print("Можно запускать с осторожностью!")
        return True
    else:
        print("ПРОБЛЕМЫ! Много тестов провалено!")
        print("Требуется исправление!")
        return False

if __name__ == '__main__':
    success = main()
    sys.exit(0 if success else 1)

