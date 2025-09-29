#!/usr/bin/env python3
"""
Проверка логов в правильной кодировке
"""

import os
import sys

def check_logs():
    """Проверяет логи в правильной кодировке"""
    print("Проверка логов в UTF-8 кодировке...")
    
    log_files = [
        "logs/app.log",
        "logs/user_actions.log", 
        "logs/activity.csv",
        "logs/incidents.json",
        "logs/suggestions.json"
    ]
    
    for log_file in log_files:
        if os.path.exists(log_file):
            print(f"\n--- {log_file} (последние 5 строк) ---")
            try:
                with open(log_file, 'r', encoding='utf-8-sig') as f:
                    lines = f.readlines()
                    for line in lines[-5:]:
                        print(line.rstrip())
            except Exception as e:
                print(f"Ошибка чтения: {e}")
        else:
            print(f"\n{log_file} - файл не найден")
    
    print("\nГотово!")

if __name__ == '__main__':
    check_logs()
