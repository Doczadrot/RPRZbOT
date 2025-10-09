#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Скрипт проверки минимального покрытия кода тестами.

Используется в CI/CD pipeline для обеспечения качества кода.
"""

import sys
import xml.etree.ElementTree as ET
from pathlib import Path

# Минимальное требуемое покрытие (%)
MINIMUM_COVERAGE = 70.0

# Фикс кодировки для Windows
if sys.platform == "win32":
    import codecs

    sys.stdout = codecs.getwriter("utf-8")(sys.stdout.buffer, "strict")
    sys.stderr = codecs.getwriter("utf-8")(sys.stderr.buffer, "strict")


def parse_coverage_xml(xml_path):
    """Парсит coverage.xml и возвращает процент покрытия."""
    try:
        tree = ET.parse(xml_path)
        root = tree.getroot()

        # Ищем общее покрытие
        coverage_element = root.find(".")
        if coverage_element is not None:
            line_rate = float(coverage_element.get("line-rate", 0))
            return line_rate * 100

        return 0.0
    except FileNotFoundError:
        print(f"❌ Файл {xml_path} не найден")
        print("   Запустите: pytest --cov=bot --cov-report=xml")
        return None
    except Exception as e:
        print(f"❌ Ошибка парсинга {xml_path}: {e}")
        return None


def get_package_coverage(xml_path):
    """Получает покрытие по пакетам."""
    try:
        tree = ET.parse(xml_path)
        root = tree.getroot()

        packages = {}
        for package in root.findall(".//package"):
            name = package.get("name", "unknown")
            line_rate = float(package.get("line-rate", 0))
            packages[name] = line_rate * 100

        return packages
    except Exception:
        return {}


def print_coverage_report(total_coverage, package_coverage):
    """Выводит детальный отчет о покрытии."""
    print("\n" + "=" * 60)
    print("📊 ОТЧЕТ О ПОКРЫТИИ КОДА ТЕСТАМИ")
    print("=" * 60)

    print(f"\n📈 Общее покрытие: {total_coverage:.2f}%")
    print(f"🎯 Минимальное требование: {MINIMUM_COVERAGE:.2f}%")

    if total_coverage >= MINIMUM_COVERAGE:
        print("✅ УСПЕХ: Покрытие соответствует требованиям!")
        status = "PASS"
    else:
        diff = MINIMUM_COVERAGE - total_coverage
        print(f"❌ ПРОВАЛ: Не хватает {diff:.2f}% покрытия")
        status = "FAIL"

    # Детали по пакетам
    if package_coverage:
        print("\n📦 Покрытие по пакетам:")
        print("-" * 60)
        for package, coverage in sorted(package_coverage.items(), key=lambda x: x[1]):
            status_icon = "✅" if coverage >= MINIMUM_COVERAGE else "⚠️"
            print(f"{status_icon} {package:40} {coverage:6.2f}%")

    print("=" * 60 + "\n")
    return status == "PASS"


def main():
    """Главная функция."""
    # Путь к coverage.xml (может быть в корне или в подпапках)
    possible_paths = ["coverage.xml", "../coverage.xml", "./coverage.xml"]

    coverage_xml = None
    for path in possible_paths:
        if Path(path).exists():
            coverage_xml = path
            break

    if not coverage_xml:
        print("❌ Файл coverage.xml не найден")
        print("\nЗапустите сначала:")
        print("  pytest --cov=bot --cov-report=xml")
        return 1

    # Парсим покрытие
    total_coverage = parse_coverage_xml(coverage_xml)
    if total_coverage is None:
        return 1

    package_coverage = get_package_coverage(coverage_xml)

    # Выводим отчет
    success = print_coverage_report(total_coverage, package_coverage)

    # Возвращаем код выхода
    if success:
        print("✅ Проверка покрытия пройдена!")
        return 0
    else:
        print("❌ Проверка покрытия не пройдена!")
        print(
            f"\n💡 Совет: Добавьте больше тестов для достижения {MINIMUM_COVERAGE}% покрытия"
        )
        return 1


if __name__ == "__main__":
    sys.exit(main())
