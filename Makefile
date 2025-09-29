# RPRZ Safety Bot - Makefile для автотестов

.PHONY: help install test test-unit test-coverage test-html clean lint format

help: ## Показать справку
	@echo "Доступные команды:"
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-20s\033[0m %s\n", $$1, $$2}'

install: ## Установить зависимости
	pip install -r requirements.txt

test: ## Запустить все тесты
	python -m pytest

test-unit: ## Запустить только unit тесты
	python -m pytest -m unit

test-coverage: ## Запустить тесты с покрытием кода
	python -m pytest --cov=bot --cov-report=term-missing --cov-fail-under=80

test-html: ## Создать HTML отчет покрытия
	python -m pytest --cov=bot --cov-report=html:htmlcov --cov-report=term-missing
	@echo "HTML отчет: htmlcov/index.html"

test-fast: ## Быстрые тесты (без покрытия)
	python -m pytest -x -v

lint: ## Проверка кода линтером
	flake8 . --count --select=E9,F63,F7,F82 --show-source --statistics
	flake8 . --count --exit-zero --max-complexity=10 --max-line-length=127 --statistics

format: ## Форматирование кода
	black . --line-length 127
	isort . --profile black

clean: ## Очистить временные файлы
	rm -rf htmlcov/
	rm -rf .coverage
	rm -rf coverage.xml
	rm -rf .pytest_cache/
	rm -rf __pycache__/
	find . -type d -name "__pycache__" -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete

ci: ## Запуск CI тестов (как в GitHub Actions)
	pip install -r requirements.txt
	python -m pytest --cov=bot --cov-report=xml --cov-report=html --cov-fail-under=80

# Алиасы
t: test
tc: test-coverage
th: test-html

