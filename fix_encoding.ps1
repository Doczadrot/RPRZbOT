# Исправление кодировки логов
Write-Host "Исправление кодировки логов..." -ForegroundColor Yellow

# Останавливаем бота
Write-Host "Остановка бота..." -ForegroundColor Yellow
Get-Process python* -ErrorAction SilentlyContinue | Stop-Process -Force
Start-Sleep -Seconds 2

# Удаляем старые логи
Write-Host "Удаление старых логов..." -ForegroundColor Yellow
if (Test-Path "logs") {
    Remove-Item "logs\*.log" -Force -ErrorAction SilentlyContinue
    Remove-Item "logs\*.csv" -Force -ErrorAction SilentlyContinue
    Remove-Item "logs\*.json" -Force -ErrorAction SilentlyContinue
}

# Запускаем бота с новой кодировкой
Write-Host "Запуск бота с исправленной кодировкой..." -ForegroundColor Green
python run_bot.py
