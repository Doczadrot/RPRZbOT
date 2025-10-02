#!/usr/bin/env python3
"""
Проверка системы перед запуском бота безопасности РПРЗ
Выполняет все необходимые проверки для безопасного запуска
"""

import os
import sys
import json
import subprocess
import time
from pathlib import Path
from loguru import logger

def setup_logging():
    """Настройка логирования"""
    logger.add(
        "logs/startup_check.log",
        rotation="1 day",
        retention="7 days",
        level="INFO",
        format="{time:YYYY-MM-DD HH:mm:ss} | {level} | {message}"
    )

def check_python_version():
    """Проверка версии Python"""
    logger.info("🐍 Проверка версии Python...")
    
    version = sys.version_info
    if version < (3, 8):
        logger.error(f"❌ Требуется Python 3.8+, текущая версия: {version.major}.{version.minor}")
        return False
    
    logger.info(f"✅ Python {version.major}.{version.minor}.{version.micro}")
    return True

def check_dependencies():
    """Проверка зависимостей"""
    logger.info("📦 Проверка зависимостей...")
    
    required_packages = [
        'telebot',
        'loguru', 
        'python-dotenv',
        'psutil'
    ]
    
    missing_packages = []
    
    for package in required_packages:
        try:
            __import__(package.replace('-', '_'))
            logger.info(f"✅ {package}")
        except ImportError:
            logger.error(f"❌ {package} - не установлен")
            missing_packages.append(package)
    
    if missing_packages:
        logger.error(f"❌ Отсутствуют пакеты: {', '.join(missing_packages)}")
        logger.info("💡 Установите недостающие пакеты: pip install " + " ".join(missing_packages))
        return False
    
    return True

def check_project_structure():
    """Проверка структуры проекта"""
    logger.info("📁 Проверка структуры проекта...")
    
    required_dirs = ['bot', 'logs', 'assets', 'configs']
    required_files = ['.env', 'bot/main.py', 'bot/handlers.py']
    
    project_root = Path(__file__).parent
    
    # Проверка папок
    for dir_name in required_dirs:
        dir_path = project_root / dir_name
        if not dir_path.exists():
            logger.error(f"❌ Папка {dir_name} не найдена")
            return False
        logger.info(f"✅ Папка {dir_name}")
    
    # Проверка файлов
    for file_name in required_files:
        file_path = project_root / file_name
        if not file_path.exists():
            logger.error(f"❌ Файл {file_name} не найден")
            return False
        logger.info(f"✅ Файл {file_name}")
    
    return True

def check_environment():
    """Проверка переменных окружения"""
    logger.info("🔧 Проверка переменных окружения...")
    
    env_file = Path(__file__).parent / ".env"
    if not env_file.exists():
        logger.error("❌ Файл .env не найден")
        logger.info("💡 Скопируйте env.example в .env и заполните настройки")
        return False
    
    # Загружаем переменные
    from dotenv import load_dotenv
    load_dotenv(env_file)
    
    required_vars = ['BOT_TOKEN']
    optional_vars = ['ADMIN_CHAT_ID', 'LOG_LEVEL', 'MAX_FILE_SIZE_MB']
    
    missing_vars = []
    
    for var in required_vars:
        value = os.getenv(var)
        if not value:
            logger.error(f"❌ {var} не установлен")
            missing_vars.append(var)
        else:
            logger.info(f"✅ {var} установлен")
    
    for var in optional_vars:
        value = os.getenv(var)
        if value:
            logger.info(f"✅ {var} = {value}")
        else:
            logger.info(f"⚠️ {var} не установлен (используется значение по умолчанию)")
    
    if missing_vars:
        logger.error(f"❌ Отсутствуют обязательные переменные: {', '.join(missing_vars)}")
        return False
    
    return True

def check_running_processes():
    """Проверка запущенных процессов"""
    logger.info("🔄 Проверка запущенных процессов...")
    
    try:
        import psutil
        
        running_bots = []
        
        for proc in psutil.process_iter(['pid', 'name', 'cmdline', 'create_time']):
            try:
                if proc.info['name'] in ['python.exe', 'python']:
                    cmdline = ' '.join(proc.info['cmdline']) if proc.info['cmdline'] else ''
                    
                    # Проверяем, что это наш бот
                    if any(keyword in cmdline.lower() for keyword in ['bot', 'main.py', 'run_bot.py']):
                        running_bots.append({
                            'pid': proc.info['pid'],
                            'cmdline': cmdline,
                            'create_time': proc.info['create_time']
                        })
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue
        
        if running_bots:
            logger.warning(f"⚠️ Найдено {len(running_bots)} запущенных процессов бота:")
            for bot in running_bots:
                logger.warning(f"  - PID {bot['pid']}: {bot['cmdline']}")
            
            response = input("Хотите завершить эти процессы? (y/N): ").strip().lower()
            if response == 'y':
                return kill_bot_processes()
            else:
                logger.error("❌ Запуск отменен - обнаружены запущенные процессы")
                return False
        else:
            logger.info("✅ Запущенные процессы бота не найдены")
            return True
            
    except ImportError:
        logger.warning("⚠️ psutil не установлен, пропускаем проверку процессов")
        return True
    except Exception as e:
        logger.error(f"❌ Ошибка проверки процессов: {e}")
        return False

