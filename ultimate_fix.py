#!/usr/bin/env python3
"""
Ультимативное исправление проблемы 409
"""

import os
import sys
import subprocess
import time
import requests

def clear_webhook():
    """Очищает webhook через API"""
    print("Очистка webhook через API...")
    
    # Читаем токен из .env
    try:
        with open('.env', 'r') as f:
            content = f.read()
            for line in content.split('\n'):
                if line.startswith('BOT_TOKEN='):
                    token = line.split('=')[1].strip()
                    break
        else:
            print("Токен не найден в .env")
            return False
    except:
        print("Файл .env не найден")
        return False
    
    # Очищаем webhook
    try:
        url = f"https://api.telegram.org/bot{token}/deleteWebhook"
        response = requests.get(url, timeout=10)
        if response.status_code == 200:
            print("Webhook очищен")
            return True
        else:
            print(f"Ошибка очистки webhook: {response.status_code}")
            return False
    except Exception as e:
        print(f"Ошибка: {e}")
        return False

def main():
    """Основная функция"""
    print("Ультимативное исправление проблемы 409")
    print("=" * 50)
    
    # 1. Останавливаем все процессы
    print("1. Остановка всех процессов...")
    try:
        subprocess.run(["python", "force_stop.py"], timeout=30)
        print("   Процессы остановлены")
    except:
        print("   Ошибка остановки процессов")
    
    # 2. Очищаем webhook
    print("2. Очистка webhook...")
    clear_webhook()
    
    # 3. Ждем долго
    print("3. Ожидание 10 секунд...")
    time.sleep(10)
    
    # 4. Запускаем бота
    print("4. Запуск бота...")
    try:
        if os.path.exists("run_bot.py"):
            subprocess.Popen([sys.executable, "run_bot.py"])
            print("   Бот запущен")
            print("   Подождите 30 секунд для стабилизации...")
            time.sleep(30)
            print("   Проверьте логи: python monitor_logs_improved.py recent")
        else:
            print("   Файл run_bot.py не найден")
    except Exception as e:
        print(f"   Ошибка запуска: {e}")
    
    print("Готово!")

if __name__ == '__main__':
    main()

