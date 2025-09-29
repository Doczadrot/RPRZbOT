#!/usr/bin/env python3
"""
Полная очистка и перезапуск бота
"""

import os
import sys
import subprocess
import time

def restart_bot():
    """Полная очистка и перезапуск бота"""
    print("🔄 Полная очистка и перезапуск бота...")
    
    # Останавливаем все процессы Python
    print("1. Остановка процессов Python...")
    try:
        # Сначала пробуем остановить через taskkill
        result = subprocess.run(["taskkill", "/f", "/im", "python.exe"], 
                              capture_output=True, timeout=10, text=True)
        if result.returncode == 0:
            print("   ✅ Процессы остановлены через taskkill")
        else:
            print("   ⚠️ taskkill не сработал, пробуем через psutil...")
            try:
                import psutil
                python_processes = [p for p in psutil.process_iter(['pid', 'name', 'cmdline']) 
                                  if p.info['name'] == 'python.exe']
                
                for proc in python_processes:
                    try:
                        proc.terminate()
                        print(f"   Остановлен процесс {proc.info['pid']}")
                    except:
                        pass
                print("   ✅ Процессы остановлены через psutil")
            except ImportError:
                print("   ⚠️ psutil не установлен, пропускаем")
            except Exception as e:
                print(f"   ❌ Ошибка остановки через psutil: {e}")
    except Exception as e:
        print(f"   ❌ Ошибка остановки процессов: {e}")
    
    # Удаляем все логи
    print("2. Удаление старых логов...")
    if os.path.exists("logs"):
        removed_count = 0
        for file in os.listdir("logs"):
            if file.endswith(('.log', '.csv', '.json')):
                try:
                    os.remove(os.path.join("logs", file))
                    print(f"   Удален: {file}")
                    removed_count += 1
                except Exception as e:
                    print(f"   ❌ Ошибка удаления {file}: {e}")
        print(f"   ✅ Удалено файлов: {removed_count}")
    else:
        print("   📁 Папка logs не найдена")
    
    # Ждем
    print("3. Ожидание 5 секунд...")
    time.sleep(5)
    
    # Запускаем бота
    print("4. Запуск бота...")
    try:
        # Проверяем наличие файла run_bot.py
        if not os.path.exists("run_bot.py"):
            print("   ❌ Файл run_bot.py не найден!")
            return
        
        # Запускаем бота
        process = subprocess.Popen([sys.executable, "run_bot.py"], 
                                 stdout=subprocess.PIPE, 
                                 stderr=subprocess.PIPE)
        print(f"   ✅ Бот запущен в фоновом режиме (PID: {process.pid})")
        
        # Ждем немного и проверяем, что процесс еще работает
        time.sleep(2)
        if process.poll() is None:
            print("   ✅ Процесс бота работает")
        else:
            print("   ❌ Процесс бота завершился неожиданно")
            stdout, stderr = process.communicate()
            if stderr:
                print(f"   Ошибка: {stderr.decode('utf-8', errors='replace')}")
        
    except Exception as e:
        print(f"   ❌ Ошибка запуска: {e}")
    
    print("🎉 Готово!")

if __name__ == '__main__':
    restart_bot()
