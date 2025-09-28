"""
Базовый класс для всех обработчиков
"""
from typing import Optional
from telegram import Update
from telegram.ext import ContextTypes

from bot.interfaces import IHandler, ILogger, IStateManager


class BaseHandler(IHandler):
    """Базовый класс для всех обработчиков команд"""
    
    def __init__(self, logger: ILogger, state_manager: IStateManager):
        self.logger = logger
        self.state_manager = state_manager
    
    async def handle(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Базовая реализация обработки"""
        user = update.effective_user
        if not user:
            return
        
        # Логируем активность
        self.logger.log_activity(
            user.id, 
            user.username, 
            self.__class__.__name__.lower().replace('handler', ''),
            self._get_payload_summary(update)
        )
        
        # Вызываем конкретную реализацию
        await self._handle_impl(update, context)
    
    async def _handle_impl(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Конкретная реализация обработки (переопределяется в наследниках)"""
        raise NotImplementedError
    
    def _get_payload_summary(self, update: Update) -> str:
        """Получить краткое описание содержимого сообщения"""
        if update.message and update.message.text:
            return update.message.text[:50]
        return ""
