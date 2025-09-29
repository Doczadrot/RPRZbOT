# Просмотр логов в правильной кодировке UTF-8
Write-Host "Просмотр логов в UTF-8 кодировке..." -ForegroundColor Green

# Устанавливаем кодировку консоли
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8

# Показываем последние 10 строк лога
if (Test-Path "logs/app.log") {
    Write-Host "`n--- Последние 10 строк app.log ---" -ForegroundColor Yellow
    Get-Content "logs/app.log" -Encoding UTF8 -Tail 10
} else {
    Write-Host "Файл logs/app.log не найден" -ForegroundColor Red
}

# Показываем последние 5 строк user_actions.log
if (Test-Path "logs/user_actions.log") {
    Write-Host "`n--- Последние 5 строк user_actions.log ---" -ForegroundColor Yellow
    Get-Content "logs/user_actions.log" -Encoding UTF8 -Tail 5
} else {
    Write-Host "Файл logs/user_actions.log не найден" -ForegroundColor Red
}

# Показываем последние 5 строк activity.csv
if (Test-Path "logs/activity.csv") {
    Write-Host "`n--- Последние 5 строк activity.csv ---" -ForegroundColor Yellow
    Get-Content "logs/activity.csv" -Encoding UTF8 -Tail 5
} else {
    Write-Host "Файл logs/activity.csv не найден" -ForegroundColor Red
}

Write-Host "`nГотово!" -ForegroundColor Green
Read-Host "Нажмите Enter для выхода"
