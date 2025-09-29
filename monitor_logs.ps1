# PowerShell скрипт для мониторинга логов бота
Write-Host "📊 Мониторинг логов RPRZ Safety Bot" -ForegroundColor Cyan

# Функция для отображения последних записей лога
function Show-LogTail {
    param(
        [string]$LogFile,
        [string]$Description,
        [int]$Lines = 10
    )
    
    if (Test-Path $LogFile) {
        Write-Host "`n📄 $Description" -ForegroundColor Yellow
        Write-Host "=" * 50 -ForegroundColor Gray
        Get-Content $LogFile -Tail $Lines -Encoding UTF8
    } else {
        Write-Host "❌ Файл $LogFile не найден" -ForegroundColor Red
    }
}

# Функция для мониторинга в реальном времени
function Watch-Log {
    param(
        [string]$LogFile,
        [string]$Description
    )
    
    if (Test-Path $LogFile) {
        Write-Host "`n👀 Мониторинг $Description (Ctrl+C для выхода)" -ForegroundColor Green
        Get-Content $LogFile -Wait -Tail 5 -Encoding UTF8
    } else {
        Write-Host "❌ Файл $LogFile не найден" -ForegroundColor Red
    }
}

# Меню выбора
while ($true) {
    Write-Host "`n📋 Выберите действие:" -ForegroundColor Cyan
    Write-Host "1. Показать последние записи основного лога" -ForegroundColor White
    Write-Host "2. Показать последние ошибки" -ForegroundColor White
    Write-Host "3. Показать действия пользователей" -ForegroundColor White
    Write-Host "4. Показать API запросы" -ForegroundColor White
    Write-Host "5. Мониторинг в реальном времени" -ForegroundColor White
    Write-Host "6. Показать все логи" -ForegroundColor White
    Write-Host "7. Очистить старые логи" -ForegroundColor White
    Write-Host "0. Выход" -ForegroundColor White
    
    $choice = Read-Host "`nВведите номер (0-7)"
    
    switch ($choice) {
        "1" {
            Show-LogTail "logs/app.log" "Основной лог" 20
        }
        "2" {
            Show-LogTail "logs/errors.log" "Ошибки" 15
        }
        "3" {
            Show-LogTail "logs/user_actions.log" "Действия пользователей" 15
        }
        "4" {
            Show-LogTail "logs/api_requests.log" "API запросы" 15
        }
        "5" {
            Write-Host "`nВыберите лог для мониторинга:" -ForegroundColor Yellow
            Write-Host "1. Основной лог"
            Write-Host "2. Ошибки"
            Write-Host "3. Действия пользователей"
            Write-Host "4. API запросы"
            $logChoice = Read-Host "Введите номер (1-4)"
            
            switch ($logChoice) {
                "1" { Watch-Log "logs/app.log" "основного лога" }
                "2" { Watch-Log "logs/errors.log" "ошибок" }
                "3" { Watch-Log "logs/user_actions.log" "действий пользователей" }
                "4" { Watch-Log "logs/api_requests.log" "API запросов" }
                default { Write-Host "❌ Неверный выбор" -ForegroundColor Red }
            }
        }
        "6" {
            Show-LogTail "logs/app.log" "Основной лог" 10
            Show-LogTail "logs/errors.log" "Ошибки" 5
            Show-LogTail "logs/user_actions.log" "Действия пользователей" 5
            Show-LogTail "logs/api_requests.log" "API запросы" 5
        }
        "7" {
            Write-Host "`n🧹 Очистка старых логов..." -ForegroundColor Yellow
            $oldLogs = Get-ChildItem "logs" -Filter "*.log" | Where-Object { $_.LastWriteTime -lt (Get-Date).AddDays(-7) }
            if ($oldLogs) {
                $oldLogs | Remove-Item -Force
                Write-Host "✅ Удалено логов: $($oldLogs.Count)" -ForegroundColor Green
            } else {
                Write-Host "ℹ️ Старых логов не найдено" -ForegroundColor Blue
            }
        }
        "0" {
            Write-Host "👋 До свидания!" -ForegroundColor Green
            break
        }
        default {
            Write-Host "❌ Неверный выбор. Попробуйте снова." -ForegroundColor Red
        }
    }
    
    if ($choice -ne "0") {
        Read-Host "`nНажмите Enter для продолжения"
    }
}
