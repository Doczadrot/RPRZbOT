# Финальный скрипт для запуска RPRZ Safety Bot
Write-Host "🚀 RPRZ Safety Bot - Финальный запуск" -ForegroundColor Cyan

# Функция для вывода статуса
function Write-Status {
    param([string]$Message, [string]$Status = "INFO")
    $timestamp = Get-Date -Format "HH:mm:ss"
    switch ($Status) {
        "SUCCESS" { Write-Host "[$timestamp] ✅ $Message" -ForegroundColor Green }
        "ERROR" { Write-Host "[$timestamp] ❌ $Message" -ForegroundColor Red }
        "WARNING" { Write-Host "[$timestamp] ⚠️ $Message" -ForegroundColor Yellow }
        "INFO" { Write-Host "[$timestamp] ℹ️ $Message" -ForegroundColor Blue }
        default { Write-Host "[$timestamp] $Message" -ForegroundColor White }
    }
}

# Функция для остановки процессов Python
function Stop-PythonProcesses {
    Write-Status "Остановка всех процессов Python..." "INFO"
    try {
        $processes = Get-Process -Name "python" -ErrorAction SilentlyContinue
        if ($processes) {
            Stop-Process -Name "python" -Force
            Write-Status "Остановлено процессов: $($processes.Count)" "SUCCESS"
        } else {
            Write-Status "Процессы Python не найдены" "INFO"
        }
    } catch {
        Write-Status "Ошибка при остановке процессов: $($_.Exception.Message)" "ERROR"
    }
}

# Функция для быстрого тестирования
function Start-QuickTest {
    Write-Status "Запуск быстрого тестирования..." "INFO"
    
    try {
        $result = python simple_test.py
        if ($LASTEXITCODE -eq 0) {
            Write-Status "Тесты пройдены успешно!" "SUCCESS"
            return $true
        } else {
            Write-Status "Тесты провалены!" "ERROR"
            return $false
        }
    } catch {
        Write-Status "Ошибка запуска тестов: $($_.Exception.Message)" "ERROR"
        return $false
    }
}

# Функция для запуска бота
function Start-Bot {
    Write-Status "Запуск бота..." "INFO"
    Write-Host ""
    Write-Host "🚀 Бот запускается..." -ForegroundColor Cyan
    Write-Host "📱 Найдите бота @FixPriceKusr_bot в Telegram" -ForegroundColor Cyan
    Write-Host "⏹️ Нажмите Ctrl+C для остановки" -ForegroundColor Yellow
    Write-Host ""
    
    try {
        python run_bot.py
    } catch {
        Write-Status "Ошибка запуска бота: $($_.Exception.Message)" "ERROR"
    } finally {
        Write-Status "Бот остановлен" "INFO"
    }
}

# Функция для показа логов
function Show-Logs {
    Write-Host ""
    Write-Host "📊 Логи бота:" -ForegroundColor Yellow
    Write-Host "1. Быстрый просмотр: .\view_logs.ps1" -ForegroundColor White
    Write-Host "2. Детальный мониторинг: .\monitor_logs.ps1" -ForegroundColor White
    Write-Host "3. Просмотр в реальном времени: Get-Content logs/app.log -Wait -Tail 10" -ForegroundColor White
    Write-Host ""
}

# Основной цикл
while ($true) {
    Write-Host ""
    Write-Host "📋 Выберите действие:" -ForegroundColor Cyan
    Write-Host "1. Полный цикл: тесты + запуск бота" -ForegroundColor White
    Write-Host "2. Только тестирование" -ForegroundColor White
    Write-Host "3. Только запуск бота" -ForegroundColor White
    Write-Host "4. Остановить все процессы Python" -ForegroundColor White
    Write-Host "5. Показать логи" -ForegroundColor White
    Write-Host "6. Просмотр логов в реальном времени" -ForegroundColor White
    Write-Host "0. Выход" -ForegroundColor White
    
    $choice = Read-Host "`nВведите номер (0-6)"
    
    switch ($choice) {
        "1" {
            Write-Status "Запуск полного цикла: тестирование + запуск" "INFO"
            
            # Останавливаем процессы
            Stop-PythonProcesses
            Start-Sleep -Seconds 3
            
            # Запускаем тесты
            if (Start-QuickTest) {
                Write-Status "Тесты пройдены, запускаем бота..." "SUCCESS"
                Start-Sleep -Seconds 2
                Start-Bot
            } else {
                Write-Status "Тесты провалены, бот не запускается!" "ERROR"
                Read-Host "Нажмите Enter для продолжения"
            }
        }
        "2" {
            Write-Status "Запуск только тестирования" "INFO"
            Stop-PythonProcesses
            Start-Sleep -Seconds 2
            Start-QuickTest
            Read-Host "Нажмите Enter для продолжения"
        }
        "3" {
            Write-Status "Запуск только бота" "INFO"
            Stop-PythonProcesses
            Start-Sleep -Seconds 2
            Start-Bot
        }
        "4" {
            Stop-PythonProcesses
            Read-Host "Нажмите Enter для продолжения"
        }
        "5" {
            Show-Logs
            try {
                .\view_logs.ps1
            } catch {
                Write-Status "Ошибка просмотра логов: $($_.Exception.Message)" "ERROR"
            }
        }
        "6" {
            Write-Status "Просмотр логов в реальном времени (Ctrl+C для выхода)" "INFO"
            try {
                Get-Content logs/app.log -Wait -Tail 10
            } catch {
                Write-Status "Ошибка просмотра логов: $($_.Exception.Message)" "ERROR"
            }
        }
        "0" {
            Write-Status "До свидания!" "SUCCESS"
            break
        }
        default {
            Write-Status "Неверный выбор. Попробуйте снова." "WARNING"
        }
    }
}

Write-Host ""
Write-Host "🎯 Спасибо за использование RPRZ Safety Bot!" -ForegroundColor Green