def kill_bot_processes():
    """Завершение процессов бота"""
    logger.info("🛑 Завершение процессов бота...")
    
    try:
        import psutil
        
        killed_count = 0
        
        for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
            try:
                if proc.info['name'] in ['python.exe', 'python']:
                    cmdline = ' '.join(proc.info['cmdline']) if proc.info['cmdline'] else ''
                    
                    if any(keyword in cmdline.lower() for keyword in ['bot', 'main.py', 'run_bot.py']):
                        process = psutil.Process(proc.info['pid'])
                        process.terminate()
                        
                        try:
                            process.wait(timeout=5)
                            logger.info(f"✅ Процесс {proc.info['pid']} завершен корректно")
                        except psutil.TimeoutExpired:
                            process.kill()
                            logger.warning(f"⚠️ Процесс {proc.info['pid']} принудительно завершен")
                        
                        killed_count += 1
                        
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue
        
        if killed_count > 0:
            logger.info(f"✅ Завершено {killed_count} процессов")
            time.sleep(2)  # Ждем завершения
        else:
            logger.info("ℹ️ Процессы для завершения не найдены")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Ошибка завершения процессов: {e}")
        return False

def check_lock_files():
    """Проверка файлов блокировки"""
    logger.info("🔒 Проверка файлов блокировки...")
    
    project_root = Path(__file__).parent
    lock_file = project_root / "bot.lock"
    pid_file = project_root / "bot.pid"
    
    if lock_file.exists() or pid_file.exists():
        logger.warning("⚠️ Найдены файлы блокировки")
        
        # Проверяем, действительно ли процесс запущен
        if pid_file.exists():
            try:
                with open(pid_file, 'r') as f:
                    pid = int(f.read().strip())
                
                import psutil
                if psutil.pid_exists(pid):
                    logger.warning(f"⚠️ Процесс с PID {pid} все еще запущен")
                    response = input("Хотите завершить этот процесс? (y/N): ").strip().lower()
                    if response == 'y':
                        try:
                            process = psutil.Process(pid)
                            process.terminate()
                            process.wait(timeout=5)
                            logger.info(f"✅ Процесс {pid} завершен")
                        except:
                            logger.error(f"❌ Не удалось завершить процесс {pid}")
                            return False
                    else:
                        logger.error("❌ Запуск отменен - обнаружен активный процесс")
                        return False
                else:
                    logger.info("ℹ️ Процесс не найден, удаляем старые файлы блокировки")
                    
            except Exception as e:
                logger.warning(f"⚠️ Ошибка проверки PID файла: {e}")
        
        # Удаляем старые файлы блокировки
        try:
            if lock_file.exists():
                lock_file.unlink()
                logger.info("✅ Удален старый файл блокировки")
            if pid_file.exists():
                pid_file.unlink()
                logger.info("✅ Удален старый PID файл")
        except Exception as e:
            logger.error(f"❌ Ошибка удаления файлов блокировки: {e}")
            return False
    else:
        logger.info("✅ Файлы блокировки не найдены")
    
    return True

def test_bot_connection():
    """Тест подключения к боту"""
    logger.info("🤖 Тест подключения к боту...")
    
    try:
        from dotenv import load_dotenv
        load_dotenv()
        
        bot_token = os.getenv('BOT_TOKEN')
        if not bot_token:
            logger.error("❌ BOT_TOKEN не найден")
            return False
        
        import telebot
        bot = telebot.TeleBot(bot_token)
        
        bot_info = bot.get_me()
        logger.info(f"✅ Бот подключен: @{bot_info.username} (ID: {bot_info.id})")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Ошибка подключения к боту: {e}")
        return False

def main():
    """Основная функция проверки"""
    setup_logging()
    
    logger.info("🚀 Запуск проверки системы перед запуском бота")
    
    checks = [
        ("Версия Python", check_python_version),
        ("Зависимости", check_dependencies),
        ("Структура проекта", check_project_structure),
        ("Переменные окружения", check_environment),
        ("Запущенные процессы", check_running_processes),
        ("Файлы блокировки", check_lock_files),
        ("Подключение к боту", test_bot_connection)
    ]
    
    failed_checks = []
    
    for check_name, check_func in checks:
        logger.info(f"\n{'='*50}")
        logger.info(f"Проверка: {check_name}")
        logger.info(f"{'='*50}")
        
        try:
            if not check_func():
                failed_checks.append(check_name)
        except Exception as e:
            logger.error(f"❌ Ошибка в проверке {check_name}: {e}")
            failed_checks.append(check_name)
    
    logger.info(f"\n{'='*50}")
    logger.info("РЕЗУЛЬТАТ ПРОВЕРКИ")
    logger.info(f"{'='*50}")
    
    if failed_checks:
        logger.error(f"❌ Проверка не пройдена. Ошибки в:")
        for check in failed_checks:
            logger.error(f"  - {check}")
        logger.info("\n💡 Исправьте ошибки и повторите проверку")
        return False
    else:
        logger.info("🎉 Все проверки пройдены успешно!")
        logger.info("✅ Система готова к запуску бота")
        return True

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
