"""
Фабрика клавиатур для устранения дублирования кода
"""
from telegram import ReplyKeyboardMarkup, KeyboardButton

from bot.interfaces import IKeyboardFactory


class KeyboardFactory(IKeyboardFactory):
    """Фабрика для создания клавиатур"""
    
    def create_main_menu(self):
        """Создать главное меню"""
        keyboard = [
            ['🚨❗ Сообщите об опасности'],
            ['🏠🛡️ Ближайшее укрытие'],
            ['🧑‍🏫📚 Консультант по безопасности РПРЗ']
        ]
        return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    
    def create_back_button(self):
        """Создать кнопку 'Назад'"""
        keyboard = [['⬅️🔙 Назад']]
        return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    
    def create_back_to_main(self):
        """Создать кнопку 'Главное меню'"""
        keyboard = [['🏠⬅️ Главное меню']]
        return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    
    def create_location_request(self):
        """Создать клавиатуру с запросом геолокации"""
        keyboard = [
            [KeyboardButton("📍🌍 Отправить геолокацию", request_location=True)],
            ['⏭️⏩ Пропустить'],
            ['⬅️🔙 Назад']
        ]
        return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    
    def create_media_buttons(self):
        """Создать кнопки для медиафайлов"""
        keyboard = [
            ['📷🎥 Прикрепить фото/видео'],
            ['⏭️⏩ Пропустить'],
            ['⬅️🔙 Назад']
        ]
        return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    
    def create_media_continue_buttons(self):
        """Создать кнопки для продолжения после медиа"""
        keyboard = [
            ['📷➕ Прикрепить еще'],
            ['⏭️▶️ Продолжить'],
            ['⬅️🔙 Назад']
        ]
        return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    
    def create_confirmation_buttons(self):
        """Создать кнопки подтверждения"""
        keyboard = [
            ['✅📤 Отправить сообщение'],
            ['✏️📝 Редактировать'],
            ['❌🚫 Отменить']
        ]
        return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    
    def create_success_buttons(self):
        """Создать кнопки после успешной отправки"""
        keyboard = [
            ['📞🛡️ Позвонить в службу безопасности'],
            ['📞👷 Позвонить в охрану труда'],
            ['🏠⬅️ Главное меню']
        ]
        return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    
    def create_shelter_buttons(self):
        """Создать кнопки для убежищ"""
        keyboard = [
            ['🔍📍 Показать на карте', '🌐🗺️ Открыть в Яндекс.Картах'],
            ['🏠⬅️ Главное меню']
        ]
        return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    
    def create_consultant_menu(self):
        """Создать меню консультанта"""
        keyboard = [
            ['📄📚 Список документов'],
            ['❓💬 Задать вопрос'],
            ['⬅️🔙 Назад']
        ]
        return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    
    def create_question_buttons(self):
        """Создать кнопки для вопросов"""
        keyboard = [
            ['📖📋 Подробнее'],
            ['📄📑 Открыть PDF'],
            ['❓🔄 Задать другой вопрос'],
            ['⬅️🔙 Назад']
        ]
        return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    
    def create_document_buttons(self, count: int):
        """Создать кнопки для документов"""
        keyboard = []
        for i in range(1, count + 1):
            keyboard.append([f"📄📑 Открыть документ {i}"])
        keyboard.append(['⬅️🔙 Назад'])
        return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
