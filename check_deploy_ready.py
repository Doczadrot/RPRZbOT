#!/usr/bin/env python3
"""
Скрипт проверки готовности к деплою на Railway
Проверяет все необходимые файлы и конфигурации
"""

import os
import sys
import json
from pathlib import Path

def check_file_exists(filepath, description):
    """Проверяет существование файла"""
    if Path(filepath).exists():
        print(f"✅ {description}: {filepath}")
        return True
    else:
        print(f"❌ {description}: {filepath} - НЕ НАЙДЕН")
        return False

def check_file_content(filepath, required_content, description):
    """Проверяет содержимое файла"""
    if not Path(filepath).exists():
        print(f"❌ {description}: файл не найден")
        return False
    
    content = Path(filepath).read_text()
    if required_content in content:
        print(f"✅ {description}: содержимое корректно")
        return True
    else:
        print(f"❌ {description}: содержимое некорректно")
        return False

def main():
    print("🚀 Проверка готовности к деплою на Railway")
    print("=" * 50)
    
    checks = []
    
    # Проверяем основные файлы
    checks.append(check_file_exists("requirements.txt", "Файл зависимостей"))
    checks.append(check_file_exists("bot/main.py", "Главный файл бота"))
    checks.append(check_file_exists("nixpacks.toml", "Конфигурация Nixpacks"))
    checks.append(check_file_exists(".nixpacks.toml", "Резервная конфигурация Nixpacks"))
    checks.append(check_file_exists("Dockerfile", "Резервный Dockerfile"))
    checks.append(check_file_exists("railway.json", "Конфигурация Railway"))
    checks.append(check_file_exists("Procfile", "Procfile"))
    
    # Проверяем содержимое файлов
    checks.append(check_file_content("nixpacks.toml", "python310", "Python 3.10 в Nixpacks"))
    checks.append(check_file_content("nixpacks.toml", "break-system-packages", "Флаг --break-system-packages"))
    checks.append(check_file_content("railway.json", "NIXPACKS", "Builder NIXPACKS"))
    
    # Проверяем .env файл (должен быть в .gitignore)
    if Path(".env").exists():
        print("⚠️  .env файл найден - убедитесь, что он в .gitignore")
    else:
        print("✅ .env файл не в репозитории (корректно)")
    
    print("\n" + "=" * 50)
    
    if all(checks):
        print("🎉 ВСЕ ПРОВЕРКИ ПРОЙДЕНЫ! Проект готов к деплою.")
        print("\n📋 Следующие шаги:")
        print("1. git add . && git commit -m 'готов к деплою'")
        print("2. git push origin main")
        print("3. Создать проект на Railway")
        print("4. Добавить переменные окружения (BOT_TOKEN, ADMIN_CHAT_ID)")
        return 0
    else:
        print("❌ НЕКОТОРЫЕ ПРОВЕРКИ НЕ ПРОЙДЕНЫ!")
        print("Исправьте ошибки перед деплоем.")
        return 1

if __name__ == "__main__":
    sys.exit(main())