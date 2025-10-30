"""
Тестовый скрипт для проверки всех функций бота
"""
import os
import sys
import asyncio
import pytest
from unittest.mock import Mock, AsyncMock
from datetime import datetime

# Добавляем путь к модулям бота
sys.path.append('.')

from bot.main_refactored import BotApplication
from bot.utils.activity_logger import ActivityLogger
from bot.utils.state_manager import StateManager
from bot.utils.file_manager import FileManager
from bot.utils.keyboard_factory import KeyboardFactory


class MockUpdate:
    """Мок для Update объекта"""
    def __init__(self, user_id=12345, username="test_user", text="", message_type="text"):
        self.effective_user = Mock()
        self.effective_user.id = user_id
        self.effective_user.username = username
        
        self.message = Mock()
        self.message.text = text
        self.message.reply_text = AsyncMock()
        self.message.reply_photo = AsyncMock()
        self.message.reply_document = AsyncMock()
        
        if message_type == "photo":
            photo_mock = Mock()
            photo_mock.file_id = "test_photo_id"
            photo_mock.file_size = 1024 * 1024  # 1 МБ
            self.message.photo = [photo_mock]
            self.message.video = None
        elif message_type == "video":
            self.message.video = Mock()
            self.message.video.file_id = "test_video_id"
            self.message.video.file_size = 10 * 1024 * 1024  # 10 МБ
            self.message.photo = None
        elif message_type == "location":
            self.message.location = Mock()
            self.message.location.latitude = 55.7558
            self.message.location.longitude = 37.6173
        else:
            self.message.photo = None
            self.message.video = None
            self.message.location = None


class MockContext:
    """Мок для Context объекта"""
    def __init__(self):
        self.bot = Mock()
        self.bot.send_message = AsyncMock()
        self.bot.send_photo = AsyncMock()
        self.bot.send_video = AsyncMock()
        self.bot_data = {'admin_chat_id': 'ADMIN_ID_PLACEHOLDER'}


@pytest.mark.asyncio
async def test_start_command():
    """Тест команды /start"""
    print("🧪 Тестируем команду /start...")
    
    app = BotApplication()
    update = MockUpdate(text="/start")
    context = MockContext()
    
    await app.start_command(update, context)
    
    # Проверяем, что сообщение отправлено
    assert update.message.reply_text.called
    print("✅ Команда /start работает")


@pytest.mark.asyncio
async def test_danger_report_flow():
    """Тест полного потока сообщения об опасности"""
    print("🧪 Тестируем поток 'Сообщите об опасности'...")
    
    app = BotApplication()
    context = MockContext()
    
    # Шаг 1: Начало сообщения об опасности
    update1 = MockUpdate(text="🚨❗ Сообщите об опасности")
    await app.handle_message(update1, context)
    print("✅ Шаг 1: Начало сообщения об опасности")
    
    # Шаг 2: Описание
    update2 = MockUpdate(text="Тестовое описание опасности")
    await app.handle_message(update2, context)
    print("✅ Шаг 2: Описание опасности")
    
    # Шаг 3: Местоположение
    update3 = MockUpdate(text="Тестовое местоположение")
    await app.handle_message(update3, context)
    print("✅ Шаг 3: Местоположение")
    
    # Шаг 4: Пропуск медиа
    update4 = MockUpdate(text="⏭️⏩ Пропустить")
    await app.handle_message(update4, context)
    print("✅ Шаг 4: Пропуск медиа")
    
    # Шаг 5: Подтверждение
    update5 = MockUpdate(text="✅📤 Отправить сообщение")
    await app.handle_message(update5, context)
    print("✅ Шаг 5: Отправка сообщения")


@pytest.mark.asyncio
async def test_shelter_finder():
    """Тест поиска убежищ"""
    print("🧪 Тестируем поиск убежищ...")
    
    app = BotApplication()
    update = MockUpdate(text="🏠🛡️ Ближайшее укрытие")
    context = MockContext()
    
    await app.handle_message(update, context)
    print("✅ Поиск убежищ работает")


@pytest.mark.asyncio
async def test_consultant():
    """Тест консультанта по безопасности"""
    print("🧪 Тестируем консультанта по безопасности...")
    
    app = BotApplication()
    update = MockUpdate(text="🧑‍🏫📚 Консультант по безопасности РПРЗ")
    context = MockContext()
    
    await app.handle_message(update, context)
    print("✅ Консультант по безопасности работает")


