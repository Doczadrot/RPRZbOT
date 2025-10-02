#!/usr/bin/env python3
"""
Система управления ботом безопасности РПРЗ
Проверяет запущенные процессы, блокирует двойные запуски
"""

import os
import sys
import time
import psutil
import signal
import json
import subprocess
from pathlib import Path
from datetime import datetime
from loguru import logger

class BotManager:
    def __init__(self):
        self.project_root = Path(__file__).parent
        self.lock_file = self.project_root / "bot.lock"
        self.pid_file = self.project_root / "bot.pid"
        self.log_file = self.project_root / "logs" / "bot_manager.log"
        
        # Настройка логирования
        logger.add(
            self.log_file,
            rotation="1 day",
            retention="7 days",
            level="INFO",
            format="{time:YYYY-MM-DD HH:mm:ss} | {level} | {message}"
        )
    
    def check_running_processes(self):
        """Проверяет запущенные процессы Python с ботом"""
        running_bots = []
        
        for proc in psutil.process_iter(['pid', 'name', 'cmdline', 'create_time']):
            try:
                if proc.info['name'] == 'python.exe' or 'python' in proc.info['name']:
                    cmdline = ' '.join(proc.info['cmdline']) if proc.info['cmdline'] else ''
                    
                    # Проверяем, что это наш бот
                    if any(keyword in cmdline.lower() for keyword in ['bot', 'main.py', 'run_bot.py']):
                        running_bots.append({
                            'pid': proc.info['pid'],
                            'cmdline': cmdline,
                            'create_time': datetime.fromtimestamp(proc.info['create_time']).isoformat()
                        })
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue
        
        return running_bots
    
    def kill_bot_processes(self):
        """Завершает все процессы бота"""
        running_bots = self.check_running_processes()
        
        if not running_bots:
            logger.info("Запущенные процессы бота не найдены")
            return True
        
        logger.warning(f"Найдено {len(running_bots)} запущенных процессов бота")
        
        for bot in running_bots:
            try:
                process = psutil.Process(bot['pid'])
                process.terminate()
                
                # Ждем завершения процесса
                try:
                    process.wait(timeout=5)
                    logger.info(f"Процесс {bot['pid']} завершен корректно")
                except psutil.TimeoutExpired:
                    # Принудительно завершаем
                    process.kill()
                    logger.warning(f"Процесс {bot['pid']} принудительно завершен")
                
            except psutil.NoSuchProcess:
                logger.info(f"Процесс {bot['pid']} уже завершен")
            except Exception as e:
                logger.error(f"Ошибка завершения процесса {bot['pid']}: {e}")
        
        # Ждем немного для полного завершения
        time.sleep(2)
        
        # Проверяем, что процессы действительно завершены
        remaining_bots = self.check_running_processes()
        if remaining_bots:
            logger.error(f"Не удалось завершить {len(remaining_bots)} процессов")
            return False
        
        logger.info("Все процессы бота успешно завершены")
        return True
    
    def create_lock(self, pid):
        """Создает файл блокировки"""
        lock_data = {
            'pid': pid,
            'started_at': datetime.now().isoformat(),
            'project_path': str(self.project_root)
        }
        
        try:
            with open(self.lock_file, 'w', encoding='utf-8') as f:
                json.dump(lock_data, f, indent=2, ensure_ascii=False)
            
            with open(self.pid_file, 'w', encoding='utf-8') as f:
                f.write(str(pid))
            
            logger.info(f"Создан файл блокировки для PID {pid}")
            return True
            
        except Exception as e:
            logger.error(f"Ошибка создания файла блокировки: {e}")
            return False
    
    def remove_lock(self):
        """Удаляет файл блокировки"""
        try:
            if self.lock_file.exists():
                self.lock_file.unlink()
            
            if self.pid_file.exists():
                self.pid_file.unlink()
            
            logger.info("Файл блокировки удален")
            return True
            
        except Exception as e:
            logger.error(f"Ошибка удаления файла блокировки: {e}")
            return False
    
    def check_lock(self):
        """Проверяет файл блокировки"""
        if not self.lock_file.exists():
            return None
        
        try:
            with open(self.lock_file, 'r', encoding='utf-8') as f:
                lock_data = json.load(f)
            
            pid = lock_data.get('pid')
            started_at = lock_data.get('started_at')
            
            # Проверяем, что процесс действительно запущен
            if pid:
                try:
                    process = psutil.Process(int(pid))
                    if process.is_running():
                        return {
                            'pid': pid,
                            'started_at': started_at,
                            'process': process
                        }
                except psutil.NoSuchProcess:
                    # Процесс не существует, блокировка недействительна
                    self.remove_lock()
            
            return None
            
        except Exception as e:
            logger.error(f"Ошибка проверки файла блокировки: {e}")
            self.remove_lock()
            return None
    
    def system_check(self):
        """Проверка системы перед запуском"""
        logger.info("🔍 Выполняется проверка системы...")
        
        # 1. Проверка Python
        python_version = sys.version_info
        if python_version < (3, 8):
            logger.error(f"Требуется Python 3.8+, текущая версия: {python_version.major}.{python_version.minor}")
            return False
        
        logger.info(f"✅ Python {python_version.major}.{python_version.minor}.{python_version.micro}")
        
        # 2. Проверка переменных окружения
        env_file = self.project_root / ".env"
        if not env_file.exists():
            logger.error("Файл .env не найден")
            return False
        
        logger.info("✅ Файл .env найден")
        
        # 3. Проверка зависимостей
        try:
            import telebot
            import psutil
            import loguru
            logger.info("✅ Основные зависимости установлены")
        except ImportError as e:
            logger.error(f"❌ Отсутствует зависимость: {e}")
            return False
        
        # 4. Проверка папок
        required_dirs = ['logs', 'bot', 'assets', 'configs']
        for dir_name in required_dirs:
            dir_path = self.project_root / dir_name
            if not dir_path.exists():
                logger.error(f"❌ Папка {dir_name} не найдена")
                return False
        
        logger.info("✅ Структура папок корректна")
        
        # 5. Проверка запущенных процессов
        running_bots = self.check_running_processes()
        if running_bots:
            logger.warning(f"⚠️ Найдено {len(running_bots)} запущенных процессов бота")
            for bot in running_bots:
                logger.warning(f"  - PID {bot['pid']}: {bot['cmdline']}")
            return False
        
        logger.info("✅ Запущенные процессы бота не найдены")
        
        # 6. Проверка блокировки
        lock_info = self.check_lock()
        if lock_info:
            logger.warning(f"⚠️ Найдена блокировка от PID {lock_info['pid']}")
            return False
        
        logger.info("✅ Файл блокировки не найден")
        logger.info("🎉 Все проверки пройдены успешно!")
        return True
    
    def start_bot(self):
        """Запуск бота с проверками"""
        logger.info("🚀 Запуск системы управления ботом")
        
        # Проверка системы
        if not self.system_check():
            logger.error("❌ Проверка системы не пройдена")
            return False
        
        # Завершение старых процессов
        if not self.kill_bot_processes():
            logger.error("❌ Не удалось завершить старые процессы")
            return False
        
        # Создание блокировки
        current_pid = os.getpid()
        if not self.create_lock(current_pid):
            logger.error("❌ Не удалось создать блокировку")
            return False
        
        logger.info("✅ Бот готов к запуску")
        return True
    
    def stop_bot(self):
        """Остановка бота"""
        logger.info("🛑 Остановка бота...")
        
        # Завершение процессов
        if not self.kill_bot_processes():
            logger.error("❌ Ошибка завершения процессов")
            return False
        
        # Удаление блокировки
        if not self.remove_lock():
            logger.error("❌ Ошибка удаления блокировки")
            return False
        
        logger.info("✅ Бот остановлен")
        return True
    
    def status(self):
        """Статус системы"""
        logger.info("📊 Статус системы:")
        
        # Проверка процессов
        running_bots = self.check_running_processes()
        if running_bots:
            logger.info(f"🔴 Запущено процессов бота: {len(running_bots)}")
            for bot in running_bots:
                logger.info(f"  - PID {bot['pid']}: {bot['cmdline']}")
        else:
            logger.info("🟢 Процессы бота не запущены")
        
        # Проверка блокировки
        lock_info = self.check_lock()
        if lock_info:
            logger.info(f"🔒 Блокировка активна: PID {lock_info['pid']}")
        else:
            logger.info("🟢 Блокировка не активна")
        
        # Проверка системы
        if self.system_check():
            logger.info("✅ Система готова к работе")
        else:
            logger.info("❌ Система не готова к работе")

def main():
    """Основная функция"""
    if len(sys.argv) < 2:
        print("Использование:")
        print("  python bot_manager.py start  - запуск бота")
        print("  python bot_manager.py stop   - остановка бота")
        print("  python bot_manager.py status - статус системы")
        print("  python bot_manager.py check  - проверка системы")
        return
    
    manager = BotManager()
    command = sys.argv[1].lower()
    
    if command == "start":
        if manager.start_bot():
            logger.info("🎉 Бот запущен успешно")
        else:
            logger.error("❌ Ошибка запуска бота")
            sys.exit(1)
    
    elif command == "stop":
        if manager.stop_bot():
            logger.info("✅ Бот остановлен")
        else:
            logger.error("❌ Ошибка остановки бота")
            sys.exit(1)
    
    elif command == "status":
        manager.status()
    
    elif command == "check":
        if manager.system_check():
            logger.info("✅ Система готова")
        else:
            logger.error("❌ Система не готова")
            sys.exit(1)
    
    else:
        logger.error(f"Неизвестная команда: {command}")
        sys.exit(1)

if __name__ == "__main__":
    main()
