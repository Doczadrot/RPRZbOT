#!/usr/bin/env python3
"""
Безопасный запуск MVP Telegram-бота по безопасности РПРЗ
С проверками системы и управлением процессами
"""

import os
import sys
import subprocess
from pathlib import Path
from loguru import logger

def main():
    """Основная функция запуска"""
    logger.info("🚀 Безопасный запуск MVP бота безопасности РПРЗ")
    
    project_root = Path(__file__).parent
    
    # Проверка системы
    logger.info("🔍 Выполняется проверка системы...")
    try:
        result = subprocess.run([
            sys.executable, "startup_check.py"
        ], cwd=project_root, capture_output=True, text=True)
        
        if result.returncode != 0:
            logger.error("❌ Проверка системы не пройдена")
            logger.error("Вывод проверки:")
            logger.error(result.stdout)
            logger.error(result.stderr)
            sys.exit(1)
        
        logger.info("✅ Проверка системы пройдена")
        
    except Exception as e:
        logger.error(f"❌ Ошибка выполнения проверки системы: {e}")
        sys.exit(1)
    
    # Управление процессами
    logger.info("🔧 Управление процессами...")
    try:
        result = subprocess.run([
            sys.executable, "bot_manager.py", "start"
        ], cwd=project_root, capture_output=True, text=True)
        
        if result.returncode != 0:
            logger.error("❌ Ошибка управления процессами")
            logger.error("Вывод менеджера:")
            logger.error(result.stdout)
            logger.error(result.stderr)
            sys.exit(1)
        
        logger.info("✅ Процессы подготовлены")
        
    except Exception as e:
        logger.error(f"❌ Ошибка управления процессами: {e}")
        sys.exit(1)
    
    # Запуск бота
    logger.info("🤖 Запуск бота...")
    try:
        # Импортируем и запускаем бота
        sys.path.append(str(project_root / 'bot'))
        from main import bot, logger as bot_logger
        
        bot_info = bot.get_me()
        bot_logger.info(f"✅ Бот подключен: @{bot_info.username}")
        
        bot.polling(none_stop=True, interval=3, timeout=20)
        
    except KeyboardInterrupt:
        logger.info("🛑 Бот остановлен пользователем")
        # Остановка через менеджер
        try:
            subprocess.run([
                sys.executable, "bot_manager.py", "stop"
            ], cwd=project_root)
        except:
            pass
    except Exception as e:
        logger.error(f"❌ Ошибка запуска бота: {e}")
        # Остановка через менеджер
        try:
            subprocess.run([
                sys.executable, "bot_manager.py", "stop"
            ], cwd=project_root)
        except:
            pass
        sys.exit(1)

if __name__ == '__main__':
    main()