@pytest.mark.asyncio
async def test_history_command():
    """Тест команды /my_history"""
    print("🧪 Тестируем команду /my_history...")
    
    app = BotApplication()
    update = MockUpdate(text="/my_history")
    context = MockContext()
    
    await app.my_history_command(update, context)
    print("✅ Команда /my_history работает")


@pytest.mark.asyncio
async def test_media_handling():
    """Тест обработки медиафайлов"""
    print("🧪 Тестируем обработку медиафайлов...")
    
    app = BotApplication()
    context = MockContext()
    
    # Устанавливаем состояние для обработки медиа
    app.state_manager.set_user_state(12345, {
        'state': 'danger_media',
        'data': {}
    })
    
    # Тест фото
    update_photo = MockUpdate(message_type="photo")
    await app.handle_media(update_photo, context)
    print("✅ Обработка фото работает")
    
    # Очищаем состояние и устанавливаем снова для видео
    app.state_manager.clear_user_state(12345)
    app.state_manager.set_user_state(12345, {
        'state': 'danger_media',
        'data': {}
    })
    
    # Тест видео
    update_video = MockUpdate(message_type="video")
    await app.handle_media(update_video, context)
    print("✅ Обработка видео работает")


@pytest.mark.asyncio
async def test_location_handling():
    """Тест обработки геолокации"""
    print("🧪 Тестируем обработку геолокации...")
    
    app = BotApplication()
    context = MockContext()
    
    # Устанавливаем состояние для обработки геолокации
    app.state_manager.set_user_state(12345, {
        'state': 'shelter_location',
        'data': {}
    })
    
    update = MockUpdate(message_type="location")
    await app.handle_location(update, context)
    print("✅ Обработка геолокации работает")


@pytest.mark.asyncio
async def test_spam_protection():
    """Тест защиты от спама"""
    print("🧪 Тестируем защиту от спама...")
    
    app = BotApplication()
    context = MockContext()
    
    # Отправляем много сообщений подряд
    for i in range(15):  # Больше лимита в 10 сообщений
        update = MockUpdate(text=f"Сообщение {i}")
        await app.handle_message(update, context)
    
    # Последнее сообщение должно быть заблокировано
    last_update = MockUpdate(text="Последнее сообщение")
    await app.handle_message(last_update, context)
    
    # Проверяем, что отправлено сообщение о спаме
    assert last_update.message.reply_text.called
    print("✅ Защита от спама работает")


@pytest.mark.asyncio
async def test_utilities():
    """Тест утилит"""
    print("🧪 Тестируем утилиты...")
    
    # Тест ActivityLogger
    logger = ActivityLogger('logs/test_activity.csv')
    logger.log_activity(12345, "test_user", "test_action", "test_payload")
    print("✅ ActivityLogger работает")
    
    # Тест StateManager
    state_manager = StateManager()
    state_manager.set_user_state(12345, {'state': 'test', 'data': {}})
    state = state_manager.get_user_state(12345)
    assert state['state'] == 'test'
    print("✅ StateManager работает")
    
    # Тест FileManager
    file_manager = FileManager()
    test_data = {'test': 'data'}
    test_file = 'logs/test.json'
    file_manager.save_json(test_file, test_data)
    loaded_data = file_manager.load_json(test_file)
    assert loaded_data == test_data
    print("✅ FileManager работает")
    
    # Тест KeyboardFactory
    keyboard_factory = KeyboardFactory()
    main_menu = keyboard_factory.create_main_menu()
    assert main_menu is not None
    print("✅ KeyboardFactory работает")
    
    # Очищаем тестовые файлы
    if os.path.exists('logs/test.json'):
        os.remove('logs/test.json')
    if os.path.exists('logs/test_activity.csv'):
        os.remove('logs/test_activity.csv')


async def run_all_tests():
    """Запустить все тесты"""
    print("🚀 Запуск тестирования бота...\n")
    
    try:
        await test_start_command()
        await test_danger_report_flow()
        await test_shelter_finder()
        await test_consultant()
        await test_history_command()
        await test_media_handling()
        await test_location_handling()
        await test_spam_protection()
        await test_utilities()
        
        print("\n🎉 Все тесты прошли успешно!")
        print("✅ Бот готов к использованию")
        
    except Exception as e:
        print(f"\n❌ Ошибка в тестах: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(run_all_tests())
