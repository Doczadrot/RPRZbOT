#!/usr/bin/env python3
"""
Простое исправление проблем с ботом
"""

import os
import sys
import subprocess
import time

def main():
    """Основная функция"""
    print("Исправление проблем с ботом РПРЗ")
    print("=" * 50)
    
    # 1. Останавливаем процессы
    print("\n1. Остановка процессов Python...")
    try:
        subprocess.run(["taskkill", "/f", "/im", "python.exe"], 
                      capture_output=True, timeout=10)
        print("   Процессы остановлены")
    except:
        print("   Процессы не найдены")
    
    time.sleep(3)
    
    # 2. Устанавливаем зависимости
    print("\n2. Установка зависимостей...")
    try:
        result = subprocess.run([sys.executable, "-m", "pip", "install", "-r", "requirements.txt"], 
                              capture_output=True, text=True, timeout=60)
        if result.returncode == 0:
            print("   Зависимости установлены")
        else:
            print(f"   Ошибка: {result.stderr}")
    except Exception as e:
        print(f"   Ошибка: {e}")
    
    # 3. Очищаем логи
    print("\n3. Очистка логов...")
    if os.path.exists("logs"):
        for file in os.listdir("logs"):
            if file.endswith('.log'):
                try:
                    os.remove(os.path.join("logs", file))
                    print(f"   Удален: {file}")
                except:
                    pass
    
    # 4. Запускаем бота
    print("\n4. Запуск бота...")
    try:
        if os.path.exists("run_bot.py"):
            subprocess.Popen([sys.executable, "run_bot.py"])
            print("   Бот запущен")
        else:
            print("   Файл run_bot.py не найден")
    except Exception as e:
        print(f"   Ошибка запуска: {e}")
    
    print("\nГотово!")

if __name__ == '__main__':
    main()

