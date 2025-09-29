#!/usr/bin/env python3
"""
Простой запуск бота
"""

import os
import sys
import subprocess
import time

def start_bot():
    """Запуск бота"""
    print("Запуск RPRZ Safety Bot...")
    
    # Останавливаем процессы
    print("Остановка процессов Python...")
    try:
        subprocess.run(["taskkill", "/f", "/im", "python.exe"], 
                      capture_output=True, timeout=5)
    except:
        pass
    
    # Ждем
    time.sleep(2)
    
    # Запускаем бота
    print("Запуск бота...")
    print("Найдите бота @FixPriceKusr_bot в Telegram")
    print("Нажмите Ctrl+C для остановки")
    print()
    
    try:
        subprocess.run([sys.executable, "run_bot.py"])
    except KeyboardInterrupt:
        print("\nБот остановлен")
    except Exception as e:
        print(f"Ошибка: {e}")

if __name__ == '__main__':
    start_bot()
