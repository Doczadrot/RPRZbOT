# PowerShell скрипт для остановки бота
Write-Host "🛑 Остановка всех экземпляров бота..." -ForegroundColor Red

# Останавливаем все процессы Python
Write-Host "1. Остановка процессов Python..." -ForegroundColor Yellow
try {
    $processes = Get-Process python -ErrorAction SilentlyContinue
    if ($processes) {
        Write-Host "   Найдено процессов Python: $($processes.Count)" -ForegroundColor Cyan
        foreach ($proc in $processes) {
            try {
                $cmdline = (Get-WmiObject Win32_Process -Filter "ProcessId = $($proc.Id)").CommandLine
                if ($cmdline -and ($cmdline -like "*main.py*" -or $cmdline -like "*run_bot.py*")) {
                    Stop-Process -Id $proc.Id -Force
                    Write-Host "   ✅ Остановлен процесс $($proc.Id): $($cmdline.Substring(0, [Math]::Min(50, $cmdline.Length)))..." -ForegroundColor Green
                } else {
                    Write-Host "   ⏭️ Пропущен процесс $($proc.Id): $($cmdline.Substring(0, [Math]::Min(50, $cmdline.Length)))..." -ForegroundColor Gray
                }
            } catch {
                Write-Host "   ❌ Ошибка остановки процесса $($proc.Id): $($_.Exception.Message)" -ForegroundColor Red
            }
        }
    } else {
        Write-Host "   📝 Процессы Python не найдены" -ForegroundColor Gray
    }
} catch {
    Write-Host "   ❌ Ошибка поиска процессов: $($_.Exception.Message)" -ForegroundColor Red
}

# Ждем
Write-Host "2. Ожидание 3 секунды..." -ForegroundColor Yellow
Start-Sleep -Seconds 3

# Проверяем, что процессы остановлены
Write-Host "3. Проверка остановки..." -ForegroundColor Yellow
try {
    $remainingProcesses = Get-Process python -ErrorAction SilentlyContinue
    if ($remainingProcesses) {
        Write-Host "   ⚠️ Остались процессы: $($remainingProcesses.Count)" -ForegroundColor Yellow
        foreach ($proc in $remainingProcesses) {
            $cmdline = (Get-WmiObject Win32_Process -Filter "ProcessId = $($proc.Id)").CommandLine
            Write-Host "   PID $($proc.Id): $($cmdline.Substring(0, [Math]::Min(50, $cmdline.Length)))..." -ForegroundColor Yellow
        }
    } else {
        Write-Host "   ✅ Все процессы бота остановлены" -ForegroundColor Green
    }
} catch {
    Write-Host "   ❌ Ошибка проверки: $($_.Exception.Message)" -ForegroundColor Red
}

Write-Host "🎉 Готово!" -ForegroundColor Green