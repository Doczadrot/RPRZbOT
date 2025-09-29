#!/usr/bin/env python3
"""
Улучшенный мониторинг логов бота
"""

import os
import sys
import time
import threading
from datetime import datetime
from pathlib import Path

def monitor_file(file_path, callback):
    """Мониторит файл на изменения"""
    if not os.path.exists(file_path):
        print(f"❌ Файл не найден: {file_path}")
        return
    
    print(f"👀 Мониторинг: {file_path}")
    
    # Читаем файл с конца
    with open(file_path, 'r', encoding='utf-8', errors='replace') as f:
        f.seek(0, 2)  # Переходим в конец файла
        
        while True:
            line = f.readline()
            if line:
                callback(line.strip())
            else:
                time.sleep(0.1)

def colorize_log_line(line):
    """Цветизирует строку лога"""
    if "ERROR" in line:
        return f"\033[91m{line}\033[0m"  # Красный
    elif "WARNING" in line:
        return f"\033[93m{line}\033[0m"  # Желтый
    elif "INFO" in line:
        return f"\033[92m{line}\033[0m"  # Зеленый
    elif "DEBUG" in line:
        return f"\033[96m{line}\033[0m"  # Голубой
    else:
        return line

def print_log_line(line):
    """Выводит строку лога с цветом"""
    if line:
        colored_line = colorize_log_line(line)
        print(colored_line)

def monitor_all_logs():
    """Мониторит все файлы логов"""
    logs_dir = Path("logs")
    if not logs_dir.exists():
        print("❌ Папка logs не найдена!")
        return
    
    log_files = [
        "app.log",
        "errors.log", 
        "user_actions.log",
        "api_requests.log"
    ]
    
    print("🔍 Мониторинг логов бота РПРЗ")
    print("=" * 50)
    print("Нажмите Ctrl+C для остановки")
    print("=" * 50)
    
    threads = []
    
    for log_file in log_files:
        file_path = logs_dir / log_file
        if file_path.exists():
            thread = threading.Thread(
                target=monitor_file,
                args=(str(file_path), print_log_line),
                daemon=True
            )
            thread.start()
            threads.append(thread)
        else:
            print(f"⚠️ Файл не найден: {log_file}")
    
    if not threads:
        print("❌ Нет файлов логов для мониторинга!")
        return
    
    try:
        # Ждем завершения всех потоков
        for thread in threads:
            thread.join()
    except KeyboardInterrupt:
        print("\n🛑 Мониторинг остановлен")

def show_recent_logs(lines=20):
    """Показывает последние строки логов"""
    logs_dir = Path("logs")
    if not logs_dir.exists():
        print("❌ Папка logs не найдена!")
        return
    
    print(f"📋 Последние {lines} строк логов:")
    print("=" * 50)
    
    # Показываем последние строки из app.log
    app_log = logs_dir / "app.log"
    if app_log.exists():
        print(f"\n📄 {app_log.name}:")
        with open(app_log, 'r', encoding='utf-8', errors='replace') as f:
            all_lines = f.readlines()
            for line in all_lines[-lines:]:
                print_log_line(line.strip())
    
    # Показываем ошибки
    errors_log = logs_dir / "errors.log"
    if errors_log.exists():
        print(f"\n🚨 {errors_log.name}:")
        with open(errors_log, 'r', encoding='utf-8', errors='replace') as f:
            all_lines = f.readlines()
            for line in all_lines[-10:]:  # Последние 10 ошибок
                print_log_line(line.strip())

def main():
    """Основная функция"""
    if len(sys.argv) > 1:
        if sys.argv[1] == "recent":
            show_recent_logs()
        elif sys.argv[1].isdigit():
            show_recent_logs(int(sys.argv[1]))
        else:
            print("Использование: python monitor_logs_improved.py [recent|число_строк]")
    else:
        monitor_all_logs()

if __name__ == '__main__':
    main()

