# PowerShell скрипт для быстрого просмотра логов
Write-Host "📊 Быстрый просмотр логов RPRZ Safety Bot" -ForegroundColor Cyan

# Проверяем наличие папки логов
if (-not (Test-Path "logs")) {
    Write-Host "❌ Папка logs не найдена!" -ForegroundColor Red
    exit 1
}

# Показываем статистику логов
Write-Host "`n📈 Статистика логов:" -ForegroundColor Yellow
$logFiles = Get-ChildItem "logs" -Filter "*.log" | Sort-Object LastWriteTime -Descending

foreach ($log in $logFiles) {
    $size = [math]::Round($log.Length / 1KB, 2)
    $lastWrite = $log.LastWriteTime.ToString("dd.MM.yyyy HH:mm:ss")
    Write-Host "📄 $($log.Name) - $size KB - $lastWrite" -ForegroundColor White
}

# Показываем последние записи из основного лога
if (Test-Path "logs/app.log") {
    Write-Host "`n📄 Последние записи основного лога:" -ForegroundColor Yellow
    Write-Host "=" * 60 -ForegroundColor Gray
    Get-Content "logs/app.log" -Tail 15 -Encoding UTF8 | ForEach-Object {
        if ($_ -match "ERROR") {
            Write-Host $_ -ForegroundColor Red
        } elseif ($_ -match "WARNING") {
            Write-Host $_ -ForegroundColor Yellow
        } elseif ($_ -match "INFO") {
            Write-Host $_ -ForegroundColor Green
        } else {
            Write-Host $_ -ForegroundColor White
        }
    }
}

# Показываем ошибки
if (Test-Path "logs/errors.log") {
    $errorCount = (Get-Content "logs/errors.log" -Encoding UTF8).Count
    if ($errorCount -gt 0) {
        Write-Host "`n❌ Ошибки ($errorCount записей):" -ForegroundColor Red
        Write-Host "=" * 60 -ForegroundColor Gray
        Get-Content "logs/errors.log" -Tail 5 -Encoding UTF8
    } else {
        Write-Host "`n✅ Ошибок не найдено" -ForegroundColor Green
    }
}

# Показываем действия пользователей
if (Test-Path "logs/user_actions.log") {
    $userActions = (Get-Content "logs/user_actions.log" -Encoding UTF8).Count
    Write-Host "`n👤 Действия пользователей: $userActions записей" -ForegroundColor Blue
}

# Показываем API запросы
if (Test-Path "logs/api_requests.log") {
    $apiRequests = (Get-Content "logs/api_requests.log" -Encoding UTF8).Count
    Write-Host "🌐 API запросы: $apiRequests записей" -ForegroundColor Magenta
}

Write-Host "`n💡 Для детального мониторинга запустите: .\monitor_logs.ps1" -ForegroundColor Cyan
Read-Host "`nНажмите Enter для выхода"

