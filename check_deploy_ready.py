#!/usr/bin/env python3
"""
Скрипт проверки готовности проекта к деплою на Railway
"""
import os
import sys
from pathlib import Path


def check_file_exists(filepath, required=True):
    """Проверяет существование файла"""
    exists = Path(filepath).exists()
    status = "✅" if exists else ("❌" if required else "⚠️")
    print(f"{status} {filepath}: {'найден' if exists else 'не найден'}")
    return exists


def check_env_file():
    """Проверяет .env файл"""
    print("\n" + "=" * 50)
    print("Проверка: .env файл (локальная разработка)")
    print("=" * 50)

    if Path(".env").exists():
        print("✅ .env файл найден (для локальной разработки)")

        # Проверяем содержимое
        with open(".env", "r", encoding="utf-8") as f:
            content = f.read()

        has_token = (
            "BOT_TOKEN=" in content
            and len(content.split("BOT_TOKEN=")[1].split("\n")[0].strip()) > 20
        )
        has_admin = (
            "ADMIN_CHAT_ID=" in content
            and len(content.split("ADMIN_CHAT_ID=")[1].split("\n")[0].strip()) > 5
        )

        if has_token:
            print("  ✅ BOT_TOKEN настроен")
        else:
            print("  ❌ BOT_TOKEN не настроен или пустой")

        if has_admin:
            print("  ✅ ADMIN_CHAT_ID настроен")
        else:
            print("  ⚠️ ADMIN_CHAT_ID не настроен или пустой")

        return has_token and has_admin
    else:
        print("⚠️ .env файл не найден (нормально для Railway деплоя)")
        print("  ℹ️ Для локальной разработки создайте .env из env.example")
        return True  # Не критично для Railway


def check_gitignore():
    """Проверяет .gitignore"""
    print("\n" + "=" * 50)
    print("Проверка: .gitignore (безопасность)")
    print("=" * 50)

    if not Path(".gitignore").exists():
        print("❌ .gitignore не найден!")
        return False

    with open(".gitignore", "r", encoding="utf-8") as f:
        content = f.read()

    checks = {
        ".env": ".env" in content,
        "*.log": "*.log" in content,
        "__pycache__": "__pycache__" in content,
        "*.key": "*.key" in content or "*.pem" in content,
    }

    all_good = True
    for item, exists in checks.items():
        status = "✅" if exists else "❌"
        print(f"{status} {item} в .gitignore: {'да' if exists else 'НЕТ - ДОБАВЬТЕ!'}")
        if not exists:
            all_good = False

    return all_good


def check_railway_files():
    """Проверяет файлы для Railway"""
    print("\n" + "=" * 50)
    print("Проверка: Файлы конфигурации Railway")
    print("=" * 50)

    files = {
        "Procfile": True,
        "railway.json": True,
        "nixpacks.toml": True,
        "runtime.txt": True,
        "requirements.txt": True,
    }

    all_good = True
    for filepath, required in files.items():
        if not check_file_exists(filepath, required):
            all_good = False

    return all_good


def check_requirements():
    """Проверяет requirements.txt"""
    print("\n" + "=" * 50)
    print("Проверка: requirements.txt")
    print("=" * 50)

    if not Path("requirements.txt").exists():
        print("❌ requirements.txt не найден!")
        return False

    with open("requirements.txt", "r", encoding="utf-8") as f:
        content = f.read()

    required_packages = [
        "pyTelegramBotAPI",
        "python-dotenv",
        "loguru",
        "flask",
        "psutil",
    ]

    all_good = True
    for package in required_packages:
        if package.lower() in content.lower():
            print(f"✅ {package} найден")
        else:
            print(f"❌ {package} НЕ НАЙДЕН!")
            all_good = False

    return all_good


def check_main_py():
    """Проверяет bot/main.py"""
    print("\n" + "=" * 50)
    print("Проверка: bot/main.py")
    print("=" * 50)

    if not Path("bot/main.py").exists():
        print("❌ bot/main.py не найден!")
        return False

    print("✅ bot/main.py найден")

    # Проверяем импорты
    with open("bot/main.py", "r", encoding="utf-8") as f:
        content = f.read()

    checks = {
        "telebot": "import telebot" in content,
        "Flask": "from flask import Flask" in content,
        "load_dotenv": "from dotenv import load_dotenv" in content,
    }

    all_good = True
    for item, exists in checks.items():
        status = "✅" if exists else "❌"
        print(f"  {status} Импорт {item}: {'да' if exists else 'НЕТ'}")
        if not exists:
            all_good = False

    return all_good


def check_directory_structure():
    """Проверяет структуру директорий"""
    print("\n" + "=" * 50)
    print("Проверка: Структура директорий")
    print("=" * 50)

    dirs = {
        "bot": True,
        "configs": True,
        "logs": False,
        "assets": False,
    }

    for dirpath, required in dirs.items():
        exists = Path(dirpath).exists()
        status = "✅" if exists else ("⚠️" if not required else "❌")
        print(f"{status} {dirpath}/: {'найден' if exists else 'не найден'}")

    return True  # Не критично


def main():
    """Основная функция проверки"""
    print("\n" + "=" * 50)
    print("🔍 ПРОВЕРКА ГОТОВНОСТИ К RAILWAY ДЕПЛОЮ")
    print("=" * 50)

    checks = [
        ("Файлы конфигурации Railway", check_railway_files),
        ("requirements.txt", check_requirements),
        (".gitignore (безопасность)", check_gitignore),
        (".env файл", check_env_file),
        ("bot/main.py", check_main_py),
        ("Структура директорий", check_directory_structure),
    ]

    results = []
    for name, check_func in checks:
        try:
            result = check_func()
            results.append((name, result))
        except Exception as e:
            print(f"\n❌ Ошибка при проверке {name}: {e}")
            results.append((name, False))

    # Итоги
    print("\n" + "=" * 50)
    print("📊 ИТОГИ ПРОВЕРКИ")
    print("=" * 50)

    failed = []
    for name, result in results:
        status = "✅" if result else "❌"
        print(f"{status} {name}")
        if not result:
            failed.append(name)

    print("\n" + "=" * 50)
    if not failed:
        print("✅ ВСЕ ПРОВЕРКИ ПРОЙДЕНЫ!")
        print("=" * 50)
        print("\n🚀 Проект готов к деплою на Railway!")
        print("\nСледующие шаги:")
        print("1. Запушьте код в GitHub:")
        print("   git add .")
        print('   git commit -m "Готов к Railway деплою"')
        print("   git push origin main")
        print("\n2. Откройте https://railway.app")
        print("3. Создайте проект из GitHub репозитория")
        print("4. Добавьте переменные: BOT_TOKEN, ADMIN_CHAT_ID")
        print("\n📖 Полная инструкция: RAILWAY_DEPLOY_GUIDE.md")
        print("⚡ Быстрый старт: RAILWAY_QUICKSTART.md")
        return 0
    else:
        print("❌ ПРОВЕРКА НЕ ПРОЙДЕНА")
        print("=" * 50)
        print("\nОшибки в следующих проверках:")
        for name in failed:
            print(f"  - {name}")
        print("\n🔧 Исправьте ошибки и запустите проверку снова:")
        print("   python check_deploy_ready.py")
        return 1


if __name__ == "__main__":
    sys.exit(main())
