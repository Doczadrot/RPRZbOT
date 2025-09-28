#!/usr/bin/env python3
"""
Скрипт для запуска бота в фоновом режиме
"""
import os
import sys
import subprocess
import time

def start_bot():
    """Запустить бота"""
    print("🤖 Запуск телеграм-бота РПРЗ...")
    
    # Проверяем наличие .env файла
    if not os.path.exists('.env'):
        print("❌ Файл .env не найден!")
        print("Запустите: python setup_env.py")
        return
    
    # Проверяем наличие токена
    with open('.env', 'r') as f:
        content = f.read()
        if 'BOT_TOKEN=YOUR_TOKEN' in content:
            print("❌ Токен бота не настроен!")
            print("Отредактируйте файл .env")
            return
    
    try:
        print("✅ Запуск бота...")
        print("📱 Бот готов к работе в Telegram!")
        print("⏹️ Для остановки нажмите Ctrl+C")
        print("-" * 50)
        
        # Запускаем бота
        subprocess.run([sys.executable, "bot/main_refactored.py"])
        
    except KeyboardInterrupt:
        print("\n🛑 Бот остановлен пользователем")
    except Exception as e:
        print(f"❌ Ошибка запуска бота: {e}")

if __name__ == "__main__":
    start_bot()
