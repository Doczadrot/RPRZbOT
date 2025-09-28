"""
Управление состояниями пользователей
"""
from typing import Dict, Any, Optional
from datetime import datetime, timedelta

from bot.interfaces import IStateManager


class StateManager(IStateManager):
    """Класс для управления состояниями пользователей"""
    
    def __init__(self):
        self._user_states: Dict[int, Dict[str, Any]] = {}
        self._message_times: Dict[int, list] = {}  # Для защиты от спама
    
    def get_user_state(self, user_id: int) -> Optional[Dict[str, Any]]:
        """Получить состояние пользователя"""
        return self._user_states.get(user_id)
    
    def set_user_state(self, user_id: int, state: Dict[str, Any]) -> None:
        """Установить состояние пользователя"""
        self._user_states[user_id] = state
    
    def clear_user_state(self, user_id: int) -> None:
        """Очистить состояние пользователя"""
        if user_id in self._user_states:
            del self._user_states[user_id]
        if user_id in self._message_times:
            del self._message_times[user_id]
    
    def check_spam_protection(self, user_id: int, max_messages: int = 10) -> bool:
        """Проверяет защиту от спама (максимум сообщений в минуту)"""
        current_time = datetime.now()
        
        # Очищаем старые сообщения (старше минуты)
        if user_id in self._message_times:
            self._message_times[user_id] = [
                msg_time for msg_time in self._message_times[user_id]
                if (current_time - msg_time).total_seconds() < 60
            ]
        else:
            self._message_times[user_id] = []
        
        # Проверяем лимит
        if len(self._message_times[user_id]) >= max_messages:
            return False
        
        # Добавляем текущее время
        self._message_times[user_id].append(current_time)
        return True
