import unittest
import sys
import os

# Добавляем текущую директорию в путь для импорта
sys.path.append(os.path.abspath(os.path.dirname(__file__)))

# Загружаем все тесты
loader = unittest.TestLoader()

# Загружаем тесты из основного файла тестов
test_suite1 = loader.loadTestsFromName('test_RPRZBOT')

# Загружаем тесты из дополнительного файла тестов
test_suite2 = loader.loadTestsFromName('test_additional')

# Объединяем все тесты в один набор
all_tests = unittest.TestSuite([test_suite1, test_suite2])

# Запускаем тесты
runner = unittest.TextTestRunner(verbosity=2)
result = runner.run(all_tests)

# Выводим информацию о запуске тестов
print(f'\nЗапущено тестов: {result.testsRun}')
print(f'Ошибок: {len(result.errors)}')
print(f'Неудач: {len(result.failures)}')

# Выходим с кодом ошибки, если есть проблемы с тестами
sys.exit(not result.wasSuccessful())