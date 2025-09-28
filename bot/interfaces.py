"""
Интерфейсы для соблюдения принципов SOLID
"""
from abc import ABC, abstractmethod
from typing import Any, Dict, Optional
from telegram import Update
from telegram.ext import ContextTypes


class IHandler(ABC):
    """Интерфейс для всех обработчиков команд"""
    
    @abstractmethod
    async def handle(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Обработать сообщение"""
        pass


class ILogger(ABC):
    """Интерфейс для логирования активности"""
    
    @abstractmethod
    def log_activity(self, user_id: int, username: Optional[str], action: str, payload_summary: str = "") -> None:
        """Логировать активность пользователя"""
        pass


class IStateManager(ABC):
    """Интерфейс для управления состояниями пользователей"""
    
    @abstractmethod
    def get_user_state(self, user_id: int) -> Optional[Dict[str, Any]]:
        """Получить состояние пользователя"""
        pass
    
    @abstractmethod
    def set_user_state(self, user_id: int, state: Dict[str, Any]) -> None:
        """Установить состояние пользователя"""
        pass
    
    @abstractmethod
    def clear_user_state(self, user_id: int) -> None:
        """Очистить состояние пользователя"""
        pass


class IFileManager(ABC):
    """Интерфейс для работы с файлами"""
    
    @abstractmethod
    def load_json(self, file_path: str) -> Dict[str, Any]:
        """Загрузить JSON файл"""
        pass
    
    @abstractmethod
    def save_json(self, file_path: str, data: Dict[str, Any]) -> None:
        """Сохранить JSON файл"""
        pass
    
    @abstractmethod
    def file_exists(self, file_path: str) -> bool:
        """Проверить существование файла"""
        pass


class IKeyboardFactory(ABC):
    """Интерфейс для создания клавиатур"""
    
    @abstractmethod
    def create_main_menu(self):
        """Создать главное меню"""
        pass
    
    @abstractmethod
    def create_back_button(self):
        """Создать кнопку 'Назад'"""
        pass


class IService(ABC):
    """Базовый интерфейс для всех сервисов"""
    
    @abstractmethod
    async def process(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Обработать запрос"""
        pass
