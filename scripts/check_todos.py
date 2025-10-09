#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Скрипт сканирования кода на наличие TODO/FIXME комментариев.

Используется для отслеживания технического долга.
"""

import re
import sys
from pathlib import Path
from typing import Dict, List, Tuple

# Фикс кодировки для Windows
if sys.platform == "win32":
    import codecs

    sys.stdout = codecs.getwriter("utf-8")(sys.stdout.buffer, "strict")
    sys.stderr = codecs.getwriter("utf-8")(sys.stderr.buffer, "strict")

# Паттерны для поиска
TODO_PATTERNS = [
    r"#\s*TODO[:\s]+(.*)",
    r"#\s*FIXME[:\s]+(.*)",
    r"#\s*HACK[:\s]+(.*)",
    r"#\s*XXX[:\s]+(.*)",
    r"#\s*BUG[:\s]+(.*)",
    r"#\s*NOTE[:\s]+(.*)",
]

# Директории для исключения
EXCLUDE_DIRS = {
    "__pycache__",
    ".git",
    ".pytest_cache",
    "htmlcov",
    "venv",
    "env",
    ".venv",
    "node_modules",
    "logs",
    ".github",
}

# Расширения файлов для проверки
INCLUDE_EXTENSIONS = {".py", ".yml", ".yaml", ".md", ".txt", ".sh"}


def find_todos_in_file(file_path: Path) -> List[Tuple[int, str, str]]:
    """Ищет TODO/FIXME в файле."""
    todos = []

    try:
        with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
            for line_num, line in enumerate(f, start=1):
                for pattern in TODO_PATTERNS:
                    match = re.search(pattern, line, re.IGNORECASE)
                    if match:
                        todo_type = (
                            line[match.start() : match.start() + 10]
                            .strip("#")
                            .strip()
                            .split()[0]
                        )
                        todo_text = (
                            match.group(1).strip() if match.groups() else line.strip()
                        )
                        todos.append((line_num, todo_type, todo_text))
    except Exception as e:
        print(f"⚠️ Ошибка чтения файла {file_path}: {e}", file=sys.stderr)

    return todos


def scan_directory(root_dir: Path) -> Dict[str, List[Tuple[int, str, str]]]:
    """Сканирует директорию на наличие TODO/FIXME."""
    results = {}

    for file_path in root_dir.rglob("*"):
        # Пропускаем директории и файлы в исключенных папках
        if file_path.is_dir():
            continue

        if any(excluded in file_path.parts for excluded in EXCLUDE_DIRS):
            continue

        # Проверяем только нужные расширения
        if file_path.suffix not in INCLUDE_EXTENSIONS:
            continue

        todos = find_todos_in_file(file_path)
        if todos:
            relative_path = str(file_path.relative_to(root_dir))
            results[relative_path] = todos

    return results


def print_report(results: Dict[str, List[Tuple[int, str, str]]]):
    """Выводит отчет о найденных TODO/FIXME."""
    total_count = sum(len(todos) for todos in results.values())

    print("\n" + "=" * 60)
    print("🔍 ОТЧЕТ О TODO/FIXME В КОДЕ")
    print("=" * 60)

    if not results:
        print("\n✅ TODO/FIXME не найдены!")
        print("=" * 60 + "\n")
        return

    print(f"\n📊 Найдено TODO/FIXME: {total_count}")
    print(f"📁 Файлов с комментариями: {len(results)}")

    # Группируем по типам
    type_counts = {}
    for todos in results.values():
        for _, todo_type, _ in todos:
            type_counts[todo_type] = type_counts.get(todo_type, 0) + 1

    print("\n📈 По типам:")
    for todo_type, count in sorted(type_counts.items(), key=lambda x: -x[1]):
        print(f"  - {todo_type}: {count}")

    # Детали по файлам
    print("\n📋 Детали:")
    print("-" * 60)

    for file_path, todos in sorted(results.items()):
        print(f"\n📄 {file_path}")
        for line_num, todo_type, todo_text in todos:
            print(f"  L{line_num:4d} [{todo_type}] {todo_text[:70]}")

    print("\n" + "=" * 60)

    # Рекомендации
    if total_count > 20:
        print("\n⚠️ ВНИМАНИЕ: Много технического долга!")
        print("💡 Рекомендация: Запланируйте рефакторинг")
    elif total_count > 10:
        print("\n💡 Совет: Постепенно устраняйте TODO в коде")
    else:
        print("\n✅ Технический долг под контролем")

    print()


def main():
    """Главная функция."""
    # Корневая директория проекта
    root_dir = Path.cwd()

    # Если запущено из scripts/, поднимаемся выше
    if root_dir.name == "scripts":
        root_dir = root_dir.parent

    print(f"🔍 Сканирование директории: {root_dir}")
    print(f"📂 Исключены: {', '.join(sorted(EXCLUDE_DIRS))}")
    print(f"📝 Проверяются: {', '.join(sorted(INCLUDE_EXTENSIONS))}")

    # Сканируем
    results = scan_directory(root_dir)

    # Выводим отчет
    print_report(results)

    # Всегда возвращаем 0 - это информационная проверка, не блокирующая
    return 0


if __name__ == "__main__":
    sys.exit(main())
