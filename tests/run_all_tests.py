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

# Загружаем тесты из всех тестовых файлов
test_suite1 = loader.loadTestsFromName('test_RPRZBOT')
test_suite2 = loader.loadTestsFromName('test_additional')
test_suite3 = loader.loadTestsFromName('test_db_operations')
test_suite4 = loader.loadTestsFromName('test_photo_handling')
test_suite5 = loader.loadTestsFromName('test_error_handling')
test_suite6 = loader.loadTestsFromName('test_additional_coverage')

# Объединяем все тесты в один набор
all_tests = unittest.TestSuite([test_suite1, test_suite2, test_suite3, test_suite4, test_suite5, test_suite6])

# Также добавляем тесты, найденные через discover (на случай, если есть другие тестовые файлы)
discovered_tests = loader.discover('.', pattern='test_*.py')
for test in discovered_tests:
    all_tests.addTest(test)

# Запускаем тесты
runner = unittest.TextTestRunner(verbosity=2)
result = runner.run(all_tests)

# Останавливаем измерение покрытия
cov.stop()

# Сохраняем результаты
cov.save()

# Выводим отчет в консоль
print('\n\nПокрытие кода тестами:')
cov_result = cov.report()

# Генерируем HTML-отчет
cov.html_report(directory='htmlcov')

print(f'\nHTML-отчет сохранен в директории: {os.path.abspath("htmlcov")}\n')
print(f'Для просмотра отчета откройте файл: {os.path.abspath("htmlcov/index.html")}\n')

# Выводим информацию о запуске тестов
print(f'Запущено тестов: {result.testsRun}')
print(f'Ошибок: {len(result.errors)}')
print(f'Неудач: {len(result.failures)}')

# Проверяем, достигли ли мы 80% покрытия
if cov_result >= 80:
    print(f'\nУспех! Достигнуто покрытие кода тестами: {cov_result:.2f}% (цель: 80%)')
else:
    print(f'\nПокрытие кода тестами: {cov_result:.2f}% (цель: 80%)')
    print('Необходимо добавить больше тестов для достижения 80% покрытия.')