# Простой скрипт для запуска RPRZ Safety Bot
Write-Host "RPRZ Safety Bot - Запуск" -ForegroundColor Cyan

# Функция для остановки процессов Python
function Stop-PythonProcesses {
    Write-Host "Остановка процессов Python..." -ForegroundColor Yellow
    
    try {
        $processes = Get-Process -Name "python*" -ErrorAction SilentlyContinue
        if ($processes) {
            Stop-Process -Name "python*" -Force
            Write-Host "Остановлено процессов: $($processes.Count)" -ForegroundColor Green
        } else {
            Write-Host "Процессы Python не найдены" -ForegroundColor Blue
        }
        
        taskkill /f /im python.exe 2>$null
        taskkill /f /im python3.exe 2>$null
        taskkill /f /im python3.12.exe 2>$null
        
        Start-Sleep -Seconds 3
        Write-Host "Процессы остановлены!" -ForegroundColor Green
        
    } catch {
        Write-Host "Ошибка: $($_.Exception.Message)" -ForegroundColor Red
    }
}

# Функция для тестирования
function Start-Test {
    Write-Host "Запуск тестов..." -ForegroundColor Yellow
    
    try {
        $result = python test_fixes_simple.py
        if ($LASTEXITCODE -eq 0) {
            Write-Host "Тесты пройдены!" -ForegroundColor Green
            return $true
        } else {
            Write-Host "Тесты провалены!" -ForegroundColor Red
            return $false
        }
    } catch {
        Write-Host "Ошибка тестов: $($_.Exception.Message)" -ForegroundColor Red
        return $false
    }
}

# Функция для запуска бота
function Start-Bot {
    Write-Host "Запуск бота..." -ForegroundColor Yellow
    Write-Host ""
    Write-Host "Бот запускается..." -ForegroundColor Cyan
    Write-Host "Найдите бота @FixPriceKusr_bot в Telegram" -ForegroundColor Cyan
    Write-Host "Нажмите Ctrl+C для остановки" -ForegroundColor Yellow
    Write-Host ""
    
    try {
        python run_bot.py
    } catch {
        Write-Host "Ошибка запуска: $($_.Exception.Message)" -ForegroundColor Red
    } finally {
        Write-Host "Бот остановлен" -ForegroundColor Blue
    }
}

# Основное меню
while ($true) {
    Write-Host ""
    Write-Host "Выберите действие:" -ForegroundColor Cyan
    Write-Host "1. Полный цикл: тесты + запуск бота" -ForegroundColor White
    Write-Host "2. Только тестирование" -ForegroundColor White
    Write-Host "3. Только запуск бота" -ForegroundColor White
    Write-Host "4. Остановить процессы Python" -ForegroundColor White
    Write-Host "0. Выход" -ForegroundColor White
    
    $choice = Read-Host "Введите номер (0-4)"
    
    switch ($choice) {
        "1" {
            Write-Host "Запуск полного цикла..." -ForegroundColor Blue
            
            Stop-PythonProcesses
            Start-Sleep -Seconds 3
            
            if (Start-Test) {
                Write-Host "Тесты пройдены, запускаем бота..." -ForegroundColor Green
                Start-Sleep -Seconds 2
                Start-Bot
            } else {
                Write-Host "Тесты провалены, бот не запускается!" -ForegroundColor Red
                Read-Host "Нажмите Enter для продолжения"
            }
        }
        "2" {
            Write-Host "Запуск тестирования..." -ForegroundColor Blue
            Stop-PythonProcesses
            Start-Sleep -Seconds 2
            Start-Test
            Read-Host "Нажмите Enter для продолжения"
        }
        "3" {
            Write-Host "Запуск бота..." -ForegroundColor Blue
            Stop-PythonProcesses
            Start-Sleep -Seconds 2
            Start-Bot
        }
        "4" {
            Stop-PythonProcesses
            Read-Host "Нажмите Enter для продолжения"
        }
        "0" {
            Write-Host "До свидания!" -ForegroundColor Green
            break
        }
        default {
            Write-Host "Неверный выбор. Попробуйте снова." -ForegroundColor Yellow
        }
    }
}

Write-Host ""
Write-Host "Спасибо за использование RPRZ Safety Bot!" -ForegroundColor Green
