#!/usr/bin/env python3
"""
Финальный безопасный запуск бота
"""

import os
import sys
import subprocess
import time

def main():
    """Основная функция"""
    print("Финальный запуск бота РПРЗ")
    print("=" * 40)
    
    # 1. Останавливаем все процессы
    print("1. Остановка всех процессов...")
    try:
        subprocess.run(["python", "force_stop.py"], timeout=30)
        print("   Процессы остановлены")
    except:
        print("   Ошибка остановки процессов")
    
    # 2. Ждем
    print("2. Ожидание 5 секунд...")
    time.sleep(5)
    
    # 3. Запускаем бота
    print("3. Запуск бота...")
    try:
        if os.path.exists("run_bot.py"):
            subprocess.Popen([sys.executable, "run_bot.py"])
            print("   Бот запущен")
            print("   Для остановки: python force_stop.py")
            print("   Для мониторинга: python monitor_logs_improved.py")
        else:
            print("   Файл run_bot.py не найден")
    except Exception as e:
        print(f"   Ошибка запуска: {e}")
    
    print("Готово!")

if __name__ == '__main__':
    main()

