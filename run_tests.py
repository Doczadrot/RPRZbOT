import unittest
import coverage
import os
import sys

# Добавляем текущую директорию в путь для импорта
sys.path.append(os.path.abspath(os.path.dirname(__file__)))

# Инициализируем coverage
cov = coverage.Coverage(
    source=['src'],
    omit=['*/__pycache__/*', '*/tests/*', '*/venv/*']
)

# Запускаем измерение покрытия
cov.start()

# Загружаем все тесты
loader = unittest.TestLoader()
test_suite = loader.discover('.', pattern='test_*.py')

# Запускаем тесты
runner = unittest.TextTestRunner(verbosity=2)
result = runner.run(test_suite)

# Останавливаем измерение покрытия
cov.stop()

# Сохраняем результаты
cov.save()

# Выводим отчет в консоль
print('\n\nПокрытие кода тестами:')
cov.report()

# Генерируем HTML-отчет
cov.html_report(directory='coverage_html')

print(f'\nHTML-отчет сохранен в директории: {os.path.abspath("coverage_html")}\n')
print(f'Для просмотра отчета откройте файл: {os.path.abspath("coverage_html/index.html")}\n')

# Выводим информацию о запуске тестов
print(f'Запущено тестов: {result.testsRun}')
print(f'Ошибок: {len(result.errors)}')
print(f'Неудач: {len(result.failures)}')

# Выходим с кодом ошибки, если есть проблемы с тестами
sys.exit(not result.wasSuccessful())