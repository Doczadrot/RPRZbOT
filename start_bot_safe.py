#!/usr/bin/env python3
"""
Безопасный запуск бота с проверками
"""

import os
import sys
import subprocess
import time
import psutil

def check_bot_running():
    """Проверяет, запущен ли уже бот"""
    try:
        for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
            if (proc.info['name'] == 'python.exe' and 
                'main.py' in ' '.join(proc.info['cmdline'] or [])):
                return True, proc.info['pid']
        return False, None
    except:
        return False, None

def stop_existing_bot():
    """Останавливает существующий бот"""
    print("🛑 Остановка существующих экземпляров...")
    try:
        for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
            if (proc.info['name'] == 'python.exe' and 
                'main.py' in ' '.join(proc.info['cmdline'] or [])):
                try:
                    proc.terminate()
                    print(f"   ✅ Остановлен процесс {proc.info['pid']}")
                except:
                    pass
        time.sleep(2)
    except Exception as e:
        print(f"   ❌ Ошибка остановки: {e}")

def start_bot():
    """Запускает бота"""
    print("🚀 Запуск бота...")
    
    # Проверяем наличие файлов
    if not os.path.exists("run_bot.py"):
        print("   ❌ Файл run_bot.py не найден!")
        return False
    
    if not os.path.exists(".env"):
        print("   ❌ Файл .env не найден!")
        print("   💡 Создайте файл .env с BOT_TOKEN")
        return False
    
    # Проверяем, не запущен ли уже бот
    is_running, pid = check_bot_running()
    if is_running:
        print(f"   ⚠️ Бот уже запущен (PID: {pid})")
        choice = input("   Остановить существующий бот? (y/n): ").lower()
        if choice == 'y':
            stop_existing_bot()
        else:
            print("   ❌ Запуск отменен")
            return False
    
    try:
        # Запускаем бота
        process = subprocess.Popen([sys.executable, "run_bot.py"], 
                                 stdout=subprocess.PIPE, 
                                 stderr=subprocess.PIPE)
        print(f"   ✅ Бот запущен (PID: {process.pid})")
        
        # Ждем и проверяем
        time.sleep(3)
        if process.poll() is None:
            print("   ✅ Бот работает стабильно")
            return True
        else:
            print("   ❌ Бот завершился неожиданно")
            stdout, stderr = process.communicate()
            if stderr:
                print(f"   Ошибка: {stderr.decode('utf-8', errors='replace')}")
            return False
            
    except Exception as e:
        print(f"   ❌ Ошибка запуска: {e}")
        return False

def main():
    """Основная функция"""
    print("🤖 Безопасный запуск бота РПРЗ")
    print("=" * 40)
    
    # Проверяем Python версию
    if sys.version_info < (3, 8):
        print("❌ Требуется Python 3.8 или выше")
        return
    
    print(f"✅ Python версия: {sys.version}")
    
    # Проверяем зависимости
    try:
        import telebot
        import loguru
        print("✅ Основные зависимости установлены")
    except ImportError as e:
        print(f"❌ Отсутствует зависимость: {e}")
        print("💡 Установите: pip install -r requirements.txt")
        return
    
    # Запускаем бота
    if start_bot():
        print("\n🎉 Бот успешно запущен!")
        print("📝 Для остановки используйте: python stop_bot.py")
        print("📊 Для просмотра логов: python view_logs_utf8.ps1")
    else:
        print("\n❌ Не удалось запустить бота")
        print("💡 Проверьте логи и настройки")

if __name__ == '__main__':
    main()

