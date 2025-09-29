#!/usr/bin/env python3
"""
Скрипт запуска MVP Telegram-бота по безопасности РПРЗ
"""

import os
import sys
from loguru import logger

# Добавляем папку bot в путь
sys.path.append(os.path.join(os.path.dirname(__file__), 'bot'))

def main():
    """Основная функция запуска"""
    logger.info("🚀 Запуск MVP бота безопасности РПРЗ")
    
    try:
        # Импортируем и запускаем бота
        from main import bot, logger as bot_logger
        
        bot_info = bot.get_me()
        bot_logger.info(f"✅ Бот подключен: @{bot_info.username}")
        
        bot.polling(none_stop=True, interval=3, timeout=20)
        
    except KeyboardInterrupt:
        logger.info("🛑 Бот остановлен пользователем")
    except Exception as e:
        logger.error(f"❌ Ошибка запуска бота: {e}")
        sys.exit(1)

if __name__ == '__main__':
    main()
