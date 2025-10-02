#!/usr/bin/env python3
"""
Скрипт для запуска всех тестов проекта RPRZ Safety Bot
Поддерживает различные режимы тестирования и отчеты
"""

import os
import sys
import subprocess
import argparse
import time
from pathlib import Path

# Добавляем путь к модулям
sys.path.insert(0, os.path.join(os.path.dirname(__file__)))

def run_command(command, description=""):
    """Выполняет команду и возвращает результат"""
    print(f"\n[EXEC] {description}")
    print(f"Команда: {command}")
    print("-" * 50)
    
    start_time = time.time()
    # Используем UTF-8 кодировку для Windows
    result = subprocess.run(command, shell=True, capture_output=True, text=True, encoding='utf-8', errors='replace')
    end_time = time.time()
    
    print(f"[TIME] Время выполнения: {end_time - start_time:.2f} секунд")
    
    if result.returncode == 0:
        print("[OK] Успешно выполнено")
        if result.stdout:
            print("Вывод:")
            print(result.stdout)
    else:
        print("[ERROR] Ошибка выполнения")
        if result.stderr:
            print("Ошибки:")
            print(result.stderr)
        if result.stdout:
            print("Вывод:")
            print(result.stdout)
    
    return result.returncode == 0

def check_dependencies():
    """Проверяет наличие необходимых зависимостей"""
    print("[CHECK] Проверка зависимостей...")
    
    required_packages = [
        'pytest',
        'pytest-cov',
        'pytest-mock',
        'coverage'
    ]
    
    missing_packages = []
    
    for package in required_packages:
        try:
            __import__(package.replace('-', '_'))
            print(f"[OK] {package}")
        except ImportError:
            print(f"[MISSING] {package} - не установлен")
            missing_packages.append(package)
    
    if missing_packages:
        print(f"\n[WARNING] Отсутствуют пакеты: {', '.join(missing_packages)}")
        print("Установите их командой: pip install " + " ".join(missing_packages))
        return False
    
    return True

def run_unit_tests():
    """Запускает unit тесты"""
    print("\n[TEST] Запуск unit тестов...")
    
    commands = [
        ("python -m pytest tests/test_main.py -v", "Тесты основного модуля"),
        ("python -m pytest tests/test_handlers.py -v", "Тесты обработчиков"),
        ("python -m pytest tests/test_notifications.py -v", "Тесты уведомлений"),
        ("python -m pytest tests/test_config.py -v", "Тесты конфигурации"),
        ("python -m pytest tests/test_utils.py -v", "Тесты утилит")
    ]
    
    success_count = 0
    total_count = len(commands)
    
    for command, description in commands:
        if run_command(command, description):
            success_count += 1
    
    print(f"\n[RESULT] Unit тесты: {success_count}/{total_count} успешно")
    return success_count == total_count

def run_integration_tests():
    """Запускает интеграционные тесты"""
    print("\n[INTEGRATION] Запуск интеграционных тестов...")
    
    command = "python -m pytest tests/test_integration.py -v"
    return run_command(command, "Интеграционные тесты")

def run_all_tests():
    """Запускает все тесты"""
    print("\n[ALL] Запуск всех тестов...")
    
    command = "python -m pytest tests/ -v --tb=short"
    return run_command(command, "Все тесты")

def run_tests_with_coverage():
    """Запускает тесты с покрытием кода"""
    print("\n[COVERAGE] Запуск тестов с покрытием кода...")
    
    commands = [
        ("python -m pytest tests/ --cov=bot --cov-report=html --cov-report=term", 
         "Тесты с HTML отчетом покрытия"),
        ("python -m pytest tests/ --cov=bot --cov-report=xml", 
         "Тесты с XML отчетом покрытия")
    ]
    
    success = True
    for command, description in commands:
        if not run_command(command, description):
            success = False
    
    if success:
        print("\n[REPORTS] Отчеты покрытия созданы:")
        print("  - HTML: htmlcov/index.html")
        print("  - XML: coverage.xml")
    
    return success

def run_specific_tests(test_pattern):
    """Запускает конкретные тесты по паттерну"""
    print(f"\n[TARGET] Запуск тестов по паттерну: {test_pattern}")
    
    command = f"python -m pytest tests/ -k '{test_pattern}' -v"
    return run_command(command, f"Тесты: {test_pattern}")

def run_smoke_tests():
    """Запускает smoke тесты"""
    print("\n[SMOKE] Запуск smoke тестов...")
    
    command = "python -m pytest tests/ -m smoke -v"
    return run_command(command, "Smoke тесты")

def run_performance_tests():
    """Запускает тесты производительности"""
    print("\n[PERFORMANCE] Запуск тестов производительности...")
    
    command = "python -m pytest tests/ -m performance -v"
    return run_command(command, "Тесты производительности")

def generate_test_report():
    """Генерирует отчет о тестах"""
    print("\n[REPORT] Генерация отчета о тестах...")
    
    command = "python -m pytest tests/ --html=test_report.html --self-contained-html"
    return run_command(command, "HTML отчет о тестах")

def clean_test_artifacts():
    """Очищает артефакты тестов"""
    print("\n[CLEAN] Очистка артефактов тестов...")
    
    artifacts = [
        ".pytest_cache",
        "htmlcov",
        "coverage.xml",
        "test_report.html",
        "__pycache__",
        "*.pyc"
    ]
    
    for artifact in artifacts:
        if os.path.exists(artifact):
            if os.path.isdir(artifact):
                import shutil
                shutil.rmtree(artifact)
                print(f"[OK] Удалена директория: {artifact}")
            else:
                os.remove(artifact)
                print(f"[OK] Удален файл: {artifact}")

def main():
    """Основная функция"""
    parser = argparse.ArgumentParser(description="Запуск тестов RPRZ Safety Bot")
    parser.add_argument("--mode", choices=[
        "unit", "integration", "all", "coverage", "smoke", 
        "performance", "specific", "clean"
    ], default="all", help="Режим тестирования")
    parser.add_argument("--pattern", help="Паттерн для конкретных тестов")
    parser.add_argument("--no-deps", action="store_true", help="Пропустить проверку зависимостей")
    parser.add_argument("--report", action="store_true", help="Генерировать отчет")
    
    args = parser.parse_args()
    
    print("RPRZ Safety Bot - Система тестирования")
    print("=" * 50)
    
    # Проверка зависимостей
    if not args.no_deps:
        if not check_dependencies():
            print("\n[ERROR] Не все зависимости установлены. Завершение.")
            return 1
    
    # Выбор режима тестирования
    success = True
    
    if args.mode == "unit":
        success = run_unit_tests()
    elif args.mode == "integration":
        success = run_integration_tests()
    elif args.mode == "all":
        success = run_all_tests()
    elif args.mode == "coverage":
        success = run_tests_with_coverage()
    elif args.mode == "smoke":
        success = run_smoke_tests()
    elif args.mode == "performance":
        success = run_performance_tests()
    elif args.mode == "specific":
        if not args.pattern:
            print("[ERROR] Необходимо указать паттерн с --pattern")
            return 1
        success = run_specific_tests(args.pattern)
    elif args.mode == "clean":
        clean_test_artifacts()
        print("[OK] Очистка завершена")
        return 0
    
    # Генерация отчета
    if args.report and success:
        generate_test_report()
    
    # Итоговый результат
    if success:
        print("\n[SUCCESS] Все тесты прошли успешно!")
        return 0
    else:
        print("\n[FAILED] Некоторые тесты не прошли!")
        return 1

if __name__ == "__main__":
    sys.exit(main())

