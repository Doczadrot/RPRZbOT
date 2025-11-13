#!/usr/bin/env python3
"""
Скрипт для анализа проекта и создания плана улучшений
"""
import re
import os
from pathlib import Path

def analyze_file(filepath):
    """Анализирует файл на предмет дублирования и неиспользованного кода"""
    try:
        with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()
        
        functions = set(re.findall(r'def\s+(\w+)', content))
        imports = set(re.findall(r'^import\s+(\w+)|^from\s+(\w+)\s+import', content, re.MULTILINE))
        
        return {
            'path': filepath,
            'lines': len(content.split('\n')),
            'functions': functions,
            'imports': imports,
            'size': len(content)
        }
    except Exception as e:
        return {'path': filepath, 'error': str(e)}

def main():
    bot_dir = Path('bot')
    files = list(bot_dir.glob('*.py'))
    
    print("=== Анализ файлов проекта ===\n")
    
    results = []
    for file in files:
        result = analyze_file(file)
        results.append(result)
        if 'error' not in result:
            print(f"{result['path']}:")
            print(f"  Строк: {result['lines']}")
            print(f"  Функций: {len(result['functions'])}")
            print(f"  Размер: {result['size']} символов")
            print()
    
    # Анализ дублирования
    print("\n=== Анализ дублирования функций ===\n")
    all_functions = {}
    for result in results:
        if 'functions' in result:
            for func in result['functions']:
                if func not in all_functions:
                    all_functions[func] = []
                all_functions[func].append(result['path'])
    
    duplicates = {k: v for k, v in all_functions.items() if len(v) > 1}
    if duplicates:
        print("Найдены дублирующиеся функции:")
        for func, files in duplicates.items():
            print(f"  {func}: {files}")
    else:
        print("Дублирующихся функций не найдено")
    
    print("\n=== Проверка main_webhook.py ===\n")
    webhook_file = bot_dir / 'main_webhook.py'
    if webhook_file.exists():
        with open(webhook_file, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()
        
        has_health = '/health' in content
        has_ping = '/ping' in content
        has_keepalive = 'keepalive' in content.lower() or 'keep-alive' in content.lower()
        has_threading = 'threading' in content or 'Thread' in content
        
        print(f"Health endpoint: {'YES' if has_health else 'NO'}")
        print(f"Ping endpoint: {'YES' if has_ping else 'NO'}")
        print(f"Keepalive механизм: {'YES' if has_keepalive else 'NO'}")
        print(f"Threading для keepalive: {'YES' if has_threading else 'NO'}")
        
        if not has_ping or not has_keepalive:
            print("\n[WARNING] Рекомендация: Добавить /ping endpoint и keepalive механизм для Railway")

if __name__ == '__main__':
    main()

