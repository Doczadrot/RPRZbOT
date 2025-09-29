#!/usr/bin/env python3
"""
Скрипт для исправления всех проблем с ботом
"""

import os
import sys
import subprocess
import time
import json
from pathlib import Path

def print_step(step, description):
    """Выводит шаг с форматированием"""
    print(f"\n{'='*60}")
    print(f"Шаг {step}: {description}")
    print(f"{'='*60}")

def check_python_version():
    """Проверяет версию Python"""
    print_step(1, "Проверка версии Python")
    
    if sys.version_info < (3, 8):
        print("❌ Требуется Python 3.8 или выше")
        print(f"   Текущая версия: {sys.version}")
        return False
    
    print(f"✅ Python версия: {sys.version}")
    return True

def install_dependencies():
    """Устанавливает зависимости"""
    print_step(2, "Установка зависимостей")
    
    try:
        print("Установка зависимостей...")
        result = subprocess.run([sys.executable, "-m", "pip", "install", "-r", "requirements.txt"], 
                              capture_output=True, text=True, timeout=60)
        
        if result.returncode == 0:
            print("Зависимости установлены")
            return True
        else:
            print(f"Ошибка установки: {result.stderr}")
            return False
    except Exception as e:
        print(f"Ошибка: {e}")
        return False

def stop_existing_processes():
    """Останавливает существующие процессы"""
    print_step(3, "Остановка существующих процессов")
    
    try:
        # Останавливаем через taskkill
        result = subprocess.run(["taskkill", "/f", "/im", "python.exe"], 
                              capture_output=True, timeout=10)
        
        if result.returncode == 0:
            print("Процессы остановлены через taskkill")
        else:
            print("taskkill не сработал, пробуем psutil...")
            try:
                import psutil
                python_processes = [p for p in psutil.process_iter(['pid', 'name', 'cmdline']) 
                                  if p.info['name'] == 'python.exe']
                
                for proc in python_processes:
                    try:
                        proc.terminate()
                        print(f"   Остановлен процесс {proc.info['pid']}")
                    except:
                        pass
                print("✅ Процессы остановлены через psutil")
            except ImportError:
                print("⚠️ psutil не установлен, пропускаем")
        
        time.sleep(3)
        return True
    except Exception as e:
        print(f"❌ Ошибка остановки процессов: {e}")
        return False

def check_env_file():
    """Проверяет файл .env"""
    print_step(4, "Проверка файла .env")
    
    if not os.path.exists(".env"):
        print("❌ Файл .env не найден!")
        print("💡 Создайте файл .env с содержимым:")
        print("BOT_TOKEN=your_telegram_bot_token_here")
        print("ADMIN_CHAT_ID=your_admin_chat_id")
        return False
    
    # Проверяем содержимое
    with open(".env", "r", encoding="utf-8") as f:
        content = f.read()
        
    if "your_telegram_bot_token_here" in content:
        print("⚠️ BOT_TOKEN не настроен в .env")
        return False
    
    print("✅ Файл .env настроен")
    return True

def clean_logs():
    """Очищает старые логи"""
    print_step(5, "Очистка старых логов")
    
    logs_dir = Path("logs")
    if logs_dir.exists():
        removed_count = 0
        for file in logs_dir.glob("*.log"):
            try:
                file.unlink()
                print(f"   Удален: {file.name}")
                removed_count += 1
            except Exception as e:
                print(f"   ❌ Ошибка удаления {file.name}: {e}")
        
        print(f"✅ Удалено файлов: {removed_count}")
    else:
        print("📁 Папка logs не найдена, создаем...")
        logs_dir.mkdir(exist_ok=True)
        print("✅ Папка logs создана")

def test_bot_connection():
    """Тестирует подключение к боту"""
    print_step(6, "Тестирование подключения к боту")
    
    try:
        # Импортируем и тестируем бота
        sys.path.append("bot")
        from main import bot, BOT_TOKEN
        
        if not BOT_TOKEN or BOT_TOKEN == "your_telegram_bot_token_here":
            print("❌ BOT_TOKEN не настроен")
            return False
        
        bot_info = bot.get_me()
        print(f"✅ Бот подключен: @{bot_info.username}")
        print(f"   ID: {bot_info.id}")
        print(f"   Имя: {bot_info.first_name}")
        return True
        
    except Exception as e:
        print(f"❌ Ошибка подключения к боту: {e}")
        return False

def start_bot():
    """Запускает бота"""
    print_step(7, "Запуск бота")
    
    try:
        print("🚀 Запуск бота в фоновом режиме...")
        process = subprocess.Popen([sys.executable, "run_bot.py"], 
                                 stdout=subprocess.PIPE, 
                                 stderr=subprocess.PIPE)
        
        print(f"✅ Бот запущен (PID: {process.pid})")
        
        # Ждем и проверяем
        time.sleep(5)
        if process.poll() is None:
            print("✅ Бот работает стабильно")
            return True
        else:
            print("❌ Бот завершился неожиданно")
            stdout, stderr = process.communicate()
            if stderr:
                print(f"Ошибка: {stderr.decode('utf-8', errors='replace')}")
            return False
            
    except Exception as e:
        print(f"❌ Ошибка запуска: {e}")
        return False

def main():
    """Основная функция"""
    print("Исправление всех проблем с ботом РПРЗ")
    print("=" * 60)
    
    steps = [
        check_python_version,
        install_dependencies,
        stop_existing_processes,
        check_env_file,
        clean_logs,
        test_bot_connection,
        start_bot
    ]
    
    for i, step in enumerate(steps, 1):
        try:
            if not step():
                print(f"\n❌ Шаг {i} не выполнен. Остановка.")
                return False
        except Exception as e:
            print(f"\n❌ Ошибка на шаге {i}: {e}")
            return False
    
    print("\nВсе проблемы исправлены!")
    print("Бот запущен и работает")
    print("Для мониторинга: python monitor_logs_improved.py")
    print("Для остановки: python stop_bot.py")
    
    return True

if __name__ == '__main__':
    main()
