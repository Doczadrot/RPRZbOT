#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Скрипт проверки готовности проекта к деплою на Railway
"""

import os
import sys
from pathlib import Path

# Фикс кодировки для Windows
if sys.platform == 'win32':
    import codecs
    sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer, 'strict')
    sys.stderr = codecs.getwriter('utf-8')(sys.stderr.buffer, 'strict')

def check_file_exists(filename, required=True):
    """Проверка существования файла"""
    exists = Path(filename).exists()
    status = "✅" if exists else ("❌" if required else "⚠️")
    print(f"{status} {filename}: {'найден' if exists else 'не найден'}")
    return exists or not required

def check_file_content(filename, should_not_contain=None):
    """Проверка содержимого файла"""
    try:
        with open(filename, 'r', encoding='utf-8') as f:
            content = f.read()
            if should_not_contain:
                for pattern in should_not_contain:
                    if pattern in content:
                        print(f"❌ {filename} содержит '{pattern}' - УДАЛИТЕ!")
                        return False
        print(f"✅ {filename} проверен")
        return True
    except FileNotFoundError:
        print(f"❌ {filename} не найден")
        return False

def check_gitignore():
    """Проверка .gitignore"""
    print("\n🔍 Проверка .gitignore...")
    required_patterns = ['.env', '*.log', 'bot.lock', 'bot.pid', '__pycache__']
    
    if not Path('.gitignore').exists():
        print("❌ .gitignore не найден")
        return False
    
    with open('.gitignore', 'r', encoding='utf-8') as f:
        content = f.read()
    
    all_good = True
    for pattern in required_patterns:
        if pattern in content:
            print(f"✅ .gitignore содержит '{pattern}'")
        else:
            print(f"❌ .gitignore НЕ содержит '{pattern}'")
            all_good = False
    
    return all_good

def check_env_not_in_git():
    """Проверка, что .env не в Git"""
    print("\n🔍 Проверка, что .env не в репозитории...")
    
    # Проверяем через git ls-files
    import subprocess
    try:
        result = subprocess.run(
            ['git', 'ls-files', '.env'],
            capture_output=True,
            text=True,
            timeout=5
        )
        
        if result.stdout.strip():  # Если есть вывод - файл в Git
            print("❌ КРИТИЧНО: .env файл находится в Git репозитории!")
            print("   Выполните: git rm --cached .env")
            return False
        else:
            print("✅ .env не в Git репозитории")
            return True
    except Exception as e:
        print(f"⚠️ Не удалось проверить Git: {e}")
        return True  # Не блокируем деплой

def check_requirements():
    """Проверка requirements.txt"""
    print("\n🔍 Проверка requirements.txt...")
    
    required_packages = [
        'pyTelegramBotAPI',
        'python-dotenv',
        'loguru',
        'requests',
        'psutil'
    ]
    
    if not Path('requirements.txt').exists():
        print("❌ requirements.txt не найден")
        return False
    
    with open('requirements.txt', 'r', encoding='utf-8') as f:
        content = f.read()
    
    all_good = True
    for package in required_packages:
        if package in content:
            print(f"✅ {package} найден в requirements.txt")
        else:
            print(f"❌ {package} НЕ найден в requirements.txt")
            all_good = False
    
    return all_good

def main():
    """Главная функция проверки"""
    print("=" * 60)
    print("🚂 ПРОВЕРКА ГОТОВНОСТИ К ДЕПЛОЮ НА RAILWAY")
    print("=" * 60)
    
    all_checks = []
    
    # Проверка обязательных файлов
    print("\n📁 Проверка обязательных файлов...")
    all_checks.append(check_file_exists('Procfile', required=True))
    all_checks.append(check_file_exists('runtime.txt', required=True))
    all_checks.append(check_file_exists('requirements.txt', required=True))
    all_checks.append(check_file_exists('.gitignore', required=True))
    
    # Проверка опциональных файлов
    print("\n📁 Проверка опциональных файлов...")
    check_file_exists('railway.json', required=False)
    check_file_exists('.railwayignore', required=False)
    
    # Проверка содержимого Procfile
    print("\n📝 Проверка Procfile...")
    if Path('Procfile').exists():
        with open('Procfile', 'r', encoding='utf-8') as f:
            procfile_content = f.read()
            if 'python' in procfile_content and 'bot/main.py' in procfile_content:
                print("✅ Procfile содержит правильную команду запуска")
                all_checks.append(True)
            else:
                print("❌ Procfile не содержит 'python bot/main.py'")
                all_checks.append(False)
    
    # Проверка runtime.txt
    print("\n🐍 Проверка runtime.txt...")
    if Path('runtime.txt').exists():
        with open('runtime.txt', 'r', encoding='utf-8') as f:
            runtime_content = f.read().strip()
            if runtime_content.startswith('python-3.'):
                print(f"✅ runtime.txt: {runtime_content}")
                all_checks.append(True)
            else:
                print(f"❌ runtime.txt не содержит версию Python: {runtime_content}")
                all_checks.append(False)
    
    # Проверка .gitignore
    all_checks.append(check_gitignore())
    
    # Проверка .env не в Git
    all_checks.append(check_env_not_in_git())
    
    # Проверка requirements.txt
    all_checks.append(check_requirements())
    
    # Проверка структуры проекта
    print("\n🗂️ Проверка структуры проекта...")
    all_checks.append(check_file_exists('bot/main.py', required=True))
    all_checks.append(check_file_exists('bot/handlers.py', required=True))
    
    # Итоги
    print("\n" + "=" * 60)
    if all(all_checks):
        print("✅ ВСЕ ПРОВЕРКИ ПРОЙДЕНЫ!")
        print("🚀 Проект готов к деплою на Railway")
        print("\nСледующие шаги:")
        print("1. git add .")
        print("2. git commit -m 'Готов к деплою'")
        print("3. git push origin main")
        print("4. Перейдите на https://railway.app")
        print("5. Создайте проект из GitHub репозитория")
        print("6. Добавьте переменные окружения (BOT_TOKEN, ADMIN_CHAT_ID)")
        return 0
    else:
        print("❌ ЕСТЬ ПРОБЛЕМЫ!")
        print("⚠️ Исправьте ошибки перед деплоем")
        print("\n📖 Смотрите полную инструкцию: RAILWAY_DEPLOY_GUIDE.md")
        return 1

if __name__ == '__main__':
    sys.exit(main())
